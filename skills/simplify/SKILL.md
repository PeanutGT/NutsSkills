---
name: simplify
description: "Use when code works but is hard to read or change, after a feature is complete and green, or when asked to refactor or clean up. Reduces complexity without changing behavior."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Simplify

**Iron law:** Behavior does not change. Tests are green before you start and after every step.

## When to use
- After `tdd` gets a feature green (the refactor step at a larger scale)
- Code review flagged complexity
- You need to change code that is too tangled to change safely

Do not mix simplification with feature work in the same commit.

## Process
1. **Safety net.** Confirm tests cover the code. If not, add characterization tests first.
2. **Find the biggest simplification**, in this order:
   1. Delete: dead code, unused params, stale flags, commented-out code
   2. Inline: one-use helpers and abstractions that hide nothing
   3. Merge: true duplication (same reason to change, not just similar text)
   4. Rename: unclear names to domain words
   5. Restructure: long functions into steps, nested conditionals into guard clauses
3. **One small step at a time.** Run tests after each.
4. **Commit** each coherent step separately.

## Smells to look for
- Function longer than a screen or with more than ~3 levels of nesting
- Boolean parameters that switch behavior
- Abstractions with exactly one implementation and no test seam need
- Comments explaining *what* the code does (rename instead)
- Wrappers that only pass arguments through

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "While I'm here, I'll also fix this bug" | Separate commit, with its own test (`debug`). |
| "Big rewrite is faster than small steps" | Until it breaks and you can't tell which step did it. |
| "DRY says merge these" | Only if they change for the same reason. Similar is not the same. |

## Done when
- [ ] Tests green, output seen (`verify`)
- [ ] Net lines of code went down, or clarity clearly went up
- [ ] No behavior change in the diff

Related: `design`, `code-review`.
