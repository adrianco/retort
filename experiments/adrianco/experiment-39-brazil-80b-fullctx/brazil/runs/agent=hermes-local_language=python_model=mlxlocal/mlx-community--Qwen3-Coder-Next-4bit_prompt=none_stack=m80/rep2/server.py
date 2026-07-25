#!/usr/bin/env python3
"""Brazilian Soccer MCP Server - Model Context Protocol server for Brazilian soccer data."""

import os
import re
import csv
from datetime import datetime
from typing import Any
from mcp.server import FastMCP
from mcp.types import TextContent

# Get the data directory path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data', 'kaggle')

# Load all CSV files
def load_csv(filename: str) -> list[dict]:
    """Load a CSV file and return a list of dictionaries."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        return list(reader)

# Load datasets
def load_all_data():
    """Load all soccer datasets."""
    data = {
        'brasileirao': load_csv('Brasileirao_Matches.csv'),
        'copa_brasil': load_csv('Brazilian_Cup_Matches.csv'),
        'libertadores': load_csv('Libertadores_Matches.csv'),
        'br_football': load_csv('BR-Football-Dataset.csv'),
        'brasileirao_2003_2019': load_csv('novo_campeonato_brasileiro.csv'),
        'fifa_players': load_csv('fifa_data.csv'),
    }
    return data

# Team name mapping for common variations
TEAM_NAME_MAP = {
    'flamengo': 'flamengo',
    'flamengo-rj': 'flamengo',
    'fluminense': 'fluminense',
    'fluminense-rj': 'fluminense',
    'palmeiras': 'palmeiras',
    'palmeiras-sp': 'palmeiras',
    'santos': 'santos',
    'santos-sp': 'santos',
    'corinthians': 'corinthians',
    'corinthians-sp': 'corinthians',
    'sao paulo': 'sao paulo',
    'sao paulo-sp': 'sao paulo',
    'gremio': 'gremio',
    'gremio-rs': 'gremio',
    'internacional': 'internacional',
    'internacional-rs': 'internacional',
    'botafogo': 'botafogo',
    'botafogo-rj': 'botafogo',
    'vasco': 'vasco',
    'vasco-da-gama': 'vasco',
    'vasco-da-gama-rj': 'vasco',
    'atletico-mg': 'atletico mineiro',
    'atletico-mg-mg': 'atletico mineiro',
    'atletico': 'atletico mineiro',
    'atletico mineiro': 'atletico mineiro',
    'bahia': 'bahia',
    'bahia-ba': 'bahia',
    'fortaleza': 'fortaleza',
    'fortaleza-ce': 'fortaleza',
    'ceara': 'ceara',
    'ceara-ce': 'ceara',
    'paysandu': 'paysandu',
    'paysandu-pa': 'paysandu',
    'parana': 'parana',
    'parana-pr': 'parana',
    'coritiba': 'coritiba',
    'coritiba-pr': 'coritiba',
    'goias': 'goias',
    'goias-go': 'goias',
    'vitoria': 'vitoria',
    'vitoria-ba': 'vitoria',
    'cruzeiro': 'cruzeiro',
    'cruzeiro-mg': 'cruzeiro',
    'america-mg': 'america mineiro',
    'america-mg-mg': 'america mineiro',
    'america': 'america mineiro',
    'america mineiro': 'america mineiro',
    'boca juniors': 'boca juniors',
    'boca': 'boca juniors',
    'nacional': 'nacional',
    'nacional (uru)': 'nacional',
    'barcelona': 'barcelona',
    'barcelona-equ': 'barcelona',
    'toluca': 'toluca',
    'newell old boys': 'newell old boys',
    'newell': 'newell old boys',
    'racing': 'racing',
    'racing club': 'racing',
    'racing-av': 'racing',
}

def normalize_team_name(name: str) -> str:
    """Normalize team name for matching with comprehensive mapping."""
    if not name:
        return ""
    name = str(name).lower().strip()
    # Remove state suffix if present
    name = re.sub(r'-[a-z]{2}$', '', name, flags=re.IGNORECASE)
    # Remove common suffixes
    name = re.sub(r'(\s+fc|\s+esporte\s+clube|\s+e\.c\.|\s+ac|sc|\s+clube|\s+esporte|\s+football\s+club)', '', name, flags=re.IGNORECASE)
    name = name.strip()
    # Use mapping if available
    return TEAM_NAME_MAP.get(name, name)

def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats."""
    if not date_str:
        return datetime.min
    
    date_str = str(date_str).strip()
    
    # Try various formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return datetime.min

