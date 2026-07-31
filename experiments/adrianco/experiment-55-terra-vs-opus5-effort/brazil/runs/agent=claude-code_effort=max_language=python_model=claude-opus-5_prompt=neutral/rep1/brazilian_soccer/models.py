"""Core entities of the Brazilian soccer knowledge graph.

Context
-------
Everything the server answers with is built from two record types:
:class:`Match` (from the five match CSVs, after cross-source de-duplication)
and :class:`Player` (from ``fifa_data.csv``).  Both are plain dataclasses with
derived helpers -- ``winner_id``, ``result``, ``goal_difference`` -- so the
query layer never re-implements "who won this match".

:class:`Match` keeps a ``sources`` tuple because the same real world fixture is
frequently present in two or three CSVs (Brasileirão 2014-2019 appears in
``Brasileirao_Matches.csv``, ``novo_campeonato_brasileiro.csv`` *and*
``BR-Football-Dataset.csv``); the merged record remembers where its fields came
from and which extras (corners, shots, attacks) were available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

__all__ = ["Match", "Player", "TeamRecord"]


HOME_WIN = "home"
AWAY_WIN = "away"
DRAW = "draw"


@dataclass(slots=True)
class Match:
    """A single fixture, possibly merged from several source files."""

    match_id: str
    competition_id: str
    competition: str
    season: int | None
    date: date | None = None
    kickoff: str | None = None
    round: int | None = None
    stage: str | None = None
    home_team: str = ""
    away_team: str = ""
    home_team_name: str = ""
    away_team_name: str = ""
    # Spelling as it appeared in the source file, kept so the graph can show
    # which variants were unified ("Sport-PE" and "Sport Club do Recife").
    home_team_raw: str = ""
    away_team_raw: str = ""
    home_goals: int | None = None
    away_goals: int | None = None
    venue: str | None = None
    sources: tuple[str, ...] = ()
    stats: dict[str, float] = field(default_factory=dict)

    # -- derived ---------------------------------------------------------
    @property
    def played(self) -> bool:
        """True when both scores are known (some rows are ``NA``/``-``)."""
        return self.home_goals is not None and self.away_goals is not None

    @property
    def result(self) -> str | None:
        if not self.played:
            return None
        if self.home_goals > self.away_goals:  # type: ignore[operator]
            return HOME_WIN
        if self.home_goals < self.away_goals:  # type: ignore[operator]
            return AWAY_WIN
        return DRAW

    @property
    def winner_id(self) -> str | None:
        result = self.result
        if result == HOME_WIN:
            return self.home_team
        if result == AWAY_WIN:
            return self.away_team
        return None

    @property
    def loser_id(self) -> str | None:
        result = self.result
        if result == HOME_WIN:
            return self.away_team
        if result == AWAY_WIN:
            return self.home_team
        return None

    @property
    def total_goals(self) -> int | None:
        if not self.played:
            return None
        return self.home_goals + self.away_goals  # type: ignore[operator]

    @property
    def goal_difference(self) -> int | None:
        """Absolute winning margin (0 for a draw)."""
        if not self.played:
            return None
        return abs(self.home_goals - self.away_goals)  # type: ignore[operator]

    @property
    def teams(self) -> tuple[str, str]:
        return (self.home_team, self.away_team)

    def involves(self, team_id: str) -> bool:
        return team_id in (self.home_team, self.away_team)

    def opponent_of(self, team_id: str) -> str | None:
        if team_id == self.home_team:
            return self.away_team
        if team_id == self.away_team:
            return self.home_team
        return None

    def is_home(self, team_id: str) -> bool:
        return team_id == self.home_team

    def goals_for(self, team_id: str) -> int | None:
        if not self.played:
            return None
        return self.home_goals if team_id == self.home_team else self.away_goals

    def goals_against(self, team_id: str) -> int | None:
        if not self.played:
            return None
        return self.away_goals if team_id == self.home_team else self.home_goals

    def outcome_for(self, team_id: str) -> str | None:
        """``"W"``, ``"D"``, ``"L"`` from *team_id*'s point of view."""
        if not self.played:
            return None
        winner = self.winner_id
        if winner is None:
            return "D"
        return "W" if winner == team_id else "L"

    @property
    def label(self) -> str:
        """``"Flamengo 2-1 Fluminense"`` (or ``"vs"`` when not played)."""
        if self.played:
            return (
                f"{self.home_team_name} {self.home_goals}-{self.away_goals} "
                f"{self.away_team_name}"
            )
        return f"{self.home_team_name} vs {self.away_team_name}"

    @property
    def stage_label(self) -> str | None:
        """Human readable round/stage, e.g. ``"Round 22"`` or ``"Final"``."""
        if self.stage:
            return self.stage
        if self.round is not None:
            return f"Round {self.round}"
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "competition": self.competition,
            "season": self.season,
            "date": self.date.isoformat() if self.date else None,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team_name,
            "away_team": self.away_team_name,
            "home_team_id": self.home_team,
            "away_team_id": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "venue": self.venue,
            "sources": list(self.sources),
            "stats": dict(self.stats),
        }


@dataclass(slots=True)
class Player:
    """A FIFA player record (``fifa_data.csv``)."""

    player_id: int
    name: str
    age: int | None = None
    nationality: str = ""
    overall: int | None = None
    potential: int | None = None
    club: str = ""
    club_team_id: str | None = None  # link into the match knowledge graph
    position: str = ""
    jersey_number: int | None = None
    preferred_foot: str = ""
    height: str = ""
    weight: str = ""
    value_eur: float | None = None
    wage_eur: float | None = None
    release_clause_eur: float | None = None
    value_label: str = ""
    wage_label: str = ""
    joined: str = ""
    contract_valid_until: str = ""
    international_reputation: int | None = None
    work_rate: str = ""
    body_type: str = ""
    skills: dict[str, int] = field(default_factory=dict)
    search_name: str = ""

    @property
    def is_goalkeeper(self) -> bool:
        return self.position == "GK"

    def top_skills(self, count: int = 5) -> list[tuple[str, int]]:
        items = sorted(self.skills.items(), key=lambda kv: (-kv[1], kv[0]))
        return items[:count]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "club_team_id": self.club_team_id,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "value": self.value_label,
            "wage": self.wage_label,
            "height": self.height,
            "weight": self.weight,
            "preferred_foot": self.preferred_foot,
        }


@dataclass(slots=True)
class TeamRecord:
    """Aggregated W/D/L record used by team stats and league tables."""

    team_id: str
    team_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add(self, scored: int, conceded: int) -> None:
        self.played += 1
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.wins += 1
        elif scored < conceded:
            self.losses += 1
        else:
            self.draws += 1

    @property
    def points(self) -> int:
        """Three points for a win, one for a draw."""
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return (self.wins / self.played * 100) if self.played else 0.0

    @property
    def points_per_game(self) -> float:
        return (self.points / self.played) if self.played else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "team": self.team_name,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": round(self.win_rate, 1),
        }
