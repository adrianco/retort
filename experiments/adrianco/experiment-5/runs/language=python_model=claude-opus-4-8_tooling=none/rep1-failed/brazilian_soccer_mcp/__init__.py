"""
================================================================================
Brazilian Soccer MCP Server - Package Root
================================================================================

CONTEXT
-------
This package implements a knowledge-graph style query interface over a set of
pre-downloaded Brazilian soccer datasets (see ``data/kaggle/``). It is the core
of an MCP (Model Context Protocol) server that lets an LLM answer natural
language questions about Brazilian football matches, teams, players and
competitions.

The package is deliberately split so that the *query engine* has **no external
dependencies** (pure Python standard library). This guarantees that the data
layer and its BDD test-suite run anywhere, while the optional MCP transport
layer (``server.py``) only needs the ``mcp`` SDK when actually served.

MODULES
-------
- ``normalize``        : team-name / date / accent normalisation helpers.
- ``models``           : ``Match`` and ``Player`` dataclasses.
- ``data_loader``      : reads the six CSV files into normalised records.
- ``knowledge_graph``  : the in-memory query engine (matches/teams/players/
                         competitions/statistics).
- ``formatting``       : render results into LLM-friendly text blocks.
- ``server``           : MCP tool definitions wrapping the knowledge graph.

PUBLIC API
----------
``from brazilian_soccer_mcp import KnowledgeGraph, load_knowledge_graph``
================================================================================
"""

from .knowledge_graph import KnowledgeGraph
from .data_loader import load_knowledge_graph, DEFAULT_DATA_DIR
from .models import Match, Player

__all__ = [
    "KnowledgeGraph",
    "load_knowledge_graph",
    "DEFAULT_DATA_DIR",
    "Match",
    "Player",
]

__version__ = "1.0.0"
