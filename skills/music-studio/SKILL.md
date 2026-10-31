---
name: music-studio
description: Create instrumental music and BGM (game loops, video scores, study/work background, personal tracks) locally with ACE-Step 1.5 on the user's NVIDIA GPU, with fully customisable defaults, style library, description lexicon and workflows plus a local dashboard. Use whenever the user wants to make, generate, loop, master or manage background music or a soundtrack, tweak music defaults or styles, fix bad-sounding results, or says 做音樂/配樂/BGM/循環音樂/遊戲音樂/讀書背景音. Also use for music-studio setup or troubleshooting.
license: Apache-2.0
metadata:
  version: "3.3.0"
  author: PeanutGT
  repository: https://github.com/PeanutGT/NutsSkills
---

# Music Studio

Generates **instrumental music** on the user's own GPU (ACE-Step 1.5), post-processes it (trim, exact length, fades, seamless loop, loudness, export) and keeps a library. Everything customisable lives in the user's **workspace**, never in this skill folder. Reply in the user's language; write captions in English.

Phase 1 scope: instrumental music/BGM only. Vocals, SFX, remixing existing audio are planned (`references/roadmap.md`) - say so plainly if asked.

All commands run from this skill's folder: `python scripts/<tool>.py`. Workspace: `%USERPROFILE%\MusicStudio` (or `$MUSIC_STUDIO_HOME`).

## Conversation style: act, do not interview
The person usually wants music, not a questionnaire.
- Ask **at most one** question, and only when a wrong guess is expensive (exact video length, must it loop?). Otherwise decide, say in one line what you assumed, and go.
- Do not narrate every command. Report: the plan (one short block), a progress line per stage while generating, then the result and what to try next.
- Never make the person run commands you can run. If you cannot reach their machine, give exactly one thing to double-click (`setup.bat`, `start_dashboard.bat`).

## 1. Make sure it can run (silent when fine)
`python scripts/engine.py check` -> read `problems` / `notes`. Fix them *for* the person:
- not set up -> run `scripts\setup_windows.ps1` (or tell them to double-click `setup.bat`); no GPU -> `-Mock`.
- models missing -> `python scripts/engine.py models --download` (use `models` with no flag to list what the tier needs; `--download acestep-v15-sft` for the high-quality model).
- `engine: mock` -> the audio is a **synthetic test signal**; say so before they judge quality.

## 2. Show the dashboard (do this proactively)
`python scripts/msclient.py url` starts the server in the background if needed (no browser) and prints its URL; hand it over. The server is the one owner of the GPU: it keeps the models loaded between jobs (the first job of a session is the slow one) and queues jobs from both Claude and the dashboard, so they can watch your job live there, audition, edit the caption and finalize. If the tools run somewhere that is not their PC, tell them to double-click `start_dashboard.bat` instead.

## 3. Plan
Write the English caption yourself - it is the biggest quality lever: 6-12 concrete tags (genre, `instrumental`, lead instruments, rhythm, mood, space/production), see `references/prompting-guide.md`. Then:
`python scripts/msconfig.py plan --style S --description "<their words>" --mood a,b --caption "tag, tag, ..." [--duration N --bpm N --key K --quality Q --workflow W --variants N --seed N]`
- `--style from-description` when no preset fits; otherwise the nearest style (`msconfig.py styles`; feelings -> styles in `references/use-cases.md`).
- Without `--caption`, the caption is built from the style + the description (via the lexicon, `msconfig.py lexicon`) + moods; unknown Chinese words are reported in `warnings` - translate them yourself.
- Show caption, BPM, key, length, workflow in one block. Keep the **spec warnings** (clamped length, trimmed tags). Length: 30-120 s is the stable range; for long pieces generate ~2 min and loop.

## 4. Generate
Save the spec and run `python scripts/msclient.py generate --spec spec.json` (`--engine mock` for a dry run). It queues the job on the server and prints JSON lines: `queued`, `phase` (`loading_models`, `encoding`, `diffusing`, `decoding`, `writing`), `warn`, then `result` (take id, folder, variant files) or `error` (code, message, hint, log tail). Give the person one short line per phase, not every line.
- Relay warnings that change the outcome: no LM, model fell back, ignored settings, OOM retry, `cpu_decode` (decoding fell back to the CPU and will take minutes; the next job is automatically tightened).
- Other commands: `msclient.py status` (queue + whether models are loaded), `cancel JOB`, `wait JOB`, `unload` (free the GPU, e.g. before they play a game).
- `engine.py generate --spec ...` runs a one-off job without the server; use it only if the server cannot start.

## 5. Audition -> refine -> finish
- Variants are `v1`, `v2`... in the take folder / dashboard. Iterate by changing **one** thing and keeping the seed of the liked variant (dashboard: 以這版為基礎微調再生). Draft on `draft`/`standard`; re-render the keeper on `high` with the same seed.
- Every variant is checked automatically when it is written: `variants[].qc` in the take (clipping, clicks, cut_off, silence, near_silent, low_volume, each with a time). Mention any issue in one line with its time; it is a heuristic, the ear decides.
- Finish: `python scripts/postprocess.py run --take ID [--variant N] [--workflow W] [--loudness video|game|background|-14] [--preview]`; `--loudness` overrides the workflow's target (video -14, game -16, background -18 LUFS). Explain `report.qc` and `report.issues` in plain words. Loops: if the seam is flagged, offer the loop preview or regenerate with "steady, repetitive, no build".
- Library: `python scripts/library.py list|show|annotate ID rating=4 favorite=true notes=...|trash ID`.

## When the person says it sounds bad
Do not guess. Read `references/quality.md`: open the take's `effective` / `warnings` (what really ran: model, steps, LM, quantization, ignored settings), fix the first cause on its list, regenerate with the same seed, and compare.

## Customisation (the point of this skill)
Four layers in the workspace, merged over the shipped defaults:
- **Parameters/defaults**: `config.json` via `python scripts/msconfig.py set KEY VALUE` / `unset KEY` (`show --explain` tells which layer a value comes from; keys in `references/config-reference.md`).
- **Styles / moods**: `styles/*.json`, `moods.json` (`references/styles-moods-workflows.md`).
- **Lexicon**: `lexicon.json` - teach it how your words map to English tags (`msconfig.py lexicon` shows the built-ins).
- **Workflows**: `workflows/*.json` - stages, gates, post-process steps.
"以後預設用 X" = a change in the **workspace** (never `defaults/`), then `msconfig.py validate`, then say exactly what changed and how to revert. A one-off wish applies to this request only.

Engine parameter precedence: generation < hardware tier < quality preset < `engine_overrides` < the request. VRAM tier is auto-detected; force it with `hardware.tier`.

## Be honest about
- First real ACE-Step runs on a given machine may need model-folder-name or setting fixes; `engine.py check` and the take's diagnostics panel show what is wrong. ACE-Step quality is bounded by the model: turbo is fast, sft is better but slower.
- Loops are crossfade-based and need steady tempo; requested BPM is a hint. QC seam numbers are heuristics - the loop preview is the real test.
- No exact cue points in time, no stems. Do not name real artists/songs/games in captions; check the model licence before commercial use.

## Files
`scripts/` tools | `defaults/` shipped config, styles, moods, lexicon, workflows | `docs/ARCHITECTURE.md` (how server, queue and worker fit together) | `references/` (read as needed): `quality.md`, `prompting-guide.md`, `use-cases.md`, `config-reference.md`, `styles-moods-workflows.md`, `troubleshooting.md`, `dashboard.md`, `roadmap.md` | `setup.bat`, `start_dashboard.bat` | `tests/` | `evals/`
