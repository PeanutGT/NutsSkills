"""ACE-Step 1.5 worker. Runs INSIDE ACE-Step's own Python environment.

    <ace-python> ace_worker.py --serve              persistent: one JSON request per stdin line
    <ace-python> ace_worker.py --request req.json   one-shot (used by `engine.py generate --direct` and tests)

Requests:  {"op":"generate","job":ID, ...}  {"op":"unload"}  {"op":"ping"}  {"op":"quit"}
Events (stdout, JSON lines, each with "job" when it belongs to one):
    phase {name, pct, detail}   name: loading_models | encoding | diffusing | decoding | writing
    warn {message, code?}       retry {reason, batch_size}
    result {ok, variants, effective, lm_metadata, warnings, elapsed_s}
    error {code, message, hint}
    ready {models_loaded, vram_total_gb, vram_free_gb}     (after start-up and after every job)
Everything else - ACE-Step's and torch's own printing - goes to stderr.

Models stay loaded between jobs and are reloaded only when the model set changes
(DiT checkpoint, quantisation, offload flags, LM). See docs/ARCHITECTURE.md.
"""
from __future__ import annotations

import argparse
import dataclasses
import gc
import inspect
import json
import os
import re
import sys
import threading
import time
import traceback
from pathlib import Path

_REAL_STDOUT = sys.stdout
sys.stdout = sys.stderr  # protect the JSON protocol from stray prints
_EMIT_LOCK = threading.Lock()
CURRENT_JOB: dict = {"id": None}


def emit(event: str, **fields) -> None:
    if CURRENT_JOB["id"] and "job" not in fields:
        fields["job"] = CURRENT_JOB["id"]
    with _EMIT_LOCK:
        _REAL_STDOUT.write(json.dumps({"event": event, **fields}, ensure_ascii=False, default=str) + "\n")
        _REAL_STDOUT.flush()


def log(*a) -> None:
    print(*a, file=sys.stderr, flush=True)


class JobError(Exception):
    def __init__(self, code: str, message: str, hint: str = ""):
        super().__init__(message)
        self.code, self.message, self.hint = code, message, hint


# --------------------------------------------------------------------------- helpers
def normalize_key(key: str | None) -> str:
    """'c minor' / 'Eb major' / 'Am' -> 'C minor' / 'Eb Major' / 'A minor' (ACE keyscale style)."""
    if not key:
        return ""
    m = re.match(r"^\s*([A-Ga-g])\s*([#b♯♭]?)\s*(.*)$", key)
    if not m:
        return key
    letter, acc, rest = m.group(1).upper(), m.group(2).replace("♯", "#").replace("♭", "b"), m.group(3).strip().lower()
    mode = "minor" if rest in ("m", "min", "minor") or rest.startswith("min") else "Major"
    return f"{letter}{acc} {mode}"


DROPPED: list[str] = []


def supported(target, kwargs: dict, label: str) -> dict:
    """Keep only the kwargs `target` (function or dataclass) accepts; remember the rest."""
    if dataclasses.is_dataclass(target):
        names = {f.name for f in dataclasses.fields(target)}
    else:
        sig = inspect.signature(target)
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            return kwargs
        names = set(sig.parameters)
    dropped = sorted(k for k in kwargs if k not in names)
    for k in dropped:
        if f"{label}.{k}" not in DROPPED:
            DROPPED.append(f"{label}.{k}")
            log(f"[{label}] this ACE-Step version ignores: {k}")
    return {k: v for k, v in kwargs.items() if k in names}


def call_ok(result) -> bool:
    """initialize_* helpers return (message, success) in some versions, nothing in others."""
    if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[1], bool):
        return result[1]
    return True


def is_oom(exc: BaseException) -> bool:
    return "out of memory" in str(exc).lower() or exc.__class__.__name__ == "OutOfMemoryError"


# --------------------------------------------------------------------------- phase tracking
PHASE_PATTERNS = [
    ("preprocess_batch", "encoding", None),
    ("Inferring prompt embeddings", "encoding", None),
    ("Generating audio...", "diffusing", None),
    ("DiT diffusion via", "diffusing", None),
    ("Decoding latents with VAE", "decoding", "gpu"),
    ("auto-enabling CPU VAE decode", "decoding", "cpu"),
    ("falling back to CPU VAE decode", "decoding", "cpu"),
    ("falling back to full CPU VAE decode", "decoding", "cpu"),
    ("Moving VAE to CPU for decode", "decoding", "cpu"),
]


