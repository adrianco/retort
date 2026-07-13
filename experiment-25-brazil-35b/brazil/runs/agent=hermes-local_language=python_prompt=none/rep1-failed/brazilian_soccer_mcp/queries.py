"""
Query handlers for Brazilian Soccer MCP Server.

Provides functions to search and analyze loaded datasets:
  - Match queries (search by team, date, competition, season)
  - Team queries (statistics, records, performance)
  - Player queries (search, filter by nationality/club)
  - Competition queries (standings, top scorers)
  - Statistical analysis (averages, trends, biggest wins)
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import re
import unicodedata
from datetime import datetime


_CLUB_ALIASES = {
    "flamengo": "Flamengo",
    "palmeiras": "Palmeiras",
    "santos": "Santos",
    "saopaulo": "Sao Paulo",
    "sao paulo": "Sao Paulo",
    "corinthians": "Corinthians",
    "atletico": "Atletico Mineiro",
    "atletico mineiro": "Atletico Mineiro",
    "gremio": "Gremio",
    "grenio": "Gremio",
    "internacional": "Internacional",
    "inter": "Internacional",
    "cruzeiro": "Cruzeiro",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "botafogo": "Botafogo",
    "fluminense": "Fluminense",
    "bahia": "Bahia",
    "ceara": "Ceara",
    "fortaleza": "Fortaleza",
    "sport": "Sport Recife",
    "sport recife": "Sport Recife",
    "coritiba": "Coritiba",
    "atletico pr": "Atletico Paranaense",
    "atletico paranaense": "Atletico Paranaense",
    "athletico pr": "Atletico Paranaense",
    "goias": "Goias",
    "america mineiro": "America Mineiro",
    "america mg": "America Mineiro",
    "nautico": "Nautico",
    "juventude": "Juventude",
    "cuiaba": "Cuiaba",
    "vitoria": "Vitoria",
    "ponte preta": "Ponte Preta",
    "bragantino": "Red Bull Bragantino",
    "red bull bragantino": "Red Bull Bragantino",
    "chapecoense": "Chapecoense",
    "chapeco": "Chapecoense",
    "guarani": "Guarani",
    "gama": "Gama",
    "fluminense rj": "Fluminense",
    "figueirense": "Figueirense",
}


def normalize_team_name(name):
    """Normalize a team name by stripping state suffixes, parens, etc."""
    if not name or not isinstance(name, str):
        return ""
    name = name.strip()
    # Remove parenthetical descriptions first to get cleaner name
    name = re.sub(r'\(.*?\)\s*-?\s*\w+\s*$', '', name)
    name = re.sub(r'\(.*?\)', '', name).strip()
    # Remove state suffix like -SP, -RJ, -MG, -PR, -SC, -PE, -DF, -CE, -ES
    name = re.sub(r'\s*-\s*[A-Z]{2}\s*$', '', name)
    # Normalize unicode
    name = unicodedata.normalize('NFKD', name)
    name = ' '.join(name.split())
    return name


def find_best_match(raw_name):
    """Try to resolve a raw team name to a canonical club name."""
    if not raw_name:
        return ""
    normalized = normalize_team_name(raw_name)
    name_lower = normalized.lower()

    # Direct lookup match (prefer exact key match)
    if name_lower in _CLUB_ALIASES:
        return _CLUB_ALIASES[name_lower]

    # Check if the name contains a multi-word alias exactly (e.g. "ao paulo" in "sao paulo")
    # Sort aliases by length (descending) to prefer longer matches
    for alias in sorted(_CLUB_ALIASES.keys(), key=len, reverse=True):
        canonical = _CLUB_ALIASES[alias]
        # Check if the alias itself is a substring of the name
        # But also ensure we don't match short common words
        if len(alias) >= 4 and alias in name_lower:
            return canonical

    return normalized


def parse_date(date_str):
    """Parse various date formats into ISO format YYYY-MM-DD."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        pass
    return None


def _compute_team_stats(matches, team):
    """Compute wins/draws/losses and goals for a team from their matches."""
    if matches.empty:
        return {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "win_rate": 0.0}
    total = len(matches)
    home_mask = matches['home_team'] == team
    away_mask = matches['away_team'] == team
    hg, ag = matches['home_goals'], matches['away_goals']
    h_w = int((home_mask & (hg > ag)).sum())
    h_d = int((home_mask & (hg == ag)).sum())
    a_w = int((away_mask & (ag > hg)).sum())
    a_d = int((away_mask & (ag == hg)).sum())
    wins = h_w + a_w
    draws = h_d + a_d
    losses = total - wins - draws
    gf = int(matches.loc[home_mask, 'home_goals'].sum() + matches.loc[away_mask, 'away_goals'].sum())
    ga = int(matches.loc[home_mask, 'away_goals'].sum() + matches.loc[away_mask, 'home_goals'].sum())
    return {
        "matches": total, "wins": wins, "draws": draws, "losses": losses,
        "goals_for": gf, "goals_against": ga,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
    }


