"""Layered configuration, style / mood / workflow libraries and request planning.

Everything user-customisable resolves through here so Claude, the dashboard and
the engine all agree on the same effective values.

Layers (lowest -> highest):
    skill defaults (defaults/)  ->  workspace (~/MusicStudio/)  ->  request

CLI:
    msconfig.py init                     create the workspace skeleton
    msconfig.py show [--explain]         effective config (+ where each value came from)
    msconfig.py tier                     detected GPU, tier and resolved params per preset
    msconfig.py styles|moods|workflows   list the libraries
    msconfig.py plan --style S [...]     build a track spec (JSON) from a style + moods
    msconfig.py set KEY VALUE            write a workspace override (dotted key, JSON value)
    msconfig.py unset KEY                remove a workspace override
    msconfig.py validate                 check config, styles and workflows
"""
from __future__ import annotations

import argparse
import copy
import random
import re
import sys
from pathlib import Path

import gpu
from common import (DEFAULTS_DIR, ensure_workspace, get_dotted, log, parse_value,
                    print_json, read_json, set_dotted, unset_dotted, workspace_dir,
                    write_json)

LOAD_PROBLEMS: list[str] = []


# --------------------------------------------------------------------------- merge
def _clean(d: dict) -> dict:
    """Drop documentation keys (_doc, _note...) so they never reach the engine."""
    return {k: v for k, v in d.items() if not k.startswith("_")}


def merge(base: dict, over: dict, source: str, prov: dict | None = None, prefix: str = "") -> dict:
    """Deep-merge `over` onto a copy of `base`, recording the source of every leaf.

    Dicts merge key by key; lists and scalars are replaced. A dict that contains
    "$replace": true replaces the base dict wholesale instead of merging.
    """
    out = copy.deepcopy(base)
    for key, val in over.items():
        if key.startswith("_"):
            continue
        path = f"{prefix}{key}"
        if isinstance(val, dict) and isinstance(out.get(key), dict) and not val.get("$replace"):
            out[key] = merge(out[key], val, source, prov, path + ".")
        else:
            if isinstance(val, dict):
                val = {k: v for k, v in val.items() if k != "$replace"}
            out[key] = copy.deepcopy(val)
            if prov is not None:
                _mark(prov, path, val, source)
    return out


def _mark(prov: dict, path: str, val, source: str) -> None:
    if isinstance(val, dict):
        for k, v in val.items():
            if not k.startswith("_"):
                _mark(prov, f"{path}.{k}", v, source)
    else:
        prov[path] = source


# --------------------------------------------------------------------------- config
def load_config(ws: Path | None = None) -> tuple[dict, dict]:
    """Return (effective_config, provenance)."""
    ws = ws or workspace_dir()
    prov: dict = {}
    base = read_json(DEFAULTS_DIR / "config.json", {}) or {}
    base = _strip_docs(base)
    _mark(prov, "", base, "default")
    prov = {k.lstrip("."): v for k, v in prov.items()}
    user = read_json(ws / "config.json", {}) or {}
    cfg = merge(base, user, "user", prov)
    return cfg, prov


def _strip_docs(d):
    if isinstance(d, dict):
        return {k: _strip_docs(v) for k, v in d.items() if not k.startswith("_")}
    return d


def resolve_tier(cfg: dict) -> tuple[str, dict]:
    info = gpu.describe()
    wanted = cfg["hardware"].get("tier", "auto")
    tiers = cfg["hardware"]["tiers"]
    if wanted != "auto":
        if wanted not in tiers:
            log(f"[warn] hardware.tier '{wanted}' is not defined; using detected tier")
        else:
            info["forced"] = True
            return wanted, info
    return info["tier"], info


