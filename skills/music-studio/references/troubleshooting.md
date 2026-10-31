# Troubleshooting (Windows first)

Bad-sounding results: read `quality.md` first. Start with `python scripts/engine.py check` - it reports ffmpeg, GPU, tier, ACE-Step install, installed checkpoints and config problems in one JSON.

## Two ways a job runs

| | Through the server (default) | Direct (fallback) |
|---|---|---|
| Started by | the dashboard, or `python scripts/msclient.py generate --spec spec.json` | `python scripts/engine.py generate --spec spec.json` |
| Models | stay loaded in a worker between jobs; unloaded after `engine_idle_unload_minutes` (10) idle or `msclient.py unload` | loaded and freed on every run |
| Cancel | dashboard 取消 or `msclient.py cancel JOB`: kills the worker, frees VRAM, moves the partial take to `<workspace>\trash` | close the window (Ctrl+C) |
| Where to look | dashboard job log; `<workspace>\server.log`; `<workspace>\jobs.json` (queue + history); `msclient.py status` | the terminal; stderr has everything ACE-Step prints |
| CPU decode | `warn` with code `cpu_decode` as soon as it happens; the next job is tightened automatically | the same line in the terminal, nothing tightened |

Use the direct path only when the server will not start, or to tell a server problem from an ACE-Step problem: if a spec fails direct too, the cause is ACE-Step or the models, not the server.

## Symptoms

| Symptom | Cause / fix |
|---|---|
| `ffmpeg not found` | `winget install Gyan.FFmpeg`, then **open a new terminal** so PATH refreshes. Or set `ffmpeg` / `ffprobe` to full paths in your config. |
| `ace_step_dir is not set` | Run `scripts\setup_windows.ps1`, or `python scripts\msconfig.py set ace_step_dir "C:/Users/you/ACE-Step-1.5"` (forward slashes are fine). |
| `no checkpoints found` / `models for this tier are not installed` | `python scripts\engine.py models --download` (downloads what your GPU tier needs; re-run to resume). `models` alone lists installed vs needed. |
| `models for this tier are not installed` | The configured `dit_model` / `lm_model` folder names do not match what is in `checkpoints`. Edit `hardware.tiers.<tier>` to a name from the `check` output. |
| `ace_import` error | The runner is not using ACE-Step's own Python. `engine.py` prefers `<ace_dir>\.venv\Scripts\python.exe`, then `uv run`. Install uv (`winget install astral-sh.uv`) or run `uv sync` inside the ACE-Step folder. |
| `oom` / "GPU ran out of memory" | The engine already retries once with 1 variant. Close games/browsers using the GPU, pick `draft`, shorten the track, or lower `hardware.tiers.<tier>.max_batch`. Forcing `hardware.tier` one step lower also helps. |
| Generation is fast (~10 s) but then "freezes" at ~80% / "Decoding audio" for minutes | 4-6 GB cards: the diffusion model stays on the GPU, the VAE finds <0.5 GB free and ACE-Step decodes on the CPU (log: `auto-enabling CPU VAE decode`). Close the window, then `python scripts/msconfig.py set hardware.tiers.<tier>.offload_dit_to_cpu true` (the `low` tier has it on by default; cards under 8 GB get it automatically). Shorter tracks decode faster. |
| First generation takes a minute | Models load into VRAM on first use; later runs in the same minute-scale are faster. |
| LM ("thinking") does not load | The runner tries `pt` then `vllm` and continues **without** thinking, with a warning. vLLM is generally not available on native Windows; `pt` is the default for that reason. |
| "this ACE-Step version ignores: ..." (stderr) | Harmless. A parameter in this skill is not known to your ACE-Step build, so it was dropped instead of crashing. If a setting seems to have no effect, check this line. |
| Server will not start / `the server did not start` | Read `<workspace>\server.log`. A `server.json` left by a crash is ignored when nothing answers at its URL; only one server runs per workspace. |
| Job shows `failed: interrupted` | The server was closed while it ran. Run it again; models reload on the first job. |
| No progress for 4 minutes (stall warning) | Usually a CPU decode or the first model download. Check the job log for `auto-enabling CPU VAE decode`; cancel and see the CPU-decode row below if so. |
| Cancel did not free the GPU | The worker should exit within seconds. Check Task Manager for a leftover `python.exe` from ACE-Step's `.venv`, end it, and report it (this is a bug). |
| Dashboard port busy | The server takes a free port automatically and prints the URL (also in `<workspace>\server.json`). To pin one: `dashboard.port`. |
| Audio will not play in the dashboard | Browsers play flac, wav, mp3 and ogg. If a codec fails, set `generation.audio_format` to `wav` or `mp3`. |
| Loop clicks or "jumps" | See the loop section in `use-cases.md`; usually the tempo drifted or the track has an intro/outro. Regenerate with "steady, repetitive" and no build, or set `crossfade` longer (4 s). |
| Mastered file sounds quiet | That is the target (-16 LUFS is typical streaming/game level; -20 for background). Change `postprocess.loudness_lufs` or the workflow's `loudnorm` step. |

## Testing without a GPU

`python scripts\engine.py generate --spec spec.json --engine mock` writes synthetic audio so you can try planning, post-processing, the library and the dashboard anywhere. It is a test signal, not music.

## Logs

Direct path: everything the engines print besides JSON goes to **stderr**; run the command in a terminal to see it. Server path: the dashboard's job log panel keeps the last 400 lines per job; `server.log` and `jobs.json` are in the workspace.
