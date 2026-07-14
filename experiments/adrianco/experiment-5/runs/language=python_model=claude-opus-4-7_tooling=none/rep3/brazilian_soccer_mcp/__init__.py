"""Brazilian Soccer MCP Server package.

Provides a knowledge-graph-style query interface over six Brazilian-soccer
CSV datasets (Brasileirão, Copa do Brasil, Copa Libertadores, extended
match stats, historical Brasileirão 2003-2019, and FIFA player data).

Public surface:
    load_dataset(data_dir)              -> Dataset
    queries.*                           -> match / team / player / competition / stats helpers
    server.run()                        -> MCP stdio server entrypoint
"""

from .data_loader import Dataset, Match, Player, load_dataset, COMPETITIONS
from .team_utils import normalize_team_name, teams_match

__all__ = [
    "Dataset",
    "Match",
    "Player",
    "load_dataset",
    "COMPETITIONS",
    "normalize_team_name",
    "teams_match",
]
