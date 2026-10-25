"""Shared helpers for music-studio scripts. Standard library only.

Contract used by every CLI in this skill:
  * stdout carries machine-readable JSON (one object per line for streaming
    commands, a single object otherwise).
  * stderr carries human-readable logs and third-party noise.
This keeps the scripts safe to drive from Claude, from the dashboard server,
or from a shell.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULTS_DIR = SKILL_DIR / "defaults"

# The real stdout, captured before anything can rebind sys.stdout.
_REAL_STDOUT = sys.stdout

WORKSPACE_SUBDIRS = ("styles", "workflows", "output", "trash")


def log(*args) -> None:
    print(*args, file=sys.stderr, flush=True)


def emit(event: str, **fields) -> None:
    """Write one JSON line to the real stdout (streaming protocol)."""
    obj = {"event": event, **fields}
    _REAL_STDOUT.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _REAL_STDOUT.flush()


def print_json(obj) -> None:
    _REAL_STDOUT.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    _REAL_STDOUT.flush()


def workspace_dir() -> Path:
    """User workspace. Kept separate from the skill so updates never clobber it."""
    env = os.environ.get("MUSIC_STUDIO_HOME")
    return Path(env).expanduser() if env else Path.home() / "MusicStudio"


def ensure_workspace(ws: Path | None = None) -> Path:
    ws = ws or workspace_dir()
    ws.mkdir(parents=True, exist_ok=True)
    for sub in WORKSPACE_SUBDIRS:
        (ws / sub).mkdir(exist_ok=True)
    cfg = ws / "config.json"
    if not cfg.exists():
        write_json(cfg, {
            "_doc": "Your overrides. Only put keys you want to change; "
                    "everything else comes from the skill defaults. "
                    "Run `python scripts/msconfig.py show --explain` to see the result.",
        })
    return ws


def read_json(path: Path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path: Path, obj) -> None:
    """Atomic write so a crash or a concurrent reader never sees a half file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def slugify(text: str, maxlen: int = 40) -> str:
    """Filesystem-safe slug that keeps CJK letters (Windows handles Unicode names)."""
    text = unicodedata.normalize("NFKC", text or "").strip().lower()
    text = re.sub(r"[^\w]+", "-", text, flags=re.UNICODE).strip("-_")
    text = text[:maxlen].strip("-_")
    return text or "track"


def timestamp_id(slug: str) -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + slug


def parse_value(raw: str):
    """CLI value -> JSON value when it parses as JSON, else the raw string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def get_dotted(d: dict, key: str, default=None):
    cur = d
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_dotted(d: dict, key: str, value) -> None:
    parts = key.split(".")
    cur = d
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def unset_dotted(d: dict, key: str) -> bool:
    parts = key.split(".")
    cur = d
    for part in parts[:-1]:
        cur = cur.get(part)
        if not isinstance(cur, dict):
            return False
    return cur.pop(parts[-1], None) is not None
