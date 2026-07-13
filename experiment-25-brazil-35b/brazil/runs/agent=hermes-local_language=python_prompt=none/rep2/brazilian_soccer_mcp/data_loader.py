"""Data loader module for Brazilian soccer datasets.

Handles loading, normalizing, and caching all 6 CSV datasets from Kaggle.
"""

import os
import re
from datetime import datetime
from functools import lru_cache
from typing import Optional

import pandas as pd


# Absolute path to the data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

# Competition mappings for the extended dataset
TOURNAMENT_COMPETITION_MAP = {
    "Brasileirao": "Brasileirao Serie A",
    "Serie A": "Brasileirao Serie A",
    "Copa do Brasil": "Copa do Brasil",
    "Libertadores": "Copa Libertadores",
    "Campeonato Brasileiro": "Brasileirao Serie A",
}

# Brazilian clubs known to be in major competitions
BRAZILIAN_CLUBS = {
    "Atletico Mineiro", "Athletico Paranaense", "Bahia", "Botafogo",
    "Corinthians", "Coritiba", "Cruzeiro", "Cuiaba", "Esporte Clube Bahia",
    "Flamengo", "Fluminense", "Fortaleza", "Gremio", "Goiás",
    "Internacional", "Madureira", "Manaus", "Mateus Cardoso", "Mirassol",
    "Nautico", "Palmeiras", "Ponte Preta", "Portuguesa", "Santos",
    "Sao Paulo", "Sport Recife", "Santos-SP", "Sport-PE",
    "Vasco da Gama", "Vitoria", "Vitoria-ES", "America-MG",
    "America Mineiro", "America-RJ", "America-RN", "Botafogo-SP",
    "Brasiliense", "Cabofriense", "Chapecoense", "Criciuma",
    "Ceara", "Cuiaba-MT", "Coritiba-PR", "CRB", "Duque de Caxias",
    "EC Juventude", "EC Juventude", "Figueirense", "Flamengo-RJ",
    "Fluminense-RJ", "Fortaleza-CE", "Gremio-BB", "Gremio-PR",
    "Goias", "Goias-ES", "Guarani", "Itumbiara", "Joinville",
    "Juventude", "Londrina", "Londrina-PR", "MACAÉ", "Madureira-RJ",
    "Maringa", "Mirassol-SP", "Nacional-AM", "Novorizontino",
    "Operario-PR", "Operario", "Oeste", "Paysandu",
    "Palmeiras-SP", "Ponte Preta-SP", "Portuguesa-RJ",
    "Red Bull Bragantino", "Renault", "Rio Branco-ES",
    "Rio Branco-SP", "Rio Claro", "Rio Verde",
    "Sampaio Correa", "Santa Cruz", "Santa Rita",
    "Santos-SP", "Sao Bernardo", "Sao Caetano",
    "Sao Carlos", "Sao Cristovao", "Sao Jose-RS",
    "Sao Paulo", "Sao Paulo-SP", "Serra MACAÉ",
    "Sport-PE", "Sport Recife-PE", "Taguatinga",
    "Tiradentes", "Torres", "Tupy", "Uberaba",
    "Uberlandia", "Ubirata", "Uniao Sao Jose",
    "Uruguay", "Vasco", "Vasco da Gama-RJ",
    "Vitoria-BA", "Vitoria-ES", "XV de Piracicaba",
    "XV de Joaquim",
}

# State suffixes to strip from team names
STATE_SUFFIX_PATTERN = re.compile(r"-(?:SP|RJ|MG|RS|PR|SC|BA|PE|CE|GO|MT|MS|PA|MA|PI|RN|PB|AL|SE|TO|DF|ES)$")


