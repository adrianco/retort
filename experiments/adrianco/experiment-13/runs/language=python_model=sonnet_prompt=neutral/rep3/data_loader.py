"""Data loading and normalization for Brazilian soccer datasets."""

import re
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Common team name normalizations
_TEAM_ALIASES = {
    "atletico mineiro": ["atletico-mg", "atletico mg", "atlético mineiro", "atlético-mg", "galo"],
    "atletico paranaense": ["atletico-pr", "atletico pr", "atlético paranaense", "atlético-pr", "athletico-pr", "athletico pr", "athletico paranaense"],
    "sao paulo": ["são paulo", "sao paulo fc", "são paulo fc", "spfc"],
    "flamengo": ["cr flamengo", "clube de regatas do flamengo"],
    "fluminense": ["flu"],
    "corinthians": ["sport club corinthians paulista", "sc corinthians paulista"],
    "palmeiras": ["se palmeiras", "sociedade esportiva palmeiras"],
    "gremio": ["grêmio", "grêmio fbpa", "gremio fbpa"],
    "internacional": ["inter", "sport club internacional"],
    "santos": ["santos fc"],
    "botafogo": ["botafogo fr", "botafogo de futebol e regatas"],
    "vasco": ["vasco da gama", "club de regatas vasco da gama", "cr vasco da gama"],
    "cruzeiro": ["cruzeiro ec"],
    "fortaleza": ["fortaleza ec"],
    "ceara": ["ceará", "ceara sc"],
    "bahia": ["ec bahia"],
    "sport": ["sport club recife", "sport recife"],
    "bragantino": ["rb bragantino", "red bull bragantino"],
    "avai": ["avaí", "avai fc"],
    "america mg": ["america mineiro", "américa mineiro", "américa-mg", "america-mg"],
    "goias": ["goiás", "goias ec"],
    "coritiba": ["coritiba fc"],
    "chapecoense": ["chapecoense af"],
    "joinville": ["joinville ec"],
    "figueirense": ["figueirense fc"],
    "vitoria": ["vitória", "ec vitoria"],
    "nautico": ["náutico", "clube nautico capibaribe"],
    "juventude": ["ec juventude"],
    "ponte preta": ["aa ponte preta"],
    "portuguesa": ["portuguesa sp", "associação portuguesa de desportos"],
    "criciuma": ["cricíuma", "criciuma ec"],
}

_NORM_CACHE: dict[str, str] = {}


def _build_norm_cache():
    for canonical, aliases in _TEAM_ALIASES.items():
        for alias in aliases:
            _NORM_CACHE[alias.lower()] = canonical
        _NORM_CACHE[canonical.lower()] = canonical


_build_norm_cache()


