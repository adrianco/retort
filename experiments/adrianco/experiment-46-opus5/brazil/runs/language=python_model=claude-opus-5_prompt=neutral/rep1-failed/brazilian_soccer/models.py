"""Domain objects shared by the loader, the knowledge graph and the query layer.

Everything downstream works with these objects rather than with pandas frames so
that queries stay readable and the graph can hold plain Python nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

HOME = "home"
AWAY = "away"
DRAW = "draw"


@dataclass(frozen=True)
class Team:
    """A club, identified by a canonical id shared across every dataset."""

    team_id: str
    name: str
    state: str | None = None
    country: str = "Brazil"
    aliases: frozenset[str] = frozenset()

    @property
    def display_name(self) -> str:
        if self.state and self.country == "Brazil":
            return f"{self.name} ({self.state})"
        if self.country != "Brazil":
            return f"{self.name} [{self.country}]"
        return self.name


@dataclass
class Match:
    """One match, merged from every source file that describes it."""

    match_id: str
    competition: str
    season: int | None
    date: date | None
    home_team: str                 # canonical team id
    away_team: str                 # canonical team id
    home_goals: int | None
    away_goals: int | None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    kickoff: str | None = None
    sources: tuple[str, ...] = ()
    stats: dict[str, float] = field(default_factory=dict)

    @property
    def played(self) -> bool:
        """True when the match has a recorded score."""
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> int:
        return (self.home_goals or 0) + (self.away_goals or 0)

    @property
    def goal_difference(self) -> int:
        """Absolute margin of victory (0 for draws / unplayed)."""
        if not self.played:
            return 0
        return abs(self.home_goals - self.away_goals)

    @property
    def result(self) -> str | None:
        """``home``, ``away`` or ``draw`` — ``None`` when not played."""
        if not self.played:
            return None
        if self.home_goals > self.away_goals:
            return HOME
        if self.away_goals > self.home_goals:
            return AWAY
        return DRAW

    @property
    def winner(self) -> str | None:
        """Canonical team id of the winner, ``None`` for draws/unplayed."""
        result = self.result
        if result == HOME:
            return self.home_team
        if result == AWAY:
            return self.away_team
        return None

    def involves(self, team_id: str) -> bool:
        return team_id in (self.home_team, self.away_team)

    def opponent_of(self, team_id: str) -> str:
        return self.away_team if team_id == self.home_team else self.home_team

    def goals_for(self, team_id: str) -> int | None:
        if not self.played:
            return None
        return self.home_goals if team_id == self.home_team else self.away_goals

    def goals_against(self, team_id: str) -> int | None:
        if not self.played:
            return None
        return self.away_goals if team_id == self.home_team else self.home_goals


@dataclass(frozen=True)
class Player:
    """A player from the FIFA dataset."""

    player_id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str | None            # club name as written in the FIFA data
    club_team_id: str | None    # canonical team id when the club is known
    position: str | None
    jersey_number: int | None
    height: str | None
    weight: str | None
    value: str | None
    wage: str | None
    preferred_foot: str | None
    skills: dict[str, int] = field(default_factory=dict)


@dataclass
class TeamRecord:
    """Aggregated win/draw/loss record for a team over a set of matches."""

    team_id: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add(self, match: Match) -> None:
        """Fold one played match into the record."""
        if not match.played:
            return
        self.matches += 1
        self.goals_for += match.goals_for(self.team_id)
        self.goals_against += match.goals_against(self.team_id)
        winner = match.winner
        if winner is None:
            self.draws += 1
        elif winner == self.team_id:
            self.wins += 1
        else:
            self.losses += 1

    @property
    def points(self) -> int:
        """Three points for a win, one for a draw."""
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return self.wins / self.matches if self.matches else 0.0

    @property
    def points_per_match(self) -> float:
        return self.points / self.matches if self.matches else 0.0

    def as_dict(self, name: str | None = None) -> dict:
        return {
            "team_id": self.team_id,
            "team": name or self.team_id,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": round(self.win_rate * 100, 1),
        }
