"""Player and competition queries for Brazilian Soccer MCP Server."""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from soccer_mcp.models import Player, QueryResult, TeamStats, Match
from soccer_mcp.loader import DataLoader


class MatchQueries:
    """Handles match-related queries."""
    
    def __init__(self, loader: DataLoader):
        """Initialize with data loader."""
        self.loader = loader
    
    def find_matches_by_teams(self, team1: str, team2: str, limit: int = 20) -> QueryResult:
        """Find matches between two teams."""
        try:
            matches = self.loader.get_matches_by_teams(team1, team2)
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found between {team1} and {team2}",
                    count=0
                )
            
            # Sort by date (most recent first)
            matches.sort(key=lambda m: m.datetime or '', reverse=True)
            
            # Limit results
            matches = matches[:limit]
            
            # Format response
            data = []
            for m in matches:
                data.append({
                    'date': m.datetime or m.date or '',
                    'home_team': m.home_team or '',
                    'away_team': m.away_team or '',
                    'home_goal': m.home_goal,
                    'away_goal': m.away_goal,
                    'competition': m.competition or '',
                    'round': m.round,
                    'season': m.season,
                    'stage': m.stage or ''
                })
            
            # Generate summary
            summary = self._format_match_summary(matches, team1, team2)
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(matches),
                metadata={'team1': team1, 'team2': team2}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def find_matches_by_team(self, team_name: str, limit: int = 20, season: Optional[int] = None) -> QueryResult:
        """Find all matches for a team."""
        try:
            matches = self.loader.get_matches_by_team(team_name)
            
            if season:
                matches = [m for m in matches if m.season == season]
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for {team_name}",
                    count=0
                )
            
            # Sort by date
            matches.sort(key=lambda m: m.datetime or m.date or '', reverse=True)
            matches = matches[:limit]
            
            data = []
            for m in matches:
                data.append({
                    'date': m.datetime or m.date or '',
                    'home_team': m.home_team or '',
                    'away_team': m.away_team or '',
                    'home_goal': m.home_goal,
                    'away_goal': m.away_goal,
                    'competition': m.competition or '',
                    'round': m.round,
                    'season': m.season
                })
            
            summary = f"Found {len(matches)} matches for {team_name}"
            if season:
                summary += f" in season {season}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(matches),
                metadata={'team': team_name, 'season': season}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def find_matches_by_competition(self, competition: str, limit: int = 50) -> QueryResult:
        """Find matches by competition."""
        try:
            matches = self.loader.get_matches_by_competition(competition)
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for {competition}",
                    count=0
                )
            
            matches.sort(key=lambda m: m.datetime or m.date or '', reverse=True)
            matches = matches[:limit]
            
            data = []
            for m in matches:
                data.append({
                    'date': m.datetime or m.date or '',
                    'home_team': m.home_team or '',
                    'away_team': m.away_team or '',
                    'home_goal': m.home_goal,
                    'away_goal': m.away_goal,
                    'round': m.round,
                    'season': m.season,
                    'stage': m.stage or ''
                })
            
            summary = f"Found {len(matches)} matches in {competition}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(matches),
                metadata={'competition': competition}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def find_matches_by_season(self, season: int) -> QueryResult:
        """Find all matches in a season."""
        try:
            matches = self.loader.get_matches_by_season(season)
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for season {season}",
                    count=0
                )
            
            matches.sort(key=lambda m: m.datetime or m.date or '')
            
            data = []
            for m in matches:
                data.append({
                    'date': m.datetime or m.date or '',
                    'home_team': m.home_team or '',
                    'away_team': m.away_team or '',
                    'home_goal': m.home_goal,
                    'away_goal': m.away_goal,
                    'competition': m.competition or '',
                    'round': m.round
                })
            
            summary = f"Found {len(matches)} matches in season {season}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(matches),
                metadata={'season': season}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_match_by_id(self, match_id: str) -> QueryResult:
        """Find a specific match by ID."""
        try:
            for m in self.loader.matches:
                if m.id and str(m.id) == match_id:
                    data = {
                        'date': m.datetime or m.date or '',
                        'home_team': m.home_team or '',
                        'away_team': m.away_team or '',
                        'home_goal': m.home_goal,
                        'away_goal': m.away_goal,
                        'competition': m.competition or '',
                        'round': m.round,
                        'season': m.season,
                        'stage': m.stage or '',
                        'arena': m.arena or '',
                        'winner': m.winner or ''
                    }
                    return QueryResult(success=True, data=[data], summary=f"Match found: {m.home_team or ''} vs {m.away_team or ''}", count=1)
            
            return QueryResult(success=True, data=[], summary=f"Match with ID {match_id} not found", count=0)
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_biggest_victories(self, competition: Optional[str] = None, limit: int = 10) -> QueryResult:
        """Find the biggest victories."""
        try:
            matches = self.loader.matches
            
            if competition:
                matches = self.loader.get_matches_by_competition(competition)
            
            # Filter matches with clear winners
            victories = []
            for m in matches:
                if m.home_goal is not None and m.away_goal is not None:
                    goal_diff = abs(m.home_goal - m.away_goal)
                    if goal_diff >= 3:  # Only include wins by 3+ goals
                        victories.append({
                            'date': m.datetime or m.date or '',
                            'home_team': m.home_team or '',
                            'away_team': m.away_team or '',
                            'home_goal': m.home_goal,
                            'away_goal': m.away_goal,
                            'goal_difference': goal_diff,
                            'competition': m.competition or ''
                        })
            
            # Sort by goal difference
            victories.sort(key=lambda x: x['goal_difference'], reverse=True)
            victories = victories[:limit]
            
            data = []
            for i, v in enumerate(victories, 1):
                winner = v['home_team'] if v['home_goal'] > v['away_goal'] else v['away_team']
                loser = v['away_team'] if v['home_goal'] > v['away_goal'] else v['home_team']
                data.append({
                    'rank': i,
                    'date': v['date'],
                    'winner': winner,
                    'loser': loser,
                    'score': f"{v['home_goal']}-{v['away_goal']}",
                    'goal_difference': v['goal_difference'],
                    'competition': v['competition']
                })
            
            summary = f"Found {len(data)} big victories"
            if competition:
                summary += f" in {competition}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'competition': competition}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_average_goals_per_match(self, competition: Optional[str] = None, season: Optional[int] = None) -> QueryResult:
        """Calculate average goals per match."""
        try:
            matches = self.loader.matches
            
            if competition:
                matches = self.loader.get_matches_by_competition(competition)
            if season:
                matches = [m for m in matches if m.season == season]
            
            total_goals = 0
            valid_matches = 0
            
            for m in matches:
                if m.home_goal is not None and m.away_goal is not None:
                    total_goals += m.home_goal + m.away_goal
                    valid_matches += 1
            
            avg_goals = round(total_goals / valid_matches, 2) if valid_matches > 0 else 0
            
            home_wins = 0
            draws = 0
            away_wins = 0
            
            for m in matches:
                if m.home_goal is not None and m.away_goal is not None:
                    if m.home_goal > m.away_goal:
                        home_wins += 1
                    elif m.home_goal == m.away_goal:
                        draws += 1
                    else:
                        away_wins += 1
            
            home_win_rate = round((home_wins / valid_matches) * 100, 1) if valid_matches > 0 else 0
            
            return QueryResult(
                success=True,
                data=[{
                    'total_matches': valid_matches,
                    'total_goals': total_goals,
                    'average_goals_per_match': avg_goals,
                    'home_wins': home_wins,
                    'draws': draws,
                    'away_wins': away_wins,
                    'home_win_rate': f"{home_win_rate}%"
                }],
                summary=f"Average goals per match: {avg_goals} (from {valid_matches} matches)",
                count=1
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def _format_match_summary(self, matches: List[Match], team1: str, team2: str) -> str:
        """Format a summary of matches between two teams."""
        if not matches:
            return f"No matches found between {team1} and {team2}"
        
        from soccer_mcp.models import Match
        team1_normalized = self.loader.normalize_team_name(team1)
        team2_normalized = self.loader.normalize_team_name(team2)
        
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
                
            if team1_normalized.lower() in self.loader.normalize_team_name(m.home_team).lower():
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
        
        summary = f"{team1} vs {team2} head-to-head:\n"
        
        for m in matches[:5]:  # Show first 5 matches
            home_normalized = self.loader.normalize_team_name(m.home_team).lower()
            away_normalized = self.loader.normalize_team_name(m.away_team).lower()
            
            if team1_normalized in home_normalized:
                team1_score = m.home_goal
                team2_score = m.away_goal
                team1_location = 'home'
            else:
                team1_score = m.away_goal
                team2_score = m.home_goal
                team1_location = 'away'
            
            summary += f"- {m.datetime or m.date}: {team1} {team1_score}-{team2_score} {team2} ({m.competition or ''})"
            if m.round:
                summary += f" Round {m.round}"
            if m.season:
                summary += f" {m.season}"
            summary += "\n"
        
        if len(matches) > 5:
            summary += f"... and {len(matches) - 5} more matches\n"
        
        summary += f"\nHead-to-head record: {team1} {team1_wins} wins, {team2} {team2_wins} wins, {draws} draws"
        
        return summary


class PlayerQueries:
    """Handles player-related queries."""
    
    def __init__(self, loader: DataLoader):
        """Initialize with data loader."""
        self.loader = loader
    
    def search_player(self, name: str) -> QueryResult:
        """Search for a player by name."""
        try:
            players = []
            for p in self.loader.players:
                if p.name and name.lower() in p.name.lower():
                    players.append(p)
            
            if not players:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No players found matching '{name}'",
                    count=0
                )
            
            # Sort by overall rating
            players.sort(key=lambda p: p.overall or 0, reverse=True)
            
            data = []
            for p in players[:10]:  # Top 10 matches
                data.append({
                    'id': p.id,
                    'name': p.name or '',
                    'age': p.age,
                    'nationality': p.nationality or '',
                    'overall': p.overall,
                    'potential': p.potential,
                    'club': p.club or '',
                    'position': p.position or '',
                    'jersey_number': p.jersey_number,
                    'height': p.height or '',
                    'weight': p.weight or ''
                })
            
            summary = f"Found {len(players)} players matching '{name}'"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'search_term': name}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_players_by_club(self, club: str, limit: int = 20) -> QueryResult:
        """Get players by club."""
        try:
            players = self.loader.get_players_by_club(club)
            
            if not players:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No players found for club '{club}'",
                    count=0
                )
            
            # Sort by overall rating
            players.sort(key=lambda p: p.overall or 0, reverse=True)
            players = players[:limit]
            
            data = []
            for p in players:
                data.append({
                    'id': p.id,
                    'name': p.name or '',
                    'age': p.age,
                    'nationality': p.nationality or '',
                    'overall': p.overall,
                    'position': p.position or '',
                    'jersey_number': p.jersey_number
                })
            
            summary = f"Found {len(data)} players at {club}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'club': club}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_top_players(self, limit: int = 10) -> QueryResult:
        """Get top rated players."""
        try:
            sorted_players = sorted(self.loader.players, key=lambda p: p.overall or 0, reverse=True)
            top_players = sorted_players[:limit]
            
            data = []
            for p in top_players:
                data.append({
                    'rank': len(data) + 1,
                    'name': p.name or '',
                    'age': p.age,
                    'nationality': p.nationality or '',
                    'overall': p.overall,
                    'potential': p.potential,
                    'club': p.club or '',
                    'position': p.position or ''
                })
            
            summary = f"Top {len(data)} players in the dataset"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data)
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_brazilian_players(self, limit: int = 20) -> QueryResult:
        """Get Brazilian players."""
        try:
            brazilian_players = self.loader.get_brazilian_players()
            
            if not brazilian_players:
                return QueryResult(
                    success=True,
                    data=[],
                    summary="No Brazilian players found in the dataset",
                    count=0
                )
            
            # Sort by overall rating
            brazilian_players.sort(key=lambda p: p.overall or 0, reverse=True)
            brazilian_players = brazilian_players[:limit]
            
            data = []
            for p in brazilian_players:
                data.append({
                    'name': p.name or '',
                    'age': p.age,
                    'nationality': p.nationality or '',
                    'overall': p.overall,
                    'potential': p.potential,
                    'club': p.club or '',
                    'position': p.position or ''
                })
            
            summary = f"Found {len(data)} Brazilian players"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data)
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_players_by_position(self, position: str, limit: int = 10) -> QueryResult:
        """Get players by position."""
        try:
            position_lower = position.lower()
            players = [p for p in self.loader.players 
                      if p.position and position_lower in p.position.lower()]
            
            if not players:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No players found for position '{position}'",
                    count=0
                )
            
            players.sort(key=lambda p: p.overall or 0, reverse=True)
            players = players[:limit]
            
            data = []
            for p in players:
                data.append({
                    'name': p.name or '',
                    'age': p.age,
                    'nationality': p.nationality or '',
                    'overall': p.overall,
                    'club': p.club or '',
                    'position': p.position or ''
                })
            
            summary = f"Found {len(data)} players at {position}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'position': position}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_player_attributes(self, player_name: str) -> QueryResult:
        """Get detailed attributes for a player."""
        try:
            player = self.loader.get_player_by_name(player_name)
            
            if not player:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"Player '{player_name}' not found",
                    count=0
                )
            
            data = {
                'id': player.id,
                'name': player.name or '',
                'age': player.age,
                'nationality': player.nationality or '',
                'overall': player.overall,
                'potential': player.potential,
                'club': player.club or '',
                'position': player.position or '',
                'height': player.height or '',
                'weight': player.weight or '',
                'preferred_foot': player.preferred_foot or '',
                'skill_ratings': {
                    'crossing': player.crossing,
                    'finishing': player.finishing,
                    'heading_accuracy': player.heading_accuracy,
                    'short_passing': player.short_passing,
                    'volleys': player.volleys,
                    'dribbling': player.dribbling,
                    'curve': player.curve,
                    'fk_accuracy': player.fk_accuracy,
                    'long_passing': player.long_passing,
                    'ball_control': player.ball_control,
                    'acceleration': player.acceleration,
                    'sprint_speed': player.sprint_speed,
                    'agility': player.agility,
                    'reactions': player.reactions,
                    'balance': player.balance,
                    'shot_power': player.shot_power,
                    'jumping': player.jumping,
                    'stamina': player.stamina,
                    'strength': player.strength,
                    'long_shots': player.long_shots,
                    'aggression': player.aggression,
                    'interceptions': player.interceptions,
                    'positioning': player.positioning,
                    'vision': player.vision,
                    'penalties': player.penalties,
                    'composure': player.composure,
                    'marking': player.marking,
                    'standing_tackle': player.standing_tackle,
                    'sliding_tackle': player.sliding_tackle,
                    'gk_diving': player.gk_diving,
                    'gk_handling': player.gk_handling,
                    'gk_kicking': player.gk_kicking,
                    'gk_positioning': player.gk_positioning,
                    'gk_reflexes': player.gk_reflexes
                }
            }
            
            summary = f"Attributes for {player.name}"
            
            return QueryResult(
                success=True,
                data=[data],
                summary=summary,
                count=1,
                metadata={'player': player.name}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))


