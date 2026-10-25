"""Generation front-end: environment check and track generation.

    engine.py check                         verify ffmpeg / GPU / ACE-Step install
    engine.py generate --spec spec.json     generate variants for one track spec ('-' = stdin)

`generate` streams JSON lines on stdout:
    {"event":"start", ...}  {"event":"progress","pct":0.4,"desc":"..."}
    {"event":"warn","message":"..."}  {"event":"retry", ...}
    {"event":"result","ok":true,"id":...,"dir":...,"variants":[...]}   |   {"event":"error",...}
A track spec is what `msconfig.py plan` prints.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import engine_mock
import gpu
import msconfig
from common import (SKILL_DIR, emit, ensure_workspace, log, print_json, read_json, slugify,
                    timestamp_id, write_json)

ACE_RUNNER = SKILL_DIR / "scripts" / "engine_ace.py"


# --------------------------------------------------------------------------- helpers
def find_exe(name: str) -> str | None:
    return shutil.which(name)


from jobs import find_ace_python  # noqa: E402  (single definition shared with the server)


def checkpoints_dir(cfg: dict, ace_dir: Path) -> Path:
    """ACE-Step keeps models in <ace_dir>/checkpoints unless ACESTEP_CHECKPOINTS_DIR / config says otherwise."""
    import os
    custom = cfg.get("ace_checkpoints_dir") or os.environ.get("ACESTEP_CHECKPOINTS_DIR")
    return Path(custom).expanduser() if custom else ace_dir / "checkpoints"


MAIN_MODEL_PARTS = ("acestep-v15-turbo", "acestep-5Hz-lm-1.7B", "vae", "Qwen3-Embedding-0.6B")  # shipped by the main download


def needed_models(cfg: dict, tier: str) -> list[str]:
    """Checkpoints this tier's presets would load (preset models only count if a preset names one)."""
    t = cfg["hardware"]["tiers"][tier]
    need = [t["dit_model"], "vae", "Qwen3-Embedding-0.6B"]
    if t.get("lm_model"):
        need.append(t["lm_model"])
    return list(dict.fromkeys(need))


def download_args(name: str) -> list[str]:
    return [] if name in MAIN_MODEL_PARTS else ["--model", name]


def make_seeds(base: int, n: int) -> list[int]:
    if base is None or base < 0:
        rng = random.SystemRandom()
        return [rng.randint(1, 2**31 - 1) for _ in range(n)]
    return [base + i for i in range(n)]


def convert_audio(src: Path, dst: Path, ffmpeg: str) -> None:
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(src), str(dst)], check=True)


# --------------------------------------------------------------------------- check
def cmd_check(_args) -> int:
    cfg, _ = msconfig.load_config()
    problems: list[str] = []
    out: dict = {}

    for key in ("ffmpeg", "ffprobe"):
        exe = find_exe(cfg[key])
        out[key] = {"ok": bool(exe), "path": exe}
        if not exe:
            problems.append(f"{cfg[key]} not found on PATH (winget install Gyan.FFmpeg, then reopen the terminal)")

    info = gpu.describe()
    tier, _ = msconfig.resolve_tier(cfg)
    out["gpu"] = info
    out["tier"] = tier
    out["tier_params"] = cfg["hardware"]["tiers"].get(tier)
    if not info["available"]:
        problems.append("no NVIDIA GPU detected - use engine 'mock' for testing, or fix the driver")

    ace = cfg.get("ace_step_dir", "CHANGE_ME")
    ace_info: dict = {"configured": ace}
    if ace == "CHANGE_ME":
        problems.append("ace_step_dir not set (run scripts/setup_windows.ps1)")
    else:
        p = Path(ace).expanduser()
        ace_info["exists"] = p.is_dir()
        if p.is_dir():
            ckpt = checkpoints_dir(cfg, p)
            installed = sorted(d.name for d in ckpt.iterdir() if d.is_dir() and not d.name.startswith('.')) if ckpt.is_dir() else []
            ace_info["checkpoints"] = installed
            ace_info["python"] = find_ace_python(p)
            need = needed_models(cfg, tier)
            ace_info["checkpoints_dir"] = str(ckpt)
            ace_info["missing_for_tier"] = [m for m in need if m not in installed]
            preset_models = sorted({pr["dit_model"] for pr in cfg["quality"]["presets"].values() if pr.get("dit_model")})
            ace_info["optional_missing"] = [m for m in preset_models if m not in installed]
            if not installed:
                problems.append("no checkpoints found - run: python scripts/engine.py models --download")
            elif ace_info["missing_for_tier"]:
                problems.append("models for this tier are not installed: " + ", ".join(ace_info["missing_for_tier"]) +
                                "  (fix: python scripts/engine.py models --download)")
            if ace_info["optional_missing"]:
                out.setdefault("notes", []).append(
                    "quality presets 'high'/'max' use " + ", ".join(ace_info["optional_missing"]) +
                    " which is not installed - they will fall back to the fast turbo model. "
                    "Install with: python scripts/engine.py models --download " + ",".join(ace_info["optional_missing"]))
            if not ace_info["python"]:
                problems.append("no Python found for ACE-Step (no .venv and no `uv`)")
        else:
            problems.append(f"ace_step_dir does not exist: {ace}")
    out["ace_step"] = ace_info

    cfg_problems = msconfig.validate()
    out["config_problems"] = cfg_problems
    out["problems"] = problems
    out["ok"] = not problems
    print_json(out)
    return 0 if not problems else 1


