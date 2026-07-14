"""
================================================================================
Package: brazilian_soccer_mcp
--------------------------------------------------------------------------------
Context:
    A Model Context Protocol (MCP) server that exposes a knowledge-graph
    interface over Brazilian soccer datasets (Brasileirão, Copa do Brasil,
    Copa Libertadores match data + the FIFA player database). See TASK.md for
    the full specification.

Layout:
    normalize.py        - name / date / encoding normalization helpers
    models.py           - Match & Player domain objects
    data_loader.py      - per-CSV parsers -> normalized domain objects
    knowledge_graph.py  - in-memory graph + all query logic (5 categories)
    formatting.py       - render query results into the answer formats in TASK.md
    server.py           - MCP stdio server (thin adapter over the graph)

Public API:
    from brazilian_soccer_mcp import KnowledgeGraph
================================================================================
"""

from .knowledge_graph import KnowledgeGraph
from .models import Match, Player

__all__ = ["KnowledgeGraph", "Match", "Player"]
__version__ = "1.0.0"