def resolve_params(cfg: dict, quality: str | None = None, overrides: dict | None = None,
                   tier: str | None = None) -> dict:
    """Resolve the engine parameters for one generation.

    Precedence: generation < tier < preset < engine_overrides < overrides (request).
    Returns {"params", "tier", "quality", "warnings", "sources"}.
    """
    warnings: list[str] = []
    if tier is None:
        tier, _ = resolve_tier(cfg)
    tier_cfg = cfg["hardware"]["tiers"].get(tier) or next(iter(cfg["hardware"]["tiers"].values()))
    quality = quality or cfg["quality"]["default"]
    presets = cfg["quality"]["presets"]
    if quality not in presets:
        warnings.append(f"quality '{quality}' unknown, using '{cfg['quality']['default']}'")
        quality = cfg["quality"]["default"]

    prov: dict = {}
    params: dict = {}
    layers = [
        ("generation", cfg["generation"]),
        (f"tier:{tier}", {k: v for k, v in tier_cfg.items() if k not in ("max_duration", "max_batch")}),
        (f"preset:{quality}", presets[quality]),
        ("engine_overrides", cfg.get("engine_overrides", {})),
        ("request", {k: v for k, v in (overrides or {}).items() if v is not None}),
    ]
    for name, layer in layers:
        params = merge(params, _clean(layer), name, prov)
    params["lm_backend"] = cfg["hardware"].get("lm_backend", "pt")

    max_dur = tier_cfg.get("max_duration")
    if max_dur and params.get("duration", 0) > max_dur:
        warnings.append(f"duration {params['duration']}s exceeds the {tier} tier cap ({max_dur}s); "
                        f"clamped. Raise hardware.tiers.{tier}.max_duration if your card copes.")
        params["duration"] = max_dur
    max_batch = tier_cfg.get("max_batch")
    if max_batch and params.get("batch_size", 1) > max_batch:
        if (overrides or {}).get("batch_size"):  # only nag when the person asked for it; presets are just defaults
            warnings.append(f"you asked for {params['batch_size']} variants but the {tier} tier allows {max_batch}; using {max_batch}.")
        params["batch_size"] = max_batch
    if params.get("thinking") and not params.get("lm_model"):
        if (overrides or {}).get("thinking"):  # presets ask for it by default; only mention it when the person did
            warnings.append(f"the {tier} tier has no language model, so 'thinking' is off.")
        params["thinking"] = False
    return {"params": params, "tier": tier, "quality": quality, "warnings": warnings, "sources": prov}


# --------------------------------------------------------------------------- libraries
def _load_dir(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path.is_dir():
        return out
    for f in sorted(path.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            obj = read_json(f)
        except ValueError as exc:  # JSONDecodeError subclasses ValueError
            LOAD_PROBLEMS.append(f"{f}: invalid JSON ({exc})")
            continue
        if not isinstance(obj, dict):
            LOAD_PROBLEMS.append(f"{f}: expected a JSON object")
            continue
        out[str(obj.get("id") or f.stem)] = obj
    return out


def _layer_collection(base: dict, user: dict) -> dict:
    out: dict = {}
    for k, v in base.items():
        out[k] = {**v, "id": k, "_source": "builtin"}
    for k, u in user.items():
        if k in base and not u.get("$replace"):
            merged = merge(base[k], u, "user")
            out[k] = {**merged, "id": k, "_source": "builtin+user"}
        else:
            u = {kk: vv for kk, vv in u.items() if kk != "$replace"}
            out[k] = {**u, "id": k, "_source": "user"}
    return out


def load_styles(ws: Path | None = None) -> dict[str, dict]:
    ws = ws or workspace_dir()
    return _layer_collection(_load_dir(DEFAULTS_DIR / "styles"), _load_dir(ws / "styles"))


def load_workflows(ws: Path | None = None) -> dict[str, dict]:
    ws = ws or workspace_dir()
    return _layer_collection(_load_dir(DEFAULTS_DIR / "workflows"), _load_dir(ws / "workflows"))


def load_moods(ws: Path | None = None) -> dict[str, dict]:
    ws = ws or workspace_dir()
    base = read_json(DEFAULTS_DIR / "moods.json", {}) or {}
    user = read_json(ws / "moods.json", {}) or {}
    base = {k: v for k, v in base.items() if not k.startswith("_")}
    user = {k: v for k, v in user.items() if not k.startswith("_")}
    return _layer_collection(base, user)


def load_lexicon(ws: Path | None = None) -> dict[str, dict]:
    ws = ws or workspace_dir()
    base = read_json(DEFAULTS_DIR / "lexicon.json", {}) or {}
    user = read_json(ws / "lexicon.json", {}) or {}
    base = {k: v for k, v in base.items() if not k.startswith("_")}
    user = {k: v for k, v in user.items() if not k.startswith("_")}
    return _layer_collection(base, user)


_FILLER = ("音樂", "背景", "一首", "一段", "幫我", "我要", "我想", "我們", "做", "的", "要", "給", "用", "bgm", "歌", "曲", "適合",
           "可以", "有點", "一點", "很", "非常", "感覺", "比較", "那種", "一個", "一些", "需要", "想要", "希望", "整體", "風格", "類型", "請",
           "畫面", "場景", "時候", "用於", "用在")


def extract_tags(description: str, lexicon: dict) -> dict:
    """Plain-language description -> English caption tags using the lexicon.

    Longest terms win and are blanked out so '電吉他' is not also read as '吉他'.
    Left-over English fragments pass through as tags; left-over Chinese is reported, never guessed.
    """
    text = (description or "").lower()
    terms = sorted(((t.lower(), k) for k, v in lexicon.items() if v.get("tags") for t in v.get("match", [])),
                   key=lambda x: -len(x[0]))
    hit: list[str] = []
    for term, key in terms:
        if not term:
            continue
        pat = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])" if re.fullmatch(r"[a-z0-9 \-]+", term) else re.escape(term)
        new, n = re.subn(pat, " ", text)
        if n:
            text = new
            if key not in hit:
                hit.append(key)
    tags, remove, delta = [], [], 0
    for key in hit:
        e = lexicon[key]
        tags += _tags(e["tags"])[: 3 if e.get("group") == "genre" else 2]
        remove += [r.lower() for r in e.get("remove", [])]
        delta += int(e.get("bpm_delta", 0))
    passthrough, unmatched = [], []
    for frag in re.split(r"[,;，；。.!?！？\n、/]+", text):
        frag = frag.strip()
        if not frag:
            continue
        if re.search(r"[\u3400-\u9fff]", frag):
            rest = frag
            for f in _FILLER:
                rest = rest.replace(f, " ")
            rest = re.sub(r"[^\u3400-\u9fffA-Za-z0-9]+", "", rest)
            if len(re.findall(r"[\u3400-\u9fff]", rest)) >= 2:
                unmatched.append(rest)
        elif re.search(r"[a-z]{3,}", frag):
            passthrough.append(re.sub(r"\s+", " ", frag))
    return {"tags": tags, "passthrough": passthrough, "unmatched": unmatched, "matched": hit, "remove": remove, "bpm_delta": delta}


