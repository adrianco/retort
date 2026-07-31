"""Brazilian soccer knowledge graph and MCP server.

Context
-------
Package layout, in dependency order:

``names``       club/competition entity resolution (accents, state suffixes, aliases)
``models``      :class:`Match`, :class:`Player`, :class:`TeamRecord` dataclasses
``loaders``     CSV parsing plus cross-source de-duplication of fixtures
``graph``       the in-memory knowledge graph (nodes, relations, indexes)
``queries``     analytics: match search, head-to-head, tables, rankings, players
``formatting``  rendering of query results as text
``server``      the MCP tool surface
``cli``         a terminal client for the same tools (demo / manual checks)

Typical use::

    from brazilian_soccer import load_graph, queries, formatting

    graph = load_graph()
    result = queries.standings(graph, "brasileirao", 2019)
    print(formatting.format_standings(result))
"""

from __future__ import annotations

from .graph import KnowledgeGraph, load_graph
from .models import Match, Player, TeamRecord

__all__ = ["KnowledgeGraph", "load_graph", "Match", "Player", "TeamRecord", "__version__"]

__version__ = "1.0.0"
