"""
Brazilian Soccer Query Engine
Implements all query functionality for the soccer data
"""

import pandas as pd
from typing import Optional, List, Dict
from data_loader import SoccerDataLoader
from pydantic import BaseModel


class TeamStats(BaseModel):
    team: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    win_rate: float


class MatchResult(BaseModel):
    datetime: str
    home_team: str
    away_team: str
    home_goal: int
    away_goal: int
    season: Optional[int] = None
    round: Optional[int] = None
    competition: str
    stage: Optional[str] = None


class PlayerInfo(BaseModel):
    id: int
    name: str
    age: int
    nationality: str
    overall: int
    potential: int
    club: str
    position: str
    jersey_number: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None


class CompetitionStandings(BaseModel):
    position: int
    team: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class BigWin(BaseModel):
    date: str
    home_team: str
    away_team: str
    home_goal: int
    away_goal: int
    competition: str
    season: Optional[int] = None


class SoccerQueryEngine:
    """Query engine for soccer data"""

    def __init__(self, loader: SoccerDataLoader):
        self.loader = loader

    def find_matches_between_teams(self, team1: str, team2: str) -> List[Dict]:
        """Find all matches between two teams"""
        matches = self.loader.get_all_matches(home_team=team1, away_team=team2)
        reverse_matches = self.loader.get_all_matches(home_team=team2, away_team=team1)
        
        all_matches = matches + reverse_matches
        seen = set()
        unique_matches = []
        for match in all_matches:
            key = (match['home_team'], match['away_team'], match['datetime'])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        unique_matches.sort(key=lambda x: x['datetime'], reverse=True)
        return unique_matches

    def get_team_statistics(self, team: str, season: Optional[int] = None, 
                           competition: Optional[str] = None) -> TeamStats:
        """Get comprehensive team statistics"""
        matches = self.loader.get_all_matches(home_team=team, competition=competition, season=season)
        away_matches = self.loader.get_all_matches(away_team=team, competition=competition, season=season)
        
        all_matches = matches + away_matches
        wins = draws = losses = goals_for = goals_against = 0
        
        for match in all_matches:
            is_home = match['home_team'].lower() == team.lower()
            team_goals = match['home_goal'] if is_home else match['away_goal']
            opponent_goals = match['away_goal'] if is_home else match['home_goal']
            
            goals_for += team_goals
            goals_against += opponent_goals
            
            if team_goals > opponent_goals:
                wins += 1
            elif team_goals == opponent_goals:
                draws += 1
            else:
                losses += 1
        
        points = wins * 3 + draws
        matches_count = wins + draws + losses
        
        return TeamStats(
            team=team,
            matches=matches_count,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=goals_for,
            goals_against=goals_against,
            goal_difference=goals_for - goals_against,
            points=points,
            win_rate=round(wins / matches_count * 100, 1) if matches_count > 0 else 0.0
        )

    def get_player_by_name(self, name: str) -> Optional[PlayerInfo]:
        """Find a player by name"""
        if self.loader.fifa_df is None:
            return None
        
        df = self.loader.fifa_df
        mask = df['Name'].str.contains(name, case=False, na=False)
        players = df[mask]
        
        if len(players) == 0:
            return None
        
        row = players.iloc[0]
        return PlayerInfo(
            id=int(row['ID']),
            name=str(row['Name']),
            age=int(row['Age']) if pd.notna(row.get('Age')) else 0,
            nationality=str(row['Nationality']) if pd.notna(row.get('Nationality')) else '',
            overall=int(row['Overall']) if pd.notna(row.get('Overall')) else 0,
            potential=int(row['Potential']) if pd.notna(row.get('Potential')) else 0,
            club=str(row['Club']) if pd.notna(row.get('Club')) else '',
            position=str(row['Position']) if pd.notna(row.get('Position')) else '',
            jersey_number=int(row['Jersey Number']) if pd.notna(row.get('Jersey Number')) else None,
            height=str(row['Height']) if pd.notna(row.get('Height')) else None,
            weight=str(row['Weight']) if pd.notna(row.get('Weight')) else None,
        )

    def get_players_by_club(self, club: str) -> List[PlayerInfo]:
        """Get all players from a club"""
        if self.loader.fifa_df is None:
            return []
        
        df = self.loader.fifa_df
        mask = df['Club'].str.contains(club, case=False, na=False)
        players = df[mask]
        
        result = []
        for _, row in players.head(50).iterrows():
            result.append(PlayerInfo(
                id=int(row['ID']),
                name=str(row['Name']),
                age=int(row['Age']) if pd.notna(row.get('Age')) else 0,
                nationality=str(row['Nationality']) if pd.notna(row.get('Nationality')) else '',
                overall=int(row['Overall']) if pd.notna(row.get('Overall')) else 0,
                potential=int(row['Potential']) if pd.notna(row.get('Potential')) else 0,
                club=str(row['Club']) if pd.notna(row.get('Club')) else '',
                position=str(row['Position']) if pd.notna(row.get('Position')) else '',
                jersey_number=int(row['Jersey Number']) if pd.notna(row.get('Jersey Number')) else None,
                height=str(row['Height']) if pd.notna(row.get('Height')) else None,
                weight=str(row['Weight']) if pd.notna(row.get('Weight')) else None,
            ))
        return result

    def get_brazilian_players(self) -> List[PlayerInfo]:
        """Get all Brazilian players"""
        if self.loader.fifa_df is None:
            return []
        
        df = self.loader.fifa_df
        mask = df['Nationality'].str.contains('Brazil', case=False, na=False) | \
               df['Nationality'].str.contains('Brasil', case=False, na=False)
        players = df[mask].sort_values('Overall', ascending=False)
        
        result = []
        for _, row in players.head(100).iterrows():
            result.append(PlayerInfo(
                id=int(row['ID']),
                name=str(row['Name']),
                age=int(row['Age']) if pd.notna(row.get('Age')) else 0,
                nationality=str(row['Nationality']),
                overall=int(row['Overall']) if pd.notna(row.get('Overall')) else 0,
                potential=int(row['Potential']) if pd.notna(row.get('Potential')) else 0,
                club=str(row['Club']) if pd.notna(row.get('Club')) else '',
                position=str(row['Position']) if pd.notna(row.get('Position')) else '',
                jersey_number=int(row['Jersey Number']) if pd.notna(row.get('Jersey Number')) else None,
                height=str(row['Height']) if pd.notna(row.get('Height')) else None,
                weight=str(row['Weight']) if pd.notna(row.get('Weight')) else None,
            ))
        return result

    def get_competition_standings(self, competition: str, season: int) -> List[CompetitionStandings]:
        """Calculate competition standings for a season"""
        matches = self.loader.get_all_matches(competition=competition, season=season)
        team_stats = {}
        
        for match in matches:
            home_team = match['home_team']
            away_team = match['away_team']
            home_goals = match['home_goal']
            away_goals = match['away_goal']
            
            if home_team not in team_stats:
                team_stats[home_team] = {
                    'team': home_team, 'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                    'goals_for': 0, 'goals_against': 0,
                }
            if away_team not in team_stats:
                team_stats[away_team] = {
                    'team': away_team, 'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                    'goals_for': 0, 'goals_against': 0,
                }
            
            team_stats[home_team]['matches'] += 1
            team_stats[home_team]['goals_for'] += home_goals
            team_stats[home_team]['goals_against'] += away_goals
            team_stats[away_team]['matches'] += 1
            team_stats[away_team]['goals_for'] += away_goals
            team_stats[away_team]['goals_against'] += home_goals
            
            if home_goals > away_goals:
                team_stats[home_team]['wins'] += 1
                team_stats[away_team]['losses'] += 1
            elif home_goals < away_goals:
                team_stats[away_team]['wins'] += 1
                team_stats[home_team]['losses'] += 1
            else:
                team_stats[home_team]['draws'] += 1
                team_stats[away_team]['draws'] += 1
        
        standings = []
        for team, stats in team_stats.items():
            points = stats['wins'] * 3 + stats['draws']
            standings.append({
                **stats,
                'goal_difference': stats['goals_for'] - stats['goals_against'],
                'points': points,
            })
        
        standings.sort(key=lambda x: (x['points'], x['goal_difference'], x['goals_for']), reverse=True)
        for i, team in enumerate(standings):
            team['position'] = i + 1
        
        return [CompetitionStandings(**s) for s in standings[:20]]

    def get_big_wins(self, limit: int = 10) -> List[BigWin]:
        """Get biggest wins in the dataset"""
        all_matches = self.loader.get_all_matches()
        big_wins = []
        
        for match in all_matches:
            home_goals = match['home_goal']
            away_goals = match['away_goal']
            goal_diff = abs(home_goals - away_goals)
            
            if goal_diff >= 4:
                big_wins.append(BigWin(
                    date=match['datetime'],
                    home_team=match['home_team'],
                    away_team=match['away_team'],
                    home_goal=home_goals,
                    away_goal=away_goals,
                    competition=match['competition'],
                    season=match['season'],
                ))
        
        big_wins.sort(key=lambda x: abs(x.home_goal - x.away_goal), reverse=True)
        return big_wins[:limit]

    def get_head_to_head(self, team1: str, team2: str) -> Dict:
        """Get head-to-head record between two teams"""
        matches = self.find_matches_between_teams(team1, team2)
        team1_wins = team2_wins = draws = 0
        
        for match in matches:
            home_goals = match['home_goal']
            away_goals = match['away_goal']
            home_team = match['home_team']
            
            if home_team.lower() == team1.lower():
                if home_goals > away_goals:
                    team1_wins += 1
                elif home_goals < away_goals:
                    team2_wins += 1
                else:
                    draws += 1
            else:
                if away_goals > home_goals:
                    team1_wins += 1
                elif away_goals < home_goals:
                    team2_wins += 1
                else:
                    draws += 1
        
        return {
            'team1': team1,
            'team2': team2,
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'draws': draws,
            'total_matches': len(matches),
            'matches': matches[:10],
        }

    def find_matches_by_team(self, team: str, limit: int = 10) -> List[Dict]:
        """Find matches for a specific team"""
        matches = self.loader.get_all_matches(home_team=team)
        away_matches = self.loader.get_all_matches(away_team=team)
        all_matches = matches + away_matches
        
        all_matches.sort(key=lambda x: x['datetime'], reverse=True)
        return all_matches[:limit]

    def get_team_match_history(self, team: str, season: Optional[int] = None) -> List[Dict]:
        """Get match history for a team"""
        matches = self.loader.get_all_matches(home_team=team, season=season)
        away_matches = self.loader.get_all_matches(away_team=team, season=season)
        all_matches = matches + away_matches
        all_matches.sort(key=lambda x: x['datetime'], reverse=True)
        return all_matches