def normalize_team_name(team: str) -> str:
    """Normalize a team name by stripping state suffixes and whitespace.

    Handles variations like:
    - "Palmeiras-SP" -> "Palmeiras"
    - "Palmeiras - SP" -> "Palmeiras"
    - "Flamengo-RJ" -> "Flamengo"
    - "Sao Paulo-SP" -> "Sao Paulo"
    - "Sao Paulo - SP" -> "Sao Paulo"
    """
    if not team or pd.isna(team):
        return ""
    team = str(team).strip()
    # Strip state suffix with or without spaces around hyphen
    team = re.sub(r"\s*-\s*(?:SP|RJ|MG|RS|PR|SC|BA|PE|CE|GO|MT|MS|PA|MA|PI|RN|PB|AL|SE|TO|DF|ES)\s*$", "", team)
    # Clean up any trailing hyphens or whitespace
    team = team.rstrip(" -").strip()
    return team


def parse_date(date_str: str) -> Optional[str]:
    """Parse a date string in multiple formats and return ISO format.

    Handles:
    - "2023-09-24" (ISO)
    - "2023-09-24 18:30:00" (ISO with time)
    - "29/03/2003" (Brazilian DD/MM/YYYY)
    """
    if date_str is None or pd.isna(date_str):
        return None
    date_str = str(date_str).strip()

    # Try ISO format first
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def parse_goals(val) -> Optional[int]:
    """Parse a goal value, converting float NaN and '-' to None."""
    if val is None or pd.isna(val):
        return None
    val = str(val).strip()
    if val == '-' or val == '':
        return None
    return int(float(val))


def load_brasileirao_matches() -> pd.DataFrame:
    """Load Brasileirao Serie A matches from CSV."""
    filepath = os.path.join(DATA_DIR, "Brasileirao_Matches.csv")
    df = pd.read_csv(filepath, encoding="utf-8")

    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["competition"] = "Brasileirao Serie A"
    df["date"] = df["datetime"].apply(parse_date)
    df["home_goal"] = df["home_goal"].apply(parse_goals)
    df["away_goal"] = df["away_goal"].apply(parse_goals)
    df["round"] = df["round"].astype(int)
    df["season"] = df["season"].astype(int)

    return df[["date", "season", "round", "competition",
               "home_team", "home_goal", "away_team", "away_goal"]]


def load_brazilian_cup_matches() -> pd.DataFrame:
    """Load Copa do Brasil matches from CSV."""
    filepath = os.path.join(DATA_DIR, "Brazilian_Cup_Matches.csv")
    df = pd.read_csv(filepath, encoding="utf-8")

    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["competition"] = "Copa do Brasil"
    df["date"] = df["datetime"].apply(parse_date)
    df["home_goal"] = df["home_goal"].apply(parse_goals)
    df["away_goal"] = df["away_goal"].apply(parse_goals)

    return df[["date", "season", "round", "competition",
               "home_team", "home_goal", "away_team", "away_goal"]]


def load_libertadores_matches() -> pd.DataFrame:
    """Load Copa Libertadores matches from CSV."""
    filepath = os.path.join(DATA_DIR, "Libertadores_Matches.csv")
    df = pd.read_csv(filepath, encoding="utf-8")

    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["competition"] = "Copa Libertadores"
    df["date"] = df["datetime"].apply(parse_date)
    df["home_goal"] = df["home_goal"].apply(parse_goals)
    df["away_goal"] = df["away_goal"].apply(parse_goals)
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    # Libertadores has no 'round' column
    df["round"] = None

    return df[["date", "season", "round", "competition",
               "home_team", "home_goal", "away_team", "away_goal"]]


