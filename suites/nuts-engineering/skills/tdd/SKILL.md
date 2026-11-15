---
name: tdd
description: "Use before writing any implementation code for a feature, bugfix, or behavior change. Drives the work with one failing test at a time (red, green, refactor) at an agreed public seam."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Test-driven development

**Iron law:** No production code without a test that you watched fail first.

A test you never saw fail proves nothing. It may test the wrong thing, or nothing at all.

## When to use
- New features and behavior changes
- Bug fixes (the failing test reproduces the bug; see `debug`)
- Refactors of untested code (write characterization tests first)

**Skip only with the user's OK:** throwaway prototypes, generated code, pure config.

## Choose the seam first
A **seam** is the public boundary where you observe behavior: a function's signature, an HTTP endpoint, a CLI command. Tests live at seams, never against internals.
- Before the first test, name the seams you will test and what each catches. For non-trivial work, confirm them with the user.
- If no clean seam exists, the design is the problem: see `design`.

## The cycle
1. **Pick one behavior**: the smallest next thing. Start simple: zero, empty, one.
2. **RED**: one test, named for the behavior (`rejects passwords shorter than 8 chars`).
3. **Watch it fail** for the expected reason (an assertion, not an import error or typo).
4. **GREEN**: the minimum code that passes. Hardcoding is fine until a test forbids it.
5. **Run the relevant suite.** All green.
6. **REFACTOR**: names and duplication only, tests green after every change. Larger cleanup goes to `simplify`.
7. Repeat until the acceptance criteria are covered.

Order of cases: zero → one → many → boundaries → errors and invalid input.

**Edge-case tests that pass on the first run are fine — write them anyway.** They guard against regressions. To prove one can fail, briefly break the code (or the expected value), watch it go red, then restore.

## Anti-patterns
- **Implementation-coupled:** mocks internal collaborators, tests private methods, or checks a side channel (querying the database instead of the interface). Tell: it breaks on a refactor that changed no behavior.
- **Tautological:** the expected value is computed the same way the code computes it (`assert add(a, b) == a + b`), so it can never disagree. Expected values come from an independent source: a literal, a worked example, the spec.
- **Horizontal slicing:** writing all the tests first, then all the code. Work in vertical slices: one test, one implementation, learn, repeat.
- **Weak assertions:** "not null", "no exception". Assert specific values.

## Good tests
- One reason to fail per test; clear arrange / act / assert.
- Mock only at system boundaries (network, clock, filesystem, third-party APIs).
- Deterministic: no real time, randomness, or ordering dependence.

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "Too simple to test" | Then the test takes 30 seconds. Write it. |
| "I'll add tests after" | Tests written after pass on the first run, so they never proved anything. |
| "I tested it manually" | Manual checks don't repeat. The next change breaks it silently. |
| "I already wrote the code, I'll keep it as reference" | Delete it and start from the test, or the test will be shaped to fit the code. |
| "This test is hard to write" | The design is hard to use. Fix the seam (`design`). |

## Done when
- [ ] Every acceptance criterion has at least one test at an agreed seam
- [ ] Edge cases covered: empty, boundaries, invalid input
- [ ] Each test was seen failing at least once (first run, or by briefly breaking the code)
- [ ] Full relevant suite passes (output seen; see `verify`)

Related: `debug`, `verify`, `design`, `simplify`.
