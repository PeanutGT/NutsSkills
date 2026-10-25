#!/usr/bin/env python3
"""Package a skill as an upload-ready zip for Claude.ai / Claude Desktop.

The zip contains a single top-level folder <name>/ with SKILL.md at its root. Development-only
files (evals/, caches, OS junk) are left out so the upload stays small.

Usage:  python tools/build_zip.py exam-prep            -> dist/exam-prep-<version>.zip
        python tools/build_zip.py exam-prep --out x.zip
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"evals", "__pycache__", "node_modules", ".git"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}


def version_of(skill: Path) -> str:
    m = re.search(r'^\s+version:\s*"?([\d.]+)"?\s*$', (skill / "SKILL.md").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "0.0.0"


def build(name: str, out: Path | None = None) -> Path:
    skill = ROOT / "skills" / name
    if not (skill / "SKILL.md").exists():
        sys.exit(f"skills/{name}/SKILL.md not found")
    out = out or ROOT / "dist" / f"{name}-{version_of(skill)}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(skill.rglob("*")):
            rel = p.relative_to(skill)
            if p.is_dir() or rel.parts[0] in EXCLUDE_DIRS or EXCLUDE_DIRS & set(rel.parts) or p.name in EXCLUDE_FILES \
                    or p.suffix == ".pyc":
                continue
            z.write(p, Path(name) / rel)
            count += 1
    print(f"{out}  ({count} files, {out.stat().st_size / 1024:.0f} KB)")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("skill")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    build(a.skill, a.out)
