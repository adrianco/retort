#!/usr/bin/env python3
"""
Brazilian Soccer MCP Server
A Model Context Protocol server for Brazilian soccer data queries.
"""

import os
import re
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

# Load all data files
def load_data():
    """Load all CSV data files."""
    data = {}
    
    # 1. Brasileirão Serie A Matches
    try:
        data['brasileirao'] = pd.read_csv(os.path.join(DATA_DIR, "Brasileirao_Matches.csv"))
        print(f"Loaded Brasileirão: {len(data['brasileirao'])} matches")
    except Exception as e:
        print(f"Error loading Brasileirão: {e}")
    
    # 2. Copa do Brasil Matches
    try:
        data['copa_brasil'] = pd.read_csv(os.path.join(DATA_DIR, "Brazilian_Cup_Matches.csv"))
        print(f"Loaded Copa do Brasil: {len(data['copa_brasil'])} matches")
    except Exception as e:
        print(f"Error loading Copa do Brasil: {e}")
    
    # 3. Copa Libertadores Matches
    try:
        data['libertadores'] = pd.read_csv(os.path.join(DATA_DIR, "Libertadores_Matches.csv"))
        print(f"Loaded Libertadores: {len(data['libertadores'])} matches")
    except Exception as e:
        print(f"Error loading Libertadores: {e}")
    
    # 4. Extended Match Statistics
    try:
        data['br_football'] = pd.read_csv(os.path.join(DATA_DIR, "BR-Football-Dataset.csv"))
        print(f"Loaded BR Football: {len(data['br_football'])} matches")
    except Exception as e:
        print(f"Error loading BR Football: {e}")
    
    # 5. Historical Brasileirão (2003-2019)
    try:
        data['brasileirao_hist'] = pd.read_csv(os.path.join(DATA_DIR, "novo_campeonato_brasileiro.csv"), encoding='latin-1')
        print(f"Loaded Historical Brasileirão: {len(data['brasileirao_hist'])} matches")
    except Exception as e:
        print(f"Error loading Historical Brasileirão: {e}")
    
    # 6. FIFA Player Database
    try:
        data['fifa'] = pd.read_csv(os.path.join(DATA_DIR, "fifa_data.csv"))
        print(f"Loaded FIFA Players: {len(data['fifa'])} players")
    except Exception as e:
        print(f"Error loading FIFA Players: {e}")
    
    return data

# Create data instance
DATA = load_data()

# Team name normalization mapping
TEAM_NAME_MAPPING = {
    # Flamengo
    "flamengo": "Flamengo",
    "flamengo-rj": "Flamengo",
    "flamengo rj": "Flamengo",
    
    # Palmeiras
    "palmeiras": "Palmeiras",
    "palmeiras-sp": "Palmeiras",
    "palmeiras sp": "Palmeiras",
    
    # São Paulo
    "são paulo": "São Paulo",
    "sao paulo": "São Paulo",
    "são paulo-sp": "São Paulo",
    "sao paulo sp": "São Paulo",
    
    # Corinthians
    "corinthians": "Corinthians",
    "corinthians-sp": "Corinthians",
    "corinthians sp": "Corinthians",
    "sport club corinthians paulista": "Corinthians",
    
    # Palmeiras variants
    "sc palmeiras": "Palmeiras",
    
    # Santos
    "santos": "Santos",
    "santos-sp": "Santos",
    "santos sp": "Santos",
    
    # Grêmio
    "grêmio": "Grêmio",
    "gremio": "Grêmio",
    "grêmio-rs": "Grêmio",
    "gremio rs": "Grêmio",
    
    # Fluminense
    "fluminense": "Fluminense",
    "fluminense-rj": "Fluminense",
    "fluminense rj": "Fluminense",
    
    # Botafogo
    "botafogo": "Botafogo",
    "botafogo-rj": "Botafogo",
    "botafogo rj": "Botafogo",
    
    # Cruzeiro
    "cruzeiro": "Cruzeiro",
    "cruzeiro-mg": "Cruzeiro",
    "cruzeiro mg": "Cruzeiro",
    
    # Athletico-PR
    "athletico-pr": "Athletico-PR",
    "athletico pr": "Athletico-PR",
    "athletico paranaense": "Athletico-PR",
    
    # Atlético-MG
    "atlético-mg": "Atlético-MG",
    "atletico-mg": "Atlético-MG",
    "atletico mg": "Atlético-MG",
    "atlético mineiro": "Atlético-MG",
    "atletico mineiro": "Atlético-MG",
}

