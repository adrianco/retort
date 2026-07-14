"""Load and normalize Brazilian soccer CSV datasets."""
import re
from pathlib import Path

import pandas as pd


# Two-letter Brazilian state abbreviations
_STATE_ABBREVS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

_DASH_STATE_RE = re.compile(
    r"\s*-\s*(" + "|".join(_STATE_ABBREVS) + r")$"
)


def normalize_team_name(name: str) -> str:
    """Strip trailing state suffix (e.g. '-SP', '- RJ') from a team name."""
    if not name:
        return name
    return _DASH_STATE_RE.sub("", name).strip()


def parse_date(value: str):
    """Parse a date string in ISO or Brazilian DD/MM/YYYY format. Returns None for empty input."""
    if not value or not str(value).strip():
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return pd.to_datetime(value, format=fmt)
        except (ValueError, TypeError):
            pass
    try:
        return pd.to_datetime(value)
    except Exception:
        return None


def _add_normalized_teams(df: pd.DataFrame, home_col: str, away_col: str) -> pd.DataFrame:
    df = df.copy()
    df["home_team_norm"] = df[home_col].astype(str).map(normalize_team_name)
    df["away_team_norm"] = df[away_col].astype(str).map(normalize_team_name)
    return df


def _add_parsed_date(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df = df.copy()
    # Try ISO-style first, then Brazilian DD/MM/YYYY
    df["date_parsed"] = pd.to_datetime(df[date_col], format="mixed", dayfirst=False, errors="coerce")
    mask = df["date_parsed"].isna()
    if mask.any():
        df.loc[mask, "date_parsed"] = pd.to_datetime(
            df.loc[mask, date_col], format="%d/%m/%Y", errors="coerce"
        )
    return df


class DataLoader:
    """Load and expose all six CSV datasets."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.brasileirao: pd.DataFrame | None = None
        self.copa_brasil: pd.DataFrame | None = None
        self.libertadores: pd.DataFrame | None = None
        self.br_football: pd.DataFrame | None = None
        self.historical: pd.DataFrame | None = None
        self.fifa: pd.DataFrame | None = None

    def load_all(self) -> None:
        self.brasileirao = self._load_brasileirao()
        self.copa_brasil = self._load_copa_brasil()
        self.libertadores = self._load_libertadores()
        self.br_football = self._load_br_football()
        self.historical = self._load_historical()
        self.fifa = self._load_fifa()

    @property
    def all_match_dfs(self) -> list[tuple[str, pd.DataFrame]]:
        return [
            ("brasileirao", self.brasileirao),
            ("copa_brasil", self.copa_brasil),
            ("libertadores", self.libertadores),
            ("br_football", self.br_football),
            ("historical", self.historical),
        ]

    # --- private loaders ---

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brasileirao_Matches.csv", encoding="utf-8")
        df = _add_normalized_teams(df, "home_team", "away_team")
        df = _add_parsed_date(df, "datetime")
        return df

    def _load_copa_brasil(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brazilian_Cup_Matches.csv", encoding="utf-8")
        df = _add_normalized_teams(df, "home_team", "away_team")
        df = _add_parsed_date(df, "datetime")
        return df

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Libertadores_Matches.csv", encoding="utf-8")
        df = _add_normalized_teams(df, "home_team", "away_team")
        df = _add_parsed_date(df, "datetime")
        return df

    def _load_br_football(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "BR-Football-Dataset.csv", encoding="utf-8")
        df = _add_normalized_teams(df, "home", "away")
        df = _add_parsed_date(df, "date")
        # Derive season from date year since no season column exists
        df["season"] = df["date_parsed"].dt.year
        return df

    def _load_historical(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "novo_campeonato_brasileiro.csv", encoding="utf-8")
        df = _add_normalized_teams(df, "Equipe_mandante", "Equipe_visitante")
        df = _add_parsed_date(df, "Data")
        return df

    def _load_fifa(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "fifa_data.csv", encoding="utf-8")
        # Drop unnamed leading index column if present
        if df.columns[0].startswith("Unnamed") or df.columns[0] == "":
            df = df.drop(columns=df.columns[0])
        return df
