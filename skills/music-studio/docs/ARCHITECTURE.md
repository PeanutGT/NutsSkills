# Music Studio architecture (v3)

## 1. Requirements

Functional:
- Turn a description into instrumental tracks on the person's own NVIDIA GPU (ACE-Step 1.5), audition variants, refine, post-process and keep a library.
- Two front doors, one engine: the **dashboard** and **Claude** (CLI calls from the skill) must share the same GPU and see the same jobs.
- Everything customisable lives in the workspace (config, styles, moods, lexicon, workflows).

Non-functional, measured on the reference machine (RTX 3050 Laptop, 4 GB, Windows):
- A 60 s track diffuses in ~8 s, but every run paid ~15 s of process start + model load + int8 quantisation before that. **Model load dominates short jobs**, so the models have to stay loaded between jobs.
- 4 GB is below ACE-Step's own comfortable floor. The failure mode is not an OOM error but a **silent CPU fallback** for VAE decoding that looks like a hang for 7+ minutes. VRAM handling must be explicit and visible.
- One person, one machine, localhost only. No accounts, no network exposure, no database server.
- Closing a window or pressing cancel must never leave the GPU stuck or a half-written take that the library shows as real.

Constraints: stdlib-only on the skill side (no pip install into the person's Python); ACE-Step runs in its own venv; the ACE-Step API drifts between releases.

## 2. High-level design

```
 Claude (skill)                    Browser (dashboard)
   msclient.py ──HTTP──┐        ┌──HTTP── app.js
                       ▼        ▼
                 ┌──────────────────────┐        workspace/
                 │ server.py (stdlib)   │──────► config.json, styles/, lexicon.json
                 │  - REST API + static │        output/<take>/{spec,meta,v*.flac,final/}
                 │  - JobQueue (1 GPU)  │──────► jobs.json  (queue + history, atomic writes)
                 │  - WorkerSupervisor  │
                 └─────────┬────────────┘
                           │ stdin/stdout JSON lines (one request -> event stream)
                           ▼
                 ┌──────────────────────┐   runs in ACE-Step's .venv
                 │ ace_worker.py        │   models stay loaded between jobs
                 │  - load/keep models  │   loguru sink -> phase events
                 │  - VRAM guard        │   idle timeout -> unload + exit
                 └──────────────────────┘
```

- **server.py** is the only process that talks to the GPU worker. It owns the queue, so the dashboard and Claude can never start two generations at once.
- **msclient.py** is what the skill calls. If the server is running it submits the job there and streams events; if not, it starts the server in the background first (no browser) and then submits. The old direct path (`engine.py generate`) stays for tests and as a fallback with `--direct`.
- **ace_worker.py** replaces the one-shot `engine_ace.py` run. It is started lazily on the first job, keeps `AceStepHandler`/`LLMHandler` alive, and reloads only when the model set changes (tier, preset `dit_model`, LM, quantisation, offload flags).
- **mock engine** implements the same worker protocol in-process so the whole stack is testable without a GPU.

## 3. Deep dive

### 3.1 Worker protocol (stdin/stdout, JSON lines)
Request (one line on stdin): `{"op":"generate","job":"j_…","models":{…},"params":{…},"out_dir":…}` or `{"op":"unload"}` / `{"op":"ping"}` / `{"op":"quit"}`.
Events (stdout, one per line, always carrying `job`):
`phase` (`loading_models | encoding | diffusing | decoding | writing`, with `pct` and `detail`), `warn`, `result`, `error` (`code`, `message`, `hint`), `ready` (after each job, with `models_loaded`, `vram_free_gb`).
Everything ACE-Step prints goes to stderr; the server keeps the last 400 lines per job.

Progress comes from two sources: ACE-Step's own progress callback (an overall 0-1 value; earlier versions of this skill rescaled it wrongly) and a loguru sink that recognises phase changes (`Decoding latents with VAE`, `auto-enabling CPU VAE decode`, `[tiled_decode] chunk_size`). Phases are what the UI shows; percentages are only a hint inside a phase.

### 3.2 VRAM guard
Before each job the worker computes a plan from the **measured** total VRAM, not just the tier name:

| total VRAM | DiT placement | quantisation | LM | decode |
|---|---|---|---|---|
| < 6 GB | offloaded between phases (`offload_dit_to_cpu`) | int8 | none | GPU, tiled |
| 6-8 GB | offloaded | none | 0.6B (pt) | GPU, tiled |
| >= 8 GB | as the tier says | as the tier says | as the tier says | GPU |

After diffusion, if ACE-Step logs a CPU decode fallback anyway, the worker emits `warn` with code `cpu_decode` immediately and the UI shows the elapsed time for that phase with a cancel button. The next job automatically tightens the plan (offload DiT, cap batch to 1) and says so. Config can override every choice; the guard only fills in values the person did not set.

### 3.3 Job queue
`jobs.json` in the workspace: `queued → running → done | failed | cancelled`, with spec, timestamps, events summary and the take id. Writes are atomic (temp file + replace). On server start, `running` jobs from a previous crash become `failed: interrupted`. Cancel of a queued job removes it; cancel of the running job kills the worker (models reload on the next job — the only reliable way to stop CUDA work) and moves the partial take folder to `trash/`.

### 3.4 Takes
A take folder is created when the job **starts**, but only gets `meta.json` when it **succeeds**. The library lists folders with `meta.json` only, so failed or cancelled runs never appear as empty takes (the three empty `frontlines-defeat` folders on the reference machine were exactly this).

### 3.5 API (localhost, token on every write)
```
GET  /api/state                 config summary, styles, moods, workflows, worker status
POST /api/plan                  preview: caption, params, warnings (no generation)
POST /api/jobs                  enqueue {spec or form}            -> {job}
GET  /api/jobs?since=<seq>      queue + recent history, incremental
GET  /api/jobs/<id>             one job with recent events and log tail
POST /api/jobs/<id>/cancel
GET  /api/worker  POST /api/worker/unload
GET  /api/tracks  GET|PATCH|DELETE /api/tracks/<id>  POST /api/tracks/<id>/finalize
GET|PUT /api/config   PUT|DELETE /api/{styles,moods,workflows}/<id>   GET /api/check
GET  /audio/<take>/<file>       Range support
```
Polling (1 s while a job runs, 10 s idle) instead of SSE/WebSocket: one local user, simple, works through any browser, no long-lived connections to babysit.

### 3.6 Errors and retries
- OOM: retry once with batch 1 and DiT offload, then fail with the hint.
- Worker crash (non-zero exit, no `result`): job fails with the stderr tail; the next job starts a fresh worker.
- LM load failure: continue without thinking, warn (unchanged).
- Idle: the worker unloads and exits after `engine.idle_unload_minutes` (default 10) so a laptop GPU is not held for games or other work.

## 4. Scale and reliability
Scale is one person and one GPU; the queue exists for correctness (never two CUDA jobs), not throughput. Reliability work goes into the edges that actually failed: silent CPU decode, killed windows, half-written takes, and model-load cost.

## 5. Trade-offs
| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Persistent engine | own `ace_worker.py` over stdin/stdout | ACE-Step's FastAPI server (`acestep-api`) | Keeps control of offload flags, the VRAM guard and phase parsing; no second port; the param mapping already exists. Revisit if ACE-Step's API gains features we would otherwise reimplement. |
| Queue store | `jobs.json` | SQLite | A handful of jobs per session; human-readable; stdlib either way. Move to SQLite if history grows past a few thousand jobs. |
| Live updates | polling | SSE | Fewer moving parts on a stdlib server; the cost is up to 1 s latency. |
| Cancel | kill the worker | cooperative cancel flag | ACE-Step has no cancellation hook inside diffusion/decoding. Cost: a model reload after cancel. |
| CLI path | via server | direct subprocess | One queue for both front doors; direct path kept for tests. |

## 6. What to revisit as it grows
- Phase 2 (vocals) adds the LM to more jobs: the VRAM guard needs an LM-aware plan for 4-6 GB cards.
- Multiple GPUs or a remote GPU box: the worker protocol already works over any pipe; the server would need a worker pool.
- If ACE-Step adds a cancellation hook, switch cancel to cooperative and keep the models loaded.
