"""Track library: browse takes, keep ratings / notes, trash.

The source of truth is each take's own folder (meta.json, final.json, audio).
Your annotations (rating, favourite, notes, tags, picked variant, custom title)
live in <workspace>/library.json, so rescanning can never lose them and
deleting library.json never deletes audio.

    library.py list | show ID | annotate ID key=value ... | trash ID
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import msconfig
from common import print_json, read_json, slugify, workspace_dir, write_json

ANN_FIELDS = {"title", "rating", "favorite", "notes", "tags", "picked"}


def safe_name(text: str) -> str:
    return slugify(text, 48)


def _out_root(ws: Path) -> Path:
    cfg, _ = msconfig.load_config(ws)
    d = Path(cfg["output"]["dir"])
    return d if d.is_absolute() else ws / d


def _annotations(ws: Path) -> dict:
    return (read_json(ws / "library.json", {}) or {}).get("annotations", {})


def get_take(take_id: str, ws: Path | None = None) -> dict | None:
    ws = ws or workspace_dir()
    folder = _out_root(ws) / take_id
    meta = read_json(folder / "meta.json") if folder.is_dir() else None
    if not meta:
        return None
    variants = []
    for v in meta.get("variants", []):
        f = folder / v["file"]
        variants.append({**v, "exists": f.exists(), "bytes": f.stat().st_size if f.exists() else 0})
    finals = read_json(folder / "final.json", []) or []
    ann = _annotations(ws).get(take_id, {})
    return {**meta, "dir": str(folder), "variants": variants, "finals": finals, "annotations": ann,
            "title": ann.get("title") or meta.get("title")}


def list_takes(ws: Path | None = None) -> list[dict]:
    ws = ws or workspace_dir()
    root = _out_root(ws)
    out = []
    if root.is_dir():
        for folder in root.iterdir():
            if not (folder / "meta.json").exists():
                continue
            t = get_take(folder.name, ws)
            if not t:
                continue
            spec = t.get("spec", {})
            ann = t["annotations"]
            out.append({
                "id": t["id"], "title": t["title"], "created": t.get("created"),
                "style": spec.get("style"), "moods": spec.get("moods", []),
                "duration": spec.get("duration"), "bpm": spec.get("bpm"), "key": spec.get("key"),
                "engine": t.get("engine"), "quality": t.get("quality"),
                "variants": len(t["variants"]), "finals": len(t["finals"]),
                "rating": ann.get("rating", 0), "favorite": bool(ann.get("favorite")),
                "tags": ann.get("tags", []), "picked": ann.get("picked"),
            })
    out.sort(key=lambda t: t.get("created") or "", reverse=True)
    return out


def annotate(take_id: str, fields: dict, ws: Path | None = None) -> dict:
    ws = ws or workspace_dir()
    if get_take(take_id, ws) is None:
        raise KeyError(f"unknown take '{take_id}'")
    clean: dict = {}
    for k, v in fields.items():
        if k not in ANN_FIELDS:
            raise ValueError(f"cannot set '{k}' (allowed: {', '.join(sorted(ANN_FIELDS))})")
        if k == "rating":
            v = max(0, min(5, int(v)))
        elif k == "favorite":
            v = bool(v)
        elif k == "picked":
            v = int(v)
        elif k == "tags":
            v = [str(t).strip() for t in (v if isinstance(v, list) else str(v).split(",")) if str(t).strip()]
        else:
            v = str(v)[:2000]
        clean[k] = v
    data = read_json(ws / "library.json", {}) or {}
    ann = data.setdefault("annotations", {})
    ann.setdefault(take_id, {}).update(clean)
    write_json(ws / "library.json", data)
    return ann[take_id]


def trash_take(take_id: str, ws: Path | None = None) -> bool:
    """Move a take to <workspace>/trash/ (never deletes audio outright)."""
    ws = ws or workspace_dir()
    folder = _out_root(ws) / take_id
    if not (folder / "meta.json").exists():
        return False
    trash = ws / "trash"
    trash.mkdir(exist_ok=True)
    dest = trash / take_id
    n = 2
    while dest.exists():
        dest = trash / f"{take_id}-{n}"
        n += 1
    folder.replace(dest)
    return True


def resolve_file(take_id: str, rel: str, ws: Path | None = None) -> Path | None:
    """Map a take-relative path to a real file, refusing anything outside the take folder."""
    ws = ws or workspace_dir()
    folder = (_out_root(ws) / take_id).resolve()
    target = (folder / rel).resolve()
    if folder not in target.parents or not target.is_file():
        return None
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("show"); s.add_argument("id")
    a = sub.add_parser("annotate"); a.add_argument("id"); a.add_argument("pairs", nargs="+")
    t = sub.add_parser("trash"); t.add_argument("id")
    args = ap.parse_args(argv)
    if args.cmd == "list":
        print_json(list_takes())
    elif args.cmd == "show":
        t = get_take(args.id)
        print_json(t if t else {"error": f"unknown take '{args.id}'"})
        return 0 if t else 1
    elif args.cmd == "annotate":
        fields = {}
        for p in args.pairs:
            k, _, v = p.partition("=")
            fields[k] = v
        print_json(annotate(args.id, fields))
    elif args.cmd == "trash":
        ok = trash_take(args.id)
        print_json({"ok": ok})
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
