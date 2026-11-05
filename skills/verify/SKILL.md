---
name: verify
description: "Use before claiming any work is done, fixed, working, or passing, and before committing or opening a PR. Requires running the check and showing its output as evidence."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Verify before claiming done

**Iron law:** No completion claim without fresh evidence from this session.

"Should work", "looks right", and "I'm confident" are not evidence.

## The gate
Before you write any claim of success:

1. **Identify** the command that proves the claim (test, build, lint, type-check, run the app, curl the endpoint).
2. **Run it now.** Not earlier in the session, not before your last edit.
3. **Read the full output.** Exit code, failure count, warnings.
4. **Report what you saw**, with the command and the relevant output lines.
5. If anything failed, say so plainly. Do not round "47/48 passing" up to "passing".

## What counts as evidence
| Claim | Evidence required |
|---|---|
| "Tests pass" | Test command output showing 0 failures, run after the last edit |
| "Bug is fixed" | The reproduction from `debug` now shows correct behavior |
| "Build works" | Build command exit 0 |
| "Feature works" | The feature exercised end-to-end (run the app, call the API, click the UI) |
| "No regressions" | The broader suite, not only the new test |
| "Subagent finished the task" | You inspected the diff or result yourself |

## Words that trigger this gate
done · fixed · works · passing · ready · complete · should be good · all set

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "It's a tiny change" | Tiny changes break builds too. Running the check is cheap. |
| "I ran it earlier" | You have edited since. Run it again. |
| "The linter passed, so it works" | Lint is not behavior. Run the tests. |
| "I can't run it here" | Then say exactly that: what was not verified and why. |

## Done when
- [ ] The proving command ran after the final edit
- [ ] Output was read and is quoted or summarized faithfully
- [ ] Anything not verified is named explicitly

Related: `tdd`, `debug`, `ship`.
