#!/usr/bin/env python3
"""
KB Skill — namespace-based CLI entry point.

Usage:
  /kb task select [--where field=value] [--sort field] [--limit n]
  /kb task new <title>
  /kb task set <id> <field>=<value>
  /kb task show <id>

  /kb reference select [...]
  /kb reference new <name>
  /kb reference set <id> <field>=<value>
  /kb reference show <id>

  /kb adr select [...]
  /kb adr new <title>
  /kb adr set <id> <field>=<value>
  /kb adr show <id>

  /kb doc open charter|glossary|roadmap

  /kb graph impact|why|trace|vocab <id>

  /kb index rebuild

  /kb init
  /kb lint
  /kb help [namespace]
"""

import sys
import re
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

KB_DIR = Path.cwd() / "kb"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s\-]", "", text.lower())
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def _require_kb() -> bool:
    if not KB_DIR.exists():
        print("✗ KB directory not found. Run: /kb init")
        return False
    return True


def _read_template(name: str) -> str:
    """Read a template file. Raises if not found."""
    path = TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def _render_template(name: str, subs: dict) -> str:
    """Read a template and apply substitutions."""
    content = _read_template(name)
    for old, new in subs.items():
        content = content.replace(old, new)
    return content


# ── Frontmatter field updater ────────────────────────────────────────────────

