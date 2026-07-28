"""
Brazilian Soccer MCP Server
A Model Context Protocol server for Brazilian soccer data
"""

import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd
from fastapi import FastAPI
from mcp.server import Server
from mcp.types import TextContent, ImageContent, Tool
from pydantic import BaseModel, Field

# Get data directory path
DATA_DIR = Path(__file__).parent / "data" / "kaggle"


class TeamStats(BaseModel):
    """Team statistics model"""
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
    """Match result model"""
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
    """Player information model"""
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
    """Competition standings model"""
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
    """Big win record model"""
    date: str
    home_team: str
    away_team: str
    home_goal: int
    away_goal: int
    competition: str
    season: Optional[int] = None


class SoccerDataLoader:
    """Load and manage all soccer data"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.brasileirao_df = None
        self.copa_do_brasil_df = None
        self.libertadores_df = None
        self.br_football_df = None
        self.campeonato_brasileiro_df = None
        self.fifa_df = None
        self._load_all_data()

    def _load_all_data(self):
        """Load all CSV files"""
        print("Loading soccer data files...")
        
        # Brasileirão Serie A Matches
        brasileirao_path = self.data_dir / "Brasileirao_Matches.csv"
        if brasileirao_path.exists():
            self.brasileirao_df = pd.read_csv(brasileirao_path)
            self.brasileirao_df['competition'] = 'Brasileirão'
            print(f"  - Brasileirão: {len(self.brasileirao_df)} matches")

        # Copa do Brasil Matches
        copa_path = self.data_dir / "Brazilian_Cup_Matches.csv"
        if copa_path.exists():
            self.copa_do_brasil_df = pd.read_csv(copa_path)
            self.copa_do_brasil_df['competition'] = 'Copa do Brasil'
            print(f"  - Copa do Brasil: {len(self.copa_do_brasil_df)} matches")

        # Copa Libertadores Matches
        libertadores_path = self.data_dir / "Libertadores_Matches.csv"
        if libertadores_path.exists():
            self.libertadores_df = pd.read_csv(libertadores_path)
            self.libertadores_df['competition'] = 'Copa Libertadores'
            print(f"  - Copa Libertadores: {len(self.libertadores_df)} matches")

        # Extended Match Statistics
        br_football_path = self.data_dir / "BR-Football-Dataset.csv"
        if br_football_path.exists():
            self.br_football_df = pd.read_csv(br_football_path)
            print(f"  - BR Football Dataset: {len(self.br_football_df)} matches")

        # Historical Brasileirão (2003-2019)
        campeonato_path = self.data_dir / "novo_campeonato_brasileiro.csv"
        if campeonato_path.exists():
            # Read with latin1 encoding to handle special characters
            self.campeonato_brasileiro_df = pd.read_csv(
                campeonato_path, encoding='latin1', on_bad_lines='skip'
            )
            print(f"  - Campeonato Brasileiro 2003-2019: {len(self.campeonato_brasileiro_df)} matches")

        # FIFA Player Database
        fifa_path = self.data_dir / "fifa_data.csv"
        if fifa_path.exists():
            # Read with latin1 encoding to handle special characters
            self.fifa_df = pd.read_csv(fifa_path, encoding='latin1', on_bad_lines='skip')
            print(f"  - FIFA Players: {len(self.fifa_df)} players")
        
        print("Data loading complete!")

    def normalize_team_name(self, team: str) -> str:
        """Normalize team names for consistent matching"""
        if not team:
            return ""
        
        # Remove state suffix if present
        normalized = re.sub(r'-[A-Z]{2}$', '', str(team))
        normalized = normalized.strip()
        
        # Remove parentheses content for some team names
        normalized = re.sub(r'\s*\([^)]*\)\s*$', '', normalized)
        normalized = normalized.strip()
        
        return normalized

    def get_all_matches(self, 
                       home_team: Optional[str] = None,
                       away_team: Optional[str] = None,
                       competition: Optional[str] = None,
                       season: Optional[int] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> List[Dict]:
        """Get matches with optional filters"""
        matches = []
        
        # Combine all match dataframes
        dfs = [
            (self.brasileirao_df, 'Brasileirão'),
            (self.copa_do_brasil_df, 'Copa do Brasil'),
            (self.libertadores_df, 'Copa Libertadores'),
            (self.br_football_df, self.br_football_df.get('tournament', 'Unknown')),
            (self.campeonato_brasileiro_df, 'Brasileirão'),
        ]
        
        for df, comp_name in dfs:
            if df is None:
                continue
            
            for _, row in df.iterrows():
                # Normalize team names for comparison
                home = self._get_team_name(row, 'home')
                away = self._get_team_name(row, 'away')
                
                # Apply filters
                if home_team and home_team.lower() not in [home.lower(), self.normalize_team_name(home).lower()]:
                    continue
                if away_team and away_team.lower() not in [away.lower(), self.normalize_team_name(away).lower()]:
                    continue
                if competition and competition.lower() not in comp_name.lower():
                    continue
                
                # Season filter
                if season:
                    row_season = self._get_season(row)
                    if row_season != season:
                        continue
                
                # Date filters
                if date_from or date_to:
                    match_date = self._get_match_date(row)
                    if match_date:
                        if date_from and match_date < date_from:
                            continue
                        if date_to and match_date > date_to:
                            continue
                
                match = self._format_match(row, comp_name)
                matches.append(match)
        
        return matches

    def _get_team_name(self, row: pd.Series, side: str) -> str:
        """Extract team name from row"""
        side_lower = side.lower()
        
        # Check different column names
        if f'{side}_team' in row.index:
            return str(row[f'{side}_team'])
        elif side_lower in row.index:
            return str(row[side_lower])
        elif f'Equipe_{side}' in row.index:
            return str(row[f'Equipe_{side}'])
        elif f'{side}_team' in row.index:
            return str(row[f'{side}_team'])
        
        return ""

    def _get_season(self, row: pd.Series) -> Optional[int]:
        """Extract season year from row"""
        for col in ['season', 'Ano', 'Year']:
            if col in row.index and pd.notna(row[col]):
                try:
                    return int(row[col])
                except (ValueError, TypeError):
                    continue
        return None

    def _get_match_date(self, row: pd.Series) -> Optional[str]:
        """Extract and normalize match date"""
        for col in ['datetime', 'date', 'Data']:
            if col in row.index and pd.notna(row[col]):
                try:
                    date_val = str(row[col])
                    # Handle various date formats
                    if '/' in date_val:
                        # Brazilian format DD/MM/YYYY
                        parts = date_val.split('/')
                        if len(parts) == 3:
                            return f"{parts[2]}-{parts[1]}-{parts[0]}"
                    elif ' ' in date_val:
                        # ISO format with time
                        return date_val.split(' ')[0]
                    return date_val
                except Exception:
                    continue
        return None

    def _format_match(self, row: pd.Series, competition: str) -> Dict:
        """Format match data"""
        home_team = self._get_team_name(row, 'home')
        away_team = self._get_team_name(row, 'away')
        
        match = {
            'datetime': self._get_match_date(row) or '',
            'home_team': home_team,
            'away_team': away_team,
            'home_goal': self._get_goals(row, 'home'),
            'away_goal': self._get_goals(row, 'away'),
            'competition': competition,
            'season': self._get_season(row),
            'round': self._get_round(row),
            'stage': self._get_stage(row),
        }
        
        # Add extended stats if available
        if 'home_corner' in row.index:
            match['home_corner'] = row['home_corner']
        if 'away_corner' in row.index:
            match['away_corner'] = row['away_corner']
        if 'home_shots' in row.index:
            match['home_shots'] = row['home_shots']
        if 'away_shots' in row.index:
            match['away_shots'] = row['away_shots']
        
        return match

    def _get_goals(self, row: pd.Series, side: str) -> int:
        """Extract goals from row"""
        side_lower = side.lower()
        for col in [f'{side}_goal', f'{side_lower}_goal', f'Gols_{side}', f'{side}_goal']:
            if col in row.index:
                try:
                    val = row[col]
                    if pd.notna(val):
                        return int(float(val))
                except (ValueError, TypeError):
                    pass
        return 0

    def _get_round(self, row: pd.Series) -> Optional[int]:
        """Extract round from row"""
        for col in ['round', 'Rodada']:
            if col in row.index:
                try:
                    val = row[col]
                    if pd.notna(val):
                        return int(float(val))
                except (ValueError, TypeError):
                    pass
        return None

    def _get_stage(self, row: pd.Series) -> Optional[str]:
        """Extract stage from row"""
        for col in ['stage', 'Stage']:
            if col in row.index:
                val = row[col]
                if pd.notna(val):
                    return str(val)
        return None


class SoccerQueryEngine:
    """Query engine for soccer data"""

    def __init__(self, loader: SoccerDataLoader):
        self.loader = loader

    def find_matches_between_teams(self, team1: str, team2: str) -> List[MatchResult]:
        """Find all matches between two teams"""
        matches = self.loader.get_all_matches(home_team=team1, away_team=team2)
        
        # Also search in reverse
        reverse_matches = self.loader.get_all_matches(home_team=team2, away_team=team1)
        
        # Remove duplicates
        all_matches = matches + reverse_matches
        seen = set()
        unique_matches = []
        for match in all_matches:
            key = (match['home_team'], match['away_team'], match['datetime'])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        # Sort by date (most recent first)
        unique_matches.sort(key=lambda x: x['datetime'], reverse=True)
        
        return unique_matches

    def get_team_statistics(self, team: str, season: Optional[int] = None, 
                           competition: Optional[str] = None) -> TeamStats:
        """Get comprehensive team statistics"""
        matches = self.loader.get_all_matches(
            home_team=team, competition=competition, season=season
        )
        away_matches = self.loader.get_all_matches(
            away_team=team, competition=competition, season=season
        )
        
        # Combine home and away matches
        all_matches = matches + away_matches
        
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0
        
        for match in all_matches:
            is_home = match['home_team'].lower() == team.lower()
            
            if is_home:
                team_goals = match['home_goal']
                opponent_goals = match['away_goal']
            else:
                team_goals = match['away_goal']
                opponent_goals = match['home_goal']
            
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
        
        # Search for player name
        df = self.loader.fifa_df
        mask = df['Name'].str.contains(name, case=False, na=False)
        players = df[mask]
        
        if len(players) == 0:
            return None
        
        # Return the most relevant match
        row = players.iloc[0]
        
        return PlayerInfo(
            id=int(row['ID']) if 'ID' in row.index else 0,
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
        for _, row in players.head(50).iterrows():  # Limit to 50 players
            player = PlayerInfo(
                id=int(row['ID']) if 'ID' in row.index else 0,
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
            result.append(player)
        
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
            player = PlayerInfo(
                id=int(row['ID']) if 'ID' in row.index else 0,
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
            )
            result.append(player)
        
        return result

    def get_competition_standings(self, competition: str, season: int) -> List[CompetitionStandings]:
        """Calculate competition standings for a season"""
        matches = self.loader.get_all_matches(competition=competition, season=season)
        
        # Aggregate team statistics
        team_stats = {}
        
        for match in matches:
            home_team = match['home_team']
            away_team = match['away_team']
            home_goals = match['home_goal']
            away_goals = match['away_goal']
            
            # Initialize team stats if needed
            if home_team not in team_stats:
                team_stats[home_team] = {
                    'team': home_team,
                    'matches': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                }
            if away_team not in team_stats:
                team_stats[away_team] = {
                    'team': away_team,
                    'matches': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                }
            
            # Update stats
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
        
        # Calculate points and sort
        standings = []
        for team, stats in team_stats.items():
            points = stats['wins'] * 3 + stats['draws']
            standings.append({
                **stats,
                'goal_difference': stats['goals_for'] - stats['goals_against'],
                'points': points,
            })
        
        # Sort by points, then goal difference, then goals for
        standings.sort(
            key=lambda x: (x['points'], x['goal_difference'], x['goals_for']),
            reverse=True
        )
        
        # Add position
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
            
            # Calculate goal difference
            goal_diff = abs(home_goals - away_goals)
            
            # Only include wins with significant margin
            if goal_diff >= 4:
                if home_goals > away_goals:
                    winner = match['home_team']
                    loser = match['away_team']
                    winner_goals = home_goals
                    loser_goals = away_goals
                else:
                    winner = match['away_team']
                    loser = match['home_team']
                    winner_goals = away_goals
                    loser_goals = home_goals
                
                big_wins.append(BigWin(
                    date=match['datetime'],
                    home_team=match['home_team'],
                    away_team=match['away_team'],
                    home_goal=home_goals,
                    away_goal=away_goals,
                    competition=match['competition'],
                    season=match['season'],
                ))
        
        # Sort by goal difference and return top wins
        big_wins.sort(
            key=lambda x: abs(x.home_goal - x.away_goal),
            reverse=True
        )
        
        return big_wins[:limit]

    def get_head_to_head(self, team1: str, team2: str) -> Dict:
        """Get head-to-head record between two teams"""
        matches = self.find_matches_between_teams(team1, team2)
        
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        for match in matches:
            if match['home_team'].lower() == team1.lower():
                if match['home_goal'] > match['away_goal']:
                    team1_wins += 1
                elif match['home_goal'] < match['away_goal']:
                    team2_wins += 1
                else:
                    draws += 1
            else:
                if match['away_goal'] > match['home_goal']:
                    team1_wins += 1
                elif match['away_goal'] < match['home_goal']:
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
        }


class SoccerMCPServer:
    """Main MCP server class"""

    def __init__(self):
        self.data_loader = SoccerDataLoader(DATA_DIR)
        self.query_engine = SoccerQueryEngine(self.data_loader)
        self.app = FastAPI(title="Brazilian Soccer MCP Server")

    def create_tool(self, name: str, description: str, parameters: Dict) -> Tool:
        """Create an MCP tool"""
        return Tool(
            name=name,
            description=description,
            inputSchema=parameters,
        )

    def get_tools(self) -> List[Tool]:
        """Get all available tools"""
        return [
            self.create_tool(
                name="find_matches",
                description="Find matches by team, competition, season, or date range",
                parameters={
                    "type": "object",
                    "properties": {
                        "home_team": {"type": "string", "description": "Home team name"},
                        "away_team": {"type": "string", "description": "Away team name"},
                        "competition": {"type": "string", "description": "Competition name"},
                        "season": {"type": "integer", "description": "Season year"},
                        "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    },
                    "required": [],
                }
            ),
            self.create_tool(
                name="get_team_stats",
                description="Get comprehensive statistics for a team",
                parameters={
                    "type": "object",
                    "properties": {
                        "team": {"type": "string", "description": "Team name"},
                        "season": {"type": "integer", "description": "Season year (optional)"},
                        "competition": {"type": "string", "description": "Competition name (optional)"},
                    },
                    "required": ["team"],
                }
            ),
            self.create_tool(
                name="find_player",
                description="Find a player by name",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Player name or partial name"},
                    },
                    "required": ["name"],
                }
            ),
            self.create_tool(
                name="get_players_by_club",
                description="Get all players from a club",
                parameters={
                    "type": "object",
                    "properties": {
                        "club": {"type": "string", "description": "Club name"},
                    },
                    "required": ["club"],
                }
            ),
            self.create_tool(
                name="get_brazilian_players",
                description="Get all Brazilian players from the dataset",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
            ),
            self.create_tool(
                name="get_competition_standings",
                description="Get competition standings for a specific season",
                parameters={
                    "type": "object",
                    "properties": {
                        "competition": {"type": "string", "description": "Competition name"},
                        "season": {"type": "integer", "description": "Season year"},
                    },
                    "required": ["competition", "season"],
                }
            ),
            self.create_tool(
                name="get_big_wins",
                description="Get biggest wins in the dataset",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of results", "default": 10},
                    },
                    "required": [],
                }
            ),
            self.create_tool(
                name="get_head_to_head",
                description="Get head-to-head record between two teams",
                parameters={
                    "type": "object",
                    "properties": {
                        "team1": {"type": "string", "description": "First team name"},
                        "team2": {"type": "string", "description": "Second team name"},
                    },
                    "required": ["team1", "team2"],
                }
            ),
        ]

    async def handle_tool(self, name: str, arguments: Dict) -> Dict:
        """Handle tool calls"""
        try:
            if name == "find_matches":
                matches = self.query_engine.find_matches_between_teams(
                    arguments.get("home_team"), arguments.get("away_team")
                )
                return {"matches": matches}

            elif name == "get_team_stats":
                stats = self.query_engine.get_team_statistics(
                    arguments["team"],
                    arguments.get("season"),
                    arguments.get("competition"),
                )
                return stats.model_dump()

            elif name == "find_player":
                player = self.query_engine.get_player_by_name(arguments["name"])
                if player:
                    return player.model_dump()
                return {"error": "Player not found"}

            elif name == "get_players_by_club":
                players = self.query_engine.get_players_by_club(arguments["club"])
                return {"players": [p.model_dump() for p in players]}

            elif name == "get_brazilian_players":
                players = self.query_engine.get_brazilian_players()
                return {"players": [p.model_dump() for p in players]}

            elif name == "get_competition_standings":
                standings = self.query_engine.get_competition_standings(
                    arguments["competition"], arguments["season"]
                )
                return {"standings": [s.model_dump() for s in standings]}

            elif name == "get_big_wins":
                wins = self.query_engine.get_big_wins(arguments.get("limit", 10))
                return {"big_wins": [w.model_dump() for w in wins]}

            elif name == "get_head_to_head":
                h2h = self.query_engine.get_head_to_head(
                    arguments["team1"], arguments["team2"]
                )
                return h2h

            else:
                return {"error": f"Unknown tool: {name}"}

        except Exception as e:
            return {"error": str(e)}


# Create server instance
server = SoccerMCPServer()

# Create MCP server
mcp_server = Server("brazilian-soccer")

# Register tools
for tool in server.get_tools():
    mcp_server.tool()(tool)
