---
name: plan
description: "Use when work has more than a few steps, touches several files, or follows an approved spec, before starting implementation. Breaks the work into small vertical slices that can each be verified on their own."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Plan the work

**Core rule:** Write the plan so that an engineer with zero context on this codebase could execute it — and no longer than that requires.

## Process
1. Read the spec (or the agreed requirements) and the code areas involved (`repo-map` helps in a large repo).
2. Note existing patterns, utilities, and tests to reuse. Do not plan new code where suitable code exists.
3. Split the work into **vertical slices**: each delivers one working, testable behavior end to end (not "all models, then all controllers").
4. Order slices so each builds on a working previous one. Put the riskiest or most uncertain slice early.
5. Write the plan with the header and slice template below.
6. Run the self-review, fix what it finds, then show the plan to the user.
7. Execute one slice at a time with `tdd` and `verify`.

## Plan header
```markdown
# <Feature> plan
Goal: one sentence.
Approach: two or three sentences.
Spec: docs/specs/<feature>.md
Constraints: rules every slice must respect (no new dependencies, keep API X stable, ...)
```

## Slice template
```markdown
### Slice N: <behavior>
- Covers: AC1, AC3
- Files: path/to/file.ts (modify), path/to/new.ts (create)
- Interfaces: new or changed signatures, named exactly
- Tests first: <test names / cases>
- Steps:
  1. ...
- Verify: <exact command> → <expected result>
```

## Sizing
- A slice takes minutes to an hour, not days. More than ~5 steps or ~5 files: split it.
- Each step is one action with a checkable result: "add test X", "make it pass", "run suite".
- A step says *what* to build, not a transcript of the code. Code belongs in the code.

## Self-review (before showing the plan)
- [ ] **Coverage:** every acceptance criterion maps to a slice
- [ ] **Failure modes:** each error case and edge case in the spec has a test in some slice
- [ ] **Consistency:** names, types, and signatures used in later slices match where they were defined
- [ ] **One thing per step:** no step hides a design decision the implementer must invent
- [ ] **Proportion:** the plan is not several times longer than the spec it implements

## While executing
- Mark a slice done only after its verify command passes.
- If reality differs from the plan, stop and update the plan before continuing.
- Do not quietly expand scope. New ideas go into a "Later" list.

## Done when
- [ ] Self-review passed
- [ ] Every slice has files, tests, and a verify command
- [ ] User approved the plan

Related: `spec`, `tdd`, `verify`, `repo-map`.