def normalize_team_name(team: str) -> str:
    """Normalize team names to a standard format."""
    if not team:
        return ""
    team_lower = str(team).lower().strip()
    
    # Remove common suffixes
    team_lower = re.sub(r'-[a-z]{2}$', '', team_lower, flags=re.IGNORECASE)
    team_lower = re.sub(r' sp$', '', team_lower)
    team_lower = re.sub(r' rj$', '', team_lower)
    team_lower = re.sub(r' pr$', '', team_lower)
    team_lower = re.sub(r' mg$', '', team_lower)
    team_lower = re.sub(r' rs$', '', team_lower)
    
    # Check mapping
    if team_lower in TEAM_NAME_MAPPING:
        return TEAM_NAME_MAPPING[team_lower]
    
    # Try to match partial
    for key, value in TEAM_NAME_MAPPING.items():
        if key in team_lower or team_lower in key:
            return value
    
    # Return original with proper capitalization
    return team.strip()

def get_team_matches(df: pd.DataFrame, team: str, home_col='home_team', away_col='away_team') -> pd.DataFrame:
    """Get all matches for a team."""
    team_norm = normalize_team_name(team)
    mask = (
        df[home_col].apply(lambda x: normalize_team_name(str(x)) == team_norm) |
        df[away_col].apply(lambda x: normalize_team_name(str(x)) == team_norm)
    )
    return df[mask].copy()

def get_head_to_head(df: pd.DataFrame, team1: str, team2: str) -> Dict[str, Any]:
    """Get head-to-head record between two teams."""
    team1_norm = normalize_team_name(team1)
    team2_norm = normalize_team_name(team2)
    
    mask = (
        ((df['home_team'].apply(lambda x: normalize_team_name(str(x)) == team1_norm) &
          df['away_team'].apply(lambda x: normalize_team_name(str(x)) == team2_norm)) |
         (df['home_team'].apply(lambda x: normalize_team_name(str(x)) == team2_norm) &
          df['away_team'].apply(lambda x: normalize_team_name(str(x)) == team1_norm)))
    )
    
    matches = df[mask].copy()
    
    if len(matches) == 0:
        return {
            "team1": team1,
            "team2": team2,
            "total_matches": 0,
            "team1_wins": 0,
            "team2_wins": 0,
            "draws": 0,
            "matches": []
        }
    
    # Determine winner for each match
    def get_result(row):
        home = normalize_team_name(str(row['home_team']))
        away = normalize_team_name(str(row['away_team']))
        # Handle NaN values for goals
        if 'home_goal' in row and pd.notna(row.get('home_goal')):
            home_goals = int(row['home_goal'])
            away_goals = int(row['away_goal'])
        elif 'home' in row and pd.notna(row.get('home')):
            home_goals = int(row['home'])
            away_goals = int(row['away'])
        else:
            return 'draw'  # Default to draw if missing data
        
        if home == team1_norm:
            if home_goals > away_goals:
                return 'team1'
            elif home_goals < away_goals:
                return 'team2'
            else:
                return 'draw'
        else:
            if away_goals > home_goals:
                return 'team1'
            elif away_goals < home_goals:
                return 'team2'
            else:
                return 'draw'
    
    matches['result'] = matches.apply(get_result, axis=1)
    
    team1_wins = len(matches[matches['result'] == 'team1'])
    team2_wins = len(matches[matches['result'] == 'team2'])
    draws = len(matches[matches['result'] == 'draw'])
    
    # Format matches
    formatted_matches = []
    for _, row in matches.iterrows():
        formatted_matches.append(format_match(row, team1_norm, team2_norm))
    
    return {
        "team1": team1,
        "team2": team2,
        "total_matches": len(matches),
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "draws": draws,
        "matches": formatted_matches
    }

