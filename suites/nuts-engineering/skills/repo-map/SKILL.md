---
name: repo-map
description: "Use when starting work in an unfamiliar or large repository, before broad grep/glob/read exploration, or when you need to know where a function, class, or module is defined and which files use it. Builds a compact map of files, public symbols, and imports so you open only the files that matter."
license: Apache-2.0
compatibility: Needs Python 3.9+ to run scripts/repo_map.py (stdlib only). Uses git ls-files when the folder is a git repo.
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Repo map

**Core rule:** Know the structure before you read the code. Open a file only when the map or `--find` points to it.

The map lists every source file with its public symbols, signatures, imports, and reverse imports in roughly 1/20 to 1/30 of the size of the source. It pays off for structure questions; for a question with a distinctive keyword, one targeted grep is just as cheap.

## When to use
- First task in an unfamiliar repo: "how is this project organized?", "where would X live?"
- "What calls Y?", "where is Z defined?" when you know a symbol name
- Before a change that may touch several files (pairs with `plan`)

Skip it for a one-file change when you already know the file, and when a single grep on a distinctive word (an error message, a config key) answers the question.

## Process
1. **Know a symbol name? Use `--find` first** (run from the repo root; `SKILL_DIR` is this skill's folder):
   ```bash
   python SKILL_DIR/scripts/repo_map.py . --find run_for_take
   ```
   Output: `file:line  signature`, then `referenced at:` with every line that mentions the name in the defining file and in files that import it. This is usually the whole answer to "what calls Y?".
2. **Need the big picture? Build the map**:
   ```bash
   python SKILL_DIR/scripts/repo_map.py .
   ```
   It writes `.nuts/repo-map.md`. Do not read it whole on a large repo: grep it for a folder or keyword (`grep -n "^## src/billing" .nuts/repo-map.md`) and read only those sections. Rebuild after large changes.
3. **Open only the candidate files**, and only the relevant line ranges when files are long.
4. Fall back to grep for things the map cannot show: private names, string literals, config keys, dynamic dispatch.
5. Do not re-verify what `--find` already showed with a second repo-wide grep.

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
