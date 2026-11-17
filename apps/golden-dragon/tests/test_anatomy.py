"""Anatomy integration: offline bridge, deterministic patch and reproducible forge.

Tests need no network, Chrome, Node, API key or installed Anatomy distribution.
The full generated EXE and browser/geometry audits require the owner's Windows forge.
"""
import importlib.util
from pathlib import Path

from conftest import FORGE


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bridge():
    return load(FORGE / "modules" / "gd_anatomy.py", "gd_anatomy_test")


def patcher():
    return load(FORGE / "gd_patches" / "gd_anatomy.py", "gd_anatomy_patch_test")


def test_missing_skill_is_reported_without_install(tmp_path, monkeypatch):
    m = bridge()
    monkeypatch.setenv("GOLDEN_ANATOMY_HOME", str(tmp_path / "absent"))
    found = m.discover()
    assert found["installed"] is False and found["path"] == ""
    assert "غير مثبتة" in m.status()
    assert m.perform("status")[1] is False
    assert "تحتاج تثبيت" in m.guide("simulator")


def test_partial_and_complete_skill(tmp_path, monkeypatch):
    m = bridge()
    root = tmp_path / "anatomy"
    root.mkdir()
    (root / "SKILL.md").write_text("# Anatomy", encoding="utf-8")
    monkeypatch.setenv("GOLDEN_ANATOMY_HOME", str(root))
    assert not m.discover()["installed"]
    assert "kit/iso-kit.mjs" in m.discover()["missing"]
    for relative in m.REQUIRED:
        p = root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("test", encoding="utf-8")
    assert m.discover()["installed"]
    assert "جاهز" in m.status()
    text = m.guide("شرح محرك")
    for name in ("audit.mjs", "capture.mjs", "drive.mjs", "lines.mjs"):
        assert name in text


def test_local_html_passes_limited_static_checks(tmp_path):
    m = bridge()
    page = tmp_path / "demo.html"
    (tmp_path / "demo.js").write_text("requestAnimationFrame(()=>{})", encoding="utf-8")
    page.write_text('''<!doctype html><html><body>
        <svg><circle r="4"/></svg><button id="run">Run</button>
        <output>0</output><script src="demo.js"></script>
        </body></html>''', encoding="utf-8")
    report, failed = m.check(str(page))
    assert not failed and "اجتاز الفحص الثابت" in report
    assert "لم تُشغّل JavaScript" in report


def test_external_or_missing_assets_fail_offline_check(tmp_path):
    m = bridge()
    page = tmp_path / "demo.html"
    page.write_text('''<svg></svg><script src="https://cdn.example/x.js"></script>
        <link rel="stylesheet" href="missing.css">''', encoding="utf-8")
    report, failed = m.check(str(page))
    assert failed and "خارجي" in report and "غير موجود محليًا" in report
    assert m.perform("check", path=str(page))[1] is True
    assert m.perform("check", path=str(tmp_path / "missing.html"))[1] is True
    assert m.perform("not-supported")[1] is True


def test_svg_xml_is_parsed_not_executed(tmp_path):
    m = bridge()
    page = tmp_path / "view.svg"
    page.write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle r="10"/></svg>', encoding="utf-8")
    assert m.check(str(page))[1] is False
    page.write_text("<svg><bad></svg>", encoding="utf-8")
    assert m.check(str(page))[1] is True


def test_generator_patch_is_anchor_guarded():
    p = patcher()
    def sub(t, old, new, count, _name):
        assert count == 1 and t.count(old) == count, old
        return t.replace(old, new)
    template = '''    tool("fusion", "schema")
        if name == "fusion":
            return fusion_dispatch(a)

def fusion_dispatch(a):
    return "", False

## عقل التنين الذهبي (تفكير فائق بالعربي والإنجليزي)
brief أول خطوة في أي طلب فيه أكتر من خطوة، وcheck قبل الرد، وdiscover لما الكتالوج المحلي قديم.
'''
    result = p.patch_app(template, sub)
    assert 'tool("anatomy"' in result
    assert 'if name == "anatomy":' in result
    assert "def anatomy_dispatch(a):" in result
    assert "Anatomy — محاكاة" in result
    assert "gd_anatomy.py" in result
    assert "--hidden-import gd_anatomy" in p.patch_build("--hidden-import gd_discover", sub)


def test_forge_carries_adapter_and_fusion_routes_to_it():
    maker = (FORGE / "make_golden_dragon.py").read_text(encoding="utf-8")
    fusion = (FORGE / "build_fusion.py").read_text(encoding="utf-8")
    recipes = (FORGE / "recipes.py").read_text(encoding="utf-8")
    assert "an.patch_app" in maker and "an.patch_build" in maker
    assert 'tmp / "gd_anatomy.py"' in maker
    assert 'unit("tool", "anatomy"' in fusion
    assert '"id": "machine-teardown"' in recipes and '"tool:anatomy"' in recipes
