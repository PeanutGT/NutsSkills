---
name: verify
description: "Use before claiming any work is done, fixed, working, or passing, before saying a task or requirement is complete, and before committing or opening a PR. Requires running the check and showing its output as evidence."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Verify before claiming done

**Iron law:** No completion claim without fresh evidence from after your last edit.

"Should work", "looks right", and "I'm confident" are not evidence.

## The gate
Before any claim of success — including "Great!", "Done!", or moving on to the next task:
1. **Identify** the command or check that proves the claim.
2. **Run it now**, in full. Not an earlier run, not a subset.
3. **Read the output**: exit code, failure count, warnings.
4. **Report what you saw**, with the command and the relevant lines.
5. If anything failed or could not be run, say so plainly. "47/48 passing" is not "passing".

## What counts as evidence
| Claim | Evidence | Not enough |
|---|---|---|
| Tests pass | Suite output with 0 failures, run after the last edit | An earlier run; "should pass" |
| Bug fixed | The original reproduction now behaves correctly | "I changed the code" |
| Regression test guards the fix | Revert the fix → test fails → restore → test passes | The test passing once |
| Build works | Build command exits 0 | Lint or type-check passing |
| Feature works | Exercised end to end (run the app, call the API, click the UI) | Unit tests alone |
| Requirements met | Re-read the spec or plan and tick each item against the code | "Tests pass, so it's done" |
| Delegated work is done | You read the diff or result yourself | The agent's own success report |
| Nothing else broke | The broader suite, and any test that was skipped or renamed is explained | Only the new test |

## Also check
- `git diff` for disabled, renamed, or skipped tests and for leftover debug code.
- That the claim matches the request, not just the code: re-read what the user asked.

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "It's a tiny change" | Tiny changes break builds too. The check is cheap. |
| "I ran it earlier" | You edited since. Run it again. |
| "The linter passed" | Lint is not behavior. |
| "I can't run it here" | Then say exactly what was not verified and why. |
| "Different wording, so the rule doesn't apply" | Any statement implying success needs evidence. |

## Done when
- [ ] The proving command ran after the final edit, and its output is quoted or summarized faithfully
- [ ] Each requirement was checked against the code, not inferred from passing tests
- [ ] Anything not verified is named explicitly

Related: `tdd`, `debug`, `ship`, `fresh-eyes`.
