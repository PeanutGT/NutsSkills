---
name: spec
description: "Use when requirements are agreed and need to become a written spec with testable acceptance criteria, before planning or implementing a feature."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Write a spec

**Core rule:** Every acceptance criterion must be checkable by a test or a single observable action.

## Process
1. Start from the decisions made in `clarify`. If none exist and the request is non-trivial, run `clarify` first.
2. Write the spec using the template below. Keep it short: one page for most features.
3. Write acceptance criteria as **Given / When / Then**. One behavior per criterion.
4. Mark anything unresolved as `OPEN:` — do not hide it.
5. Show the spec to the user and get approval. Save it where the project keeps docs (default `docs/specs/<feature>.md`).

## Template

```markdown
# <Feature name>

## Goal
One or two sentences: the problem and who has it.

## Scope
- In: ...
- Out: ...

## Acceptance criteria
- AC1: Given <state>, when <action>, then <observable result>.
- AC2: ...

## Edge cases and errors
- <input or condition> → <expected behavior>

## Constraints
Performance, security, compatibility, dependencies.

## Open questions
- OPEN: ...
```

## Good acceptance criteria
| Weak | Strong |
|---|---|
| "Search is fast" | "Given 10k records, search returns in < 200 ms (p95)" |
| "Handles bad input" | "Given an email without '@', submit shows 'Invalid email' and nothing is saved" |
| "Users can log in" | Split: valid login, wrong password, locked account, expired session |

## Done when
- [ ] Every AC is testable and covers one behavior
- [ ] Scope in/out is explicit
- [ ] No `OPEN:` items, or the user accepted them
- [ ] User approved the spec

Next: `plan`.