def format_match(row: pd.Series, team1_norm: str = None, team2_norm: str = None) -> Dict[str, Any]:
    """Format a match record for output."""
    result = {}
    
    # Date
    if 'datetime' in row:
        result['date'] = str(row['datetime']).split(' ')[0] if pd.notna(row['datetime']) else ''
    elif 'date' in row:
        result['date'] = str(row['date'])
    else:
        result['date'] = ''
    
    # Teams
    home = normalize_team_name(str(row.get('home_team', row.get('home', ''))))
    away = normalize_team_name(str(row.get('away_team', row.get('away', ''))))
    result['home_team'] = home
    result['away_team'] = away
    
    # Scores
    if 'home_goal' in row:
        result['home_score'] = int(row['home_goal']) if pd.notna(row['home_goal']) else 0
        result['away_score'] = int(row['away_goal']) if pd.notna(row['away_goal']) else 0
    elif 'home' in row and 'away' in row:
        result['home_score'] = int(row['home']) if pd.notna(row['home']) else 0
        result['away_score'] = int(row['away']) if pd.notna(row['away']) else 0
    else:
        result['home_score'] = 0
        result['away_score'] = 0
    
    result['total_score'] = f"{result['home_score']}-{result['away_score']}"
    
    # Competition
    if 'season' in row:
        result['season'] = int(row['season']) if pd.notna(row['season']) else ''
    if 'round' in row:
        result['round'] = str(row['round'])
    if 'stage' in row:
        result['stage'] = str(row['stage'])
    if 'tournament' in row:
        result['tournament'] = str(row['tournament'])
    
    return result

def calculate_team_stats(matches: pd.DataFrame, team: str) -> Dict[str, Any]:
    """Calculate statistics for a team from matches."""
    team_norm = normalize_team_name(team)
    
    if len(matches) == 0:
        return {
            "team": team,
            "total_matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "win_rate": 0.0
        }
    
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0
    
    for _, row in matches.iterrows():
        home = normalize_team_name(str(row.get('home_team', row.get('home', ''))))
        away = normalize_team_name(str(row.get('away_team', row.get('away', ''))))
        
        # Handle NaN values for goals
        if 'home_goal' in row and pd.notna(row.get('home_goal')):
            home_goals = int(row['home_goal'])
            away_goals = int(row['away_goal'])
        elif 'home' in row and pd.notna(row.get('home')):
            home_goals = int(row['home'])
            away_goals = int(row['away'])
        else:
            continue  # Skip rows with missing goal data
        
        if home == team_norm:
            goals_for += home_goals
            goals_against += away_goals
            if home_goals > away_goals:
                wins += 1
            elif home_goals == away_goals:
                draws += 1
            else:
                losses += 1
        else:
            goals_for += away_goals
            goals_against += home_goals
            if away_goals > home_goals:
                wins += 1
            elif away_goals == home_goals:
                draws += 1
            else:
                losses += 1
    
    total_matches = wins + draws + losses
    
    return {
        "team": team,
        "total_matches": total_matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "win_rate": round(wins / total_matches * 100, 1) if total_matches > 0 else 0.0
    }

# FastAPI app
app = FastAPI(
    title="Brazilian Soccer MCP Server",
    description="Model Context Protocol server for Brazilian soccer data queries",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class MatchQuery(BaseModel):
    team1: Optional[str] = None
    team2: Optional[str] = None
    season: Optional[int] = None
    competition: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: Optional[int] = 50

class TeamQuery(BaseModel):
    team: str
    season: Optional[int] = None
    competition: Optional[str] = None

class PlayerQuery(BaseModel):
    name: Optional[str] = None
    nationality: Optional[str] = None
    club: Optional[str] = None
    position: Optional[str] = None
    min_overall: Optional[int] = None
    limit: Optional[int] = 50

class CompetitionQuery(BaseModel):
    competition: str
    season: int
    limit: Optional[int] = 20

class StatisticalQuery(BaseModel):
    metric: str  # "average_goals", "home_record", "biggest_wins", "top_scorers"
    competition: Optional[str] = None
    season: Optional[int] = None


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Brazilian Soccer MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for Brazilian soccer data queries",
        "endpoints": [
            "/matches", "/teams", "/players", "/competitions", "/stats"
        ],
        "data_loaded": len(DATA) > 0
    }