class Tracker:
    """Turns ACE-Step's loguru lines + progress callback into phase events."""

    def __init__(self):
        self.phase = None
        self.pct = 0.0
        self.cpu_decode = False
        self.lock = threading.Lock()

    def reset(self):
        with self.lock:
            self.phase, self.pct, self.cpu_decode = None, 0.0, False

    def set_phase(self, name: str, detail: str = "", pct: float | None = None):
        with self.lock:
            if pct is not None:
                self.pct = max(self.pct, pct)
            if name == self.phase and not detail:
                return
            self.phase = name
            p = self.pct
        emit("phase", name=name, pct=round(p, 3), detail=detail)

    def progress(self, value=None, desc=None, *_a, **_k):
        try:
            v = float(value) if value is not None else None
        except (TypeError, ValueError):
            v = None
        if v is not None:
            with self.lock:
                self.pct = max(self.pct, min(0.99, 0.1 + 0.9 * v))  # ACE reports an overall 0-1 value
                p, ph = self.pct, self.phase
            emit("phase", name=ph or "diffusing", pct=round(p, 3), detail=str(desc or ""))

    def on_log(self, text: str):
        for needle, phase, mode in PHASE_PATTERNS:
            if needle in text:
                if mode == "cpu" and not self.cpu_decode:
                    self.cpu_decode = True
                    emit("warn", code="cpu_decode",
                         message="the GPU has no room left for audio decoding, so ACE-Step is decoding on the CPU. "
                                 "This can take many minutes. The next job will move the diffusion model off the GPU first.")
                    self.set_phase("decoding", "cpu")
                elif mode != "cpu":
                    self.set_phase(phase, mode or "")
                return


TRACKER = Tracker()


