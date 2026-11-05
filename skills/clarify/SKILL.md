---
name: clarify
description: "Use when a request is vague, open-ended, or a new feature idea (\"I want to build X\", \"add support for Y\"), before writing a spec, plan, or code. Interviews the user until goals, constraints, and edge cases are unambiguous."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Clarify requirements

**Iron law:** No spec, plan, or code while a material question is still open.

Building the wrong thing well is still building the wrong thing.

## Process
1. **Look first.** Read the relevant code, docs, and recent commits so you only ask what you cannot find out yourself.
2. **Restate the goal** in one or two sentences: who it is for, what problem it solves, how success is measured.
3. **Ask one question at a time.** Each question:
   - is about one decision,
   - gives your recommended answer and why,
   - offers 2–4 concrete options when there are clear alternatives.
4. **Walk the decision tree.** Resolve parent decisions before children. Follow every branch until it reaches a leaf.
5. **Probe the edges:** empty and huge inputs, failure modes, permissions, concurrency, migration of existing data, what happens on undo.
6. **Name what is out of scope** and get agreement.
7. **Summarize** the decisions as a short list and get a clear "yes" before moving on.

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
| "I'll pick a sensible default" | Fine for minor choices — state it. Not fine for choices that change what gets built. |
| "Asking too much annoys the user" | Asking one sharp question at a time is fast. Rebuilding is slow. |

## Done when
- [ ] The user approved a written summary of decisions
- [ ] No open question would change what gets built

Next: `spec`.
