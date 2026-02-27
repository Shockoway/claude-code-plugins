---
description: Strategic KB planning — triage backlog, align with charter
allowed-tools: Bash(bash:*)
---

**Charter:**
!`bash ${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh doc open charter`

**Roadmap:**
!`bash ${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh doc open roadmap`

**In-progress tasks:**
!`bash ${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh task select --where status=in-progress`

**Planned tasks (by priority):**
!`bash ${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh task select --where status=planned --sort priority`

You are running a strategic KB planning session. Work through this sequentially — do not skip steps, do not write code.

**Step 1 — Triage in-progress tasks**
For each in-progress task: is it still active, stale, or actually done?
Update statuses as needed using:
  bash ${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh task set <id> status=<done|cancelled|planned>

**Step 2 — Review planned tasks against charter goals**
For each planned task: does it still align with the stated goals and non-goals?
Cancel anything no longer relevant. Reprioritize if needed.

**Step 3 — Propose top 1–3 priorities**
Based on charter goals and current state, what should be worked on next?
Give explicit reasoning tied to charter goals.

**Step 4 — Flag roadmap drift**
Does the roadmap reflect the current direction?
Note any epics that are stale, completed, or need revision.
