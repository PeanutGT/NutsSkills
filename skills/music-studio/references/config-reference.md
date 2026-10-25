# Configuration reference

Two layers, merged key by key (lists and scalars are replaced, objects are merged):

1. **Skill defaults** - `defaults/config.json` (never edit; updates overwrite it)
2. **Your workspace** - `<workspace>/config.json` (only the keys you change)

The workspace is `%USERPROFILE%\MusicStudio` unless the environment variable `MUSIC_STUDIO_HOME` points elsewhere.

```
python scripts/msconfig.py show --explain     # effective values + which layer each came from
python scripts/msconfig.py set generation.duration 90
python scripts/msconfig.py set hardware.tier high        # plain words are taken as strings; numbers, true/false, [..] and {..} are parsed as JSON
python scripts/msconfig.py unset generation.duration
python scripts/msconfig.py validate
```

## Engine parameter precedence

For every generation, lowest to highest:
`generation` -> `hardware.tiers.<tier>` -> `quality.presets.<preset>` -> `engine_overrides` -> the request itself.

So a preset beats a tier and your explicit request beats everything. `engine_overrides` pins a value across **all** presets (setting `batch_size` there silently defeats `draft`'s 3 variants) - use it deliberately.

## Keys

| Key | Meaning |
|---|---|
| `engine` | `ace` (ACE-Step on your GPU) or `mock` (synthetic test audio, no GPU) |
| `ace_step_dir` | Folder of the ACE-Step 1.5 install. The installer fills this in. |
| `ffmpeg`, `ffprobe` | Executable names or full paths |
| `generation.duration` | Seconds when nothing else says. A style's default duration wins over this. |
| `generation.instrumental` | Phase 1 is instrumental-only; keep `true` |
| `generation.seed` | `-1` = random per variant; a number = reproducible (variant *i* uses seed+i) |
| `generation.guidance_scale`, `shift`, `inference_steps` | Diffusion settings; turbo checkpoints override guidance to 1.0 internally |
| `generation.audio_format` | Format ACE-Step writes: `flac`, `wav`, `mp3`... |
| `hardware.tier` | `auto` detects VRAM; or force `low` / `mid` / `high` / `ultra` |
| `hardware.lm_backend` | `pt` by default (works on Windows); the runner falls back to `vllm` and back automatically |
| `hardware.tiers.<t>.dit_model` | Checkpoint folder under `<ace_step_dir>/checkpoints` |
| `hardware.tiers.<t>.lm_model` | Language-model checkpoint for "thinking" mode, or `null` |
| `hardware.tiers.<t>.offload_to_cpu`, `quantization` | Memory savers for smaller cards |
| `hardware.tiers.<t>.max_duration`, `max_batch` | Safety caps (clamped with a warning) - raise them if your card copes |
| `quality.default` | Preset used when a request names none |
| `quality.presets.<p>` | Any engine parameter; `thinking` needs an LM in the tier |
| `postprocess.loudness_lufs` | Integrated loudness target (default -16) |
| `postprocess.true_peak_db` | True-peak ceiling (default -1.5) |
| `postprocess.loop_crossfade` | Seconds folded over the seam when looping (default 2.0) |
| `postprocess.export_formats` | Used when a workflow has no `export` step |
| `postprocess.sample_rate` | Working/export sample rate (default 48000) |
| `workflow.default` | Workflow used when a request names none |
| `output.dir` | Where takes are written (relative = inside the workspace) |
| `dashboard.host`, `dashboard.port` | Keep host on `127.0.0.1` |

## VRAM tiers (defaults, following ACE-Step 1.5's own guidance)

| Tier | VRAM | Diffusion | LM ("thinking") | Offload | Quantization |
|---|---|---|---|---|---|
| low | < 6 GB | turbo 2B | none | yes | int8 |
| mid | 6-12 GB | turbo 2B | 0.6B | yes | none |
| high | 12-20 GB | turbo 2B | 1.7B | yes | none |
| ultra | 20 GB+ | XL turbo 4B | 4B | no | none |

Quality presets: `draft` (turbo 8 steps, no LM, 3 variants), `standard` (turbo 8 steps + LM, 2 variants), `high` (sft 50 steps + LM), `max` (sft 64 steps + LM, 1 variant). `high`/`max` need `acestep-v15-sft`: `python scripts/engine.py models --download acestep-v15-sft`; without it they fall back to turbo with a warning. Extra engine knobs may go in any preset or `engine_overrides`: `lm_temperature`, `lm_cfg_scale`, `use_cot_caption`, `use_cot_metas`, `infer_method`.

`ace_checkpoints_dir` (default `null`) points at a shared model folder (also honours the `ACESTEP_CHECKPOINTS_DIR` environment variable).

Model folder names are what ACE-Step 1.5 uses at the time of writing. They must exist under `<ace_step_dir>/checkpoints`; `python scripts/engine.py check` lists what is installed and reports mismatches. If a preset's checkpoint is missing the tier model is used with a warning.

Moving to a different GPU needs no edits: `tier: auto` re-detects. To see what a given card would get without owning it: `MUSIC_STUDIO_FAKE_VRAM_GB=8 python scripts/msconfig.py tier`.