def load_extended_matches() -> pd.DataFrame:
    """Load extended match statistics from CSV."""
    filepath = os.path.join(DATA_DIR, "BR-Football-Dataset.csv")
    df = pd.read_csv(filepath, encoding="utf-8")

    df["home_team"] = df["home"].apply(normalize_team_name)
    df["away_team"] = df["away"].apply(normalize_team_name)
    df["date"] = df["date"].apply(parse_date)
    df["home_goal"] = df["home_goal"].apply(parse_goals)
    df["away_goal"] = df["away_goal"].apply(parse_goals)

    # Map tournament names to competition names
    def map_tournament(t):
        t = str(t).strip() if pd.notna(t) else "Unknown"
        for key, val in TOURNAMENT_COMPETITION_MAP.items():
            if key.lower() in t.lower():
                return val
        return t

    df["competition"] = df["tournament"].apply(map_tournament)
    # Infer season from date
    df["season"] = df["date"].apply(lambda d: int(d.split("-")[0]) if d and len(str(d)) >= 4 else None)
    df["round"] = None  # Not available in this dataset

    return df[["date", "season", "round", "competition",
               "home_team", "home_goal", "away_team", "away_goal"]]


def load_historical_matches() -> pd.DataFrame:
    """Load historical Campeonato Brasileiro (2003-2019) from CSV."""
    filepath = os.path.join(DATA_DIR, "novo_campeonato_brasileiro.csv")
    df = pd.read_csv(filepath, encoding="utf-8")

    df["home_team"] = df["Equipe_mandante"].apply(normalize_team_name)
    df["away_team"] = df["Equipe_visitante"].apply(normalize_team_name)
    df["date"] = df["Data"].apply(parse_date)
    df["home_goal"] = df["Gols_mandante"].apply(parse_goals)
    df["away_goal"] = df["Gols_visitante"].apply(parse_goals)
    df["competition"] = "Brasileirao Serie A"
    df["season"] = df["Ano"].astype(int)
    df["round"] = df["Rodada"].astype(int)

    return df[["date", "season", "round", "competition",
               "home_team", "home_goal", "away_team", "away_goal"]]


def load_fifa_players() -> pd.DataFrame:
    """Load FIFA player database from CSV."""
    filepath = os.path.join(DATA_DIR, "fifa_data.csv")
    df = pd.read_csv(filepath, encoding="utf-8")

    # Keep only key columns
    key_cols = ["Name", "Age", "Nationality", "Overall", "Potential",
                "Club", "Position", "Jersey Number", "Height", "Weight"]
    available_cols = [c for c in key_cols if c in df.columns]
    return df[available_cols].copy()


def load_all_match_data() -> pd.DataFrame:
    """Load and combine all match datasets."""
    dfs = []
    try:
        dfs.append(load_brasileirao_matches())
    except Exception as e:
        print(f"Warning: Could not load Brasileirao matches: {e}")

    try:
        dfs.append(load_brazilian_cup_matches())
    except Exception as e:
        print(f"Warning: Could not load Copa do Brasil matches: {e}")

    try:
        dfs.append(load_libertadores_matches())
    except Exception as e:
        print(f"Warning: Could not load Libertadores matches: {e}")

    try:
        dfs.append(load_extended_matches())
    except Exception as e:
        print(f"Warning: Could not load extended matches: {e}")

    try:
        dfs.append(load_historical_matches())
    except Exception as e:
        print(f"Warning: Could not load historical matches: {e}")

    if dfs:
        all_matches = pd.concat(dfs, ignore_index=True)
        all_matches["date"] = pd.to_datetime(all_matches["date"])
        return all_matches.sort_values("date").reset_index(drop=True)

    return pd.DataFrame(columns=["date", "season", "round", "competition",
                                  "home_team", "home_goal", "away_team", "away_goal"])


@lru_cache(maxsize=2)
def get_match_data(force_reload: bool = False) -> pd.DataFrame:
    """Get all match data, cached by default."""
    if not force_reload:
        return load_all_match_data()
    # Flush LRU cache for reload
    get_match_data.cache_clear()
    return load_all_match_data()


@lru_cache(maxsize=1)
def get_player_data() -> pd.DataFrame:
    """Get FIFA player data, cached."""
    return load_fifa_players()


def get_all_competitions(df: pd.DataFrame = None) -> list[str]:
    """Get list of all competitions in the dataset."""
    if df is None:
        df = get_match_data()
    return sorted(df["competition"].dropna().unique().tolist())