def update_frontmatter_field(file_path: Path, field: str, value: str) -> bool:
    """
    Update a single scalar field in YAML frontmatter.
    Line-by-line rewriter — does not require full YAML parsing.
    Returns True if field was found and updated, False otherwise.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"✗ Cannot read {file_path}: {e}")
        return False

    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return False

    in_fm = False
    found = False
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n\r")
        if stripped.strip() == "---":
            if not in_fm and i == 0:
                in_fm = True
                new_lines.append(line)
                continue
            else:
                in_fm = False
                new_lines.append(line)
                continue
        if in_fm and not line.startswith(" ") and not line.startswith("\t"):
            key, sep, _ = stripped.partition(":")
            if key.strip() == field and sep:
                # Preserve indentation; write updated value
                indent = len(line) - len(line.lstrip())
                new_lines.append(" " * indent + f"{field}: {value}\n")
                found = True
                continue
        new_lines.append(line)

    if found:
        file_path.write_text("".join(new_lines), encoding="utf-8")
    return found


# ── Select DSL ────────────────────────────────────────────────────────────────

def parse_dsl(args: list) -> dict:
    """
    Parse select DSL from arg list.
    --where field=value (repeatable)
    --sort field
    --limit n
    """
    opts = {"where": [], "sort": None, "limit": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--where" and i + 1 < len(args):
            opts["where"].append(args[i + 1])
            i += 2
        elif a == "--sort" and i + 1 < len(args):
            opts["sort"] = args[i + 1]
            i += 2
        elif a == "--limit" and i + 1 < len(args):
            try:
                opts["limit"] = int(args[i + 1])
            except ValueError:
                print(f"⚠ --limit value must be integer, got: {args[i+1]}")
            i += 2
        else:
            i += 1
    return opts


def run_select(entries: list, dsl: dict) -> list:
    """Filter/sort/limit entries per DSL options."""
    results = list(entries)

    for clause in dsl.get("where", []):
        if "=" in clause:
            field, _, val = clause.partition("=")
            field = field.strip()
            val = val.strip()
            filtered = []
            for e in results:
                entry_val = str(e.get(field, "")).lower()
                if entry_val == val.lower():
                    filtered.append(e)
            results = filtered

    sort_field = dsl.get("sort")
    if sort_field:
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        if sort_field == "priority":
            results.sort(key=lambda e: priority_order.get(e.get("priority", "medium"), 99))
        else:
            results.sort(key=lambda e: str(e.get(sort_field, "")))

    limit = dsl.get("limit")
    if limit is not None:
        results = results[:limit]

    return results


def _print_entry(entry: dict) -> None:
    """Print a single index entry in a readable format."""
    t = entry.get("type", "")
    eid = entry.get("id", "?")
    title = entry.get("title", "")
    status = entry.get("status", "")
    extra = ""
    if t == "task":
        prio = entry.get("priority", "")
        extra = f"  priority={prio}" if prio else ""
    elif t == "adr":
        date = entry.get("date", "")
        extra = f"  date={date}" if date else ""
    elif t == "ref":
        owner = entry.get("owner", "")
        extra = f"  owner={owner}" if owner else ""
    print(f"  {eid}  [{status}]{extra}  {title}")


def _load_index() -> list:
    """Load index.jsonl. Prints hint if missing."""
    import kb_index
    index_path = KB_DIR / "index.jsonl"
    if not index_path.exists():
        print("ℹ index.jsonl not found — run: /kb index rebuild")
        return []
    return kb_index.load_index(KB_DIR)


def _show_file(file_path: Path) -> None:
    """Print the content of a file."""
    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return
    print(file_path.read_text(encoding="utf-8"))


def _find_doc_file(folder: Path, prefix: str, doc_id: str, name_fallback: bool = False) -> Path | None:
    """Find a KB document file by its id. Returns None if not found."""
    slug = doc_id.lower().removeprefix(prefix.rstrip("-").lower()).lstrip("-")
    candidates = list(folder.glob(f"{prefix}{slug}.md"))
    if candidates:
        return candidates[0]
    # fallback: index lookup
    for e in _load_index():
        if e.get("id") == doc_id:
            p = Path(e["path"])
            return p if p.is_absolute() else Path.cwd() / p
    # third fallback: name-based glob (used for ADR partial id match)
    if name_fallback:
        candidates = [c for c in folder.glob(f"{prefix}*.md") if doc_id.lower() in c.name.lower()]
        if candidates:
            return candidates[0]
    return None


# ── Namespace: task ───────────────────────────────────────────────────────────

def _task_new(args: list) -> int:
    if not args:
        print("✗ Usage: /kb task new <title>")
        return 1
    if not _require_kb():
        return 1

    title = " ".join(args)
    slug = _slugify(title)
    file_path = KB_DIR / "tasks" / f"task-{slug}.md"

    if file_path.exists():
        print(f"⚠ Task already exists: {file_path.relative_to(Path.cwd())}")
        return 0

    content = _render_template("task.md", {
        "TASK-<slug>": f"TASK-{slug}",
        "<slug>": slug,
        '"<title>"': f'"{title}"',
        "<title>": title,
        "YYYY-MM-DD": _today(),
    })

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    print(f"✓ Created: {file_path.relative_to(Path.cwd())}")
    print(f"  id: TASK-{slug}")
    return 0


def _task_select(args: list) -> int:
    if not _require_kb():
        return 1
    entries = _load_index()
    tasks = [e for e in entries if e.get("type") == "task"]
    dsl = parse_dsl(args)
    results = run_select(tasks, dsl)
    if not results:
        print("No results")
        return 0
    print(f"Tasks ({len(results)}):")
    for e in results:
        _print_entry(e)
    return 0


def _task_set(args: list) -> int:
    if len(args) < 2:
        print("✗ Usage: /kb task set <id> <field>=<value>")
        return 1
    if not _require_kb():
        return 1

    task_id = args[0]
    assignment = args[1]
    if "=" not in assignment:
        print(f"✗ Expected <field>=<value>, got: {assignment}")
        return 1

    field, _, value = assignment.partition("=")
    field = field.strip()
    value = value.strip()

    file_path = _find_doc_file(KB_DIR / "tasks", "task-", task_id)
    if not file_path:
        print(f"✗ Task not found: {task_id}")
        return 1

    if field == "updated":
        value = _today()

    if update_frontmatter_field(file_path, field, value):
        # Also update the 'updated' timestamp
        if field != "updated":
            update_frontmatter_field(file_path, "updated", _today())
        print(f"✓ {task_id}: {field} = {value}")
        return 0
    else:
        print(f"✗ Field '{field}' not found in frontmatter of {file_path.name}")
        return 1


def _task_show(args: list) -> int:
    if not args:
        print("✗ Usage: /kb task show <id>")
        return 1
    if not _require_kb():
        return 1

    task_id = args[0]
    file_path = _find_doc_file(KB_DIR / "tasks", "task-", task_id)
    if not file_path:
        print(f"✗ Task not found: {task_id}")
        return 1
    _show_file(file_path)
    return 0


# ── Namespace: reference ──────────────────────────────────────────────────────

def _reference_new(args: list) -> int:
    if not args:
        print("✗ Usage: /kb reference new <name>")
        return 1
    if not _require_kb():
        return 1

    name = " ".join(args)
    slug = _slugify(name)
    file_path = KB_DIR / "reference" / f"ref-{slug}.md"

    if file_path.exists():
        print(f"⚠ Module reference already exists: {file_path.relative_to(Path.cwd())}")
        return 0

    content = _render_template("module.md", {
        "ref-<slug>": f"ref-{slug}",
        "<slug>": slug,
        '"<name>"': f'"{name}"',
        "<name>": name,
        "YYYY-MM-DD": _today(),
    })

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    print(f"✓ Created: {file_path.relative_to(Path.cwd())}")
    print(f"  id: ref-{slug}")
    return 0


def _reference_select(args: list) -> int:
    if not _require_kb():
        return 1
    entries = _load_index()
    modules = [e for e in entries if e.get("type") == "ref"]
    dsl = parse_dsl(args)
    results = run_select(modules, dsl)
    if not results:
        print("No results")
        return 0
    print(f"References ({len(results)}):")
    for e in results:
        _print_entry(e)
    return 0


def _reference_set(args: list) -> int:
    if len(args) < 2:
        print("✗ Usage: /kb reference set <id> <field>=<value>")
        return 1
    if not _require_kb():
        return 1

    ref_id = args[0]
    assignment = args[1]
    if "=" not in assignment:
        print(f"✗ Expected <field>=<value>, got: {assignment}")
        return 1

    field, _, value = assignment.partition("=")
    field = field.strip()
    value = value.strip()

    file_path = _find_doc_file(KB_DIR / "reference", "ref-", ref_id)
    if not file_path:
        print(f"✗ Reference not found: {ref_id}")
        return 1

    if update_frontmatter_field(file_path, field, value):
        print(f"✓ {ref_id}: {field} = {value}")
        return 0
    else:
        print(f"✗ Field '{field}' not found in frontmatter of {file_path.name}")
        return 1


def _reference_show(args: list) -> int:
    if not args:
        print("✗ Usage: /kb reference show <id>")
        return 1
    if not _require_kb():
        return 1

    ref_id = args[0]
    file_path = _find_doc_file(KB_DIR / "reference", "ref-", ref_id)
    if not file_path:
        print(f"✗ Reference not found: {ref_id}")
        return 1
    _show_file(file_path)
    return 0


# ── Namespace: adr ────────────────────────────────────────────────────────────

def _adr_new(args: list) -> int:
    if not args:
        print("✗ Usage: /kb adr new <title>")
        return 1
    if not _require_kb():
        return 1

    title = " ".join(args)
    slug = _slugify(title)
    date_str = datetime.now().strftime("%Y%m%d")
    adr_id = f"ADR-{date_str}-{slug}"
    file_path = KB_DIR / "decisions" / f"adr-{date_str}-{slug}.md"

    if file_path.exists():
        print(f"⚠ ADR already exists: {file_path.relative_to(Path.cwd())}")
        return 0

    content = _render_template("adr.md", {
        "ADR-YYYYMMDD-<slug>": adr_id,
        "<slug>": slug,
        '"<title>"': f'"{title}"',
        "<title>": title,
        "YYYY-MM-DD": _today(),
    })

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    print(f"✓ Created: {file_path.relative_to(Path.cwd())}")
    print(f"  id: {adr_id}")
    return 0


def _adr_select(args: list) -> int:
    if not _require_kb():
        return 1
    entries = _load_index()
    adrs = [e for e in entries if e.get("type") == "adr"]
    dsl = parse_dsl(args)
    results = run_select(adrs, dsl)
    if not results:
        print("No results")
        return 0
    print(f"ADRs ({len(results)}):")
    for e in results:
        _print_entry(e)
    return 0


def _adr_set(args: list) -> int:
    if len(args) < 2:
        print("✗ Usage: /kb adr set <id> <field>=<value>")
        return 1
    if not _require_kb():
        return 1

    adr_id = args[0]
    assignment = args[1]
    if "=" not in assignment:
        print(f"✗ Expected <field>=<value>, got: {assignment}")
        return 1

    field, _, value = assignment.partition("=")
    field = field.strip()
    value = value.strip()

    file_path = _find_doc_file(KB_DIR / "decisions", "adr-", adr_id, name_fallback=True)
    if not file_path:
        print(f"✗ ADR not found: {adr_id}")
        return 1

    if update_frontmatter_field(file_path, field, value):
        print(f"✓ {adr_id}: {field} = {value}")
        return 0
    else:
        print(f"✗ Field '{field}' not found in frontmatter of {file_path.name}")
        return 1


def _adr_show(args: list) -> int:
    if not args:
        print("✗ Usage: /kb adr show <id>")
        return 1
    if not _require_kb():
        return 1

    adr_id = args[0]
    file_path = _find_doc_file(KB_DIR / "decisions", "adr-", adr_id, name_fallback=True)
    if not file_path:
        print(f"✗ ADR not found: {adr_id}")
        return 1
    _show_file(file_path)
    return 0


# ── Entity dispatch ───────────────────────────────────────────────────────────

_ENTITY_VERBS = {
    "task":      {"new": _task_new, "select": _task_select, "set": _task_set, "show": _task_show},
    "reference": {"new": _reference_new, "select": _reference_select, "set": _reference_set, "show": _reference_show},
    "adr":       {"new": _adr_new, "select": _adr_select, "set": _adr_set, "show": _adr_show},
}


def _dispatch_entity(ns: str, args: list) -> int:
    if not args:
        return _help_namespace(ns)
    verb, rest = args[0], args[1:]
    verbs = _ENTITY_VERBS[ns]
    if verb not in verbs:
        print(f"✗ Unknown {ns} verb: {verb}. Use: {' | '.join(verbs)}")
        return 1
    return verbs[verb](rest)


# ── Namespace: doc ────────────────────────────────────────────────────────────

def ns_doc(args: list) -> int:
    if not args or args[0] != "open":
        print("✗ Usage: /kb doc open charter|glossary|roadmap")
        return 1

    if len(args) < 2:
        print("✗ Specify a document: charter | glossary | roadmap")
        return 1

    doc_name = args[1].lower().strip()
    valid_docs = {"charter", "glossary", "roadmap"}
    if doc_name not in valid_docs:
        print(f"✗ Unknown document '{doc_name}'. Valid: {', '.join(sorted(valid_docs))}")
        return 1

    if not _require_kb():
        return 1

    file_path = KB_DIR / f"{doc_name}.md"
    if not file_path.exists():
        print(f"✗ {doc_name}.md not found — run: /kb init")
        return 1

    _show_file(file_path)
    return 0


# ── Namespace: graph ──────────────────────────────────────────────────────────

def ns_graph(args: list) -> int:
    if not args:
        return _help_namespace("graph")

    subcommand = args[0]
    rest = args[1:]

    valid = {"impact", "why", "trace", "vocab"}
    if subcommand not in valid:
        print(f"✗ Unknown graph subcommand: {subcommand}. Use: impact | why | trace | vocab")
        return 1

    if not rest:
        print(f"✗ Usage: /kb graph {subcommand} <id>")
        return 1

    if not _require_kb():
        return 1

    import kb_graph
    try:
        graph = kb_graph.load_graph(KB_DIR)
    except Exception as e:
        print(f"✗ Cannot load graph.json: {e}")
        print("  Run: /kb index rebuild")
        return 1

    node_id = rest[0]
    if subcommand == "impact":
        kb_graph.cmd_impact(graph, node_id)
    elif subcommand == "why":
        kb_graph.cmd_why(graph, node_id)
    elif subcommand == "trace":
        kb_graph.cmd_trace(graph, node_id)
    elif subcommand == "vocab":
        kb_graph.cmd_vocab(graph, node_id)

    return 0


# ── Namespace: index ──────────────────────────────────────────────────────────

def ns_index(args: list) -> int:
    if not args or args[0] != "rebuild":
        print("✗ Usage: /kb index rebuild")
        return 1

    if not _require_kb():
        return 1

    import kb_index
    import kb_graph

    print("Rebuilding index.jsonl...")
    try:
        entries = kb_index.scan_kb(KB_DIR)
        kb_index.write_index(KB_DIR, entries)
        print(f"✓ index.jsonl — {len(entries)} entries")
    except Exception as e:
        print(f"✗ Error building index: {e}")
        return 1

    print("Rebuilding graph.json...")
    try:
        graph = kb_graph.build_graph(KB_DIR)
        kb_graph.write_graph(KB_DIR, graph)
        n_nodes = len(graph["nodes"])
        n_edges = len(graph["edges"])
        print(f"✓ graph.json — {n_nodes} nodes, {n_edges} edges")
    except Exception as e:
        print(f"✗ Error building graph: {e}")
        return 1

    return 0


# ── Top-level commands ────────────────────────────────────────────────────────

def cmd_init(args: list) -> int:
    import kb_init
    try:
        kb_init.main([str(KB_DIR)])
        return 0
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


def cmd_lint(args: list) -> int:
    import kb_lint
    try:
        linter = kb_lint.KBLinter(KB_DIR)
        return 0 if linter.lint() else 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


# ── Help ──────────────────────────────────────────────────────────────────────

HELP_TEXT = {
    "task": """\
