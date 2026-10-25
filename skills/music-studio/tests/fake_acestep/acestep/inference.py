import dataclasses
import os
import struct
import wave
from pathlib import Path


@dataclasses.dataclass
class GenerationParams:
    task_type: str = "text2music"
    caption: str = ""
    lyrics: str = ""
    # NOTE: no `instrumental` field on purpose (older build) -> must be filtered, not crash
    vocal_language: str = "unknown"
    bpm: int | None = None
    keyscale: str = ""
    timesignature: str = ""
    duration: float = -1.0
    inference_steps: int = 8
    guidance_scale: float = 7.0
    shift: float = 1.0
    thinking: bool = True
    seed: int = -1


@dataclasses.dataclass
class GenerationConfig:
    batch_size: int = 2
    use_random_seed: bool = True
    seeds: list | None = None
    audio_format: str = "flac"


class GenerationResult:
    def __init__(self, success, audios=None, error=None):
        self.success, self.audios, self.error = success, audios or [], error
        self.extra_outputs = {"lm_metadata": {"bpm": 80, "keyscale": "C minor"}, "time_costs": {"total": 1.0}}


def generate_music(dit, llm, params, config, save_dir=None, progress=None):
    if os.environ.get("FAKE_OOM") and config.batch_size > 1:
        raise RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")
    if os.environ.get("FAKE_FAIL"):
        return GenerationResult(False, error="model exploded")
    if progress:
        progress(0.5, desc="denoising")
    if os.environ.get("FAKE_SLOW"):
        import time
        time.sleep(float(os.environ["FAKE_SLOW"]))
    audios = []
    for i in range(config.batch_size):
        # write a tiny valid wav, but name it with the requested extension like ACE does
        path = Path(save_dir) / f"uuid-{i}.{config.audio_format}"
        tmp = Path(save_dir) / f"uuid-{i}.tmp.wav"
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
            w.writeframes(struct.pack("<hh", 0, 0) * 4800)
        tmp.replace(path)
        seed = (config.seeds or [0] * config.batch_size)[i]
        audios.append({"path": str(path), "tensor": None, "key": f"k{i}", "sample_rate": 48000,
                       "params": {"seed": seed, "thinking": params.thinking,
                                  "caption": params.caption, "keyscale": params.keyscale}})
    return GenerationResult(True, audios)
