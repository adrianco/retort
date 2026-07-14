"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Package   : brazilian_soccer.queries
Purpose   : Query functions grouped by domain. Each module takes a KnowledgeGraph
            and returns plain dicts/lists (JSON-serialisable) so the same
            functions back both the MCP server tools and the pytest suite.

Modules:
  matches       - find matches, head-to-head records
  teams         - team records and goal statistics
  players       - player search by name / nationality / club / rating
  competitions  - season standings calculated from match results
  stats         - aggregate analytics (averages, biggest wins, home/away)
================================================================================
"""

from . import competitions, matches, players, stats, teams

__all__ = ["matches", "teams", "players", "competitions", "stats"]
