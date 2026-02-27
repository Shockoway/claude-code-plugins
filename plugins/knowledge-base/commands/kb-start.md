---
description: Start work — establish what/why/done before planning
argument-hint: [task description or title]
allowed-tools: Bash(bash:*)
---

You are about to start work on: **$ARGUMENTS**

Before any planning or implementation, you MUST ask the user these three questions one at a time. Wait for the answer before asking the next. Do not skip ahead.

**Gate 1 — What?**
Ask: "In one sentence, what exactly are we building or changing?"
→ Wait for answer.

**Gate 2 — Why?**
Ask: "Why does this matter? Which project goal does it serve, or what user pain does it address?"
→ Wait for answer.

**Gate 3 — Done looks like?**
Ask: "What does 'done' look like? What would you check to confirm it's complete?"
→ Wait for answer.

---

Only after all three gates are answered, continue:

**Check for existing tasks:**

In-progress:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task select --where status=in-progress`

Planned:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task select --where status=planned`

- If a matching task exists → reference it and mark it in-progress:
    bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task set <id> status=in-progress
- If no matching task exists → offer to create one:
    bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task new <title>

Only after completing the above, proceed with planning.
