"""
================================================================================
Brazilian Soccer MCP Server
================================================================================

CONTEXT
-------
This package implements a Model Context Protocol (MCP) server that exposes a
knowledge-graph style interface over a collection of Brazilian soccer datasets
(see ``brazilian-soccer-mcp-guide.md`` for the full specification).

The package is organised in layers so that the data/query logic is completely
independent of the MCP transport. This makes the core engine trivially testable
with plain ``pytest`` (no running server or external database required):

    normalize.py        - team-name / date / competition normalisation helpers
    data_loader.py      - reads the 6 provided CSV files into tidy pandas tables
    knowledge_graph.py  - the KnowledgeGraph query engine (all business logic)
    formatting.py       - human readable rendering of query results
    server.py           - thin FastMCP wrapper exposing the engine as MCP tools

DESIGN NOTES
------------
* All match data from the different CSVs is unified into a single normalised
  "matches" table with a common schema; player data lives in a "players" table.
* Team names are normalised (state suffixes such as ``-SP`` / ``(URU)`` removed,
  accents stripped, lower-cased) so that the many naming conventions used across
  the datasets resolve to the same entity.
* The store is purely in-memory (pandas). The spec mentions Neo4j as one option,
  but an in-memory graph keeps the deliverable self-contained and lets the BDD
  test-suite run with no external services, satisfying the build/test gate.

LICENSE / DATA
--------------
Demo / non-commercial use. See README.md for dataset licenses.
================================================================================
"""

from .knowledge_graph import KnowledgeGraph, get_knowledge_graph
from .data_loader import load_all

__all__ = ["KnowledgeGraph", "get_knowledge_graph", "load_all"]

__version__ = "1.0.0"
