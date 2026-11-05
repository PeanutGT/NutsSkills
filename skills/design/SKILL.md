---
name: design
description: "Use when adding a new module, service, API, or data model, choosing between architectural approaches, or when code is hard to test or change. Covers module boundaries, interfaces, domain naming, and recording decisions."
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: PeanutGT
  suite: nuts-engineering
  repository: https://github.com/PeanutGT/NutsSkills
---

# Design modules and interfaces

**Core rule:** Follow the existing pattern unless you can name the concrete problem it fails to solve.

Most tasks need no new architecture. Check the codebase first.

## Principles
- **Deep modules.** A small, simple interface hiding a lot of behavior. Avoid shallow modules whose interface is as complex as their implementation.
- **Information hiding.** Each module owns one decision that is likely to change (a storage format, a vendor, an algorithm) and hides it.
- **Dependencies point inward.** Business logic does not import frameworks, databases, or HTTP. Adapters depend on the core, not the reverse.
- **Domain language.** Name types and functions with the words the users and docs use. If the code says `Item` but the business says `Shipment`, fix the name.
- **Design for testability.** If it needs heavy mocking to test, the boundaries are wrong. Pass dependencies in.
- **YAGNI.** No extension points, plugins, or config for needs that do not exist yet.

## Process
1. Describe the problem and the forces (what changes often, what must stay stable, scale, team).
2. Look at how similar things are done in this codebase. Prefer that.
3. If a new approach is warranted, sketch **two or three options** briefly: interface, data flow, trade-offs.
4. Recommend one. Pick the simplest that meets the forces.
5. Write the public interface (types, function signatures) before the implementation.
6. Record significant decisions as an ADR (template below), default `docs/adr/NNNN-title.md`.

## API checklist
- [ ] Names describe intent, not implementation
- [ ] Inputs validated at the boundary; errors are explicit and typed
- [ ] Hard to misuse: no boolean flag soup, no order-dependent calls
- [ ] Backward compatibility / versioning considered for public APIs
- [ ] Idempotency for anything retried over the network

## ADR template
```markdown
# NNNN. <Decision title>
Status: proposed | accepted | superseded by NNNN
## Context
## Decision
## Options considered
## Consequences (good and bad)
```

## Rationalizations to reject
| Excuse | Answer |
|---|---|
| "We might need this flexibility later" | Add it later, when you know its shape. |
| "Let's use the pattern from <famous system>" | Your forces are not theirs. Name the problem it solves here. |

Related: `tdd`, `simplify`, `spec`.