def save_user_item(kind: str, obj: dict, ws: Path | None = None) -> Path:
    """Persist a user style/workflow into the workspace (kind: 'styles'|'workflows')."""
    ws = ensure_workspace(ws)
    item_id = re.sub(r"[^\w\-]+", "-", str(obj.get("id", ""))).strip("-")
    if not item_id:
        raise ValueError("item needs an 'id'")
    obj = {k: v for k, v in obj.items() if not k.startswith("_") or k == "_doc"}
    obj["id"] = item_id
    path = ws / kind / f"{item_id}.json"
    write_json(path, obj)
    return path


def delete_user_item(kind: str, item_id: str, ws: Path | None = None) -> bool:
    ws = ws or workspace_dir()
    path = ws / kind / f"{item_id}.json"
    if path.exists():
        trash = ws / "trash"
        trash.mkdir(exist_ok=True)
        path.replace(trash / f"{kind}-{item_id}.json")
        return True
    return False


# --------------------------------------------------------------------------- planning
def _tags(text: str) -> list[str]:
    return [t.strip() for t in (text or "").split(",") if t.strip()]


def build_spec(cfg: dict, styles: dict, moods: dict, *, style_id: str, description: str = "",
               mood_ids: list[str] | tuple = (), title: str | None = None,
               duration: float | None = None, bpm: int | None = None, key: str | None = None,
               time_signature: str | None = None, variants: int | None = None,
               quality: str | None = None, workflow: str | None = None, seed: int | None = None,
               instrumental: bool | None = None, caption_extra: str = "",
               workflows: dict | None = None, lexicon: dict | None = None,
               caption_override: str | None = None) -> dict:
    """Turn a style + moods + overrides into a portable track spec.

    Precedence for quality / variants / duration: explicit argument > workflow `defaults`
    > style (duration only) > generation config.
    """
    warnings: list[str] = []
    style = styles.get(style_id)
    if style is None:
        raise KeyError(f"unknown style '{style_id}'. Known: {', '.join(sorted(styles))}")

    style_tags: list[str] = _tags(style.get("caption", ""))
    bpm_delta = 0
    mood_tags: list[str] = []
    for mid in mood_ids:
        mood = moods.get(mid)
        if mood is None:
            warnings.append(f"unknown mood '{mid}' ignored")
            continue
        mood_tags += _tags(mood.get("caption", ""))
        bpm_delta += int(mood.get("bpm_delta", 0))
    ext = extract_tags(description, lexicon if lexicon is not None else load_lexicon())
    bpm_delta += ext["bpm_delta"]
    desc_tags = ext["tags"] + ext["passthrough"]
    if ext["remove"]:
        drop = lambda t: any(r in t.lower() for r in ext["remove"])  # noqa: E731
        style_tags = [t for t in style_tags if not drop(t)]
        mood_tags = [t for t in mood_tags if not drop(t)]
    if ext["unmatched"]:
        warnings.append("not understood from your description: " + " / ".join(ext["unmatched"]) +
                        " - add English tags in 'extra tags', or teach it in <workspace>/lexicon.json")
    extra_tags = _tags(caption_extra)

    def join(parts: list[list[str]]) -> list[str]:
        seen, uniq = set(), []
        for t in (t for part in parts for t in part):
            if t.lower() not in seen:
                seen.add(t.lower())
                uniq.append(t)
        return uniq

    if caption_override and caption_override.strip():
        uniq = join([_tags(caption_override)])
        parts = {"style": [], "description": [], "moods": [], "extra": [], "override": uniq}
    else:
        uniq = join([style_tags, desc_tags, mood_tags, extra_tags])
        parts = {"style": style_tags, "description": desc_tags, "moods": mood_tags, "extra": extra_tags, "override": []}
        # Too many tags blur the result and ACE-Step caps the caption at 512 chars. Keep, in priority order:
        # the style's core tags, everything the person said, their moods, then the rest of the style.
        MAX_TAGS = 14
        prio = join([style_tags[:4], desc_tags, extra_tags, mood_tags, style_tags[4:]])
        if len(prio) > MAX_TAGS or len(", ".join(uniq)) > 480:
            kept = []
            for t in prio:
                if len(kept) < MAX_TAGS and len(", ".join(kept + [t])) <= 480:
                    kept.append(t)
            dropped = [t for t in prio if t not in kept]
            order = {t.lower(): i for i, t in enumerate(uniq)}
            uniq = sorted(kept, key=lambda t: order[t.lower()])
            if dropped:
                warnings.append(f"kept the {len(kept)} most important tags; dropped: {', '.join(dropped)}")
    caption = ", ".join(uniq)
    if len(caption) > 512:
        caption = caption[:512].rsplit(",", 1)[0]
        warnings.append("caption cut at 512 characters (ACE-Step limit)")
    elif len(caption) > 400:
        warnings.append(f"caption is {len(caption)} chars; very long captions tend to blur the style")
    if caption_override and len(uniq) > 16:
        warnings.append(f"{len(uniq)} tags - more than ~14 tends to blur the result")

    rng = random.Random(f"{style_id}|{description}|{seed}")  # stable: the dashboard preview must match what gets generated
    style_bpm = style.get("bpm")
    if bpm is None and style_bpm:
        if isinstance(style_bpm, (list, tuple)) and len(style_bpm) == 2:
            bpm = round((style_bpm[0] + style_bpm[1]) / 2)
        elif isinstance(style_bpm, (int, float)):
            bpm = int(style_bpm)
        if bpm is not None and bpm_delta:
            # moods nudge the tempo, but never far outside what the style is meant to sound like
            lo, hi = (style_bpm if isinstance(style_bpm, (list, tuple)) else (style_bpm, style_bpm))
            bpm = int(max(lo - 10, min(hi + 10, bpm + bpm_delta)))
    if key is None and style.get("keys"):
        key = rng.choice(style["keys"])
    wf_defaults = ((workflows or {}).get(workflow or cfg["workflow"]["default"]) or {}).get("defaults", {})
    quality = quality or wf_defaults.get("quality")
    variants = variants or wf_defaults.get("variants")
    dur_cfg = style.get("duration") or {}
    if duration is None:
        duration = wf_defaults.get("duration") or dur_cfg.get("default", cfg["generation"].get("duration", 60))
    if dur_cfg.get("max") and duration > dur_cfg["max"]:
        warnings.append(f"duration {duration}s is above this style's usual max ({dur_cfg['max']}s)")

    workflow = workflow or cfg["workflow"]["default"]
    spec = {
        "title": title or (description[:40] if description else style.get("name", style_id)),
        "style": style_id,
        "moods": list(mood_ids),
        "description": description,
        "caption": caption,
        "caption_parts": parts,
        "bpm": bpm,
        "key": key,
        "time_signature": time_signature or style.get("time_signature", "4"),
        "duration": duration,
        "variants": variants,
        "quality": quality,
        "workflow": workflow,
        "seed": -1 if seed is None else seed,
        "instrumental": cfg["generation"]["instrumental"] if instrumental is None else instrumental,
        "loopable": bool(style.get("loopable", False)),
        "warnings": warnings,
    }
    if duration and duration > 180:
        warnings.append(f"{duration}s is long for ACE-Step: instrumentals are most stable at 30-180 s. "
                        "For longer pieces generate ~2 min and loop it.")
    return spec