def format_match_response(match: dict) -> str:
    """Format a match result for display."""
    home_team = match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', '')
    away_team = match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', '')
    home_goal = match.get('home_goal', '') or match.get('home_goal', '') or match.get('Gols_mandante', '')
    away_goal = match.get('away_goal', '') or match.get('away_goal', '') or match.get('Gols_visitante', '')
    date = match.get('datetime', '') or match.get('date', '') or match.get('Data', '')
    round_num = match.get('round', '') or match.get('Rodada', '') or match.get('stage', '')
    competition = match.get('competition', '')
    
    if date:
        date = date[:10] if len(date) >= 10 else date
    
    score = f"{home_goal}-{away_goal}" if home_goal and away_goal else "TBD"
    
    if round_num:
        return f"- {date}: {home_team} {score} {away_team} ({competition}, Round {round_num})"
    else:
        return f"- {date}: {home_team} {score} {away_team} ({competition})"

# Initialize FastMCP server
mcp = FastMCP(
    name="brazilian-soccer",
    instructions="A Brazilian Soccer MCP Server that provides a knowledge graph interface for Brazilian soccer data. You can query matches, teams, players, competitions, and calculate statistics."
)

@mcp.tool()
async def query_matches(
    team: str = "",
    opponent: str = "",
    date_from: str = "",
    date_to: str = "",
    competition: str = "",
    season: int | None = None,
    limit: int = 20
) -> list:
    """Query matches by team, date range, competition, or season.
    
    Args:
        team: Team name to search for
        opponent: Opponent team name
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        competition: Competition name (brasileirao, copa_brasil, Libertadores)
        season: Season year
        limit: Maximum results to return
    """
    data = load_all_data()
    results = []
    
    # Search across all match datasets
    match_files = ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'brasileirao_2003_2019']
    
    for file_key in match_files:
        if competition and file_key != competition:
            continue
            
        for match in data.get(file_key, []):
            # Normalize team names for comparison
            home_team = normalize_team_name(match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''))
            away_team = normalize_team_name(match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', ''))
            
            # Check team filter
            if team and team not in home_team and team not in away_team:
                continue
            
            # Check opponent filter
            if opponent and opponent not in home_team and opponent not in away_team:
                continue
            
            # Check season filter
            if season:
                match_season = match.get('season', '') or match.get('Ano', '')
                if str(match_season) != str(season):
                    continue
            
            # Build match result
            result = {
                'date': match.get('datetime', '') or match.get('date', '') or match.get('Data', ''),
                'home_team': match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''),
                'away_team': match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', ''),
                'home_goal': match.get('home_goal', '') or match.get('home_goal', '') or match.get('Gols_mandante', ''),
                'away_goal': match.get('away_goal', '') or match.get('away_goal', '') or match.get('Gols_visitante', ''),
                'competition': file_key.replace('_', ' ').title(),
                'round': match.get('round', '') or match.get('Rodada', '') or match.get('stage', ''),
            }
            
            # Parse date for filtering
            try:
                match_date = parse_date(result['date'])
                if date_from and match_date < parse_date(date_from):
                    continue
                if date_to and match_date > parse_date(date_to):
                    continue
            except:
                pass
            
            results.append(result)
            
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break
    
    # Format response
    response = f"Found {len(results)} matches:\n\n"
    for match in results[:limit]:
        response += format_match_response(match)
        response += "\n"
    
    return [TextContent(type="text", text=response)]