def _compute_h2h(all_matches, team_a, team_b):
    """Compute head-to-head between two teams."""
    mask = ((all_matches['home_team'] == team_a) & (all_matches['away_team'] == team_b)) | \
           ((all_matches['home_team'] == team_b) & (all_matches['away_team'] == team_a))
    matches = all_matches[mask].copy()
    if matches.empty:
        return {"team_a": team_a, "team_b": team_b, "matches": 0,
                "team_a_wins": 0, "team_b_wins": 0, "draws": 0, "matches_list": []}
    results = []
    for _, row in matches.iterrows():
        if row['home_team'] == team_a:
            if row['home_goals'] > row['away_goals']: results.append('a')
            elif row['home_goals'] < row['away_goals']: results.append('b')
            else: results.append('d')
        else:
            if row['away_goals'] > row['home_goals']: results.append('a')
            elif row['away_goals'] < row['home_goals']: results.append('b')
            else: results.append('d')
    a_wins = results.count('a')
    b_wins = results.count('b')
    draws = results.count('d')
    match_rows = []
    for _, row in matches.iterrows():
        match_rows.append({
            "date": row['date'], "home": row['home_team'], "away": row['away_team'],
            "home_goals": int(row['home_goals']), "away_goals": int(row['away_goals']),
            "source": row['source'],
            "season": int(row['season']) if pd.notna(row['season']) else None,
            "round": int(row['round']) if pd.notna(row['round']) else None,
        })
    return {
        "team_a": team_a, "team_b": team_b,
        "matches": len(matches), "team_a_wins": a_wins, "team_b_wins": b_wins, "draws": draws,
        "matches_list": match_rows,
    }


# --- Match queries ---

def search_matches(all_matches, team=None, date_from=None, date_to=None,
                   competition=None, season=None, limit=50):
    mask = pd.Series([True] * len(all_matches), index=all_matches.index)
    if team:
        mask &= ((all_matches['home_team'] == team) | (all_matches['away_team'] == team))
    if date_from:
        mask &= (all_matches['date'] >= date_from)
    if date_to:
        mask &= (all_matches['date'] <= date_to)
    if competition:
        mask &= all_matches['source'].str.contains(competition, case=False, na=False)
    if season is not None:
        mask &= (all_matches['season'] == season)
    results = all_matches[mask].head(limit)
    rows = []
    for _, r in results.iterrows():
        rows.append({
            "date": r['date'], "season": int(r['season']) if pd.notna(r['season']) else None,
            "round": int(r['round']) if pd.notna(r['round']) else None,
            "stage": r['stage'] if r['stage'] else None,
            "competition": r['source'],
            "home_team": r['home_team'], "away_team": r['away_team'],
            "home_goals": int(r['home_goals']), "away_goals": int(r['away_goals']),
        })
    return {"total_found": int(len(results)), "matches": rows}


def find_matches_between(all_matches, team_a, team_b, limit=100):
    mask = ((all_matches['home_team'] == team_a) & (all_matches['away_team'] == team_b)) | \
           ((all_matches['home_team'] == team_b) & (all_matches['away_team'] == team_a))
    matches = all_matches[mask].sort_values('date', ascending=False)
    matches = matches.head(limit)
    rows = []
    for _, r in matches.iterrows():
        rows.append({
            "date": r['date'], "season": int(r['season']) if pd.notna(r['season']) else None,
            "round": int(r['round']) if pd.notna(r['round']) else None,
            "competition": r['source'],
            "home_team": r['home_team'], "away_team": r['away_team'],
            "home_goals": int(r['home_goals']), "away_goals": int(r['away_goals']),
        })
    return {"total_found": len(matches), "matches": rows}


def get_h2h(all_matches, team_a, team_b, limit=100):
    result = _compute_h2h(all_matches, team_a, team_b)
    if result['matches_list']:
        result['matches_list'] = result['matches_list'][:limit]
    return result


def get_biggest_wins(all_matches, competition=None, limit=10):
    df = all_matches.copy()
    df['goal_diff'] = (df['home_goals'] - df['away_goals']).abs()
    if competition:
        df = df[df['source'].str.contains(competition, case=False, na=False)]
    df = df.sort_values('goal_diff', ascending=False).head(limit)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": r['date'], "season": int(r['season']) if pd.notna(r['season']) else None,
            "competition": r['source'],
            "home_team": r['home_team'], "away_team": r['away_team'],
            "home_goals": int(r['home_goals']), "away_goals": int(r['away_goals']),
            "goal_difference": int(r['goal_diff']),
        })
    return {"matches": rows}


