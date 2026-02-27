---
description: Finalize work — close tasks, surface decisions, update docs
allowed-tools: Bash(bash:*), Read, Write, Edit
---

You are running the KB completion checklist. Work through each step sequentially. For each step, ask the user the question, wait for their answer, act on it, then move to the next step.

**Current in-progress tasks:**
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task select --where status=in-progress`

---

**Step 1 — Close or update worked-on tasks**

Ask about the **first** in-progress task: "Was [task title] worked on during this session?"

**STOP. Wait for the user's reply. Then act on it, then ask about the next task. Repeat until all tasks are covered.**

- Yes, it's done →
    bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task set <actual-id> status=done
- Yes, but not finished → ask for a brief progress note, then find the task file at
  `kb/tasks/task-<slug>.md` (where `<slug>` is the ID after `TASK-`), and edit its `## Next steps` section
- Not touched → skip

---

**Step 2 — Surface undocumented decisions**

Ask the user: "Were any non-obvious trade-offs or architectural decisions made during this work?"

**STOP. Wait for the user's reply.**

- Yes → create an ADR and fill in the body (use sections: Context, Decision, Consequences):
    bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" adr new <title>
- No → skip

---

**Step 3 — Update affected reference docs**

**Current references:**
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" reference select`

Ask the user: "Were any component contracts or interfaces changed?"

**STOP. Wait for the user's reply.**

- Yes → ask which references to update, show the user the current content of each, then edit them
- No → skip

---

**Step 4 — Glossary hygiene**

**Current glossary:**
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" doc open glossary`

Ask the user: "Were any new terms introduced that aren't in the glossary?"

**STOP. Wait for the user's reply.**

- Yes → add them to `kb/glossary.md`
- No → skip

---

When all four steps are complete, rebuild the index:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" index rebuild`
