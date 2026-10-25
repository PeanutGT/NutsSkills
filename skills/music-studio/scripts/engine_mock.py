"""Mock engine: synthesises a simple, deterministic instrumental with numpy.

Purpose: let the whole pipeline (planning -> variants -> post-processing ->
library -> dashboard) be exercised on a machine without a GPU or ACE-Step.
It is NOT a music model - it honours bpm / key / duration / seed / rough
style tags so everything downstream behaves like it would with real audio.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000
NOTE_INDEX = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6,
              "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
PROGRESSIONS = {
    "minor": [[0, 5, 2, 6], [0, 3, 4, 0], [0, 6, 5, 6], [0, 2, 5, 6]],
    "major": [[0, 4, 5, 3], [0, 5, 3, 4], [0, 3, 0, 4], [0, 5, 1, 4]],
}
DRUM_WORDS = ("drum", "beat", "hip hop", "hip-hop", "lo-fi", "lofi", "electronic", "house",
              "techno", "synthwave", "rock", "trap", "dnb", "percussion")


def parse_key(key: str | None) -> tuple[int, str]:
    """'F# minor' / 'Eb Major' / 'Am' -> (root_semitone, 'minor'|'major')."""
    if not key:
        return 0, "major"
    k = key.strip().replace("♭", "b").replace("♯", "#")
    root = k[0].upper()
    rest = k[1:]
    if rest[:1] in ("#", "b", "B") and not rest.lower().startswith(("aj", "in")):
        root += rest[0].upper() if rest[0] != "b" else "B"
        rest = rest[1:]
    mode = "minor" if rest.strip().lower() in ("m", "min", "minor") or "min" in rest.lower() else "major"
    return NOTE_INDEX.get(root.upper(), 0), mode


def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _add(buf: np.ndarray, start: int, sig: np.ndarray, pan: float = 0.0) -> None:
    if start >= buf.shape[0] or start + len(sig) <= 0:
        return
    end = min(buf.shape[0], start + len(sig))
    seg = sig[: end - start]
    left, right = (1 - max(pan, 0)), (1 + min(pan, 0))
    buf[start:end, 0] += seg * left
    buf[start:end, 1] += seg * right


def _tone(freq: float, dur: float, attack: float, decay: float, harmonics=(1.0, 0.4, 0.2),
          detune: float = 0.0) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for i, amp in enumerate(harmonics, start=1):
        sig += amp * np.sin(2 * np.pi * freq * i * t)
        if detune:
            sig += amp * 0.6 * np.sin(2 * np.pi * freq * i * (1 + detune) * t)
    env = np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t * decay)
    # short release so notes never end with a click
    rel = min(int(0.01 * SR), n)
    if rel:
        env[-rel:] *= np.linspace(1, 0, rel)
    return sig * env


def synth(*, bpm: float, key: str | None, duration: float, seed: int, caption: str = "",
          time_signature: str = "4", progress=None) -> np.ndarray:
    rng = np.random.default_rng(seed & 0xFFFFFFFF)
    bpm = float(bpm or 90)
    beats = int(str(time_signature).split("/")[0] or 4)
    beat_s = 60.0 / bpm
    bar_s = beat_s * beats
    root, mode = parse_key(key)
    scale = MINOR if mode == "minor" else MAJOR
    prog = PROGRESSIONS[mode][int(rng.integers(len(PROGRESSIONS[mode])))]
    slow = any(w in caption.lower() for w in ("ambient", "drone", "meditation", "sleep"))
    bars_per_chord = 2 if slow else 1
    total_bars = int(np.ceil(duration / bar_s)) + 2
    n = int((total_bars * bar_s + 2) * SR)
    buf = np.zeros((n, 2))
    use_drums = any(w in caption.lower() for w in DRUM_WORDS) and not slow
    arp_pattern = [int(x) for x in rng.permutation([0, 1, 2, 1, 2, 1, 0, 2])[:8]]

    for bar in range(total_bars):
        chord_deg = prog[(bar // bars_per_chord) % len(prog)]
        triad = [scale[chord_deg % 7], scale[(chord_deg + 2) % 7] + (12 if (chord_deg + 2) >= 7 else 0),
                 scale[(chord_deg + 4) % 7] + (12 if (chord_deg + 4) >= 7 else 0)]
        base_midi = 48 + root  # around C3
        bar_start = int(bar * bar_s * SR)
        if bar % bars_per_chord == 0:  # pad lasts through the chord, with a slow attack
            for semi in triad:
                pad = _tone(_hz(base_midi + 12 + semi), bar_s * bars_per_chord + 0.6, 0.35, 0.12,
                            harmonics=(1.0, 0.25, 0.1), detune=0.004)
                _add(buf, bar_start, pad * 0.11, pan=float(rng.uniform(-0.3, 0.3)))
        # bass: root on beat 1 and the "and" of 2
        for b_off in (0.0, 1.5):
            if b_off < beats:
                bass = _tone(_hz(base_midi - 12 + triad[0]), beat_s * 1.4, 0.01, 4.0, harmonics=(1.0, 0.35))
                _add(buf, bar_start + int(b_off * beat_s * SR), bass * 0.32)
        # arpeggio on eighth notes
        for step in range(beats * 2):
            note = triad[arp_pattern[step % len(arp_pattern)] % 3] + 12
            pl = _tone(_hz(base_midi + 12 + note), beat_s * 0.9, 0.004, 7.0, harmonics=(1.0, 0.3, 0.1))
            _add(buf, bar_start + int(step * beat_s / 2 * SR), pl * 0.12,
                 pan=0.35 if step % 2 else -0.35)
        if use_drums:
            for b in range(beats):
                pos = bar_start + int(b * beat_s * SR)
                if b % 2 == 0:  # kick
                    t = np.arange(int(0.22 * SR)) / SR
                    f = 45 + 80 * np.exp(-t * 30)
                    kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)
                    _add(buf, pos, kick * 0.55)
                else:  # snare-ish noise
                    t = np.arange(int(0.18 * SR)) / SR
                    _add(buf, pos, rng.standard_normal(len(t)) * np.exp(-t * 22) * 0.12)
                for h in (0.0, 0.5):  # hats on eighths
                    t = np.arange(int(0.05 * SR)) / SR
                    noise = np.diff(rng.standard_normal(len(t) + 1))
                    _add(buf, pos + int(h * beat_s * SR), noise * np.exp(-t * 90) * 0.06,
                         pan=0.2 if h else -0.2)
        if progress and bar % 4 == 0:
            progress(0.1 + 0.8 * bar / total_bars, "synthesising")

    out = buf[: int(duration * SR)]
    # gentle fade-out so a mock track never ends on a click (loop tool still has work to do)
    fade = min(int(0.5 * SR), len(out))
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    peak = float(np.max(np.abs(out))) or 1.0
    return (out / peak * 0.85).astype(np.float32)


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def generate(spec: dict, params: dict, seeds: list[int], out_dir: Path, emit_progress=None) -> list[dict]:
    """Write one wav per seed into out_dir and return per-variant metadata."""
    results = []
    dur = float(params["duration"])
    for i, seed in enumerate(seeds, start=1):
        def prog(frac, desc, _i=i):
            if emit_progress:
                emit_progress((( _i - 1) + frac) / len(seeds), f"variant {_i}/{len(seeds)}: {desc}")
        audio = synth(bpm=spec.get("bpm") or 90, key=spec.get("key"), duration=dur, seed=seed,
                      caption=spec.get("caption", ""), time_signature=spec.get("time_signature", "4"),
                      progress=prog)
        path = out_dir / f"v{i}.wav"
        write_wav(path, audio)
        results.append({"index": i, "file": path.name, "seed": seed, "duration": round(dur, 3),
                        "lm_metadata": {"bpm": spec.get("bpm") or 90, "keyscale": spec.get("key"),
                                        "note": "mock engine"}})
    return results