# --- Team queries ---

def get_team_stats(all_matches, team, season=None, competition=None,
                   home_only=False, away_only=False):
    mask = ((all_matches['home_team'] == team) | (all_matches['away_team'] == team))
    team_matches = all_matches[mask].copy()
    if season is not None:
        team_matches = team_matches[team_matches['season'] == season]
    if competition:
        team_matches = team_matches[team_matches['source'].str.contains(competition, case=False, na=False)]
    if home_only:
        team_matches = team_matches[team_matches['home_team'] == team]
    if away_only:
        team_matches = team_matches[team_matches['away_team'] == team]
    stats = _compute_team_stats(team_matches, team)
    comp_stats = {}
    if not team_matches.empty:
        for comp, grp in team_matches.groupby('source'):
            comp_stats[comp] = _compute_team_stats(grp, team)
    return {"team": team, "overall": stats, "by_competition": comp_stats}


def get_team_matches(all_matches, team, season=None, competition=None,
                     limit=20, order="desc"):
    mask = ((all_matches['home_team'] == team) | (all_matches['away_team'] == team))
    team_matches = all_matches[mask].copy()
    if season is not None:
        team_matches = team_matches[team_matches['season'] == season]
    if competition:
        team_matches = team_matches[team_matches['source'].str.contains(competition, case=False, na=False)]
    team_matches = team_matches.sort_values('date', ascending=(order == "asc"))
    team_matches = team_matches.head(limit)
    rows = []
    for _, r in team_matches.iterrows():
        rows.append({
            "date": r['date'], "season": int(r['season']) if pd.notna(r['season']) else None,
            "round": int(r['round']) if pd.notna(r['round']) else None,
            "competition": r['source'],
            "home_team": r['home_team'], "away_team": r['away_team'],
            "home_goals": int(r['home_goals']), "away_goals": int(r['away_goals']),
        })
    return {"team": team, "total_matches": len(team_matches), "matches": rows}


def get_competition_leaderboard(all_matches, competition, season=None):
    comp_matches = all_matches[all_matches['source'].str.contains(competition, case=False, na=False)].copy()
    if season is not None:
        comp_matches = comp_matches[comp_matches['season'] == season]
    if comp_matches.empty:
        return {"competition": competition, "season": season, "standings": []}
    teams = set(comp_matches['home_team'].unique()) | set(comp_matches['away_team'].unique())
    standings = {}
    for t in teams:
        standings[t] = {"team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0,
                        "goals_for": 0, "goals_against": 0, "goal_difference": 0, "points": 0}
    for _, r in comp_matches.iterrows():
        h, a, hg, ag = r['home_team'], r['away_team'], r['home_goals'], r['away_goals']
        for t in [h, a]:
            standings[t]["played"] += 1
        standings[h]["goals_for"] += hg
        standings[h]["goals_against"] += ag
        standings[a]["goals_for"] += ag
        standings[a]["goals_against"] += hg
        if hg > ag:
            standings[h]["won"] += 1; standings[h]["points"] += 3
            standings[a]["lost"] += 1
        elif hg < ag:
            standings[a]["won"] += 1; standings[a]["points"] += 3
            standings[h]["lost"] += 1
        else:
            standings[h]["drawn"] += 1; standings[a]["drawn"] += 1
            standings[h]["points"] += 1; standings[a]["points"] += 1
    for t in standings.values():
        t["goal_difference"] = t["goals_for"] - t["goals_against"]
    standings_list = sorted(standings.values(), key=lambda x: (-x["points"], -x["goal_difference"], -x["goals_for"]))
    return {"competition": competition, "season": int(season) if season else None, "standings": standings_list[:20]}


# --- Player queries ---

def search_players(fifa_df, name=None, nationality=None, club=None,
                   position=None, min_overall=None, limit=20):
    mask = pd.Series([True] * len(fifa_df), index=fifa_df.index)
    if name:
        mask &= fifa_df['Name'].str.contains(name, case=False, na=False)
    if nationality:
        mask &= fifa_df['Nationality'].str.contains(nationality, case=False, na=False)
    if club:
        mask &= fifa_df['Club'].str.contains(club, case=False, na=False)
    if position:
        mask &= fifa_df['Position'].str.contains(position, case=False, na=False)
    if min_overall is not None:
        mask &= (fifa_df['Overall'] >= min_overall)
    # Use sort_values instead of nlargest (pandas 3.0 compatibility)
    results = fifa_df[mask].sort_values('Overall', ascending=False).head(limit)
    rows = []
    for _, r in results.iterrows():
        rows.append({
            "name": r['Name'], "age": int(r['Age']),
            "nationality": r['Nationality'], "overall": int(r['Overall']),
            "potential": int(r['Potential']), "club": r['Club'],
            "position": r['Position'],
            "jersey_number": int(r['Jersey Number']) if pd.notna(r['Jersey Number']) else None,
            "height": r['Height'], "weight": r['Weight'],
        })
    return {"total_found": len(results), "players": rows}


