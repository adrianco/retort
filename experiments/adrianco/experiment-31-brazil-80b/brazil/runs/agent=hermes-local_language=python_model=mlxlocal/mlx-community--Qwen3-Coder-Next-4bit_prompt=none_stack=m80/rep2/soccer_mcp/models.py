"""Data models for Brazilian Soccer MCP Server."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Match:
    """Represents a soccer match."""
    id: Optional[int] = None
    datetime: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    home_team_state: Optional[str] = None
    away_team_state: Optional[str] = None
    home_goal: Optional[int] = None
    away_goal: Optional[int] = None
    season: Optional[int] = None
    round: Optional[int] = None
    stage: Optional[str] = None
    competition: Optional[str] = None
    ht_result: Optional[str] = None
    at_result: Optional[str] = None
    home_corner: Optional[int] = None
    away_corner: Optional[int] = None
    home_attack: Optional[int] = None
    away_attack: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    total_corners: Optional[int] = None
    arena: Optional[str] = None
    winner: Optional[str] = None
    original_file: Optional[str] = None


@dataclass
class Team:
    """Represents a soccer team."""
    name: Optional[str] = None
    normalized_name: Optional[str] = None
    state: Optional[str] = None
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0


@dataclass
class Player:
    """Represents a soccer player."""
    id: Optional[int] = None
    name: Optional[str] = None
    age: Optional[int] = None
    nationality: Optional[str] = None
    overall: Optional[int] = None
    potential: Optional[int] = None
    club: Optional[str] = None
    position: Optional[str] = None
    jersey_number: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    preferred_foot: Optional[str] = None
    international_reputation: Optional[int] = None
    weak_foot: Optional[int] = None
    skill_moves: Optional[int] = None
    work_rate: Optional[str] = None
    body_type: Optional[str] = None
    position_full: Optional[str] = None
    # Skill ratings
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


@dataclass
class Competition:
    """Represents a soccer competition."""
    name: Optional[str] = None
    season: Optional[int] = None
    matches: int = 0
    teams: int = 0
    total_goals: int = 0
    avg_goals_per_match: float = 0.0


@dataclass
class QueryResult:
    """Result of a query."""
    success: bool = False
    error: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamStats:
    """Statistics for a team."""
    team_name: str
    season: Optional[int] = None
    competition: Optional[str] = None
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    win_rate: float = 0.0
    home_matches: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    away_matches: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