@app.post("/matches")
async def query_matches(query: MatchQuery):
    """Query matches by criteria."""
    results = []
    
    # Combine all match data
    all_matches = []
    for key, df in DATA.items():
        if key in ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'brasileirao_hist']:
            all_matches.append(df)
    
    if not all_matches:
        return {"error": "No match data loaded", "matches": []}
    
    combined = pd.concat(all_matches, ignore_index=True)
    
    # Apply filters
    if query.team1:
        combined = get_team_matches(combined, query.team1)
    if query.team2:
        combined = get_team_matches(combined, query.team2)
    
    if query.season:
        if 'season' in combined.columns:
            combined = combined[combined['season'] == query.season]
    
    if query.competition:
        for col in ['tournament', 'competition', 'round']:
            if col in combined.columns:
                mask = combined[col].apply(lambda x: query.competition.lower() in str(x).lower())
                combined = combined[mask]
    
    # Limit results
    combined = combined.head(query.limit or 50)
    
    # Format matches
    for _, row in combined.iterrows():
        results.append(format_match(row))
    
    return {
        "query": query.dict(),
        "total_matches": len(results),
        "matches": results
    }


@app.post("/teams")
async def query_teams(query: TeamQuery):
    """Query team information and statistics."""
    # Combine all match data
    all_matches = []
    for key, df in DATA.items():
        if key in ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'brasileirao_hist']:
            all_matches.append(df)
    
    if not all_matches:
        return {"error": "No match data loaded", "team": query.team}
    
    combined = pd.concat(all_matches, ignore_index=True)
    
    # Get team matches
    team_matches = get_team_matches(combined, query.team)
    
    # Calculate stats
    stats = calculate_team_stats(team_matches, query.team)
    
    # Filter by season if specified
    if query.season and 'season' in combined.columns:
        season_matches = combined[combined['season'] == query.season]
        season_stats = calculate_team_stats(season_matches, query.team)
    else:
        season_stats = None
    
    # Find head-to-head opponents
    opponents = set()
    for _, row in team_matches.iterrows():
        home = normalize_team_name(str(row.get('home_team', row.get('home', ''))))
        away = normalize_team_name(str(row.get('away_team', row.get('away', ''))))
        team_norm = normalize_team_name(query.team)
        if home != team_norm:
            opponents.add(home)
        if away != team_norm:
            opponents.add(away)
    
    return {
        "team": query.team,
        "statistics": stats,
        "season_statistics": season_stats,
        "opponents": list(opponents)[:20],
        "matches": [format_match(row) for _, row in team_matches.head(20).iterrows()]
    }


@app.post("/players")
async def query_players(query: PlayerQuery):
    """Query player information."""
    if 'fifa' not in DATA:
        return {"error": "FIFA player data not loaded", "players": []}
    
    df = DATA['fifa']
    results = df.copy()
    
    # Apply filters
    if query.name:
        results = results[results['Name'].str.contains(query.name, case=False, na=False)]
    
    if query.nationality:
        results = results[results['Nationality'].str.contains(query.nationality, case=False, na=False)]
    
    if query.club:
        results = results[results['Club'].str.contains(query.club, case=False, na=False)]
    
    if query.position:
        results = results[results['Position'].str.contains(query.position, case=False, na=False)]
    
    if query.min_overall:
        results = results[results['Overall'] >= query.min_overall]
    
    # Sort by overall rating
    if 'Overall' in results.columns:
        results = results.sort_values('Overall', ascending=False)
    
    # Limit results
    results = results.head(query.limit or 50)
    
    # Format players
    players = []
    for _, row in results.iterrows():
        player = {
            "name": row.get('Name', ''),
            "age": int(row['Age']) if pd.notna(row.get('Age')) else None,
            "nationality": row.get('Nationality', ''),
            "overall": int(row['Overall']) if pd.notna(row.get('Overall')) else None,
            "potential": int(row['Potential']) if pd.notna(row.get('Potential')) else None,
            "club": row.get('Club', ''),
            "position": row.get('Position', ''),
            "jersey_number": int(row['Jersey Number']) if pd.notna(row.get('Jersey Number')) else None,
            "height": row.get('Height', ''),
            "weight": row.get('Weight', '')
        }
        players.append(player)
    
    return {
        "query": query.dict(),
        "total_players": len(players),
        "players": players
    }


