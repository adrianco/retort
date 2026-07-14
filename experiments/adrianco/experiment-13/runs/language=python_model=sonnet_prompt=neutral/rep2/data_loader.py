"""Load and normalize all Brazilian soccer CSV datasets."""

import re
import os
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Team name normalization: maps variations to a canonical base name
_STATE_SUFFIX_RE = re.compile(r"-[A-Z]{2}$")
_BRACKET_RE = re.compile(r"\s*\(.*?\)\s*")

# Known full-name -> short-name mappings
_TEAM_ALIASES: dict[str, str] = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "fluminense football club": "fluminense",
    "sport club internacional": "internacional",
    "gremio foot-ball porto alegrense": "grêmio",
    "gremio": "grêmio",
    "atletico mineiro": "atlético mineiro",
    "atletico-mg": "atlético mineiro",
    "atlético-mg": "atlético mineiro",
    "atletico paranaense": "athletico paranaense",
    "athletico-pr": "athletico paranaense",
    "atlético-pr": "athletico paranaense",
    "atletico-pr": "athletico paranaense",
    "sport recife": "sport",
    "sport-pe": "sport",
    "vasco da gama": "vasco",
    "clube de regatas vasco da gama": "vasco",
    "santos futebol clube": "santos",
    "são paulo futebol clube": "são paulo",
    "sao paulo": "são paulo",
    "cruzeiro esporte clube": "cruzeiro",
    "botafogo de futebol e regatas": "botafogo",
    "boavista sport club": "boavista",
}


def normalize_team(name: str) -> str:
    """Return a normalized, lowercase team name for fuzzy matching."""
    if not isinstance(name, str):
        return ""
    n = name.strip()
    n_lower = n.lower()

    # Check aliases on the original lowercase form first (e.g. "atletico-mg")
    if n_lower in _TEAM_ALIASES:
        return _TEAM_ALIASES[n_lower]

    # Remove state suffix like -SP, -RJ, -MG (uppercase in raw names)
    n = _STATE_SUFFIX_RE.sub("", n)
    # Remove parenthetical notes
    n = _BRACKET_RE.sub(" ", n)
    n = n.strip().lower()
    return _TEAM_ALIASES.get(n, n)


_DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y/%m/%d",
]


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse a mixed-format date series to datetime, coercing errors."""
    result = pd.Series([pd.NaT] * len(series), dtype="datetime64[us]")
    remaining = series.copy()
    for fmt in _DATE_FORMATS:
        parsed = pd.to_datetime(remaining, format=fmt, errors="coerce")
        filled = result.isna() & parsed.notna()
        result = result.where(~filled, parsed)
    return result


def load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv", encoding="utf-8")
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_norm"] = df["home_team"].map(normalize_team)
    df["away_norm"] = df["away_team"].map(normalize_team)
    df["competition"] = "Brasileirao Serie A"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv", encoding="utf-8")
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_norm"] = df["home_team"].map(normalize_team)
    df["away_norm"] = df["away_team"].map(normalize_team)
    df["competition"] = "Copa do Brasil"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv", encoding="utf-8")
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_norm"] = df["home_team"].map(normalize_team)
    df["away_norm"] = df["away_team"].map(normalize_team)
    df["competition"] = "Copa Libertadores"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv", encoding="utf-8")
    df = df.rename(columns={"home": "home_team", "away": "away_team", "date": "datetime"})
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_norm"] = df["home_team"].map(normalize_team)
    df["away_norm"] = df["away_team"].map(normalize_team)
    df["competition"] = df["tournament"].fillna("Unknown")
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    if "season" not in df.columns:
        df["season"] = df["datetime"].dt.year
    return df


def load_historico() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    df = df.rename(
        columns={
            "Data": "datetime",
            "Ano": "season",
            "Rodada": "round",
            "Equipe_mandante": "home_team",
            "Equipe_visitante": "away_team",
            "Gols_mandante": "home_goal",
            "Gols_visitante": "away_goal",
            "Mandante_UF": "home_team_state",
            "Visitante_UF": "away_team_state",
            "Arena": "arena",
            "Vencedor": "winner",
        }
    )
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_norm"] = df["home_team"].map(normalize_team)
    df["away_norm"] = df["away_team"].map(normalize_team)
    df["competition"] = "Brasileirao Serie A"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_fifa() -> pd.DataFrame:
    # FIFA CSV has a BOM/unnamed leading column
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8-sig")
    # Drop unnamed index column if present
    unnamed = [c for c in df.columns if c.startswith("Unnamed")]
    if unnamed:
        df = df.drop(columns=unnamed)
    df["name_norm"] = df["Name"].str.lower().str.strip()
    df["club_norm"] = df["Club"].map(normalize_team)
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
    return df


def load_all_matches() -> pd.DataFrame:
    """Load and concatenate all match datasets into a unified DataFrame."""
    common_cols = ["datetime", "home_team", "away_team", "home_goal", "away_goal",
                   "season", "competition", "home_norm", "away_norm"]

    frames = []
    for loader in [load_brasileirao, load_copa_brasil, load_libertadores,
                   load_br_football, load_historico]:
        df = loader()
        # Keep only common columns that exist + round/stage if present
        keep = [c for c in common_cols if c in df.columns]
        for extra in ["round", "stage", "home_team_state", "away_team_state", "arena", "winner"]:
            if extra in df.columns:
                keep.append(extra)
        frames.append(df[keep])

    combined = pd.concat(frames, ignore_index=True)
    # Deduplicate by date + teams + goals
    combined = combined.drop_duplicates(
        subset=["datetime", "home_norm", "away_norm", "home_goal", "away_goal"],
        keep="first"
    )
    combined = combined.sort_values("datetime", ascending=False).reset_index(drop=True)
    return combined


# Module-level cached data
_matches: pd.DataFrame | None = None
_fifa: pd.DataFrame | None = None


def get_matches() -> pd.DataFrame:
    global _matches
    if _matches is None:
        _matches = load_all_matches()
    return _matches


def get_fifa() -> pd.DataFrame:
    global _fifa
    if _fifa is None:
        _fifa = load_fifa()
    return _fifa


def find_team_matches(team: str, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return all matches involving a team (partial, case-insensitive match)."""
    if df is None:
        df = get_matches()
    t = normalize_team(team)
    mask = df["home_norm"].str.contains(t, na=False) | df["away_norm"].str.contains(t, na=False)
    return df[mask]
