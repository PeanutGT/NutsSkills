---
name: ship
description: "Use when committing changes, writing a commit message, opening a pull request, or finishing a development branch. Covers branch naming, commit hygiene, PR descriptions, and the pre-merge checklist."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Ship

**Core rule:** Nothing leaves your machine without passing `verify`.

## Branches
- Never commit directly to the default branch. Create `type/short-description` (e.g. `feat/csv-export`, `fix/login-timeout`).
- One branch, one purpose.

## Commits
- Each commit is one coherent change that builds and passes tests.
- Stage specific files; review `git diff --staged` before committing. Never commit secrets, build output, or local config.
- Message format:
  ```
  <type>: <what changed, imperative, ≤ 72 chars>

  <why: the problem and the reason for this approach>
  ```
  Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`.
- The subject says *what*; the body says *why*. The diff already shows *how*.

## Pull requests
Template:
```markdown
## What
One or two sentences.

## Why
The problem or ticket link.

## How
Key decisions and trade-offs; anything surprising.

## Testing
Commands run and results. Manual steps if any.

## Risk
What could break; rollback plan if relevant.
```
- Keep PRs small enough to review in one sitting (rough guide: < 400 changed lines).
- Separate refactors from behavior changes.

## Pre-merge checklist
- [ ] Tests, lint, type-check, build pass (output seen)
- [ ] Diff contains only intended changes
- [ ] No debug logs, TODOs without tickets, or commented-out code
- [ ] Docs / changelog updated if behavior changed
- [ ] Migrations reversible; feature flags in place for risky changes

## Finishing a branch
After merge: delete the branch, close related tickets, and note follow-ups.

## Rules
- Ask before pushing, force-pushing, or merging unless the user already said to.
- Never skip hooks (`--no-verify`) to make a commit pass. Fix the cause.

Related: `verify`, `code-review`.
