#!/usr/bin/env python3
"""Red Dragon «التنين الأحمر» — the brain above the Black Dragon engine. Standard library only.

  python scripts/rd.py start                 first thing when the package reaches Claude
  python scripts/rd.py understand "<نص>"     fix wrong-keyboard and voice-typing slips
  python scripts/rd.py brief "<الطلب>"       short mission brief as JSON (used by the desktop app)
  python scripts/rd.py plan "<الطلب>"        mission plan: playbook + steps for this place + gates + lessons
  python scripts/rd.py route|map|show        find / list / open a playbook or a power
  python scripts/rd.py learn|recall|outcome|retro|memory   self-learning
  python scripts/rd.py skills find "<كلمات>"  search the bundled library of 200 famous Claude skills (list / show NAME / install NAME)
  python scripts/rd.py re TARGET             what a file / folder / URL is, and the analysis road
  python scripts/rd.py repo PATH             dossier of a source repository (read-only)
  python scripts/rd.py intel "<words>"       search the dossiers bundled in mind/intel
  python scripts/rd.py doctor                what is reachable here
  python scripts/rd.py chats "<سؤال>"        memory of every past conversation (what was asked, decided, delivered)
  python scripts/rd.py files "<كلمة>"        delivered file paths from those chats + does each still exist
  python scripts/rd.py guard PATH            is another session writing this folder? (--save / --diff snapshot, lock / unlock)
  python scripts/rd.py x ARGS...             pass through to the engine (engine/scripts/dragon.py)
It reads and advises; it never installs, publishes, spends or deletes."""
import argparse, datetime, hashlib, json, math, os, re, shutil, subprocess, sys
from pathlib import Path

VERSION = "2.7.1"
ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
MIND = ROOT / "mind"
MEM = Path(os.environ.get("RED_DRAGON_HOME") or Path.home() / ".red-dragon")
# v2.4: what the white dragon learned on this machine is read too (read-only, never written).
LEGACY_MEM = [Path(os.environ.get("WHITE_DRAGON_HOME") or Path.home() / ".white-dragon")]
COST = {"free": "✅ ببلاش", "ask": "🔒 بموافقة", "paid": "💰 مدفوع", "never": "⛔ ممنوع"}
COST_RANK = {"free": 0, "ask": 1, "paid": 2, "never": 3}

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ------------------------------------------------------------------ words
AR_DIAC = re.compile("[ً-ْـ]")
STOP = set("في من على عن الى إلى ده دي دا اللي عايز عاوز اعمل اعملي ممكن يا كل مع او أو و the a an of to for and or in on with me my this that please make do".split())
PREFIXES = ("وبال", "فبال", "وال", "فال", "بال", "كال", "لل", "ال")


def norm(s):
    s = AR_DIAC.sub("", str(s).lower())
    return re.sub("[إأآا]", "ا", s).replace("ة", "ه").replace("ى", "ي")


def tokens(s):
    out = []
    for w in re.findall(r"[\w؀-ۿ]+", norm(s)):
        for p in PREFIXES:
            if w.startswith(p) and len(w) - len(p) >= 3:
                w = w[len(p):]
                break
        if len(w) > 1 and w not in STOP:
            out.append(w)
    return out


def match(a, b):
    if a == b:
        return 2
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return 1
    return 0


def score(qt, bag):
    return sum(max((match(t, k) for k in bag), default=0) for t in qt)


# ------------------------------------------------------------------ place
def place():
    """cloud-chat (claude.ai), cloud-code (Claude Code remote), pc-owner (the owner's laptop), pc-other."""
    m = os.environ.get("RED_DRAGON_MODE") or os.environ.get("DRAGON_MODE")
    if m:
        return {"pc": "pc-owner", "cloud": "cloud-chat"}.get(m, m)
    if Path("/mnt/user-data").exists():
        return "cloud-chat"
    if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        return "cloud-code"
    owner = (Path.home() / "OneDrive" / "Desktop" / "التنين الأسود").exists() or (Path.home() / "re-tools" / "retool.py").exists()
    return "pc-owner" if owner else "pc-other"


def is_pc(p=None):
    return (p or place()).startswith("pc")


# ------------------------------------------------------------------ data
def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def playbooks():
    d = jload(MIND / "playbooks.json", {"playbooks": []})
    for p in d["playbooks"]:
        p["_tok"] = set(tokens(p.get("triggers", "") + " " + p["ar"] + " " + p.get("en", "")))
    return d["playbooks"]


def powers():
    out = []
    for f, src in ((ENGINE / "tools" / "powers" / "powers.json", "engine"), (MIND / "connections.json", "red")):
        d = jload(f, {})
        for p in d.get("powers", []):
            p["_src"] = src
            p["_tok"] = set(tokens(p.get("triggers", "") + " " + p.get("ar", "") + " " + p.get("en", "")))
            out.append(p)
    return out


# ------------------------------------------------------------------ memory (self-learning)
def mem_file(name):
    MEM.mkdir(parents=True, exist_ok=True)
    return MEM / name


def lessons():
    """Bundled seed lessons + what this machine learned. Later lines win on the same id."""
    rows = {}
    for f in (MIND / "lessons_seed.jsonl", *[m / "lessons.jsonl" for m in LEGACY_MEM], MEM / "lessons.jsonl"):
        if f.is_file():
            for ln in f.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(ln)
                    rows[r["id"]] = {**rows.get(r["id"], {}), **r}
                except Exception:
                    continue
    return list(rows.values())


def lesson_id(text):
    return hashlib.sha1(" ".join(tokens(text)).encode("utf-8")).hexdigest()[:10]


