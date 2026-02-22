---
name: kb
description: Maintain the repo-local KB in kb/. Manage tasks, reference docs, and ADRs; query the knowledge graph; run lint/index rebuild. Use at the start of significant work, when making architecture decisions, or when you need to know what to work on next.
user-invocable: true
allowed-tools: Bash, Write, Edit
context: default
---

# KB Skill

**For agents: Use `Skill(shockoway-knowledge-base:kb)` to invoke this skill.**

Namespace-based knowledge base management for long-running projects.

## Philosophy

Three questions drive all KB work:
1. **Is this in scope?** → `/kb doc open charter`
2. **What's the canonical name?** → `/kb doc open glossary`
3. **Why is it shaped this way?** → `/kb graph why <ref-id>`

Two laws:
- **Law 1 (charter):** Every invariant lives in `kb/charter.md`. If it's not there, it's not an invariant.
- **Law 2 (glossary):** Every canonical name lives in `kb/glossary.md`. If it's not there, it's not canonical.

## Agent behavior rules

```
Before any decision or introducing a new term:
  /kb doc open charter   → check invariants
  /kb doc open glossary  → use canonical names

For "what should I work on next?":
  /kb task select --where status=planned --sort priority

For "why is X shaped this way?":
  /kb graph why <ref-id>  →  /kb graph trace <adr-id>

For multi-session work:
  /kb task new <title>  →  update ## Next steps at each stop

For real trade-offs:
  /kb adr new <title>  →  mark accepted after decision is made

For contract changes to a component:
  /kb reference show <id>  →  edit doc

When asked to set up KB for an existing project:
  1. If kb/ doesn't exist: /kb init
  2. Ask: "Do you want to fill in the charter now? I'll ask one question at a time."
  3. If yes, interview — one question at a time, wait for answer before asking next:
     - "What problem are we solving, and who has it?"
     - "What are the goals? (top 1–3)"
     - "What is explicitly out of scope?"
     - "Any hard constraints or invariants?"
  Do NOT infer charter content from the codebase.
  Write only what the user explicitly provides.
```

## Scope and safety

- This skill may ONLY create/edit files under `kb/`.
- Never modify product code with this skill.
- Scripts use Python 3.6+ standard library only.

## Execution

Two rules, no exceptions:

1. **Structure and metadata → CLI only.** Creating files, updating frontmatter fields, querying, rebuilding index — always via the shell wrapper. Never create KB files with Write, never patch frontmatter with Edit.
2. **Document content → Write/Edit.** After CLI creates a stub, fill in the markdown body with Write or Edit.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" <command> [args...]
```

Examples:
```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" init
bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" task select --where status=planned --sort priority --limit 10
bash "${CLAUDE_PLUGIN_ROOT}/skills/kb/scripts/kb.sh" adr new "use postgres for storage"
```

Show CLI output to the user as-is.

## Commands

### /kb init
Bootstrap KB structure. Run once when starting a new KB.

### /kb task new <title>
Create a task. Example: `/kb task new implement auth middleware`
Creates: `kb/tasks/task-implement-auth-middleware.md`

### /kb task select [--where field=value] [--sort field] [--limit n]
Query tasks from the index. Example: `/kb task select --where status=planned --sort priority`

### /kb task set <id> <field>=<value>
Update a frontmatter field. Example: `/kb task set TASK-my-task status=in-progress`

### /kb task show <id>
Print the full task document.

### /kb reference new <name>
Create a reference doc. Example: `/kb reference new auth module`
Creates: `kb/reference/ref-auth-module.md`

### /kb reference select / set / show
Same verb pattern as task.

### /kb adr new <title>
Create an Architecture Decision Record.
Creates: `kb/decisions/adr-YYYYMMDD-<slug>.md`

### /kb adr select / set / show
Same verb pattern as task.

### /kb doc open charter|glossary|roadmap
Print a strategic document.

### /kb graph impact <id>
What does this node touch or affect? BFS outward.

### /kb graph why <id>
Which ADRs explain why this component is shaped this way?

### /kb graph trace <adr-id>
Walk the supersedes chain both directions.

### /kb graph vocab <id>
Which glossary terms does this node use? Who else uses them?

### /kb index rebuild
Rebuild `kb/index.jsonl` (cache) and `kb/graph.json` (derived).
Index rebuilds automatically at session start/end. Use manually if index gets out of sync.

### /kb lint
Validate KB structure, frontmatter schemas, git hygiene.

### /kb help [namespace]
Show help. Run `/kb help select` for the query DSL.

## KB structure (output of /kb init)

```
kb/
  charter.md              # Law 1: scope/goals/non-goals/invariants
  glossary.md             # Law 2: canonical terms
  roadmap.md              # Epics only
  index.jsonl             # Cache — rebuild with /kb index rebuild (gitignored)
  graph.json              # Derived — rebuild with /kb index rebuild (gitignored)
  tasks/
    task-*.md
  reference/
    ref-*.md
  decisions/
    adr-*.md
```

## Frontmatter schemas

### task-*.md
```yaml
id: TASK-<slug>
type: task
title: "<title>"
status: planned          # planned | in-progress | done | cancelled
priority: medium         # critical | high | medium | low
refs:
  touches: []            # ref-* ids
  motivated_by: []       # adr-* ids
  uses_term: []          # glossary term slugs
created: YYYY-MM-DD
updated: YYYY-MM-DD
```

### adr-*.md
```yaml
id: ADR-YYYYMMDD-<slug>
type: adr
title: "<title>"
status: proposed         # proposed | accepted | rejected | superseded
date: YYYY-MM-DD
refs:
  affects: []            # ref-* ids
  supersedes: null
  constrained_by: []     # charter section names
  uses_term: []
```

### ref-*.md
```yaml
id: ref-<slug>
type: ref
name: "<name>"
owner: "@you"
last_reviewed: YYYY-MM-DD
refs:
  uses_term: []
```

## Old → New command map

| Old | New |
|-----|-----|
| `/kb pack <title>` | `/kb task new <title>` |
| `/kb module <name>` | `/kb reference new <name>` |
| `/kb adr <title>` | `/kb adr new <title>` |
| `/kb sync` | `/kb lint` + `/kb index rebuild` |
| `kb/INDEX.md` | `kb/index.jsonl` (cache, gitignored) |
