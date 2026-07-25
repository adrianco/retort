"""Brazilian Soccer MCP Server - Statistical Analysis."""

from typing import Dict, List, Optional, Tuple
from soccer_data import SoccerDataLoader, get_loader
from match_queries import MatchQueryEngine, get_match_engine
from team_queries import TeamQueryEngine, get_team_engine
import pandas as pd
import statistics


class StatisticalAnalysisEngine:
    """Engine for statistical analysis of soccer data."""
    
    def __init__(self, loader: Optional[SoccerDataLoader] = None,
                 match_engine: Optional[MatchQueryEngine] = None,
                 team_engine: Optional[TeamQueryEngine] = None):
        """Initialize with engines."""
        self.loader = loader or get_loader()
        self.match_engine = match_engine or get_match_engine()
        self.team_engine = team_engine or get_team_engine()
        self.data = self.loader.load_all()
    
    def get_average_goals_per_match(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None
    ) -> Dict:
        """Calculate average goals per match."""
        matches = self.match_engine.find_matches(
            competition=competition, season=season
        )
        
        if not matches:
            return {'error': 'No matches found'}
        
        total_goals = sum(m['home_goal'] + m['away_goal'] for m in matches)
        avg_goals = total_goals / len(matches) if matches else 0
        
        return {
            'total_matches': len(matches),
            'total_goals': total_goals,
            'average_goals_per_match': round(avg_goals, 2),
            'min_goals_per_match': min(m['home_goal'] + m['away_goal'] for m in matches),
            'max_goals_per_match': max(m['home_goal'] + m['away_goal'] for m in matches)
        }
    
    def get_home_advantage(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None
    ) -> Dict:
        """Calculate home advantage statistics."""
        matches = self.match_engine.find_matches(
            competition=competition, season=season
        )
        
        if not matches:
            return {'error': 'No matches found'}
        
        home_wins = 0
        draws = 0
        away_wins = 0
        
        for match in matches:
            if match['home_goal'] > match['away_goal']:
                home_wins += 1
            elif match['home_goal'] == match['away_goal']:
                draws += 1
            else:
                away_wins += 1
        
        total = home_wins + draws + away_wins
        
        return {
            'total_matches': total,
            'home_wins': home_wins,
            'draws': draws,
            'away_wins': away_wins,
            'home_win_rate': round(home_wins / total * 100, 1) if total > 0 else 0,
            'draw_rate': round(draws / total * 100, 1) if total > 0 else 0,
            'away_win_rate': round(away_wins / total * 100, 1) if total > 0 else 0
        }
    
    def get_biggest_victories(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get the biggest victories by goal difference."""
        matches = self.match_engine.find_matches(
            competition=competition, season=season
        )
        
        if not matches:
            return []
        
        # Calculate goal difference
        for match in matches:
            home_goal = match['home_goal'] if match['home_goal'] is not None else 0
            away_goal = match['away_goal'] if match['away_goal'] is not None else 0
            match['goal_diff'] = abs(home_goal - away_goal)
        
        # Sort by goal difference
        matches.sort(key=lambda x: x['goal_diff'], reverse=True)
        
        return [{
            'date': m['date'],
            'home_team': m['home_team'],
            'away_team': m['away_team'],
            'home_goal': m['home_goal'],
            'away_goal': m['away_goal'],
            'goal_difference': m['goal_diff'],
            'competition': m['competition']
        } for m in matches[:limit]]
    
    def get_top_teams_by_win_rate(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        min_matches: int = 10
    ) -> List[Dict]:
        """Get teams with the highest win rates."""
        # Get unique teams
        teams = set()
        matches = self.match_engine.find_matches(
            season=season, competition=competition
        )
        
        for match in matches:
            teams.add(match['home_team'])
            teams.add(match['away_team'])
        
        # Calculate win rates
        team_stats = []
        for team in teams:
            stats = self.team_engine.get_team_statistics(
                team, season=season, competition=competition
            )
            if stats.get('total_matches', 0) >= min_matches:
                team_stats.append(stats)
        
        # Sort by win rate
        team_stats.sort(key=lambda x: x['win_rate'], reverse=True)
        
        return team_stats[:20]
    
    def get_best_away_teams(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = None
    ) -> List[Dict]:
        """Get teams with the best away records."""
        teams = set()
        matches = self.match_engine.find_matches(
            season=season, competition=competition
        )
        
        for match in matches:
            teams.add(match['home_team'])
            teams.add(match['away_team'])
        
        away_stats = []
        for team in teams:
            # Get away matches only
            away_matches = [m for m in matches 
                          if (m['away_team'] == team or m['away_team'] == team.lower())]
            
            if not away_matches:
                continue
            
            wins = sum(1 for m in away_matches if m['away_goal'] > m['home_goal'])
            draws = sum(1 for m in away_matches if m['away_goal'] == m['home_goal'])
            losses = sum(1 for m in away_matches if m['away_goal'] < m['home_goal'])
            
            total = wins + draws + losses
            points = wins * 3 + draws
            
            away_stats.append({
                'team': team,
                'matches': total,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'points': points,
                'win_rate': round(wins / total * 100, 1) if total > 0 else 0
            })
        
        away_stats.sort(key=lambda x: (-x['points'], -x['wins']))
        return away_stats[:10]
    
    def get_team_performance_trend(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        last_n: int = 10
    ) -> Dict:
        """Get recent performance trend for a team."""
        history = self.team_engine.get_team_match_history(
            team, limit=last_n, competition=competition, season=season
        )
        
        if not history:
            return {'error': 'No recent matches found'}
        
        # Reverse to get chronological order
        history.reverse()
        
        results = []
        for match in history:
            is_home = match.get('is_home', True)
            home_goals = match['home_goal']
            away_goals = match['away_goal']
            
            if is_home:
                if home_goals > away_goals:
                    result = 'W'
                elif home_goals == away_goals:
                    result = 'D'
                else:
                    result = 'L'
            else:
                if away_goals > home_goals:
                    result = 'W'
                elif away_goals == home_goals:
                    result = 'D'
                else:
                    result = 'L'
            
            results.append({
                'date': match['date'],
                'opponent': match['away_team'] if is_home else match['home_team'],
                'result': result,
                'score': f"{match['home_goal']}-{match['away_goal']}"
            })
        
        # Calculate streak
        streak = 0
        for r in reversed(results):
            if r['result'] == 'W':
                streak += 1
            elif r['result'] == 'D':
                streak += 0.5
            else:
                break
        
        return {
            'team': team,
            'last_n_matches': len(results),
            'results': results,
            'current_streak': streak,
            'wins': sum(1 for r in results if r['result'] == 'W'),
            'draws': sum(1 for r in results if r['result'] == 'D'),
            'losses': sum(1 for r in results if r['result'] == 'L')
        }
    
    def get_competition_analysis(
        self,
        competition: str,
        season: int
    ) -> Dict:
        """Get comprehensive competition analysis."""
        standings = self.match_engine.find_matches(
            competition=competition, season=season
        )
        
        if not standings:
            return {'error': 'No data found'}
        
        # Get champion
        champion = self.competition_engine.get_champion(competition, season)
        
        # Calculate statistics
        goals_per_match = self.get_average_goals_per_match(
            competition=competition, season=season
        )
        home_advantage = self.get_home_advantage(
            competition=competition, season=season
        )
        biggest_victories = self.get_biggest_victories(
            competition=competition, season=season, limit=5
        )
        
        return {
            'competition': competition,
            'season': season,
            'champion': champion,
            'total_matches': len(standings),
            'goals_per_match': goals_per_match,
            'home_advantage': home_advantage,
            'biggest_victories': biggest_victories
        }
    
    def get_head_to_head_stats(
        self,
        team1: str,
        team2: str
    ) -> Dict:
        """Get comprehensive head-to-head statistics."""
        h2h = self.match_engine.get_head_to_head(team1, team2)
        
        stats = h2h['statistics']
        matches = h2h['matches']
        
        # Calculate home/away breakdown
        team1_home = [m for m in matches if m['home_team'] == team1 or m['home_team'] == team1.lower()]
        team1_away = [m for m in matches if m['away_team'] == team1 or m['away_team'] == team1.lower()]
        
        return {
            'team1': team1,
            'team2': team2,
            'total_matches': stats['total_matches'],
            f'{team1}_wins': stats[f'{team1}_wins'],
            f'{team2}_wins': stats[f'{team2}_wins'],
            'draws': stats['draws'],
            f'{team1}_goals': stats[f'{team1}_goals'],
            f'{team2}_goals': stats[f'{team2}_goals'],
            f'{team1}_home_record': {
                'matches': len(team1_home),
                'wins': sum(1 for m in team1_home if m['home_goal'] > m['away_goal']),
                'draws': sum(1 for m in team1_home if m['home_goal'] == m['away_goal']),
                'losses': sum(1 for m in team1_home if m['home_goal'] < m['away_goal'])
            },
            f'{team1}_away_record': {
                'matches': len(team1_away),
                'wins': sum(1 for m in team1_away if m['away_goal'] > m['home_goal']),
                'draws': sum(1 for m in team1_away if m['away_goal'] == m['home_goal']),
                'losses': sum(1 for m in team1_away if m['away_goal'] < m['home_goal'])
            }
        }
    
    def get_season_comparison(
        self,
        season1: int,
        season2: int,
        competition: Optional[str] = None
    ) -> Dict:
        """Compare two seasons."""
        matches1 = self.match_engine.find_matches(
            season=season1, competition=competition
        )
        matches2 = self.match_engine.find_matches(
            season=season2, competition=competition
        )
        
        def analyze_season(matches):
            if not matches:
                return None
            total_goals = sum(m['home_goal'] + m['away_goal'] for m in matches)
            return {
                'total_matches': len(matches),
                'total_goals': total_goals,
                'avg_goals': round(total_goals / len(matches), 2),
                'home_win_rate': round(
                    sum(1 for m in matches if m['home_goal'] > m['away_goal']) / len(matches) * 100, 1
                )
            }
        
        return {
            'season1': season1,
            'season2': season2,
            'season1_stats': analyze_season(matches1),
            'season2_stats': analyze_season(matches2)
        }


def get_statistical_engine() -> StatisticalAnalysisEngine:
    """Get or create a statistical analysis engine instance."""
    if not hasattr(get_statistical_engine, "instance"):
        get_statistical_engine.instance = StatisticalAnalysisEngine()
    return get_statistical_engine.instance
