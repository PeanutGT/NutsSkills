---
name: code-review
description: "Use when reviewing a diff, branch, or PR, when asked whether it is safe to merge, and when acting on review comments (the reviewer says X, address the feedback). Covers giving reviews on two separate axes (spec and standards) and verifying feedback before applying it."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Code review

## Part A — Giving a review

**Core rule:** Every reported finding has been checked against the code and names a concrete failure: this input, in this state, gives this wrong result.

### 1. Pin what you are reviewing
- Find the base (the user's ref, or the merge-base with the default branch) and capture `git diff <base>...HEAD` plus `git log <base>..HEAD --oneline`.
- Stop early if the ref does not resolve or the diff is empty.
- Read the whole diff, then the surrounding code it touches. Bugs often live in what the diff did not change.

### 2. Find what the change is judged against
- **Spec:** issue references in commit messages, the PR description, a file under `docs/specs/` matching the branch. If none exists, ask; if there truly is none, say the spec axis was skipped.
- **Standards:** `CONTRIBUTING.md`, `CLAUDE.md` / `AGENTS.md`, style guides, lint and formatter config. Skip anything tooling already enforces.

### 3. Review on two axes, kept separate
A change can follow every rule and build the wrong thing, or build the right thing badly. Report the axes separately so one cannot hide the other.

**Spec axis**
- Requirements missing or only partly done
- Requirements that look done but behave wrongly
- Behavior nobody asked for (scope creep)

**Standards & quality axis**
- Documented repo rules first; cite the rule.
- Then this checklist:
  - [ ] Security: injection, missing authorization, secrets, untrusted input at boundaries
  - [ ] Errors surfaced, not swallowed
  - [ ] Edge cases: empty, null, huge, repeated, concurrent
  - [ ] Data: N+1 queries, transactions, reversible migrations
  - [ ] Tests cover the new behavior and would fail if it broke
- Then design smells, always labelled as judgement calls and overridden by repo rules: unclear name, duplicated logic, feature envy, data clumps, primitive obsession, speculative generality, shotgun surgery, middle man.

### 4. Check every finding before reporting it
Confirm it against the code. When it is cheap, prove it: a few lines of script or a throwaway test that shows the wrong result. Drop findings you cannot support; say "possible" only for genuine judgement calls.

For a large diff, if you can start subagents, give each axis to a reviewer with a fresh context (see `fresh-eyes`): it sees the diff, not your assumptions.

### 5. Report
Per axis, most severe first. Do not merge the axes into one ranking.
```
[blocker] path/file.py:42 — <one-sentence defect>
Scenario: <input/state> → <wrong result>   (verified: <how>)
Fix: <suggestion>
```
Labels: `blocker` / `should-fix` / `nit`. End with one line per axis: count and worst finding. Say briefly what is good.

## Part B — Receiving a review

**Core rule:** Verify before you agree. Feedback is a claim to check, not an order to follow.

1. Read all feedback before changing anything.
2. Check each item against the code. Is it right for *this* codebase?
3. If right: fix it, one item at a time, running tests after each.
4. If wrong or unclear: say so with technical reasons, or ask. Do not implement something you believe is wrong.
5. No performative agreement ("Great catch!"). State what you changed, or why you did not.

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "Looks good to me" without reading the tests | Rubber stamp. Read them. |
| "I'm fairly sure this is a bug" | Then a three-line script proves it. Run it. |
| "The reviewer is senior, just do it" | Seniority is not evidence. Check the claim. |

Related: `verify`, `simplify`, `ship`, `fresh-eyes`.
