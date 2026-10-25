"""Detect the NVIDIA GPU and map its VRAM to a hardware tier.

The tier picks sensible model / offload defaults (see defaults/config.json ->
hardware.tiers). Nothing is hard-coded to one card: a different GPU, or a
config override, changes the result.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from common import print_json

# Upper bounds (GB, exclusive) for each tier. Anything above the last is "ultra".
TIER_BOUNDS = (("low", 6.0), ("mid", 12.0), ("high", 20.0))


def detect() -> dict:
    """Return {"available", "gpus": [{"name","vram_gb"}], "vram_gb", "source"}."""
    fake = os.environ.get("MUSIC_STUDIO_FAKE_VRAM_GB")
    if fake:  # test hook, also handy for "what would a 8 GB card get?"
        gb = float(fake)
        return {"available": True, "gpus": [{"name": "fake", "vram_gb": gb}],
                "vram_gb": gb, "source": "env"}

    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, "gpus": [], "vram_gb": 0.0, "source": "none",
                "note": "nvidia-smi not found (no NVIDIA driver, or not on PATH)"}
    try:
        out = subprocess.run(
            [exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        return {"available": False, "gpus": [], "vram_gb": 0.0, "source": "error",
                "note": f"nvidia-smi failed: {exc}"}

    gpus = []
    for line in out.strip().splitlines():
        name, _, mem = line.rpartition(",")
        try:
            gpus.append({"name": name.strip(), "vram_gb": round(float(mem) / 1024.0, 1)})
        except ValueError:
            continue
    if not gpus:
        return {"available": False, "gpus": [], "vram_gb": 0.0, "source": "error",
                "note": "could not parse nvidia-smi output"}
    # Generation runs on one device; use the biggest card.
    best = max(g["vram_gb"] for g in gpus)
    return {"available": True, "gpus": gpus, "vram_gb": best, "source": "nvidia-smi"}


def tier_for(vram_gb: float) -> str:
    for name, bound in TIER_BOUNDS:
        if vram_gb < bound:
            return name
    return "ultra"


def describe() -> dict:
    info = detect()
    if info["available"]:
        info["tier"] = tier_for(info["vram_gb"])
    else:
        # No CUDA: ACE-Step can run on CPU but very slowly; use the lightest tier.
        info["tier"] = "low"
        info["cpu_only"] = True
    return info


if __name__ == "__main__":
    print_json(describe())
