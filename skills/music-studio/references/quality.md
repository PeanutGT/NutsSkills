# When the result sounds bad (checklist, in order of payoff)

Open the take's **「實際使用的設定」** panel in the dashboard (or `python scripts/library.py show ID` -> `effective`, `warnings`). Most "bad quality" is a setting that silently did not apply.

Both ways of running a job (the server, used by the dashboard and `msclient.py`, and the direct `engine.py generate`) record the same `effective` / `warnings`. The server path can also change settings between jobs: after a CPU decode it turns on DiT offload and caps the batch at 1 for the next job, and an OOM is retried once in the same job with the same changes; both are listed in `warnings`. When comparing two takes, check that panel before blaming the prompt.

The **automatic check** (shown under the comparison deck, `variants[].qc` in the take) points at problems you can hear: clipping, clicks, a cut-off ending, a silent gap, near silence, low volume. It is a heuristic: an empty list does not mean it sounds good, and a flagged click in a loud passage may be inaudible. Use it to know where to listen.

| Symptom | Likely cause | Fix |
|---|---|---|
| Does not sound like what you described | Your words never reached the caption (older versions), a style fought your description, or no LM ("thinking") | Look at the **caption preview** before generating; use style `from-description`; make sure the panel shows a language model; keep <= 12 tags; say what to omit as `no percussion` |
| Rough / noisy / metallic | int8 quantization (`low` tier only should use it), too few steps for a non-turbo model, very long duration | `msconfig.py show` -> `hardware.tiers.<tier>.quantization` should be `null` on 6 GB+ cards; keep turbo at 8 steps, sft/base at 32-64; generate <= 120 s |
| Structure wanders, tempo drifts, odd endings | Duration too long for the model; a big BPM/key conflict with the caption | 30-120 s, then loop. Give BPM and key once and do not contradict them in the caption |
| "high"/"max" sounds the same as "standard" | `acestep-v15-sft` is not installed, so they fell back to turbo (a warning says so) | `python scripts/engine.py models --download acestep-v15-sft` |
| A setting seems ignored | Your ACE-Step build does not know it (panel lists "ignored settings") | Update ACE-Step (`git pull`, `uv sync`) or drop the setting |
| Same prompt, every variant different | Normal: each variant has its own seed | Keep the seed of the one you like and change ONE tag ("以這版為基礎微調再生") |

## Tier expectations
- **low (<6 GB)**: turbo 2B, no LM, int8. Fast and usable for ideas; caption adherence is the weakest here - write precise tags yourself.
- **mid (6-12 GB)**: turbo 2B + LM 0.6B, no quantization. The sweet spot for most cards.
- **high (12-20 GB)**: turbo + LM 1.7B; **ultra (20 GB+)**: XL turbo + LM 4B.
- Quality `high`/`max`: sft model, 50-64 steps; 5-8x slower than `standard`, better detail and coherence.

## Workflow that gets good results
1. Draft with `draft`/`standard` (several variants, short, 30-60 s).
2. Pick one; "微調再生" with its seed, changing a single tag.
3. Re-render the keeper at `high` with the same seed; audition it as a new take.
4. Finalize (loop / loudness / export).