def install_log_sink() -> None:
    try:
        from loguru import logger
    except Exception:  # noqa: BLE001
        return
    try:
        logger.add(lambda m: TRACKER.on_log(str(m)), level="INFO", format="{message}")
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- session
class Session:
    """Holds the loaded ACE-Step handlers between jobs."""

    def __init__(self):
        self.ace_dir: Path | None = None
        self.torch = None
        self.api = None  # (AceStepHandler, LLMHandler, GenerationParams, GenerationConfig, generate_music)
        self.dit = None
        self.llm = None
        self.key: tuple | None = None
        self.lm_backend_used = None
        self.cpu_decode_seen = False

    # -- environment
    def attach(self, ace_dir: Path) -> None:
        if self.ace_dir == ace_dir and self.api is not None:
            return
        if not ace_dir.is_dir():
            raise JobError("ace_dir", f"ace_step_dir does not exist: {ace_dir}",
                           "Run setup.bat, or: msconfig.py set ace_step_dir \"C:/path/to/ACE-Step-1.5\"")
        if str(ace_dir) not in sys.path:
            sys.path.insert(0, str(ace_dir))
        os.chdir(ace_dir)
        try:
            try:
                import torch
            except ImportError:
                torch = None
            from acestep.handler import AceStepHandler
            from acestep.inference import GenerationConfig, GenerationParams, generate_music
            from acestep.llm_inference import LLMHandler
        except Exception as exc:  # noqa: BLE001
            raise JobError("ace_import", f"cannot import ACE-Step: {exc}",
                           "The worker must run in ACE-Step's environment (<ace_dir>/.venv or `uv run`).")
        self.ace_dir, self.torch = ace_dir, torch
        self.api = (AceStepHandler, LLMHandler, GenerationParams, GenerationConfig, generate_music)
        install_log_sink()

    @property
    def device(self) -> str:
        t = self.torch
        return "cuda" if (t is not None and t.cuda.is_available()) else "cpu"

    def vram(self) -> tuple[float | None, float | None]:
        t = self.torch
        if t is None or not t.cuda.is_available():
            return None, None
        try:
            free, total = t.cuda.mem_get_info()
            return round(total / 1024**3, 2), round(free / 1024**3, 2)
        except Exception:  # noqa: BLE001
            return None, None

    # -- models
    def unload(self) -> None:
        self.dit = self.llm = None
        self.key = None
        self.lm_backend_used = None
        gc.collect()
        try:
            if self.torch is not None and self.torch.cuda.is_available():
                self.torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001
            pass

    def ensure_models(self, plan: dict, ckpt: Path) -> None:
        key = (plan["dit_model"], plan.get("quantization"), bool(plan.get("offload_to_cpu")),
               bool(plan.get("offload_dit_to_cpu")), plan.get("lm_model") if plan.get("thinking") else None,
               str(ckpt))
        if key == self.key and self.dit is not None:
            return
        if self.key is not None:
            emit("warn", code="reload", message="model settings changed; reloading models")
        self.unload()
        AceStepHandler, LLMHandler = self.api[0], self.api[1]
        TRACKER.set_phase("loading_models", plan["dit_model"], 0.02)
        dit = AceStepHandler()
        init = dict(project_root=str(self.ace_dir), config_path=plan["dit_model"], device=self.device,
                    offload_to_cpu=bool(plan.get("offload_to_cpu")),
                    offload_dit_to_cpu=bool(plan.get("offload_dit_to_cpu")))
        if plan.get("quantization"):
            init["quantization"] = plan["quantization"]
        if "use_flash_attention" in plan:
            init["use_flash_attention"] = plan["use_flash_attention"]
        res = dit.initialize_service(**supported(dit.initialize_service, init, "dit"))
        if not call_ok(res):
            raise JobError("dit_init", f"diffusion model failed to initialise: {res}")
        llm = LLMHandler()
        backend_used = None
        if plan.get("thinking") and plan.get("lm_model"):
            TRACKER.set_phase("loading_models", plan["lm_model"], 0.06)
            first = plan.get("lm_backend", "pt")
            for backend in [first] + [b for b in ("pt", "vllm") if b != first]:
                try:
                    res = llm.initialize(**supported(llm.initialize, dict(
                        checkpoint_dir=str(ckpt), lm_model_path=plan["lm_model"], backend=backend,
                        device=self.device), "llm"))
                    if call_ok(res):
                        backend_used = backend
                        break
                    log(f"[llm] backend '{backend}' reported failure: {res}")
                except Exception as exc:  # noqa: BLE001
                    log(f"[llm] backend '{backend}' failed: {exc}")
            if backend_used is None:
                emit("warn", code="no_lm", message="language model could not be loaded; continuing without thinking mode")
                plan["thinking"] = False
                key = key[:4] + (None,) + key[5:]
        self.dit, self.llm, self.key, self.lm_backend_used = dit, llm, key, backend_used


SESSION = Session()


# --------------------------------------------------------------------------- planning
def make_plan(req: dict, installed: list[str], total_gb: float | None, warnings: list[str]) -> dict:
    """Resolve the model set + VRAM guard for one job. Fills only what config did not decide."""
    p = dict(req["params"])
    explicit = set(req.get("explicit_keys") or [])
    dit_model = p["dit_model"]
    if installed and dit_model not in installed:
        fallback = req.get("tier_dit_model")
        if fallback and fallback in installed:
            warnings.append(f"checkpoint '{dit_model}' is not installed; using tier model '{fallback}'")
            dit_model = fallback
        else:
            raise JobError("missing_model", f"checkpoint '{dit_model}' is not installed",
                           f"Installed: {', '.join(installed) or '(none)'}. Run: python scripts/engine.py models --download")
    p["dit_model"] = dit_model
    steps = int(p["inference_steps"])
    if "turbo" in dit_model and steps > 20:
        warnings.append(f"'{dit_model}' is a turbo model (max 20 steps); using 8 steps instead of {steps}")
        steps = 8
    elif "turbo" not in dit_model and steps < 20:
        warnings.append(f"'{dit_model}' is not a turbo model and {steps} steps sounds rough; using 32")
        steps = 32
    p["inference_steps"] = steps
    if p.get("lm_model") and installed and p["lm_model"] not in installed:
        warnings.append(f"LM '{p['lm_model']}' is not installed; thinking mode disabled")
        p["lm_model"], p["thinking"] = None, False
    if not p.get("lm_model"):
        p["thinking"] = False

    # VRAM guard (docs/ARCHITECTURE.md 3.2)
    if req.get("vram_guard", True) and total_gb is not None:
        if total_gb < 8.0 and "offload_dit_to_cpu" not in explicit and not p.get("offload_dit_to_cpu"):
            p["offload_to_cpu"] = True
            p["offload_dit_to_cpu"] = True
            warnings.append(f"{total_gb:.1f} GB card: the diffusion model leaves the GPU before audio decoding")
        if SESSION.cpu_decode_seen:
            if not p.get("offload_dit_to_cpu"):
                p["offload_to_cpu"] = p["offload_dit_to_cpu"] = True
                warnings.append("last job fell back to CPU decoding; moving the diffusion model off the GPU this time")
            if int(p.get("batch_size", 1)) > 1:
                p["batch_size"] = 1
                warnings.append("last job fell back to CPU decoding; generating 1 variant at a time")
    return p


