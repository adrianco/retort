"""Data loader for Brazilian soccer datasets."""

import re
import pandas as pd
from pathlib import Path
from functools import lru_cache


DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Team name normalization map (common variations -> canonical name)
TEAM_NAME_MAP = {
    # Remove state suffixes like -SP, -RJ, etc.
    # These are handled dynamically in normalize_team_name()
    "atletico": "Atletico-MG",
    "atletico mineiro": "Atletico-MG",
    "atletico-mg": "Atletico-MG",
    "gremio": "Grêmio",
    "grêmio": "Grêmio",
    "sao paulo": "São Paulo",
    "são paulo": "São Paulo",
    "sao paulo fc": "São Paulo",
    "fluminense": "Fluminense",
    "flamengo": "Flamengo",
    "corinthians": "Corinthians",
    "palmeiras": "Palmeiras",
    "santos": "Santos",
    "vasco": "Vasco",
    "cruzeiro": "Cruzeiro",
    "botafogo": "Botafogo",
    "internacional": "Internacional",
    "sport": "Sport",
    "bahia": "Bahia",
    "fortaleza": "Fortaleza",
    "ceara": "Ceará",
    "ceará": "Ceará",
    "athletico": "Athletico-PR",
    "athletico-pr": "Athletico-PR",
    "athletico parana": "Athletico-PR",
    "atletico-pr": "Athletico-PR",
    "goias": "Goiás",
    "goiás": "Goiás",
    "america": "América-MG",
    "america-mg": "América-MG",
    "america mg": "América-MG",
    "bragantino": "Bragantino",
    "red bull bragantino": "Bragantino",
    "coritiba": "Coritiba",
    "avai": "Avaí",
    "avaí": "Avaí",
}

STATE_SUFFIX_RE = re.compile(r"-([A-Z]{2})$")


def normalize_team_name(name: str) -> str:
    """Normalize team name by removing state suffix and lowercasing."""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    # Remove state suffix like -SP, -RJ
    name_no_state = STATE_SUFFIX_RE.sub("", name).strip()
    lower = name_no_state.lower()
    if lower in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[lower]
    return name_no_state


def team_matches(team_name: str, candidate: str) -> bool:
    """Check if a team name matches a candidate (fuzzy)."""
    t_norm = normalize_team_name(team_name).lower()
    c_norm = normalize_team_name(candidate).lower()
    return t_norm in c_norm or c_norm in t_norm


@lru_cache(maxsize=1)
def load_brasileirao() -> pd.DataFrame:
    """Load Brasileirão Serie A matches."""
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df["competition"] = "Brasileirão Serie A"
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


@lru_cache(maxsize=1)
def load_copa_brasil() -> pd.DataFrame:
    """Load Copa do Brasil matches."""
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    df["competition"] = "Copa do Brasil"
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


@lru_cache(maxsize=1)
def load_libertadores() -> pd.DataFrame:
    """Load Copa Libertadores matches."""
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df["competition"] = "Copa Libertadores"
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


@lru_cache(maxsize=1)
def load_br_football() -> pd.DataFrame:
    """Load extended BR Football Dataset."""
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df["competition"] = df["tournament"]
    df["datetime"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.rename(columns={"home": "home_team", "away": "away_team"})
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = df["datetime"].dt.year
    return df


@lru_cache(maxsize=1)
def load_historico() -> pd.DataFrame:
    """Load historical Brasileirão 2003-2019."""
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv")
    df["competition"] = "Brasileirão Serie A"
    df["datetime"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df = df.rename(columns={
        "Equipe_mandante": "home_team",
        "Equipe_visitante": "away_team",
        "Gols_mandante": "home_goal",
        "Gols_visitante": "away_goal",
        "Ano": "season",
        "Rodada": "round",
        "Vencedor": "winner",
        "Arena": "arena",
    })
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


@lru_cache(maxsize=1)
def load_fifa() -> pd.DataFrame:
    """Load FIFA player data."""
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", low_memory=False)
    # Strip BOM from first column name if present
    df.columns = [c.lstrip("\ufeff").lstrip() for c in df.columns]
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    return df


@lru_cache(maxsize=1)
def load_all_matches() -> pd.DataFrame:
    """Combine all match datasets into a single DataFrame."""
    cols = ["datetime", "home_team", "away_team", "home_goal", "away_goal",
            "season", "competition", "home_team_norm", "away_team_norm"]

    frames = []
    for loader, extra_cols in [
        (load_brasileirao, ["round"]),
        (load_copa_brasil, ["round"]),
        (load_libertadores, ["stage"]),
        (load_historico, ["round", "arena", "winner"]),
    ]:
        df = loader()
        available = [c for c in cols + extra_cols if c in df.columns]
        frames.append(df[available])

    combined = pd.concat(frames, ignore_index=True)
    combined["season"] = pd.to_numeric(combined["season"], errors="coerce")
    return combined


def filter_by_team(df: pd.DataFrame, team: str, role: str = "either") -> pd.DataFrame:
    """Filter matches by team name.

    Args:
        df: DataFrame with home_team_norm and away_team_norm columns
        team: Team name to search for
        role: 'home', 'away', or 'either'
    """
    team_lower = normalize_team_name(team).lower()

    home_mask = df["home_team_norm"].str.lower().str.contains(team_lower, na=False, regex=False)
    away_mask = df["away_team_norm"].str.lower().str.contains(team_lower, na=False, regex=False)

    if role == "home":
        return df[home_mask]
    elif role == "away":
        return df[away_mask]
    else:
        return df[home_mask | away_mask]
