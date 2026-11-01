# Styles, moods and workflows (all user-extensible)

Drop a file in your workspace and it is live - no restart, no skill edit. After changing anything run
`python scripts/msconfig.py validate`.

| What | Skill default | Your workspace | Merge rule |
|---|---|---|---|
| Style | `defaults/styles/<id>.json` | `<ws>/styles/<id>.json` | same `id` -> your fields override the built-in's; add `"$replace": true` to replace it entirely |
| Moods | `defaults/moods.json` | `<ws>/moods.json` | same shape, merged by mood id |
| Workflow | `defaults/workflows/<id>.json` | `<ws>/workflows/<id>.json` | same as styles |

Deleting your file reverts to the built-in. The dashboard's delete button moves your file to `<ws>/trash/`.

## Style

```json
{
  "id": "rainy-lofi",
  "name": "Rainy Lo-fi",
  "description": "Lo-fi with rain texture.",
  "caption": "lo-fi hip hop, instrumental, mellow, soft rain ambience, warm Rhodes piano",
  "avoid": "vocals, bright hi-hats",
  "bpm": [68, 80],
  "keys": ["A minor", "D minor"],
  "time_signature": "4",
  "duration": {"min": 60, "default": 150, "max": 480},
  "loopable": true,
  "tags": ["focus"],
  "notes": "Anything Claude should remember when using this style."
}
```

Required: `id` (or the file name), `name`, `caption`. `bpm` is a number or `[min, max]` (the midpoint is used) or `null` for beatless styles. `keys` is a list; one is chosen per seed. `loopable` decides whether `when: loopable` post-processing steps run. `avoid` and `notes` are guidance for Claude and for you; they are not sent to the model.

`instruments` (optional) lists lexicon instrument ids (`msconfig.py instruments`):

```json
"instruments": {"suggest": ["rhodes", "drums", "bass"], "avoid": ["guitar-electric", "trumpet"]}
```

- `suggest`: the default instrumentation. A suggested instrument the caption does not already mention is added as a tag.
- `avoid`: style and mood tags that mention these instruments are dropped (detected by the entry's English `match` words, e.g. `strings` finds "driving strings ostinato").
- A request can replace the set: `plan --instruments erhu,guzheng` (dashboard: the 樂器 chips; click cycles use -> avoid -> neutral). Style tags for suggested instruments that were not picked are dropped, and the style's avoid list no longer applies, only the request's `--avoid-instruments` and the moods'.
- Instruments named in the description always win, with a warning when the style usually avoids them.
- Moods may carry `"instruments": {"avoid": [...]}` too.

`msconfig.py validate` reports unknown ids. To add an instrument, add a lexicon entry with `"group": "instrument"` (optional `label_zh` for the chip label).

## Mood

```json
"rainy": {"caption": "rainy, grey, introspective", "bpm_delta": -6}
```

Tags are appended to the style's caption (duplicates removed); `bpm_delta` shifts the style tempo but is kept within 10 BPM of the style's range.

## Workflow

A workflow is the ordered list of stages a track goes through, which of them pause for a human decision, and what the final processing does.

```json
{
  "id": "my-loop",
  "name": "My loop recipe",
  "description": "...",
  "defaults": {"quality": "high", "variants": 3, "duration": 90},
  "stages": [
    {"id": "plan",        "gate": "confirm", "note": "Confirm style/BPM/key/length"},
    {"id": "generate",    "gate": "auto"},
    {"id": "audition",    "gate": "pick"},
    {"id": "postprocess", "steps": [
      {"op": "trim_silence"},
      {"op": "loop", "crossfade": 2.0, "snap_bars": true, "when": "loopable"},
      {"op": "loudnorm", "target_lufs": -16, "true_peak_db": -1.5},
      {"op": "export", "formats": ["ogg", "wav"]}
    ]}
  ]
}
```

- **Stage ids**: `plan`, `generate`, `audition`, `postprocess`. `generate` is mandatory.
- **Gates**: `auto` = continue without asking; `confirm` = show the plan and wait for a yes; `pick` = the person chooses a variant. Claude honours gates in conversation; the dashboard shows the same stages as buttons.
- **`defaults`** fill `quality`, `variants`, `duration` when the request leaves them out.
- **Post-processing ops** run in the order listed. Ops: `trim_silence` (`threshold_db`, `keep_tail`), `fit` (`duration` seconds or `"spec"`, `snap` `none|bars`), `fade` (`in`, `out` seconds), `loop` (`crossfade`, `snap_bars`), `loudnorm` (`target_lufs`, `true_peak_db`), `export` (`formats`: `flac wav wav24 mp3 ogg opus m4a`). Any step may add `"when": "loopable"` or `"not_loopable"`.
- Order matters: `fit` before `fade`; `loop` before `loudnorm` (so the crossfade does not change the level you just set); `export` last.

## Built-in workflows

`quick` (everyday), `sketch` (3 fast drafts, no mastering), `game-bgm` (seamless loop, ogg+wav), `video-score` (exact length, fade, -18 LUFS, wav24+mp3), `focus-session` (5 min, quiet -20 LUFS, mp3).


## Lexicon (your words -> English tags)

`defaults/lexicon.json` maps words in the plain-language description to caption tags (instruments, textures, scenes, moods, tempo). Longest match wins, `不要鼓` removes drum tags from the style, unknown Chinese is reported (never guessed), English fragments pass through. Extend or override in `<workspace>/lexicon.json`:

```json
{ "雨夜咖啡": { "match": ["雨夜咖啡", "rainy cafe"], "tags": "rainy night cafe, soft jazz piano", "group": "scene", "bpm_delta": -6 } }
```
`"tags": ""` disables a built-in entry. List entries: `python scripts/msconfig.py lexicon`. The `from-description` style adds nothing of its own, so the description drives the whole caption.