@app.post("/competitions")
async def query_competitions(query: CompetitionQuery):
    """Query competition information and standings."""
    # Find matches for the competition
    all_matches = []
    for key, df in DATA.items():
        if key in ['brasileirao', 'copa_brasil', 'libertadores', 'brasileirao_hist']:
            all_matches.append(df)
    
    if not all_matches:
        return {"error": "No match data loaded", "competition": query.competition}
    
    combined = pd.concat(all_matches, ignore_index=True)
    
    # Filter by competition and season
    mask = combined['season'] == query.season
    
    # Try to match competition name
    for col in ['tournament', 'round', 'stage', 'competition']:
        if col in combined.columns:
            competition_mask = combined[col].apply(lambda x: query.competition.lower() in str(x).lower())
            mask = mask & competition_mask
    
    competition_matches = combined[mask].copy()
    
    if len(competition_matches) == 0:
        return {
            "competition": query.competition,
            "season": query.season,
            "matches_found": 0,
            "standings": []
        }
    
    # Calculate standings
    standings = calculate_standings(competition_matches)
    
    # Find top scorers (if we have goals data)
    top_scorers = calculate_top_scorers(competition_matches)
    
    # Format matches
    formatted_matches = [format_match(row) for _, row in competition_matches.head(50).iterrows()]
    
    return {
        "competition": query.competition,
        "season": query.season,
        "total_matches": len(competition_matches),
        "standings": standings,
        "top_scorers": top_scorers,
        "matches": formatted_matches
    }


def calculate_standings(matches: pd.DataFrame) -> List[Dict[str, Any]]:
    """Calculate league standings from match data."""
    team_stats = {}
    
    for _, row in matches.iterrows():
        home = normalize_team_name(str(row.get('home_team', row.get('home', ''))))
        away = normalize_team_name(str(row.get('away_team', row.get('away', ''))))
        
        if 'home_goal' in row:
            home_goals = int(row['home_goal'])
            away_goals = int(row['away_goal'])
        else:
            home_goals = int(row.get('home', 0))
            away_goals = int(row.get('away', 0))
        
        for team, goals_for, goals_against in [(home, home_goals, away_goals), 
                                                  (away, away_goals, home_goals)]:
            if team not in team_stats:
                team_stats[team] = {
                    "team": team,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "for": 0,
                    "against": 0,
                    "points": 0
                }
            
            team_stats[team]["played"] += 1
            team_stats[team]["for"] += goals_for
            team_stats[team]["against"] += goals_against
            
            if goals_for > goals_against:
                team_stats[team]["won"] += 1
                team_stats[team]["points"] += 3
            elif goals_for == goals_against:
                team_stats[team]["drawn"] += 1
                team_stats[team]["points"] += 1
            else:
                team_stats[team]["lost"] += 1
    
    # Sort by points
    standings = sorted(team_stats.values(), key=lambda x: x["points"], reverse=True)
    return standings[:20]  # Top 20