def learn(text, domain="general", trigger="", kind="rule", source="owner"):
    text = " ".join(str(text).split())
    if len(text) < 8:
        raise SystemExit("الدرس قصير قوي: اكتب إيه اللي حصل وإيه اللي يتعمل المرة الجاية.")
    if re.search(r"(sk-ant-|sk-[A-Za-z0-9]{24,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|password\s*[:=])", text):
        raise SystemExit("الدرس فيه حاجة شبه مفتاح أو باسورد: مااتحفظش.")
    lid = lesson_id(text)
    old = next((l for l in lessons() if l["id"] == lid), None)
    row = {"id": lid, "text": text, "domain": domain, "trigger": trigger, "kind": kind, "source": source,
           "date": datetime.date.today().isoformat(), "seen": (old or {}).get("seen", 0) + 1, "hits": (old or {}).get("hits", 0)}
    with mem_file("lessons.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row, bool(old)


def recall(q, limit=6, domain=None, minscore=2):
    qt = tokens(q)
    out = []
    for l in lessons():
        s = score(qt, set(tokens(l["text"] + " " + l.get("trigger", "") + " " + l.get("domain", ""))))
        if domain and l.get("domain") == domain:
            s += 1
        if s >= minscore:
            out.append((s + min(l.get("seen", 1), 3) * 0.3, l))      # a lesson repeated by the owner weighs more
    out.sort(key=lambda x: -x[0])
    return [l for _, l in out[:limit]]


def outcomes():
    """playbook id -> {ok, fail}. Read from the append-only outcome log."""
    d = {}
    for f in (*[m / "outcomes.jsonl" for m in LEGACY_MEM], MEM / "outcomes.jsonl"):
        if not f.is_file():
            continue
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                d.setdefault(r["id"], {"ok": 0, "fail": 0})[r["result"]] += 1
            except Exception:
                continue
    return d


def trust(pid, oc):
    """Laplace-smoothed success rate: 0.5 with no history, moves with evidence."""
    o = oc.get(pid, {"ok": 0, "fail": 0})
    return (o["ok"] + 1) / (o["ok"] + o["fail"] + 2)


# ------------------------------------------------------------------ route / plan
# words that carry no task (Egyptian question words and filler); "فين", "خلصت", "عملت" stay: they mean status
QSTOP = set(norm(w) for w in "ايه ازاي ازى هل هو هي هى دي ده دا ما ماذا لماذا ليه لو عشان علشان بس كده برضه انا انت احنا لي ليا "
            "عندي عندك ممكن عايزك عاوزك اريد اريدك قم كمان تاني الان دلوقتي جدا اي اى ايضا كمان بكل جميع لكل الذي التي اللى".split())
SUFFIX = ("ات", "ين", "ون", "ها", "هم", "كم", "نا", "يه", "ه")
_idf = {}


def _stem(w):
    for suf in SUFFIX:
        if len(w) - len(suf) >= 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _lev1(a, b):
    """True when a and b differ by one insertion, deletion or substitution."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = j = d = 0
    while i < len(a) and j < len(b):
        if a[i] != b[j]:
            d += 1
            if d > 1:
                return False
            if len(a) == len(b):
                i += 1
            j += 1
        else:
            i += 1
            j += 1
    return d + (len(b) - j) + (len(a) - i) <= 1


def _tmatch(a, b):
    if a == b:
        return 2.0
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return 1.0
    sa, sb = _stem(a), _stem(b)
    if len(sa) >= 3 and sa == sb:
        return 1.6
    if min(len(a), len(b)) >= 5 and _lev1(a, b):   # one slip of voice typing: فديو / فيديو, مهارهة / مهاره
        return 1.0
    return 0.0


def _route_idf(pbs):
    key = tuple(p["id"] for p in pbs)
    if _idf.get("k") != key:
        n = len(pbs)
        df = {}
        for p in pbs:
            for t in p["_tok"]:
                df[t] = df.get(t, 0) + 1
        w = {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}
        mean = sum(w.values()) / max(1, len(w))
        _idf.update(k=key, w={t: v / mean for t, v in w.items()})
    return _idf["w"]


INTENT = [  # (pattern on the normalized text, playbook id, bonus): few, general, high precision
    (r"(حلل|افحص|ادرس)\S*.{0,80}(اصنع|اعمل|ابني|سوي)\S*.{0,40}(مثله|زيه|شبيه|شبهه|نسخه|نفسه)", "clone-own-tool", 6.0),
    (r"(طور|طوير|تطوير|ارفع|زود)\S*.{0,60}(التنين|نفسك|ذكاءك|ذكائك|قدراتك)", "self-improve", 5.0),
    (r"(فين|وين)\s+(الملف|الفيديو|الفديو|المهاره|النسخه|الناتج)|^(خلصت|عملت ايه|وصلت لفين)", "status", 5.0),
    (r"(اصنع|اعمل|ابني|سوي|انشئ)\S*\s+(لي\s+|لكلاود\s+)?مهار", "build-skill", 4.0),
]
URL_ONLY = [(r"github\.com/", "re-repo"), (r"(tiktok\.com|youtu\.?be|instagram\.com|facebook\.com|x\.com/|twitter\.com)", "download")]
NONE_RX = (r"^\W*(ازيك|ازيكم|اهلا|مرحبا|السلام عليكم|صباح الخير|مساء الخير|من انت|مين انت|انت مين|شكرا|تمام|موافق|ماشي|اوك|ok|كمل|اكمل|يلا)\W*$")


def route(q, limit=5):
    t = norm(q).strip()
    bare = re.sub(r"[a-z]:\\\S*|https?://\S+|\(مرفقات:[^)]*\)", " ", t)
    oc = outcomes()
    pbs = playbooks()
    qt = tokens(q)                      # powers keep the plain match below
    if len(tokens(bare)) == 0 and re.search(r"https?://", t):     # a bare link: the site says what to do with it
        pid = next((p for rx, p in URL_ONLY if re.search(rx, t)), None)
        pb = [(4.0, p) for p in pbs if p["id"] == pid]
    elif re.match(NONE_RX, t) or len(tokens(bare)) == 0:
        pb = []
    else:
        qp = [w for w in qt if w not in QSTOP]
        idf = _route_idf(pbs)

        def sc(p):
            tot = 0.0
            for w in qp:
                best = 0.0
                for k in p["_tok"]:
                    m = _tmatch(w, k)
                    if m:
                        best = max(best, m * idf.get(k, 1.0))
                tot += best
            for rx, pid, bonus in INTENT:
                if pid == p["id"] and re.search(rx, t):
                    tot += bonus
            return tot
        pb = [(sc(p) * (0.7 + 0.6 * trust(p["id"], oc)), p) for p in pbs]
    pb = sorted([x for x in pb if x[0] > 0], key=lambda x: -x[0])[:limit]
    pw = [(score(qt, p["_tok"]), p) for p in powers()]
    pw = sorted([x for x in pw if x[0] > 0], key=lambda x: (-x[0], COST_RANK.get(x[1].get("cost"), 9)))[:limit + 2]
    return pb, pw


def here_steps(p, where):
    """A step may start with [pc] or [cloud]; unmarked steps apply everywhere."""
    out = []
    for s in p.get("steps", []):
        m = re.match(r"\[(pc|cloud)\]\s*", s)
        if m and ((m.group(1) == "pc") != is_pc(where)):
            continue
        out.append(s[m.end():] if m else s)
    return out


def plan(q, as_json=False):
    where = place()
    u = understand(q)
    q = u["text"]
    pb, pw = route(q)
    ls = recall(q, domain=pb[0][1].get("domain") if pb else None)
    if as_json:
        print(json.dumps({"place": where, "playbooks": [{k: v for k, v in p.items() if not k.startswith("_")} | {"score": round(s, 2)} for s, p in pb],
                          "powers": [{"id": p["id"], "ar": p.get("ar"), "cost": p.get("cost"), "score": s} for s, p in pw],
                          "lessons": ls}, ensure_ascii=False, indent=1))
        return
    P = print
    P(f"🐉 التنين الأحمر v{VERSION} · المكان: {where}")
    if u["changed"]:
        P("🔤 الطلب بعد فك الكتابة: " + q[:200] + ("  (الكيبورد كان إنجليزي)" if u["layout_fixed"] else "") + ("  · " + "، ".join(u["words_fixed"]) if u["words_fixed"] else ""))
    P("\n① أول رد (قبل أي أداة):")
    P(f"   فهمت إنك عايز: «{' '.join(q.split())[:160]}» ← اكتبها بكلامك بعد فك غلطات الإملاء، وقول خمّنت إيه.")
    P("   هعمل: 3–5 نقط + الناتج فين + ⏱ التقدير. سؤال واحد بس لو الطلب ليه معنيين.")
    if not pb:
        P("\n② مفيش playbook مطابق. استخدم: rd.py map ، أو المحرك: rd.py x find \"<الطلب>\" ، وبعد ما تخلص: rd.py learn …")
    for i, (s, p) in enumerate(pb[:2]):
        P(f"\n{'②' if i == 0 else '②ب (بديل)'} الطريق: {p['ar']}  [{p['id']}]  ثقة {trust(p['id'], outcomes()):.0%}")
        if i:
            continue
        for n, st in enumerate(here_steps(p, where), 1):
            P(f"   {n}. {st}")
        if p.get("skills"):
            P("   مهارات تتحمّل الأول: " + "، ".join(p["skills"]))
        if p.get("ask"):
            P("   🔒 محتاج «أيوه» صريحة: " + " · ".join(p["ask"]))
        if p.get("gates"):
            P("   ✅ مايتسلّمش غير لما: " + " · ".join(p["gates"]))
        if p.get("pitfalls"):
            P("   ⚠ فخاخ معروفة: " + " · ".join(p["pitfalls"]))
    if pw:
        P("\n③ القدرات والاتصالات الأقرب:")
        for s, p in pw:
            how = p.get("how", "")
            if p.get("where") == "pc" and not is_pc(where):
                how = "هنا: " + p.get("cloud_alt", "مش متاح في السحابة")
            P(f"   • {COST.get(p.get('cost'), '')} {p.get('ar')} [{p['id']}] — {how[:230]}")
    ih = inst_find(q, 4)
    if ih:
        P("\n③ب مهارات متثبتة على الجهاز تفيد (حمّلها بأداة Skill أو اقرا SKILL.md):")
        for r in ih:
            P("   • " + inst_line(r))
    lb = lib_find(q, 4)
    if lb:
        P("\n③ج من مكتبة المهارات (مش متثبتة؛ اقرا SKILL.md بـ Read واستخدمها كمرجع):")
        for r in lb:
            P("   • " + lib_line(r))
    if ls:
        P("\n④ دروس اتعلمناها في حاجة شبه دي:")
        for l in ls:
            P(f"   • ({l.get('domain')}) {l['text'][:260]}")
            bump(l["id"])
    hits = chat_hits(q, 2)
    if hits:
        P("\n④ب من ذاكرة المحادثات (اتعمل قبل كده؟ اتقرر إيه؟ — التفاصيل: rd.py chats):")
        for h in hits:
            P(f"   • {h['title'][:70]} ({h['date'][:10]}, {h['id']})")
            for ln in h["lines"][:2]:
                P(f"       {ln[:220]}")
    P("\n⚑ لو هتكتب في مجلد مشترك أو مهارة متثبتة: rd.py guard PATH الأول (جلستين على نفس المجلد حصلت 5 مرات).")
    P("\n⑤ بعد التسليم: rd.py outcome " + (pb[0][1]["id"] if pb else "ID") + " ok|fail --note \"…\"  ، وأي تصحيح من صاحب الشغل: rd.py learn \"…\"")


def chats_mod():
    """scripts/rd_chats.py (memory of past conversations + guard). Imported by path so python -I works too."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import rd_chats
    return rd_chats


def chat_hits(q, limit=2):
    try:
        return chats_mod().search(q, limit=limit, per=2, min_terms=2)
    except Exception:
        return []


def bump(lid):
    try:
        with mem_file("hits.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"id": lid, "t": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
    except OSError:
        pass


# ------------------------------------------------------------------ skill library (200 famous Claude skills, not auto-loaded)
LIBRARY = ROOT / "library"
_lib = {}


def library():
    if "rows" not in _lib:
        d = jload(LIBRARY / "index.json", {}) or {}
        rows = d.get("skills", [])
        for r in rows:
            r["_tok"] = set(tokens(r["name"].replace("-", " ") + " " + r.get("title", "") + " " + r["description"]))
        _lib["rows"] = rows
    return _lib["rows"]


LIB_AR = {"مونتاج": "video edit editing montage cut", "فيديو": "video", "ترجمه": "subtitle caption translate", "صوت": "audio voice sound", "موشن": "motion animation", "انيميشن": "animation",
          "تصميم": "design ui", "واجهه": "ui frontend interface", "موقع": "website web frontend", "بلندر": "blender 3d", "تسويق": "marketing", "انستجرام": "instagram", "يوتيوب": "youtube",
          "لينكدان": "linkedin", "تداول": "trading stock market", "اسهم": "stock equity trading", "برومبت": "prompt", "كتاب": "book", "اختبار": "test testing", "مراجعه": "review audit",
          "امان": "security audit", "قاعده": "database sql", "بيانات": "data database", "سيارات": "automotive vehicle", "سياره": "automotive vehicle", "اندرويد": "android", "متصفح": "browser",
          "خطه": "plan planning", "تخطيط": "plan planning", "كود": "code coding", "برمجه": "code programming", "مستند": "document docs", "عرض": "presentation slides", "رسم": "draw drawing sketch",
          "بيكسل": "pixel", "العاب": "game sprite", "لعبه": "game sprite", "شركه": "business startup founder", "مشروع": "business startup project", "كتابه": "writing copy", "محتوى": "content", "هندسه": "engineering reverse",
          "ظل": "shadow silhouette", "ظلال": "shadow silhouette", "دمي": "puppet puppetry", "دميه": "puppet puppetry", "عرائس": "puppet marionette puppetry",
          "مسافه": "distance measure", "مسافات": "distance measure", "رياضه": "math geometry", "رياضيه": "math geometry", "نسب": "proportion anthropometry",
          "زاويه": "angle geometry", "منظور": "perspective camera", "فيزيا": "physics", "فيزياء": "physics", "قياس": "measure", "روتوسكوب": "rotoscope trace", "شخصيه": "character", "كرتون": "cartoon character", "تتبع": "tracking"}


def lib_find(q, limit=8):
    """Arabic words map to the English the skill descriptions are written in."""
    qt = tokens(q)
    extra = []
    for t in qt:
        for k, v in LIB_AR.items():
            if match(t, norm(k)):
                extra += v.split()
    qt = qt + extra
    out = [(score(qt, r["_tok"]) + min(r["stars"], 50000) / 50000, r) for r in library()]
    return [r for sc, r in sorted(out, key=lambda x: -x[0]) if sc >= 2][:limit]


# ------------------------------------------------------------------ top 500 GitHub repositories (index only: nothing is cloned)
_top = {}
WIN_AR = {"yes": "يشتغل على ويندوز", "docker": "محتاج Docker", "wsl": "محتاج WSL", "no": "مش لويندوز", "n/a": "مرجع للقراية"}


def repos_top():
    if "rows" not in _top:
        d = jload(MIND / "intel" / "top500.json", {}) or {}
        rows = d.get("repos", [])
        for r in rows:
            r["_tok"] = set(tokens(r["repo"].replace("/", " ").replace("-", " ") + " " + r.get("what", "") + " " + r.get("use_when", "") + " " + r.get("category", "").replace("-", " ")
                                   + " " + " ".join(r.get("keywords_en", [])) + " " + " ".join(r.get("keywords_ar", []))))
        _top["rows"] = rows
    return _top["rows"]


def repos_find(q, limit=8):
    qt = tokens(q)
    extra = []
    for t in qt:
        for k, v in LIB_AR.items():
            if match(t, norm(k)):
                extra += v.split()
    qt = qt + extra
    out = [(score(qt, r["_tok"]) + r.get("value_for_claude", 0) * 0.15 + min(r["stars"], 300000) / 600000, r) for r in repos_top()]
    return [r for sc, r in sorted(out, key=lambda x: -x[0]) if sc >= 2][:limit]


def repo_line(r):
    w = WIN_AR.get(str(r.get("windows_ok")), str(r.get("windows_ok")))
    inst = r.get("install_windows") or ""
    return (f"#{r['rank']} {r['repo']}  ★{r['stars']:,}  ({r.get('category')}، {r.get('license') or 'رخصة مش معروفة'}، {w})\n     {r.get('what', '')[:200]}\n     إمتى: {r.get('use_when', '')[:170]}"
            + (f"\n     التثبيت (بموافقة): {inst[:150]}" if inst and inst != "n/a" else "") + f"\n     {r.get('url', '')}")


def lib_line(r):
    flag = (" · ⚠ راجع قبل تشغيل سكربتاته: " + "، ".join(r["review"])) if r.get("review") else ""
    return f"{r['name']}  ★{r['stars']:,}  ({r['repo']}، {r['license']}){flag}\n     {r['description'][:210]}\n     اقرا: {LIBRARY / r['name'] / 'SKILL.md'}"


def lib_install(name, yes=False):
    r = next((x for x in library() if x["name"] == name), None)
    if not r:
        raise SystemExit(f"مفيش مهارة بالاسم ده في المكتبة: {name}")
    dst = Path.home() / ".claude" / "skills" / name
    if dst.exists():
        raise SystemExit(f"موجودة قبل كده: {dst}")
    if not yes:
        print(f"هيتنسخ: {LIBRARY / name}  →  {dst}\nالمصدر: {r['repo']} (★{r['stars']:,}، {r['license']})" + (f"\n⚠ فيها سكربتات بأنماط: {', '.join(r['review'])} — اقراها الأول." if r.get("review") else "")
              + "\nده تثبيت: محتاج موافقة صاحب الشغل، وبعدها نفس الأمر بـ --yes")
        return None
    shutil.copytree(LIBRARY / name, dst)
    (dst / ".blackdragon.json").write_text(json.dumps({"made_by": "black-dragon-app", "source": f"https://github.com/{r['repo']} ({r['license']})", "mode": "library",
                                                       "created": datetime.datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
    return dst


# ------------------------------------------------------------------ installed skills (every SKILL.md under ~/.claude/skills)
SKILLS_HOME = Path(os.environ.get("CLAUDE_SKILLS_HOME") or Path.home() / ".claude" / "skills")
_inst = {}


def _frontmatter(path):
    """name and description from a SKILL.md's YAML front matter (plain, quoted, or a folded > / | block)."""
    try:
        txt = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not txt.startswith("---"):
        return {}
    end = txt.find("\n---", 3)
    lines = txt[3:end if end > 0 else 4000].splitlines()
    out, i = {}, 0
    while i < len(lines):
        m = re.match(r"^(name|description):\s*(.*)$", lines[i])
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val in (">", "|", ">-", "|-", ""):
                buf = []
                while i + 1 < len(lines) and (lines[i + 1].startswith((" ", "\t")) or not lines[i + 1].strip()):
                    i += 1
                    buf.append(lines[i].strip())
                val = " ".join(b for b in buf if b)
            out[key] = val.strip().strip('"').strip("'")
        i += 1
    return out


def installed():
    """Every installed skill: name, description, mode ("own", or "library" when the app installed it from the library),
    path. Cached in ~/.red-dragon/installed_index.json on the folder's mtime and count, so a chat does not re-read 500 files."""
    try:
        st = SKILLS_HOME.stat()
        dirs = sorted(d.name for d in SKILLS_HOME.iterdir() if (d / "SKILL.md").is_file())
    except OSError:
        return []
    sig = f"{st.st_mtime_ns}:{len(dirs)}"
    if _inst.get("sig") == sig:
        return _inst["rows"]
    cache = MEM / "installed_index.json"
    d = jload(cache, {}) or {}
    if d.get("sig") == sig:
        rows = d["rows"]
    else:
        rows = []
        for name in dirs:
            fm = _frontmatter(SKILLS_HOME / name / "SKILL.md")
            mk = jload(SKILLS_HOME / name / ".blackdragon.json", {}) or {}
            rows.append({"name": fm.get("name") or name, "dir": name, "description": (fm.get("description") or "")[:700],
                         "mode": mk.get("mode", "own"), "path": str(SKILLS_HOME / name / "SKILL.md")})
        try:
            MEM.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"sig": sig, "rows": rows}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    for r in rows:
        r["_tok"] = set(tokens(r["name"].replace("-", " ").replace(":", " ") + " " + r["description"]))
    _inst.update(sig=sig, rows=rows)
    return rows


def inst_find(q, limit=8, mode=None):
    """Installed skills for a request (Arabic words widened to the English the descriptions use); own skills win ties."""
    qt = tokens(q)
    extra = []
    for t in qt:
        for k, v in LIB_AR.items():
            if match(t, norm(k)):
                extra += v.split()
    qt = qt + extra
    out = [(score(qt, r["_tok"]) + (0.5 if r["mode"] == "own" else 0.0), r) for r in installed() if mode in (None, r["mode"])]
    return [r for sc, r in sorted(out, key=lambda x: -x[0]) if sc >= 2.5][:limit]


def inst_line(r):
    tag = "مهارتك" if r["mode"] == "own" else "من المكتبة، متثبتة"
    return f"{r['name']}  ({tag})\n     {r['description'][:200]}\n     {r['path']}"


# ------------------------------------------------------------------ understand: what did the owner actually type
# Arabic typed while the keyboard was on English (Arabic 101 layout). Seen 9 times in the owner's chats.
LAYOUT = dict(zip("qwertyuiop[]asdfghjkl;'zxcvnm,./`", "ضصثقفغعهخحجدشسيبلاتنمكطئءؤرىةوزظذ"))
LAYOUT["b"] = "لا"
DICTATION = jload(MIND / "dictation.json", {}) or {}


def _garbled(run):
    """A run of Latin tokens that is not English: keys like ; ' , inside words, or almost no vowels."""
    toks = run.split()
    letters = [c for c in run.lower() if c.isalpha()]
    if len(letters) < 5 or re.search(r"https?://|[\\/]\w+[\\/]|\.\w{2,4}\b|--\w|^\s*(pip|npm|npx|git|cd|python|curl)\b", run):
        return False
    odd = sum(1 for t in toks if re.search(r"[A-Za-z][;',\[\]`][A-Za-z]|[;'\[\]`]$|^[;',\[\]`]", t))
    vowels = sum(1 for c in letters if c in "aeiou") / len(letters)
    known = sum(1 for t in toks if t.lower().strip(".,") in ENGLISH)
    if known >= max(1, len(toks) // 2):
        return False
    return odd >= max(1, len(toks) // 4) or (vowels < 0.24 and len(toks) >= 2)


ENGLISH = set("the a an and or to of in on for with is are it this that you me my i we be do not no yes can will have has from at by as if so but ok okay please make create build run test install update fix "
              "open file files app video image skill skills dragon black white red claude code github repo link download upload render blender chrome windows".split())


def fix_layout(text):
    """Decode every garbled Latin run; leave real English, paths, links and commands alone."""
    changed = False

    def rep(m):
        nonlocal changed
        run = m.group(0)
        if not _garbled(run):
            return run
        changed = True
        return "".join(LAYOUT.get(c, c) for c in run.lower())
    out = re.sub(r"[A-Za-z;',\.\[\]`/]+(?:\s+[A-Za-z;',\.\[\]`/]+)*", rep, text)
    return out, changed


def fix_dictation(text):
    """Known voice-typing slips -> the intended word (mind/dictation.json)."""
    hits = []
    for bad, good in DICTATION.items():
        if re.search(r"(?<![؀-ۿ])" + re.escape(bad) + r"(?![؀-ۿ])", text):
            text = re.sub(r"(?<![؀-ۿ])" + re.escape(bad) + r"(?![؀-ۿ])", good, text)
            hits.append(f"{bad}→{good}")
    return text, hits


def understand(text):
    t1, lay = fix_layout(" ".join(str(text).split()))
    t2, hits = fix_dictation(t1)
    return {"text": t2, "layout_fixed": lay, "words_fixed": hits, "changed": lay or bool(hits)}


def brief(text, limit=1400):
    """A short mission brief for a host app to put in front of the model. Pure function, no I/O beyond the mind files."""
    u = understand(text)
    pb, pw = route(u["text"])
    where = place()
    L = []
    if u["changed"]:
        L.append("الطلب بعد فك الكتابة: «" + u["text"][:300] + "»" + (" (كان مكتوب والكيبورد إنجليزي)" if u["layout_fixed"] else "") + (" · تصحيح: " + "، ".join(u["words_fixed"]) if u["words_fixed"] else ""))
    if pb and pb[0][0] >= 2:
        p = pb[0][1]
        L.append(f"الطريق المقترح: {p['ar']} [{p['id']}]")
        L += [f" {n}. {s}" for n, s in enumerate(here_steps(p, where)[:6], 1)]
        if p.get("skills"):
            L.append(" مهارات: " + "، ".join(p["skills"][:5]))
        if p.get("ask"):
            L.append(" 🔒 بموافقة: " + " · ".join(p["ask"]))
        if p.get("gates"):
            L.append(" ✅ قبل التسليم: " + " · ".join(p["gates"][:4]))
    tr = repos_find(u["text"], 2)
    if tr:
        L.append("من أشهر 500 مستودع GitHub (فهرس بس، مفيش حاجة متنزّلة): " + " ⏐ ".join(f"{r['repo']} ★{r['stars']:,} ({WIN_AR.get(str(r.get('windows_ok')), '')})" for r in tr))
    ih = inst_find(u["text"], 3)
    if ih:
        L.append("مهارات متثبتة تفيد (حمّلها بأداة Skill): " + " ⏐ ".join(r["name"] for r in ih))
    lb = lib_find(u["text"], 2)
    if lb:
        L.append("من مكتبة المهارات (مش متثبتة، اقرا SKILL.md بتاعها لو هتفيد): " + " ⏐ ".join(f"{r['name']} ★{r['stars']:,} → {LIBRARY / r['name'] / 'SKILL.md'}" for r in lb))
    ls = recall(u["text"], 3, pb[0][1].get("domain") if pb else None, minscore=4)
    if ls:
        L.append("دروس سابقة: " + " ⏐ ".join(l["text"][:170] for l in ls))
    out = "\n".join(L)[:limit + 500]
    return {"understood": u, "playbook": pb[0][1]["id"] if pb and pb[0][0] >= 2 else None, "library": [r["name"] for r in lb], "installed": [r["name"] for r in ih], "brief": out}


# ------------------------------------------------------------------ re: what is this target
MAGIC = [(b"MZ", "pe"), (b"\x7fELF", "elf"), (b"PK\x03\x04", "zip"), (b"%PDF", "pdf"), (b"\x00asm", "wasm"), (b"SQLite format 3", "sqlite"),
         (b"\xca\xfe\xba\xbe", "macho/java-class"), (b"\xcf\xfa\xed\xfe", "macho"), (b"dex\n", "dex"), (b"\xd0\xcf\x11\xe0", "ole-office"),
         (b"GGUF", "gguf-model"), (b"\x89PNG", "png"), (b"\xff\xd8\xff", "jpeg"), (b"Rar!", "rar"), (b"7z\xbc\xaf", "7z"),
         (b"\xd4\xc3\xb2\xa1", "pcap"), (b"\x0a\x0d\x0d\x0a", "pcapng"), (b"\x1f\x8b", "gzip"), (b"ftyp", "mp4@4")]


def classify(path):
    p = Path(path)
    if re.match(r"https?://", str(path)):
        u = str(path)
        return "repo-url" if re.search(r"github\.com/[^/]+/[^/]+", u) else "site-url"
    if p.is_dir():
        if (p / ".git").exists() or any((p / f).exists() for f in ("package.json", "pyproject.toml", "setup.py", "Cargo.toml", "go.mod")):
            return "repo"
        return "skill-package" if (p / "SKILL.md").exists() else "folder"
    if not p.is_file():
        return "missing"
    head = p.read_bytes()[:4096]
    kind = next((k for m, k in MAGIC if head.startswith(m) or (k == "mp4@4" and head[4:8] == m)), None)
    if kind == "pe":
        blob = p.read_bytes()[:40_000_000]
        if b"_MEIPASS" in blob or b"PyInstaller" in blob or b"pyi-runtime" in blob:
            return "pe/pyinstaller"
        if b"mscoree.dll" in blob or b"_CorExeMain" in blob:
            return "pe/dotnet"
        if b"app.asar" in blob or b"Electron" in blob[:2_000_000]:
            return "pe/electron"
        if b"UPX!" in blob[:4000]:
            return "pe/upx"
        return "pe/native"
    if kind == "zip":
        import zipfile
        try:
            names = zipfile.ZipFile(p).namelist()
        except Exception:
            return "zip"
        if "AndroidManifest.xml" in names:
            return "apk"
        if any(n.endswith("SKILL.md") for n in names):
            return "skill-package"
        if any(n.startswith("word/") or n.startswith("xl/") or n.startswith("ppt/") for n in names):
            return "office-ooxml"
        if any(n.endswith(".asar") for n in names):
            return "electron-bundle"
        return "jar" if "META-INF/MANIFEST.MF" in names else "zip"
    if kind == "mp4@4":
        return "media"
    if kind:
        return kind
    ext = p.suffix.lower()
    return {".js": "javascript", ".mjs": "javascript", ".py": "python", ".pyc": "pyc", ".asar": "electron-bundle", ".har": "har",
            ".blend": "blender", ".psd": "psd", ".aep": "after-effects", ".prproj": "premiere"}.get(ext, "unknown")


def re_cmd(target):
    kind = classify(target)
    roads = jload(MIND / "re_roads.json", {})
    key = kind if kind in roads else kind.split("/")[0]
    road = roads.get(key) or roads.get("unknown", {})
    print(f"🔬 الهدف: {target}\n   النوع (من البايتات مش من الامتداد): {kind}")
    if Path(str(target)).is_file():
        b = Path(target).read_bytes()
        print(f"   الحجم: {len(b):,} بايت · sha256: {hashlib.sha256(b).hexdigest()}")
    w = place()
    print(f"   المكان: {w}\n")
    for n, st in enumerate(here_steps(road, w), 1):
        print(f"   {n}. {st.replace('{T}', str(target))}")
    for k, lab in (("ask", "🔒 بموافقة صريحة"), ("proof", "✅ الدليل المطلوب"), ("limits", "⛔ الحدود")):
        if road.get(k):
            print(f"   {lab}: " + " · ".join(road[k]))
    print("\n   التقرير دايمًا تلات خانات: «اتأكد بدليل» / «استنتاج» / «مجهول». مرجع: references/RD_RE.md")


# ------------------------------------------------------------------ repo dossier (read-only static scan)
LANG = {".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".jsx": "JavaScript", ".go": "Go",
        ".rs": "Rust", ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".java": "Java", ".kt": "Kotlin", ".swift": "Swift", ".sh": "Shell",
        ".ps1": "PowerShell", ".html": "HTML", ".css": "CSS", ".glsl": "GLSL", ".md": "Markdown", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
        ".toml": "TOML", ".ipynb": "Notebook", ".vue": "Vue", ".svelte": "Svelte", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".lua": "Lua"}
SKIPD = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "target", ".cache", "vendor", ".idea", ".vscode"}
RISK = {"network": r"\b(requests\.(get|post)|urllib\.request|fetch\(|axios\.|http\.client|socket\.socket|XMLHttpRequest|aiohttp|httpx\.)",
        "exec": r"\b(subprocess\.|os\.system\(|child_process|execSync|spawn\(|Popen\(|ShellExecute|eval\(|exec\()",
        "download-run": r"(curl[^\n|]*\|\s*(ba)?sh|iwr[^\n|]*\|\s*iex|Invoke-Expression|wget[^\n|]*\|\s*sh)",
        "secrets-read": r"(\.aws/credentials|id_rsa|\.npmrc|keychain|credential|ANTHROPIC_API_KEY|OPENAI_API_KEY|GITHUB_TOKEN)",
        "delete": r"\b(shutil\.rmtree|rm -rf|Remove-Item[^\n]*-Recurse|fs\.rm(Sync)?\(|unlinkSync)",
        "telemetry": r"(posthog|sentry|segment\.io|mixpanel|amplitude|google-analytics|telemetry)"}
CODE = {".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".sh", ".ps1", ".go", ".rs", ".rb", ".php"}


def repo_scan(path, max_files=6000):
    root = Path(path)
    langs, files, total, risk = {}, 0, 0, {k: [] for k in RISK}
    skills, entry, big = [], [], []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIPD]
        if files >= max_files:                 # huge trees (ghidra, sam2): stop walking, the dossier says it was capped
            dn[:] = []
            continue
        for name in fn:
            if files >= max_files:
                break
            f = Path(dp) / name
            try:
                size = f.stat().st_size
            except OSError:
                continue
            files += 1
            total += size
            rel = f.relative_to(root).as_posix()
            ext = f.suffix.lower()
            if ext in LANG:
                langs[LANG[ext]] = langs.get(LANG[ext], 0) + size
            if name == "SKILL.md":
                skills.append(rel)
            if name in ("main.py", "cli.py", "__main__.py", "index.js", "index.ts", "main.go", "main.rs", "server.py", "app.py") and rel.count("/") <= 2:
                entry.append(rel)
            if size > 5_000_000:
                big.append(f"{rel} ({size / 1e6:.0f} MB)")
            if ext in CODE and size < 400_000:
                try:
                    txt = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for k, rx in RISK.items():
                    if len(risk[k]) < 6 and re.search(rx, txt):
                        risk[k].append(rel)
    def rd(n, lim=200_000):
        f = root / n
        return f.read_text(encoding="utf-8", errors="ignore")[:lim] if f.is_file() else ""
    readme = next((rd(n) for n in ("README.md", "readme.md", "README.rst", "README", "README_EN.md") if (root / n).is_file()), "")
    lic = next((n for n in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "LICENCE") if (root / n).is_file()), "")
    lic_kind = ""
    if lic:
        t = rd(lic, 3000)
        lic_kind = next((k for k, pat in (("MIT", "MIT License|Permission is hereby granted, free of charge"), ("Apache-2.0", "Apache License"), ("GPL-3.0", "GNU GENERAL PUBLIC LICENSE\\s+Version 3"),
                                          ("AGPL-3.0", "AFFERO GENERAL PUBLIC"), ("GPL-2.0", "GNU GENERAL PUBLIC LICENSE\\s+Version 2"), ("BSD", "Redistribution and use in source and binary forms"),
                                          ("LGPL", "LESSER GENERAL PUBLIC"), ("MPL-2.0", "Mozilla Public License"), ("CC", "Creative Commons"), ("Unlicense", "This is free and unencumbered")) if re.search(pat, t)), "other")
    pkg = jload(root / "package.json", {}) or {}
    deps = sorted(set(list((pkg.get("dependencies") or {})) + list((pkg.get("devDependencies") or {}))))
    pyd = []
    for ln in rd("requirements.txt", 20000).splitlines():
        m = re.match(r"\s*([A-Za-z0-9_.\-]+)\s*(?:[=<>~!\[;@]|$)", ln)
        if m and not ln.lstrip().startswith(("#", "-")):
            pyd.append(m.group(1))
    for blk in re.findall(r"(?s)\bdependencies\s*=\s*\[(.*?)\]", rd("pyproject.toml", 40000)):   # only the dependency arrays, not the TOML keys
        pyd += [m.group(1) for m in re.finditer(r"[\"']\s*([A-Za-z0-9_.\-]+)", blk)]
    title = next((ln.lstrip("# ").strip() for ln in readme.splitlines() if ln.startswith("#")), root.name)
    para = next((" ".join(b.split()) for b in re.split(r"\n\s*\n", readme) if len(b.strip()) > 60 and not b.lstrip().startswith(("#", "!", "<", "[", "|", "```"))), "")
    install = sorted(set(m.group(0).strip()[:110] for m in re.finditer(r"(?m)^\s*(pip install|npm (?:install|i)\b|npx |uv (?:pip|tool|add)|cargo install|brew install|winget install|git clone|docker (?:run|compose))[^\n]*", readme)))[:8]
    head = ""
    try:
        h = (root / ".git" / "HEAD").read_text().strip()
        head = (root / ".git" / h[5:]).read_text().strip()[:12] if h.startswith("ref: ") and (root / ".git" / h[5:]).is_file() else h[:12]
    except OSError:
        pass
    top = sorted(langs.items(), key=lambda x: -x[1])
    code = [(k, v) for k, v in top if k not in ("Markdown", "JSON", "YAML", "TOML", "HTML", "CSS")]
    return {"name": root.name, "title": title[:120], "what": para[:420], "commit": head, "files": files, "capped": files >= max_files, "mb": round(total / 1e6, 1), "license": lic_kind or "none found",
            "languages": [f"{k} {v * 100 // max(1, sum(x[1] for x in top))}%" for k, v in top[:5]], "main_language": code[0][0] if code else (top[0][0] if top else "-"),
            "entry": entry[:8], "scripts": list((pkg.get("scripts") or {}))[:10], "bin": pkg.get("bin") if isinstance(pkg.get("bin"), (dict, str)) else None,
            "deps_js": deps[:25], "deps_py": sorted(set(pyd))[:25], "agent_skills": skills[:20], "install": install,
            "has": {k: (root / v).exists() for k, v in (("docker", "Dockerfile"), ("tests", "tests"), ("ci", ".github/workflows"), ("claude", "CLAUDE.md"), ("agents", "AGENTS.md"), ("mcp", ".mcp.json"))},
            "risk": {k: v for k, v in risk.items() if v}, "big_files": big[:6],
            "windows": "docker/WSL غالبًا" if (root / "Dockerfile").exists() and not any(l in dict(top) for l in ("Python", "JavaScript", "TypeScript")) else "يشتغل مباشرة غالبًا (Python/Node)" if code else "-"}


def repo_md(d):
    L = [f"### {d['name']} — {d['title']}", f"- **إيه ده:** {d['what'] or '(الـ README مافيهوش فقرة وصف واضحة)'}",
         f"- **حقائق مقاسة:** {d['files']}{'+ (الفحص وقف عند الحد)' if d.get('capped') else ''} ملف · {d['mb']} MB · الرخصة: {d['license']} · commit `{d['commit'] or '?'}` · اللغات: {'، '.join(d['languages'])}"]
    if d["entry"] or d["scripts"]:
        L.append(f"- **نقط الدخول:** {'، '.join('`' + e + '`' for e in d['entry']) or '—'}" + (f" · npm scripts: {'، '.join(d['scripts'])}" if d["scripts"] else ""))
    if d["agent_skills"]:
        L.append(f"- **مهارات Claude جواه ({len(d['agent_skills'])}):** " + "، ".join("`" + s + "`" for s in d["agent_skills"][:8]))
    if d["install"]:
        L.append("- **التثبيت من الـ README (بموافقة):** " + " ⏐ ".join("`" + i + "`" for i in d["install"][:4]))
    if d["deps_py"] or d["deps_js"]:
        L.append(f"- **اعتماديات:** {'، '.join((d['deps_py'] + d['deps_js'])[:14])}")
    if d["risk"]:
        L.append("- **قبل التشغيل راجع:** " + " · ".join(f"{k} ({len(v)} ملف، مثلًا `{v[0]}`)" for k, v in d["risk"].items()))
    L.append(f"- **على ويندوز:** {d['windows']} · " + "، ".join(k for k, v in d["has"].items() if v))
    return "\n".join(L)


# ------------------------------------------------------------------ doctor
def doctor():
    w = place()
    print(f"🐉 Red Dragon v{VERSION} · place={w} · python {sys.version.split()[0]} · root={ROOT}")
    ok = lambda b: "✓" if b else "✗"
    print(f" {ok((ENGINE / 'scripts' / 'dragon.py').is_file())} المحرك engine/scripts/dragon.py")
    print(f" {ok(len(playbooks()) > 0)} playbooks: {len(playbooks())} · قدرات واتصالات: {len(powers())} · دروس: {len(lessons())} · مستودعات متحلّلة: {len(jload(MIND / 'intel' / 'repos.json', []) or [])}")
    nch = len(list((MIND / "chats").glob("[cst]*.md")))
    try:
        fresh = chats_mod().banner()
    except Exception as e:
        fresh = f"rd_chats: {e}"
    print(f" {ok(nch > 0)} {fresh} · mind/chats_index.json · references/RD_CHATS_MEMORY.md")
    for b in ("ffmpeg", "ffprobe", "python3" if os.name != "nt" else "python", "node", "git", "blender", "yt-dlp", "claude", "rea", "magick", "7z"):
        print(f" {ok(shutil.which(b))} {b}" + (f"  → {shutil.which(b)}" if shutil.which(b) else ""))
    if w == "pc-owner":
        H = Path.home()
        for lab, p in (("تطبيق التنين (مصدر)", H / "OneDrive/Desktop/التنين الأسود/apps/dragon_desktop/app.py"), ("التطبيق المتثبت", Path(os.environ.get("LOCALAPPDATA", "")) / "BlackDragon"),
                       ("صندوق الهندسة العكسية retool", H / "re-tools/retool.py"), ("مستودعات المونتاج", H / "dragon-repos"), ("مهارات Claude", H / ".claude/skills"),
                       ("KOSIF hub", H / "kosif-tool/.claude/skills/kosif-superpowers/scripts/hub.py"), ("ذاكرة التنين الأحمر", MEM)):
            print(f" {ok(p.exists())} {lab}  → {p}")
    print("\n للتفاصيل الكاملة على اللابتوب: rd.py x tool powers doctor --mcp   (بيفحص MCP والبرامج والمهارات)")
    print(" اتصالات الجلسة (MCP، كروم، وكلاء) مابتتشافش من بايثون: اتأكد منها بـ ToolSearch، والقايمة في references/RD_CONNECTIONS.md")


# ------------------------------------------------------------------ docs (generated references)
def docs():
    R = ROOT / "references"
    R.mkdir(exist_ok=True)
    L = [f"# Playbooks التنين الأحمر — v{VERSION}", "", "متولّد من `mind/playbooks.json` بأمر `rd.py docs`. عدّل الـ JSON وولّد تاني.", "",
         "`$R` = `python scripts/rd.py` · `$E` = `python engine/scripts/dragon.py` · [pc] = على اللابتوب بس · [cloud] = في السحابة بس.", ""]
    for p in playbooks():
        L += [f"## {p['ar']} (`{p['id']}`)", f"*{p.get('en', '')}* · المجال: {p.get('domain', '')}", ""]
        L += [f"{n}. {s}" for n, s in enumerate(p.get("steps", []), 1)]
        for k, lab in (("skills", "مهارات"), ("ask", "🔒 بموافقة"), ("gates", "✅ بوابة التسليم"), ("pitfalls", "⚠ فخاخ")):
            if p.get(k):
                L.append(f"- **{lab}:** " + " · ".join(p[k]))
        L.append("")
    (R / "RD_PLAYBOOKS.md").write_text("\n".join(L), encoding="utf-8")
    C = jload(MIND / "connections.json", {})
    L = [f"# اتصالات التنين الأحمر — v{VERSION}", "", C.get("_doc_ar", ""), ""]
    for p in C.get("powers", []):
        L += [f"## {p['ar']} (`{p['id']}`) — {COST.get(p.get('cost'), '')} · {p.get('where')}", f"- **إزاي تتأكد إنه موجود:** {p.get('detect', '—')}", f"- **إزاي تستخدمه:** {p.get('how', '')}"]
        if p.get("tools"):
            L.append(f"- **الأدوات بالاسم:** {p['tools']}")
        L += [f"- **لو مش موجود:** {p.get('cloud_alt', '—')}", ""]
    L += ["## باقي القدرات (50 قدرة من سجل المحرك)", "`references/ENGINE_POWERS.md` (نسخة من `engine/references/ALL_POWERS_*.md`) أو `$R map`.", ""]
    (R / "RD_CONNECTIONS.md").write_text("\n".join(L), encoding="utf-8")
    rd = jload(MIND / "re_roads.json", {})
    L = [f"# طرق الهندسة العكسية حسب نوع الهدف — v{VERSION}", "", "متولّد من `mind/re_roads.json`. `{T}` = الهدف. الأمر: `$R re TARGET`.", ""]
    for k, r in rd.items():
        L += [f"## {k} — {r.get('ar', '')}"] + [f"{n}. {s}" for n, s in enumerate(r.get("steps", []), 1)]
        for kk, lab in (("ask", "🔒 بموافقة"), ("proof", "✅ الدليل"), ("limits", "⛔ الحدود")):
            if r.get(kk):
                L.append(f"- **{lab}:** " + " · ".join(r[kk]))
        L.append("")
    (R / "RD_RE_ROADS.md").write_text("\n".join(L), encoding="utf-8")
    if repos_top():
        L = [f"# أشهر {len(repos_top())} مستودع على GitHub — فهرس التنين الأحمر", "",
             "المصدر: أطلس GitHub اللي على اللابتوب (بحث GitHub بالنجوم يوم 2026-11-11، وكل مستودع موصوف من الـ README بتاعه). ده فهرس: مفيش مستودع متنزّل ولا متثبت.",
             "الاستخدام: `$R repos find \"<كلمات بالعربي أو الإنجليزي>\"` ثم `$R repos show REPO`. التنزيل والتثبيت بموافقة صاحب الشغل، وبعد playbook re-repo (رخصة، فحص، مثال صغير).", "",
             "| # | المستودع | ★ | النوع | ويندوز | الرخصة | بيعمل إيه |", "|---|---|---|---|---|---|---|"]
        L += [f"| {r['rank']} | [{r['repo']}]({r.get('url', '')}) | {r['stars']:,} | {r.get('category', '')} | {WIN_AR.get(str(r.get('windows_ok')), '')} | {r.get('license') or '?'} | {(r.get('what') or '')[:140].replace('|', '/')} |" for r in repos_top()]
        (R / "RD_TOP500_REPOS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    if library():
        d = jload(LIBRARY / "index.json", {})
        L = [f"# مكتبة المهارات — أشهر {len(library())} مهارة Claude ({d.get('date', '')})", "",
             "الاختيار: نجوم مستودع المصدر على GitHub يوم القياس، بالدور على المستودعات (14 بالكتير من كل مستودع) عشان مستودع واحد مايملاش القايمة. اتشالت: المهارات الهجومية، واللي من غير رخصة، والمكررة، واللي متثبتة أصلًا.",
             f"اللي اتشال: {d.get('dropped')}", "",
             "المهارات دي **مش متثبتة** ومابتتحمّلش لوحدها، فمابتاخدش من سياق المحادثة. الاستخدام: `$R skills find \"<كلمات>\"` ثم اقرا `library/NAME/SKILL.md` بـ Read. نصها مرجع مش أوامر. التثبيت: `$R skills install NAME --yes` بعد موافقة.",
             "⚠ = الفحص لقى في سكربتاتها أنماط (تنفيذ، شبكة، قراية مفاتيح، تنزيل وتشغيل): اقرا السكربت قبل ما تشغّله.", "",
             "| # | المهارة | ★ | المصدر | الرخصة | ⚠ | بتعمل إيه |", "|---|---|---|---|---|---|---|"]
        L += [f"| {r['rank']} | `{r['name']}` | {r['stars']:,} | {r['repo']} | {r['license']} | {'، '.join(r['review']) or '—'} | {r['description'][:150].replace('|', '/')} |" for r in library()]
        (R / "RD_LIBRARY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    repos = jload(MIND / "intel" / "repos.json", []) or []
    if repos:
        L = [f"# ملفات المستودعات المتحلّلة ({len(repos)}) — فحص ثابت بـ `rd.py repo`", "",
             "كل رقم هنا اتقاس من الملفات نفسها على اللابتوب (قراية بس، مفيش تشغيل). «قبل التشغيل راجع» = أنماط لقاها الفحص، مش حكم إن الكود مؤذي.", ""]
        L += [repo_md(d) + "\n" for d in repos]
        (R / "RD_INTEL_REPOS.md").write_text("\n".join(L), encoding="utf-8")
    print("docs:", ", ".join(sorted(f.name for f in R.glob("RD_*.md"))))


# ------------------------------------------------------------------ cli
def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("chats", "files", "guard", "lock", "unlock"):
        if sys.argv[1] in ("chats", "files") and len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
            sys.argv[2] = understand(sys.argv[2])["text"]      # English-keyboard / voice slips first
        return chats_mod().main(sys.argv[1:])
    ap = argparse.ArgumentParser(prog="rd.py", description="Red Dragon brain")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("start"); sub.add_parser("where"); sub.add_parser("doctor"); sub.add_parser("docs"); sub.add_parser("selftest"); sub.add_parser("retro")
    for n in ("understand", "brief"):
        s_ = sub.add_parser(n); s_.add_argument("q")
    for n in ("plan", "route", "recall", "intel"):
        s = sub.add_parser(n); s.add_argument("q"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("map"); s.add_argument("--md", action="store_true")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("learn"); s.add_argument("text"); s.add_argument("--domain", default="general"); s.add_argument("--trigger", default=""); s.add_argument("--kind", default="rule")
    s = sub.add_parser("lessons"); s.add_argument("--domain")
    s = sub.add_parser("outcome"); s.add_argument("id"); s.add_argument("result", choices=["ok", "fail"]); s.add_argument("--note", default="")
    s = sub.add_parser("memory"); s.add_argument("action", choices=["export", "import", "stats"]); s.add_argument("file", nargs="?")
    s = sub.add_parser("re"); s.add_argument("target")
    s = sub.add_parser("repo"); s.add_argument("path"); s.add_argument("--json", action="store_true"); s.add_argument("--save", action="store_true")
    s = sub.add_parser("repos"); s.add_argument("action", choices=["find", "list", "show", "stats"]); s.add_argument("q", nargs="?", default=""); s.add_argument("--json", action="store_true")
    s = sub.add_parser("skills"); s.add_argument("action", choices=["find", "list", "show", "install", "stats"]); s.add_argument("q", nargs="?", default=""); s.add_argument("--yes", action="store_true"); s.add_argument("--json", action="store_true"); s.add_argument("--installed", action="store_true")
    s = sub.add_parser("x"); s.add_argument("args", nargs=argparse.REMAINDER)
    s = sub.add_parser("character", help="character memory + auto rotoscope: doctor, demo, extract, analyze, redraw, memory, animate, edit, export"); s.add_argument("args", nargs=argparse.REMAINDER)
    s = sub.add_parser("math", help="drawing maths (draw-math): body, dist, angle, ik2, cam, frame-fit, puppet-shadow, gait, ease ..."); s.add_argument("args", nargs=argparse.REMAINDER)
    s = sub.add_parser("dcm", help="dragon-character-memory v1.0 (second engine): extract, analyze, redraw, memory, rebuild, animate, identity, demo"); s.add_argument("args", nargs=argparse.REMAINDER)
    s = sub.add_parser("desktop", help="guarded BlackDragon desktop bridge: catalog, doctor, read, snapshot"); s.add_argument("args", nargs=argparse.REMAINDER)
    a = ap.parse_args()

    if a.cmd in (None, "start"):
        w = place()
        print(f"🐉 التنين الأحمر v{VERSION} — عقل فوق محرك التنين الأسود ({len(playbooks())} playbook · {len(powers())} قدرة واتصال · {len(lessons())} درس)")
        try:
            print(chats_mod().banner() + ' · سؤال عن حاجة اتعملت قبل كده: rd.py chats "…" / files "…" · قبل الكتابة في مجلد مشترك: rd.py guard PATH')
        except Exception:
            pass
        print(f"المكان اللي اتعرف لوحده: {w}")
        if w == "pc-owner":
            print("ده لابتوب صاحب التنين: كل الاتصالات متاحة. ابدأ بـ: rd.py doctor  ثم  rd.py plan \"<الطلب>\"")
        else:
            print("اسأل صاحب الشغل سؤال واحد: «أنا شغال على لابتوبك ولا في محادثة سحابة؟»")
            print(" • لابتوبه (Claude Code أو تطبيق التنين): اقرا references/RD_CONNECTIONS.md و engine/references/MACHINE_MAP.md وامشي بمسارات [pc].")
            print(" • سحابة: امشي بخطوات [cloud]، واللي محتاج اللابتوب قول عليه بصراحة واقترح البديل (سحابة Higgsfield المجانية لو مربوطة).")
        print("القواعد اللي مابتتكسرش: references/RD_RULES.md · كل الأوامر: rd.py --help")
    elif a.cmd == "where":
        print(json.dumps({"place": place(), "root": str(ROOT), "engine": (ENGINE / "scripts" / "dragon.py").is_file(), "memory": str(MEM), "version": VERSION}, ensure_ascii=False))
    elif a.cmd == "understand":
        print(json.dumps(understand(a.q), ensure_ascii=False, indent=1))
    elif a.cmd == "brief":
        print(json.dumps(brief(a.q), ensure_ascii=False, indent=1))
    elif a.cmd == "plan":
        plan(a.q, a.json)
    elif a.cmd == "route":
        pb, pw = route(understand(a.q)["text"])
        for s, p in pb:
            print(f"playbook {s:5.1f}  {p['id']:<16} {p['ar']}")
        for s, p in pw:
            print(f"power    {s:5.1f}  {p['id']:<16} {COST.get(p.get('cost'), '')} {p.get('ar')}")
    elif a.cmd == "map":
        print("## Playbooks")
        for p in playbooks():
            print(f"- `{p['id']}` {p['ar']}" if a.md else f"  {p['id']:<16} {p['ar']}")
        print("## القدرات والاتصالات")
        for p in powers():
            print(f"- `{p['id']}` {COST.get(p.get('cost'), '')} {p.get('ar')} ({p.get('where')})" if a.md else f"  {p['id']:<18} {COST.get(p.get('cost'), ''):<10} {p.get('where', ''):<5} {p.get('ar')}")
    elif a.cmd == "show":
        hit = next((p for p in playbooks() + powers() if p["id"] == a.id), None)
        if not hit:
            raise SystemExit(f"مفيش id بالاسم ده: {a.id} (شوف rd.py map)")
        print(json.dumps({k: v for k, v in hit.items() if not k.startswith("_")}, ensure_ascii=False, indent=1))
    elif a.cmd == "learn":
        row, again = learn(a.text, a.domain, a.trigger, a.kind)
        print(("الدرس ده اتكرر، وزنه زاد" if again else "اتحفظ") + f": [{row['id']}] ({row['domain']}) seen={row['seen']} → {MEM / 'lessons.jsonl'}")
    elif a.cmd == "recall":
        for l in recall(a.q, 10):
            print(f"[{l['id']}] ({l.get('domain')}, seen {l.get('seen', 1)}) {l['text']}")
        hits = chat_hits(a.q, 2)
        if hits:
            print('\n— من ذاكرة المحادثات (rd.py chats "…" للتفاصيل، rd.py files "…" للمسارات):')
            chats_mod().print_hits(hits)
    elif a.cmd == "lessons":
        for l in sorted(lessons(), key=lambda x: (x.get("domain", ""), -x.get("seen", 1))):
            if not a.domain or l.get("domain") == a.domain:
                print(f"[{l['id']}] ({l.get('domain')}) {l['text']}")
    elif a.cmd == "outcome":
        ids = {p["id"] for p in playbooks()}
        if a.id not in ids:
            raise SystemExit(f"مفيش playbook بالاسم ده: {a.id}")
        with mem_file("outcomes.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"id": a.id, "result": a.result, "note": a.note, "date": datetime.date.today().isoformat()}, ensure_ascii=False) + "\n")
        print(f"اتسجّل: {a.id} = {a.result} · الثقة دلوقتي {trust(a.id, outcomes()):.0%}")
        if a.result == "fail" and a.note:
            row, _ = learn(a.note, next(p for p in playbooks() if p["id"] == a.id).get("domain", "general"), a.id, "failure", "outcome")
            print(f"والسبب اتحفظ كدرس [{row['id']}]")
    elif a.cmd == "retro":
        print("مراجعة بعد المهمة (جاوب في سطر لكل واحدة، وكل إجابة مفيدة = rd.py learn):\n"
              " 1. إيه اللي صاحب الشغل صحّحه أو كرّره؟ (ده أهم درس)\n 2. أنهي خطوة اتعادت أو فشلت، وإيه اللي كان هيمنعها من الأول؟\n"
              " 3. أنهي افتراض طلع غلط؟ كان يتقاس بإيه؟\n 4. إيه اللي اتسلّم من غير دليل؟ (لازم يتقال في التقرير)\n"
              " 5. أنهي أمر أو مسار اشتغل ويستاهل يتحفظ؟\n ثم: rd.py outcome <playbook> ok|fail --note \"…\"")
        oc = outcomes()
        for pid, o in sorted(oc.items(), key=lambda x: trust(x[0], oc)):
            print(f"  {pid:<16} ok {o['ok']} / fail {o['fail']} → ثقة {trust(pid, oc):.0%}")
    elif a.cmd == "memory":
        f = MEM / "lessons.jsonl"
        if a.action == "stats":
            ls = lessons()
            by = {}
            for l in ls:
                by[l.get("domain", "general")] = by.get(l.get("domain", "general"), 0) + 1
            print(json.dumps({"lessons": len(ls), "by_domain": by, "local_file": str(f), "local_exists": f.is_file(), "outcomes": outcomes()}, ensure_ascii=False, indent=1))
        elif a.action == "export":
            out = Path(a.file or "red-dragon-lessons.jsonl")
            out.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lessons()), encoding="utf-8")
            print(f"{len(lessons())} درس → {out}  (حطه مكان mind/lessons_seed.jsonl في الحزمة عشان الدروس تسافر مع الملف لأي محادثة)")
        else:
            if not a.file or not Path(a.file).is_file():
                raise SystemExit("memory import FILE.jsonl")
            n = 0
            for ln in Path(a.file).read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(ln)
                    learn(r["text"], r.get("domain", "general"), r.get("trigger", ""), r.get("kind", "rule"), "import")
                    n += 1
                except (SystemExit, Exception):
                    continue
            print(f"اتستورد {n} درس")
    elif a.cmd == "re":
        re_cmd(a.target)
    elif a.cmd == "repo":
        d = repo_scan(a.path)
        if a.save:
            f = MIND / "intel" / "repos.json"
            f.parent.mkdir(parents=True, exist_ok=True)
            cur = [r for r in (jload(f, []) or []) if r["name"] != d["name"]] + [d]
            f.write_text(json.dumps(sorted(cur, key=lambda r: r["name"].lower()), ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(d, ensure_ascii=False, indent=1) if a.json else repo_md(d))
    elif a.cmd == "intel":
        qt = tokens(a.q)
        rows = []
        for d in jload(MIND / "intel" / "repos.json", []) or []:
            s = score(qt, set(tokens(" ".join([d["name"], d["title"], d["what"], " ".join(d["deps_py"] + d["deps_js"] + d["agent_skills"]), d["main_language"]]))))
            if s:
                rows.append((s, d))
        for s, d in sorted(rows, key=lambda x: -x[0])[:6]:
            print(repo_md(d) + "\n")
        notes = MIND / "intel" / "FINDINGS.md"
        if notes.is_file():
            for blk in re.split(r"\n(?=## )", notes.read_text(encoding="utf-8")):
                if score(qt, set(tokens(blk))) >= 3:
                    print(blk.strip()[:1500] + "\n")
        if not rows:
            print("مفيش مستودع مطابق في mind/intel. للأطلس الأكبر (1000 مستودع): rd.py x tool atlas find \"…\" أو مهارة github-atlas.")
    elif a.cmd == "repos":
        rows = repos_top()
        if a.action == "stats":
            by = {}
            for r in rows:
                by[r.get("category", "")] = by.get(r.get("category", ""), 0) + 1
            print(json.dumps({"repos": len(rows), "windows_yes": sum(1 for r in rows if r.get("windows_ok") == "yes"), "by_category": dict(sorted(by.items(), key=lambda x: -x[1]))}, ensure_ascii=False, indent=1))
        elif a.action == "list":
            for r in rows:
                print(f"{r['rank']:>3}. {r['repo']:<48} ★{r['stars']:>7,}  {r.get('category', '')}")
        elif a.action == "find":
            hits = repos_find(a.q, 10)
            if a.json:
                print(json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in hits], ensure_ascii=False, indent=1))
            else:
                print("\n".join(repo_line(r) for r in hits) or "مفيش مطابق في أشهر 500. جرّب كلمات تانية، أو الأطلس الكامل (1000): rd.py x tool atlas find \"…\".")
        else:
            r = next((x for x in rows if x["repo"].lower() == a.q.lower() or x["repo"].split("/")[-1].lower() == a.q.lower()), None)
            if not r:
                raise SystemExit(f"مفيش: {a.q}")
            print(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False, indent=1))
    elif a.cmd == "skills":
        rows = library()
        if a.action == "stats":
            by = {}
            for r in rows:
                by[r["repo"]] = by.get(r["repo"], 0) + 1
            print(json.dumps({"skills": len(rows), "repos": len(by), "with_review_flags": sum(1 for r in rows if r.get("review")), "by_repo": by}, ensure_ascii=False, indent=1))
        elif a.action == "list":
            for r in rows:
                print(f"{r['rank']:>3}. {r['name']:<42} ★{r['stars']:>6,}  {r['repo']}")
        elif a.action == "find":
            hits = lib_find(a.q, 10)
            if getattr(a, "installed", False):
                print(json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in inst_find(a.q, 15)], ensure_ascii=False, indent=1))
            elif a.json:
                print(json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in hits], ensure_ascii=False, indent=1))
            else:
                ih = inst_find(a.q, 8)
                if ih:
                    print("🟢 متثبتة على الجهاز (" + str(len(installed())) + " مهارة):\n" + "\n".join(inst_line(r) for r in ih) + "\n")
                print(("📚 من المكتبة (مش متثبتة):\n" + "\n".join(lib_line(r) for r in hits)) if hits else "مفيش مطابق في المكتبة. جرّب كلمات إنجليزي، أو rd.py intel / x tool atlas find.")
        elif a.action == "show":
            f = LIBRARY / a.q / "SKILL.md"
            if not f.is_file():
                raise SystemExit(f"مفيش: {a.q}")
            print((LIBRARY / a.q / "SOURCE.json").read_text(encoding="utf-8"))
            print(f.read_text(encoding="utf-8", errors="replace")[:6000])
        else:
            d = lib_install(a.q, a.yes)
            if d:
                print(f"اتثبّتت: {d}")
    elif a.cmd == "character":
        cm = ROOT / "engine" / "skills" / "character-memory" / "scripts" / "charmem_cli.py"
        raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", str(cm)] + (a.args or ["--help"])))
    elif a.cmd == "math":
        dm = ROOT / "tools" / "draw-math" / "scripts" / "dmath.py"
        if not dm.is_file():
            raise SystemExit(f"مفيش draw-math: {dm}")
        raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", str(dm)] + (a.args or ["--help"])))
    elif a.cmd == "dcm":
        dc = ROOT / "engine" / "skills" / "dragon-character-memory" / "scripts" / "dcm.py"
        raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", str(dc)] + (a.args or ["--help"])))
    elif a.cmd == "desktop":
        bridge = ROOT / "engine" / "skills" / "blackdragon-desktop-bridge" / "scripts" / "bridge.py"
        raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", str(bridge)] + (a.args or ["--help"])))
    elif a.cmd == "doctor":
        doctor()
    elif a.cmd == "docs":
        docs()
    elif a.cmd == "x":
        d = ENGINE / "scripts" / "dragon.py"
        if not d.is_file():
            raise SystemExit("المحرك مش موجود: engine/scripts/dragon.py")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        sys.exit(subprocess.call([sys.executable, "-X", "utf8", str(d)] + a.args, env=env))
    elif a.cmd == "selftest":
        bad = []
        ids = [p["id"] for p in playbooks()]
        pids = {p["id"] for p in powers()}
        if len(ids) != len(set(ids)):
            bad.append("duplicate playbook id")
        for p in playbooks():
            for k in ("id", "ar", "triggers", "steps", "domain"):
                if not p.get(k):
                    bad.append(f"{p.get('id')}: missing {k}")
            for x in p.get("powers", []):
                if x not in pids:
                    bad.append(f"{p['id']}: unknown power {x}")
        for q, want in (jload(MIND / "route_tests.json", {}) or {}).items():
            pb, _ = route(understand(q)["text"])
            if not pb or pb[0][1]["id"] != want:
                bad.append(f"route «{q}» → {pb[0][1]['id'] if pb else None}, expected {want}")
        for raw, want in (jload(MIND / "understand_tests.json", {}) or {}).items():
            got = understand(raw)["text"]
            if got != want:
                bad.append(f"understand «{raw}» → «{got}», expected «{want}»")
        if (LIBRARY / "index.json").is_file():
            for r in library():
                if not (LIBRARY / r["name"] / "SKILL.md").is_file():
                    bad.append(f"library: missing {r['name']}/SKILL.md")
            if not lib_find("مونتاج فيديو", 3):
                bad.append("library: Arabic search returned nothing")
        if classify(__file__) != "python" or classify(str(ROOT)) not in ("skill-package", "repo"):
            bad.append("classify")
        idx = jload(MIND / "chats_index.json", {}) or {}
        nch = len(list((MIND / "chats").glob("[cst]*.md")))
        public = (MIND / "PUBLIC_EDITION.md").is_file() and not nch   # public repo: the owner's chats memory is left out on purpose
        if public:
            pass
        elif not nch or idx.get("count") != nch or any(not (MIND / "chats" / f"{c['id']}.md").is_file() for c in idx.get("convs", [])):
            bad.append(f"chats memory: index {idx.get('count')} vs files {nch}")
        try:
            C = chats_mod()
            for cq, want in ({} if public else (jload(MIND / "chats_tests.json", {}) or {})).items():
                if cq.startswith("_"):
                    continue
                h = C.search(cq, limit=1)
                if not h or h[0]["id"] != want:
                    bad.append(f"chats «{cq}» → {h[0]['id'] if h else None}, expected {want}")
            blind = [] if public else (jload(MIND / "chats_eval_blind.json", {}) or {}).get("items", [])
            if blind:                       # 30 questions written by an agent that never saw the search code
                t3 = sum(1 for it in blind if it["id"] in [h["id"] for h in C.search(it["q"], limit=3)])
                if t3 < 0.85 * len(blind):
                    bad.append(f"blind chats eval: top-3 {t3}/{len(blind)} < 85%")
        except Exception as e:
            bad.append(f"rd_chats: {e}")
        print(json.dumps({"ok": not bad, "playbooks": len(ids), "powers": len(pids), "lessons": len(lessons()), "chats": nch, "edition": "public (no chats memory)" if public else "full", "problems": bad}, ensure_ascii=False, indent=1))
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
