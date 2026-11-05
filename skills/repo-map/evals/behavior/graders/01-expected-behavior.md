# Expected behavior

Pass if: the agent runs scripts/repo_map.py (build or --find) before opening source files, opens at most the files the map points to, and answers with file:line references. Fail if it reads many files or greps the whole tree first.