# --------------------------------------------------------------------------- validation
def validate(ws: Path | None = None) -> list[str]:
    ws = ws or workspace_dir()
    LOAD_PROBLEMS.clear()
    problems: list[str] = []
    cfg, _ = load_config(ws)
    styles, workflows, moods = load_styles(ws), load_workflows(ws), load_moods(ws)
    problems += LOAD_PROBLEMS

    if cfg["engine"] not in ("ace", "mock"):
        problems.append(f"engine must be 'ace' or 'mock', got {cfg['engine']!r}")
    if cfg["engine"] == "ace":
        d = cfg.get("ace_step_dir", "CHANGE_ME")
        if d == "CHANGE_ME":
            problems.append("ace_step_dir is not set (run scripts/setup_windows.ps1 or `msconfig.py set ace_step_dir \"C:/path\"`)")
        elif not Path(d).expanduser().is_dir():
            problems.append(f"ace_step_dir does not exist: {d}")
    if cfg["quality"]["default"] not in cfg["quality"]["presets"]:
        problems.append(f"quality.default '{cfg['quality']['default']}' is not a defined preset")
    if cfg["hardware"]["tier"] not in ("auto", *cfg["hardware"]["tiers"]):
        problems.append(f"hardware.tier '{cfg['hardware']['tier']}' is not 'auto' or a defined tier")
    if cfg["workflow"]["default"] not in workflows:
        problems.append(f"workflow.default '{cfg['workflow']['default']}' does not exist")
    for key in ("duration", "guidance_scale", "shift", "inference_steps"):
        v = cfg["generation"].get(key)
        if not isinstance(v, (int, float)) or v <= 0:
            problems.append(f"generation.{key} must be a positive number, got {v!r}")
    for name, preset in cfg["quality"]["presets"].items():
        b = preset.get("batch_size", 1)
        if not isinstance(b, int) or not 1 <= b <= 8:
            problems.append(f"quality.presets.{name}.batch_size must be an integer 1-8")

    for sid, s in styles.items():
        for req in ("name", "caption"):
            if not s.get(req):
                problems.append(f"style '{sid}' ({s['_source']}) is missing '{req}'")
        b = s.get("bpm")
        if b is not None and not (isinstance(b, (int, float)) or
                                  (isinstance(b, list) and len(b) == 2 and b[0] <= b[1])):
            problems.append(f"style '{sid}': bpm must be a number or [min, max]")
    for wid, w in workflows.items():
        stages = w.get("stages")
        if not isinstance(stages, list) or not stages:
            problems.append(f"workflow '{wid}' has no stages")
            continue
        ids = [st.get("id") for st in stages]
        if "generate" not in ids:
            problems.append(f"workflow '{wid}' has no 'generate' stage")
        for st in stages:
            if st.get("id") not in ("plan", "generate", "audition", "postprocess"):
                problems.append(f"workflow '{wid}': unknown stage id {st.get('id')!r}")
            if st.get("gate", "auto") not in ("auto", "confirm", "pick"):
                problems.append(f"workflow '{wid}': gate must be auto|confirm|pick")
        for st in stages:
            if st.get("id") == "postprocess":
                for step in st.get("steps", []):
                    if step.get("op") not in ("trim_silence", "fit", "fade", "loop", "loudnorm", "export"):
                        problems.append(f"workflow '{wid}': unknown postprocess op {step.get('op')!r}")
                    if step.get("when") not in (None, "loopable", "not_loopable"):
                        problems.append(f"workflow '{wid}': step 'when' must be loopable|not_loopable")
    return problems