def calculate_top_scorers(matches: pd.DataFrame) -> List[Dict[str, Any]]:
    """Calculate top scorers from match data (inferred from goals)."""
    scorers = {}
    
    for _, row in matches.iterrows():
        home = normalize_team_name(str(row.get('home_team', row.get('home', ''))))
        away = normalize_team_name(str(row.get('away_team', row.get('away', ''))))
        
        if 'home_goal' in row:
            home_goals = int(row['home_goal'])
            away_goals = int(row['away_goal'])
        else:
            home_goals = int(row.get('home', 0))
            away_goals = int(row.get('away', 0))
        
        # Inferred scorers (team goals)
        if home not in scorers:
            scorers[home] = {"team": home, "goals": 0}
        scorers[home]["goals"] += home_goals
        
        if away not in scorers:
            scorers[away] = {"team": away, "goals": 0}
        scorers[away]["goals"] += away_goals
    
    top_scorers = sorted(scorers.values(), key=lambda x: x["goals"], reverse=True)[:10]
    return top_scorers


@app.post("/stats")
async def query_stats(query: StatisticalQuery):
    """Query statistical information."""
    # Combine all match data
    all_matches = []
    for key, df in DATA.items():
        if key in ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'brasileirao_hist']:
            all_matches.append(df)
    
    if not all_matches:
        return {"error": "No match data loaded"}
    
    combined = pd.concat(all_matches, ignore_index=True)
    
    # Filter by competition if specified
    if query.competition:
        for col in ['tournament', 'round', 'stage', 'competition']:
            if col in combined.columns:
                mask = combined[col].apply(lambda x: query.competition.lower() in str(x).lower())
                combined = combined[mask]
    
    # Filter by season if specified
    if query.season and 'season' in combined.columns:
        combined = combined[combined['season'] == query.season]
    
    # Calculate requested metric
    if query.metric == "average_goals":
        total_goals = 0
        total_matches = 0
        
        for _, row in combined.iterrows():
            if 'home_goal' in row:
                total_goals += int(row['home_goal']) + int(row['away_goal'])
            elif 'home' in row and 'away' in row:
                total_goals += int(row['home']) + int(row['away'])
            total_matches += 1
        
        avg_goals = total_goals / total_matches if total_matches > 0 else 0
        
        return {
            "metric": "average_goals",
            "total_matches": total_matches,
            "total_goals": total_goals,
            "average_goals_per_match": round(avg_goals, 2)
        }
    
    elif query.metric == "home_record":
        home_wins = 0
        home_draws = 0
        home_losses = 0
        
        for _, row in combined.iterrows():
            if 'home_goal' in row:
                home_goals = int(row['home_goal'])
                away_goals = int(row['away_goal'])
            else:
                home_goals = int(row.get('home', 0))
                away_goals = int(row.get('away', 0))
            
            if home_goals > away_goals:
                home_wins += 1
            elif home_goals == away_goals:
                home_draws += 1
            else:
                home_losses += 1
        
        total = home_wins + home_draws + home_losses
        win_rate = (home_wins / total * 100) if total > 0 else 0
        
        return {
            "metric": "home_record",
            "total_matches": total,
            "home_wins": home_wins,
            "home_draws": home_draws,
            "home_losses": home_losses,
            "win_rate": round(win_rate, 1)
        }
    
    elif query.metric == "biggest_wins":
        # Find biggest victories
        results = []
        for _, row in combined.iterrows():
            if 'home_goal' in row:
                home_goals = int(row['home_goal'])
                away_goals = int(row['away_goal'])
            else:
                home_goals = int(row.get('home', 0))
                away_goals = int(row.get('away', 0))
            
            goal_diff = abs(home_goals - away_goals)
            if goal_diff >= 3:  # Big wins only
                results.append({
                    "date": str(row.get('datetime', row.get('date', ''))).split(' ')[0],
                    "home_team": normalize_team_name(str(row.get('home_team', row.get('home', '')))),
                    "away_team": normalize_team_name(str(row.get('away_team', row.get('away', '')))),
                    "score": f"{home_goals}-{away_goals}",
                    "goal_difference": goal_diff
                })
        
        # Sort by goal difference and limit
        results.sort(key=lambda x: x["goal_difference"], reverse=True)
        results = results[:20]
        
        return {
            "metric": "biggest_wins",
            "total_matches": len(results),
            "biggest_wins": results
        }
    
    elif query.metric == "top_scorers":
        return calculate_top_scorers(combined)
    
    return {"error": f"Unknown metric: {query.metric}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