class CompetitionQueries:
    """Handles competition-related queries."""
    
    def __init__(self, loader: DataLoader):
        """Initialize with data loader."""
        self.loader = loader
    
    def get_competition_standings(self, competition: str, season: int) -> QueryResult:
        """Calculate standings for a competition."""
        try:
            matches = self.loader.get_matches_by_competition(competition)
            matches = [m for m in matches if m.season == season]
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for {competition} in season {season}",
                    count=0
                )
            
            # Calculate standings
            standings = defaultdict(lambda: {
                'team': '',
                'matches_played': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_difference': 0,
                'points': 0
            })
            
            for m in matches:
                if m.home_team and m.away_team and m.home_goal is not None and m.away_goal is not None:
                    home_team = self.loader.normalize_team_name(m.home_team)
                    away_team = self.loader.normalize_team_name(m.away_team)
                    
                    standings[home_team]['team'] = home_team
                    standings[home_team]['matches_played'] += 1
                    standings[home_team]['goals_for'] += m.home_goal
                    standings[home_team]['goals_against'] += m.away_goal
                    
                    standings[away_team]['team'] = away_team
                    standings[away_team]['matches_played'] += 1
                    standings[away_team]['goals_for'] += m.away_goal
                    standings[away_team]['goals_against'] += m.home_goal
                    
                    if m.home_goal > m.away_goal:
                        standings[home_team]['wins'] += 1
                        standings[home_team]['points'] += 3
                        standings[away_team]['losses'] += 1
                    elif m.home_goal < m.away_goal:
                        standings[away_team]['wins'] += 1
                        standings[away_team]['points'] += 3
                        standings[home_team]['losses'] += 1
                    else:
                        standings[home_team]['draws'] += 1
                        standings[home_team]['points'] += 1
                        standings[away_team]['draws'] += 1
                        standings[away_team]['points'] += 1
            
            # Calculate goal difference
            for team in standings.values():
                team['goal_difference'] = team['goals_for'] - team['goals_against']
            
            # Sort by points, then goal difference
            sorted_standings = sorted(
                standings.values(),
                key=lambda x: (x['points'], x['goal_difference']),
                reverse=True
            )
            
            data = []
            for i, team in enumerate(sorted_standings[:20], 1):  # Top 20
                data.append({
                    'rank': i,
                    'team': team['team'],
                    'matches_played': team['matches_played'],
                    'wins': team['wins'],
                    'draws': team['draws'],
                    'losses': team['losses'],
                    'goals_for': team['goals_for'],
                    'goals_against': team['goals_against'],
                    'goal_difference': team['goal_difference'],
                    'points': team['points']
                })
            
            summary = f"{competition} {season} Standings"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'competition': competition, 'season': season}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_competition_info(self, competition: str) -> QueryResult:
        """Get information about a competition."""
        try:
            matches = self.loader.get_matches_by_competition(competition)
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for {competition}",
                    count=0
                )
            
            # Get unique seasons
            seasons = set(m.season for m in matches if m.season)
            
            # Get unique teams
            teams = set()
            for m in matches:
                if m.home_team:
                    teams.add(self.loader.normalize_team_name(m.home_team))
                if m.away_team:
                    teams.add(self.loader.normalize_team_name(m.away_team))
            
            # Calculate total goals
            total_goals = sum((m.home_goal or 0) + (m.away_goal or 0) for m in matches)
            
            return QueryResult(
                success=True,
                data=[{
                    'competition': competition,
                    'seasons': sorted(list(seasons)),
                    'teams': len(teams),
                    'matches': len(matches),
                    'total_goals': total_goals
                }],
                summary=f"{competition}: {len(seasons)} seasons, {len(teams)} teams, {len(matches)} matches",
                count=1,
                metadata={'competition': competition}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_copa_libertadores_bracket(self, season: int) -> QueryResult:
        """Get Copa Libertadores bracket for a season."""
        try:
            matches = self.loader.get_matches_by_competition('Copa Libertadores')
            matches = [m for m in matches if m.season == season]
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for Copa Libertadores in season {season}",
                    count=0
                )
            
            # Group by stage
            stages = defaultdict(list)
            for m in matches:
                stage = m.stage or 'Unknown'
                stages[stage].append(m)
            
            data = []
            for stage, stage_matches in stages.items():
                data.append({
                    'stage': stage,
                    'matches': len(stage_matches),
                    'sample_matches': [
                        {
                            'home_team': m.home_team or '',
                            'away_team': m.away_team or '',
                            'home_goal': m.home_goal,
                            'away_goal': m.away_goal,
                            'date': m.datetime or m.date or ''
                        }
                        for m in stage_matches[:3]
                    ]
                })
            
            summary = f"Copa Libertadores {season} bracket"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'season': season}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_relegated_teams(self, season: int) -> QueryResult:
        """Get relegated teams from Brasileirao."""
        try:
            matches = self.loader.get_matches_by_competition('Brasileirao')
            matches = [m for m in matches if m.season == season]
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for Brasileirao in season {season}",
                    count=0
                )
            
            # Calculate standings
            standings = defaultdict(lambda: {
                'team': '',
                'matches_played': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_difference': 0,
                'points': 0
            })
            
            for m in matches:
                if m.home_team and m.away_team and m.home_goal is not None and m.away_goal is not None:
                    home_team = self.loader.normalize_team_name(m.home_team)
                    away_team = self.loader.normalize_team_name(m.away_team)
                    
                    standings[home_team]['team'] = home_team
                    standings[home_team]['matches_played'] += 1
                    standings[home_team]['goals_for'] += m.home_goal
                    standings[home_team]['goals_against'] += m.away_goal
                    
                    standings[away_team]['team'] = away_team
                    standings[away_team]['matches_played'] += 1
                    standings[away_team]['goals_for'] += m.away_goal
                    standings[away_team]['goals_against'] += m.home_goal
                    
                    if m.home_goal > m.away_goal:
                        standings[home_team]['wins'] += 1
                        standings[home_team]['points'] += 3
                        standings[away_team]['losses'] += 1
                    elif m.home_goal < m.away_goal:
                        standings[away_team]['wins'] += 1
                        standings[away_team]['points'] += 3
                        standings[home_team]['losses'] += 1
                    else:
                        standings[home_team]['draws'] += 1
                        standings[home_team]['points'] += 1
                        standings[away_team]['draws'] += 1
                        standings[away_team]['points'] += 1
            
            # Calculate goal difference
            for team in standings.values():
                team['goal_difference'] = team['goals_for'] - team['goals_against']
            
            # Sort by points, then goal difference
            sorted_standings = sorted(
                standings.values(),
                key=lambda x: (x['points'], x['goal_difference']),
                reverse=True
            )
            
            # Get relegated teams (last 4 in Brasileirao)
            relegated = sorted_standings[-4:]
            
            data = []
            for i, team in enumerate(reversed(relegated), 1):
                data.append({
                    'rank': len(sorted_standings) - i + 1,
                    'team': team['team'],
                    'matches_played': team['matches_played'],
                    'points': team['points'],
                    'goal_difference': team['goal_difference']
                })
            
            summary = f"Relegated from Brasileirao {season}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'season': season}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))


