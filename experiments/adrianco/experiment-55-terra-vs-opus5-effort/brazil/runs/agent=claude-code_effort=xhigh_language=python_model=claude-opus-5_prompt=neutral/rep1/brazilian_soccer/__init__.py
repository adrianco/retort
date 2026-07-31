"""
Brazilian Soccer MCP Server
===========================

Context
-------
This package implements the specification in ``TASK.md``: an MCP (Model Context
Protocol) server that exposes a knowledge graph built from six Kaggle datasets
covering Brazilian soccer (Brasileirao Serie A/B/C, Copa do Brasil, Copa
Libertadores and the FIFA 19 player database).

Layer map (bottom-up)
---------------------
``config``      -- locates the CSV data directory.
``text``        -- unicode/date/number helpers shared by every loader.
``teams``       -- canonical club registry; reconciles the many spellings of a
                   club across datasets ("Palmeiras-SP", "Palmeiras", ...).
``models``      -- dataclasses for Team / Match / Player / statistics rows.
``loaders``     -- one reader per CSV file, all producing ``Match``/``Player``.
``graph``       -- in-memory knowledge graph (nodes + typed edges + indexes)
                   including cross-source match de-duplication.
``queries``     -- the analytical API (search, head-to-head, standings, stats).
``formatting``  -- renders query results as the answer formats in TASK.md.
``tools``       -- transport independent tool layer (name -> callable).
``server``      -- MCP server binding the tool layer to the MCP SDK.
``cli``         -- command line entry point (``serve``, ``call``, ``tools``).

The knowledge graph is loaded once per process and cached; see
``brazilian_soccer.graph.load_knowledge_graph``.
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "load_knowledge_graph",
    "KnowledgeGraph",
]


def __getattr__(name: str):  # pragma: no cover - thin lazy import shim
    if name in {"load_knowledge_graph", "KnowledgeGraph"}:
        from . import graph

        return getattr(graph, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
