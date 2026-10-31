"""One generation job from spec to finished take, independent of who runs the engine.

    ctx = prepare(spec, engine=None)     resolve params, create the take folder, build the worker request
    result = run_mock(ctx, emit)          (mock engine)   - or send ctx["request"] to ace_worker
    meta = finish(ctx, result)            write meta.json -> the take now exists in the library
    discard(ctx, reason)                  failed / cancelled: move the folder to trash, never a half take

Used by the server's job queue and by `engine.py generate --direct`.
"""
from __future__ import annotations

import random
import shutil
import subprocess
import time
from pathlib import Path

import engine_mock
import gpu
import msconfig
from common import ensure_workspace, read_json, slugify, timestamp_id, write_json


def make_seeds(base, n: int) -> list[int]:
    if base is None or int(base) < 0:
        rng = random.SystemRandom()
        return [rng.randint(1, 2**31 - 1) for _ in range(n)]
    return [int(base) + i for i in range(n)]


def checkpoints_dir(cfg: dict, ace_dir: Path) -> Path:
    import os
    custom = cfg.get("ace_checkpoints_dir") or os.environ.get("ACESTEP_CHECKPOINTS_DIR")
    return Path(custom).expanduser() if custom else ace_dir / "checkpoints"


def _has_key(d, key: str) -> bool:
    if isinstance(d, dict):
        return key in d or any(_has_key(v, key) for v in d.values())
    return False


def prepare(spec: dict, engine: str | None = None, job_id: str | None = None, ws: Path | None = None) -> dict:
    ws = ensure_workspace(ws)
    cfg, _ = msconfig.load_config(ws)
    engine = engine or spec.get("engine") or cfg["engine"]
    if engine not in ("ace", "mock"):
        raise ValueError(f"unknown engine {engine!r}")
    tier = None
    if engine == "mock" and cfg["hardware"]["tier"] == "auto" and not gpu.detect()["available"]:
        tier = "high"  # no GPU in a test sandbox: do not clamp mock runs to the 'low' caps
    overrides = {"duration": spec.get("duration"), "batch_size": spec.get("variants"),
                 "instrumental": spec.get("instrumental"), **(spec.get("engine_params") or {})}
    res = msconfig.resolve_params(cfg, spec.get("quality"), overrides, tier=tier)
    params = res["params"]
    warnings = list(res["warnings"]) + list(spec.get("warnings", []))

    title = spec.get("title") or spec.get("style") or "track"
    take_id = timestamp_id(slugify(title))
    out_root = ws / cfg["output"]["dir"]
    out_dir, n = out_root / take_id, 2
    while out_dir.exists():
        out_dir, n = out_root / f"{take_id}-{n}", n + 1
    out_dir.mkdir(parents=True)
    write_json(out_dir / "spec.json", spec)

    seeds = make_seeds(spec.get("seed", -1), int(params.get("batch_size", 1)))
    user_cfg = read_json(ws / "config.json", {}) or {}
    ctx = {"job": job_id, "ws": str(ws), "engine": engine, "spec": spec, "title": title, "take_id": out_dir.name,
           "out_dir": str(out_dir), "tier": res["tier"], "quality": res["quality"], "params": params,
           "warnings": warnings, "seeds": seeds, "t0": time.time(), "request": None}
    if engine == "ace":
        ace = cfg.get("ace_step_dir", "CHANGE_ME")
        if ace == "CHANGE_ME" or not Path(ace).expanduser().is_dir():
            discard(ctx, "ace_step_dir missing")
            raise FileNotFoundError(f"ace_step_dir is not set or missing ({ace}). Run setup.bat, or "
                                    "msconfig.py set ace_step_dir \"C:/path/to/ACE-Step-1.5\"")
        ctx["ace_dir"] = str(Path(ace).expanduser())
        ctx["request"] = {
            "op": "generate", "job": job_id, "ace_step_dir": ace,
            "checkpoints_dir": str(checkpoints_dir(cfg, Path(ace).expanduser())),
            "params": params, "tier_dit_model": cfg["hardware"]["tiers"].get(res["tier"], {}).get("dit_model"),
            "explicit_keys": [k for k in ("offload_dit_to_cpu",) if _has_key(user_cfg, k)],
            "vram_guard": cfg.get("engine_vram_guard", True),
            "caption": spec["caption"], "bpm": spec.get("bpm"), "key": spec.get("key"),
            "time_signature": spec.get("time_signature"), "instrumental": params.get("instrumental", True),
            "lyrics": spec.get("lyrics", ""), "seeds": seeds, "out_dir": str(out_dir), "warnings": warnings}
    return ctx


