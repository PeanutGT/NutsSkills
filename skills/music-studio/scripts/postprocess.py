"""Post-processing: trim / fit / fade / seamless loop / loudness / export + QC.

    postprocess.py analyze FILE
    postprocess.py run --take ID [--variant N] [--workflow ID] [--steps steps.json] [--name NAME] [--preview]
    postprocess.py op OPNAME IN OUT [--param key=value ...]

Design: audio is decoded once with ffmpeg into float32 numpy, processed in
memory, and only encoded at the `export` step, so chained steps never
accumulate lossy-codec damage. Loudness uses ffmpeg's two-pass `loudnorm`
(EBU R128 / ITU BS.1770), which is the standard, well-tested implementation.

Step vocabulary (what a workflow's postprocess.steps may contain):
    {"op":"trim_silence", "threshold_db":-50, "keep_tail":0.05}
    {"op":"fit", "duration": 90 | "spec", "snap":"none"|"bars"}
    {"op":"fade", "in":0.0, "out":2.0}
    {"op":"loop", "crossfade":2.0, "snap_bars":true}
    {"op":"loudnorm", "target_lufs":-16, "true_peak_db":-1.5}
    {"op":"export", "formats":["flac","ogg"]}
Any step may carry  "when": "loopable" | "not_loopable"  to run only for loopable / non-loopable styles.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

import library
import msconfig
from common import log, print_json, read_json, write_json, workspace_dir

SR_DEFAULT = 48000
CODECS = {
    "wav": ["-c:a", "pcm_s16le"],
    "wav24": ["-c:a", "pcm_s24le"],
    "flac": ["-c:a", "flac", "-compression_level", "8", "-sample_fmt", "s32", "-bits_per_raw_sample", "24"],
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
    "opus": ["-c:a", "libopus", "-b:a", "160k"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
}
EXT = {"wav24": "wav"}


class PostError(RuntimeError):
    pass


def _bin(cfg: dict, key: str) -> str:
    exe = shutil.which(cfg[key])
    if not exe:
        raise PostError(f"{cfg[key]} not found on PATH (winget install Gyan.FFmpeg)")
    return exe


# --------------------------------------------------------------------------- audio io
def decode(path: Path, cfg: dict, sr: int) -> np.ndarray:
    cmd = [_bin(cfg, "ffmpeg"), "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise PostError(f"could not decode {path.name}: {proc.stderr.decode(errors='replace')[:300]}")
    return np.frombuffer(proc.stdout, dtype="<f4").reshape(-1, 2).copy()


def encode(x: np.ndarray, sr: int, out: Path, cfg: dict, codec_args: list[str], metadata: dict | None = None) -> None:
    cmd = [_bin(cfg, "ffmpeg"), "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-"]
    for k, v in (metadata or {}).items():
        cmd += ["-metadata", f"{k}={v}"]
    cmd += codec_args + [str(out)]
    proc = subprocess.run(cmd, input=np.ascontiguousarray(x, dtype="<f4").tobytes(), capture_output=True)
    if proc.returncode != 0:
        raise PostError(f"encode to {out.name} failed: {proc.stderr.decode(errors='replace')[:300]}")


# --------------------------------------------------------------------------- measurements
def _loudnorm_json(path: Path, cfg: dict, target: float, tp: float) -> dict:
    cmd = [_bin(cfg, "ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-af",
           f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    blocks = re.findall(r"\{[^{}]*\}", proc.stderr, flags=re.S)
    if not blocks:
        raise PostError("loudness measurement produced no result")
    return json.loads(blocks[-1])


def _num(v) -> float | None:
    try:
        f = float(v)
        return None if math.isinf(f) or math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def seam_metrics(x: np.ndarray, sr: int, bar: int | None = None) -> dict:
    """How audible would the wrap-around be if this file were looped?

    click_ratio     : jump between the last and first sample vs. the typical sample-to-sample
                      step (~1 = inaudible, >>5 = a click).
    level_jump_db   : loudness difference between the last and the first second.
    typical_step_db : how much loudness moves across ordinary musical boundaries elsewhere in
                      the track. With a known tempo (`bar` = samples per bar) these are the
                      interior bar lines - the right comparison, because a loop seam is a bar
                      line and bars always start louder than they end. Without a tempo it
                      falls back to neighbouring one-second windows.
    seam_vs_typical : level_jump_db / typical_step_db. ~1 means the seam is as natural as any
                      bar line in the piece; >>3 means a faded-out end meeting a fresh start.
    Heuristics only - always audition a loop.
    """
    w = int(1.0 * sr)
    if bar:
        w = min(w, bar // 2)
    empty = {"click_ratio": None, "level_jump_db": None, "typical_step_db": None, "seam_vs_typical": None}
    if len(x) < 4 * w or w < sr // 20:
        return empty
    step = float(np.mean(np.abs(np.diff(x, axis=0)))) or 1e-9
    jump = float(np.mean(np.abs(x[0] - x[-1])))
    db = lambda seg: 20 * math.log10(float(np.sqrt(np.mean(seg ** 2))) + 1e-9)  # noqa: E731
    if bar and len(x) >= 3 * bar:
        steps = [abs(db(x[b - w:b]) - db(x[b:b + w])) for b in range(bar, len(x) - w, bar)]
    else:
        levels = [db(x[i * w:(i + 1) * w]) for i in range(len(x) // w)]
        steps = [abs(levels[i + 1] - levels[i]) for i in range(len(levels) - 1)]
    typical = max(float(np.median(steps)) if steps else 0.5, 0.5)
    seam_db = abs(db(x[:w]) - db(x[-w:]))
    return {"click_ratio": round(jump / step, 2), "level_jump_db": round(seam_db, 2),
            "typical_step_db": round(typical, 2), "seam_vs_typical": round(seam_db / typical, 2)}


def analyze_array(x: np.ndarray, sr: int, path: Path | None, cfg: dict, lufs_target: float, tp_target: float,
                  bar: int | None = None) -> dict:
    out: dict = {"duration": round(len(x) / sr, 3), "sample_rate": sr}
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    out["peak_dbfs"] = round(20 * math.log10(peak), 2) if peak > 0 else None
    out["clipped_samples"] = int(np.sum(np.abs(x) >= 0.999))
    out["dc_offset"] = round(float(np.mean(x)), 5)
    env = np.max(np.abs(x), axis=1) if len(x) else np.zeros(1)
    loud = np.nonzero(env > 10 ** (-50 / 20))[0]
    out["head_silence_s"] = round(float(loud[0]) / sr, 2) if len(loud) else None
    out["tail_silence_s"] = round(float(len(x) - 1 - loud[-1]) / sr, 2) if len(loud) else None
    out["seam"] = seam_metrics(x, sr, bar)
    if path is not None:
        try:
            m = _loudnorm_json(path, cfg, lufs_target, tp_target)
            out["lufs"] = _num(m.get("input_i"))
            out["true_peak_db"] = _num(m.get("input_tp"))
            out["lra"] = _num(m.get("input_lra"))
        except PostError as exc:
            out["loudness_error"] = str(exc)
    return out


def qc(report: dict, cfg: dict, expected_duration: float | None = None, looped: bool = False) -> list[str]:
    pp = cfg["postprocess"]
    notes: list[str] = []
    if report.get("lufs") is not None and abs(report["lufs"] - pp["loudness_lufs"]) > 1.0:
        notes.append(f"loudness {report['lufs']:.1f} LUFS is off target {pp['loudness_lufs']}")
    if report.get("true_peak_db") is not None and report["true_peak_db"] > pp["true_peak_db"] + 0.2:
        notes.append(f"true peak {report['true_peak_db']:.1f} dB above ceiling {pp['true_peak_db']}")
    if report.get("clipped_samples", 0) > 0:
        notes.append(f"{report['clipped_samples']} clipped samples")
    if (report.get("head_silence_s") or 0) > 1.0:
        notes.append(f"{report['head_silence_s']}s of silence at the start")
    if (report.get("tail_silence_s") or 0) > 3.0:
        notes.append(f"{report['tail_silence_s']}s of silence at the end")
    if expected_duration and abs(report["duration"] - expected_duration) > 0.5:
        notes.append(f"duration {report['duration']}s differs from the requested {expected_duration}s")
    if abs(report.get("dc_offset", 0)) > 0.01:
        notes.append("noticeable DC offset")
    seam = report.get("seam") or {}
    if looped and seam.get("click_ratio") is not None:
        if seam["click_ratio"] > 4:
            notes.append(f"loop seam may click (click_ratio {seam['click_ratio']}); audition the loop preview")
        if seam["seam_vs_typical"] > 4:
            notes.append(f"loop seam changes level {seam['seam_vs_typical']}x more than the music does; audition it")
    return notes


# --------------------------------------------------------------------------- operations
def op_trim_silence(x, sr, p, ctx):
    thr = 10 ** (float(p.get("threshold_db", -50)) / 20)
    env = np.max(np.abs(x), axis=1)
    idx = np.nonzero(env > thr)[0]
    if not len(idx):
        ctx["warnings"].append("trim_silence: file is silent, left unchanged")
        return x
    start = max(0, int(idx[0]) - int(float(p.get("keep_head", 0.0)) * sr))
    end = min(len(x), int(idx[-1]) + 1 + int(float(p.get("keep_tail", 0.05)) * sr))
    return x[start:end]


def _bar_samples(ctx, sr) -> int | None:
    bpm = ctx.get("bpm")
    if not bpm:
        return None
    return int(round(60.0 / float(bpm) * int(ctx.get("beats_per_bar", 4)) * sr))


def op_fit(x, sr, p, ctx):
    dur = p.get("duration", "spec")
    dur = ctx.get("duration") if dur == "spec" else dur
    if not dur:
        ctx["warnings"].append("fit: no target duration known, skipped")
        return x
    n = int(float(dur) * sr)
    if p.get("snap") == "bars":
        bar = _bar_samples(ctx, sr)
        if bar:
            n = max(bar, (n // bar) * bar)
        else:
            ctx["warnings"].append("fit: snap=bars needs a bpm, cutting at the exact duration instead")
    if len(x) < n:
        ctx["warnings"].append(f"fit: track is {len(x) / sr:.1f}s, shorter than {n / sr:.1f}s; not extended")
        return x
    return x[:n]


def op_fade(x, sr, p, ctx):
    x = x.copy()
    fin, fout = int(float(p.get("in", 0)) * sr), int(float(p.get("out", 0)) * sr)
    if fin > 0:
        fin = min(fin, len(x))
        x[:fin] *= np.sin(np.linspace(0, np.pi / 2, fin))[:, None]
    if fout > 0:
        fout = min(fout, len(x))
        x[-fout:] *= np.cos(np.linspace(0, np.pi / 2, fout))[:, None]
    return x


def op_loop(x, sr, p, ctx):
    """Make the file loop seamlessly by folding its tail back over its head.

    Take segment S = x[:L+X]. Output = S[:L] with its first X samples replaced by
    head*fade_in + tail*fade_out (equal-power), where tail = S[L:L+X]. When the player
    wraps from the end to the start, the last sample (S[L-1]) is followed by a signal that
    begins exactly at S[L] - the natural continuation - so there is no discontinuity.
    """
    X = int(float(p.get("crossfade", ctx["cfg"]["postprocess"]["loop_crossfade"])) * sr)
    n = len(x)
    if n < 6 * X or X <= 0:
        ctx["warnings"].append("loop: track too short for that crossfade; skipped")
        return x
    L = n - X
    if p.get("snap_bars", True):
        bar = _bar_samples(ctx, sr)
        if bar and L >= bar:
            L = (L // bar) * bar
            ctx["notes"].append(f"loop length snapped to {L // bar} bars")
        elif not bar:
            ctx["notes"].append("loop: no bpm known, length not snapped to bars")
    seg = x[: L + X]
    body, tail = seg[:L].copy(), seg[L:L + X]
    # Crossfade law depends on how alike the two overlapped passages are. Uncorrelated material
    # (evolving pads) needs equal-POWER gains (sin/cos) to keep a constant level. Identical or
    # repeating material (loop-based drums, arps - most game/lo-fi music) adds coherently, so
    # equal-POWER gains would bump the level by up to 3 dB; it needs equal-GAIN (linear) fades.
    a, b = body[:X].mean(axis=1), tail.mean(axis=1)
    corr = float(np.clip(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12), 0.0, 1.0))
    u = np.linspace(0.0, 1.0, X)[:, None]
    g_in = (1 - corr) * np.sin(u * np.pi / 2) + corr * u
    g_out = (1 - corr) * np.cos(u * np.pi / 2) + corr * (1 - u)
    body[:X] = body[:X] * g_in + tail * g_out
    ctx["notes"].append(f"loop crossfade {X / sr:.1f}s, passage similarity {corr:.2f}")
    ctx["loop"] = True
    return body


def op_loudnorm(x, sr, p, ctx):
    cfg = ctx["cfg"]
    target = float(p.get("target_lufs", cfg["postprocess"]["loudness_lufs"]))
    tp = float(p.get("true_peak_db", cfg["postprocess"]["true_peak_db"]))
    with tempfile.TemporaryDirectory(prefix="msnorm_") as tmp:
        src, dst = Path(tmp) / "in.wav", Path(tmp) / "out.wav"
        encode(x, sr, src, cfg, ["-c:a", "pcm_f32le"])
        m = _loudnorm_json(src, cfg, target, tp)
        measured = _num(m.get("input_i"))
        if measured is None or measured < -69:
            ctx["warnings"].append("loudnorm: audio is (almost) silent, skipped")
            return x
        flt = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_LRA={m['input_lra']}"
               f":measured_TP={m['input_tp']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}"
               f":linear=true")
        proc = subprocess.run([_bin(cfg, "ffmpeg"), "-y", "-v", "error", "-i", str(src), "-af", flt,
                               "-ar", str(sr), "-c:a", "pcm_f32le", str(dst)], capture_output=True)
        if proc.returncode != 0:
            raise PostError("loudnorm failed: " + proc.stderr.decode(errors="replace")[:300])
        y = decode(dst, cfg, sr)
    ctx["notes"].append(f"loudness {measured:.1f} -> {target} LUFS")
    return y


def op_export(x, sr, p, ctx):  # handled by run_steps (needs file naming); kept for the vocabulary
    return x


OPS = {"trim_silence": op_trim_silence, "fit": op_fit, "fade": op_fade, "loop": op_loop,
       "loudnorm": op_loudnorm, "export": op_export}


# --------------------------------------------------------------------------- pipeline
def export_files(x, sr, out_dir: Path, base: str, formats: list[str], cfg: dict, meta: dict) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for fmt in formats:
        if fmt not in CODECS:
            raise PostError(f"unknown export format '{fmt}'. Known: {', '.join(CODECS)}")
        path = out_dir / f"{base}.{EXT.get(fmt, fmt)}"
        encode(x, sr, path, cfg, CODECS[fmt], meta)
        files.append(path.name)
    return files


def run_steps(src: Path, steps: list[dict], out_dir: Path, base: str, cfg: dict, *,
              spec: dict | None = None, preview: bool = False) -> dict:
    spec = spec or {}
    sr = int(cfg["postprocess"].get("sample_rate", SR_DEFAULT))
    x = decode(src, cfg, sr)
    ctx = {"cfg": cfg, "bpm": spec.get("bpm"), "duration": spec.get("duration"),
           "beats_per_bar": int(str(spec.get("time_signature") or 4).split("/")[0] or 4),
           "warnings": [], "notes": [], "loop": False}
    formats = list(cfg["postprocess"]["export_formats"])
    applied = []
    for step in steps:
        op = step.get("op")
        if op not in OPS:
            raise PostError(f"unknown step '{op}'")
        when = step.get("when")
        if (when == "loopable" and not spec.get("loopable")) or (when == "not_loopable" and spec.get("loopable")):
            continue
        if op == "export":
            formats = list(step.get("formats") or formats)
            continue
        x = OPS[op](x, sr, step, ctx)
        applied.append(op)

    if not np.all(np.isfinite(x)):
        raise PostError("processing produced non-finite samples")
    meta = {"title": spec.get("title", base), "comment": f"music-studio | style={spec.get('style')} | caption={spec.get('caption', '')}"[:500]}
    files = export_files(x, sr, out_dir, base, formats, cfg, meta)
    if preview and ctx["loop"]:
        export_files(np.concatenate([x, x]), sr, out_dir, base + ".loop-preview", formats[:1], cfg, meta)
        files.append(f"{base}.loop-preview.{EXT.get(formats[0], formats[0])}")

    first = out_dir / files[0]
    pp = cfg["postprocess"]
    report = analyze_array(x, sr, first, cfg, pp["loudness_lufs"], pp["true_peak_db"], bar=_bar_samples(ctx, sr))
    report["qc"] = qc(report, cfg, ctx["duration"] if "fit" in applied else None, looped=ctx["loop"])
    return {"files": files, "applied": applied, "notes": ctx["notes"], "warnings": ctx["warnings"], "report": report}


def workflow_steps(workflow: dict | None, cfg: dict) -> list[dict]:
    if workflow:
        for st in workflow.get("stages", []):
            if st.get("id") == "postprocess" and st.get("steps"):
                return st["steps"]
    return [{"op": "loudnorm"}, {"op": "export"}]


def run_for_take(take_id: str, variant: int | None, workflow_id: str | None, steps: list[dict] | None,
                 name: str | None, preview: bool) -> dict:
    ws = workspace_dir()
    cfg, _ = msconfig.load_config(ws)
    take = library.get_take(take_id, ws)
    if take is None:
        raise PostError(f"unknown take '{take_id}'")
    variants = take["variants"]
    if variant is None:
        variant = take.get("annotations", {}).get("picked") or 1
    match = next((v for v in variants if v["index"] == int(variant)), None)
    if match is None:
        raise PostError(f"take has no variant {variant} (have {[v['index'] for v in variants]})")
    spec = take.get("spec", {})
    if steps is None:
        wf = msconfig.load_workflows(ws).get(workflow_id or spec.get("workflow") or cfg["workflow"]["default"])
        steps = workflow_steps(wf, cfg)
    base = name or f"{library.safe_name(take.get('title') or take_id)}_v{variant}"
    out_dir = Path(take["dir"]) / "final"
    result = run_steps(Path(take["dir"]) / match["file"], steps, out_dir, base, cfg, spec=spec, preview=preview)
    record = {"variant": int(variant), "base": base, "created": time.strftime("%Y-%m-%dT%H:%M:%S"), **result}
    finals = read_json(Path(take["dir"]) / "final.json", []) or []
    finals = [f for f in finals if f.get("base") != base] + [record]
    write_json(Path(take["dir"]) / "final.json", finals)
    return record


# --------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("file")
    a.add_argument("--bpm", type=float, help="tempo, enables bar-aware loop seam measurement")
    a.add_argument("--beats", type=int, default=4, help="beats per bar")
    r = sub.add_parser("run")
    r.add_argument("--take", required=True)
    r.add_argument("--variant", type=int)
    r.add_argument("--workflow")
    r.add_argument("--steps", help="JSON file with a list of steps (overrides the workflow)")
    r.add_argument("--name")
    r.add_argument("--preview", action="store_true", help="also write a 2x loop preview")
    o = sub.add_parser("op")
    o.add_argument("name", choices=[k for k in OPS if k != "export"])
    o.add_argument("input"); o.add_argument("output")
    o.add_argument("--param", action="append", default=[], help="key=value (JSON values allowed)")
    args = ap.parse_args(argv)

    try:
        cfg, _ = msconfig.load_config()
        if args.cmd == "analyze":
            sr = int(cfg["postprocess"].get("sample_rate", SR_DEFAULT))
            path = Path(args.file)
            x = decode(path, cfg, sr)
            pp = cfg["postprocess"]
            bar = int(round(60.0 / args.bpm * args.beats * sr)) if args.bpm else None
            rep = analyze_array(x, sr, path, cfg, pp["loudness_lufs"], pp["true_peak_db"], bar=bar)
            rep["qc"] = qc(rep, cfg, looped=bool(args.bpm))
            print_json(rep)
        elif args.cmd == "run":
            steps = json.loads(Path(args.steps).read_text(encoding="utf-8")) if args.steps else None
            print_json(run_for_take(args.take, args.variant, args.workflow, steps, args.name, args.preview))
        elif args.cmd == "op":
            sr = int(cfg["postprocess"].get("sample_rate", SR_DEFAULT))
            params = {}
            for kv in args.param:
                k, _, v = kv.partition("=")
                try:
                    params[k] = json.loads(v)
                except json.JSONDecodeError:
                    params[k] = v
            ctx = {"cfg": cfg, "bpm": params.pop("bpm", None), "duration": params.get("duration"),
                   "beats_per_bar": int(params.pop("beats_per_bar", 4)), "warnings": [], "notes": [], "loop": False}
            x = OPS[args.name](decode(Path(args.input), cfg, sr), sr, params, ctx)
            out = Path(args.output)
            fmt = out.suffix.lstrip(".") or "wav"
            encode(x, sr, out, cfg, CODECS.get(fmt, CODECS["wav"]))
            print_json({"output": str(out), "duration": round(len(x) / sr, 3),
                        "notes": ctx["notes"], "warnings": ctx["warnings"]})
    except PostError as exc:
        log(f"error: {exc}")
        print_json({"ok": False, "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
