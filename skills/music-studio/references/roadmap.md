# Roadmap and extension points (phases 2+)

Phase 1 is instrumental music/BGM on ACE-Step with a customisable pipeline. The remaining scope was agreed up front; the structure below is where each piece plugs in so nothing needs a rewrite.

## Phase 2 - songs with vocals

- Spec already carries `instrumental`; `msconfig.py plan --vocals` is reserved. Add `lyrics` (text with `[Verse]` / `[Chorus]` section tags) and `vocal_language` to the spec.
- `engine_ace.py` already sets `lyrics`/`vocal_language`; it currently forces `"[Instrumental]"` when `instrumental` is true. The change is feeding real lyrics when false.
- New sub-skill/reference: lyric writing (structure, syllable counts per line, rhyme scheme), a lyrics gate in the workflows (`plan` already supports gates).
- Styles gain an optional `vocals` block (voice type, language) the same way they carry `bpm` and `keys`.

## Phase 3 - sound effects (SFX)

- ACE-Step is a music model; short one-shot effects are a different problem. Two realistic routes: (a) procedural synthesis in Python - `engine_mock.py` already shows the numpy approach (envelopes, noise, filtered tones) and is the seed of an `engine_sfx.py`; (b) a separate local text-to-audio model behind a second engine file.
- Add `kind: "sfx"` to the spec, an `sfx/` styles folder (recipes: whoosh, UI click, coin, explosion, footstep) and a `sfx-pack` workflow that makes N variations and normalises each to a consistent level.
- Post-processing already has `trim_silence`, `fade`, `loudnorm`, `export`; add `pitch/speed` and `layer` ops.

## Phase 4 - remix / rearrange / edit existing music

- ACE-Step supports `cover` and `repaint` tasks (`GenerationParams.task_type`, `src_audio`, `audio_cover_strength`, `repainting_start/end`) for the DiT models; `engine_ace.py` only sets `task_type="text2music"` today.
- Add `task` + `source` fields to the spec, a `remix` workflow, and a dashboard upload box. Check licensing/ownership of the source before use - this skill does not assert you have the rights to a track you upload.
- Stem-level remixing needs stem separation, which is not part of ACE-Step; plan it as an optional external tool step.

## Other candidates

- A second backend (another local model, or a hosted API) behind the same `engine.py generate` contract: stdout JSON lines with `start / progress / warn / result / error`. Anything that honours that contract works with the dashboard and with Claude unchanged.
- Adaptive game music: generate matched-key/BPM variants and ship a crossfade map.
- Batch generation from a CSV/JSON list of specs (a thin loop around `engine.py generate`).
