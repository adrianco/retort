"""Brazilian Soccer knowledge graph + MCP server.

Context
-------
Implements the specification in ``TASK.md``: a knowledge graph built from six
Kaggle CSV files (five match files, one FIFA player file) plus an MCP server
that exposes natural-language-friendly query tools over that graph.

Layering (each module depends only on the ones above it)::

    normalization.py  team-name / date / number canonicalisation
    models.py         Match, Player, Team, TeamRecord, ... dataclasses
    loader.py         CSV -> Match/Player records (one reader per dataset)
    graph.py          KnowledgeGraph: nodes, edges, indexes, de-duplication
    queries.py        the analytical API (matches, teams, players, standings)
    formatting.py     human-readable rendering of query results
    server.py         MCP tool surface
    cli.py            offline demo driver (no MCP client required)
"""

from .graph import KnowledgeGraph, load_default_graph
from .models import Match, Player, Team, TeamRecord
from .queries import SoccerQueries

__all__ = [
    "KnowledgeGraph",
    "load_default_graph",
    "Match",
    "Player",
    "Team",
    "TeamRecord",
    "SoccerQueries",
]

__version__ = "1.0.0"
