"""Reproducible Anatomy integration patch, applied AFTER the existing Golden Dragon layers.

No modifications to the generated app/ tree: make_golden_dragon.py owns that tree.
"""

TOOLS = '''    tool("anatomy", "Anatomy MIT skill bridge: doctor checks installation/Node; brief chooses a suitable SVG, SVG+WebGL or interactive 3D reference and quality gates. No download and no Node execution.",
         {"action": {"type": "string", "enum": ["doctor", "brief"]}, "query": S}, ["action"]),
    tool("anatomy_scaffold", "Copy the installed Anatomy kit, original example, scripts, SKILL.md and MIT LICENSE into a NEW relative working-folder path. Never download, run external code or overwrite. Requires approval.",
         {"destination": S, "example": {"type": "string", "enum": ["dial-indicator", "desk-computer", "arcade-cabinet", "raptor-engine", "ripple-tank", "turning-dial"]}}, ["destination"], approval=True),
'''

DISPATCH = '''def anatomy_dispatch(a, workdir):
    """Offline Anatomy bridge; writes only for explicitly approved scaffold."""
    import anatomy_bridge as ab
    try:
        act = a.get("action") or ""
        if act == "doctor":
            res = ab.doctor()
        elif act == "brief":
            res = ab.brief(a.get("query") or "")
        elif act == "scaffold":
            res = ab.scaffold(a.get("destination") or "",
                              a.get("example") or "dial-indicator", workdir=workdir)
        else:
            raise ValueError("INVALID_JSON: anatomy action")
        return json.dumps(res, ensure_ascii=False, indent=2), not res.get("ok", False)
    except (OSError, ValueError) as exc:
        return "✗ Anatomy: " + str(exc), True


'''

PROMPT = """- **Anatomy: النماذج الهندسية التفاعلية:** عند طلب رسم إيزومتري أو شرح حركة ماكينة، افحص anatomy doctor ثم anatomy brief مع وصف الطلب. مهارة Anatomy (MIT) تستخدم SVG مع ظلال وحركة، وWebGL للنار والماء، و3D تجريبي للأجزاء الدوارة. بعد موافقة المستخدم استخدم anatomy_scaffold لنسخ مثال حقيقي داخل مجلد عمل جديد؛ اقرأ SKILL.md ومراجع المصدر أولًا، وعدّل نموذج الحركة، وتحقق من الهندسة والتصادمات واللقطات وسجل المتصفح. لا تقل إن المثال الجاهز تنفيذ للطلب، ولا تدّع دقة فيزيائية دون إثبات. الأداة لا تثبّت شيئًا ولا تشغّل Node تلقائيًا.
  - باشتراك Claude: python -X utf8 "{APP_SOURCE}\\\\anatomy_bridge.py" doctor | brief "<الطلب>" | scaffold <مجلد> --example dial-indicator.
  - للتثبيت اليدوي من المصدر بموافقة صاحب الجهاز: npx skills add wheresryan22/anatomy -g -a claude-code. حافظ على LICENSE، وNode.js 20.10+ مطلوب.
"""


def patch_app(t, sub):
    t = sub(t, '    tool("rebuild_app",', TOOLS + '    tool("rebuild_app",', 1,
            "register anatomy read-only and approved scaffold tools")
    t = sub(t, '        if name == "fusion":\n            return fusion_dispatch(a)\n',
            '        if name == "fusion":\n            return fusion_dispatch(a)\n'
            '        if name == "anatomy":\n            return anatomy_dispatch(a, self.wd())\n'
            '        if name == "anatomy_scaffold":\n'
            '            return anatomy_dispatch({"action": "scaffold", **a}, self.wd())\n',
            1, "anatomy dispatcher hook")
    t = sub(t, '\ndef fusion_dispatch(a):', '\n' + DISPATCH + 'def fusion_dispatch(a):',
            1, "anatomy_dispatch helper")
    t = sub(t, "- **قواعد الفهرس:**", PROMPT + "- **قواعد الفهرس:**", 1,
            "Anatomy prompt and subscription commands")
    return t


def patch_build(t, sub):
    return sub(t, "--hidden-import gd_discover",
               "--hidden-import gd_discover --hidden-import anatomy_bridge", 1,
               "PyInstaller includes Anatomy bridge")
