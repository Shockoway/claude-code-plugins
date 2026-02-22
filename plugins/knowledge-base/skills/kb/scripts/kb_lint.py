#!/usr/bin/env python3
"""
kb_lint: Validate KB structure, frontmatter schemas, and git hygiene.

Run:
  python scripts/kb_lint.py [kb_dir]
"""

import sys
import subprocess
from pathlib import Path

# ANSI colors
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
GREEN = '\033[0;32m'
NC = '\033[0m'

# Required fields and valid status enums per type
REQUIRED_FIELDS = {
    "task": ["id", "type", "title", "status", "priority", "created", "updated"],
    "adr": ["id", "type", "title", "status", "date", "refs"],
    "ref": ["id", "type", "name", "owner", "last_reviewed", "refs"],
}

STATUS_ENUMS = {
    "task": {"planned", "in-progress", "done", "cancelled"},
    "adr": {"proposed", "accepted", "rejected", "superseded"},
}


def _is_git_tracked(path: Path) -> bool:
    """Return True if path is tracked by git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            capture_output=True,
            cwd=str(path.parent),
        )
        return result.returncode == 0
    except Exception:
        return False


class KBLinter:
    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.errors: list = []
        self.warnings: list = []
        self.valid = True

    def error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False
        print(f"{RED}✗ {msg}{NC}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"{YELLOW}⚠ {msg}{NC}")

    def ok(self, msg: str) -> None:
        print(f"{GREEN}✓ {msg}{NC}")

    # ── Structural checks ───────────────────────────────────────────────────

    def check_kb_exists(self) -> bool:
        if not self.kb_dir.exists():
            self.error(f"KB directory not found: {self.kb_dir}")
            return False
        return True

    def check_index_md_gone(self) -> None:
        """Warn if old INDEX.md still exists (replaced by index.jsonl)."""
        index_md = self.kb_dir / "INDEX.md"
        if index_md.exists():
            self.warn(
                "kb/INDEX.md exists — this is replaced by kb/index.jsonl. "
                "Consider deleting kb/INDEX.md."
            )

    def check_cache_files_not_tracked(self) -> None:
        """Warn if index.jsonl or graph.json are git-tracked."""
        for fname in ("index.jsonl", "graph.json"):
            f = self.kb_dir / fname
            if f.exists() and _is_git_tracked(f):
                self.warn(
                    f"kb/{fname} is tracked by git — it should be in .gitignore "
                    f"(it's a rebuild-able cache)."
                )

    def check_required_docs(self) -> None:
        """Warn if charter.md or glossary.md are missing."""
        for fname in ("charter.md", "glossary.md"):
            if not (self.kb_dir / fname).exists():
                self.warn(f"kb/{fname} is missing — run /kb init to create it")

    # ── Frontmatter validation ──────────────────────────────────────────────

    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter, handling nested structures like refs:."""
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

        result = {}
        i = 0
        while i < len(fm_lines):
            line = fm_lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Only process top-level keys (no leading spaces/tabs)
            if line.startswith(" ") or line.startswith("\t"):
                i += 1
                continue

            # Parse key: value
            if ":" not in line:
                i += 1
                continue

            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()

            # If this is a block (value is empty but has indented children),
            # mark it as non-empty so validation passes
            if not val:
                j = i + 1
                has_children = False
                while j < len(fm_lines):
                    next_line = fm_lines[j]
                    if not next_line.strip():
                        j += 1
                        continue
                    if next_line.startswith(" ") or next_line.startswith("\t"):
                        has_children = True
                        break
                    else:
                        break

                if has_children:
                    val = "<block>"  # Non-empty marker for validation

            result[key] = val
            i += 1

        return result

    def check_document_schemas(self) -> None:
        """Validate required fields and enum values for task/adr/ref files."""
        patterns = [
            (self.kb_dir / "tasks", "task-*.md", "task"),
            (self.kb_dir / "decisions", "adr-*.md", "adr"),
            (self.kb_dir / "reference", "ref-*.md", "ref"),
        ]
        for folder, glob, doc_type in patterns:
            if not folder.exists():
                continue
            for md_file in sorted(folder.glob(glob)):
                try:
                    content = md_file.read_text(encoding="utf-8")
                except Exception as e:
                    self.warn(f"Cannot read {md_file.name}: {e}")
                    continue

                if not content.startswith("---"):
                    self.error(f"{md_file.name}: missing frontmatter")
                    continue

                fm = self._parse_frontmatter(content)
                rel = md_file.relative_to(self.kb_dir)

                # Check required fields
                for field in REQUIRED_FIELDS.get(doc_type, []):
                    if field not in fm or not fm[field]:
                        self.error(f"{rel}: missing required field '{field}'")

                # Check status enum
                status = fm.get("status", "").strip('"\'')
                valid_statuses = STATUS_ENUMS.get(doc_type, set())
                if status and status not in valid_statuses:
                    self.error(
                        f"{rel}: invalid status '{status}' for type '{doc_type}'. "
                        f"Valid: {sorted(valid_statuses)}"
                    )

    def check_naming_conventions(self) -> None:
        """Check file naming conventions."""
        checks = [
            (self.kb_dir / "decisions", "*.md", "adr-", ["README.md"]),
            (self.kb_dir / "reference", "*.md", "ref-", ["README.md"]),
            (self.kb_dir / "tasks", "*.md", "task-", ["README.md"]),
        ]
        for folder, glob, prefix, allowed_exceptions in checks:
            if not folder.exists():
                continue
            for f in sorted(folder.glob(glob)):
                if f.name not in allowed_exceptions and not f.name.startswith(prefix):
                    self.warn(
                        f"File in {folder.name}/ should start with '{prefix}': {f.name}"
                    )

    # ── Main ────────────────────────────────────────────────────────────────

    def lint(self) -> bool:
        print("Running KB lint...\n")

        if not self.check_kb_exists():
            return False

        self.check_index_md_gone()
        self.check_cache_files_not_tracked()
        self.check_required_docs()
        self.check_document_schemas()
        self.check_naming_conventions()

        print()
        if not self.errors and not self.warnings:
            self.ok("KB lint passed — no issues found")
            return True
        elif not self.errors:
            print(f"{YELLOW}KB lint passed with {len(self.warnings)} warning(s){NC}")
            return True
        else:
            print(
                f"{RED}KB lint failed — {len(self.errors)} error(s), "
                f"{len(self.warnings)} warning(s){NC}"
            )
            return False


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    kb_dir = Path(argv[0]) if argv else Path("kb")
    linter = KBLinter(kb_dir)
    if not linter.lint():
        sys.exit(1)


if __name__ == "__main__":
    main()
