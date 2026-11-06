---
name: writing-skills
description: "Use when creating a new skill, editing an existing skill, or when a skill fails to trigger or is not followed. Covers the SKILL.md template, writing descriptions that trigger, and testing skills with evals."
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Writing skills

**Iron law:** Every skill ships with evals, and you only claim it helps after a baseline comparison.

If the agent already does it right unprompted, the skill is noise. But do not block the user waiting for proof: when asked to create a skill, draft it and its evals right away, aim it at the most likely failures, and mark the baseline as pending.

## Structure
```
skills/<name>/
  SKILL.md                 # required, keep under ~300 lines
  CHANGELOG.md             # one entry per metadata.version
  references/              # optional: long docs loaded only when needed
  scripts/                 # optional: deterministic helpers
  evals/triggers.json      # should / should-not trigger prompts
  evals/<case>/            # behavior case: case.yaml, prompt.md, graders/
```

## SKILL.md template
```markdown
---
name: <kebab-case, matches folder>
description: Use when <triggering situations>. <One clause on what it does.>
license: Apache-2.0
metadata:
  version: "1.0.0"
---

# <Title>

**Iron law / Core rule:** <one sentence that must never be broken>

## When to use
## Process            (numbered steps)
## Rationalizations to reject   (table: excuse | answer)
## Done when          (checklist)

Related: `other-skill`
```

## Descriptions decide triggering
- Start with **"Use when…"** and list the situations, symptoms, and words a user would say.
- Describe *when*, not a summary of the steps. If the description summarizes the process, the agent may follow the summary and skip the body.
- Be specific: "failing test, error message, crash" beats "problems".
- Keep it under ~300 characters.

## Writing the body
- Imperative, short sentences. Tables and checklists over prose.
- One iron law per skill. More than one and none of them stick.
- Fill the rationalizations table from real failures you observed in evals, not imagined ones.
- Link to related skills by name; do not duplicate their content.
- Move anything long or rarely needed into `references/`.
- **Survive context compaction:** put the iron law and the checklist near the top, keep SKILL.md short, and restate the one rule that matters at the point where it applies instead of relying on something said earlier.

## Testing with evals
Each skill's `evals/` contains:
- **triggers.json → should_trigger:** ≥ 3 realistic prompts where the skill must load
- **triggers.json → should_not_trigger:** ≥ 2 nearby prompts where it must not
- **a behavior case:** ≥ 1 scenario with the expected behavior the skill enforces

Process:
1. Run the behavior scenario **without** the skill. Record what goes wrong (baseline).
2. Add the skill. Run again. The failure should be gone.
3. Run trigger prompts; fix the description until triggering is right.
4. When the agent finds a new excuse, add it to the rationalizations table and re-run.

**Keep eval cost low.** One trigger run covering all skills at once; behavior cases only for behavior the model does not already show by default; one run per case first, and more only when a result surprises you. A skill that changes nothing on a strong model is worth knowing about, not hiding.

## Done when
- [ ] Frontmatter valid; `name` matches folder; CHANGELOG has the version
- [ ] Evals exist with trigger, no-trigger, and behavior cases
- [ ] Baseline vs. with-skill difference observed — or explicitly reported to the user as pending
- [ ] Added to the table in `nutshell`
