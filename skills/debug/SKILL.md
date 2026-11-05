---
name: debug
description: "Use when facing a bug, failing test, error message, crash, flaky behavior, or anything that works differently than expected, before proposing or making any fix."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Systematic debugging

**Iron law:** No fix without a confirmed root cause.

Guessing fixes wastes time, hides the real bug, and adds new ones.

## Process

### 1. Reproduce
- Get a reliable, minimal reproduction. Write down the exact command and input.
- If you cannot reproduce it, gather more data (logs, environment, versions). Do not fix what you cannot see.

### 2. Read before you change
- Read the full error message and stack trace. Every line.
- Read the code on the failing path, not just the line in the trace.
- Check what changed recently: `git log`, `git diff`, dependency bumps, config.

### 3. Isolate
- Find a working example nearby and compare. What is different?
- Narrow the search: binary-search the input, the commits (`git bisect`), or the code path.
- In multi-layer systems, log what enters and leaves each layer to find where good data turns bad.

### 4. Hypothesize and test — one at a time
- Write the hypothesis down: "X fails because Y."
- Design the smallest experiment that proves or disproves it.
- Change one variable per experiment. Revert experiments that disproved the hypothesis.

### 5. Fix the root cause
- Write a failing test that reproduces the bug (see `tdd`).
- Fix at the source, not where the symptom appears.
- Run the test and the surrounding suite (see `verify`).

## Stop rule
If three fix attempts have failed, **stop**. The problem is likely your model of the system, not the fix. Step back, re-read the code, question the architecture, and tell the user what you have learned so far.

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "I think I see it, let me just try this" | That is a guess. State the hypothesis and test it. |
| "Add a try/catch so it stops crashing" | That hides the bug. Find why it throws. |
| "It's flaky, retry it" | Flakiness has a cause: timing, shared state, ordering. Find it. |
| "Several changes at once will be faster" | Then you won't know which one mattered. |
| "Works on my machine" | Then the difference between machines is the bug. Find it. |

## Done when
- [ ] Root cause stated in one sentence
- [ ] A test reproduces the bug and now passes
- [ ] Fix is at the source, not a symptom patch
- [ ] Debug logging and experiments removed

Related: `tdd`, `verify`.
