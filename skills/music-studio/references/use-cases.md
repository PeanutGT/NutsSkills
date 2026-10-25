# Recipes by use case

## Game BGM (loops)

- Workflow `game-bgm`; styles `rpg-town`, `rpg-battle`, `dungeon-ambient`, `chiptune-adventure`, `puzzle-calm`, `synthwave-drive`.
- **Ask for a loop-friendly structure up front**: steady, repetitive, no long intro, no outro, no crescendo. A track that builds and resolves cannot loop well however the seam is handled.
- The `loop` step folds the last 2 s over the first 2 s and (given a BPM) snaps the length to whole bars. It picks the crossfade law from how similar the two passages are, so repetitive drum loops do not bump in level.
- **Read the QC line.** `seam_vs_typical` near 1 = the seam is as natural as any bar line. `click_ratio` above ~4 or `seam_vs_typical` above ~4 = audition `*.loop-preview.*` (the track played twice) before shipping.
- **Limits you should state**: the loop is made by crossfading, so it works best when the model kept a steady tempo. The BPM in the spec is a request, not a guarantee - if the generated tempo drifted from it, bar-snapping lands off the beat. The model also does not return stems, so there is no layered/adaptive music in phase 1; for "exploration vs combat" generate two tracks in the same key and BPM and crossfade them in the engine.
- Export `ogg` (small, loops cleanly in Unity/Godot/FMOD) and `wav` (source). Avoid mp3 for loops: its encoder delay adds a gap at the seam.

## Video / short-film score

- Workflow `video-score`; styles `cinematic-emotional`, `cinematic-tension`, `corporate-upbeat`, `epic-trailer`, `nature-piano`.
- Get the **exact duration** from the person (seconds). Generate slightly longer than needed, then `fit` cuts to the exact length and `fade` gives a natural end.
- Describe the **arc**, not just the mood: "calm for 15 s, builds, resolves". The model follows an arc loosely; do not promise it hits a cue at a precise second. If a hit point matters, generate, find where the swell lands, and trim the start so it lines up.
- Dialogue sits on top: the workflow normalises to -18 LUFS instead of -16 so the music stays under speech. Adjust `target_lufs` if the person's platform or mix wants something else.
- Deliver `wav24` for the editor and `mp3` for quick review.

## Work / study background

- Workflow `focus-session`; styles `lofi`, `ambient-focus`, `jazz-cafe`, `nature-piano`, `chill-electronic`.
- Add the `focused` mood: it asks for steady, unobtrusive material with little melodic change.
- Long durations are capped per tier (`max_duration`); for an hour of audio, generate a 5-10 minute track and loop it with the player, or generate several in the same style and playlist them.
- Quieter target (-20 LUFS) and long fades make it easy to leave running.

## Personal creation

- Workflow `quick` or `sketch`. Explore with `sketch` (cheap drafts, 3 variants), then regenerate the favourite at `high`/`max` quality **with the same seed and caption**. It often keeps the draft's character with better fidelity, but different steps or thinking mode can change the arrangement, so audition it as a new take.
- Rate and annotate takes in the dashboard so good seeds are findable later.

## Matching a described feeling to a style

| They say | Start from | Add moods |
|---|---|---|
| "cozy", "rainy day", "study" | `lofi` | `cozy`, `nostalgic` |
| "peaceful town", "farm" | `rpg-town` | `calm`, `hopeful` |
| "boss fight", "chase" | `rpg-battle` | `epic`, `tense` |
| "creepy", "cave" | `dungeon-ambient` | `eerie` |
| "retro", "arcade" | `chiptune-adventure` | `playful`, `energetic` |
| "sad scene", "memory" | `cinematic-emotional` | `melancholic`, `nostalgic` |
| "product demo", "startup" | `corporate-upbeat` | `hopeful` |
