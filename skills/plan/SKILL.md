---
name: plan
description: "Use when work has more than a few steps, touches several files, or follows an approved spec, before starting implementation. Breaks the work into small vertical slices that can each be verified on their own."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Plan the work

**Core rule:** Write the plan so that an engineer with zero context on this codebase could execute it.

## Process
1. Read the spec (or the agreed requirements) and the code areas involved.
2. Note existing patterns, utilities, and tests to reuse. Do not plan new code where suitable code exists.
3. Split the work into **vertical slices**: each slice delivers one working, testable behavior end-to-end (not "all models, then all controllers").
4. Order slices so each builds on a working previous one. Riskiest or most uncertain slice early.
5. For each slice, fill in the template below.
6. Show the plan to the user; adjust; then execute one slice at a time with `tdd` and `verify`.

## Slice template

```markdown
### Slice N: <behavior>
- Covers: AC1, AC3
- Files: path/to/file.ts (modify), path/to/new.ts (create)
- Tests first: <test names / cases>
- Steps:
  1. ...
- Verify: <exact command> → <expected result>
```

## Sizing
- A slice should take minutes to an hour, not days.
- If a slice has more than ~5 steps or touches more than ~5 files, split it.
- Each step is one action: "add test X", "make it pass", "run suite".

## While executing
- Mark each slice done only after its verify command passes.
- If reality differs from the plan, stop and update the plan before continuing.
- Do not quietly expand scope. New ideas go into a "Later" list.

## Done when
- [ ] Every acceptance criterion maps to at least one slice
- [ ] Every slice has files, tests, and a verify command
- [ ] User approved the plan

Related: `spec`, `tdd`, `verify`.
