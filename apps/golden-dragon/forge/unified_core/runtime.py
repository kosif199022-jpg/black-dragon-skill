"""Golden Dragon unified read-only core.

One programmatic entry point for catalog evidence, source inventory, and
native Windows PE header analysis. Direct Python calls, no MCP adapters.
This is a prototype diagnostic core, not the finished GoldenDragon app.

CLI: python runtime.py audit --root REPO --index INDEX --recipes RECIPES --binary EXE
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path


def inspect_pe(path: Path) -> dict:
    """Read PE headers directly; never launch or load target code."""
    path = Path(path)
    size = path.stat().st_size
    with path.open("rb") as stream:
        dos = stream.read(64)
        if len(dos) < 64 or dos[:2] != b"MZ":
            raise ValueError("not an MZ executable")
        pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
        if pe_offset < 64 or pe_offset > min(size - 26, 1024 * 1024):
            raise ValueError("invalid PE header location")
        stream.seek(pe_offset)
        coff = stream.read(26)
        if len(coff) < 26 or coff[:4] != b"PE\x00\x00":
            raise ValueError("missing PE signature")
        machine, sections, timestamp, _, _, optional_size, characteristics = struct.unpack_from("<HHIIIHH", coff, 4)
        if optional_size < 2:
            raise ValueError("missing PE optional header")
        magic = struct.unpack_from("<H", coff, 24)[0]
        if magic not in (0x10B, 0x20B):
            raise ValueError("unsupported PE optional header")
        sha = hashlib.sha256()
        stream.seek(0)
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            sha.update(block)
    return {
        "path": str(path), "format": "PE32+" if magic == 0x20B else "PE32",
        "machine": hex(machine), "sections": sections, "timestamp": timestamp,
        "characteristics": hex(characteristics), "bytes": size,
        "sha256": sha.hexdigest(),
        "execution": "not executed", "decompilation": "not performed",
    }



MEDIA_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".wav",
                  ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def inspect_media(path: Path, *, timeout: int = 30) -> dict:
    """Real FFprobe execution for one local media file; no network or shell.

    Enforces an explicit file path and restricts FFmpeg protocols to local
    file/pipe so nested playlist URLs cannot trigger remote network fetches.
    """
    path = Path(path).expanduser()
    if path.suffix.lower() not in MEDIA_SUFFIXES or not path.is_file():
        raise ValueError("media source must be an existing local audio/video file")
    if path.is_symlink():
        raise ValueError("media symlinks are not allowed")
    path = path.resolve()
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise ValueError("ffprobe is not installed or not on PATH")
    if not 1 <= timeout <= 120:
        raise ValueError("invalid probe timeout")
    args = [ffprobe, "-hide_banner", "-v", "error", "-protocol_whitelist",
            "file,pipe", "-show_format", "-show_streams", "-of", "json",
            "-i", str(path)]
    flags = 0x08000000 if sys.platform == "win32" else 0
    try:
        run = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             check=False, timeout=timeout, shell=False,
                             creationflags=flags)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("ffprobe timed out") from exc
    if run.returncode != 0:
        message = run.stderr.decode("utf-8", errors="replace").strip()[:240]
        raise ValueError("ffprobe failed: " + message)
    try:
        info = json.loads(run.stdout)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("ffprobe returned invalid JSON") from exc
    tracks = []
    for item in info.get("streams") or []:
        tracks.append({
            "index": item.get("index"),
            "type": item.get("codec_type"),
            "codec": item.get("codec_name"),
            "width": item.get("width"),
            "height": item.get("height"),
            "sample_rate": item.get("sample_rate"),
            "channels": item.get("channels"),
            "frame_rate": item.get("avg_frame_rate"),
        })
    fmt = info.get("format") or {}
    try:
        seconds = float(fmt["duration"]) if fmt.get("duration") else None
    except (ValueError, TypeError):
        seconds = None
    return {
        "path": str(path), "bytes": path.stat().st_size,
        "format": fmt.get("format_name"), "duration_seconds": seconds,
        "streams": tracks, "ffprobe_executed": True,
        "transcode_performed": False, "network_access": False,
    }

class GoldenDragonCore:
    """Single dispatch boundary for proven read-only operations."""

    OPERATIONS = {
        "catalog.audit": "Validate catalog declarations and passive presence",
        "source.audit": "Inventory source without importing or running it",
        "binary.pe_header": "Inspect a PE header without executing the binary",
        "media.probe": "Read media metadata with local FFprobe (no transcode)",
        "audit": "Run all selected read-only audit stages",
    }

    def __init__(self, root: Path, index: Path | None = None,
                 recipes: Path | None = None, binary: Path | None = None,
                 media: Path | None = None):
        self.root = Path(root)
        self.index = Path(index) if index else None
        self.recipes = Path(recipes) if recipes else None
        self.binary = Path(binary) if binary else None
        self.media = Path(media) if media else None

    def _catalog(self) -> dict:
        if self.index is None:
            raise ValueError("index path is required")
        from capability_ledger import build_ledger
        idx = json.loads(self.index.read_text(encoding="utf-8-sig"))
        rec = json.loads(self.recipes.read_text(encoding="utf-8-sig")) if self.recipes else []
        ledger = build_ledger(idx, rec)
        return {"summary": ledger["counts"], "recipe_issues": ledger["recipe_issues"],
                "duplicate_ids": ledger["duplicate_ids"]}

    def _source(self) -> dict:
        if not self.root.is_dir():
            raise ValueError("source root does not exist")
        from audit_tree import inventory
        result = inventory(self.root)
        return {"summary": result["summary"], "verification": result["verification"]}

    def execute(self, operation: str) -> dict:
        """Fail closed for unknown operations; no shell or arbitrary command."""
        if operation not in self.OPERATIONS:
            raise ValueError("unknown capability: " + operation)
        if operation == "catalog.audit":
            return {"operation": operation, "result": self._catalog()}
        if operation == "source.audit":
            return {"operation": operation, "result": self._source()}
        if operation == "binary.pe_header":
            if self.binary is None:
                raise ValueError("binary path is required")
            return {"operation": operation, "result": inspect_pe(self.binary)}
        if operation == "media.probe":
            if self.media is None:
                raise ValueError("media path is required")
            return {"operation": operation, "result": inspect_media(self.media)}
        stages = {"catalog": self._catalog(), "source": self._source()}
        if self.binary is not None:
            stages["binary"] = inspect_pe(self.binary)
        return {
            "operation": "audit", "stages": stages,
            "verified_runtime_capabilities": 0,
            "note": "PE identity and static analysis do not prove application operation",
        }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=sorted(GoldenDragonCore.OPERATIONS))
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--index", type=Path)
    p.add_argument("--recipes", type=Path)
    p.add_argument("--binary", type=Path)
    p.add_argument("--media", type=Path)
    args = p.parse_args(argv)
    core = GoldenDragonCore(args.root, args.index, args.recipes, args.binary, args.media)
    try:
        result = core.execute(args.operation)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        p.exit(1, f"ERROR: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
