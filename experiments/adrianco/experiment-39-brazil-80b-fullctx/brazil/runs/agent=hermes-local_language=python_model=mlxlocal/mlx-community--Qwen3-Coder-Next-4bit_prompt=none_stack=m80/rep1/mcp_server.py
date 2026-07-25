#!/usr/bin/env python3
"""
Brazilian Soccer MCP Server
A Model Context Protocol server for Brazilian soccer data queries.
"""

import os
import re
import csv
import json
from datetime import datetime
from typing import Optional
from collections import defaultdict

# Data directory path
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

class BrazilianSoccerMCP:
    """MCP Server for Brazilian Soccer Data"""
    
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.matches = []
        self.players = []
        self._load_data()
    
    def _normalize_team_name(self, team: str) -> str:
        """Normalize team names for consistent matching."""
        if not team:
            return ""
        # Remove state suffix like -SP, -RJ, -PE
        normalized = re.sub(r'-[A-Z]{2}$', '', team)
        # Remove parentheses with annotations
        normalized = re.sub(r'\s*\(.*?\)\s*$', '', normalized)
        # Remove leading/trailing whitespace
        normalized = normalized.strip()
        return normalized
    
    def _safe_int(self, value, default=0):
        """Safely convert value to int, handling NA and empty strings."""
        if value is None or value == '' or str(value).upper() == 'NA':
            return default
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return default
    
    def _load_brasiileirao_matches(self):
        """Load Brasileirão Serie A matches."""
        filepath = os.path.join(self.data_dir, "Brasileirao_Matches.csv")
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = {
                    'competition': 'Brasileirão',
                    'datetime': row.get('datetime', ''),
                    'home_team': row.get('home_team', ''),
                    'home_team_normalized': self._normalize_team_name(row.get('home_team', '')),
                    'home_team_state': row.get('home_team_state', ''),
                    'away_team': row.get('away_team', ''),
                    'away_team_normalized': self._normalize_team_name(row.get('away_team', '')),
                    'away_team_state': row.get('away_team_state', ''),
                    'home_goal': self._safe_int(row.get('home_goal', 0)),
                    'away_goal': self._safe_int(row.get('away_goal', 0)),
                    'season': self._safe_int(row.get('season', 0)),
                    'round': self._safe_int(row.get('round', 0))
                }
                self.matches.append(match)
    
    def _load_copa_do_brasil_matches(self):
        """Load Copa do Brasil matches."""
        filepath = os.path.join(self.data_dir, "Brazilian_Cup_Matches.csv")
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = {
                    'competition': 'Copa do Brasil',
                    'datetime': row.get('datetime', ''),
                    'home_team': row.get('home_team', ''),
                    'home_team_normalized': self._normalize_team_name(row.get('home_team', '')),
                    'away_team': row.get('away_team', ''),
                    'away_team_normalized': self._normalize_team_name(row.get('away_team', '')),
                    'home_goal': self._safe_int(row.get('home_goal', 0)),
                    'away_goal': self._safe_int(row.get('away_goal', 0)),
                    'season': self._safe_int(row.get('season', 0)),
                    'round': row.get('round', '')
                }
                self.matches.append(match)
    
    def _load_libertadores_matches(self):
        """Load Copa Libertadores matches."""
        filepath = os.path.join(self.data_dir, "Libertadores_Matches.csv")
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = {
                    'competition': 'Copa Libertadores',
                    'datetime': row.get('datetime', ''),
                    'home_team': row.get('home_team', ''),
                    'home_team_normalized': self._normalize_team_name(row.get('home_team', '')),
                    'away_team': row.get('away_team', ''),
                    'away_team_normalized': self._normalize_team_name(row.get('away_team', '')),
                    'home_goal': self._safe_int(row.get('home_goal', 0)),
                    'away_goal': self._safe_int(row.get('away_goal', 0)),
                    'season': self._safe_int(row.get('season', 0)),
                    'round': row.get('stage', '') or row.get('round', '')
                }
                self.matches.append(match)
    
    def _load_extended_matches(self):
        """Load extended match statistics."""
        filepath = os.path.join(self.data_dir, "BR-Football-Dataset.csv")
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match = {
                    'competition': row.get('tournament', 'Unknown'),
                    'datetime': row.get('date', ''),
                    'time': row.get('time', ''),
                    'home_team': row.get('home', ''),
                    'home_team_normalized': self._normalize_team_name(row.get('home', '')),
                    'away_team': row.get('away', ''),
                    'away_team_normalized': self._normalize_team_name(row.get('away', '')),
                    'home_goal': self._safe_int(row.get('home_goal', 0)),
                    'away_goal': self._safe_int(row.get('away_goal', 0)),
                    'season': self._extract_year(row.get('date', '')),
                    'round': row.get('tournament', ''),
                    'home_corner': self._safe_int(row.get('home_corner', 0)),
                    'away_corner': self._safe_int(row.get('away_corner', 0)),
                    'home_attack': self._safe_int(row.get('home_attack', 0)),
                    'away_attack': self._safe_int(row.get('away_attack', 0)),
                    'home_shots': self._safe_int(row.get('home_shots', 0)),
                    'away_shots': self._safe_int(row.get('away_shots', 0)),
                    'ht_result': row.get('ht_result', ''),
                    'at_result': row.get('at_result', ''),
                    'total_corners': self._safe_int(row.get('total_corners', 0))
                }
                self.matches.append(match)
    
    def _load_historical_brasileirao(self):
        """Load historical Brasileirão data (2003-2019)."""
        filepath = os.path.join(self.data_dir, "novo_campeonato_brasileiro.csv")
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse Brazilian date format: DD/MM/YYYY
                date_str = row.get('Data', '')
                datetime_str = self._parse_brazilian_date(date_str)
                match = {
                    'competition': 'Brasileirão',
                    'datetime': datetime_str,
                    'home_team': row.get('Equipe_mandante', ''),
                    'home_team_normalized': self._normalize_team_name(row.get('Equipe_mandante', '')),
                    'away_team': row.get('Equipe_visitante', ''),
                    'away_team_normalized': self._normalize_team_name(row.get('Equipe_visitante', '')),
                    'home_goal': self._safe_int(row.get('Gols_mandante', 0)),
                    'away_goal': self._safe_int(row.get('Gols_visitante', 0)),
                    'season': self._safe_int(row.get('Ano', 0)),
                    'round': self._safe_int(row.get('Rodada', 0)),
                    'home_team_state': row.get('Mandante_UF', ''),
                    'away_team_state': row.get('Visitante_UF', ''),
                    'winner': row.get('Vencedor', ''),
                    'arena': row.get('Arena', ''),
                    'id': row.get('ID', '')
                }
                self.matches.append(match)
    
    def _load_players(self):
        """Load FIFA player data."""
        filepath = os.path.join(self.data_dir, "fifa_data.csv")
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                player = {
                    'id': int(row.get('ID', 0)) if row.get('ID', '') else 0,
                    'name': row.get('Name', ''),
                    'age': int(row.get('Age', 0)) if row.get('Age', '') else 0,
                    'nationality': row.get('Nationality', ''),
                    'overall': int(row.get('Overall', 0)) if row.get('Overall', '') else 0,
                    'potential': int(row.get('Potential', 0)) if row.get('Potential', '') else 0,
                    'club': row.get('Club', ''),
                    'position': row.get('Position', ''),
                    'jersey_number': int(row.get('Jersey Number', 0)) if row.get('Jersey Number', '') else 0,
                    'height': row.get('Height', ''),
                    'weight': row.get('Weight', ''),
                    'crossing': int(row.get('Crossing', 0)) if row.get('Crossing', '') else 0,
                    'finishing': int(row.get('Finishing', 0)) if row.get('Finishing', '') else 0,
                    'dribbling': int(row.get('Dribbling', 0)) if row.get('Dribbling', '') else 0,
                    'short_passing': int(row.get('ShortPassing', 0)) if row.get('ShortPassing', '') else 0,
                    'volleys': int(row.get('Volleys', 0)) if row.get('Volleys', '') else 0,
                    'speed': int(row.get('SprintSpeed', 0)) if row.get('SprintSpeed', '') else 0,
                    'acceleration': int(row.get('Acceleration', 0)) if row.get('Acceleration', '') else 0,
                    'reactions': int(row.get('Reactions', 0)) if row.get('Reactions', '') else 0,
                    'balance': int(row.get('Balance', 0)) if row.get('Balance', '') else 0,
                    'shot_power': int(row.get('ShotPower', 0)) if row.get('ShotPower', '') else 0,
                    'stamina': int(row.get('Stamina', 0)) if row.get('Stamina', '') else 0,
                    'strength': int(row.get('Strength', 0)) if row.get('Strength', '') else 0,
                    'long_shots': int(row.get('LongShots', 0)) if row.get('LongShots', '') else 0,
                    'aggression': int(row.get('Aggression', 0)) if row.get('Aggression', '') else 0,
                    'interceptions': int(row.get('Interceptions', 0)) if row.get('Interceptions', '') else 0,
                    'positioning': int(row.get('Positioning', 0)) if row.get('Positioning', '') else 0,
                    'vision': int(row.get('Vision', 0)) if row.get('Vision', '') else 0,
                    'penalties': int(row.get('Penalties', 0)) if row.get('Penalties', '') else 0,
                    'composure': int(row.get('Composure', 0)) if row.get('Composure', '') else 0,
                }
                self.players.append(player)
    
    def _extract_year(self, date_str: str) -> int:
        """Extract year from date string."""
        if not date_str:
            return 0
        # Try to extract year from various formats
        match = re.search(r'(\d{4})', date_str)
        if match:
            return int(match.group(1))
        return 0
    
    def _parse_brazilian_date(self, date_str: str) -> str:
        """Parse Brazilian date format DD/MM/YYYY to ISO format."""
        if not date_str:
            return ""
        match = re.match(r'(\d{2})/(\d{2})/(\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month}-{day}"
        return date_str
    
    def _load_data(self):
        """Load all data files."""
        self._load_brasiileirao_matches()
        self._load_copa_do_brasil_matches()
        self._load_libertadores_matches()
        self._load_extended_matches()
        self._load_historical_brasileirao()
        self._load_players()
    
    def get_matches_by_teams(self, team1: str, team2: str = None, limit: int = 20):
        """Find matches between two teams or by a single team."""
        team1_norm = self._normalize_team_name(team1)
        team2_norm = self._normalize_team_name(team2) if team2 else None
        
        results = []
        for match in self.matches:
            home_norm = match.get('home_team_normalized', '')
            away_norm = match.get('away_team_normalized', '')
            
            if team2_norm:
                # Search for matches between two specific teams
                if (home_norm == team1_norm and away_norm == team2_norm) or \
                   (home_norm == team2_norm and away_norm == team1_norm):
                    results.append(match)
            else:
                # Search for matches involving a single team
                if home_norm == team1_norm or away_norm == team1_norm:
                    results.append(match)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_matches_by_competition(self, competition: str, limit: int = 50):
        """Find matches by competition."""
        competition_lower = competition.lower()
        results = []
        for match in self.matches:
            comp_lower = match.get('competition', '').lower()
            if competition_lower in comp_lower:
                results.append(match)
                if len(results) >= limit:
                    break
        return results
    
    def get_matches_by_season(self, season: int, limit: int = 100):
        """Find matches by season."""
        results = []
        for match in self.matches:
            if match.get('season') == season:
                results.append(match)
                if len(results) >= limit:
                    break
        return results
    
    def get_team_stats(self, team: str, season: int = None, competition: str = None):
        """Calculate team statistics."""
        team_norm = self._normalize_team_name(team)
        stats = {
            'team': team,
            'matches': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0,
            'home_matches': 0,
            'home_wins': 0,
            'home_draws': 0,
            'home_losses': 0,
            'home_goals_for': 0,
            'home_goals_against': 0,
            'away_matches': 0,
            'away_wins': 0,
            'away_draws': 0,
            'away_losses': 0,
            'away_goals_for': 0,
            'away_goals_against': 0
        }
        
        for match in self.matches:
            home_norm = match.get('home_team_normalized', '')
            away_norm = match.get('away_team_normalized', '')
            
            # Check competition filter
            if competition:
                comp_lower = match.get('competition', '').lower()
                if competition.lower() not in comp_lower:
                    continue
            
            # Check season filter
            if season and match.get('season') != season:
                continue
            
            if home_norm == team_norm:
                stats['matches'] += 1
                stats['goals_for'] += match.get('home_goal', 0)
                stats['goals_against'] += match.get('away_goal', 0)
                stats['home_matches'] += 1
                stats['home_goals_for'] += match.get('home_goal', 0)
                stats['home_goals_against'] += match.get('away_goal', 0)
                
                if match.get('home_goal', 0) > match.get('away_goal', 0):
                    stats['wins'] += 1
                    stats['home_wins'] += 1
                    stats['points'] += 3
                elif match.get('home_goal', 0) == match.get('away_goal', 0):
                    stats['draws'] += 1
                    stats['home_draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
                    stats['home_losses'] += 1
            elif away_norm == team_norm:
                stats['matches'] += 1
                stats['goals_for'] += match.get('away_goal', 0)
                stats['goals_against'] += match.get('home_goal', 0)
                stats['away_matches'] += 1
                stats['away_goals_for'] += match.get('away_goal', 0)
                stats['away_goals_against'] += match.get('home_goal', 0)
                
                if match.get('away_goal', 0) > match.get('home_goal', 0):
                    stats['wins'] += 1
                    stats['away_wins'] += 1
                    stats['points'] += 3
                elif match.get('away_goal', 0) == match.get('home_goal', 0):
                    stats['draws'] += 1
                    stats['away_draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
                    stats['away_losses'] += 1
        
        return stats
    
    def get_head_to_head(self, team1: str, team2: str):
        """Get head-to-head record between two teams."""
        matches = self.get_matches_by_teams(team1, team2)
        
        team1_norm = self._normalize_team_name(team1)
        team2_norm = self._normalize_team_name(team2)
        
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        results = []
        for match in matches:
            home_norm = match.get('home_team_normalized', '')
            away_norm = match.get('away_team_normalized', '')
            
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            home_goal = match.get('home_goal', 0)
            away_goal = match.get('away_goal', 0)
            datetime_str = match.get('datetime', '')
            round_info = match.get('round', '')
            competition = match.get('competition', '')
            
            # Format date
            date_str = datetime_str.split(' ')[0] if ' ' in datetime_str else datetime_str
            
            # Determine winner
            if home_norm == team1_norm:
                if home_goal > away_goal:
                    winner = team1
                    team1_wins += 1
                elif home_goal < away_goal:
                    winner = team2
                    team2_wins += 1
                else:
                    winner = 'Draw'
                    draws += 1
            else:
                if away_goal > home_goal:
                    winner = team1
                    team1_wins += 1
                elif away_goal < home_goal:
                    winner = team2
                    team2_wins += 1
                else:
                    winner = 'Draw'
                    draws += 1
            
            results.append({
                'date': date_str,
                'home_team': home_team,
                'away_team': away_team,
                'score': f"{home_goal}-{away_goal}",
                'winner': winner,
                'competition': competition,
                'round': round_info
            })
        
        return {
            'team1': team1,
            'team2': team2,
            'total_matches': len(results),
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'draws': draws,
            'matches': results
        }
    
    def get_player_by_name(self, name: str, limit: int = 20):
        """Search for players by name."""
        results = []
        name_lower = name.lower()
        for player in self.players:
            if name_lower in player.get('name', '').lower():
                results.append(player)
                if len(results) >= limit:
                    break
        return results
    
    def get_players_by_club(self, club: str, limit: int = 50):
        """Get players by club."""
        club_norm = club.lower()
        results = []
        for player in self.players:
            if club_norm in player.get('club', '').lower():
                results.append(player)
                if len(results) >= limit:
                    break
        return results
    
    def get_brazilian_players(self, limit: int = 100):
        """Get Brazilian players."""
        results = []
        for player in self.players:
            if player.get('nationality', '').lower() == 'brazil':
                results.append(player)
                if len(results) >= limit:
                    break
        return results
    
    def get_top_players(self, limit: int = 20, min_overall: int = 0):
        """Get top-rated players."""
        sorted_players = sorted(
            [p for p in self.players if p.get('overall', 0) >= min_overall],
            key=lambda x: x.get('overall', 0),
            reverse=True
        )
        return sorted_players[:limit]
    
    def get_competition_standings(self, competition: str, season: int = None):
        """Calculate competition standings."""
        team_stats = {}
        
        for match in self.matches:
            comp = match.get('competition', '')
            if comp.lower() not in competition.lower():
                continue
            
            if season and match.get('season') != season:
                continue
            
            home_norm = match.get('home_team_normalized', '')
            away_norm = match.get('away_team_normalized', '')
            home_goal = match.get('home_goal', 0)
            away_goal = match.get('away_goal', 0)
            
            for team, goals_for, goals_against in [
                (home_norm, home_goal, away_goal),
                (away_norm, away_goal, home_goal)
            ]:
                if team not in team_stats:
                    team_stats[team] = {
                        'team': team,
                        'matches': 0,
                        'wins': 0,
                        'draws': 0,
                        'losses': 0,
                        'goals_for': 0,
                        'goals_against': 0,
                        'points': 0
                    }
                
                stats = team_stats[team]
                stats['matches'] += 1
                stats['goals_for'] += goals_for
                stats['goals_against'] += goals_against
                
                if goals_for > goals_against:
                    stats['wins'] += 1
                    stats['points'] += 3
                elif goals_for == goals_against:
                    stats['draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
        
        standings = sorted(
            team_stats.values(),
            key=lambda x: (x['points'], x['goals_for'] - x['goals_against'], x['goals_for']),
            reverse=True
        )
        
        return standings
    
    def get_biggest_victories(self, limit: int = 10, competition: str = None):
        """Find the biggest victories by goal difference."""
        results = []
        
        for match in self.matches:
            if competition:
                comp_lower = match.get('competition', '').lower()
                if competition.lower() not in comp_lower:
                    continue
            
            home_goal = match.get('home_goal', 0)
            away_goal = match.get('away_goal', 0)
            goal_diff = abs(home_goal - away_goal)
            
            if goal_diff >= 3:  # Only significant victories
                results.append({
                    'date': match.get('datetime', '').split(' ')[0],
                    'home_team': match.get('home_team', ''),
                    'away_team': match.get('away_team', ''),
                    'score': f"{match.get('home_goal', 0)}-{match.get('away_goal', 0)}",
                    'goal_difference': goal_diff,
                    'competition': match.get('competition', '')
                })
        
        results.sort(key=lambda x: x['goal_difference'], reverse=True)
        return results[:limit]
    
    def get_average_goals(self, competition: str = None, season: int = None):
        """Calculate average goals per match."""
        total_goals = 0
        total_matches = 0
        
        for match in self.matches:
            if competition:
                comp_lower = match.get('competition', '').lower()
                if competition.lower() not in comp_lower:
                    continue
            
            if season and match.get('season') != season:
                continue
            
            total_goals += match.get('home_goal', 0) + match.get('away_goal', 0)
            total_matches += 1
        
        return {
            'total_matches': total_matches,
            'total_goals': total_goals,
            'average_goals_per_match': round(total_goals / total_matches, 2) if total_matches > 0 else 0
        }
    
    def get_team_competition_history(self, team: str, competition: str):
        """Get team's history in a specific competition."""
        team_norm = self._normalize_team_name(team)
        competition_lower = competition.lower()
        
        results = []
        for match in self.matches:
            comp_lower = match.get('competition', '').lower()
            if competition_lower not in comp_lower:
                continue
            
            home_norm = match.get('home_team_normalized', '')
            away_norm = match.get('away_team_normalized', '')
            
            if home_norm == team_norm or away_norm == team_norm:
                results.append({
                    'date': match.get('datetime', '').split(' ')[0],
                    'home_team': match.get('home_team', ''),
                    'away_team': match.get('away_team', ''),
                    'score': f"{match.get('home_goal', 0)}-{match.get('away_goal', 0)}",
                    'round': match.get('round', '')
                })
        
        return results
    
    def search_matches(self, team: str = None, season: int = None, competition: str = None, limit: int = 50):
        """Search matches with optional filters."""
        results = []
        
        for match in self.matches:
            if team:
                team_norm = self._normalize_team_name(team)
                home_norm = match.get('home_team_normalized', '')
                away_norm = match.get('away_team_normalized', '')
                if home_norm != team_norm and away_norm != team_norm:
                    continue
            
            if season and match.get('season') != season:
                continue
            
            if competition:
                comp_lower = match.get('competition', '').lower()
                if competition.lower() not in comp_lower:
                    continue
            
            results.append(match)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_match_details(self, match_id: str):
        """Get detailed match information."""
        for match in self.matches:
            if match.get('id') == match_id:
                return match
        return None


def main():
    """Main function to run the MCP server."""
    print("Brazilian Soccer MCP Server")
    print("=" * 40)
    
    server = BrazilianSoccerMCP()
    
    print(f"\nLoaded {len(server.matches)} matches")
    print(f"Loaded {len(server.players)} players")
    
    # Example queries
    print("\n--- Example Queries ---")
    
    # Query 1: Find Flamengo vs Fluminense matches
    print("\n1. Flamengo vs Fluminense matches:")
    matches = server.get_matches_by_teams("Flamengo", "Fluminense", limit=5)
    for m in matches[:3]:
        print(f"   {m['datetime'].split(' ')[0]}: {m['home_team']} {m['home_goal']}-{m['away_goal']} {m['away_team']}")
    
    # Query 2: Team statistics
    print("\n2. Flamengo home record in 2023:")
    stats = server.get_team_stats("Flamengo", season=2023)
    print(f"   Matches: {stats['matches']}, Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}")
    
    # Query 3: Player search
    print("\n3. Search for 'Neymar':")
    players = server.get_player_by_name("Neymar", limit=3)
    for p in players:
        print(f"   {p['name']} - {p['position']} - {p['club']} (Overall: {p['overall']})")
    
    # Query 4: Competition standings
    print("\n4. 2019 Brasileirão standings:")
    standings = server.get_competition_standings("Brasileirão", season=2019)
    for i, team in enumerate(standings[:5], 1):
        print(f"   {i}. {team['team']}: {team['points']} pts")
    
    print("\nServer ready for MCP connections!")


if __name__ == "__main__":
    main()
