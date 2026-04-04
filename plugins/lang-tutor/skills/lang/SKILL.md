---
name: lang
description: Language learning framework. Use when the user wants to study a language, practice, check progress, or set up a learning schedule. Invoke proactively when the working directory contains lang.db or lang-guide.md.
user-invocable: true
allowed-tools: Bash, Read, Write, Edit, Agent
context: default
---

# Lang-Tutor

**For agents: `Skill(lang-tutor:lang)`**

Adaptive language learning system. You are the orchestrator — detect state, route to the right sub-agent, stay out of the way.

## Scripts

All data operations:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py" <command>
```

Database resolves to `./lang.db` in the current working directory (`LANG_DB` env to override).

## State detection

Run these to understand what to do next:

```bash
# Is there a profile?
python3 "${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py" profile get

# Is there a roadmap?
python3 "${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py" roadmap get

# Is there a session today?
python3 "${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py" session get
```

## Routing table

| State | Action |
|---|---|
| No `lang.db` / no profile | Run onboarding → spawn **RoadmapAgent** |
| Profile exists, no topics in roadmap | Spawn **RoadmapAgent** |
| Profile + roadmap, no session today | Spawn **ExerciseAgent** |
| Session exists, answers not yet submitted | Display session file, wait for user |
| User just submitted answers | Spawn **EvaluatorAgent** |
| User asks for progress / stats / weak spots | Spawn **ProgressAgent** |
| User asks for weekly plan / schedule | Spawn **ProgressAgent** (weekly mode) |
| User asks to see dashboard / progress visually | Run `lang.py dashboard`, report paths |

When in doubt, check state and ask: "Хочешь потренироваться, посмотреть прогресс или обновить роадмап?"

## Onboarding

When there is no profile, ask **one question at a time** and wait for the answer:

1. "What language are you studying?"
2. "What's your current level? (A1 / A2 / B1 / B2 / C1)"
3. "What's your goal? (e.g. professional English for IT, conversational Spanish for travel)"
4. "Target level? (B2 / C1 / C2)"
5. "Minutes per day you can study? (15–60)"
6. "Preferred schedule — days and time? (e.g. Mon–Fri at 09:00)"

Then:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py" db init
python3 "${CLAUDE_PLUGIN_ROOT}/skills/lang/scripts/lang.py" profile save '<json>'
```

Check for `lang-guide.md` in the working directory — if present, pass its content to RoadmapAgent.

## Variable conventions

- `${CLAUDE_PLUGIN_ROOT}` — shell env var, use in bash command blocks within this skill
- `{{PLUGIN_ROOT}}` — template placeholder in `prompts/*.md`, substituted by the orchestrator before spawning; replace with the actual value of `${CLAUDE_PLUGIN_ROOT}`
- Hook scripts resolve paths relative to `$SCRIPT_DIR` — no variable needed

## Spawning agents

Load the agent prompt file, substitute variables, then spawn via Agent tool.

Agent prompt templates are at: `${CLAUDE_PLUGIN_ROOT}/skills/lang/prompts/`

**RoadmapAgent:**
```
Read: ${CLAUDE_PLUGIN_ROOT}/skills/lang/prompts/roadmap.md
Substitute: PLUGIN_ROOT, PROFILE_JSON, LANG_GUIDE_CONTENT
Spawn via Agent tool with allowed tools: Bash, Read, Write
```

**ExerciseAgent:**
```
Read: ${CLAUDE_PLUGIN_ROOT}/skills/lang/prompts/exercise.md
Substitute: PLUGIN_ROOT, TODAY
Spawn via Agent tool with allowed tools: Bash, Write
```

**EvaluatorAgent:**
```
Read: ${CLAUDE_PLUGIN_ROOT}/skills/lang/prompts/evaluator.md
Substitute: PLUGIN_ROOT, SESSION_DATE
Spawn via Agent tool with allowed tools: Bash, Read
```

**ProgressAgent:**
```
Read: ${CLAUDE_PLUGIN_ROOT}/skills/lang/prompts/progress.md
Substitute: PLUGIN_ROOT, MODE (progress|weekly)
Spawn via Agent tool with allowed tools: Bash
```

## After agents complete

- After RoadmapAgent: show a summary of the roadmap (top 5 topics with milestone)
- After ExerciseAgent: display `sessions/YYYY-MM-DD.md` to the user, ask them to fill in answers
- After EvaluatorAgent: show the feedback summary and updated mastery highlights
- After ProgressAgent: present the report; if weekly mode, confirm calendar events created

## Safety

Only create/modify files inside: `sessions/`, `lang.db`, `lang-guide.md` in the current working directory. Never touch files outside.
