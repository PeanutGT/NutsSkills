---
name: nutshell
description: "Use at the start of every software engineering task (building, fixing, reviewing, planning, refactoring, shipping), together with any more specific skill that applies. Holds the always-on baseline rules and picks which engineering skill to load next."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Nutshell — the nuts-engineering router

**Core rule:** If there is even a small chance a skill applies, read it before you act. Skills are cheap to read and expensive to skip.

## Baseline (always on)
1. **Think before coding.** If the request is ambiguous, ask. State assumptions before acting on them.
2. **Simplest thing that works.** Build only what was asked. No speculative features, options, or abstractions.
3. **Surgical changes.** Touch only what the task needs. Match the surrounding style. Mention unrelated problems instead of fixing them silently.
4. **Goal-driven.** Define what "done" looks like before starting, and never claim done without evidence (`verify`).

## Which skill when

| Situation | Skill |
|---|---|
| Need to find where things live in an unfamiliar or large repo | `repo-map` |
| Request is vague, new feature idea, "I want to build X" | `clarify` |
| Requirements are clear, need acceptance criteria | `spec` |
| Work has more than ~3 steps or touches several files | `plan` |
| About to write implementation code (feature or bugfix) | `tdd` |
| Bug, failing test, error message, unexpected behavior | `debug` |
| About to say "done", "fixed", "passing", or open a PR | `verify` |
| Reviewing a diff, or received review feedback | `code-review` |
| New module, API, data model, or architectural choice | `design` |
| Code works but feels too complex, or after a feature lands | `simplify` |
| Committing, opening a PR, finishing a branch | `ship` |
| Spec, plan, or risky decision about to be handed over or committed | `fresh-eyes` |
| Creating or editing a skill | `writing-skills` |

## The default flow

```
clarify → spec → plan → tdd ⇄ debug → verify → code-review → ship
       repo-map / design / simplify / fresh-eyes can be called at any point
```

Small tasks skip early steps: a one-line fix goes straight to `tdd` → `verify`. A typo needs no skill at all.

## Rules
- The user's explicit instructions override any skill.
- Announce which skill you are using in one short line, then follow it.
- If a skill has a checklist, track each item; do not skip silently.
- If two skills apply, process skills (`clarify`, `debug`) come before implementation skills (`tdd`, `design`).

## Red flags — you are about to skip a skill
| Thought | Reality |
|---|---|
| "This is simple, I'll just do it" | Simple tasks are where unchecked assumptions hide. Check the table. |
| "I'll read the skill after I look around" | The skill tells you how to look around. |
| "I remember what that skill says" | Skills change. Read the current version. |
