"""Brazilian Soccer MCP server package.

Provides a knowledge-graph interface over the bundled Kaggle datasets and an
MCP server (see :mod:`brazilian_soccer_mcp.server`) exposing it as tools.
"""

from __future__ import annotations

from typing import Optional

from .knowledge_graph import SoccerKnowledgeGraph, TeamRecord
from .models import Match, Player

__all__ = [
    "SoccerKnowledgeGraph",
    "TeamRecord",
    "Match",
    "Player",
    "get_graph",
]

__version__ = "1.0.0"

_GRAPH: Optional[SoccerKnowledgeGraph] = None


def get_graph(data_dir: Optional[str] = None) -> SoccerKnowledgeGraph:
    """Return a process-wide cached knowledge graph (lazy loaded)."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = SoccerKnowledgeGraph.from_data_dir(data_dir)
    return _GRAPH
