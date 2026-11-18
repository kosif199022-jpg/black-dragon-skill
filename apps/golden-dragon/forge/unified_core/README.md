# Golden Dragon capability evidence ledger

This is an **experimental, passive diagnostic** for the ongoing unified-core rebuild. It is not a completed fusion of engines or a rebuilt Windows EXE.

From `apps/golden-dragon`:

```powershell
python -B forge/unified_core/capability_ledger.py --index forge/data/fusion/index.json --recipes forge/data/fusion/recipes.json --out "$env:TEMP/gd-capability-ledger.json"
python -B -m pytest forge/unified_core/tests/test_capability_ledger.py -q
```

The script reads catalog JSON and optionally writes a **new** report; it refuses to overwrite reports. It never imports target modules, launches programs, calls MCP, or changes the built app.

**Evidence rules:** `status: ok` is an index assertion, not a runtime test; a skill's source file and a program on PATH prove only passive presence. Recipe references are checked, but successful execution of every recipe still requires separate integration tests.

Verified in this development session: four synthetic unit tests passed and one synthetic CLI smoke run passed. **The real 1,101-unit catalog was not scanned with this new script yet** because the remote desktop stopped responding. The legacy app's 50 smoke/routing tests passed previously on its correct original Windows project path. No edits to `main` or installed `GoldenDragon.exe`.