# --------------------------------------------------------------------------- generate
def generate(req: dict) -> dict:
    t0 = time.time()
    warnings: list[str] = list(req.get("warnings", []))
    TRACKER.reset()
    DROPPED.clear()
    SESSION.attach(Path(req["ace_step_dir"]).expanduser().resolve())
    ckpt = Path(req.get("checkpoints_dir") or SESSION.ace_dir / "checkpoints")
    installed = sorted(d.name for d in ckpt.iterdir() if d.is_dir() and not d.name.startswith(".")) if ckpt.is_dir() else []
    total_gb, _ = SESSION.vram()
    plan = make_plan(req, installed, total_gb, warnings)
    if SESSION.device == "cpu":
        warnings.append("CUDA not available: generating on CPU will be very slow")
    for w in warnings:
        emit("warn", message=w)
    warned = set(warnings)

    seeds = [int(s) for s in req["seeds"]][: max(1, int(plan.get("batch_size", 1)))]
    attempt = 0
    while True:
        attempt += 1
        try:
            SESSION.ensure_models(plan, ckpt)
            result = _run_once(req, plan, seeds)
            break
        except JobError:
            raise
        except Exception as exc:  # noqa: BLE001
            log(traceback.format_exc())
            if is_oom(exc) and attempt == 1:
                SESSION.unload()
                plan["offload_to_cpu"] = plan["offload_dit_to_cpu"] = True
                seeds = seeds[:1]
                emit("retry", reason="out of memory", batch_size=1)
                continue
            if is_oom(exc):
                raise JobError("oom", "GPU ran out of memory",
                               "Close other GPU apps (games, browsers with video), shorten the track, or use quality 'draft'.")
            raise JobError("exception", f"{exc.__class__.__name__}: {exc}")

    if TRACKER.cpu_decode:
        SESSION.cpu_decode_seen = True
    if DROPPED:
        emit("warn", code="ignored", message="your ACE-Step version does not know these settings, so they had NO effect: " + ", ".join(DROPPED))
    out_dir = Path(req["out_dir"])
    TRACKER.set_phase("writing", "", 0.99)
    variants = []
    for i, audio in enumerate(result.audios, start=1):
        src = Path(audio["path"])
        dst = out_dir / f"v{i}{src.suffix}"
        if src.resolve() != dst.resolve():
            src.replace(dst)
        seed = (audio.get("params") or {}).get("seed", seeds[min(i - 1, len(seeds) - 1)])
        variants.append({"index": i, "file": dst.name, "seed": seed, "sample_rate": audio.get("sample_rate", 48000)})
    extra = getattr(result, "extra_outputs", None) or {}
    total_gb, free_gb = SESSION.vram()
    return {"ok": True, "variants": variants, "warnings": warnings,
            "effective": {"dit_model": plan["dit_model"], "lm_model": plan.get("lm_model") if plan.get("thinking") else None,
                          "lm_backend": SESSION.lm_backend_used, "thinking": bool(plan.get("thinking")),
                          "device": SESSION.device, "inference_steps": plan["inference_steps"],
                          "shift": float(plan.get("shift", 3.0)), "quantization": plan.get("quantization"),
                          "offload_to_cpu": bool(plan.get("offload_to_cpu")),
                          "offload_dit_to_cpu": bool(plan.get("offload_dit_to_cpu")),
                          "batch_size": len(seeds), "vram_gb": total_gb, "cpu_decode": TRACKER.cpu_decode,
                          "ignored_settings": list(DROPPED)},
            "lm_metadata": extra.get("lm_metadata"), "time_costs": extra.get("time_costs"),
            "elapsed_s": round(time.time() - t0, 1)}


