"""
================================================================================
Brazilian Soccer MCP Server - Package Root
================================================================================

CONTEXT
-------
This package implements a Model Context Protocol (MCP) server that exposes a
queryable knowledge base built from six pre-downloaded Kaggle datasets covering
Brazilian soccer (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores and
a FIFA player database).

The package is split into clearly separated, independently testable layers so
that the data/query logic can be exercised by the BDD test-suite without
requiring the MCP transport to be running:

    normalize.py     - team-name canonicalisation + multi-format date parsing
    data_loader.py   - typed in-memory store loaded from the CSV files
    query_engine.py  - all match/team/player/competition/statistics queries
    server.py        - FastMCP server wiring the query engine to MCP tools

Data quality is handled centrally: the three overlapping Série A sources and the
two overlapping Copa do Brasil sources are de-duplicated by selecting a single
"canonical" source per (competition, season) so that standings and league-wide
statistics are never double counted.

Public API
----------
    >>> from brazilian_soccer_mcp import QueryEngine, load_default_store
    >>> engine = QueryEngine(load_default_store())
    >>> engine.head_to_head("Flamengo", "Fluminense")
================================================================================
"""

from .data_loader import DataStore, Match, Player, load_default_store, default_data_dir
from .query_engine import QueryEngine

__all__ = [
    "DataStore",
    "Match",
    "Player",
    "QueryEngine",
    "load_default_store",
    "default_data_dir",
]

__version__ = "1.0.0"
