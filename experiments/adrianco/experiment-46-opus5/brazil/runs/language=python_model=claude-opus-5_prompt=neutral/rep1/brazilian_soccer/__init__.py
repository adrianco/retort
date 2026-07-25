"""Brazilian Soccer knowledge graph and MCP server.

Loads the Kaggle datasets in ``data/kaggle`` into an in-memory knowledge graph
(teams, players, matches, competitions) and exposes query tools over MCP.
"""

from .models import Match, Player, Team
from .graph import KnowledgeGraph, load_graph

__all__ = ["Match", "Player", "Team", "KnowledgeGraph", "load_graph"]
__version__ = "1.0.0"
