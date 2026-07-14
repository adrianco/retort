"""
Data loading and normalization for Brazilian soccer datasets.
"""

import re
import pandas as pd
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

_STATE_SUFFIX = re.compile(r'\s*-\s*[A-Z]{2}\s*$')


def normalize_team_name(name: str) -> str:
    """Remove state/country suffix and trim whitespace from team name."""
    if not isinstance(name, str):
        return ""
    return _STATE_SUFFIX.sub('', name.strip()).strip()


def _parse_goals(val) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def _to_iso_date(val) -> str:
    """Convert various date formats to YYYY-MM-DD string."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if re.match(r'^\d{2}/\d{2}/\d{4}', s):
        parts = s.split('/')
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return s[:10]


class DataLoader:
    """Loads and normalises the six Brazilian soccer CSV datasets."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self._brasileirao: Optional[pd.DataFrame] = None
        self._copa: Optional[pd.DataFrame] = None
        self._libertadores: Optional[pd.DataFrame] = None
        self._historical: Optional[pd.DataFrame] = None
        self._br_football: Optional[pd.DataFrame] = None
        self._players: Optional[pd.DataFrame] = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        if self._loaded:
            return
        self._brasileirao = self._load_brasileirao()
        self._copa = self._load_copa()
        self._libertadores = self._load_libertadores()
        self._historical = self._load_historical()
        self._br_football = self._load_br_football()
        self._players = self._load_players()
        self._loaded = True

    def get_all_matches(self) -> pd.DataFrame:
        """Unified match DataFrame from all datasets (may contain duplicates for search)."""
        self.load_all()
        frames = [
            self._brasileirao,
            self._copa,
            self._libertadores,
            self._historical,
            self._br_football,
        ]
        return pd.concat(frames, ignore_index=True)

    def get_brasileirao_matches(self) -> pd.DataFrame:
        """Primary Brasileirao dataset (2012-2022, no duplicates)."""
        self.load_all()
        return self._brasileirao

    def get_copa_matches(self) -> pd.DataFrame:
        self.load_all()
        return self._copa

    def get_libertadores_matches(self) -> pd.DataFrame:
        self.load_all()
        return self._libertadores

    def get_historical_matches(self) -> pd.DataFrame:
        """Pre-2012 Brasileirao historical data."""
        self.load_all()
        return self._historical

    def get_players(self) -> pd.DataFrame:
        self.load_all()
        return self._players

    # ------------------------------------------------------------------
    # Private loaders – each returns a normalised DataFrame with columns:
    # date, home_team, away_team, home_goals, away_goals, competition, season, round_or_stage
    # ------------------------------------------------------------------

    def _std_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure column order is consistent."""
        return df[["date", "home_team", "away_team", "home_goals", "away_goals",
                   "competition", "season", "round_or_stage"]]

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brasileirao_Matches.csv")
        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df["datetime"], errors="coerce").dt.strftime("%Y-%m-%d")
        # Keep original names (with state suffix) to disambiguate e.g. Atletico-MG vs Atletico-GO
        out["home_team"] = df["home_team"].str.strip()
        out["away_team"] = df["away_team"].str.strip()
        out["home_goals"] = df["home_goal"].apply(_parse_goals)
        out["away_goals"] = df["away_goal"].apply(_parse_goals)
        out["competition"] = "brasileirao"
        out["season"] = df["season"].astype(int)
        out["round_or_stage"] = df["round"].astype(str)
        return self._std_cols(out)

    def _load_copa(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brazilian_Cup_Matches.csv")
        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df["datetime"], errors="coerce").dt.strftime("%Y-%m-%d")
        out["home_team"] = df["home_team"].apply(normalize_team_name)
        out["away_team"] = df["away_team"].apply(normalize_team_name)
        out["home_goals"] = df["home_goal"].apply(_parse_goals)
        out["away_goals"] = df["away_goal"].apply(_parse_goals)
        out["competition"] = "copa_do_brasil"
        out["season"] = df["season"].astype(int)
        out["round_or_stage"] = df["round"].astype(str)
        return self._std_cols(out)

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Libertadores_Matches.csv")
        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df["datetime"], errors="coerce").dt.strftime("%Y-%m-%d")
        out["home_team"] = df["home_team"].apply(normalize_team_name)
        out["away_team"] = df["away_team"].apply(normalize_team_name)
        out["home_goals"] = df["home_goal"].apply(_parse_goals)
        out["away_goals"] = df["away_goal"].apply(_parse_goals)
        out["competition"] = "libertadores"
        out["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)
        out["round_or_stage"] = df["stage"].astype(str)
        return self._std_cols(out)

    def _load_historical(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "novo_campeonato_brasileiro.csv")
        # Only keep pre-2012 to avoid duplicates with Brasileirao_Matches.csv
        df = df[df["Ano"] < 2012].copy()
        out = pd.DataFrame()
        out["date"] = df["Data"].apply(_to_iso_date)
        out["home_team"] = df["Equipe_mandante"].apply(normalize_team_name)
        out["away_team"] = df["Equipe_visitante"].apply(normalize_team_name)
        out["home_goals"] = df["Gols_mandante"].apply(_parse_goals)
        out["away_goals"] = df["Gols_visitante"].apply(_parse_goals)
        out["competition"] = "brasileirao"
        out["season"] = df["Ano"].astype(int)
        out["round_or_stage"] = df["Rodada"].astype(str)
        return self._std_cols(out)

    def _load_br_football(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "BR-Football-Dataset.csv")

        def _map_competition(t: str) -> str:
            t = str(t).lower()
            if "serie a" in t:
                return "brasileirao"
            if "copa do brasil" in t:
                return "copa_do_brasil"
            if "serie b" in t:
                return "serie_b"
            if "serie c" in t:
                return "serie_c"
            return t.replace(" ", "_")

        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        out["home_team"] = df["home"].apply(normalize_team_name)
        out["away_team"] = df["away"].apply(normalize_team_name)
        out["home_goals"] = df["home_goal"].apply(_parse_goals)
        out["away_goals"] = df["away_goal"].apply(_parse_goals)
        out["competition"] = df["tournament"].apply(_map_competition)
        out["season"] = pd.to_datetime(df["date"], errors="coerce").dt.year.fillna(0).astype(int)
        out["round_or_stage"] = ""
        return self._std_cols(out)

    def _load_players(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "fifa_data.csv", low_memory=False)
