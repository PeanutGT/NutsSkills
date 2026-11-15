---
name: clarify
description: "Use when a request is vague, open-ended, or a new feature idea (I want to build X, add support for Y), before writing a spec, plan, or code. Decides whether questions are needed at all, then interviews one question at a time until goals, constraints, and edge cases are unambiguous."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Clarify requirements

**Iron law:** No spec, plan, or code while a question that would change what gets built is still open.

Building the wrong thing well is still building the wrong thing. Asking about things that don't matter wastes the user's time just as surely.

## 0. Triage first
Ask yourself: what do I know about what they want, and why?
- **Everything that matters is in the request** ("make the button blue"): do it and say what you did. No interview.
- **Something non-trivial is missing:** continue below.

## Process
1. **Look before you ask.** Read the relevant code, docs, and recent commits. Never ask what the repo can tell you.
2. **Restate the goal** in one or two sentences: who it is for, what problem it solves, how success is measured.
3. **One question per message.** Each question:
   - is about one decision, specific to their project;
   - gives your recommended answer and why;
   - offers 2–4 concrete options when there are clear alternatives.
4. **Walk the decision tree.** Settle parent decisions before children.
5. **Probe the edges:** empty and huge inputs, failure modes, permissions, concurrency, existing data, undo.
6. **Lay out the approaches.** When there is more than one sensible way to build it, describe two or three with their trade-offs, recommend one, and let the user pick.
7. **Play it back in chunks.** As soon as one part is clear, describe it back briefly. Mark what the user said as theirs and what you filled in as *your proposal, with your reason*. A default they never heard is one they could not reject.
8. **Size the work** in plain words (small change / project) and name what is out of scope.
9. **Summarize** the decisions and get a clear "yes" before moving on.

## Question checklist
- [ ] Goal and success measure
- [ ] Users / callers and their main scenarios
- [ ] Inputs, outputs, and error behavior
- [ ] Constraints: performance, security, compatibility, deadlines
- [ ] Existing code or patterns this must fit
- [ ] Explicitly out of scope

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "The intent is obvious" | Then confirming it takes one message. |
| "I'll pick sensible defaults" | Good — say them out loud as proposals. Silent defaults are guesses. |
| "I'll ask everything at once to save time" | A wall of questions gets skimmed. One sharp question gets answered. |
| "This is too small to ask about" | Then triage says do it. Don't interview for a one-liner. |

## Done when
- [ ] The user approved a written summary of decisions, including which approach
- [ ] No open question would change what gets built

Next: `spec` (or straight to `plan` for a small change).
