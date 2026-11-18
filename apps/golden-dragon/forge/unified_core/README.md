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

## Native unified diagnostic core (experimental)

`runtime.py` provides one direct Python interface: `GoldenDragonCore.execute(...)`. Its supported read-only operations are `catalog.audit`, `source.audit`, `binary.pe_header`, and `audit` (combined stages). The PE reader uses Python's standard library, not MCP.

From `apps/golden-dragon` on a machine with the project checkout:

```powershell
python -B forge/unified_core/runtime.py audit --root . --index forge/data/fusion/index.json --recipes forge/data/fusion/recipes.json --binary "$env:USERPROFILE/GoldenDragon/GoldenDragon.exe"
python -B -m pytest forge/unified_core/tests -q
```

`forge/make_golden_dragon.py` in this feature branch now copies the three core files into the future generated application and registers **fusion action `audit`** for a read-only catalog check. It also adds the PyInstaller hidden imports.

**Verification performed on DESKTOP-EUGN3DS, 2026-11-18:** the new ledger ran directly against the 1,101-unit / 42-recipe catalog and found zero broken recipe references; the combined core analyzed the 77 files in `apps/golden-dragon` and inspected the installed EXE's PE headers with a SHA-256 matching REA; a memory-only simulation of the generator's `fusion_dispatch({'action':'audit'})` returned the real catalog report successfully. Generator Python syntax, embedded dispatch syntax and the added bundle copy/import statements were independently checked. No installed app or `main` code was changed.

**Not yet verified:** a full regenerated GoldenDragon app, PyInstaller packaging of the new modules, actual runtime behavior of 1,101 indexed units, Ghidra decompilation, or an MP4 render. The catalog's `ok` label cannot substitute for runtime tests.
