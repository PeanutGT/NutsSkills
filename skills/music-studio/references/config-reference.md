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

## Every tunable generation setting

`defaults/knobs.json` is the catalog of what can be tuned: type, range, effect (in Traditional Chinese for the UI) and which layer may set it. Three ways to see it:

- Dashboard -> 設定 -> **所有可調的生成參數**: effective value per quality preset, which layer it came from, range, explanation; edit it into the layer you pick (全域預設 = `generation`, 只有品質 X = `quality.presets.X`, 強制所有品質 = `engine_overrides`, 硬體等級 = `hardware.tiers.<t>`) and reset it. It warns when the layer you save to is shadowed by a higher one, and shows when the hardware adjusted a value (tier caps, no LM).
- Dashboard -> 建立 -> **進階：生成參數**: per-take values (`engine_params` in the spec); empty fields show the value that would be used and its layer.
- `python scripts/msconfig.py knobs [--quality Q] [--tier T]`; per take: `msconfig.py plan ... --param shift=2.5 --param thinking=false`.

Values are range-checked (`validate`, the dashboard and `--param` all use the same catalog). Unset settings use ACE-Step's own default.

| Key | Layer | Range | Per take | Effect |
|---|---|---|---|---|
| `duration` | engine | 5-600 s | form field | Seconds; capped by the tier's `max_duration` |
| `batch_size` | engine | 1-8 | form field (版本數) | Variants per take; capped by `max_batch` |
| `seed` | engine | -1 or integer | form field | -1 random; fixed = reproducible (variant i uses seed+i) |
| `audio_format` | engine | flac / wav / mp3 | - | Raw file ACE-Step writes |
| `inference_steps` | engine | 1-100 | yes | More = more detail, slower. Turbo: 8, max 20 (more is reset to 8); sft: 20+ (less becomes 32) |
| `guidance_scale` | engine | 1-15 | yes | How closely the caption is followed; turbo models fix it to 1.0 internally |
| `shift` | engine | 1-10 | yes | Timestep shift (structure vs detail); 3 recommended for turbo |
| `infer_method` | engine | ode / sde | yes | ode deterministic per seed; sde adds noise each step |
| `use_adg` | engine | bool | yes | Adaptive dual guidance; sft models only |
| `cfg_interval_start`, `cfg_interval_end` | engine | 0-1 | yes | Fraction of the steps where guidance applies |
| `thinking` | engine | bool | yes | LM expands the caption and picks BPM/key; forced off when the tier has no LM |
| `lm_temperature` | engine | 0-2 | yes | LM randomness |
| `lm_cfg_scale` | engine | 0-10 | yes | How closely the LM follows the prompt |
| `lm_top_k` | engine | 0-200 | yes | LM sampling: top-k (0 = off) |
| `lm_top_p` | engine | 0-1 | yes | LM sampling: nucleus |
| `use_cot_metas`, `use_cot_caption`, `use_cot_language` | engine | bool | yes | Let the LM decide BPM/key, rewrite the caption, detect the lyric language |
| `dit_model`, `lm_model` | tier | checkpoint name | - | Models for this tier (a preset may name `dit_model` too) |
| `quantization` | tier | null / int8_weight_only | - | Saves VRAM, hurts sound |
| `offload_to_cpu`, `offload_dit_to_cpu` | tier | bool | - | Memory savers for small cards |
| `max_duration`, `max_batch` | tier | number | - | Safety caps |

ACE-Step 1.5 settings Music Studio does **not** send yet (listed under 設定 so people know they exist; each needs a listening test first): `sampler_mode`, `dcw_*`, `latent_shift`, `latent_rescale`, `velocity_norm_threshold`, `velocity_ema_factor`, `timesteps`, `enable_normalization` / `normalization_db`, `fade_in` / `fade_out`, and the cover / repaint / lego / extract / complete task types.

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
| `postprocess.loudness_presets` | Named targets picked at export (`video` -14, `game` -16, `background` -18 LUFS, all -1 dBTP); override the workflow's `loudnorm` target. Add your own: `{"label": ..., "lufs": ..., "true_peak_db": ...}` |
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
| low | < 6 GB | turbo 2B | none | yes | none (int8 sounded broken on 4 GB; set `int8_weight_only` only if you run out of VRAM) |
| mid | 6-12 GB | turbo 2B | 0.6B | yes | none |
| high | 12-20 GB | turbo 2B | 1.7B | yes | none |
| ultra | 20 GB+ | XL turbo 4B | 4B | no | none |

Quality presets: `draft` (turbo 8 steps, no LM, 3 variants), `standard` (turbo 8 steps + LM, 2 variants), `high` (sft 50 steps + LM), `max` (sft 64 steps + LM, 1 variant). `high`/`max` need `acestep-v15-sft`: `python scripts/engine.py models --download acestep-v15-sft`; without it they fall back to turbo with a warning. Any engine setting from the table above may go in `generation`, any preset or `engine_overrides`.

`ace_checkpoints_dir` (default `null`) points at a shared model folder (also honours the `ACESTEP_CHECKPOINTS_DIR` environment variable).

Model folder names are what ACE-Step 1.5 uses at the time of writing. They must exist under `<ace_step_dir>/checkpoints`; `python scripts/engine.py check` lists what is installed and reports mismatches. If a preset's checkpoint is missing the tier model is used with a warning.

Moving to a different GPU needs no edits: `tier: auto` re-detects. To see what a given card would get without owning it: `MUSIC_STUDIO_FAKE_VRAM_GB=8 python scripts/msconfig.py tier`.