def _run_once(req: dict, plan: dict, seeds: list[int]):
    GenerationParams, GenerationConfig, generate_music = SESSION.api[2], SESSION.api[3], SESSION.api[4]
    instrumental = bool(req.get("instrumental", True))
    gp = dict(
        task_type="text2music", caption=req["caption"],
        lyrics="[Instrumental]" if instrumental else req.get("lyrics", ""),
        instrumental=instrumental, vocal_language="unknown",
        bpm=int(req["bpm"]) if req.get("bpm") else None, keyscale=normalize_key(req.get("key")),
        timesignature=str(req.get("time_signature") or ""), duration=float(plan["duration"]),
        inference_steps=int(plan["inference_steps"]), guidance_scale=float(plan.get("guidance_scale", 7.0)),
        shift=float(plan.get("shift", 3.0)), thinking=bool(plan.get("thinking")), seed=seeds[0])
    for knob in ("lm_temperature", "lm_cfg_scale", "lm_top_k", "lm_top_p", "use_cot_metas", "use_cot_caption",
                 "use_cot_language", "infer_method", "use_adg", "cfg_interval_start", "cfg_interval_end"):
        if plan.get(knob) is not None:
            gp[knob] = plan[knob]
    gc_kwargs = dict(batch_size=len(seeds), seeds=seeds, use_random_seed=False, audio_format=plan.get("audio_format", "flac"))
    params = GenerationParams(**supported(GenerationParams, gp, "params"))
    config = GenerationConfig(**supported(GenerationConfig, gc_kwargs, "config"))
    out_dir = Path(req["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    TRACKER.set_phase("encoding", "", 0.1)
    result = generate_music(SESSION.dit, SESSION.llm, params, config, save_dir=str(out_dir), progress=TRACKER.progress)
    if not getattr(result, "success", False):
        err = str(getattr(result, "error", None) or "generation failed")
        if "out of memory" in err.lower():
            raise RuntimeError("CUDA out of memory: " + err)
        raise JobError("generate", err)
    return result


def run_job(req: dict) -> bool:
    CURRENT_JOB["id"] = req.get("job")
    try:
        res = generate(req)
        emit("result", **res)
        return True
    except JobError as exc:
        emit("error", code=exc.code, message=exc.message, hint=exc.hint)
        return False
    except Exception as exc:  # noqa: BLE001
        log(traceback.format_exc())
        emit("error", code="exception", message=f"{exc.__class__.__name__}: {exc}")
        return False
    finally:
        CURRENT_JOB["id"] = None
        try:
            if SESSION.torch is not None and SESSION.torch.cuda.is_available():
                SESSION.torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001
            pass


def ready() -> None:
    total, free = SESSION.vram()
    emit("ready", models_loaded=SESSION.key is not None, model=SESSION.key[0] if SESSION.key else None,
         vram_total_gb=total, vram_free_gb=free)


def serve() -> int:
    emit("ready", models_loaded=False)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            emit("error", code="bad_request", message="not JSON")
            continue
        op = req.get("op", "generate")
        if op == "quit":
            break
        if op == "ping":
            ready()
        elif op == "unload":
            SESSION.unload()
            ready()
        elif op == "generate":
            run_job(req)
            ready()
        else:
            emit("error", code="bad_request", message=f"unknown op {op!r}")
    SESSION.unload()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--serve", action="store_true")
    g.add_argument("--request")
    args = ap.parse_args()
    if args.serve:
        return serve()
    req = json.loads(Path(args.request).read_text(encoding="utf-8"))
    return 0 if run_job(req) else 1


if __name__ == "__main__":
    sys.exit(main())
