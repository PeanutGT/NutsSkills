# Expected behavior

Pass if: the answer names `resolve_loudness` in postprocess.py, `run_for_take` as its caller, and `server.py` as the other module, with file:line references; and the agent built the map or used `--find` before opening source files.

Compare with a baseline run without the skill on: correctness, number of files read, and total tokens used (see `skills/nutshell/evals/RESULTS.md`).
