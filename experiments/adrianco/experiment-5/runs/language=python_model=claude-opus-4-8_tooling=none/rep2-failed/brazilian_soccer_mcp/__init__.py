"""
Context
=======
Package: brazilian_soccer_mcp
Purpose: A knowledge-graph + MCP server over the bundled Kaggle Brazilian
soccer datasets (matches, players, competitions).

Layout
------
* ``normalize``       - team-name / date / int normalisation helpers.
* ``models``          - :class:`Match` and :class:`Player` dataclasses.
* ``data_loader``     - load the six CSV files into those models.
* ``knowledge_graph`` - :class:`KnowledgeGraph`, the in-memory graph + query API.
* ``formatting``      - render query results as the text answers in TASK.md.
* ``server``          - the MCP server exposing the query API as tools.

A cached singleton graph is available via :func:`get_graph` so the data is only
parsed once per process.
"""

from __future__ import annotations

from typing import Optional

from .knowledge_graph import KnowledgeGraph
from .models import Match, Player

__all__ = ["KnowledgeGraph", "Match", "Player", "get_graph"]

_GRAPH: Optional[KnowledgeGraph] = None


def get_graph(data_dir: Optional[str] = None) -> KnowledgeGraph:
    """Return a process-wide cached :class:`KnowledgeGraph`."""
    global _GRAPH
    if _GRAPH is None or data_dir is not None:
        _GRAPH = KnowledgeGraph.load(data_dir)
    return _GRAPH