# --------------------------------------------------------------------------- CLI
def _summ(items: dict, fields=("name", "description")) -> list[dict]:
    return [{"id": k, "source": v.get("_source"), **{f: v.get(f) for f in fields}} for k, v in items.items()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sp = sub.add_parser("show"); sp.add_argument("--explain", action="store_true")
    sub.add_parser("tier")
    sub.add_parser("styles"); sub.add_parser("moods"); sub.add_parser("workflows"); sub.add_parser("lexicon")
    sp = sub.add_parser("plan")
    sp.add_argument("--style", required=True)
    sp.add_argument("--mood", default="", help="comma separated mood ids")
    sp.add_argument("--description", default="")
    sp.add_argument("--caption-extra", default="")
    sp.add_argument("--caption", help="use exactly this caption (comma separated English tags) instead of building one")
    sp.add_argument("--title")
    sp.add_argument("--duration", type=float)
    sp.add_argument("--bpm", type=int)
    sp.add_argument("--key")
    sp.add_argument("--time-signature")
    sp.add_argument("--variants", type=int)
    sp.add_argument("--quality")
    sp.add_argument("--workflow")
    sp.add_argument("--seed", type=int)
    sp.add_argument("--vocals", action="store_true", help="not instrumental (reserved for phase 2)")
    sp = sub.add_parser("set"); sp.add_argument("key"); sp.add_argument("value")
    sp = sub.add_parser("unset"); sp.add_argument("key")
    sub.add_parser("validate")
    args = ap.parse_args(argv)

    ws = ensure_workspace() if args.cmd in ("init", "set", "unset") else workspace_dir()

    if args.cmd == "init":
        print_json({"workspace": str(ws)})
    elif args.cmd == "show":
        cfg, prov = load_config(ws)
        print_json({"workspace": str(ws), "config": cfg, **({"sources": prov} if args.explain else {})})
    elif args.cmd == "tier":
        cfg, _ = load_config(ws)
        tier, info = resolve_tier(cfg)
        presets = {q: resolve_params(cfg, q, tier=tier) for q in cfg["quality"]["presets"]}
        print_json({"gpu": info, "tier": tier,
                    "presets": {q: {"params": r["params"], "warnings": r["warnings"]} for q, r in presets.items()}})
    elif args.cmd == "styles":
        print_json(_summ(load_styles(ws)))
    elif args.cmd == "moods":
        print_json(_summ(load_moods(ws), ("caption",)))
    elif args.cmd == "workflows":
        print_json(_summ(load_workflows(ws)))
    elif args.cmd == "lexicon":
        print_json(_summ(load_lexicon(ws), ("match", "tags", "group")))
    elif args.cmd == "plan":
        cfg, _ = load_config(ws)
        try:
            spec = build_spec(
                cfg, load_styles(ws), load_moods(ws), style_id=args.style,
                description=args.description, mood_ids=[m for m in args.mood.split(",") if m],
                title=args.title, duration=args.duration, bpm=args.bpm, key=args.key,
                time_signature=args.time_signature, variants=args.variants, quality=args.quality,
                workflow=args.workflow, seed=args.seed, instrumental=not args.vocals,
                caption_extra=args.caption_extra, workflows=load_workflows(ws), lexicon=load_lexicon(ws),
                caption_override=args.caption)
        except KeyError as exc:
            log(f"error: {exc.args[0]}")
            return 2
        print_json(spec)
    elif args.cmd == "set":
        path = ws / "config.json"
        user = read_json(path, {}) or {}
        set_dotted(user, args.key, parse_value(args.value))
        write_json(path, user)
        print_json({"ok": True, "key": args.key, "value": get_dotted(user, args.key), "file": str(path)})
    elif args.cmd == "unset":
        path = ws / "config.json"
        user = read_json(path, {}) or {}
        removed = unset_dotted(user, args.key)
        write_json(path, user)
        print_json({"ok": removed, "key": args.key})
    elif args.cmd == "validate":
        problems = validate(ws)
        print_json({"ok": not problems, "problems": problems})
        return 0 if not problems else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
