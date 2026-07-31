"""
Context
=======
Package: brazilian_soccer

An MCP (Model Context Protocol) server that exposes a knowledge graph built from
six public Brazilian-soccer datasets (see README.md / TASK.md) so that an LLM can
answer natural-language questions about matches, teams, players, competitions and
aggregate statistics.

Layering (each module has its own context block):
  names.py      -> team-name normalisation / alias resolution
  models.py     -> immutable Match and Player records
  loader.py     -> CSV readers, one per dataset, plus cross-source de-duplication
  graph.py      -> the KnowledgeGraph: indexes + all query/aggregation logic
  formatters.py -> human-readable renderings used by the MCP tool responses
  server.py     -> MCP tool definitions and stdio entry point

Everything below graph.py is pure-stdlib and synchronous, which keeps simple
lookups well under the 2s budget and aggregates under 5s after a one-off load.
"""

from .graph import KnowledgeGraph, load_default_graph
from .models import Match, Player

__all__ = ["KnowledgeGraph", "load_default_graph", "Match", "Player"]
__version__ = "1.0.0"