/kb task — manage tasks

  /kb task new <title>                    Create a new task
  /kb task select [--where f=v] [--sort f] [--limit n]
                                          Query tasks
  /kb task set <id> <field>=<value>       Update a frontmatter field
  /kb task show <id>                      Show full task document

  select DSL:  /kb help select
""",
    "reference": """\
/kb reference — manage module reference docs

  /kb reference new <name>               Create a new module reference
  /kb reference select [...]             Query references (same DSL as task)
  /kb reference set <id> <field>=<value> Update a frontmatter field
  /kb reference show <id>                Show full reference document
""",
    "adr": """\
/kb adr — manage Architecture Decision Records

  /kb adr new <title>                    Create a new ADR
  /kb adr select [...]                   Query ADRs
  /kb adr set <id> <field>=<value>       Update a frontmatter field
  /kb adr show <id>                      Show full ADR
""",
    "doc": """\
/kb doc — open strategic documents

  /kb doc open charter                   Project scope, goals, invariants
  /kb doc open glossary                  Canonical terminology
  /kb doc open roadmap                   Epics and future work
""",
    "graph": """\
/kb graph — knowledge graph queries

  /kb graph impact <id>    What does this node affect? (BFS via touches/affects/supersedes)
  /kb graph why <id>       Why is this module shaped this way? (ADRs affecting it)
  /kb graph trace <adr-id> Walk the supersedes chain both directions
  /kb graph vocab <id>     What terms does this node use, and who else uses them?

  Requires: /kb index rebuild
