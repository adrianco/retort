"""Query handlers for the Brazilian Soccer MCP server."""

import re
from typing import Optional
from datetime import datetime

import pandas as pd

from brazilian_soccer_mcp.data_loader import DataLoader, normalize_team_name


def _get_match_columns(df: pd.DataFrame) -> list[str]:
    """Return standardized match columns."""
    cols = ['date', 'home_team', 'away_team', 'home_goal', 'away_goal', 'competition']
    if 'season' in df.columns:
        cols.append('season')
    if 'round' in df.columns:
        cols.append('round')
    if 'stage' in df.columns:
        cols.append('stage')
    return [c for c in cols if c in df.columns]


def find_matches(
    loader: DataLoader,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Find matches by various criteria."""
    df = loader.all_matches().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    if team:
        team_norm = normalize_team_name(team).lower()
        mask = (
            df['home_team'].str.lower().str.contains(team_norm, na=False)
            | df['away_team'].str.lower().str.contains(team_norm, na=False)
        )
        df = df[mask]
    
    if opponent:
        opp_norm = normalize_team_name(opponent).lower()
        if team:
            mask = (
                (df['home_team'].str.lower().str.contains(opp_norm, na=False))
                & (df['away_team'].str.lower().str.contains(team_norm, na=False))
            ) | (
                (df['away_team'].str.lower().str.contains(opp_norm, na=False))
                & (df['home_team'].str.lower().str.contains(team_norm, na=False))
            )
        else:
            mask = df['home_team'].str.lower().str.contains(opp_norm, na=False) | df['away_team'].str.lower().str.contains(opp_norm, na=False)
        df = df[mask]
    
    if competition:
        comp_norm = competition.lower()
        mask = df['competition'].str.lower().str.contains(comp_norm, na=False, regex=False)
        df = df[mask]
    
    if season:
        df = df[df['season'] == season]
    
    if date_from:
        df = df[df['date'] >= pd.to_datetime(date_from)]
    
    if date_to:
        df = df[df['date'] <= pd.to_datetime(date_to)]
    
    df = df.head(limit)
    df = df.sort_values('date', ascending=False)
    
    results = []
    for _, row in df.iterrows():
        match = {
            'date': row['date'].strftime('%Y-%m-%d'),
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'home_goal': int(row['home_goal']),
            'away_goal': int(row['away_goal']),
            'competition': row.get('competition', 'Unknown'),
        }
        if 'round' in row and pd.notna(row['round']):
            match['round'] = int(row['round'])
        if 'season' in row and pd.notna(row['season']):
            match['season'] = int(row['season'])
        if 'stage' in row and pd.notna(row['stage']):
            match['stage'] = row['stage']
        results.append(match)
    
    return results


def get_team_statistics(
    loader: DataLoader,
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Get team match statistics."""
    df = loader.all_matches().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    team_norm = normalize_team_name(team).lower()
    match_mask = (
        df['home_team'].str.lower().str.contains(team_norm, na=False)
        | df['away_team'].str.lower().str.contains(team_norm, na=False)
    )
    df = df[match_mask]
    
    if competition:
        comp_norm = competition.lower()
        comp_mask = df['competition'].str.lower().str.contains(comp_norm, na=False, regex=False)
        df = df[comp_mask]
    
    if season:
        df = df[df['season'] == season]
    
    if df.empty:
        return {
            'team': team,
            'matches': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'win_rate': 0.0,
        }
    
    goals_for = 0
    goals_against = 0
    wins = 0
    draws = 0
    losses = 0
    
    for _, row in df.iterrows():
        home_norm = normalize_team_name(str(row['home_team'])).lower()
        is_home = home_norm == team_norm
        
        gf = int(row['home_goal'] if is_home else row['away_goal'])
        ga = int(row['away_goal'] if is_home else row['home_goal'])
        
        goals_for += gf
        goals_against += ga
        
        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1
    
    total = wins + draws + losses
    return {
        'team': team,
        'matches': total,
        'wins': int(wins),
        'draws': int(draws),
        'losses': int(losses),
        'goals_for': int(goals_for),
        'goals_against': int(goals_against),
        'win_rate': round(wins / total * 100, 1) if total > 0 else 0.0,
    }


def get_head_to_head(
    loader: DataLoader,
    team1: str,
    team2: str,
    competition: Optional[str] = None,
) -> dict:
    """Get head-to-head statistics between two teams."""
    df = loader.all_matches().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    t1_norm = normalize_team_name(team1).lower()
    t2_norm = normalize_team_name(team2).lower()
    
    mask = (
        ((df['home_team'].str.lower().str.contains(t1_norm, na=False))
         & (df['away_team'].str.lower().str.contains(t2_norm, na=False)))
        | ((df['home_team'].str.lower().str.contains(t2_norm, na=False))
           & (df['away_team'].str.lower().str.contains(t1_norm, na=False)))
    )
    df = df[mask]
    
    if competition:
        comp_norm = competition.lower()
        comp_mask = df['competition'].str.lower().str.contains(comp_norm, na=False, regex=False)
        df = df[comp_mask]
    
    t1_wins = 0
    t2_wins = 0
    draws = 0
    
    matches = []
    for _, row in df.iterrows():
        h_norm = normalize_team_name(str(row['home_team'])).lower()
        a_norm = normalize_team_name(str(row['away_team'])).lower()
        
        h_goals = int(row['home_goal'])
        a_goals = int(row['away_goal'])
        
        match_info = {
            'date': row['date'].strftime('%Y-%m-%d'),
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'home_goal': h_goals,
            'away_goal': a_goals,
            'competition': row.get('competition', 'Unknown'),
        }
        
        if 'season' in row and pd.notna(row.get('season')):
            match_info['season'] = int(row['season'])
        if 'round' in row and pd.notna(row.get('round')):
            match_info['round'] = int(row['round'])
        
        if h_norm == t1_norm:
            if h_goals > a_goals:
                t1_wins += 1
            elif h_goals == a_goals:
                draws += 1
            else:
                t2_wins += 1
        else:
            if a_goals > h_goals:
                t1_wins += 1
            elif a_goals == h_goals:
                draws += 1
            else:
                t2_wins += 1
        
        matches.append(match_info)
    
    return {
        'team1': team1,
        'team2': team2,
        'team1_wins': t1_wins,
        'team2_wins': t2_wins,
        'draws': draws,
        'total_matches': len(matches),
        'matches': matches,
    }


def search_players(
    loader: DataLoader,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_rating: Optional[int] = None,
    max_results: int = 50,
) -> list[dict]:
    """Search for players by various criteria."""
    df = loader.players.copy()
    
    if name:
        mask = df['name'].str.contains(name, case=False, na=False, regex=False)
        df = df[mask]
    
    if nationality:
        nat_norm = nationality.lower()
        mask = df['nationality'].str.contains(nat_norm, case=False, na=False, regex=False)
        df = df[mask]
    
    if club:
        club_norm = club.lower()
        mask = df['club'].str.contains(club_norm, case=False, na=False, regex=False)
        df = df[mask]
    
    if position:
        pos_norm = position.lower()
        mask = df['position'].str.lower().str.contains(pos_norm, na=False, regex=False)
        df = df[mask]
    
    if min_rating is not None:
        df = df[df['overall'] >= min_rating]
    
    df = df.sort_values('overall', ascending=False).head(max_results)
    
    results = []
    for _, row in df.iterrows():
        results.append({
            'name': row['name'],
            'age': int(row['age']) if pd.notna(row['age']) else None,
            'nationality': row['nationality'],
            'overall': int(row['overall']) if pd.notna(row['overall']) else None,
            'potential': int(row['potential']) if pd.notna(row['potential']) else None,
            'club': row['club'],
            'position': row['position'],
            'jersey_number': int(row['jersey_number']) if pd.notna(row.get('jersey_number')) else None,
        })
    
    return results


def get_standings(
    loader: DataLoader,
    competition: str,
    season: int,
) -> list[dict]:
    """Calculate standings for a competition and season."""
    df = loader.all_matches().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    comp_norm = competition.lower()
    comp_mask = df['competition'].str.lower().str.contains(comp_norm, na=False, regex=False)
    df = df[comp_mask]
    df = df[df['season'] == season]
    
    if df.empty:
        return []
    
    teams = {}
    
    for _, row in df.iterrows():
        home = normalize_team_name(str(row['home_team']))
        away = normalize_team_name(str(row['away_team']))
        h_goals = int(row['home_goal'])
        a_goals = int(row['away_goal'])
        
        for t in [home, away]:
            if t not in teams:
                teams[t] = {
                    'team': t,
                    'played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                    'points': 0,
                }
        
        teams[home]['played'] += 1
        teams[away]['played'] += 1
        teams[home]['goals_for'] += h_goals
        teams[home]['goals_against'] += a_goals
        teams[away]['goals_for'] += a_goals
        teams[away]['goals_against'] += h_goals
        
        if h_goals > a_goals:
            teams[home]['wins'] += 1
            teams[home]['points'] += 3
            teams[away]['losses'] += 1
        elif h_goals == a_goals:
            teams[home]['draws'] += 1
            teams[away]['draws'] += 1
            teams[home]['points'] += 1
            teams[away]['points'] += 1
        else:
            teams[away]['wins'] += 1
            teams[away]['points'] += 3
            teams[home]['losses'] += 1
    
    standings = list(teams.values())
    standings.sort(key=lambda x: (-x['points'], -(x['goals_for'] - x['goals_against']), -x['goals_for']))
    return standings


def get_biggest_wins(loader: DataLoader, limit: int = 10) -> list[dict]:
    """Find the biggest wins in the dataset."""
    df = loader.all_matches().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    df['goal_diff'] = (df['home_goal'] - df['away_goal']).abs()
    df = df[df['goal_diff'] >= 3].copy()
    df = df.sort_values('goal_diff', ascending=False).head(limit)
    
    results = []
    for _, row in df.iterrows():
        results.append({
            'date': row['date'].strftime('%Y-%m-%d'),
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'home_goal': int(row['home_goal']),
            'away_goal': int(row['away_goal']),
            'goal_diff': int(row['goal_diff']),
            'competition': row.get('competition', 'Unknown'),
        })
    
    return results


def get_average_goals(loader: DataLoader, competition: Optional[str] = None) -> dict:
    """Calculate average goals per match."""
    df = loader.all_matches().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    if competition:
        comp_norm = competition.lower()
        comp_mask = df['competition'].str.lower().str.contains(comp_norm, na=False, regex=False)
        df = df[comp_mask]
    
    total_goals = (df['home_goal'] + df['away_goal']).sum()
    total_matches = len(df)
    avg_goals = round(total_goals / total_matches, 2) if total_matches > 0 else 0
    
    home_wins = (df['home_goal'] > df['away_goal']).sum()
    away_wins = (df['home_goal'] < df['away_goal']).sum()
    draws = (df['home_goal'] == df['away_goal']).sum()
    
    return {
        'total_matches': total_matches,
        'total_goals': int(total_goals),
        'average_goals_per_match': avg_goals,
        'home_win_rate': round(home_wins / total_matches * 100, 1) if total_matches > 0 else 0,
        'away_win_rate': round(away_wins / total_matches * 100, 1) if total_matches > 0 else 0,
        'draw_rate': round(draws / total_matches * 100, 1) if total_matches > 0 else 0,
    }


def get_best_away_record(loader: DataLoader, limit: int = 10) -> list[dict]:
    """Find teams with best away records."""
    df = loader.all_matches().copy()
    df['date'] = pd.to_datetime(df['date'])
    
    teams = {}
    for _, row in df.iterrows():
        away = normalize_team_name(str(row['away_team']))
        if away not in teams:
            teams[away] = {'played': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'goals_for': 0, 'goals_against': 0}
        
        teams[away]['played'] += 1
        teams[away]['goals_for'] += int(row['away_goal'])
        teams[away]['goals_against'] += int(row['home_goal'])
        
        if int(row['away_goal']) > int(row['home_goal']):
            teams[away]['wins'] += 1
        elif int(row['away_goal']) == int(row['home_goal']):
            teams[away]['draws'] += 1
        else:
            teams[away]['losses'] += 1
    
    records = []
    for team, stats in teams.items():
        if stats['played'] >= 5:
            records.append({
                'team': team,
                'matches': stats['played'],
                'wins': stats['wins'],
                'draws': stats['draws'],
                'losses': stats['losses'],
                'goals_for': stats['goals_for'],
                'goals_against': stats['goals_against'],
                'win_rate': round(stats['wins'] / stats['played'] * 100, 1),
            })
    
    records.sort(key=lambda x: (-x['win_rate'], x['goals_for']))
    return records[:limit]


def get_brazilian_players_by_club(loader: DataLoader) -> dict:
    """Get Brazilian players grouped by club."""
    df = loader.players.copy()
    brazilian = df[df['nationality'].str.lower().str.contains('brazil', na=False)]
    
    club_groups = brazilian.groupby('club').agg(
        count=('name', 'size'),
        avg_rating=('overall', 'mean'),
    ).reset_index()
    club_groups['avg_rating'] = club_groups['avg_rating'].round(1)
    
    result = {}
    for _, row in club_groups.iterrows():
        result[row['club']] = {
            'count': int(row['count']),
            'avg_rating': float(row['avg_rating']),
        }
    
    return result


def get_team_names(loader: DataLoader) -> list[str]:
    """Get all unique team names from match data."""
    all_matches = loader.all_matches()
    teams = set()
    for col in ['home_team', 'away_team']:
        for team in all_matches[col].unique():
            teams.add(str(team))
    return sorted(teams)