@mcp.tool()
async def query_team_stats(
    team: str,
    season: int | None = None,
    competition: str = ""
) -> list:
    """Get team statistics for a specific season.
    
    Args:
        team: Team name
        season: Season year
        competition: Competition name
    """
    data = load_all_data()
    
    if not team:
        return [TextContent(type="text", text="Error: Team name is required")]
    
    # Collect team stats from all match datasets
    stats = {
        'matches': 0,
        'wins': 0,
        'draws': 0,
        'losses': 0,
        'goals_for': 0,
        'goals_against': 0,
        'home_matches': 0,
        'away_matches': 0,
    }
    
    match_files = ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'brasileirao_2003_2019']
    
    for file_key in match_files:
        if competition and file_key != competition:
            continue
            
        for match in data.get(file_key, []):
            # Get team names
            home_team = normalize_team_name(match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''))
            away_team = normalize_team_name(match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', ''))
            
            # Check if team played
            is_home = team in home_team
            is_away = team in away_team
            
            if not is_home and not is_away:
                continue
            
            # Check season filter
            if season:
                match_season = match.get('season', '') or match.get('Ano', '')
                if str(match_season) != str(season):
                    continue
            
            stats['matches'] += 1
            
            # Get goals
            home_goal = int(match.get('home_goal', 0) or match.get('Gols_mandante', 0) or 0)
            away_goal = int(match.get('away_goal', 0) or match.get('Gols_visitante', 0) or 0)
            
            if is_home:
                stats['home_matches'] += 1
                stats['goals_for'] += home_goal
                stats['goals_against'] += away_goal
                if home_goal > away_goal:
                    stats['wins'] += 1
                elif home_goal == away_goal:
                    stats['draws'] += 1
                else:
                    stats['losses'] += 1
            else:
                stats['away_matches'] += 1
                stats['goals_for'] += away_goal
                stats['goals_against'] += home_goal
                if away_goal > home_goal:
                    stats['wins'] += 1
                elif away_goal == home_goal:
                    stats['draws'] += 1
                else:
                    stats['losses'] += 1
    
    # Format response
    response = f"Team Statistics for {team.title()}:\n\n"
    response += f"- Matches: {stats['matches']}\n"
    response += f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
    response += f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
    if stats['matches'] > 0:
        win_rate = (stats['wins'] / stats['matches']) * 100
        response += f"- Win rate: {win_rate:.1f}%\n"
    
    if stats['home_matches'] > 0 or stats['away_matches'] > 0:
        response += f"\nHome record: {stats['home_matches']} matches\n"
        response += f"Away record: {stats['away_matches']} matches\n"
    
    return [TextContent(type="text", text=response)]

@mcp.tool()
async def query_player(
    name: str = "",
    nationality: str = "",
    club: str = "",
    position: str = "",
    min_rating: int | None = None,
    limit: int = 20
) -> list:
    """Search for players by name, nationality, or club.
    
    Args:
        name: Player name (partial match)
        nationality: Nationality filter
        club: Club name filter
        position: Position filter
        min_rating: Minimum overall rating
        limit: Maximum results to return
    """
    data = load_all_data()
    players = data.get('fifa_players', [])
    results = []
    
    for player in players:
        player_name = player.get('Name', '').lower()
        player_nationality = player.get('Nationality', '').lower()
        player_club = player.get('Club', '').lower()
        player_position = player.get('Position', '').lower()
        player_overall = player.get('Overall', 0)
        
        # Check filters
        if name and name.lower() not in player_name:
            continue
        if nationality and nationality not in player_nationality:
            continue
        if club and club not in player_club:
            continue
        if position and position not in player_position:
            continue
        if min_rating and (not player_overall or int(player_overall) < min_rating):
            continue
        
        results.append({
            'name': player.get('Name', ''),
            'age': player.get('Age', ''),
            'nationality': player.get('Nationality', ''),
            'club': player.get('Club', ''),
            'position': player.get('Position', ''),
            'overall': player.get('Overall', ''),
            'potential': player.get('Potential', ''),
        })
        
        if len(results) >= limit:
            break
    
    # Sort by overall rating
    results.sort(key=lambda x: int(x['overall']) if x['overall'] else 0, reverse=True)
    
    # Format response
    response = f"Found {len(results)} players:\n\n"
    for player in results[:limit]:
        response += f"- {player['name']} ({player['position']}) - {player['club']}, Overall: {player['overall']}, Age: {player['age']}, {player['nationality']}\n"
    
    return [TextContent(type="text", text=response)]

@mcp.tool()
async def query_competition(
    competition: str,
    season: int | None = None,
    team: str = ""
) -> list:
    """Get competition information and standings.
    
    Args:
        competition: Competition name
        season: Season year
        team: Team name for standings
    """
    data = load_all_data()
    
    if not competition:
        return [TextContent(type="text", text="Error: Competition name is required")]
    
    # Determine match file
    match_files = {
        'brasileirao': 'brasileirao',
        'brasileirao serie a': 'brasileirao',
        'copa do brasil': 'copa_brasil',
        'libertadores': 'libertadores',
    }
    
    file_key = match_files.get(competition.lower(), competition.replace(' ', '_'))
    
    if file_key not in data:
        return [TextContent(type="text", text=f"Competition '{competition}' not found in data")]
    
    matches = data.get(file_key, [])
    results = []
    
    for match in matches:
        # Check season filter
        if season:
            match_season = match.get('season', '') or match.get('Ano', '')
            if str(match_season) != str(season):
                continue
        
        # Check team filter
        if team:
            home_team = normalize_team_name(match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''))
            away_team = normalize_team_name(match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', ''))
            if team.lower() not in home_team and team.lower() not in away_team:
                continue
        
        results.append(match)
    
    # Calculate standings if team requested
    if team:
        stats = {
            'matches': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
        }
        
        for match in results:
            home_team = normalize_team_name(match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''))
            away_team = normalize_team_name(match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', ''))
            
            is_home = team.lower() in home_team
            is_away = team.lower() in away_team
            
            if is_home or is_away:
                stats['matches'] += 1
                home_goal = int(match.get('home_goal', 0) or match.get('Gols_mandante', 0) or 0)
                away_goal = int(match.get('away_goal', 0) or match.get('Gols_visitante', 0) or 0)
                
                if is_home:
                    stats['goals_for'] += home_goal
                    stats['goals_against'] += away_goal
                    if home_goal > away_goal:
                        stats['wins'] += 1
                    elif home_goal == away_goal:
                        stats['draws'] += 1
                    else:
                        stats['losses'] += 1
                else:
                    stats['goals_for'] += away_goal
                    stats['goals_against'] += home_goal
                    if away_goal > home_goal:
                        stats['wins'] += 1
                    elif away_goal == home_goal:
                        stats['draws'] += 1
                    else:
                        stats['losses'] += 1
        
        response = f"Team Statistics for {team.title()} in {competition} {season}:\n\n"
        response += f"- Matches: {stats['matches']}\n"
        response += f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
        response += f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
        if stats['matches'] > 0:
            points = stats['wins'] * 3 + stats['draws']
            response += f"- Points: {points}\n"
            win_rate = (stats['wins'] / stats['matches']) * 100
            response += f"- Win rate: {win_rate:.1f}%\n"
    else:
        # Show match results
        response = f"Matches in {competition}:\n\n"
        for match in results[:20]:
            response += format_match_response(match)
            response += "\n"
    
    return [TextContent(type="text", text=response)]

@mcp.tool()
async def analyze_statistics(
    statistic_type: str,
    team1: str = "",
    team2: str = "",
    season: int | None = None,
    competition: str = "",
    limit: int = 10
) -> list:
    """Calculate aggregated statistics from match data.
    
    Args:
        statistic_type: Type of statistic (head_to_head, home_record, away_record, biggest_wins, avg_goals)
        team1: First team for head-to-head
        team2: Second team for head-to-head
        season: Season year
        competition: Competition name
        limit: Maximum results to return
    """
    data = load_all_data()
    
    if not statistic_type:
        return [TextContent(type="text", text="Error: Statistic type is required")]
    
    match_files = ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'brasileirao_2003_2019']
    
    # Collect all matches
    all_matches = []
    for file_key in match_files:
        if competition and file_key != competition:
            continue
        all_matches.extend(data.get(file_key, []))
    
    if statistic_type == 'head_to_head':
        if not team1 or not team2:
            return [TextContent(type="text", text="Error: Both team1 and team2 are required for head-to-head")]
        
        results = []
        for match in all_matches:
            home_team = normalize_team_name(match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''))
            away_team = normalize_team_name(match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', ''))
            
            if (team1.lower() in home_team and team2.lower() in away_team) or (team2.lower() in home_team and team1.lower() in away_team):
                results.append(match)
        
        # Count results
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        for match in results:
            home_team = normalize_team_name(match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''))
            away_team = normalize_team_name(match.get('away_team', '') or match.get('away', '') or match.get('Equipe_visitante', ''))
            home_goal = int(float(match.get('home_goal', 0) or match.get('Gols_mandante', 0) or 0))
            away_goal = int(float(match.get('away_goal', 0) or match.get('Gols_visitante', 0) or 0))
            
            if team1.lower() in home_team:
                if home_goal > away_goal:
                    team1_wins += 1
                elif home_goal == away_goal:
                    draws += 1
                else:
                    team2_wins += 1
            else:
                if away_goal > home_goal:
                    team1_wins += 1
                elif away_goal == home_goal:
                    draws += 1
                else:
                    team2_wins += 1
        
        response = f"Head-to-Head between {team1.title()} and {team2.title()}:\n\n"
        response += f"- {team1.title()} wins: {team1_wins}\n"
        response += f"- {team2.title()} wins: {team2_wins}\n"
        response += f"- Draws: {draws}\n"
        response += f"- Total matches: {len(results)}\n\n"
        
        response += "Recent matches:\n"
        for match in results[:5]:
            response += format_match_response(match)
            response += "\n"
    
    elif statistic_type == 'biggest_wins':
        results = []
        for match in all_matches:
            try:
                home_goal = int(float(match.get('home_goal', 0) or match.get('Gols_mandante', 0) or 0))
                away_goal = int(float(match.get('away_goal', 0) or match.get('Gols_visitante', 0) or 0))
            except:
                continue
            goal_diff = abs(home_goal - away_goal)
            if goal_diff >= 3:  # Only wins by 3+ goals
                results.append((goal_diff, match))
        
        results.sort(key=lambda x: x[0], reverse=True)
        
        response = f"Biggest wins in {'all competitions' if not competition else competition}:\n\n"
        for diff, match in results[:limit]:
            response += format_match_response(match)
            response += f" (Goal difference: {diff})\n"
    
    elif statistic_type == 'avg_goals':
        total_goals = 0
        total_matches = 0
        
        for match in all_matches:
            home_goal = match.get('home_goal', 0) or match.get('Gols_mandante', 0) or 0
            away_goal = match.get('away_goal', 0) or match.get('Gols_visitante', 0) or 0
            
            try:
                total_goals += int(float(home_goal)) + int(float(away_goal))
                total_matches += 1
            except:
                pass
        
        if total_matches > 0:
            avg_goals = total_goals / total_matches
            response = f"Average goals per match in {'all competitions' if not competition else competition}: {avg_goals:.2f}\n"
            response += f"Total matches analyzed: {total_matches}\n"
            response += f"Total goals scored: {total_goals}\n"
        else:
            response = "No matches found for this query."
    
    elif statistic_type == 'home_record':
        team_stats = {}
        
        for match in all_matches:
            if season:
                match_season = match.get('season', '') or match.get('Ano', '')
                if str(match_season) != str(season):
                    continue
            
            home_team = normalize_team_name(match.get('home_team', '') or match.get('home', '') or match.get('Equipe_mandante', ''))
            try:
                home_goal = int(float(match.get('home_goal', 0) or match.get('Gols_mandante', 0) or 0))
                away_goal = int(float(match.get('away_goal', 0) or match.get('Gols_visitante', 0) or 0))
            except:
                continue
            
            if home_team not in team_stats:
                team_stats[home_team] = {'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'gf': 0, 'ga': 0}
            
            team_stats[home_team]['matches'] += 1
            team_stats[home_team]['gf'] += home_goal
            team_stats[home_team]['ga'] += away_goal
            
            if home_goal > away_goal:
                team_stats[home_team]['wins'] += 1
            elif home_goal == away_goal:
                team_stats[home_team]['draws'] += 1
            else:
                team_stats[home_team]['losses'] += 1
        
        # Sort by win rate
        sorted_teams = sorted(
            [(k, v) for k, v in team_stats.items() if v['matches'] > 0],
            key=lambda x: (x[1]['wins'] / x[1]['matches'], x[1]['gf'] - x[1]['ga']),
            reverse=True
        )
        
        response = f"Best home records in {'all competitions' if not competition else competition}:\n\n"
        for i, (team, stats) in enumerate(sorted_teams[:limit], 1):
            win_rate = (stats['wins'] / stats['matches']) * 100
            response += f"{i}. {team.title()}: {stats['wins']}W-{stats['draws']}D-{stats['losses']}L ({win_rate:.1f}% win rate), GF:{stats['gf']} GA:{stats['ga']}\n"
    
    else:
        response = f"Unknown statistic type: {statistic_type}"
    
    return [TextContent(type="text", text=response)]

if __name__ == "__main__":
    # Run the server
    import asyncio
    
    async def run():
        # Start the server on port 8000
        await mcp.run_stdio_async()
    
    asyncio.run(run())
