"""Statistical analysis for the Brazilian Soccer MCP server."""

from typing import List, Dict, Any
import pandas as pd
from .data_loader import DataFileManager
from .match_queries import MatchQueryEngine
from .competition_queries import CompetitionQueryEngine


class StatisticalAnalysisEngine:
    """Engine for statistical analysis of soccer data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize with optional data directory path."""
        self.data_manager = DataFileManager(data_dir)
        self.match_engine = MatchQueryEngine(data_dir)
        self.competition_engine = CompetitionQueryEngine(data_dir)
    
    def get_average_goals_per_match(self, competition: str = None) -> float:
        """Calculate average goals per match."""
        matches = self.match_engine.find_matches(competition=competition, limit=10000)
        
        total_goals = 0
        for match in matches:
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            total_goals += home_score + away_score
        
        if len(matches) > 0:
            return round(total_goals / len(matches), 2)
        return 0.0
    
    def get_home_win_rate(self, competition: str = None) -> float:
        """Calculate home win rate."""
        matches = self.match_engine.find_matches(competition=competition, limit=10000)
        
        home_wins = 0
        draws = 0
        away_wins = 0
        
        for match in matches:
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
            if home_score > away_score:
                home_wins += 1
            elif home_score == away_score:
                draws += 1
            else:
                away_wins += 1
        
        total = home_wins + draws + away_wins
        if total > 0:
            return round((home_wins / total) * 100, 1)
        return 0.0
    
    def get_biggest_victories(
        self,
        competition: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the biggest victories by goal difference."""
        matches = self.match_engine.find_matches(competition=competition, limit=10000)
        
        # Calculate goal differences
        results = []
        for match in matches:
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            goal_diff = abs(home_score - away_score)
            
            if home_score > away_score:
                winner = match.get('home_team', 'Unknown')
                loser = match.get('away_team', 'Unknown')
                score = f"{home_score}-{away_score}"
            else:
                winner = match.get('away_team', 'Unknown')
                loser = match.get('home_team', 'Unknown')
                score = f"{away_score}-{home_score}"
            
            results.append({
                'date': match.get('date', ''),
                'home_team': match.get('home_team', ''),
                'away_team': match.get('away_team', ''),
                'score': score,
                'winner': winner,
                'loser': loser,
                'goal_difference': goal_diff
            })
        
        # Sort by goal difference
        results.sort(key=lambda x: -x['goal_difference'])
        
        return results[:limit]
    
    def get_team_performance_trend(
        self,
        team: str,
        season: int = None,
        competition: str = None,
        matches_back: int = 10
    ) -> Dict[str, Any]:
        """Get recent performance trend for a team."""
        history = self.match_engine.get_team_match_history(
            team=team,
            season=season,
            competition=competition
        )
        
        matches = history['matches'][:matches_back]
        
        # Calculate trend
        results = []
        points = 0
        streak = []
        
        for match in matches:
            home = match.get('home_team', '')
            away = match.get('away_team', '')
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
            # Determine result
            if team.lower() in home.lower():
                if home_score > away_score:
                    result = 'W'
                    points += 3
                elif home_score == away_score:
                    result = 'D'
                    points += 1
                else:
                    result = 'L'
            elif team.lower() in away.lower():
                if away_score > home_score:
                    result = 'W'
                    points += 3
                elif away_score == home_score:
                    result = 'D'
                    points += 1
                else:
                    result = 'L'
            else:
                result = '-'
            
            streak.append(result)
            
            results.append({
                'date': match.get('date', ''),
                'opponent': away if team.lower() in home.lower() else home,
                'score': f"{home_score}-{away_score}",
                'result': result
            })
        
        return {
            'team': team,
            'matches': results,
            'points': points,
            'streak': ''.join(streak[-5:])  # Last 5 results
        }
    
    def get_head_to_head_statistics(
        self,
        team1: str,
        team2: str
    ) -> Dict[str, Any]:
        """Get detailed head-to-head statistics between two teams."""
        h2h = self.match_engine.get_match_by_teams(team1, team2, limit=100)
        
        matches = h2h['matches']
        stats = h2h['statistics']
        
        # Calculate more detailed stats
        team1_normalized = stats['team1_normalized'] if 'team1_normalized' in stats else stats['team1']
        team2_normalized = stats['team2_normalized'] if 'team2_normalized' in stats else stats['team2']
        
        # Home vs Away breakdown
        team1_home = [m for m in matches if team1_normalized.lower() in m.get('home_team', '').lower()]
        team1_away = [m for m in matches if team1_normalized.lower() in m.get('away_team', '').lower()]
        
        team1_stats = {
            'home_matches': len(team1_home),
            'away_matches': len(team1_away)
        }
        
        team2_stats = {
            'home_matches': len(team1_away),  # Team2 is home when team1 is away
            'away_matches': len(team1_home)   # Team2 is away when team1 is home
        }
        
        return {
            'team1': team1,
            'team2': team2,
            'total_matches': len(matches),
            'head_to_head': stats['head_to_head'],
            'team1_stats': team1_stats,
            'team2_stats': team2_stats,
            'matches': matches[:10]  # First 10 matches
        }
    
    def get_competition_statistics(self, competition: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a competition."""
        # Get all matches
        matches = self.match_engine.find_matches(competition=competition, limit=10000)
        
        # Calculate stats
        stats = {
            'competition': competition,
            'total_matches': len(matches),
            'total_goals': 0,
            'home_wins': 0,
            'draws': 0,
            'away_wins': 0,
            'biggest_win': {'goal_difference': 0},
            'teams': set()
        }
        
        for match in matches:
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            goal_diff = abs(home_score - away_score)
            
            stats['total_goals'] += home_score + away_score
            
            if home_score > away_score:
                stats['home_wins'] += 1
            elif home_score == away_score:
                stats['draws'] += 1
            else:
                stats['away_wins'] += 1
            
            if goal_diff > stats['biggest_win']['goal_difference']:
                stats['biggest_win'] = {
                    'goal_difference': goal_diff,
                    'home_team': match.get('home_team', ''),
                    'away_team': match.get('away_team', ''),
                    'score': f"{home_score}-{away_score}"
                }
            
            stats['teams'].add(match.get('home_team', ''))
            stats['teams'].add(match.get('away_team', ''))
        
        stats['teams'] = list(stats['teams'])
        
        if len(matches) > 0:
            stats['average_goals'] = round(stats['total_goals'] / len(matches), 2)
            stats['home_win_rate'] = round((stats['home_wins'] / len(matches)) * 100, 1)
        
        return stats
    
    def get_season_summary(self, season: int) -> Dict[str, Any]:
        """Get summary of a season."""
        competitions = ['Brasileirão']
        summary = {
            'season': season,
            'competitions': {}
        }
        
        for comp in competitions:
            standings = self.competition_engine.get_competition_standings(comp, season)
            if standings['standings']:
                summary['competitions'][comp] = {
                    'champion': standings['standings'][0]['team'] if standings['standings'] else 'Unknown',
                    'total_teams': len(standings['standings']),
                    'matches_played': sum(t['played'] for t in standings['standings']) // 2
                }
        
        return summary
    
    def get_top_scorers_by_competition(
        self,
        competition: str,
        season: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top scorers for a competition (placeholder - data doesn't have individual scorers)."""
        # Since match data doesn't include individual scorers, return team stats instead
        standings = self.competition_engine.get_competition_standings(competition, season)
        
        # Sort by goals for
        sorted_teams = sorted(
            standings['standings'],
            key=lambda x: -x['goals_for']
        )[:limit]
        
        return [
            {
                'team': team['team'],
                'goals_scored': team['goals_for'],
                'position': i + 1
            }
            for i, team in enumerate(sorted_teams)
        ]
