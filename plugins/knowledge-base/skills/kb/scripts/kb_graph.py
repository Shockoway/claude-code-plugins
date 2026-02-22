#!/usr/bin/env python3
"""
kb_graph: Build graph.json from index.jsonl + glossary terms.

graph.json schema:
  {
    "nodes": [{"id": "...", "type": "...", "title": "...", "path": "..."}],
    "edges": [{"from": "...", "relation": "...", "to": "..."}]
  }

Node types: task, adr, ref, term
Edge relations: touches, motivated_by, affects, supersedes, uses_term, constrained_by

Run:
  python scripts/kb_graph.py [kb_dir] build     # build graph.json
  python scripts/kb_graph.py [kb_dir] impact <id>
  python scripts/kb_graph.py [kb_dir] why <id>
  python scripts/kb_graph.py [kb_dir] trace <adr-id>
  python scripts/kb_graph.py [kb_dir] vocab <id>
"""

import sys
import json
from pathlib import Path
from collections import deque


# ── Graph building ───────────────────────────────────────────────────────────

def extract_glossary_terms(kb_dir: Path) -> list:
    """Extract term nodes from kb/glossary.md using ### headings."""
    glossary = kb_dir / "glossary.md"
    if not glossary.exists():
        return []

    terms = []
    content = glossary.read_text(encoding="utf-8")
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            slug = line[4:].strip()
            # Look ahead for **id:** line
            term_id = slug
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = lines[j].strip()
                if candidate.startswith("**id:**"):
                    term_id = candidate.replace("**id:**", "").strip()
                    break
            terms.append({
                "id": term_id,
                "type": "term",
                "title": slug,
                "path": str(glossary.relative_to(kb_dir.parent)),
            })
        i += 1
    return terms


