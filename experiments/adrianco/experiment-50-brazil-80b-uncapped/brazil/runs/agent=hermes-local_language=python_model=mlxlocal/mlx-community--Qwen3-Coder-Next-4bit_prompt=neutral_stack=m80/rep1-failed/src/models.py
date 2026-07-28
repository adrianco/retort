# Data models for Brazilian Soccer MCP Server
"""Data models for the Brazilian Soccer MCP Server."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Match:
    """Represents a soccer match."""
    id: Optional[int] = None
    datetime: Optional[datetime] = None
    home_team: str = ""
    away_team: str = ""
    home_team_state: Optional[str] = None
    away_team_state: Optional[str] = None
    home_goal: int = 0
    away_goal: int = 0
    season: Optional[int] = None
    round: Optional[int] = None
    competition: str = ""
    stage: Optional[str] = None
    home_corner: Optional[int] = None
    away_corner: Optional[int] = None
    home_attack: Optional[int] = None
    away_attack: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    time: Optional[str] = None
    date: Optional[str] = None
    ht_result: Optional[str] = None
    at_result: Optional[str] = None
    total_corners: Optional[int] = None
    arena: Optional[str] = None
    winner: Optional[str] = None
    referee: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "datetime": self.datetime.isoformat() if self.datetime else None,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_team_state": self.home_team_state,
            "away_team_state": self.away_team_state,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "season": self.season,
            "round": self.round,
            "competition": self.competition,
            "stage": self.stage,
            "home_corner": self.home_corner,
            "away_corner": self.away_corner,
            "home_attack": self.home_attack,
            "away_attack": self.away_attack,
            "home_shots": self.home_shots,
            "away_shots": self.away_shots,
            "time": self.time,
            "date": self.date,
            "ht_result": self.ht_result,
            "at_result": self.at_result,
            "total_corners": self.total_corners,
            "arena": self.arena,
            "winner": self.winner,
            "referee": self.referee,
        }
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class TeamStats:
    """Represents team statistics."""
    team_name: str = ""
    competition: str = ""
    season: Optional[int] = None
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    win_rate: float = 0.0
    home_matches: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    home_goals_for: int = 0
    home_goals_against: int = 0
    away_matches: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
    away_goals_for: int = 0
    away_goals_against: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "team_name": self.team_name,
            "competition": self.competition,
            "season": self.season,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "points": self.points,
            "win_rate": round(self.win_rate, 2),
            "home_matches": self.home_matches,
            "home_wins": self.home_wins,
            "home_draws": self.home_draws,
            "home_losses": self.home_losses,
            "home_goals_for": self.home_goals_for,
            "home_goals_against": self.home_goals_against,
            "away_matches": self.away_matches,
            "away_wins": self.away_wins,
            "away_draws": self.away_draws,
            "away_losses": self.away_losses,
            "away_goals_for": self.away_goals_for,
            "away_goals_against": self.away_goals_against,
        }


@dataclass
class TeamComparison:
    """Represents head-to-head comparison between two teams."""
    team1: str = ""
    team2: str = ""
    matches: List[Match] = field(default_factory=list)
    team1_wins: int = 0
    team2_wins: int = 0
    draws: int = 0
    team1_goals_for: int = 0
    team1_goals_against: int = 0
    team2_goals_for: int = 0
    team2_goals_against: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "team1": self.team1,
            "team2": self.team2,
            "matches": len(self.matches),
            "team1_wins": self.team1_wins,
            "team2_wins": self.team2_wins,
            "draws": self.draws,
            "team1_goals_for": self.team1_goals_for,
            "team1_goals_against": self.team1_goals_against,
            "team2_goals_for": self.team2_goals_for,
            "team2_goals_against": self.team2_goals_against,
            "match_details": [m.to_dict() for m in self.matches],
        }


@dataclass
class Player:
    """Represents a soccer player."""
    id: Optional[int] = None
    name: str = ""
    age: Optional[int] = None
    nationality: str = ""
    overall: Optional[int] = None
    potential: Optional[int] = None
    club: str = ""
    position: str = ""
    jersey_number: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    photo_url: Optional[str] = None
    flag_url: Optional[str] = None
    preferred_foot: Optional[str] = None
    international_reputation: Optional[int] = None
    weak_foot: Optional[int] = None
    skill_moves: Optional[int] = None
    work_rate: Optional[str] = None
    body_type: Optional[str] = None
    real_face: Optional[bool] = None
    position_full: Optional[str] = None
    joined: Optional[str] = None
    contract_valid_until: Optional[str] = None
    value: Optional[str] = None
    wage: Optional[str] = None
    release_clause: Optional[str] = None

    # Detailed ratings
    crossing: Optional[int] = None
    finishing: Optional[int] = None
    heading_accuracy: Optional[int] = None
    short_passing: Optional[int] = None
    volleys: Optional[int] = None
    dribbling: Optional[int] = None
    curve: Optional[int] = None
    fk_accuracy: Optional[int] = None
    long_passing: Optional[int] = None
    ball_control: Optional[int] = None
    acceleration: Optional[int] = None
    sprint_speed: Optional[int] = None
    agility: Optional[int] = None
    reactions: Optional[int] = None
    balance: Optional[int] = None
    shot_power: Optional[int] = None
    jumping: Optional[int] = None
    stamina: Optional[int] = None
    strength: Optional[int] = None
    long_shots: Optional[int] = None
    aggression: Optional[int] = None
    interceptions: Optional[int] = None
    positioning: Optional[int] = None
    vision: Optional[int] = None
    penalties: Optional[int] = None
    composure: Optional[int] = None
    marking: Optional[int] = None
    standing_tackle: Optional[int] = None
    sliding_tackle: Optional[int] = None
    gk_diving: Optional[int] = None
    gk_handling: Optional[int] = None
    gk_kicking: Optional[int] = None
    gk_positioning: Optional[int] = None
    gk_reflexes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "photo_url": self.photo_url,
            "flag_url": self.flag_url,
            "preferred_foot": self.preferred_foot,
            "international_reputation": self.international_reputation,
            "weak_foot": self.weak_foot,
            "skill_moves": self.skill_moves,
            "work_rate": self.work_rate,
            "body_type": self.body_type,
            "real_face": self.real_face,
            "position_full": self.position_full,
            "joined": self.joined,
            "contract_valid_until": self.contract_valid_until,
            "value": self.value,
            "wage": self.wage,
            "release_clause": self.release_clause,
            "crossing": self.crossing,
            "finishing": self.finishing,
            "heading_accuracy": self.heading_accuracy,
            "short_passing": self.short_passing,
            "volleys": self.volleys,
            "dribbling": self.dribbling,
            "curve": self.curve,
            "fk_accuracy": self.fk_accuracy,
            "long_passing": self.long_passing,
            "ball_control": self.ball_control,
            "acceleration": self.acceleration,
            "sprint_speed": self.sprint_speed,
            "agility": self.agility,
            "reactions": self.reactions,
            "balance": self.balance,
            "shot_power": self.shot_power,
            "jumping": self.jumping,
            "stamina": self.stamina,
            "strength": self.strength,
            "long_shots": self.long_shots,
            "aggression": self.aggression,
            "interceptions": self.interceptions,
            "positioning": self.positioning,
            "vision": self.vision,
            "penalties": self.penalties,
            "composure": self.composure,
            "marking": self.marking,
            "standing_tackle": self.standing_tackle,
            "sliding_tackle": self.sliding_tackle,
            "gk_diving": self.gk_diving,
            "gk_handling": self.gk_handling,
            "gk_kicking": self.gk_kicking,
            "gk_positioning": self.gk_positioning,
            "gk_reflexes": self.gk_reflexes,
        }
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class CompetitionStandings:
    """Represents competition standings."""
    competition: str = ""
    season: int = 0
    position: int = 0
    team: str = ""
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    qualified_for: Optional[str] = None
    relegated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "competition": self.competition,
            "season": self.season,
            "position": self.position,
            "team": self.team,
            "matches_played": self.matches_played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "qualified_for": self.qualified_for,
            "relegated": self.relegated,
        }


@dataclass
class BigWin:
    """Represents a big win in a match."""
    date: str = ""
    home_team: str = ""
    away_team: str = ""
    home_goal: int = 0
    away_goal: int = 0
    competition: str = ""
    goal_difference: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "competition": self.competition,
            "goal_difference": self.goal_difference,
        }


@dataclass
class QueryResponse:
    """Response from a query."""
    query_type: str = ""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None
    count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_type": self.query_type,
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "count": self.count,
            "metadata": self.metadata,
        }
