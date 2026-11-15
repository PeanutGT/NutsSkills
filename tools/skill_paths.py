"""Where skills live in this repo.

A standalone skill is skills/<name>/. A suite is its own plugin directory suites/<suite>/ with
.claude-plugin/plugin.json and its skills under suites/<suite>/skills/<name>/, so claude.ai can sync it
from the marketplace (a plugin source needs its own manifest and a skills/ folder).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ("skills/*/SKILL.md", "suites/*/skills/*/SKILL.md")


def skill_dirs() -> list[Path]:
    """Every skill folder, standalone or in a suite, sorted by name."""
    return sorted({p.parent for pat in PATTERNS for p in ROOT.glob(pat)}, key=lambda d: (d.name, str(d)))


def find_skill(name: str) -> Path | None:
    for d in skill_dirs():
        if d.name == name:
            return d
    return None


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()
