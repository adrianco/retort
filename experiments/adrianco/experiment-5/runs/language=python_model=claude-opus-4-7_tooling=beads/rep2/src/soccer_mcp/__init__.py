"""Brazilian Soccer MCP — package root.

Exposes a knowledge-graph-style interface over six Kaggle CSV datasets covering
the Brasileirão Serie A, Copa do Brasil, Copa Libertadores, an extended match
statistics dump, the historical Brasileirão 2003-2019 set, and a FIFA player
database. The package surface is intentionally small: load data with
``soccer_mcp.data.SoccerData.load`` then call query functions in the
sibling modules, or run ``soccer_mcp.server`` to expose those queries as MCP
tools.
"""

from soccer_mcp.data import SoccerData, normalize_team_name

__all__ = ["SoccerData", "normalize_team_name"]
