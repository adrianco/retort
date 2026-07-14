"""
================================================================================
 Brazilian Soccer MCP Server
================================================================================
Context
-------
This package implements a Model Context Protocol (MCP) server that exposes a
knowledge graph interface over a collection of Brazilian soccer datasets
(Brasileirao Serie A / B / C, Copa do Brasil, Copa Libertadores, a historical
Brasileirao dataset and the FIFA player database).

The package is intentionally dependency-light: the data layer is built on the
Python standard library (``csv``) so the knowledge graph and query engine can be
imported and tested without any third-party packages.  Only ``server.py``
depends on the optional ``mcp`` package, and that import is isolated so the rest
of the package remains importable in environments where ``mcp`` is absent.

Modules
-------
- ``normalization``   : team-name / date / number normalization helpers.
- ``data_loader``     : loads the six CSV datasets into normalized records.
- ``knowledge_graph`` : in-memory graph of teams, players, matches, competitions.
- ``queries``         : high-level query API used by tests and the MCP server.
- ``server``          : FastMCP server exposing the query API as MCP tools.

Author : Brazilian Soccer MCP implementation
License : Demo / non-commercial use (see dataset licenses in README.md)
================================================================================
"""

from .knowledge_graph import KnowledgeGraph
from .queries import SoccerQueryEngine

__all__ = ["KnowledgeGraph", "SoccerQueryEngine"]

__version__ = "1.0.0"
