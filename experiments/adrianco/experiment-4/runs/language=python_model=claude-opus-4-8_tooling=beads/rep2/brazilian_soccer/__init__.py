"""
================================================================================
Brazilian Soccer MCP Server
================================================================================

Context
-------
This package implements a Model Context Protocol (MCP) server that exposes a
knowledge graph built from six pre-downloaded Kaggle datasets covering Brazilian
soccer (matches across Brasileirao, Copa do Brasil and Copa Libertadores, plus a
FIFA player database). It lets an LLM answer natural-language questions about
players, teams, matches, competitions and aggregated statistics.

Module map
----------
- data_loader.py     : Load & normalise the six CSV datasets into typed records.
- knowledge_graph.py : In-memory knowledge graph + lookup indexes.
- queries.py         : Query engine implementing the 5 required capabilities and
                       human-readable formatters.
- server.py          : MCP server (FastMCP) exposing the query engine as tools.

Design notes
------------
The implementation is intentionally dependency-light at runtime: the knowledge
graph is held in memory (plain Python objects + dict indexes) so that simple
lookups respond well under the 2s budget and aggregate queries under 5s without
needing an external database. Team names are normalised (state/country suffixes
stripped, accents folded) so the many naming conventions across datasets unify.
================================================================================
"""

from .data_loader import DataLoader, Match, Player, normalize_team_name
from .knowledge_graph import KnowledgeGraph
from .queries import QueryEngine

__all__ = [
    "DataLoader",
    "Match",
    "Player",
    "normalize_team_name",
    "KnowledgeGraph",
    "QueryEngine",
]