def get_brazilian_players(fifa_df, limit=50):
    mask = fifa_df['Nationality'].str.contains('Brazil', case=False, na=False)
    results = fifa_df[mask].sort_values('Overall', ascending=False).head(limit)
    rows = []
    for _, r in results.iterrows():
        rows.append({
            "name": r['Name'], "age": int(r['Age']),
            "overall": int(r['Overall']), "potential": int(r['Potential']),
            "club": r['Club'], "position": r['Position'],
        })
    return {"total_found": len(results), "players": rows}


def get_players_by_club(fifa_df, club, nationality=None, limit=20):
    mask = fifa_df['Club'].str.contains(club, case=False, na=False)
    if nationality:
        mask &= fifa_df['Nationality'].str.contains(nationality, case=False, na=False)
    results = fifa_df[mask].sort_values('Overall', ascending=False).head(limit)
    rows = []
    for _, r in results.iterrows():
        rows.append({
            "name": r['Name'], "age": int(r['Age']),
            "nationality": r['Nationality'], "overall": int(r['Overall']),
            "position": r['Position'],
        })
    return {"club": club, "total_found": len(results), "players": rows}


# --- Stats queries ---

def get_average_goals(all_matches, competition=None):
    df = all_matches.copy()
    if competition:
        df = df[df['source'].str.contains(competition, case=False, na=False)]
    if df.empty:
        return {"competition": competition, "avg_total_goals": 0, "avg_home_goals": 0,
                "avg_away_goals": 0, "total_matches": 0, "home_win_rate": 0}
    total = len(df)
    avg_total = round(float((df['home_goals'] + df['away_goals']).mean()), 2)
    avg_home = round(float(df['home_goals'].mean()), 2)
    avg_away = round(float(df['away_goals'].mean()), 2)
    home_wins = int((df['home_goals'] > df['away_goals']).sum())
    away_wins = int((df['home_goals'] < df['away_goals']).sum())
    draws = int((df['home_goals'] == df['away_goals']).sum())
    return {
        "competition": competition, "total_matches": total,
        "avg_total_goals": avg_total, "avg_home_goals": avg_home, "avg_away_goals": avg_away,
        "home_win_rate": round(home_wins / total * 100, 1),
        "away_win_rate": round(away_wins / total * 100, 1),
        "draw_rate": round(draws / total * 100, 1),
    }


def get_team_best_away_record(all_matches, competition=None, limit=10):
    df = all_matches.copy()
    if competition:
        df = df[df['source'].str.contains(competition, case=False, na=False)]
    if df.empty:
        return {"away_records": []}
    all_teams = set(df['away_team'].unique())
    records = []
    for team in all_teams:
        team_away = df[df['away_team'] == team]
        stats = _compute_team_stats(team_away, team)
        records.append({"team": team, **stats})
    records.sort(key=lambda x: (-x['win_rate'], x['goals_against']))
    return {"away_records": records[:limit]}


# --- Display helpers ---

def format_match_display(row):
    """Format a match row into a human-readable string."""
    date = row.get('date', 'N/A')
    season = row.get('season')
    comp = row.get('competition', 'N/A')
    home = row.get('home_team', '?')
    away = row.get('away_team', '?')
    hg = row.get('home_goals', '?')
    ag = row.get('away_goals', '?')
    round_num = row.get('round')
    extra = f" (Season {season})" if season else ""
    if round_num:
        extra += f", Round {round_num}"
    return f"{date}: {home} {hg}-{ag} {away} ({comp}{extra})"


def format_h2h_display(result):
    """Format head-to-head results into a readable string."""
    if result['matches'] == 0:
        return f"No matches found between {result['team_a']} and {result['team_b']} in dataset."
    lines = [
        f"{result['team_a']} vs {result['team_b']}:",
        f"  Head-to-head in dataset: "
        f"{result['team_a']} {result['team_a_wins']} wins, "
        f"{result['team_b']} {result['team_b_wins']} wins, "
        f"{result['draws']} draws",
    ]
    for m in result['matches_list'][:10]:
        lines.append(f"  {format_match_display(m)}")
    if len(result['matches_list']) > 10:
        lines.append(f"  ... ({result['matches']} total matches in dataset)")
    return "\n".join(lines)