def build_graph(kb_dir: Path) -> dict:
    """Build graph dict from index.jsonl + glossary terms."""
    # Load index
    index_path = kb_dir / "index.jsonl"
    if not index_path.exists():
        return {"nodes": [], "edges": []}

    entries = []
    with open(index_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    nodes = {}
    edges = []

    # Add document nodes
    for e in entries:
        node_id = e["id"]
        nodes[node_id] = {
            "id": node_id,
            "type": e["type"],
            "title": e.get("title", node_id),
            "path": e.get("path", ""),
        }

    # Add term nodes from glossary
    for term in extract_glossary_terms(kb_dir):
        nodes[term["id"]] = term

    # Build edges from refs block (all types)
    for e in entries:
        refs = e.get("refs") or {}
        if not isinstance(refs, dict):
            continue
        for relation, targets in refs.items():
            if isinstance(targets, list):
                for target in targets:
                    if target:
                        edges.append({"from": e["id"], "relation": relation, "to": target})
            elif targets:
                edges.append({"from": e["id"], "relation": relation, "to": targets})

    return {"nodes": list(nodes.values()), "edges": edges}


def write_graph(kb_dir: Path, graph: dict) -> Path:
    graph_path = kb_dir / "graph.json"
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    return graph_path


def load_graph(kb_dir: Path) -> dict:
    graph_path = kb_dir / "graph.json"
    if not graph_path.exists():
        return {"nodes": [], "edges": []}
    with open(graph_path, encoding="utf-8") as f:
        return json.load(f)


# ── Query helpers ─────────────────────────────────────────────────────────────

def _node_index(graph: dict) -> dict:
    return {n["id"]: n for n in graph.get("nodes", [])}


def _edges_from(graph: dict, node_id: str, relations=None) -> list:
    """Edges going outward from node_id, optionally filtered by relations."""
    return [
        e for e in graph.get("edges", [])
        if e["from"] == node_id and (relations is None or e["relation"] in relations)
    ]


def _edges_to(graph: dict, node_id: str, relations=None) -> list:
    """Edges pointing to node_id, optionally filtered by relations."""
    return [
        e for e in graph.get("edges", [])
        if e["to"] == node_id and (relations is None or e["relation"] in relations)
    ]


def _fmt_node(node_id: str, nodes: dict) -> str:
    n = nodes.get(node_id)
    if n:
        return f"  [{n['type']}] {node_id} — {n['title']}"
    return f"  {node_id} (not in index)"


# ── Query commands ────────────────────────────────────────────────────────────

def cmd_impact(graph: dict, node_id: str) -> None:
    """BFS outward via touches/affects/supersedes."""
    nodes = _node_index(graph)
    if node_id not in nodes:
        print(f"No node found: {node_id}")
        return

    visited = set()
    queue = deque([(node_id, 0)])
    results = []

    while queue:
        current, depth = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        if current != node_id:
            results.append((depth, current))
        for edge in _edges_from(graph, current, {"touches", "affects", "supersedes"}):
            if edge["to"] not in visited:
                queue.append((edge["to"], depth + 1))

    if not results:
        print(f"No impact found from {node_id}")
        return

    print(f"Impact of {node_id}:")
    for depth, nid in sorted(results, key=lambda x: (x[0], x[1])):
        indent = "  " * depth
        print(f"{indent}{_fmt_node(nid, nodes)}")


def cmd_why(graph: dict, module_id: str) -> None:
    """Find ADRs with affects → <module_id>, trace supersedes chain."""
    nodes = _node_index(graph)
    adrs = [
        e["from"] for e in _edges_to(graph, module_id, {"affects"})
        if nodes.get(e["from"], {}).get("type") == "adr"
    ]

    if not adrs:
        print(f"No ADRs found that affect {module_id}")
        return

    print(f"Why {module_id} is shaped this way:")
    for adr_id in adrs:
        print(f"\n{_fmt_node(adr_id, nodes)}")
        # Trace supersedes chain
        current = adr_id
        seen = set()
        while True:
            seen.add(current)
            superseded_by = [
                e["from"] for e in _edges_to(graph, current, {"supersedes"})
                if e["from"] not in seen
            ]
            supersedes = [
                e["to"] for e in _edges_from(graph, current, {"supersedes"})
                if e["to"] not in seen
            ]
            if superseded_by:
                for s in superseded_by:
                    print(f"    ← superseded by: {_fmt_node(s, nodes)}")
                current = superseded_by[0]
            else:
                break
        if supersedes:
            for s in supersedes:
                print(f"    → supersedes: {_fmt_node(s, nodes)}")


def _walk_chain(graph: dict, start: str, outward: bool) -> list:
    """Walk supersedes chain from start. outward=True follows 'supersedes' edges forward."""
    fn = _edges_from if outward else _edges_to
    key = "to" if outward else "from"
    result, current, seen = [], start, {start}
    while True:
        edges = [e[key] for e in fn(graph, current, {"supersedes"}) if e[key] not in seen]
        if not edges:
            break
        result.extend(edges)
        seen.update(edges)
        current = edges[0]
    return result


def cmd_trace(graph: dict, adr_id: str) -> None:
    """Walk supersedes edges both directions from an ADR."""
    nodes = _node_index(graph)
    if adr_id not in nodes:
        print(f"No node found: {adr_id}")
        return

    older = _walk_chain(graph, adr_id, outward=True)   # what this supersedes
    newer = _walk_chain(graph, adr_id, outward=False)  # what supersedes this

    print(f"Supersession chain for {adr_id}:")
    for n in reversed(older):
        print(f"  (older) {_fmt_node(n, nodes)}")
    print(f"  * {_fmt_node(adr_id, nodes)}")
    for n in newer:
        print(f"  (newer) {_fmt_node(n, nodes)}")

    if not older and not newer:
        print("  (no supersession relationships found)")


def cmd_vocab(graph: dict, node_id: str) -> None:
    """Find uses_term edges from <node_id>, show co-users of same terms."""
    nodes = _node_index(graph)
    if node_id not in nodes:
        print(f"No node found: {node_id}")
        return

    terms = [e["to"] for e in _edges_from(graph, node_id, {"uses_term"})]
    if not terms:
        print(f"{node_id} uses no glossary terms")
        return

    print(f"Terms used by {node_id}:")
    for term in terms:
        print(f"  {_fmt_node(term, nodes)}")
        co_users = [
            e["from"] for e in _edges_to(graph, term, {"uses_term"})
            if e["from"] != node_id
        ]
        if co_users:
            print("    Also used by:")
            for cu in co_users:
                print(f"      {_fmt_node(cu, nodes)}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    kb_dir = Path(argv[0]) if argv else Path("kb")

    if not kb_dir.exists():
        print(f"✗ KB directory not found: {kb_dir}")
        sys.exit(1)

    subcommand = argv[1] if len(argv) > 1 else "build"

    if subcommand == "build":
        graph = build_graph(kb_dir)
        path = write_graph(kb_dir, graph)
        n_nodes = len(graph["nodes"])
        n_edges = len(graph["edges"])
        print(f"✓ Written graph.json — {n_nodes} nodes, {n_edges} edges → {path}")

    elif subcommand in ("impact", "why", "trace", "vocab"):
        if len(argv) < 3:
            print(f"✗ Usage: kb_graph.py [kb_dir] {subcommand} <id>")
            sys.exit(1)
        node_id = argv[2]
        graph = load_graph(kb_dir)
        if subcommand == "impact":
            cmd_impact(graph, node_id)
        elif subcommand == "why":
            cmd_why(graph, node_id)
        elif subcommand == "trace":
            cmd_trace(graph, node_id)
        elif subcommand == "vocab":
            cmd_vocab(graph, node_id)

    else:
        print(f"✗ Unknown subcommand: {subcommand}")
        print("Usage: kb_graph.py [kb_dir] build|impact|why|trace|vocab [id]")
        sys.exit(1)


if __name__ == "__main__":
    main()