def run_mock(ctx: dict, emit) -> dict:
    """Mock engine with the same event vocabulary as ace_worker (phase / result)."""
    emit("phase", name="loading_models", pct=0.02, detail="mock")
    emit("phase", name="encoding", pct=0.08, detail="")

    def prog(frac, desc):
        emit("phase", name="diffusing", pct=round(0.1 + 0.8 * frac, 3), detail=desc)
    variants = engine_mock.generate(ctx["spec"], ctx["params"], ctx["seeds"], Path(ctx["out_dir"]), emit_progress=prog)
    emit("phase", name="writing", pct=0.97, detail="")
    return {"ok": True, "variants": variants, "warnings": [],
            "effective": {"engine": "mock", "dit_model": "mock", "inference_steps": ctx["params"].get("inference_steps"),
                          "thinking": False, "batch_size": len(variants)},
            "lm_metadata": {"bpm": ctx["spec"].get("bpm"), "keyscale": ctx["spec"].get("key"), "note": "mock engine"}}


def finish(ctx: dict, result: dict) -> dict:
    cfg, _ = msconfig.load_config(Path(ctx["ws"]))
    out_dir = Path(ctx["out_dir"])
    variants = result["variants"]
    warnings = list(ctx["warnings"]) + [w for w in result.get("warnings", []) if w not in ctx["warnings"]]
    want = ctx["params"].get("audio_format", "flac")
    if ctx["engine"] == "mock" and want != "wav":
        ffmpeg = shutil.which(cfg["ffmpeg"])
        if ffmpeg:
            for v in variants:
                src = out_dir / v["file"]
                dst = src.with_suffix("." + want)
                try:
                    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(src), str(dst)], check=True)
                    src.unlink()
                    v["file"] = dst.name
                except (subprocess.CalledProcessError, OSError) as exc:
                    warnings.append(f"could not convert mock audio to {want}: {exc}")
    try:  # automatic check of every variant; a failure here never loses the take
        import postprocess
        loopable = bool(ctx["spec"].get("loopable"))
        for v in variants:
            v["qc"] = postprocess.inspect_file(out_dir / v["file"], cfg, loopable)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"automatic audio check skipped: {exc}")
    meta = {"id": ctx["take_id"], "title": ctx["title"], "spec": ctx["spec"], "engine": ctx["engine"],
            "tier": ctx["tier"], "quality": ctx["quality"], "params": ctx["params"], "warnings": warnings,
            "effective": result.get("effective"), "lm_metadata": result.get("lm_metadata"),
            "time_costs": result.get("time_costs"), "job": ctx.get("job"),
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "elapsed_s": round(time.time() - ctx["t0"], 1),
            "variants": variants}
    write_json(out_dir / "meta.json", meta)
    return meta


def discard(ctx: dict, reason: str) -> None:
    """Failed or cancelled: keep nothing that looks like a take. The folder goes to trash for debugging."""
    out_dir = Path(ctx["out_dir"])
    if not out_dir.exists():
        return
    write_json(out_dir / "failed.json", {"reason": reason, "job": ctx.get("job"),
                                         "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    trash = Path(ctx["ws"]) / "trash"
    trash.mkdir(exist_ok=True)
    dst = trash / out_dir.name
    n = 2
    while dst.exists():
        dst, n = trash / f"{out_dir.name}-{n}", n + 1
    try:
        out_dir.replace(dst)
    except OSError:
        shutil.move(str(out_dir), str(dst))


def sweep_orphans(ws: Path | None = None) -> list[str]:
    """Take folders without meta.json left by crashes of older versions -> trash."""
    ws = ensure_workspace(ws)
    cfg, _ = msconfig.load_config(ws)
    root = ws / cfg["output"]["dir"]
    moved = []
    if root.is_dir():
        for d in root.iterdir():
            if d.is_dir() and not (d / "meta.json").exists() and time.time() - d.stat().st_mtime > 120:
                discard({"out_dir": str(d), "ws": str(ws), "job": None}, "orphan: no meta.json")
                moved.append(d.name)
    return moved