""",
    "index": """\
/kb index — manage the index cache

  /kb index rebuild    Rebuild index.jsonl + graph.json from all KB files
""",
    "select": """\
select DSL:

  --where <field>=<value>   Filter by field value (repeatable)
  --sort <field>            Sort by field (priority sorts by severity: critical>high>medium>low)
  --limit <n>               Return at most n results

Examples:
  /kb task select --where status=planned --sort priority
  /kb task select --where priority=high --limit 5
  /kb adr select --where status=proposed
  /kb reference select --where status=active
""",
}


def _help_namespace(ns: str) -> int:
    text = HELP_TEXT.get(ns)
    if text:
        print(text)
        return 0
    print(f"No help for namespace: {ns}")
    return 1


def cmd_help(args: list) -> int:
    if args:
        return _help_namespace(args[0])

    print("""\
KB Skill — repo-local knowledge base

NAMESPACES:
  /kb task <verb> [...]         Manage tasks
  /kb reference <verb> [...]    Manage module reference docs
  /kb adr <verb> [...]          Manage Architecture Decision Records
  /kb doc open <name>           Open charter | glossary | roadmap
  /kb graph <cmd> <id>          Graph queries: impact | why | trace | vocab
  /kb index rebuild             Rebuild index.jsonl + graph.json

TOP-LEVEL:
  /kb init                      Bootstrap KB structure
  /kb lint                      Validate KB
  /kb help [namespace]          Show this help (or namespace help)

Run /kb help <namespace> for details on each namespace.
Run /kb help select for the query DSL.
""")
    return 0


# ── Main dispatcher ───────────────────────────────────────────────────────────

NAMESPACES = {
    "task":      lambda args: _dispatch_entity("task", args),
    "reference": lambda args: _dispatch_entity("reference", args),
    "adr":       lambda args: _dispatch_entity("adr", args),
    "doc":       ns_doc,
    "graph":     ns_graph,
    "index":     ns_index,
}

TOP_LEVEL = {
    "init": cmd_init,
    "lint": cmd_lint,
    "help": cmd_help,
}


def main():
    args = sys.argv[1:]

    if not args:
        cmd_help([])
        return 0

    command = args[0]
    rest = args[1:]

    if command in NAMESPACES:
        return NAMESPACES[command](rest)
    elif command in TOP_LEVEL:
        return TOP_LEVEL[command](rest)
    else:
        print(f"✗ Unknown command: {command}")
        cmd_help([])
        return 1


if __name__ == "__main__":
    sys.exit(main())
