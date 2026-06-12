import re
import datetime
from pathlib import Path
import pandas as pd


# ─── Cycle 1: Team name normalization ─────────────────────────────────────────

def normalize_team_name(name: str) -> str:
    """Strip state suffix from team name (e.g. 'Palmeiras-SP' -> 'Palmeiras')."""
    if not isinstance(name, str):
        return name
    # Remove ` - XX` pattern (spaces around dash, 2 uppercase letters)
    name = re.sub(r'\s*-\s*[A-Z]{2}$', '', name)
    return name.strip()


def teams_match(name1: str, name2: str) -> bool:
    """Return True if two team names refer to the same team after normalization."""
    return normalize_team_name(name1) == normalize_team_name(name2)


# ─── Cycle 2: Date parsing ─────────────────────────────────────────────────────

def parse_date(value) -> datetime.date | None:
    """Parse various date string formats into datetime.date. Returns None for None input."""
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    s = str(value).strip()
    if not s or s.lower() == 'nan':
        return None
    # Try ISO datetime format: "2012-05-19 18:30:00"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ─── Cycle 3: DataLoader ──────────────────────────────────────────────────────

class DataLoader:
    """Lazy-loading data loader for Brazilian soccer CSV files."""

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self._brasileirao = None
        self._cup = None
        self._libertadores = None
        self._historical = None
        self._extended = None
        self._players = None
        self._all_matches = None

    def _parse_dates_series(self, series: pd.Series) -> pd.Series:
        return series.apply(parse_date)

    def load_brasileirao(self) -> pd.DataFrame:
        if self._brasileirao is None:
            df = pd.read_csv(self.data_dir / "Brasileirao_Matches.csv")
            # Normalize team names (strip state suffixes)
            df["home_team"] = df["home_team"].apply(normalize_team_name)
            df["away_team"] = df["away_team"].apply(normalize_team_name)
            df["date"] = self._parse_dates_series(df["datetime"])
            df["competition"] = "brasileirao"
            df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
            df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
            self._brasileirao = df
        return self._brasileirao

    def load_cup(self) -> pd.DataFrame:
        if self._cup is None:
            df = pd.read_csv(self.data_dir / "Brazilian_Cup_Matches.csv")
            df["home_team"] = df["home_team"].apply(normalize_team_name)
            df["away_team"] = df["away_team"].apply(normalize_team_name)
            df["date"] = self._parse_dates_series(df["datetime"])
            df["competition"] = "cup"
            df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
            df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
            self._cup = df
        return self._cup

    def load_libertadores(self) -> pd.DataFrame:
        if self._libertadores is None:
            df = pd.read_csv(self.data_dir / "Libertadores_Matches.csv")
            df["home_team"] = df["home_team"].apply(normalize_team_name)
            df["away_team"] = df["away_team"].apply(normalize_team_name)
            df["date"] = self._parse_dates_series(df["datetime"])
            df["competition"] = "libertadores"
            df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
            df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
            self._libertadores = df
        return self._libertadores

    def load_historical(self) -> pd.DataFrame:
        """Load novo_campeonato_brasileiro.csv with Portuguese column names normalized."""
        if self._historical is None:
            df = pd.read_csv(self.data_dir / "novo_campeonato_brasileiro.csv")
            df = df.rename(columns={
                "Equipe_mandante": "home_team",
                "Equipe_visitante": "away_team",
                "Gols_mandante": "home_goal",
                "Gols_visitante": "away_goal",
                "Ano": "season",
                "Data": "datetime_raw",
            })
            df["home_team"] = df["home_team"].apply(normalize_team_name)
            df["away_team"] = df["away_team"].apply(normalize_team_name)
            df["date"] = self._parse_dates_series(df["datetime_raw"])
            df["competition"] = "historical"
            df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
            df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
            self._historical = df
        return self._historical

    def load_extended(self) -> pd.DataFrame:
        """Load BR-Football-Dataset.csv, renaming home/away to home_team/away_team."""
        if self._extended is None:
            df = pd.read_csv(self.data_dir / "BR-Football-Dataset.csv")
            df = df.rename(columns={"home": "home_team", "away": "away_team"})
            df["home_team"] = df["home_team"].apply(normalize_team_name)
            df["away_team"] = df["away_team"].apply(normalize_team_name)
            if "date" in df.columns:
                df["date"] = self._parse_dates_series(df["date"])
            df["competition"] = "extended"
            df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
            df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
            # No season column in this dataset — derive from date if possible
            if "date" in df.columns:
                df["season"] = df["date"].apply(lambda d: d.year if d else None)
            self._extended = df
        return self._extended

    def load_players(self) -> pd.DataFrame:
        if self._players is None:
            df = pd.read_csv(self.data_dir / "fifa_data.csv")
            self._players = df
        return self._players

    def load_all_matches(self) -> pd.DataFrame:
        """Combine all match sources into one DataFrame with a competition column."""
        if self._all_matches is None:
            common_cols = ["home_team", "away_team", "home_goal", "away_goal", "competition"]

            def _select(df, extra_cols=None):
                cols = common_cols[:]
                for c in (extra_cols or []):
                    if c in df.columns:
                        cols.append(c)
                available = [c for c in cols if c in df.columns]
                return df[available].copy()

            frames = [
                _select(self.load_brasileirao(), ["season", "date"]),
                _select(self.load_cup(), ["season", "date"]),
                _select(self.load_libertadores(), ["season", "date"]),
                _select(self.load_historical(), ["season", "date"]),
                _select(self.load_extended(), ["season", "date"]),
            ]
            self._all_matches = pd.concat(frames, ignore_index=True)
        return self._all_matches
