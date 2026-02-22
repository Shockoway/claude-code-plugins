#!/usr/bin/env python3
"""
kb_init: Bootstrap KB structure.

Creates:
  kb/
    charter.md
    glossary.md
    roadmap.md
    dashboard.html
    tasks/
    reference/
    decisions/

Does NOT create INDEX.md (replaced by index.jsonl cache).
Adds kb/index.jsonl, kb/graph.json, and kb/dashboard.html to .gitignore.

Run:
  python scripts/kb_init.py [kb_dir]
"""

import sys
from pathlib import Path
from datetime import datetime


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def create_directories(kb_dir: Path) -> None:
    for d in [kb_dir / "tasks", kb_dir / "reference", kb_dir / "decisions"]:
        d.mkdir(parents=True, exist_ok=True)
    print("✓ Created directories (tasks/, reference/, decisions/)")


def _create_from_template(dest: Path, tmpl: Path, subs: dict) -> bool:
    """Create dest from template with substitutions. Returns True if created."""
    if dest.exists():
        print(f"ℹ {dest.name} already exists — skipping")
        return False
    content = tmpl.read_text(encoding="utf-8")
    for old, new in subs.items():
        content = content.replace(old, new)
    dest.write_text(content, encoding="utf-8")
    print(f"✓ Created {dest.name}")
    return True


def copy_dashboard(kb_dir: Path, templates_dir: Path) -> None:
    """Copy dashboard.html template to kb/. No substitutions."""
    dest = kb_dir / "dashboard.html"
    tmpl = templates_dir / "dashboard.html"
    if dest.exists():
        print(f"ℹ dashboard.html already exists — skipping")
        return
    if not tmpl.exists():
        print(f"⚠ dashboard.html template not found in {templates_dir}")
        return
    content = tmpl.read_text(encoding="utf-8")
    dest.write_text(content, encoding="utf-8")
    print("✓ Created dashboard.html")


def update_gitignore(kb_dir: Path) -> None:
    """Add index.jsonl, graph.json, and dashboard.html to .gitignore (project root level)."""
    root = kb_dir.parent
    gitignore = root / ".gitignore"

    entries_to_add = ["kb/index.jsonl", "kb/graph.json", "kb/dashboard.html"]

    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8")
    else:
        existing = ""

    lines_to_add = [e for e in entries_to_add if e not in existing]
    if lines_to_add:
        separator = "\n" if existing and not existing.endswith("\n") else ""
        gitignore.write_text(
            existing + separator + "\n".join(lines_to_add) + "\n",
            encoding="utf-8",
        )
        print(f"✓ Added to .gitignore: {', '.join(lines_to_add)}")
    else:
        print("ℹ .gitignore already contains index.jsonl and graph.json entries")


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    kb_dir = Path(argv[0]) if argv else Path("kb")
    templates_dir = Path(__file__).parent.parent / "templates"

    if not kb_dir.exists():
        kb_dir.mkdir(parents=True, exist_ok=True)

    print("Initializing KB structure...")
    print()

    create_directories(kb_dir)

    subs = {"YYYY-MM-DD": _today()}
    _create_from_template(kb_dir / "charter.md",  templates_dir / "charter.md",  subs)
    _create_from_template(kb_dir / "glossary.md", templates_dir / "glossary.md", subs)
    _create_from_template(kb_dir / "roadmap.md",  templates_dir / "roadmap.md",  subs)

    copy_dashboard(kb_dir, templates_dir)
    update_gitignore(kb_dir)

    print()
    print("✅ KB initialized")
    print()
    print("Next steps:")
    print("  1. Edit kb/charter.md — define scope, goals, invariants")
    print("  2. Edit kb/glossary.md — add canonical terms")
    print("  3. /kb task new <title> — create your first task")
    print("  4. /kb index rebuild — build index.jsonl + graph.json")
    print("  5. Open kb/dashboard.html in browser to view the dashboard")


if __name__ == "__main__":
    main()
