---
description: Start work — establish what/why/done before planning
argument-hint: [task description or title]
allowed-tools: Bash(bash:*)
---

You are about to start work on: **$ARGUMENTS**

Before any planning or implementation, work through the three gates below ONE AT A TIME. Send each question as a separate message. Do not ask the next gate until the user has replied to the current one.

**Gate 1 — What?**
Send this message now, then stop and wait for the user's reply:
"In one sentence, what exactly are we building or changing?"

**STOP. Do not continue until the user replies to Gate 1.**

---

**Gate 2 — Why?**
Send this message now, then stop and wait for the user's reply:
"Why does this matter? Which project goal does it serve, or what user pain does it address?"

**STOP. Do not continue until the user replies to Gate 2.**

---

**Gate 3 — Done looks like?**
Send this message now, then stop and wait for the user's reply:
"What specific behavior, test, or artifact would prove this is done?"

**STOP. Do not continue until the user replies to Gate 3.**

---

Only after all three gates are answered, continue:

**Check for existing tasks:**

In-progress:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task select --where status=in-progress`

Planned:
!`bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task select --where status=planned`

Show the results to the user and ask: "Do any of these match what we're working on? If yes, which one?"

- If the user confirms a match → mark it in-progress using the task's actual ID:
    bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task set <actual-id> status=in-progress
- If no match → offer to create a new task:
    bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task new <title>

Only after completing the above, proceed with planning.
