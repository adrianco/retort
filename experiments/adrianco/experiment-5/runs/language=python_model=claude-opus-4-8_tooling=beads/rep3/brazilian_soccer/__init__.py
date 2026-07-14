"""
==============================================================================
Package: brazilian_soccer
==============================================================================
CONTEXT
-------
A knowledge-graph backed query engine + MCP server for Brazilian soccer data.
See README.md for the full picture. Public surface:

    * KnowledgeGraph / get_graph .. in-memory property graph over the datasets
    * queries ..................... pure query functions (match/team/player/...)
    * server ...................... FastMCP server exposing the queries as tools
==============================================================================
"""

from .knowledge_graph import KnowledgeGraph, get_graph
from .models import Match, Player

__all__ = ["KnowledgeGraph", "get_graph", "Match", "Player"]

__version__ = "1.0.0"