class TeamQueries:
    """Handles team-related queries."""
    
    def __init__(self, loader: DataLoader):
        """Initialize with data loader."""
        self.loader = loader
    
    def get_team_stats(self, team_name: str, season: Optional[int] = None, 
                       competition: Optional[str] = None) -> QueryResult:
        """Get comprehensive statistics for a team."""
        try:
            stats = self.loader.get_team_stats(team_name, season, competition)
            
            data = {
                'team_name': stats.team_name,
                'season': stats.season,
                'competition': stats.competition,
                'matches_played': stats.matches_played,
                'wins': stats.wins,
                'draws': stats.draws,
                'losses': stats.losses,
                'goals_for': stats.goals_for,
                'goals_against': stats.goals_against,
                'goal_difference': stats.goal_difference,
                'points': stats.points,
                'win_rate': f"{stats.win_rate}%",
                'home_record': {
                    'matches': stats.home_matches,
                    'wins': stats.home_wins,
                    'draws': stats.home_draws,
                    'losses': stats.home_losses
                },
                'away_record': {
                    'matches': stats.away_matches,
                    'wins': stats.away_wins,
                    'draws': stats.away_draws,
                    'losses': stats.away_losses
                }
            }
            
            summary = self._format_team_summary(stats)
            
            return QueryResult(
                success=True,
                data=[data],
                summary=summary,
                count=1,
                metadata={'team': team_name, 'season': season, 'competition': competition}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_team_head_to_head(self, team1: str, team2: str) -> QueryResult:
        """Get head-to-head record between two teams."""
        try:
            h2h = self.loader.get_head_to_head(team1, team2)
            
            summary = f"{team1} vs {team2} Head-to-Head:\n"
            summary += f"- Matches: {h2h['matches']}\n"
            summary += f"- {team1} wins: {h2h[f'{team1}_wins']}\n"
            summary += f"- {team2} wins: {h2h[f'{team2}_wins']}\n"
            summary += f"- Draws: {h2h['draws']}\n"
            
            return QueryResult(
                success=True,
                data=[h2h],
                summary=summary,
                count=1,
                metadata={'team1': team1, 'team2': team2}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_team_history(self, team_name: str, limit: int = 10) -> QueryResult:
        """Get recent matches for a team."""
        try:
            matches = self.loader.get_matches_by_team(team_name)
            matches.sort(key=lambda m: m.datetime or m.date or '', reverse=True)
            matches = matches[:limit]
            
            data = []
            for m in matches:
                data.append({
                    'date': m.datetime or m.date or '',
                    'home_team': m.home_team or '',
                    'away_team': m.away_team or '',
                    'home_goal': m.home_goal,
                    'away_goal': m.away_goal,
                    'competition': m.competition or '',
                    'round': m.round,
                    'season': m.season
                })
            
            summary = f"Recent matches for {team_name}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'team': team_name}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_best_teams(self, limit: int = 10, season: Optional[int] = None, 
                       competition: Optional[str] = None) -> QueryResult:
        """Get best performing teams."""
        try:
            # Get all teams and calculate stats
            team_stats = {}
            for m in self.loader.matches:
                if season and m.season != season:
                    continue
                if competition and m.competition != competition:
                    continue
                    
                if m.home_team and m.away_team:
                    home_team = self.loader.normalize_team_name(m.home_team)
                    away_team = self.loader.normalize_team_name(m.away_team)
                    
                    for team in [home_team, away_team]:
                        if team not in team_stats:
                            team_stats[team] = TeamStats(team_name=team)
                        
                        stats = team_stats[team]
                        stats.matches_played += 1
                        
                        if m.home_goal is not None and m.away_goal is not None:
                            if team.lower() in self.loader.normalize_team_name(m.home_team).lower():
                                stats.goals_for += m.home_goal
                                stats.goals_against += m.away_goal
                                if m.home_goal > m.away_goal:
                                    stats.wins += 1
                                    stats.points += 3
                                    stats.home_wins += 1
                                elif m.home_goal == m.away_goal:
                                    stats.draws += 1
                                    stats.points += 1
                                    stats.home_draws += 1
                                else:
                                    stats.losses += 1
                                    stats.home_losses += 1
                            else:
                                stats.goals_for += m.away_goal
                                stats.goals_against += m.home_goal
                                if m.away_goal > m.home_goal:
                                    stats.wins += 1
                                    stats.points += 3
                                    stats.away_wins += 1
                                elif m.away_goal == m.home_goal:
                                    stats.draws += 1
                                    stats.points += 1
                                    stats.away_draws += 1
                                else:
                                    stats.losses += 1
                                    stats.away_losses += 1
            
            # Sort by points
            sorted_teams = sorted(
                team_stats.values(),
                key=lambda t: t.points,
                reverse=True
            )[:limit]
            
            data = []
            for i, stats in enumerate(sorted_teams, 1):
                data.append({
                    'rank': i,
                    'team': stats.team_name,
                    'matches_played': stats.matches_played,
                    'wins': stats.wins,
                    'draws': stats.draws,
                    'losses': stats.losses,
                    'goals_for': stats.goals_for,
                    'goals_against': stats.goals_against,
                    'goal_difference': stats.goals_for - stats.goals_against,
                    'points': stats.points
                })
            
            summary = f"Top {len(data)} teams"
            if season:
                summary += f" in {season}"
            if competition:
                summary += f" in {competition}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'season': season, 'competition': competition}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_team_achievements(self, team_name: str) -> QueryResult:
        """Get achievements for a team."""
        try:
            # Find championship wins
            championships = defaultdict(int)
            
            matches = self.loader.get_matches_by_team(team_name)
            
            # Track unique seasons where team participated
            seasons_participated = set()
            for m in matches:
                if m.season:
                    seasons_participated.add(m.season)
            
            # Count Brasileirao wins
            brasileirao_matches = self.loader.get_matches_by_competition('Brasileirao')
            Brasileirao_champions = set()
            
            # Calculate Brasileirao champions
            for season in seasons_participated:
                season_matches = [m for m in brasileirao_matches if m.season == season]
                if len(season_matches) > 0:
                    # Simple champion detection - team with most points
                    standings = defaultdict(lambda: {'points': 0, 'gd': 0, 'team': ''})
                    for m in season_matches:
                        if m.home_team and m.away_team and m.home_goal is not None and m.away_goal is not None:
                            home_team = self.loader.normalize_team_name(m.home_team)
                            away_team = self.loader.normalize_team_name(m.away_team)
                            
                            standings[home_team]['team'] = home_team
                            standings[home_team]['points'] += 3 if m.home_goal > m.away_goal else (1 if m.home_goal == m.away_goal else 0)
                            standings[home_team]['gd'] += m.home_goal - m.away_goal
                            
                            standings[away_team]['team'] = away_team
                            standings[away_team]['points'] += 3 if m.away_goal > m.home_goal else (1 if m.away_goal == m.home_goal else 0)
                            standings[away_team]['gd'] += m.away_goal - m.home_goal
                    
                    sorted_standings = sorted(standings.values(), key=lambda x: (x['points'], x['gd']), reverse=True)
                    if sorted_standings:
                        Brasileirao_champions.add(sorted_standings[0]['team'])
            
            champion_count = sum(1 for t in Brasileirao_champions if self.loader.normalize_team_name(team_name).lower() in t.lower())
            
            data = {
                'team': team_name,
                'brasileirao_championships': champion_count,
                'seasons_participated': len(seasons_participated),
                'total_matches': len(matches)
            }
            
            summary = f"{team_name} Achievements:\n"
            summary += f"- Brasileirao Championships: {champion_count}\n"
            summary += f"- Seasons Participated: {len(seasons_participated)}\n"
            summary += f"- Total Matches: {len(matches)}"
            
            return QueryResult(
                success=True,
                data=[data],
                summary=summary,
                count=1,
                metadata={'team': team_name}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def _format_team_summary(self, stats: TeamStats) -> str:
        """Format a summary for team statistics."""
        summary = f"{stats.team_name} Statistics"
        if stats.season:
            summary += f" ({stats.season})"
        if stats.competition:
            summary += f" - {stats.competition}"
        summary += f":\n"
        summary += f"- Matches: {stats.matches_played}\n"
        summary += f"- Wins: {stats.wins}, Draws: {stats.draws}, Losses: {stats.losses}\n"
        summary += f"- Goals For: {stats.goals_for}, Goals Against: {stats.goals_against}\n"
        summary += f"- Goal Difference: {stats.goal_difference}, Points: {stats.points}\n"
        summary += f"- Win Rate: {stats.win_rate}%\n"
        summary += f"- Home Record: {stats.home_wins}W-{stats.home_draws}D-{stats.home_losses}L\n"
        summary += f"- Away Record: {stats.away_wins}W-{stats.away_draws}D-{stats.away_losses}L"
        
        return summary


class StatisticalAnalysis:
    """Handles statistical analysis queries."""
    
    def __init__(self, loader: DataLoader):
        """Initialize with data loader."""
        self.loader = loader
    
    def get_average_goals_per_match(self, competition: Optional[str] = None, 
                                    season: Optional[int] = None) -> QueryResult:
        """Calculate average goals per match."""
        try:
            matches = self.loader.matches
            
            if competition:
                matches = self.loader.get_matches_by_competition(competition)
            if season:
                matches = [m for m in matches if m.season == season]
            
            total_goals = 0
            valid_matches = 0
            
            for m in matches:
                if m.home_goal is not None and m.away_goal is not None:
                    total_goals += m.home_goal + m.away_goal
                    valid_matches += 1
            
            avg_goals = round(total_goals / valid_matches, 2) if valid_matches > 0 else 0
            
            home_wins = 0
            draws = 0
            away_wins = 0
            
            for m in matches:
                if m.home_goal is not None and m.away_goal is not None:
                    if m.home_goal > m.away_goal:
                        home_wins += 1
                    elif m.home_goal == m.away_goal:
                        draws += 1
                    else:
                        away_wins += 1
            
            home_win_rate = round((home_wins / valid_matches) * 100, 1) if valid_matches > 0 else 0
            
            return QueryResult(
                success=True,
                data=[{
                    'total_matches': valid_matches,
                    'total_goals': total_goals,
                    'average_goals_per_match': avg_goals,
                    'home_wins': home_wins,
                    'draws': draws,
                    'away_wins': away_wins,
                    'home_win_rate': f"{home_win_rate}%"
                }],
                summary=f"Average goals per match: {avg_goals} (from {valid_matches} matches)",
                count=1,
                metadata={'competition': competition, 'season': season}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_biggest_victories(self, competition: Optional[str] = None, limit: int = 10) -> QueryResult:
        """Find the biggest victories."""
        try:
            matches = self.loader.matches
            
            if competition:
                matches = self.loader.get_matches_by_competition(competition)
            
            # Filter matches with clear winners
            victories = []
            for m in matches:
                if m.home_goal is not None and m.away_goal is not None:
                    goal_diff = abs(m.home_goal - m.away_goal)
                    if goal_diff >= 3:  # Only include wins by 3+ goals
                        victories.append({
                            'date': m.datetime or m.date or '',
                            'home_team': m.home_team or '',
                            'away_team': m.away_team or '',
                            'home_goal': m.home_goal,
                            'away_goal': m.away_goal,
                            'goal_difference': goal_diff,
                            'competition': m.competition or ''
                        })
            
            # Sort by goal difference
            victories.sort(key=lambda x: x['goal_difference'], reverse=True)
            victories = victories[:limit]
            
            data = []
            for i, v in enumerate(victories, 1):
                winner = v['home_team'] if v['home_goal'] > v['away_goal'] else v['away_team']
                loser = v['away_team'] if v['home_goal'] > v['away_goal'] else v['home_team']
                data.append({
                    'rank': i,
                    'date': v['date'],
                    'winner': winner,
                    'loser': loser,
                    'score': f"{v['home_goal']}-{v['away_goal']}",
                    'goal_difference': v['goal_difference'],
                    'competition': v['competition']
                })
            
            summary = f"Found {len(data)} big victories"
            if competition:
                summary += f" in {competition}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'competition': competition}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_home_vs_away_performance(self, competition: Optional[str] = None) -> QueryResult:
        """Analyze home vs away performance."""
        try:
            matches = self.loader.matches
            
            if competition:
                matches = self.loader.get_matches_by_competition(competition)
            
            home_wins = 0
            home_draws = 0
            home_losses = 0
            away_wins = 0
            away_draws = 0
            away_losses = 0
            
            for m in matches:
                if m.home_goal is not None and m.away_goal is not None:
                    if m.home_goal > m.away_goal:
                        home_wins += 1
                        away_losses += 1
                    elif m.home_goal == m.away_goal:
                        home_draws += 1
                        away_draws += 1
                    else:
                        home_losses += 1
                        away_wins += 1
            
            total_home = home_wins + home_draws + home_losses
            total_away = away_wins + away_draws + away_losses
            
            home_win_rate = round((home_wins / total_home) * 100, 1) if total_home > 0 else 0
            away_win_rate = round((away_wins / total_away) * 100, 1) if total_away > 0 else 0
            
            return QueryResult(
                success=True,
                data=[{
                    'home_wins': home_wins,
                    'home_draws': home_draws,
                    'home_losses': home_losses,
                    'home_win_rate': f"{home_win_rate}%",
                    'away_wins': away_wins,
                    'away_draws': away_draws,
                    'away_losses': away_losses,
                    'away_win_rate': f"{away_win_rate}%"
                }],
                summary=f"Home vs Away Performance:\n"
                        f"Home: {home_wins}W-{home_draws}D-{home_losses}L ({home_win_rate}% win rate)\n"
                        f"Away: {away_wins}W-{away_draws}D-{away_losses}L ({away_win_rate}% win rate)",
                count=1,
                metadata={'competition': competition}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
    
    def get_top_scorers_by_season(self, season: int, limit: int = 10) -> QueryResult:
        """Get top scorers for a season (inferred from match data)."""
        try:
            matches = [m for m in self.loader.matches if m.season == season]
            
            if not matches:
                return QueryResult(
                    success=True,
                    data=[],
                    summary=f"No matches found for season {season}",
                    count=0
                )
            
            # Count goals per team
            team_goals = defaultdict(int)
            for m in matches:
                if m.home_goal is not None:
                    team_goals[self.loader.normalize_team_name(m.home_team)] += m.home_goal
                if m.away_goal is not None:
                    team_goals[self.loader.normalize_team_name(m.away_team)] += m.away_goal
            
            # Sort by goals
            sorted_teams = sorted(team_goals.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            data = []
            for i, (team, goals) in enumerate(sorted_teams, 1):
                data.append({
                    'rank': i,
                    'team': team,
                    'goals': goals
                })
            
            summary = f"Top Scoring Teams in Season {season}"
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                count=len(data),
                metadata={'season': season}
            )
        except Exception as e:
            return QueryResult(success=False, error=str(e))
