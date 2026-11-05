---
name: repo-map
description: "Use when starting work in an unfamiliar or large repository, before broad grep/glob/read exploration, or when you need to know where a function, class, or module is defined and which files use it. Builds a compact map of files, public symbols, and imports so you open only the files that matter."
license: Apache-2.0
compatibility: Needs Python 3.9+ to run scripts/repo_map.py (stdlib only). Uses git ls-files when the folder is a git repo.
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Repo map

**Core rule:** Read the map before you read the code. Open a file only when the map says it is relevant.

Exploring by grepping and reading whole files burns context. The map lists every source file with its public symbols, signatures, imports, and reverse imports in roughly 1/20 to 1/30 of the size of the source.

## When to use
- First task in a repo you have not mapped in this session
- "Where is X handled?", "what calls Y?", "how is this project organized?"
- Before a change that may touch several files (pairs with `plan`)

Skip it for a one-file change when you already know the file.

## Process
1. **Build or refresh the map** (run from the repo root; `SKILL_DIR` is this skill's folder):
   ```bash
   python SKILL_DIR/scripts/repo_map.py .
   ```
   It writes `.nuts/repo-map.md` and prints its size against the source. Rebuild after large changes or when the map is from an earlier session.
2. **Read `.nuts/repo-map.md`** (or `--stdout` for small repos). Use it to pick candidate files.
3. **Look up a symbol directly** when you know its name:
   ```bash
   python SKILL_DIR/scripts/repo_map.py . --find total
   ```
   Output: `file:line  signature` and the files that import that file.
4. **Open only the candidate files**, and only the relevant line ranges when files are long.
5. Fall back to grep for things the map cannot show: private names, string literals, config keys, dynamic dispatch.

## What the map contains
```
## shop/cart.py (16 lines)
- def load_items(path)
- def total(path, *, rounding=2)
imports: shop/models.py
used by: tests/test_cart.py
```
- Python is parsed with `ast` (classes, methods, functions, signatures, relative and absolute imports).
- JS/TS: exported functions, classes, consts, interfaces/types; relative imports are resolved to files.
- Go, Rust, Java, Kotlin, C#, Ruby, PHP, Swift: top-level types and public functions by pattern. Imports are not resolved for these.
- Private names (leading `_`) are hidden. Vendored and build folders (`node_modules`, `dist`, `.venv`, …) are skipped.

## Rules
- Add `.nuts/` to `.gitignore` if the user does not want the map committed. Ask before editing `.gitignore`.
- The map is a guide, not truth: confirm by opening the file before you edit or cite a line.

## Done when
- [ ] The map was built or refreshed this session
- [ ] Files were opened because the map pointed to them, not by blind search

Related: `plan`, `debug`, `nutshell`.
