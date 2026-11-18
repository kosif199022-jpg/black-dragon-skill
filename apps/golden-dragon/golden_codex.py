"""Run a Golden Dragon request through the local Codex CLI."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help="Golden Dragon request in Arabic or English")
    parser.add_argument("--preview", action="store_true", help="Print the brief locally")
    args = parser.parse_args()
    if not args.request.strip():
        parser.error("Enter a non-empty request.")
    fusion = Path(__file__).resolve().parent / "app" / "dragon_fusion.py"
    brief = subprocess.run(
        [sys.executable, "-X", "utf8", str(fusion), "brief", args.request],
        stdout=subprocess.PIPE, encoding="utf-8",
    )
    if brief.returncode:
        print(brief.stdout, file=sys.stderr)
        return brief.returncode
    prompt = f"Golden Dragon request:\n{args.request}\n\nLocal planning context:\n{brief.stdout}"
    if args.preview:
        print(prompt)
        return 0
    codex = shutil.which("codex")
    if not codex:
        parser.exit(1, "Codex CLI is required. Use --preview to inspect the brief locally.\n")
    return subprocess.run(
        [codex, "exec", "--sandbox", "read-only", "-"],
        input=prompt.encode("utf-8"),
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
