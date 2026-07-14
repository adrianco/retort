"""In-memory knowledge graph over the normalized match and player data.

Nodes are teams, players, competitions and seasons; edges are implicit in
the indices below (team -> matches it played, team -> competitions it
appeared in, club -> players on its roster). Numeric aggregation (sums,
averages, sorting) is left to pandas in `queries.py`; this module's job is
fast relationship lookups: "what matches did this team play", "what
competitions has this team appeared in", "who plays for this club".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .normalize import normalize_key


@dataclass
class TeamNode:
    key: str
    display: str
    states: set[str] = field(default_factory=set)
    competitions: set[str] = field(default_factory=set)
    seasons: set[int] = field(default_factory=set)
    match_indices: list[int] = field(default_factory=list)


class TeamNotFoundError(KeyError):
    """Raised when a team name doesn't resolve to any known team node."""


class KnowledgeGraph:
    """Graph of teams, matches, competitions, and players built from the
    unified `matches` and `players` DataFrames produced by data_loader.
    """

    def __init__(self, matches: pd.DataFrame, players: pd.DataFrame):
        self.matches = matches.reset_index(drop=True)
        self.players = players.reset_index(drop=True)
        self._teams: dict[str, TeamNode] = {}
        self._club_player_indices: dict[str, list[int]] = {}
        self._build_team_index()
        self._build_player_index()

    def _build_team_index(self) -> None:
        home_groups = self.matches.groupby("home_team_key").indices
        away_groups = self.matches.groupby("away_team_key").indices
        all_keys = (set(home_groups) | set(away_groups)) - {""}

        for key in all_keys:
            home_idx = home_groups.get(key, [])
            away_idx = away_groups.get(key, [])
            all_idx = sorted(set(home_idx) | set(away_idx))
            rows = self.matches.iloc[all_idx]

            display = None
            if len(home_idx):
                display = self.matches["home_team"].iat[home_idx[0]]
            elif len(away_idx):
                display = self.matches["away_team"].iat[away_idx[0]]

            states = set(rows.loc[rows["home_team_key"] == key, "home_state"].dropna())
            states |= set(rows.loc[rows["away_team_key"] == key, "away_state"].dropna())

            self._teams[key] = TeamNode(
                key=key,
                display=display or key.title(),
                states=states,
                competitions=set(rows["competition"].dropna().unique()),
                seasons=set(int(s) for s in rows["season"].dropna().unique()),
                match_indices=all_idx,
            )

    def _build_player_index(self) -> None:
        groups = self.players.groupby("club_key").indices
        self._club_player_indices = {key: list(idx) for key, idx in groups.items() if key}

    # -- Team lookups -----------------------------------------------------

    def resolve_team(self, name: str) -> TeamNode:
        """Look up a team by any spelling; raises TeamNotFoundError if the
        normalized key doesn't match a team that appears in the match data.
        """
        key = normalize_key(name)
        node = self._teams.get(key)
        if node is None:
            raise TeamNotFoundError(f"No team found matching {name!r}")
        return node

    def find_team_keys(self, name: str) -> list[str]:
        """Return all team keys whose display name or key contains `name`
        (case/accent-insensitive substring match), for fuzzy lookups.
        """
        needle = normalize_key(name)
        if not needle:
            return []
        return [key for key in self._teams if needle in key]

    def team_matches(self, name: str) -> pd.DataFrame:
        node = self.resolve_team(name)
        return self.matches.iloc[node.match_indices]

    def team_competitions(self, name: str) -> set[str]:
        return self.resolve_team(name).competitions

    def all_team_keys(self) -> list[str]:
        return list(self._teams.keys())

    def team_display(self, key: str) -> str:
        node = self._teams.get(key)
        return node.display if node else key.title()

    # -- Player lookups -----------------------------------------------------

    def club_players(self, club_name: str) -> pd.DataFrame:
        key = normalize_key(club_name)
        indices = self._club_player_indices.get(key, [])
        return self.players.iloc[indices]
