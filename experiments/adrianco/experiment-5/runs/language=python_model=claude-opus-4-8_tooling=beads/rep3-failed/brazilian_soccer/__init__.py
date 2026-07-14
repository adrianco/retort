"""
================================================================================
Context: Brazilian Soccer MCP Server
Package:  brazilian_soccer
--------------------------------------------------------------------------------
Purpose:
    A knowledge-graph style query engine over six Brazilian-soccer datasets
    (Brasileirao, Copa do Brasil, Copa Libertadores, an extended match-stats
    set, a historical Brasileirao set and the FIFA player database) plus an
    MCP (Model Context Protocol) server that exposes the engine as tools an
    LLM can call to answer natural-language questions.

Public surface:
    - load_default_graph() -> KnowledgeGraph   (lazy, cached)
    - KnowledgeGraph                            (entity store + indexes)
    - QueryEngine                               (the 5 query categories)

Design notes:
    - Pure standard library for the data/query layer so the engine and its
      tests have zero third-party dependencies and load fast.
    - Team names are normalised (state suffixes / country tags / accents
      stripped to a canonical key) so the many naming conventions across the
      datasets resolve to a single team identity.
================================================================================
"""

from .knowledge_graph import KnowledgeGraph, load_default_graph
from .queries import QueryEngine

__all__ = ["KnowledgeGraph", "load_default_graph", "QueryEngine"]
__version__ = "1.0.0"
