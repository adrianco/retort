"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Package   : brazilian_soccer
Purpose   : Knowledge-graph style interface over Brazilian soccer datasets
            (matches, teams, players, competitions) that powers an MCP server
            answering natural-language questions about Brazilian football.

This package loads six Kaggle CSV datasets (see data/kaggle/) into an in-memory
knowledge graph and exposes query modules for matches, teams, players,
competitions and aggregate statistics. The MCP server (brazilian_soccer.server)
surfaces these capabilities as MCP tools.

Design goals
  * Pure Python standard library for the data layer (no heavy deps) so it loads
    fast and runs anywhere.
  * Robust normalization of team names, dates and encodings, because the source
    datasets are inconsistent ("Palmeiras-SP" vs "Palmeiras", DD/MM/YYYY vs ISO).
  * Deterministic, testable query functions used both by the MCP server and the
    BDD (Given/When/Then) pytest suite.
================================================================================
"""

from .knowledge_graph import KnowledgeGraph, get_default_graph

__all__ = ["KnowledgeGraph", "get_default_graph"]

__version__ = "1.0.0"
