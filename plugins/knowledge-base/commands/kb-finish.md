---
description: Finalize work — close tasks, surface decisions, update docs
allowed-tools: Bash(bash:*), Read, Write, Edit
---

You are running the KB completion checklist. Your job is to **propose** what needs to be updated based on available context, then let the user confirm or correct. Do not interrogate the user — reason first, ask only to confirm.

**Gather context:**

Recent changes:
!`bash -c "git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only"`

In-progress tasks:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task select --where status=in-progress`

Current references:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" reference select`

Current glossary:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" doc open glossary`

---

Using the context above and your knowledge of this session, reason through each of the four areas below and form your own assessment. Then present a **single summary proposal** to the user covering all four areas at once. Wait for one confirmation before acting.

**Area 1 — Tasks**
For each in-progress task: based on what was worked on this session, is it done, partially done (what's left?), or untouched?

**Area 2 — Decisions**
Were any non-obvious trade-offs or architectural decisions made? If yes, propose an ADR title and a brief summary of Context / Decision / Consequences.

**Area 3 — Reference docs**
Cross-reference changed files with the reference list. Which refs (if any) had their contracts or interfaces changed and need updating?

**Area 4 — Glossary**
Compare terms used during this session with the current glossary. Which new terms (if any) should be added?

---

Present your assessment in this format:

```
Here's what I think happened this session:

Tasks:
  ✓ TASK-foo — done
  ~ TASK-bar — not finished; suggested next step: [...]
  — TASK-baz — untouched, leaving as-is

Decisions:
  → ADR: "[proposed title]" — [one-line summary]
  (or: no ADRs needed)

References:
  → ref-foo needs updating: [what changed]
  (or: no ref changes)

Glossary:
  → add: [term] — [definition]
  (or: no new terms)

Does this look right? Any corrections?
```

**STOP. Wait for the user's confirmation or corrections.**

Once confirmed (with any adjustments), execute all updates:
- Tasks: `bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task set <id> status=done` (or edit `kb/tasks/task-<slug>.md` `## Next steps` for partial)
- ADRs: `bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" adr new <title>` then fill in body
- Refs: edit the relevant `kb/reference/ref-*.md` files
- Glossary: edit `kb/glossary.md`

Then rebuild the index:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" index rebuild`
