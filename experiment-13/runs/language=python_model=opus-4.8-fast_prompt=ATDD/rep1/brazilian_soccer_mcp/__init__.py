"""
Context
=======
Brazilian Soccer MCP Server.

A Model Context Protocol server that answers natural-language questions about
Brazilian soccer — matches, teams, players, competitions and aggregate
statistics — backed by the pre-downloaded Kaggle datasets in ``data/kaggle``.

The package is organised as:
  * ``normalize``       — team / text normalization (state & country suffixes,
                          accents, club aliases).
  * ``models``          — ``Match`` and ``Player`` domain records.
  * ``loader``          — parse the six CSV schemas into domain records.
  * ``knowledge_base``  — the query engine (find matches, team records,
                          head-to-head, player search, standings, stats).
  * ``server``          — the MCP tool surface exposed to clients.
"""

__all__ = ["__version__"]

__version__ = "1.0.0"
