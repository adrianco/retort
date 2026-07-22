"""Graphify pre-run hook — build a code knowledge graph in the playpen.

The ``tooling: graphify`` factor level means: before the agent starts, extract a
knowledge graph of the *seeded* code into ``graphify-out/`` so the agent can query
relationships (what-calls-what, blast radius) instead of grepping. Its value is
comprehending an **existing** codebase, so it is a near-no-op on a greenfield task
(nothing to graph) and pays off on a modify-existing task.

Extraction is Graphify's deterministic, **offline, no-API-key** AST pass
(``graphify.extract``). We run it in a SUBPROCESS with Graphify's own interpreter
for two reasons:

* Graphify's tree-sitter grammars live in its venv, not retort's.
* ``graphify.extract.extract`` uses a ``multiprocessing`` pool with the ``spawn``
  start method (the macOS default), which re-imports the driver's ``__main__`` —
  so it must run from a real ``.py`` FILE, never ``python -c`` / a heredoc, or
  every worker dies with ``FileNotFoundError: <stdin>`` and it returns 0 nodes.

Best-effort: if Graphify isn't installed the hook does nothing and the run
proceeds exactly as ``tooling: none`` (the scorers already tolerate a missing
tool), so a run is never *worse off* for enabling the factor.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# The extraction driver. Kept as a module-level string so we can drop it into the
# playpen as a real file (spawn needs a file, see module docstring). It writes
# graph.json + a GRAPH_REPORT.md derived from the AST result (node/edge counts,
# highest-degree "god nodes", per-file counts) — enough for the agent to orient
# without the full clustering pipeline, and $0.
_DRIVER = r'''
import json, sys
from collections import Counter
from pathlib import Path
from graphify.extract import collect_files, extract

def main():
    target = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    files = collect_files(target)
    result = extract(files, cache_root=target)
    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    (out / "graph.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    # Degree over edges → "god nodes" (highest-connectivity symbols): the map an
    # agent wants before touching an existing codebase.
    deg = Counter()
    for e in edges:
        for k in ("source", "target", "from", "to"):
            v = e.get(k) if isinstance(e, dict) else None
            if v is not None:
                deg[v] += 1
    id_to_name = {}
    for n in nodes:
        if isinstance(n, dict):
            id_to_name[n.get("id", n.get("name"))] = n.get("name") or n.get("id")
    top = deg.most_common(20)
    lines = [
        "# GRAPH_REPORT.md — code knowledge graph (graphify, offline AST)",
        "",
        f"- **{len(nodes)} nodes**, **{len(edges)} edges** across **{len(files)} files**.",
        "- Graph data: `graphify-out/graph.json` (GraphRAG-ready).",
        "- Query it: `graphify query \"<question>\"`, `graphify path \"A\" \"B\"`, "
        "`graphify explain \"X\"` (all read graphify-out/graph.json).",
        "",
        "## Highest-connectivity nodes (\"god nodes\" — change these ripple widest)",
        "",
    ]
    for nid, d in top:
        lines.append(f"- `{id_to_name.get(nid, nid)}` — degree {d}")
    (out / "GRAPH_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"nodes": len(nodes), "edges": len(edges), "files": len(files)}))

if __name__ == "__main__":
    main()
'''


def resolve_graphify_python() -> str | None:
    """Path to the interpreter that can ``import graphify`` — resolved from the
    ``graphify`` launcher's shebang (it's a ``uv``/pipx tool, not on retort's
    venv). Returns None if graphify isn't installed."""
    launcher = shutil.which("graphify")
    if launcher is None:
        return None
    try:
        first = Path(launcher).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except OSError:
        return None
    if first.startswith("#!"):
        cand = first[2:].strip()
        if cand and Path(cand).exists():
            return cand
    # Fallback: a sibling `python` next to the launcher (venv/bin layout).
    sibling = Path(launcher).resolve().parent / "python"
    return str(sibling) if sibling.exists() else None


def build_graph(target_dir: Path, *, timeout: int = 300) -> dict | None:
    """Build ``target_dir/graphify-out/{graph.json,GRAPH_REPORT.md}`` from the
    seeded code. Returns ``{nodes, edges, files}`` on success, or None when
    graphify is unavailable or extraction failed (best-effort — never raises)."""
    py = resolve_graphify_python()
    if py is None:
        logger.info("graphify not installed — tooling:graphify is a no-op this run")
        return None

    target_dir = target_dir.resolve()
    out_dir = target_dir / "graphify-out"
    driver = out_dir / ".build_graph.py"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        driver.write_text(_DRIVER, encoding="utf-8")
    except OSError as exc:
        logger.warning("graphify hook: could not stage driver: %s", exc)
        return None

    try:
        proc = subprocess.run(
            [py, str(driver), str(target_dir), str(out_dir)],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            # never let a stray GEMINI key pull in the paid semantic path
            env={k: v for k, v in os.environ.items()
                 if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")},
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("graphify hook: extraction failed: %s", exc)
        return None

    if not (out_dir / "graph.json").is_file():
        logger.warning("graphify hook: no graph.json produced (rc=%s): %s",
                       proc.returncode, (proc.stderr or "")[-300:])
        return None
    try:
        stats = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        stats = {}
    logger.info("graphify hook: built graph — %s", stats)
    return stats