def normalize_team(name: str) -> str:
    """Normalize team name to a canonical lowercase form.

    Tries the full name first (handles "Atletico-MG" vs "Atletico-PR" disambiguation),
    then strips state suffix and parenthetical notes as a fallback.
    """
    if not name or pd.isna(name):
        return ""
    name = str(name).strip()

    # Try full name with state suffix in cache first (preserves MG/PR distinction)
    key = name.lower()
    if key in _NORM_CACHE:
        return _NORM_CACHE[key]

    # Strip state suffix like "-SP", "-RJ", "- RJ", " - RJ"
    stripped = re.sub(r'\s*[-–]\s*[A-Z]{2}\s*$', '', name)
    # Strip parenthetical suffixes like "(antigo ...)"
    stripped = re.sub(r'\s*\(.*\)', '', stripped).strip()
    key2 = stripped.lower()
    return _NORM_CACHE.get(key2, key2)


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse dates handling ISO, Brazilian DD/MM/YYYY, and datetime formats."""
    # Try ISO/American format first (dayfirst=False is the pandas default)
    with pd.option_context("mode.chained_assignment", None):
        parsed = pd.to_datetime(series, format="mixed", dayfirst=False, errors='coerce')
    # Retry unparsed entries with explicit Brazilian DD/MM/YYYY format
    mask = parsed.isna()
    if mask.any():
        parsed = parsed.copy()
        parsed[mask] = pd.to_datetime(series[mask], format="%d/%m/%Y", errors='coerce')
    return parsed


class SoccerData:
    """Container for all loaded soccer datasets."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self._brasileirao: pd.DataFrame | None = None
        self._cup: pd.DataFrame | None = None
        self._libertadores: pd.DataFrame | None = None
        self._br_football: pd.DataFrame | None = None
        self._historico: pd.DataFrame | None = None
        self._fifa: pd.DataFrame | None = None
        self._all_matches: pd.DataFrame | None = None

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brasileirao_Matches.csv", encoding="utf-8")
        df["datetime"] = _parse_dates(df["datetime"])
        df["date"] = df["datetime"].dt.date
        df["home_norm"] = df["home_team"].apply(normalize_team)
        df["away_norm"] = df["away_team"].apply(normalize_team)
        df["competition"] = "Brasileirão Serie A"
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_cup(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brazilian_Cup_Matches.csv", encoding="utf-8")
        df["datetime"] = _parse_dates(df["datetime"])
        df["date"] = df["datetime"].dt.date
        df["home_norm"] = df["home_team"].apply(normalize_team)
        df["away_norm"] = df["away_team"].apply(normalize_team)
        df["competition"] = "Copa do Brasil"
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Libertadores_Matches.csv", encoding="utf-8")
        df["datetime"] = _parse_dates(df["datetime"])
        df["date"] = df["datetime"].dt.date
        df["home_norm"] = df["home_team"].apply(normalize_team)
        df["away_norm"] = df["away_team"].apply(normalize_team)
        df["competition"] = "Copa Libertadores"
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_br_football(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "BR-Football-Dataset.csv", encoding="utf-8")
        df = df.rename(columns={"home": "home_team", "away": "away_team"})
        df["datetime"] = _parse_dates(df["date"])
        df["date"] = df["datetime"].dt.date
        df["home_norm"] = df["home_team"].apply(normalize_team)
        df["away_norm"] = df["away_team"].apply(normalize_team)
        df["competition"] = df["tournament"]
        df["season"] = df["datetime"].dt.year
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_historico(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "novo_campeonato_brasileiro.csv", encoding="utf-8")
        df = df.rename(columns={
            "Equipe_mandante": "home_team",
            "Equipe_visitante": "away_team",
            "Gols_mandante": "home_goal",
            "Gols_visitante": "away_goal",
            "Ano": "season",
            "Rodada": "round",
            "Arena": "arena",
            "Vencedor": "winner",
        })
        df["datetime"] = _parse_dates(df["Data"])
        df["date"] = df["datetime"].dt.date
        df["home_norm"] = df["home_team"].apply(normalize_team)
        df["away_norm"] = df["away_team"].apply(normalize_team)
        df["competition"] = "Brasileirão Serie A"
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_fifa(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "fifa_data.csv", encoding="utf-8")
        # Drop unnamed first column if present
        if df.columns[0].startswith("Unnamed") or df.columns[0] == "":
            df = df.iloc[:, 1:]
        df["Nationality_norm"] = df["Nationality"].str.lower().str.strip()
        df["Club_norm"] = df["Club"].apply(normalize_team)
        return df

    @property
    def brasileirao(self) -> pd.DataFrame:
        if self._brasileirao is None:
            self._brasileirao = self._load_brasileirao()
        return self._brasileirao

    @property
    def cup(self) -> pd.DataFrame:
        if self._cup is None:
            self._cup = self._load_cup()
        return self._cup

    @property
    def libertadores(self) -> pd.DataFrame:
        if self._libertadores is None:
            self._libertadores = self._load_libertadores()
        return self._libertadores

    @property
    def br_football(self) -> pd.DataFrame:
        if self._br_football is None:
            self._br_football = self._load_br_football()
        return self._br_football

    @property
    def historico(self) -> pd.DataFrame:
        if self._historico is None:
            self._historico = self._load_historico()
        return self._historico

    @property
    def fifa(self) -> pd.DataFrame:
        if self._fifa is None:
            self._fifa = self._load_fifa()
        return self._fifa

    @property
    def all_matches(self) -> pd.DataFrame:
        """Unified match frame from all sources."""
        if self._all_matches is None:
            frames = []
            for df, source in [
                (self.brasileirao, "brasileirao"),
                (self.cup, "cup"),
                (self.libertadores, "libertadores"),
                (self.historico, "historico"),
            ]:
                subset = df[["datetime", "date", "home_team", "away_team",
                             "home_norm", "away_norm", "home_goal", "away_goal",
                             "competition", "season"]].copy()
                subset["source"] = source
                if "round" in df.columns:
                    subset["round"] = df["round"]
                frames.append(subset)
            combined = pd.concat(frames, ignore_index=True)
            combined = combined.drop_duplicates(
                subset=["date", "home_norm", "away_norm", "home_goal", "away_goal", "competition"],
                keep="first"
            )
            self._all_matches = combined
        return self._all_matches


# Module-level singleton
_data: SoccerData | None = None


def get_data(data_dir: Path = DATA_DIR) -> SoccerData:
    global _data
    if _data is None:
        _data = SoccerData(data_dir)
    return _data
