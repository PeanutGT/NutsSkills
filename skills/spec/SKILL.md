---
name: spec
description: "Use when requirements are agreed and need to become a written spec with testable acceptance criteria, before planning or implementing a feature."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Write a spec

**Core rule:** A builder who was not in the conversation must be able to build from it, and every acceptance criterion must be checkable by a test or one observable action.

## Process
1. Start from the decisions made in `clarify`. If none exist and the request is non-trivial, run `clarify` first.
2. Write the spec with the template below. Keep it short: one page for most features.
3. Acceptance criteria as **Given / When / Then**, one behavior each.
4. Mark anything unresolved as `OPEN:`. Mark choices you made yourself as `Our call:` so the user can check them.
5. **Builder check.** Before handing it over, read it as someone who has seen only this document (or give it to a fresh-context reviewer; see `fresh-eyes`). Sort every question that comes up into three piles:
   - **Already answered** in the conversation or the code → write the answer into the spec.
   - **Minor** — a sensible builder could settle it without changing what gets built → decide, mark `Our call:`.
   - **Theirs** — only the user can answer, and the answer changes what gets built → ask them, most important first, in one message.
6. Get approval. Save where the project keeps docs (default `docs/specs/<feature>.md`).

## Template

```markdown
# <Feature name>

## Goal
One or two sentences: the problem and who has it.

## Scope
- In: ...
- Out (non-goals): ...

## Approach
The option chosen and why; the alternatives considered in one line each.

## Acceptance criteria
- AC1: Given <state>, when <action>, then <observable result>.
- AC2: ...

## Edge cases and errors
- <input or condition> → <expected behavior>

## Constraints
Performance, security, compatibility, dependencies.

## Open questions and our calls
- OPEN: ...
- Our call: ... (because ...)
```

## Good acceptance criteria
| Weak | Strong |
|---|---|
| "Search is fast" | "Given 10k records, search returns in < 200 ms (p95)" |
| "Handles bad input" | "Given an email without '@', submit shows 'Invalid email' and nothing is saved" |
| "Users can log in" | Split: valid login, wrong password, locked account, expired session |

## Done when
- [ ] Every AC is testable and covers one behavior
- [ ] Scope and non-goals are explicit
- [ ] Builder check done; no `OPEN:` items left, or the user accepted them
- [ ] User approved the spec

Next: `plan`.
