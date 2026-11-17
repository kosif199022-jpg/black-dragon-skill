# -*- coding: utf-8 -*-
"""Deterministic Golden Dragon patch: register the read-only Anatomy bridge.

Keep the permanent change in forge/, never edit the generated app.py by hand.
Each source anchor must match exactly once; otherwise the forge stops safely.
"""

ANATOMY_TOOL = '''    tool("anatomy", "Anatomy visual-engineering bridge (offline, read-only). "
         "status: detect whether the upstream Anatomy Agent Skill and its SVG/WebGL/3D kit exist locally; "
         "guide: return an actionable implementation, interaction, geometry-audit and browser-verification workflow; "
         "check: perform limited static checks on a local HTML/SVG output. No install, download, code execution "
         "or publishing is performed. Never claim check proves rendering/physics correctness.",
         {"action": {"type": "string", "enum": ["status", "guide", "check"]},
          "query": S, "path": S}, ["action"]),
'''

ANATOMY_DISPATCH = '''def anatomy_dispatch(a):
    """Golden Dragon: no network or execution; real visual audits are separate."""
    import gd_anatomy
    return gd_anatomy.perform(a.get("action") or "", query=a.get("query") or "",
                              path=a.get("path") or "")

'''

PROMPT_ANCHOR = "## عقل التنين الذهبي (تفكير فائق بالعربي والإنجليزي)"
PROMPT_SECTION = """## 🔧 Anatomy — محاكاة ورسومات هندسية تفاعلية
- لطلبات «اشرح كيف تعمل الماكينة»، «تفكيك محرك»، «مجسم تفاعلي»، «محاكاة حركة»، استخدم
  `anatomy status` ثم `anatomy guide` مع الطلب. لو المهارة ناقصة، اقترح تثبيتها ولا تدّعي إنها موجودة.
- Anatomy من https://github.com/wheresryan22/anatomy (MIT، مستقلة عن التنين). اقرأ
  SKILL.md وreferences/ قبل الاستخدام. استخدم kit/iso-kit.mjs وlathe/tube للمجسم،
  WebGL للمؤثرات عند الحاجة، ووضع 3D التجريبي للدوران الحقيقي؛ لا تختلق إمكانيات غير موجودة.
- نموذج حالة واحد يحرك الأجزاء والعدادات. اعمل أزرار تفكيك/إرجاع/تشغيل وإيقاف،
  وصول لوحة مفاتيح، وHTML يعمل أوفلاين؛ وبعده تدقيق تصادم/ترتيب عمق، ولقطات
  capture/drive/lines وفحص بصري حقيقي. `anatomy check` فحص ثابت فقط وليس اعتماد هندسي.
- ثبّت/شغّل سكربتات خارجية فقط بعد موافقة المستخدم؛ لا تنشر تلقائيًا.

"""

SUBSCRIPTION = ("\n- anatomy: `python -X utf8 \"{APP_SOURCE}\\\\gd_anatomy.py\" status | guide \"<الطلب>\" "
                "| check \"<الملف.html>\"`. الفحص الثابت لا يغني عن اختبارات Anatomy بالمتصفح.")


def patch_app(t, sub):
    t = sub(t, '    tool("fusion",', ANATOMY_TOOL + '    tool("fusion",', 1,
            "gd_anatomy: tool schema")
    t = sub(t, '        if name == "fusion":\n            return fusion_dispatch(a)\n',
            '        if name == "fusion":\n            return fusion_dispatch(a)\n'
            '        if name == "anatomy":\n            return anatomy_dispatch(a)\n',
            1, "gd_anatomy: dispatcher")
    t = sub(t, '\ndef fusion_dispatch(a):', '\n' + ANATOMY_DISPATCH + 'def fusion_dispatch(a):',
            1, "gd_anatomy: function")
    t = sub(t, PROMPT_ANCHOR, PROMPT_SECTION + PROMPT_ANCHOR, 1,
            "gd_anatomy: prompt")
    # Exact insertion point already present in generated Golden Dragon source.
    t = sub(t, 'brief أول خطوة في أي طلب فيه أكتر من خطوة، وcheck قبل الرد، وdiscover لما الكتالوج المحلي قديم.',
            'brief أول خطوة في أي طلب فيه أكتر من خطوة، وcheck قبل الرد، وdiscover لما الكتالوج المحلي قديم.'
            + SUBSCRIPTION, 1, "gd_anatomy: subscription CLI")
    return t


def patch_build(t, sub):
    return sub(t, "--hidden-import gd_discover",
               "--hidden-import gd_discover --hidden-import gd_anatomy",
               1, "gd_anatomy: PyInstaller hidden import")
