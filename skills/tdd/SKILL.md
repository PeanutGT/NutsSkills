---
name: tdd
description: "Use before writing any implementation code for a feature, bugfix, or behavior change. Drives the work with one failing test at a time (red, green, refactor)."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Test-driven development

**Iron law:** No production code without a test that you watched fail first.

A test you never saw fail proves nothing. It may test the wrong thing, or nothing at all.

## When to use
- New features and behavior changes
- Bug fixes (the failing test reproduces the bug)
- Refactors of code that has no tests yet (write characterization tests first)

**Skip only with the user's OK:** throwaway prototypes, generated code, pure config.

## The cycle
1. **Pick one behavior.** The smallest next thing the code should do. Start with the simplest case (zero, empty, one).
2. **RED — write one test.** Name it after the behavior, not the function (`rejects passwords shorter than 8 chars`, not `test_validate`).
3. **Run it. Watch it fail.** Confirm it fails for the *expected reason* (assertion fails), not a typo or import error.
4. **GREEN — write the minimum code** that makes this test pass. Hardcoding is fine if no other test forbids it.
5. **Run the whole relevant suite.** Everything green.
6. **REFACTOR.** Remove duplication, improve names. Tests stay green after every change.
7. Repeat from 1 until the acceptance criteria are covered.

Order of cases to drive out: zero → one → many → boundaries → errors and invalid input.

**Edge-case tests that pass on the first run are fine — write them anyway.** Once the core behavior exists, tests for empty input, boundaries, or invalid input may already pass. Keep them: they guard against regressions. To prove such a test can fail, briefly break the code (or the expected value), watch it go red, then restore. Never skip edge cases just because they would not be red first.

## Good tests
- Test behavior through the public interface, not private internals.
- One reason to fail per test. Clear arrange / act / assert.
- Mock only at system boundaries (network, clock, filesystem, third-party APIs). Never mock the thing under test.
- Deterministic: no real time, randomness, or ordering dependence.
- Assertions on specific values, not just "not null" or "no exception".

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "Too simple to test" | Then the test takes 30 seconds. Write it. |
| "I'll add tests after" | Tests written after pass on the first run, so they never proved anything. |
| "I already tested it manually" | Manual checks don't repeat. The next change breaks it silently. |
| "I wrote the code already, I'll keep it as reference" | Delete it. Start from the test. Code written without a test shapes the test to fit the code. |
| "This test is hard to write" | The design is hard to use. Fix the design (see `design`). |
| "Just this once" | That is how every untested module started. |

## Done when
- [ ] Every acceptance criterion has at least one test
- [ ] Edge cases covered: empty, boundaries, invalid input
- [ ] Each test was seen failing at least once (first run, or by briefly breaking the code)
- [ ] Full relevant suite passes (output seen, see `verify`)
- [ ] No production code exists that no test exercises

Related: `debug` (when a test fails unexpectedly), `verify`, `design`.
