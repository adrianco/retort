"""Data loader for Brazilian soccer datasets."""

import re
import unicodedata
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Known aliases to normalize team names to a canonical form.
# Keys must be accent-stripped and lowercase. State-aware keys (e.g. "atletico-mg")
# are matched BEFORE the state suffix is stripped in normalize_team_name.
TEAM_ALIASES: dict[str, str] = {
    # Atletico Mineiro (MG) - must come before generic "atletico"
    "atletico mineiro": "Atletico Mineiro",
    "atletico-mg": "Atletico Mineiro",
    # Athletico Paranaense (PR) - different spelling from Mineiro
    "athletico paranaense": "Athletico Paranaense",
    "athletico-pr": "Athletico Paranaense",
    "atletico paranaense": "Athletico Paranaense",
    "atletico-pr": "Athletico Paranaense",
    # Other normalizations
    "gremio": "Gremio",
    "sao paulo": "Sao Paulo",
    "goias": "Goias",
    "avai": "Avai",
    "ceara": "Ceara",
    "csa": "CSA",
    "vasco da gama": "Vasco",
}


def _strip_accents(s: str) -> str:
    """Remove diacritics from a string."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def normalize_team_name(name: str) -> str:
    """Normalize team name by removing state suffix, accents, and applying aliases."""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    # Remove parenthetical notes like "(antigo ...)"
    name = re.sub(r"\s*\([^)]+\)\s*$", "", name)
    # Check alias table BEFORE stripping state suffix, so state-aware keys work
    # e.g. "Atletico-MG" vs "Atletico-PR" must be distinguished
    key_with_state = _strip_accents(name).lower()
    if key_with_state in TEAM_ALIASES:
        return TEAM_ALIASES[key_with_state]
    # Now strip state suffix like "-SP", "-RJ", " - UF", etc.
    name = re.sub(r"\s*-\s*[A-Z]{2}\s*$", "", name)
    name = name.strip()
    # Check alias table again after stripping suffix
    key = _strip_accents(name).lower()
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    # Return with accents stripped for consistent matching
    return _strip_accents(name)


def team_matches(team_name: str, candidate: str) -> bool:
    """Check if a candidate team name matches the search term (case-insensitive, partial)."""
    norm_team = normalize_team_name(team_name).lower()
    norm_cand = normalize_team_name(candidate).lower()
    return norm_team in norm_cand or norm_cand in norm_team


def load_brasileirao() -> pd.DataFrame:
    """Load Brasileirão Serie A matches."""
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df["competition"] = "Brasileirao Serie A"
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


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


def load_br_football() -> pd.DataFrame:
    """Load extended BR football statistics dataset."""
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df = df.rename(columns={"home": "home_team", "away": "away_team", "tournament": "competition"})
    df["datetime"] = pd.to_datetime(df["date"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_historico_brasileiro() -> pd.DataFrame:
    """Load historical Brasileirão 2003-2019 dataset."""
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    df["competition"] = "Brasileirao Serie A"
    df["datetime"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df = df.rename(
        columns={
            "Equipe_mandante": "home_team",
            "Equipe_visitante": "away_team",
            "Gols_mandante": "home_goal",
            "Gols_visitante": "away_goal",
            "Ano": "season",
            "Rodada": "round",
        }
    )
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_fifa_players() -> pd.DataFrame:
    """Load FIFA player database."""
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8")
    # Drop unnamed first column if present
    if df.columns[0].startswith("Unnamed") or df.columns[0] == "":
        df = df.iloc[:, 1:]
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    return df


class DataStore:
    """Central data store that loads and caches all datasets."""

    def __init__(self):
        self._brasileirao = None
        self._copa_brasil = None
        self._libertadores = None
        self._br_football = None
        self._historico = None
        self._fifa = None

    @property
    def brasileirao(self) -> pd.DataFrame:
        if self._brasileirao is None:
            self._brasileirao = load_brasileirao()
        return self._brasileirao

    @property
    def copa_brasil(self) -> pd.DataFrame:
        if self._copa_brasil is None:
            self._copa_brasil = load_copa_brasil()
        return self._copa_brasil

    @property
    def libertadores(self) -> pd.DataFrame:
        if self._libertadores is None:
            self._libertadores = load_libertadores()
        return self._libertadores

    @property
    def br_football(self) -> pd.DataFrame:
        if self._br_football is None:
            self._br_football = load_br_football()
        return self._br_football

    @property
    def historico(self) -> pd.DataFrame:
        if self._historico is None:
            self._historico = load_historico_brasileiro()
        return self._historico

    @property
    def fifa(self) -> pd.DataFrame:
        if self._fifa is None:
            self._fifa = load_fifa_players()
        return self._fifa

    def all_matches(self) -> pd.DataFrame:
        """Return all matches from all datasets combined.

        Strategy: prefer the primary datasets (brasileirao, copa, libertadores).
        Only include historico rows for seasons NOT covered by brasileirao to
        avoid double-counting (the historico and brasileirao overlap 2012-2019
        but use different datetime formats that break naive deduplication).
        """
        cols = ["datetime", "home_team", "away_team", "home_team_norm", "away_team_norm",
                "home_goal", "away_goal", "season", "competition"]
        frames = []
        for df in [self.brasileirao, self.copa_brasil, self.libertadores]:
            available = [c for c in cols if c in df.columns]
            frames.append(df[available])

        # Only add historico seasons not already in brasileirao
        br_seasons = set(self.brasileirao["season"].dropna().unique())
        df_h = self.historico
        df_h_extra = df_h[~df_h["season"].isin(br_seasons)]
        if not df_h_extra.empty:
            available = [c for c in cols if c in df_h_extra.columns]
            frames.append(df_h_extra[available])

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["datetime", "home_team_norm", "away_team_norm", "home_goal", "away_goal"],
            keep="first"
        )
        return combined


# Singleton
store = DataStore()
