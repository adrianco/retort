# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : soccer_mcp package root
# Purpose : A Model Context Protocol (MCP) server that exposes a knowledge graph
#           interface over six Brazilian-soccer datasets (matches + FIFA players).
#           It answers natural-language style queries about matches, teams,
#           players, competitions and aggregate statistics.
# Design  : The data + query layers are completely independent of the MCP
#           transport so they can be unit-tested without a running server and
#           without any external database. The server module (server.py) is a
#           thin adapter that wires the query layer into MCP tools.
# Layers  :
#   models.py          - typed records (Match, Player) used across the package
#   normalize.py       - team-name / date / accent normalisation helpers
#   data_loader.py     - parses the six CSV files into Match / Player records
#   knowledge_graph.py - in-memory store + query API over the records
#   server.py          - MCP server exposing the query API as tools
# Data    : data/kaggle/*.csv (see README.md for sources and licenses)
# =============================================================================

from .knowledge_graph import KnowledgeGraph
from .models import Match, Player

__all__ = ["KnowledgeGraph", "Match", "Player"]
__version__ = "1.0.0"
