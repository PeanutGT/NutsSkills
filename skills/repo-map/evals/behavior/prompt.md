In a copy of this repo with skills/repo-map removed, the user asks:

"How does music-studio turn a loudness preset like 'video' or 'game' into actual loudnorm settings, and which other module calls that code path? Answer with file:line references."

Answer key: `resolve_loudness()` in skills/music-studio/scripts/postprocess.py (about line 402) maps the preset name or a LUFS number to loudnorm parameters; `run_for_take()` in the same file calls it (about line 491); `server.py` (about line 179) calls `postprocess.run_for_take`.
