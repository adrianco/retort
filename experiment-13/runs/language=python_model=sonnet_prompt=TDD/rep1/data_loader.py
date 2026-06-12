"""Load and normalize Brazilian soccer datasets."""
import re
import pandas as pd
from pathlib import Path


def normalize_team_name(name) -> str:
    """Normalize a team name to a consistent format for matching and disambiguation.

    Converts state-suffix formats (Palmeiras-SP, Atletico-MG) to space-separated
    (Palmeiras SP, Atletico MG) so different states remain distinct while partial-
    string search still works (searching "Atletico" still finds both clubs).
    """
    if not name:
        return ""
    name = str(name).strip()
    # Replace "- XX" / "-XX" state suffix with " XX" (space-separated, not stripped)
    name = re.sub(r"\s*-\s*([A-Z]{2})$", r" \1", name)
    return name.strip()


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse dates from various formats."""
    parsed = pd.to_datetime(series, format="mixed", dayfirst=False, errors="coerce")
    # For rows that failed, try Brazilian DD/MM/YYYY format
    mask = parsed.isna()
    if mask.any():
        br_parsed = pd.to_datetime(series[mask], format="%d/%m/%Y", errors="coerce")
        parsed[mask] = br_parsed
    return parsed


def load_brasileirao(data_dir: str) -> pd.DataFrame:
    path = Path(data_dir) / "Brasileirao_Matches.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["date"] = _parse_dates(df["datetime"])
    df["competition"] = "Brasileirão Serie A"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_copa_brasil(data_dir: str) -> pd.DataFrame:
    path = Path(data_dir) / "Brazilian_Cup_Matches.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["date"] = _parse_dates(df["datetime"])
    df["competition"] = "Copa do Brasil"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_libertadores(data_dir: str) -> pd.DataFrame:
    path = Path(data_dir) / "Libertadores_Matches.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["date"] = _parse_dates(df["datetime"])
    df["competition"] = "Copa Libertadores"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_br_football(data_dir: str) -> pd.DataFrame:
    path = Path(data_dir) / "BR-Football-Dataset.csv"
    df = pd.read_csv(path, encoding="utf-8")
    # Rename columns to standard names
    df = df.rename(columns={"home": "home_team", "away": "away_team"})
    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["date"] = _parse_dates(df["date"])
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    if "competition" not in df.columns:
        df["competition"] = df.get("tournament", "Unknown")
    return df


def load_historico_brasileiro(data_dir: str) -> pd.DataFrame:
    path = Path(data_dir) / "novo_campeonato_brasileiro.csv"
    df = pd.read_csv(path, encoding="utf-8")
    # Rename Brazilian Portuguese columns to standard names
    df = df.rename(columns={
        "Equipe_mandante": "home_team",
        "Equipe_visitante": "away_team",
        "Gols_mandante": "home_goal",
        "Gols_visitante": "away_goal",
        "Ano": "season",
        "Rodada": "round",
        "Data": "date_raw",
        "Vencedor": "winner",
        "Arena": "stadium",
        "Mandante_UF": "home_team_state",
        "Visitante_UF": "away_team_state",
    })
    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["date"] = _parse_dates(df["date_raw"])
    df["competition"] = "Brasileirão Serie A"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_fifa_players(data_dir: str) -> pd.DataFrame:
    path = Path(data_dir) / "fifa_data.csv"
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
    return df


_COMMON_COLS = ["home_team", "away_team", "home_goal", "away_goal", "date", "competition", "season"]


def _to_common(df: pd.DataFrame, extra_cols: list[str] = None) -> pd.DataFrame:
    out = df.copy()
    # Derive season from date when not present
    if "season" not in out.columns and "date" in out.columns:
        out["season"] = out["date"].dt.year
    cols = [c for c in _COMMON_COLS if c in out.columns]
    if extra_cols:
        cols += [c for c in extra_cols if c in out.columns and c not in cols]
    return out[cols].copy()


def get_all_matches(data_dir: str) -> pd.DataFrame:
    """Return a unified DataFrame of all matches from all sources."""
    frames = []
    for loader in [load_brasileirao, load_copa_brasil, load_libertadores,
                   load_br_football, load_historico_brasileiro]:
        try:
            df = loader(data_dir)
            frames.append(_to_common(df))
        except Exception:
            pass
    combined = pd.concat(frames, ignore_index=True)
    combined["home_goal"] = pd.to_numeric(combined["home_goal"], errors="coerce")
    combined["away_goal"] = pd.to_numeric(combined["away_goal"], errors="coerce")
    return combined


class DataLoader:
    """Singleton-style loader for all datasets."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.brasileirao = load_brasileirao(data_dir)
        self.copa_brasil = load_copa_brasil(data_dir)
        self.libertadores = load_libertadores(data_dir)
        self.br_football = load_br_football(data_dir)
        self.historico = load_historico_brasileiro(data_dir)
        self.fifa_players = load_fifa_players(data_dir)
        self.all_matches = get_all_matches(data_dir)
