"""Data loader for Brazilian Soccer MCP Server."""

import os
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from soccer_mcp.models import Match, Player, TeamStats


class DataLoader:
    """Loads and normalizes soccer data from CSV files."""
    
    def __init__(self, data_dir: str):
        """Initialize with path to data directory."""
        self.data_dir = data_dir
        self.matches: List[Match] = []
        self.players: List[Player] = []
        self.team_name_mapping: Dict[str, str] = {}
        
    def load_all_data(self) -> None:
        """Load all data files."""
        self.load_brasileirao_matches()
        self.load_copa_do_brasil_matches()
        self.load_libertadores_matches()
        self.load_extended_matches()
        self.load_historical_brasileirao()
        self.load_fifa_players()
        self.build_team_name_mapping()
        
    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team name for consistent matching."""
        if not team_name:
            return ""
        
        # Remove state suffix for normalization
        normalized = re.sub(r'-[A-Z]{2}$', '', team_name)
        # Remove parenthetical content
        normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized)
        # Normalize spaces
        normalized = ' '.join(normalized.split())
        # Convert to title case
        normalized = normalized.title()
        
        # Store mapping
        self.team_name_mapping[team_name.strip()] = normalized
        self.team_name_mapping[normalized] = normalized
        
        return normalized
    
    def build_team_name_mapping(self) -> None:
        """Build comprehensive team name mapping."""
        # Common mappings for Brazilian teams
        mappings = {
            'Flamengo': ['Flamengo', 'Flamengo-RJ', 'Flamengo RJ', 'FLAMENGO'],
            'Fluminense': ['Fluminense', 'Fluminense-RJ', 'Fluminense RJ', 'FLUMINENSE'],
            'Palmeiras': ['Palmeiras', 'Palmeiras-SP', 'Palmeiras SP', 'PALMEIRAS'],
            'São Paulo': ['São Paulo', 'Sao Paulo', 'São Paulo-SP', 'Sao Paulo SP', 'SAO PAULO'],
            'Corinthians': ['Corinthians', 'Corinthians-SP', 'Corinthians SP', 'SPORT CLUB CORINTHIANS PAULISTA', 'CORINTHIANS'],
            'Santos': ['Santos', 'Santos-SP', 'Santos SP', 'SANTOS'],
            'Grêmio': ['Grêmio', 'Gremio', 'Grêmio-RS', 'Gremio RS', 'GRÊMIO'],
            'Internacional': ['Internacional', 'Internacional-RS', 'Internacional RS', 'INTER', 'INTERNACIONAL'],
            'Botafogo': ['Botafogo', 'Botafogo-RJ', 'Botafogo RJ', 'BOTAFOGO'],
            'Vasco': ['Vasco', 'Vasco da Gama', 'VASCO DA GAMA'],
            'Palmeiras SP': ['Palmeiras-SP', 'Palmeiras SP', 'Palmeiras'],
            'São Paulo SP': ['São Paulo-SP', 'Sao Paulo SP', 'São Paulo'],
            'Corinthians SP': ['Corinthians-SP', 'Corinthians SP', 'Corinthians'],
            'Santos SP': ['Santos-SP', 'Santos SP', 'Santos'],
            'Grêmio RS': ['Grêmio-RS', 'Gremio RS', 'Grêmio RS', 'Grêmio'],
        }
        
        for canonical, variants in mappings.items():
            for variant in variants:
                self.team_name_mapping[variant] = canonical
        
        # Add normalized names from loaded matches
        for match in self.matches:
            if match.home_team:
                self.normalize_team_name(match.home_team)
            if match.away_team:
                self.normalize_team_name(match.away_team)
    
    def load_brasileirao_matches(self) -> None:
        """Load Brasileirão Serie A matches."""
        filepath = os.path.join(self.data_dir, 'Brasileirao_Matches.csv')
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = Match()
                match.competition = 'Brasileirão'
                match.datetime = row.get('datetime', '')
                match.home_team = row.get('home_team', '').strip()
                match.home_team_state = row.get('home_team_state', '').strip()
                match.away_team = row.get('away_team', '').strip()
                match.away_team_state = row.get('away_team_state', '').strip()
                
                try:
                    match.home_goal = int(row.get('home_goal', 0))
                except (ValueError, TypeError):
                    match.home_goal = 0
                    
                try:
                    match.away_goal = int(row.get('away_goal', 0))
                except (ValueError, TypeError):
                    match.away_goal = 0
                    
                try:
                    match.season = int(row.get('season', 0))
                except (ValueError, TypeError):
                    match.season = None
                    
                try:
                    match.round = int(row.get('round', 0))
                except (ValueError, TypeError):
                    match.round = None
                    
                match.original_file = 'Brasileirao_Matches.csv'
                self.matches.append(match)
    
    def load_copa_do_brasil_matches(self) -> None:
        """Load Copa do Brasil matches."""
        filepath = os.path.join(self.data_dir, 'Brazilian_Cup_Matches.csv')
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = Match()
                match.competition = 'Copa do Brasil'
                match.datetime = row.get('datetime', '')
                match.home_team = row.get('home_team', '').strip()
                match.away_team = row.get('away_team', '').strip()
                
                try:
                    match.home_goal = int(row.get('home_goal', 0))
                except (ValueError, TypeError):
                    match.home_goal = 0
                    
                try:
                    match.away_goal = int(row.get('away_goal', 0))
                except (ValueError, TypeError):
                    match.away_goal = 0
                    
                try:
                    match.season = int(row.get('season', 0))
                except (ValueError, TypeError):
                    match.season = None
                    
                # Extract round from round field
                round_val = row.get('round', '')
                if round_val:
                    try:
                        match.round = int(round_val.strip('"'))
                    except (ValueError, TypeError):
                        match.round = None
                        
                match.original_file = 'Brazilian_Cup_Matches.csv'
                self.matches.append(match)
    
    def load_libertadores_matches(self) -> None:
        """Load Copa Libertadores matches."""
        filepath = os.path.join(self.data_dir, 'Libertadores_Matches.csv')
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = Match()
                match.competition = 'Copa Libertadores'
                match.datetime = row.get('datetime', '')
                match.home_team = row.get('home_team', '').strip()
                match.away_team = row.get('away_team', '').strip()
                
                try:
                    match.home_goal = int(row.get('home_goal', 0))
                except (ValueError, TypeError):
                    match.home_goal = 0
                    
                try:
                    match.away_goal = int(row.get('away_goal', 0))
                except (ValueError, TypeError):
                    match.away_goal = 0
                    
                try:
                    match.season = int(row.get('season', 0))
                except (ValueError, TypeError):
                    match.season = None
                    
                match.stage = row.get('stage', '').strip()
                match.original_file = 'Libertadores_Matches.csv'
                self.matches.append(match)
    
    def load_extended_matches(self) -> None:
        """Load extended match statistics."""
        filepath = os.path.join(self.data_dir, 'BR-Football-Dataset.csv')
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = Match()
                match.competition = row.get('tournament', 'Unknown').strip()
                match.home_team = row.get('home', '').strip()
                match.away_team = row.get('away', '').strip()
                
                try:
                    match.home_goal = int(float(row.get('home_goal', 0)))
                except (ValueError, TypeError):
                    match.home_goal = 0
                    
                try:
                    match.away_goal = int(float(row.get('away_goal', 0)))
                except (ValueError, TypeError):
                    match.away_goal = 0
                    
                try:
                    match.home_corner = int(float(row.get('home_corner', 0)))
                except (ValueError, TypeError):
                    match.home_corner = 0
                    
                try:
                    match.away_corner = int(float(row.get('away_corner', 0)))
                except (ValueError, TypeError):
                    match.away_corner = 0
                    
                try:
                    match.home_attack = int(float(row.get('home_attack', 0)))
                except (ValueError, TypeError):
                    match.home_attack = 0
                    
                try:
                    match.away_attack = int(float(row.get('away_attack', 0)))
                except (ValueError, TypeError):
                    match.away_attack = 0
                    
                try:
                    match.home_shots = int(float(row.get('home_shots', 0)))
                except (ValueError, TypeError):
                    match.home_shots = 0
                    
                try:
                    match.away_shots = int(float(row.get('away_shots', 0)))
                except (ValueError, TypeError):
                    match.away_shots = 0
                    
                match.time = row.get('time', '').strip()
                match.date = row.get('date', '').strip()
                match.ht_result = row.get('ht_result', '').strip()
                match.at_result = row.get('at_result', '').strip()
                try:
                    match.total_corners = int(float(row.get('total_corners', 0)))
                except (ValueError, TypeError):
                    match.total_corners = 0
                    
                match.original_file = 'BR-Football-Dataset.csv'
                self.matches.append(match)
    
    def load_historical_brasileirao(self) -> None:
        """Load historical Brasileirão data (2003-2019)."""
        filepath = os.path.join(self.data_dir, 'novo_campeonato_brasileiro.csv')
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = Match()
                match.competition = 'Brasileirão'
                match.id = row.get('ID', '').strip()
                
                # Parse date in DD/MM/YYYY format
                date_str = row.get('Data', '').strip()
                if date_str and '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        match.date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                
                try:
                    match.season = int(row.get('Ano', 0))
                except (ValueError, TypeError):
                    match.season = None
                    
                try:
                    match.round = int(row.get('Rodada', 0))
                except (ValueError, TypeError):
                    match.round = None
                    
                match.home_team = row.get('Equipe_mandante', '').strip()
                match.away_team = row.get('Equipe_visitante', '').strip()
                
                try:
                    match.home_goal = int(row.get('Gols_mandante', 0))
                except (ValueError, TypeError):
                    match.home_goal = 0
                    
                try:
                    match.away_goal = int(row.get('Gols_visitante', 0))
                except (ValueError, TypeError):
                    match.away_goal = 0
                    
                match.home_team_state = row.get('Mandante_UF', '').strip()
                match.away_team_state = row.get('Visitante_UF', '').strip()
                match.winner = row.get('Vencedor', '').strip()
                match.arena = row.get('Arena', '').strip()
                match.original_file = 'novo_campeonato_brasileiro.csv'
                self.matches.append(match)
    
    def load_fifa_players(self) -> None:
        """Load FIFA player data."""
        filepath = os.path.join(self.data_dir, 'fifa_data.csv')
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                player = Player()
                
                try:
                    player.id = int(row.get('ID', 0))
                except (ValueError, TypeError):
                    player.id = None
                    
                player.name = row.get('Name', '').strip()
                try:
                    player.age = int(row.get('Age', 0))
                except (ValueError, TypeError):
                    player.age = None
                    
                player.nationality = row.get('Nationality', '').strip()
                
                try:
                    player.overall = int(row.get('Overall', 0))
                except (ValueError, TypeError):
                    player.overall = None
                    
                try:
                    player.potential = int(row.get('Potential', 0))
                except (ValueError, TypeError):
                    player.potential = None
                    
                player.club = row.get('Club', '').strip()
                player.position = row.get('Position', '').strip()
                
                try:
                    player.jersey_number = int(row.get('Jersey Number', 0))
                except (ValueError, TypeError):
                    player.jersey_number = None
                    
                player.height = row.get('Height', '').strip()
                player.weight = row.get('Weight', '').strip()
                player.preferred_foot = row.get('Preferred Foot', '').strip()
                
                try:
                    player.international_reputation = int(row.get('International Reputation', 0))
                except (ValueError, TypeError):
                    player.international_reputation = None
                    
                try:
                    player.weak_foot = int(row.get('Weak Foot', 0))
                except (ValueError, TypeError):
                    player.weak_foot = None
                    
                try:
                    player.skill_moves = int(row.get('Skill Moves', 0))
                except (ValueError, TypeError):
                    player.skill_moves = None
                    
                player.work_rate = row.get('Work Rate', '').strip()
                player.body_type = row.get('Body Type', '').strip()
                player.position_full = row.get('Position', '').strip()
                
                # Skill ratings
                try:
                    player.crossing = int(row.get('Crossing', 0))
                except (ValueError, TypeError):
                    player.crossing = None
                    
                try:
                    player.finishing = int(row.get('Finishing', 0))
                except (ValueError, TypeError):
                    player.finishing = None
                    
                try:
                    player.heading_accuracy = int(row.get('HeadingAccuracy', 0))
                except (ValueError, TypeError):
                    player.heading_accuracy = None
                    
                try:
                    player.short_passing = int(row.get('ShortPassing', 0))
                except (ValueError, TypeError):
                    player.short_passing = None
                    
                try:
                    player.volleys = int(row.get('Volleys', 0))
                except (ValueError, TypeError):
                    player.volleys = None
                    
                try:
                    player.dribbling = int(row.get('Dribbling', 0))
                except (ValueError, TypeError):
                    player.dribbling = None
                    
                try:
                    player.curve = int(row.get('Curve', 0))
                except (ValueError, TypeError):
                    player.curve = None
                    
                try:
                    player.fk_accuracy = int(row.get('FKAccuracy', 0))
                except (ValueError, TypeError):
                    player.fk_accuracy = None
                    
                try:
                    player.long_passing = int(row.get('LongPassing', 0))
                except (ValueError, TypeError):
                    player.long_passing = None
                    
                try:
                    player.ball_control = int(row.get('BallControl', 0))
                except (ValueError, TypeError):
                    player.ball_control = None
                    
                try:
                    player.acceleration = int(row.get('Acceleration', 0))
                except (ValueError, TypeError):
                    player.acceleration = None
                    
                try:
                    player.sprint_speed = int(row.get('SprintSpeed', 0))
                except (ValueError, TypeError):
                    player.sprint_speed = None
                    
                try:
                    player.agility = int(row.get('Agility', 0))
                except (ValueError, TypeError):
                    player.agility = None
                    
                try:
                    player.reactions = int(row.get('Reactions', 0))
                except (ValueError, TypeError):
                    player.reactions = None
                    
                try:
                    player.balance = int(row.get('Balance', 0))
                except (ValueError, TypeError):
                    player.balance = None
                    
                try:
                    player.shot_power = int(row.get('ShotPower', 0))
                except (ValueError, TypeError):
                    player.shot_power = None
                    
                try:
                    player.jumping = int(row.get('Jumping', 0))
                except (ValueError, TypeError):
                    player.jumping = None
                    
                try:
                    player.stamina = int(row.get('Stamina', 0))
                except (ValueError, TypeError):
                    player.stamina = None
                    
                try:
                    player.strength = int(row.get('Strength', 0))
                except (ValueError, TypeError):
                    player.strength = None
                    
                try:
                    player.long_shots = int(row.get('LongShots', 0))
                except (ValueError, TypeError):
                    player.long_shots = None
                    
                try:
                    player.aggression = int(row.get('Aggression', 0))
                except (ValueError, TypeError):
                    player.aggression = None
                    
                try:
                    player.interceptions = int(row.get('Interceptions', 0))
                except (ValueError, TypeError):
                    player.interceptions = None
                    
                try:
                    player.positioning = int(row.get('Positioning', 0))
                except (ValueError, TypeError):
                    player.positioning = None
                    
                try:
                    player.vision = int(row.get('Vision', 0))
                except (ValueError, TypeError):
                    player.vision = None
                    
                try:
                    player.penalties = int(row.get('Penalties', 0))
                except (ValueError, TypeError):
                    player.penalties = None
                    
                try:
                    player.composure = int(row.get('Composure', 0))
                except (ValueError, TypeError):
                    player.composure = None
                    
                try:
                    player.marking = int(row.get('Marking', 0))
                except (ValueError, TypeError):
                    player.marking = None
                    
                try:
                    player.standing_tackle = int(row.get('StandingTackle', 0))
                except (ValueError, TypeError):
                    player.standing_tackle = None
                    
                try:
                    player.sliding_tackle = int(row.get('SlidingTackle', 0))
                except (ValueError, TypeError):
                    player.sliding_tackle = None
                    
                try:
                    player.gk_diving = int(row.get('GKDiving', 0))
                except (ValueError, TypeError):
                    player.gk_diving = None
                    
                try:
                    player.gk_handling = int(row.get('GKHandling', 0))
                except (ValueError, TypeError):
                    player.gk_handling = None
                    
                try:
                    player.gk_kicking = int(row.get('GKKicking', 0))
                except (ValueError, TypeError):
                    player.gk_kicking = None
                    
                try:
                    player.gk_positioning = int(row.get('GKPositioning', 0))
                except (ValueError, TypeError):
                    player.gk_positioning = None
                    
                try:
                    player.gk_reflexes = int(row.get('GKReflexes', 0))
                except (ValueError, TypeError):
                    player.gk_reflexes = None
                    
                self.players.append(player)
    
    def get_matches_by_competition(self, competition: str) -> List[Match]:
        """Get matches by competition name."""
        competition_lower = competition.lower()
        return [m for m in self.matches if m.competition and m.competition.lower() == competition_lower]
    
    def get_matches_by_team(self, team_name: str) -> List[Match]:
        """Get matches involving a team."""
        normalized_name = self.normalize_team_name(team_name)
        matches = []
        for m in self.matches:
            home_normalized = self.normalize_team_name(m.home_team) if m.home_team else ''
            away_normalized = self.normalize_team_name(m.away_team) if m.away_team else ''
            if normalized_name.lower() in home_normalized.lower() or normalized_name.lower() in away_normalized.lower():
                matches.append(m)
        return matches
    
    def get_matches_by_teams(self, team1: str, team2: str) -> List[Match]:
        """Get matches between two teams."""
        normalized1 = self.normalize_team_name(team1)
        normalized2 = self.normalize_team_name(team2)
        matches = []
        for m in self.matches:
            home_normalized = self.normalize_team_name(m.home_team) if m.home_team else ''
            away_normalized = self.normalize_team_name(m.away_team) if m.away_team else ''
            if (normalized1.lower() in home_normalized.lower() and normalized2.lower() in away_normalized.lower()) or \
               (normalized2.lower() in home_normalized.lower() and normalized1.lower() in away_normalized.lower()):
                matches.append(m)
        return matches
    
    def get_matches_by_season(self, season: int) -> List[Match]:
        """Get matches from a specific season."""
        return [m for m in self.matches if m.season and m.season == season]
    
    def get_matches_by_date_range(self, start_date: str, end_date: str) -> List[Match]:
        """Get matches within a date range."""
        matches = []
        for m in self.matches:
            if m.datetime:
                try:
                    match_date = m.datetime.split()[0]
                    if start_date <= match_date <= end_date:
                        matches.append(m)
                except:
                    pass
            elif m.date:
                if start_date <= m.date <= end_date:
                    matches.append(m)
        return matches
    
    def get_player_by_name(self, name: str) -> Optional[Player]:
        """Find a player by name."""
        name_lower = name.lower()
        for p in self.players:
            if p.name and name_lower in p.name.lower():
                return p
        return None
    
    def get_players_by_club(self, club: str) -> List[Player]:
        """Get players by club."""
        club_lower = club.lower()
        return [p for p in self.players if p.club and club_lower in p.club.lower()]
    
    def get_brazilian_players(self) -> List[Player]:
        """Get all Brazilian players."""
        return [p for p in self.players if p.nationality and 'Brazil' in p.nationality]
    
    def get_top_players(self, limit: int = 10) -> List[Player]:
        """Get top rated players."""
        sorted_players = sorted(self.players, key=lambda p: p.overall or 0, reverse=True)
        return sorted_players[:limit]
    
    def get_team_stats(self, team_name: str, season: Optional[int] = None, competition: Optional[str] = None) -> TeamStats:
        """Calculate team statistics."""
        stats = TeamStats(team_name=team_name)
        normalized_name = self.normalize_team_name(team_name)
        
        matches = self.get_matches_by_team(team_name)
        
        if season:
            matches = [m for m in matches if m.season == season]
        if competition:
            matches = [m for m in matches if m.competition and m.competition.lower() == competition.lower()]
        
        stats.matches_played = len(matches)
        
        for m in matches:
            is_home = normalized_name.lower() in self.normalize_team_name(m.home_team).lower()
            
            if is_home:
                stats.home_matches += 1
                if m.home_goal and m.away_goal:
                    if m.home_goal > m.away_goal:
                        stats.home_wins += 1
                        stats.wins += 1
                    elif m.home_goal == m.away_goal:
                        stats.home_draws += 1
                        stats.draws += 1
                    else:
                        stats.home_losses += 1
                        stats.losses += 1
                if m.home_goal:
                    stats.goals_for += m.home_goal
                if m.away_goal:
                    stats.goals_against += m.away_goal
            else:
                stats.away_matches += 1
                if m.home_goal and m.away_goal:
                    if m.away_goal > m.home_goal:
                        stats.away_wins += 1
                        stats.wins += 1
                    elif m.away_goal == m.home_goal:
                        stats.away_draws += 1
                        stats.draws += 1
                    else:
                        stats.away_losses += 1
                        stats.losses += 1
                if m.away_goal:
                    stats.goals_for += m.away_goal
                if m.home_goal:
                    stats.goals_against += m.home_goal
        
        stats.goal_difference = stats.goals_for - stats.goals_against
        stats.points = stats.wins * 3 + stats.draws
        
        if stats.matches_played > 0:
            stats.win_rate = round((stats.wins / stats.matches_played) * 100, 1)
        
        return stats
    
    def get_head_to_head(self, team1: str, team2: str) -> Dict[str, Any]:
        """Get head-to-head record between two teams."""
        matches = self.get_matches_by_teams(team1, team2)
        
        team1_normalized = self.normalize_team_name(team1)
        team2_normalized = self.normalize_team_name(team2)
        
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
                
            if team1_normalized.lower() in self.normalize_team_name(m.home_team).lower():
                if m.home_goal > m.away_goal:
                    team1_wins += 1
                elif m.home_goal < m.away_goal:
                    team2_wins += 1
                else:
                    draws += 1
            else:
                if m.away_goal > m.home_goal:
                    team1_wins += 1
                elif m.away_goal < m.home_goal:
                    team2_wins += 1
                else:
                    draws += 1
        
        return {
            'team1': team1,
            'team2': team2,
            'matches': len(matches),
            f'{team1}_wins': team1_wins,
            f'{team2}_wins': team2_wins,
            'draws': draws
        }
