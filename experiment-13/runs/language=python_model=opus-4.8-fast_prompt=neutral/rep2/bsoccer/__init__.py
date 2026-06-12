"""
Context
=======
Package: bsoccer
Purpose: A Brazilian Soccer MCP (Model Context Protocol) server and query
         library built over the provided Kaggle datasets (matches for the
         Brasileirão, Copa do Brasil and Copa Libertadores, plus the FIFA
         player database).

Layout
------
  normalize.py  Team-name normalization (accents, state suffixes, aliases).
  data.py       Loads the six CSVs into unified, normalized DataFrames.
  queries.py    QueryEngine: matches, teams, players, competitions, stats.
  format.py     Renders query results as human-readable text.
  server.py     FastMCP server exposing the engine as MCP tools.
  cli.py        Thin command-line front end for manual exploration/demo.

Quick start
-----------
  from bsoccer import QueryEngine, get_data
  eng = QueryEngine(get_data())
  eng.head_to_head("Flamengo", "Fluminense")
"""

from .data import SoccerData, get_data
from .queries import QueryEngine

__all__ = ["SoccerData", "get_data", "QueryEngine"]
__version__ = "1.0.0"
