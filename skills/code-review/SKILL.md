---
name: code-review
description: "Use when reviewing a diff or PR, when asked \"review this\" or \"is this safe to merge\", and when receiving review feedback on your own changes. Covers both giving and responding to reviews."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Code review

## Part A — Giving a review

**Core rule:** Every finding names a concrete failure: this input, in this state, produces this wrong result.

### Process
1. **Understand intent.** Read the spec, ticket, or PR description. Review against what the change is supposed to do.
2. **Read the whole diff**, then the surrounding code it touches. Bugs often live in what the diff did not change.
3. **Pass 1 — Correctness vs. spec.** Does it do what was asked? Missing cases? Wrong edge behavior?
4. **Pass 2 — Quality.** Use the checklist below.
5. **Rank findings** most severe first. Label each: `blocker` / `should-fix` / `nit`.
6. Say what is good too, briefly. Do not pad.

### Checklist
- [ ] Error handling: failures surfaced, not swallowed
- [ ] Edge cases: empty, null, huge, concurrent, repeated
- [ ] Security: injection, authz checks, secrets, untrusted input
- [ ] Data: migrations reversible, no N+1 queries, transactions correct
- [ ] Tests: cover the new behavior, would fail if the code broke
- [ ] Naming and structure: matches the codebase, no dead code
- [ ] Scope: no unrelated changes mixed in

### Finding format
```
[blocker] path/file.ts:42 — <one-sentence defect>
Scenario: <input/state> → <wrong result>
Suggestion: <fix>
```

## Part B — Receiving a review

**Core rule:** Verify before you agree. Feedback is a claim to check, not an order to follow.

1. Read all feedback before changing anything.
2. For each item, check it against the code. Is it correct for *this* codebase?
3. If correct: fix it, one item at a time, and run tests after each.
4. If wrong or unclear: say so with technical reasons, or ask. Do not implement something you believe is wrong.
5. Do not reply with performative agreement ("Great catch!"). State what you changed or why you did not.

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "Looks good to me" without reading tests | Rubber stamp. Read the tests. |
| "The reviewer is senior, just do it" | Seniority is not evidence. Check the claim. |
| "Small diff, quick skim" | Small diffs in critical paths cause big outages. |

Related: `verify`, `simplify`, `ship`.
