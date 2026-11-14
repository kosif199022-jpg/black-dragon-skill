# عدّة البرمجة والتصميم (v2.17.0): المهارات اللي في صور صاحب الشغل

كل اللي هنا اتنسخ زي ما هو في `library/` ومعاه `LICENSE` و`SOURCE.json`. **مش متثبت**: Claude بيقرا `library/NAME/SKILL.md` وقت الحاجة، أو صاحب الشغل يثبّته. الرخص كلها بتسمح بالنسخ (MIT أو Apache-2.0).

| الصورة | المستودع | ⭐ | الرخصة | في المكتبة | بيعمل إيه |
|---|---|---|---|---|---|
| find-skills | vercel-labs/skills | 39k | MIT | `find-skills` | يدوّر على مهارة مناسبة في skills.sh ويثبّتها (`npx skills find …`) |
| UI UX Pro Max | nextlevelbuilder/ui-ux-pro-max-skill | 149k | MIT | `ui-ux-pro-max` | ذكاء تصميم: أنماط، ألوان، خطوط، مكونات، لكل نوع منتج (فيه RTL). سكربت بحث محلي على CSV |
| Context7 | upstash/context7 | 65k | MIT | `context7-cli`، `context7-mcp`، `find-docs` | يجيب توثيق المكتبات الحالي بالنسخة بدل التخمين من الذاكرة |
| Ponytail | DietrichGebert/ponytail | 191k | MIT | `ponytail` + review/audit/debt/gain/help | «أكسل سينيور»: أصغر تغيير يحل المشكلة كلها، ومراجعة وتدقيق |
| Agent Skills | addyosmani/agent-skills | 118k | MIT | 14 من 25 (حد المكتبة لكل مستودع) | spec، تقسيم المهام، TDD، debugging، code review، تبسيط، أمان، frontend، context، توثيق، interview-me، idea-refine |
| Strix | usestrix/strix | 76k | Apache-2.0 | `find-security-vulnerabilities-in-code`، `fix-security-vulnerabilities-with-strix` | فحص كودك إنت وتصليح ثغراته. مهارات الاختراق الهجومية **مادخلتش** (سياسة المكتبة) |
| Graphify | Graphify-Labs/graphify | 148k | Apache-2.0 أو MIT | `graphify` | يحوّل مشروع كامل (كود، docs، PDF) لخريطة معرفة تسأله عليها، ويوفّر توكنز |
| برومت بسيط ← احترافي | (الريل مش باين فيه اسم المستودع) | — | — | `prompt-master` (موجودة من قبل، 16k، MIT) و`mkprompt-*` | نفس الفكرة |
| subagent بـ Haiku | — | — | — | `agents/rd-runner.md` (v2.15) | اتعمل |
| instagram-agent-skill | — | — | — | `library/ig-*` (v2.16) | اتعمل |

## التثبيت الكامل على اللابتوب (بموافقة صاحب الشغل)
```bash
python -X utf8 scripts/rd.py skills install ui-ux-pro-max --yes      # أي مهارة من المكتبة لـ ~/.claude/skills
npx skills add addyosmani/agent-skills                                 # الـ 25 كلهم من المصدر
npx ctx7 setup                                                         # Context7 (أو موصّل Context7 من claude.ai)
/plugin marketplace add DietrichGebert/ponytail  ثم  /plugin install ponytail@ponytail
uv tool install graphifyy  ثم  graphify claude install --project       # Graphify (فيه كمان موصّل graphify في claude.ai محتاج تسجيل دخول تاني)
```
- Strix نفسه (الأداة) بيشغّل وكلاء اختراق على هدف: **على حاجتك إنت بس، وبإذن مكتوب**.
- `ui-ux-pro-max` فيه سكربت بيكلّم النت لتحديث الكتالوج (`review_before_running: network`): اقراه قبل ما تشغّله.
