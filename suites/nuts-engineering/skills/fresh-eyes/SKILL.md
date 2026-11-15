---
name: fresh-eyes
description: "Use before handing over a spec, plan, or design for approval, before an irreversible or cross-module decision, before claiming a non-obvious fact (safe, scales, matches the spec), and when reviewing a large diff. A reviewer with no conversation history reads it cold."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Fresh eyes

**Core rule:** The person who wrote it cannot see what it fails to say. Have someone without your context read it before it stands.

Long sessions turn assumptions into "facts" without anyone noticing. A reviewer with a clean context sees only what is on the page, which is exactly what the next reader will see.

## When to use
- A spec, plan, or design is about to go to the user for approval
- A decision is hard to undo: data migration, public API, production deploy, architecture
- You are about to assert something the compiler cannot check: thread safety, idempotence, security, "matches the spec"
- A diff is large enough that you reviewed it while tired or deep in context

Skip it for small, reversible changes. Fresh eyes cost a reviewer's whole context; spend them where a miss is expensive.

## Process
1. **Pick the artifact and the question.** One document, decision, or diff, and what the reviewer should judge: "Could you build this without asking anything?", "What breaks if this runs twice?", "Does this diff do what the spec says?"
2. **Start a reviewer with a fresh context** (a new subagent, not a fork of this conversation). Give it:
   - the artifact (path or content),
   - the minimum it needs to judge it: the spec, the relevant files, the repo's standards,
   - the question, and "list concrete problems; say what is unclear and what you would have to guess".
   Do not give it your reasoning, your conclusions, or the conversation. That is what it must not inherit.
3. **No subagent tool?** Do it yourself in a separate step: re-read the artifact top to bottom as a stranger who has only that page, and write down every place you had to fill something in from memory.
4. **Sort what comes back:**
   - **Already answered** elsewhere → put the answer into the artifact.
   - **Minor** — settle it yourself without changing the outcome → fix it and note it as your call.
   - **For the user** — the answer changes what gets built → ask, most important first, in one message.
   - **Wrong** — the reviewer misread → check whether the artifact invited the misreading; if so, fix the wording.
5. One round is usually enough. Do not loop reviewers until nothing is said.

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "I already checked it carefully" | You checked it with the context that hides its gaps. |
| "The reviewer will just nitpick" | Then the sort takes a minute. The one real gap is worth it. |
| "I'll give the reviewer my notes so it is up to speed" | Then it is no longer fresh. Give the artifact, not your reasoning. |

## Done when
- [ ] A fresh-context read happened (subagent, or a written stranger-read)
- [ ] Every finding was sorted; user questions sent in one message
- [ ] The artifact was updated, not just the conversation

Related: `spec`, `plan`, `design`, `code-review`, `verify`.
