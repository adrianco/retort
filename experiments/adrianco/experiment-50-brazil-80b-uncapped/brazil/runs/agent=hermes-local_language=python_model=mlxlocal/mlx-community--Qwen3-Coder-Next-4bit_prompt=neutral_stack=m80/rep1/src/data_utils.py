# Data utilities for Brazilian Soccer MCP Server
"""Data utilities for loading and normalizing Brazilian soccer data."""

import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
from pathlib import Path

from src.models import Match, Player, CompetitionStandings, TeamStats, BigWin, TeamComparison


def safe_int(value):
    """Safely convert a value to int, handling floats and invalid values."""
    if value is None:
        return 0
    if isinstance(value, float) and (value != value):  # Check for NaN
        return 0
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0


class DataUtils:
    """Utility class for data operations."""
    
    @staticmethod
    def normalize_team_name(name: str) -> str:
        """Normalize team name by removing state suffix and extra spaces."""
        if not name:
            return ""
        # Remove state suffix like -SP, -RJ, -PE, etc. (with or without space before)
        normalized = re.sub(r'\s*-\s*[A-Z]{2}$', '', str(name).strip())
        # Remove parentheses content like "(antigo ...)"
        normalized = re.sub(r'\s*\([^)]*\)\s*', ' ', normalized).strip()
        # Normalize spaces
        normalized = ' '.join(normalized.split())
        return normalized
    
    @staticmethod
    def extract_team_base(name: str) -> str:
        """Extract base team name without state suffix or extra info."""
        if not name:
            return ""
        # Remove state suffix
        base = re.sub(r'-[A-Z]{2}$', '', str(name).strip())
        # Remove club suffixes
        base = re.sub(r'\s*Esporte\s+Clube\s*', ' ', base, flags=re.IGNORECASE)
        base = re.sub(r'\s*Futebol\s+Clube\s*', ' ', base, flags=re.IGNORECASE)
        base = re.sub(r'\s*Sport\s+Club\s*', ' ', base, flags=re.IGNORECASE)
        base = re.sub(r'\s*Santa\s+Cruz\s*', ' ', base, flags=re.IGNORECASE)
        # Normalize
        base = ' '.join(base.split())
        return base.strip()
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parse date from various formats."""
        if not date_str:
            return None
        
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S.%f",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def get_competition_from_file(filename: str) -> str:
        """Determine competition name from file path."""
        filename_lower = filename.lower()
        if 'brasileirao' in filename_lower:
            return 'Brasileirão'
        elif 'libertadores' in filename_lower:
            return 'Copa Libertadores'
        elif 'cup' in filename_lower or 'copa' in filename_lower:
            return 'Copa do Brasil'
        else:
            return 'Other'
    
    @staticmethod
    def parse_date_brasileiro(date_str: str) -> Optional[datetime]:
        """Parse Brazilian date format DD/MM/YYYY."""
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
        except ValueError:
            return None


class DataLoader:
    """Data loader for Brazilian soccer datasets."""
    
    def __init__(self, data_dir: str = "data/kaggle"):
        """Initialize data loader."""
        self.data_dir = Path(data_dir)
        self.matches: List[Match] = []
        self.players: List[Player] = []
        self._load_all_data()
    
    def _load_all_data(self):
        """Load all datasets."""
        self._load_brasileirao_matches()
        self._load_copa_do_brasil_matches()
        self._load_libertadores_matches()
        self._load_extended_matches()
        self._load_historical_brasileirao()
        self._load_fifa_players()
    
    def _load_brasileirao_matches(self):
        """Load Brasileirão matches."""
        filepath = self.data_dir / "Brasileirao_Matches.csv"
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            return
        
        df = pd.read_csv(filepath)
        for _, row in df.iterrows():
            match = Match(
                datetime=DataUtils.parse_date(row.get('datetime')),
                home_team=str(row.get('home_team', '')).strip(),
                away_team=str(row.get('away_team', '')).strip(),
                home_team_state=str(row.get('home_team_state', '')).strip() if pd.notna(row.get('home_team_state')) else None,
                away_team_state=str(row.get('away_team_state', '')).strip() if pd.notna(row.get('away_team_state')) else None,
                home_goal=safe_int(row.get('home_goal')),
                away_goal=safe_int(row.get('away_goal')),
                season=safe_int(row.get('season')) if safe_int(row.get('season')) > 0 else None,
                round=safe_int(row.get('round')) if safe_int(row.get('round')) > 0 else None,
                competition='Brasileirão',
            )
            self.matches.append(match)
    
    def _load_copa_do_brasil_matches(self):
        """Load Copa do Brasil matches."""
        filepath = self.data_dir / "Brazilian_Cup_Matches.csv"
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            return
        
        df = pd.read_csv(filepath)
        for _, row in df.iterrows():
            match = Match(
                datetime=DataUtils.parse_date(row.get('datetime')),
                home_team=str(row.get('home_team', '')).strip(),
                away_team=str(row.get('away_team', '')).strip(),
                home_goal=safe_int(row.get('home_goal')),
                away_goal=safe_int(row.get('away_goal')),
                season=safe_int(row.get('season')) if safe_int(row.get('season')) > 0 else None,
                round=safe_int(row.get('round')) if safe_int(row.get('round')) > 0 else None,
                competition='Copa do Brasil',
            )
            self.matches.append(match)
    
    def _load_libertadores_matches(self):
        """Load Copa Libertadores matches."""
        filepath = self.data_dir / "Libertadores_Matches.csv"
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            return
        
        df = pd.read_csv(filepath)
        for _, row in df.iterrows():
            match = Match(
                datetime=DataUtils.parse_date(row.get('datetime')),
                home_team=str(row.get('home_team', '')).strip(),
                away_team=str(row.get('away_team', '')).strip(),
                home_goal=safe_int(row.get('home_goal')),
                away_goal=safe_int(row.get('away_goal')),
                season=safe_int(row.get('season')) if safe_int(row.get('season')) > 0 else None,
                stage=str(row.get('stage', '')).strip() if pd.notna(row.get('stage')) else None,
                competition='Copa Libertadores',
            )
            self.matches.append(match)
    
    def _load_extended_matches(self):
        """Load extended match statistics."""
        filepath = self.data_dir / "BR-Football-Dataset.csv"
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            return
        
        df = pd.read_csv(filepath)
        for _, row in df.iterrows():
            match = Match(
                datetime=DataUtils.parse_date(row.get('date')),
                home_team=str(row.get('home', '')).strip(),
                away_team=str(row.get('away', '')).strip(),
                home_goal=safe_int(row.get('home_goal')),
                away_goal=safe_int(row.get('away_goal')),
                competition=str(row.get('tournament', '')).strip(),
                home_corner=safe_int(row.get('home_corner')),
                away_corner=safe_int(row.get('away_corner')),
                home_attack=safe_int(row.get('home_attack')),
                away_attack=safe_int(row.get('away_attack')),
                home_shots=safe_int(row.get('home_shots')),
                away_shots=safe_int(row.get('away_shots')),
                time=str(row.get('time', '')).strip() if pd.notna(row.get('time')) else None,
                date=str(row.get('date', '')).strip() if pd.notna(row.get('date')) else None,
                ht_result=str(row.get('ht_result', '')).strip() if pd.notna(row.get('ht_result')) else None,
                at_result=str(row.get('at_result', '')).strip() if pd.notna(row.get('at_result')) else None,
                total_corners=safe_int(row.get('total_corners')),
            )
            self.matches.append(match)
    
    def _load_historical_brasileirao(self):
        """Load historical Brasileirão matches (2003-2019)."""
        filepath = self.data_dir / "novo_campeonato_brasileiro.csv"
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            return
        
        df = pd.read_csv(filepath)
        for _, row in df.iterrows():
            match = Match(
                datetime=DataUtils.parse_date_brasileiro(row.get('Data')),
                home_team=str(row.get('Equipe_mandante', '')).strip(),
                away_team=str(row.get('Equipe_visitante', '')).strip(),
                home_team_state=str(row.get('Mandante_UF', '')).strip() if pd.notna(row.get('Mandante_UF')) else None,
                away_team_state=str(row.get('Visitante_UF', '')).strip() if pd.notna(row.get('Visitante_UF')) else None,
                home_goal=safe_int(row.get('Gols_mandante')),
                away_goal=safe_int(row.get('Gols_visitante')),
                season=safe_int(row.get('Ano')) if safe_int(row.get('Ano')) > 0 else None,
                round=safe_int(row.get('Rodada')) if safe_int(row.get('Rodada')) > 0 else None,
                competition='Brasileirão',
                arena=str(row.get('Arena', '')).strip() if pd.notna(row.get('Arena')) else None,
                winner=str(row.get('Vencedor', '')).strip() if pd.notna(row.get('Vencedor')) else None,
            )
            self.matches.append(match)
    
    def _load_fifa_players(self):
        """Load FIFA player data."""
        filepath = self.data_dir / "fifa_data.csv"
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            return
        
        df = pd.read_csv(filepath)
        for _, row in df.iterrows():
            player = Player(
                id=safe_int(row.get('ID')),
                name=str(row.get('Name', '')).strip(),
                age=safe_int(row.get('Age')) if safe_int(row.get('Age')) > 0 else None,
                nationality=str(row.get('Nationality', '')).strip(),
                overall=safe_int(row.get('Overall')) if safe_int(row.get('Overall')) > 0 else None,
                potential=safe_int(row.get('Potential')) if safe_int(row.get('Potential')) > 0 else None,
                club=str(row.get('Club', '')).strip(),
                position=str(row.get('Position', '')).strip(),
                jersey_number=safe_int(row.get('Jersey Number')) if safe_int(row.get('Jersey Number')) > 0 else None,
                height=str(row.get('Height', '')).strip() if pd.notna(row.get('Height')) else None,
                weight=str(row.get('Weight', '')).strip() if pd.notna(row.get('Weight')) else None,
                photo_url=str(row.get('Photo', '')).strip() if pd.notna(row.get('Photo')) else None,
                flag_url=str(row.get('Flag', '')).strip() if pd.notna(row.get('Flag')) else None,
                preferred_foot=str(row.get('Preferred Foot', '')).strip() if pd.notna(row.get('Preferred Foot')) else None,
                international_reputation=safe_int(row.get('International Reputation')) if safe_int(row.get('International Reputation')) > 0 else None,
                weak_foot=safe_int(row.get('Weak Foot')) if safe_int(row.get('Weak Foot')) > 0 else None,
                skill_moves=safe_int(row.get('Skill Moves')) if safe_int(row.get('Skill Moves')) > 0 else None,
                work_rate=str(row.get('Work Rate', '')).strip() if pd.notna(row.get('Work Rate')) else None,
                body_type=str(row.get('Body Type', '')).strip() if pd.notna(row.get('Body Type')) else None,
                real_face=bool(row.get('Real Face', False)) if pd.notna(row.get('Real Face')) else None,
                position_full=str(row.get('Position', '')).strip() if pd.notna(row.get('Position')) else None,
                joined=str(row.get('Joined', '')).strip() if pd.notna(row.get('Joined')) else None,
                contract_valid_until=str(row.get('Contract Valid Until', '')).strip() if pd.notna(row.get('Contract Valid Until')) else None,
                value=str(row.get('Value', '')).strip() if pd.notna(row.get('Value')) else None,
                wage=str(row.get('Wage', '')).strip() if pd.notna(row.get('Wage')) else None,
                release_clause=str(row.get('Release Clause', '')).strip() if pd.notna(row.get('Release Clause')) else None,
                # Detailed ratings
                crossing=safe_int(row.get('Crossing')),
                finishing=safe_int(row.get('Finishing')),
                heading_accuracy=safe_int(row.get('HeadingAccuracy')),
                short_passing=safe_int(row.get('ShortPassing')),
                volleys=safe_int(row.get('Volleys')),
                dribbling=safe_int(row.get('Dribbling')),
                curve=safe_int(row.get('Curve')),
                fk_accuracy=safe_int(row.get('FKAccuracy')),
                long_passing=safe_int(row.get('LongPassing')),
                ball_control=safe_int(row.get('BallControl')),
                acceleration=safe_int(row.get('Acceleration')),
                sprint_speed=safe_int(row.get('SprintSpeed')),
                agility=safe_int(row.get('Agility')),
                reactions=safe_int(row.get('Reactions')),
                balance=safe_int(row.get('Balance')),
                shot_power=safe_int(row.get('ShotPower')),
                jumping=safe_int(row.get('Jumping')),
                stamina=safe_int(row.get('Stamina')),
                strength=safe_int(row.get('Strength')),
                long_shots=safe_int(row.get('LongShots')),
                aggression=safe_int(row.get('Aggression')),
                interceptions=safe_int(row.get('Interceptions')),
                positioning=safe_int(row.get('Positioning')),
                vision=safe_int(row.get('Vision')),
                penalties=safe_int(row.get('Penalties')),
                composure=safe_int(row.get('Composure')),
                marking=safe_int(row.get('Marking')),
                standing_tackle=safe_int(row.get('StandingTackle')),
                sliding_tackle=safe_int(row.get('SlidingTackle')),
                gk_diving=safe_int(row.get('GKDiving')),
                gk_handling=safe_int(row.get('GKHandling')),
                gk_kicking=safe_int(row.get('GKKicking')),
                gk_positioning=safe_int(row.get('GKPositioning')),
                gk_reflexes=safe_int(row.get('GKReflexes')),
            )
            self.players.append(player)


class QueryEngine:
    """Engine for executing queries on soccer data."""
    
    def __init__(self, data_dir: str = "data/kaggle"):
        """Initialize query engine."""
        self.loader = DataLoader(data_dir)
    
    def get_all_matches(self) -> List[Match]:
        """Get all matches."""
        return self.loader.matches
    
    def find_matches_by_teams(self, team1: str, team2: str = None, limit: int = 100) -> List[Match]:
        """Find matches involving one or two teams."""
        team1_normalized = DataUtils.normalize_team_name(team1)
        team2_normalized = DataUtils.normalize_team_name(team2) if team2 else None
        
        results = []
        for match in self.loader.matches:
            home_normalized = DataUtils.normalize_team_name(match.home_team)
            away_normalized = DataUtils.normalize_team_name(match.away_team)
            
            # Check if team1 is involved
            if team1_normalized.lower() in home_normalized.lower() or team1_normalized.lower() in away_normalized.lower():
                if team2:
                    # Check if team2 is also involved
                    if team2_normalized.lower() in home_normalized.lower() or team2_normalized.lower() in away_normalized.lower():
                        results.append(match)
                else:
                    results.append(match)
            
            if len(results) >= limit:
                break
        
        return results
    
    def find_matches_by_team(self, team: str, season: int = None, competition: str = None) -> List[Match]:
        """Find matches for a specific team."""
        team_normalized = DataUtils.normalize_team_name(team)
        results = []
        
        for match in self.loader.matches:
            home_normalized = DataUtils.normalize_team_name(match.home_team)
            away_normalized = DataUtils.normalize_team_name(match.away_team)
            
            if (team_normalized.lower() in home_normalized.lower() or 
                team_normalized.lower() in away_normalized.lower()):
                if season and match.season != season:
                    continue
                if competition and match.competition.lower() != competition.lower():
                    continue
                results.append(match)
        
        return results
    
    def get_team_stats(self, team: str, season: int = None, competition: str = None) -> TeamStats:
        """Calculate team statistics."""
        team_normalized = DataUtils.normalize_team_name(team)
        matches = self.find_matches_by_team(team, season, competition)
        
        stats = TeamStats(team_name=team)
        
        for match in matches:
            stats.matches += 1
            home = DataUtils.normalize_team_name(match.home_team).lower() == team_normalized.lower()
            
            if home:
                stats.home_matches += 1
                stats.home_goals_for += match.home_goal
                stats.home_goals_against += match.away_goal
                
                if match.home_goal > match.away_goal:
                    stats.wins += 1
                    stats.home_wins += 1
                elif match.home_goal == match.away_goal:
                    stats.draws += 1
                    stats.home_draws += 1
                else:
                    stats.losses += 1
                    stats.home_losses += 1
            else:
                stats.away_matches += 1
                stats.away_goals_for += match.away_goal
                stats.away_goals_against += match.home_goal
                
                if match.away_goal > match.home_goal:
                    stats.wins += 1
                    stats.away_wins += 1
                elif match.away_goal == match.home_goal:
                    stats.draws += 1
                    stats.away_draws += 1
                else:
                    stats.losses += 1
                    stats.away_losses += 1
            
            stats.goals_for += match.home_goal if home else match.away_goal
            stats.goals_against += match.away_goal if home else match.home_goal
        
        stats.points = stats.wins * 3 + stats.draws
        if stats.matches > 0:
            stats.win_rate = round((stats.wins / stats.matches) * 100, 2)
        
        return stats
    
    def get_team_comparison(self, team1: str, team2: str) -> TeamComparison:
        """Get head-to-head comparison between two teams."""
        team1_normalized = DataUtils.normalize_team_name(team1)
        team2_normalized = DataUtils.normalize_team_name(team2)
        
        matches = self.find_matches_by_teams(team1, team2)
        
        comparison = TeamComparison(
            team1=team1,
            team2=team2,
            matches=matches,
        )
        
        for match in matches:
            home_normalized = DataUtils.normalize_team_name(match.home_team).lower()
            away_normalized = DataUtils.normalize_team_name(match.away_team).lower()
            
            if team1_normalized.lower() in home_normalized:
                comparison.team1_goals_for += match.home_goal
                comparison.team1_goals_against += match.away_goal
                comparison.team2_goals_for += match.away_goal
                comparison.team2_goals_against += match.home_goal
                
                if match.home_goal > match.away_goal:
                    comparison.team1_wins += 1
                elif match.away_goal > match.home_goal:
                    comparison.team2_wins += 1
                else:
                    comparison.draws += 1
            else:
                comparison.team1_goals_for += match.away_goal
                comparison.team1_goals_against += match.home_goal
                comparison.team2_goals_for += match.home_goal
                comparison.team2_goals_against += match.away_goal
                
                if match.away_goal > match.home_goal:
                    comparison.team1_wins += 1
                elif match.home_goal > match.away_goal:
                    comparison.team2_wins += 1
                else:
                    comparison.draws += 1
        
        return comparison
    
    def get_player_by_name(self, name: str) -> List[Player]:
        """Find players by name."""
        results = []
        name_lower = name.lower()
        for player in self.loader.players:
            if name_lower in player.name.lower():
                results.append(player)
        return results
    
    def get_players_by_club(self, club: str) -> List[Player]:
        """Find players by club."""
        results = []
        club_normalized = DataUtils.normalize_team_name(club)
        for player in self.loader.players:
            if club_normalized.lower() in DataUtils.normalize_team_name(player.club).lower():
                results.append(player)
        return results
    
    def get_brazilian_players(self) -> List[Player]:
        """Get all Brazilian players."""
        return [p for p in self.loader.players if p.nationality.lower() == 'brazil']
    
    def get_top_brazilian_players(self, limit: int = 10) -> List[Player]:
        """Get top rated Brazilian players."""
        brazilian = self.get_brazilian_players()
        sorted_players = sorted(brazilian, key=lambda p: p.overall or 0, reverse=True)
        return sorted_players[:limit]
    
    def get_competition_standings(self, competition: str, season: int) -> List[CompetitionStandings]:
        """Calculate competition standings for a season."""
        matches = [m for m in self.loader.matches if m.competition.lower() == competition.lower() and m.season == season]
        
        teams: Dict[str, Dict[str, int]] = {}
        
        for match in matches:
            home = DataUtils.normalize_team_name(match.home_team)
            away = DataUtils.normalize_team_name(match.away_team)
            
            if home not in teams:
                teams[home] = {
                    'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                    'goals_for': 0, 'goals_against': 0, 'points': 0
                }
            if away not in teams:
                teams[away] = {
                    'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                    'goals_for': 0, 'goals_against': 0, 'points': 0
                }
            
            teams[home]['matches'] += 1
            teams[away]['matches'] += 1
            teams[home]['goals_for'] += match.home_goal
            teams[home]['goals_against'] += match.away_goal
            teams[away]['goals_for'] += match.away_goal
            teams[away]['goals_against'] += match.home_goal
            
            if match.home_goal > match.away_goal:
                teams[home]['wins'] += 1
                teams[home]['points'] += 3
                teams[away]['losses'] += 1
            elif match.away_goal > match.home_goal:
                teams[away]['wins'] += 1
                teams[away]['points'] += 3
                teams[home]['losses'] += 1
            else:
                teams[home]['draws'] += 1
                teams[home]['points'] += 1
                teams[away]['draws'] += 1
                teams[away]['points'] += 1
        
        standings = []
        for team, stats in teams.items():
            standings.append(CompetitionStandings(
                competition=competition,
                season=season,
                team=team,
                matches_played=stats['matches'],
                wins=stats['wins'],
                draws=stats['draws'],
                losses=stats['losses'],
                goals_for=stats['goals_for'],
                goals_against=stats['goals_against'],
                goal_difference=stats['goals_for'] - stats['goals_against'],
                points=stats['points'],
            ))
        
        # Sort by points, then goal difference
        standings.sort(key=lambda s: (-s.points, -s.goal_difference))
        
        for i, standing in enumerate(standings, 1):
            standing.position = i
        
        return standings
    
    def get_big_wins(self, competition: str = None, limit: int = 10) -> List[BigWin]:
        """Get biggest wins in matches."""
        wins = []
        
        for match in self.loader.matches:
            goal_diff = abs(match.home_goal - match.away_goal)
            if goal_diff >= 3:  # Big win threshold
                wins.append(BigWin(
                    date=match.datetime.strftime("%Y-%m-%d") if match.datetime else "",
                    home_team=match.home_team,
                    away_team=match.away_team,
                    home_goal=match.home_goal,
                    away_goal=match.away_goal,
                    competition=match.competition,
                    goal_difference=goal_diff,
                ))
        
        # Sort by goal difference
        wins.sort(key=lambda w: -w.goal_difference)
        return wins[:limit]
    
    def get_average_goals_per_match(self, competition: str = None) -> float:
        """Calculate average goals per match."""
        matches = self.loader.matches
        if competition:
            matches = [m for m in matches if m.competition.lower() == competition.lower()]
        
        if not matches:
            return 0.0
        
        total_goals = sum(m.home_goal + m.away_goal for m in matches)
        return round(total_goals / len(matches), 2)
    
    def get_home_win_rate(self) -> float:
        """Calculate home win rate."""
        if not self.loader.matches:
            return 0.0
        
        home_wins = 0
        total = 0
        
        for match in self.loader.matches:
            if match.home_goal != match.away_goal:
                total += 1
                if match.home_goal > match.away_goal:
                    home_wins += 1
        
        if total == 0:
            return 0.0
        
        return round((home_wins / total) * 100, 1)
