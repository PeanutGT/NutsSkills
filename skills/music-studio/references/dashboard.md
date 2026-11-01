# Local dashboard

```
start_dashboard.bat                     (Windows, double-click)
python scripts/server.py [--port N] [--no-open]
python scripts/msclient.py url          start it in the background if needed and print the URL
```

The server is also the single owner of the GPU: it runs the job queue and the persistent ACE-Step worker
(docs/ARCHITECTURE.md). Claude's `msclient.py` and the dashboard submit to the same queue, so a job Claude starts
shows up live in the dashboard and vice versa. Only one server runs per workspace; starting a second one just
opens the first.

## Layout
- **Engine readout** (top right): whether models are loaded, free / total VRAM, a button to free VRAM now.
- **創作**: describe the track; the "會送給 ACE-Step 的內容" box shows, live, the exact caption tags (yours are outlined in amber), BPM, key, model, steps, LM and quantisation, and lets you edit the caption by hand. Under the moods, **樂器** shows the style's suggested (✓) and avoided (✕) instruments as chips; click one to cycle use -> avoid -> neutral, which switches to your own instrumentation (改回依風格 resets it). Submitting more than once queues.
- **Comparison deck**: all variants of a take stacked on one bar-line ruler with one playhead. Space plays/pauses, number keys switch variant at the same position, arrows seek 5 s, clicking a waveform seeks there. "選定目前這版", "用目前這版微調再生" (same seed, edit one tag), rating, favourite.
- **Automatic check**: under the deck, the issues found in each variant when it was generated (clipping, clicks, cut-off ending, a silent gap, near silence, low volume) with their times; a variant with issues shows ⚠ in its lane.
- **後製與匯出**: runs the chosen workflow's steps on the variant you are listening to. 響度 picks a loudness preset (影片平台 -14, 遊戲 BGM -16, 背景／讀書 -18 LUFS) instead of the workflow's own target. Shows loudness, true peak, length, loop seam (for loops), the automatic check of the finished file, a loop preview and download buttons.
- **實際使用的設定**: what really ran (model, steps, LM, quantisation, DiT offload, CPU-decode fallback, settings your ACE-Step build ignored).
- **Queue dock** (bottom): the running job's phases (載入模型 / 編碼提示 / 生成 / 解碼音訊 / 寫檔) with elapsed time and cancel; queued jobs with their own cancel; the last finished jobs (click to open).
- **資料庫**, **設定**: library with search/favourites; common settings and the style editor (writes only to your workspace).

## Safety
- Binds `127.0.0.1` only; `Host` must be localhost; every write needs the per-start token (embedded in the page, and written to `<workspace>/server.json` for msclient).
- Cancel kills the worker (the only way to stop CUDA work); the partial take goes to `<workspace>/trash`, never into the library.
- Deleting a take or style moves it to `<workspace>/trash`. Audio is only served from inside take folders.

## API
`GET /api/state`, `POST /api/plan`, `GET /api/check`,
`POST /api/jobs` (`{"spec":{...}}` or the form fields), `GET /api/jobs?since=SEQ&wait=1` (long poll), `GET /api/jobs/<id>`, `POST /api/jobs/<id>/cancel`,
`GET /api/worker`, `POST /api/worker/unload`,
`GET /api/tracks`, `GET|PATCH|DELETE /api/tracks/<id>`, `POST /api/tracks/<id>/finalize`,
`GET|PUT /api/config`, `PUT|DELETE /api/{styles,moods,workflows}/<id>`, `GET /audio/<take>/<file>` (Range; `?download=1`).

## Notes
- Fonts (Barlow Condensed, Noto Sans TC) load from Google Fonts; offline the page uses system fonts.
- Waveforms are decoded in the browser from the take's audio; very long takes take a moment to draw.
