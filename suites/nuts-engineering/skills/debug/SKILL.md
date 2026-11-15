---
name: debug
description: "Use when facing a bug, failing test, error message, crash, flaky or slow behavior, or anything that works differently than expected, before proposing or making any fix."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Systematic debugging

**Iron law:** No hypothesis before you have a command that goes red on this bug. No fix before a confirmed root cause.

Reading code to build a theory before you can reproduce the bug is the failure this skill exists to prevent.

## Phase 1 — Build the feedback loop (most of the work)
Get **one command you have actually run** that:
- goes red on **the user's exact symptom** (their error, their wrong output), not merely "runs";
- gives the same verdict every run (flaky bugs: a pinned, high failure rate);
- finishes in seconds and runs unattended.

Ways to get one, roughly in this order:
1. A failing test at the seam that reaches the bug (unit, integration, e2e)
2. A CLI run on a fixture input, diffed against known-good output
3. A curl / HTTP script against a running dev server
4. A headless-browser script asserting on DOM, console, or network
5. Replaying a captured request, payload, or log through the code path
6. A throwaway harness that calls the failing path directly with stubs
7. A random-input loop for "sometimes wrong" bugs
8. `git bisect run <check>` when it worked at some earlier commit
9. Old-vs-new (or config A vs B) on the same input, diffing outputs

Then tighten it: cut setup time, assert on the specific symptom, pin time, random seeds, and network.

**Flaky bugs:** loop the trigger 100×, in parallel, under load, until the failure rate is high enough to debug against.

**No loop possible?** Stop. List what you tried and ask for access to an environment that reproduces it, a redacted artifact (log, HAR, dump), or permission for temporary instrumentation.

## Phase 2 — Reproduce and minimise
- Confirm the loop shows the user's failure, not a different one nearby. Wrong bug, wrong fix.
- Remove inputs, config, data, and steps one at a time, re-running each time, until every remaining piece is needed to stay red.

## Phase 3 — Hypothesise: 3–5, ranked
- Write each as a prediction: "If X is the cause, changing Y makes the bug disappear."
- Check what changed recently: `git log`, dependency bumps, config, data.
- Show the ranked list to the user; they may rule some out instantly. Do not wait if they are away.

## Phase 4 — Test one variable at a time
- Prefer a debugger or REPL; otherwise targeted logs at the boundary that separates two hypotheses. Never "log everything".
- Tag every temporary log with one prefix, e.g. `[DEBUG-7f3a]`, so cleanup is a single grep.
- Performance bugs: measure a baseline first (timer, profiler, query plan), then bisect. Logs are the wrong tool.

## Phase 5 — Fix with a regression test
1. Turn the minimised repro into a failing test at a seam that exercises the real call pattern. If no honest seam exists, say so: that is a design finding (`design`), not something to paper over with a shallow test.
2. Watch it fail. If you forced the red by editing code or a fixture, diff against a clean copy to prove the edit landed.
3. Fix at the source, not where the symptom shows.
4. Watch it pass, then re-run the Phase 1 loop on the original, unminimised scenario.

## Stop rule
Three failed fixes → stop. Your model of the system is wrong. Re-read the code, question the design, and report what you know so far.

## Rules
- Redact secrets in every command and output you show: `<REDACTED>`.
- Change one thing per experiment; revert experiments that disproved their hypothesis.

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "I can see the bug from reading the code" | Then the loop takes a minute to write, and it proves you right. |
| "Add a try/catch so it stops crashing" | That hides the bug. Find why it throws. |
| "It's flaky, just retry" | Flakiness has a cause: timing, shared state, ordering. Raise the failure rate and find it. |
| "Several changes at once will be faster" | Then you will not know which one mattered. |

## Done when
- [ ] Root cause stated in one sentence, and written into the commit message
- [ ] The Phase 1 loop no longer reproduces the original scenario
- [ ] Regression test passes, or the missing seam is reported
- [ ] `grep` for the debug tag finds nothing; throwaway files removed

Related: `tdd`, `verify`, `design`.