def cmd_models(args) -> int:
    cfg, _ = msconfig.load_config()
    ace = cfg.get("ace_step_dir", "CHANGE_ME")
    if ace == "CHANGE_ME" or not Path(ace).expanduser().is_dir():
        emit("error", code="ace_dir", message="ace_step_dir is not set; run scripts/setup_windows.ps1 first")
        return 1
    ace_dir = Path(ace).expanduser()
    tier, _ = msconfig.resolve_tier(cfg)
    ckpt = checkpoints_dir(cfg, ace_dir)
    installed = sorted(d.name for d in ckpt.iterdir() if d.is_dir() and not d.name.startswith('.')) if ckpt.is_dir() else []
    preset_models = sorted({pr["dit_model"] for pr in cfg["quality"]["presets"].values() if pr.get("dit_model")})
    wanted = [m for m in (args.download.split(",") if args.download else []) if m]
    if args.download is not None and not wanted:
        wanted = [m for m in needed_models(cfg, tier) if m not in installed]
    if args.download is None:
        print_json({"tier": tier, "checkpoints_dir": str(ckpt), "installed": installed,
                    "needed_for_tier": needed_models(cfg, tier),
                    "missing": [m for m in needed_models(cfg, tier) if m not in installed],
                    "optional_quality_models": preset_models,
                    "download": "python scripts/engine.py models --download [name,name]  (no name = what this tier needs)"})
        return 0
    py = find_ace_python(ace_dir)
    if not py:
        emit("error", code="no_python", message="cannot find ACE-Step's Python (.venv or uv)")
        return 1
    ok = True
    main_done = False
    for name in wanted:
        extra = download_args(name)
        if not extra and main_done:
            continue
        main_done = main_done or not extra
        emit("progress", desc=f"downloading {name if extra else 'main model (turbo, VAE, text encoder, LM 1.7B)'} - several GB, please wait")
        cmd = py + ["-m", "acestep.model_downloader", *extra]
        log("[models] " + " ".join(cmd))
        rc = subprocess.call(cmd, cwd=str(ace_dir))
        if rc != 0:
            ok = False
            emit("error", code="download_failed", message=f"download of {name} failed (exit {rc})",
                 hint="Check your internet connection; for China try ACESTEP_DOWNLOAD_SOURCE=modelscope. Re-running resumes.")
    after = sorted(d.name for d in ckpt.iterdir() if d.is_dir() and not d.name.startswith('.')) if ckpt.is_dir() else []
    emit("result", ok=ok, installed=after, missing=[m for m in needed_models(cfg, tier) if m not in after])
    return 0 if ok else 1


# --------------------------------------------------------------------------- generate
def cmd_generate(args) -> int:
    """Direct, one-shot generation (no server, no persistent worker). Claude normally uses msclient.py;
    this path exists for tests and as a fallback."""
    import pipeline
    spec = json.load(sys.stdin) if args.spec == "-" else json.loads(Path(args.spec).read_text(encoding="utf-8"))
    try:
        ctx = pipeline.prepare(spec, engine=args.engine)
    except (ValueError, FileNotFoundError) as exc:
        emit("error", code="prepare", message=str(exc))
        return 1
    emit("start", id=ctx["take_id"], dir=ctx["out_dir"], engine=ctx["engine"], tier=ctx["tier"],
         quality=ctx["quality"], params=ctx["params"], warnings=ctx["warnings"])
    if ctx["engine"] == "mock":
        try:
            result = pipeline.run_mock(ctx, emit)
        except Exception as exc:  # noqa: BLE001
            pipeline.discard(ctx, str(exc))
            emit("error", code="mock_failed", message=str(exc))
            return 1
    else:
        py = find_ace_python(Path(ctx["ace_dir"]))
        if not py:
            pipeline.discard(ctx, "no ACE python")
            emit("error", code="no_python", message="cannot find ACE-Step's Python (.venv or uv)",
                 hint="Install uv (winget install astral-sh.uv) or run setup.bat")
            return 1
        result = None
        with tempfile.TemporaryDirectory(prefix="msace_") as tmp:
            req_path = Path(tmp) / "request.json"
            write_json(req_path, ctx["request"])
            cmd = py + [str(SKILL_DIR / "scripts" / "ace_worker.py"), "--request", str(req_path)]
            log("[engine] " + " ".join(cmd))
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=None, text=True, encoding="utf-8",
                                    errors="replace", cwd=ctx["ace_dir"])
            for line in proc.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                ev.pop("job", None)
                if ev.get("event") == "result":
                    result = ev
                elif ev.get("event") == "error":
                    pipeline.discard(ctx, ev.get("message", "error"))
                    emit(**ev)
                    proc.wait()
                    return 1
                elif ev.get("event") not in ("ready",):
                    emit(**ev)
            code = proc.wait()
        if result is None:
            pipeline.discard(ctx, f"runner exited {code}")
            emit("error", code="engine_crashed", message=f"ACE-Step runner exited with code {code} without a result",
                 hint="Run `python scripts/engine.py check` and read the log above.")
            return 1
    meta = pipeline.finish(ctx, result)
    emit("result", ok=True, id=meta["id"], dir=ctx["out_dir"], variants=meta["variants"], warnings=meta["warnings"],
         effective=meta.get("effective"), elapsed_s=meta["elapsed_s"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    m = sub.add_parser("models", help="list / download ACE-Step model checkpoints")
    m.add_argument("--download", nargs="?", const="", default=None,
                   help="download names (comma separated); with no value, downloads what this hardware tier needs")
    g = sub.add_parser("generate")
    g.add_argument("--spec", required=True, help="path to a track spec JSON, or - for stdin")
    g.add_argument("--engine", choices=("ace", "mock"), help="override config engine for this run")
    g.add_argument("--direct", action="store_true", help="accepted for clarity; this command is always direct")
    args = ap.parse_args(argv)
    return {"check": cmd_check, "models": cmd_models}.get(args.cmd, cmd_generate)(args)


if __name__ == "__main__":
    sys.exit(main())
