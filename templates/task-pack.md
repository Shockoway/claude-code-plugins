---
type: task-context-pack
id: TASK-<slug-or-issue>
title: "<human title>"
status: draft|active|done
created_at: YYYY-MM-DD
last_updated_at: YYYY-MM-DD
owners: ["@you"]
provenance:
  repo: "<repo name>"
  base_ref: "<branch or commit>"
  evidence:
    - "<file path>:<section or line range>"
---

# Purpose

Describe the user-visible outcome and why it matters.

# Current state

What exists today (code + behavior). Link to key modules in `kb/reference/`.

# Constraints

Performance, compatibility, security, product constraints.

# Decisions in scope

List any decisions needed. If a decision is made, create an ADR and link it.

# Work plan

A short plan that can survive context resets:
- Step 1
  - Expected validation evidence
- Step 2
  - Expected validation evidence

# Progress log

- (YYYY-MM-DD HH:MM) Done: …
- Next: …

# Validation

Commands/tests to run and expected outputs.
