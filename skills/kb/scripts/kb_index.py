#!/usr/bin/env python3
"""
kb_index: Generate kb/index.jsonl from all task/adr/module frontmatter.

index.jsonl is a rebuild-able cache — safe to delete and regenerate anytime.
Never commit it to git (add kb/index.jsonl to .gitignore).

Run:
  python scripts/kb_index.py [kb_dir]        # build index.jsonl
  python scripts/kb_index.py [kb_dir] verify # verify JSON validity
"""

import sys
import json
from pathlib import Path


def parse_frontmatter(content: str) -> dict:
    """
    Parse YAML frontmatter from a markdown file using stdlib only.

    Handles:
    - Scalar strings (quoted or unquoted)
    - null / ~ values
    - Simple lists (block style: "  - item")
    - Nested dicts of lists (for refs: block)

    Returns {} if no frontmatter found.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fm_lines = []
    i = 1
    while i < len(lines):
        if lines[i].strip() == "---":
            break
        fm_lines.append(lines[i])
        i += 1

    if i >= len(lines):
        return {}  # no closing ---

    result = {}
    j = 0
    while j < len(fm_lines):
        line = fm_lines[j]
        # Skip blank lines
        if not line.strip():
            j += 1
            continue
        # Top-level key: value
        if line and not line.startswith(" ") and ":" in line:
            key, _, raw_val = line.partition(":")
            key = key.strip()
            raw_val = raw_val.strip()

            if raw_val == "" or raw_val is None:
                # Could be a block mapping or block sequence
                # Peek ahead to determine which
                sub_lines = []
                k = j + 1
                while k < len(fm_lines) and (fm_lines[k].startswith("  ") or fm_lines[k].startswith("\t")):
                    sub_lines.append(fm_lines[k])
                    k += 1
                j = k

                if not sub_lines:
                    result[key] = None
                elif sub_lines[0].lstrip().startswith("- "):
                    # Block sequence (simple list)
                    items = []
                    for sl in sub_lines:
                        stripped = sl.lstrip()
                        if stripped.startswith("- "):
                            items.append(_parse_scalar(stripped[2:].strip()))
                    result[key] = items
                else:
                    # Block mapping (dict of lists, e.g. refs:)
                    sub_dict = {}
                    m = 0
                    while m < len(sub_lines):
                        sl = sub_lines[m]
                        stripped = sl.strip()
                        if ":" in stripped:
                            sub_key, _, sub_raw = stripped.partition(":")
                            sub_key = sub_key.strip()
                            sub_raw = sub_raw.strip()
                            if sub_raw == "[]":
                                sub_dict[sub_key] = []
                                m += 1
                            elif sub_raw == "":
                                # nested list
                                items = []
                                m += 1
                                while m < len(sub_lines):
                                    inner = sub_lines[m].strip()
                                    if inner.startswith("- "):
                                        items.append(_parse_scalar(inner[2:].strip()))
                                        m += 1
                                    else:
                                        break
                                sub_dict[sub_key] = items
                            else:
                                # inline list [a, b] or scalar
                                sub_dict[sub_key] = _parse_inline_or_scalar(sub_raw)
                                m += 1
                        else:
                            m += 1
                    result[key] = sub_dict
            else:
                result[key] = _parse_inline_or_scalar(raw_val)
                j += 1
        else:
            j += 1

    return result


def _parse_scalar(s: str):
    """Parse a scalar YAML value."""
    if s in ("null", "~", ""):
        return None
    if s in ("true", "True", "yes"):
        return True
    if s in ("false", "False", "no"):
        return False
    # Strip surrounding quotes
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _parse_inline_or_scalar(s: str):
    """Parse inline list [a, b, c] or a scalar."""
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in inner.split(","):
            items.append(_parse_scalar(item.strip()))
        return items
    return _parse_scalar(s)


def scan_kb(kb_dir: Path) -> list:
    """Scan KB for task/adr/module files and return list of index entries."""
    entries = []

    patterns = [
        ("tasks", "task-*.md", "task"),
        ("decisions", "adr-*.md", "adr"),
        ("reference", "module-*.md", "module"),
    ]

    for subdir, glob_pat, expected_type in patterns:
        folder = kb_dir / subdir
        if not folder.exists():
            continue
        for md_file in sorted(folder.glob(glob_pat)):
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  ⚠ Cannot read {md_file.name}: {e}", file=sys.stderr)
                continue

            fm = parse_frontmatter(content)
            if not fm:
                print(f"  ⚠ No frontmatter in {md_file.name}", file=sys.stderr)
                continue

            entry = _build_entry(fm, md_file, kb_dir, expected_type)
            if entry:
                entries.append(entry)

    return entries


def _build_entry(fm: dict, path: Path, kb_dir: Path, expected_type: str) -> dict:
    """Build an index entry from frontmatter + path."""
    doc_id = fm.get("id") or fm.get("module_name") or path.stem
    doc_type = fm.get("type", expected_type)
    title = fm.get("title") or fm.get("name") or doc_id

    entry = {
        "id": str(doc_id),
        "type": str(doc_type),
        "title": str(title),
        "path": str(path.relative_to(kb_dir.parent)),
    }

    # Type-specific fields
    if expected_type == "task":
        entry["status"] = fm.get("status", "planned")
        entry["priority"] = fm.get("priority", "medium")
        refs = fm.get("refs", {})
        if isinstance(refs, dict):
            entry["refs"] = {
                "touches": refs.get("touches") or [],
                "motivated_by": refs.get("motivated_by") or [],
                "uses_term": refs.get("uses_term") or [],
            }
        else:
            entry["refs"] = {"touches": [], "motivated_by": [], "uses_term": []}
        entry["updated"] = fm.get("updated", "")

    elif expected_type == "adr":
        entry["status"] = fm.get("status", "proposed")
        entry["date"] = fm.get("date", "")
        entry["affects"] = fm.get("affects") or []
        entry["supersedes"] = fm.get("supersedes")
        entry["constrained_by"] = fm.get("constrained_by") or []
        entry["uses_term"] = fm.get("uses_term") or []

    elif expected_type == "module":
        entry["status"] = fm.get("status", "active")
        entry["owner"] = fm.get("owner", "")
        entry["last_reviewed"] = fm.get("last_reviewed", "")

    return entry


def write_index(kb_dir: Path, entries: list) -> Path:
    """Write entries to kb/index.jsonl."""
    index_path = kb_dir / "index.jsonl"
    with open(index_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return index_path


def load_index(kb_dir: Path) -> list:
    """Load entries from kb/index.jsonl. Returns [] if not found."""
    index_path = kb_dir / "index.jsonl"
    if not index_path.exists():
        return []
    entries = []
    with open(index_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    kb_dir = Path(argv[0]) if argv else Path("kb")
    verify_mode = len(argv) > 1 and argv[1] == "verify"

    if not kb_dir.exists():
        print(f"✗ KB directory not found: {kb_dir}")
        sys.exit(1)

    if verify_mode:
        index_path = kb_dir / "index.jsonl"
        if not index_path.exists():
            print("✗ index.jsonl not found")
            sys.exit(1)
        try:
            entries = load_index(kb_dir)
            print(f"✓ index.jsonl valid — {len(entries)} entries")
        except Exception as e:
            print(f"✗ index.jsonl invalid: {e}")
            sys.exit(1)
        return

    entries = scan_kb(kb_dir)
    index_path = write_index(kb_dir, entries)
    print(f"✓ Written {len(entries)} entries to {index_path}")


if __name__ == "__main__":
    main()
