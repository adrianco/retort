"""
Data Loader Module for Brazilian Soccer MCP Server.

Loads and normalizes all 6 Kaggle CSV datasets for querying:
  - Brasileirao Serie A Matches (Brasileirao_Matches.csv)
  - Copa do Brasil Matches (Brazilian_Cup_Matches.csv)
  - Copa Libertadores Matches (Libertadores_Matches.csv)
  - Extended Match Statistics (BR-Football-Dataset.csv)
  - Historical Brasileirao (novo_campeonato_brasileiro.csv)
  - FIFA Player Database (fifa_data.csv)

Team name normalization strips state suffixes (e.g. "Flamengo-RJ" -> "Flamengo")
and handles various naming conventions across datasets.
"""

import os
import re
import unicodedata
from typing import Dict, List, Optional, Any

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'kaggle')


# Known club alias mapping: lowercase alias -> canonical club name
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
    "mirassol": "Mirassol",
    "ponte preta": "Ponte Preta",
    "bragantino": "Red Bull Bragantino",
    "red bull bragantino": "Red Bull Bragantino",
    "botafogo sp": "Botafogo-SP",
    "chapecoense": "Chapecoense",
    "chapeco": "Chapecoense",
    "londrina": "Londrina",
    "gama": "Gama",
    "guarani": "Guarani",
    "boavista": "Boavista",
    "fluminense rj": "Fluminense",
    "figueirense": "Figueirense",
    "ponte": "Ponte Preta",
    "serrano": "Serrano",
    "amazonas": "Amazonas",
    "macae": "Macaue",
    "paysandu": "Paysandu",
    "rem": "Rem",
}


def normalize_team_name(name: str) -> str:
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


def find_best_match(raw_name: str) -> str:
    """
    Try to resolve a raw team name to a canonical club name.
    Returns the canonical name if a match is found, otherwise returns
    the cleaned/normalized name.
    """
    if not raw_name:
        return ""
    normalized = normalize_team_name(raw_name)
    name_lower = normalized.lower()

    # Direct lookup match
    if name_lower in _CLUB_ALIASES:
        return _CLUB_ALIASES[name_lower]

    # Substring match -- prefer longer/more specific aliases first
    for alias in sorted(_CLUB_ALIASES.keys(), key=len, reverse=True):
        canonical = _CLUB_ALIASES[alias]
        if len(alias) >= 4 and (alias in name_lower or name_lower in alias):
            return canonical

    return normalized


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats into ISO format YYYY-MM-DD."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    from datetime import datetime
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


class DataLoader:
    """Loads all soccer datasets into memory as Pandas DataFrames."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = DATA_DIR
        self.data_dir = data_dir
        self.brasileirao_df: Optional[pd.DataFrame] = None
        self.brazilian_cup_df: Optional[pd.DataFrame] = None
        self.libertadores_df: Optional[pd.DataFrame] = None
        self.br_football_df: Optional[pd.DataFrame] = None
        self.novo_campeonato_df: Optional[pd.DataFrame] = None
        self.fifa_df: Optional[pd.DataFrame] = None

    def load_all(self) -> None:
        """Load every dataset."""
        self.load_brasileirao()
        self.load_brazilian_cup()
        self.load_libertadores()
        self.load_br_football()
        self.load_novo_campeonato()
        self.load_fifa()

    def _standardize_match(
        self, df: pd.DataFrame, source: str,
        home_col: str, away_col: str,
        hg_col: str, ag_col: str,
        dt_col: Optional[str] = None,
        season_col: Optional[str] = None,
        round_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Reindex match data to a common schema.
        """
        # Build columns as lists first to avoid index-alignment bugs
        n = len(df)
        rows = []
        for _, r in df.iterrows():
            home = find_best_match(str(r.get(home_col, '')))
            away = find_best_match(str(r.get(away_col, '')))

            # Date
            date_val = ''
            if dt_col and dt_col in df.columns and pd.notna(r.get(dt_col)):
                parsed = parse_date(str(r[dt_col]))
                date_val = parsed if parsed else ''

            # Season
            season_val = pd.NA
            if season_col and season_col in df.columns and pd.notna(r.get(season_col)):
                season_val = r[season_col]

            # Round
            round_val = pd.NA
            if round_col and round_col in df.columns and pd.notna(r.get(round_col)):
                round_val = r[round_col]

            # Stage
            stage_val = ''
            if 'stage' in df.columns and pd.notna(r.get('stage')):
                stage_val = str(r['stage'])

            rows.append({
                'source': source,
                'date': date_val,
                'season': season_val,
                'round': round_val,
                'stage': stage_val,
                'home_team': home,
                'away_team': away,
                'home_goals': int(pd.to_numeric(r.get(hg_col, 0), errors='coerce') or 0),
                'away_goals': int(pd.to_numeric(r.get(ag_col, 0), errors='coerce') or 0),
            })

        result = pd.DataFrame(rows)

        # Handle BR Football tournament suffix
        if source == 'BR_Football' and 'tournament' in df.columns:
            result['source'] = result['source'] + ': ' + df['tournament'].astype(str)

        return result

    def load_brasileirao(self) -> None:
        path = os.path.join(self.data_dir, 'Brasileirao_Matches.csv')
        df = pd.read_csv(path)
        self.brasileirao_df = self._standardize_match(
            df, 'Brasileirao',
            home_col='home_team', away_col='away_team',
            hg_col='home_goal', ag_col='away_goal',
            dt_col='datetime', season_col='season', round_col='round',
        )

    def load_brazilian_cup(self) -> None:
        path = os.path.join(self.data_dir, 'Brazilian_Cup_Matches.csv')
        df = pd.read_csv(path)
        self.brazilian_cup_df = self._standardize_match(
            df, 'Brazilian_Cup',
            home_col='home_team', away_col='away_team',
            hg_col='home_goal', ag_col='away_goal',
            dt_col='datetime', season_col='season', round_col='round',
        )

    def load_libertadores(self) -> None:
        path = os.path.join(self.data_dir, 'Libertadores_Matches.csv')
        df = pd.read_csv(path)
        self.libertadores_df = self._standardize_match(
            df, 'Libertadores',
            home_col='home_team', away_col='away_team',
            hg_col='home_goal', ag_col='away_goal',
            dt_col='datetime', season_col='season', round_col=None,
        )

    def load_br_football(self) -> None:
        path = os.path.join(self.data_dir, 'BR-Football-Dataset.csv')
        df = pd.read_csv(path)
        self.br_football_df = self._standardize_match(
            df, 'BR_Football',
            home_col='home', away_col='away',
            hg_col='home_goal', ag_col='away_goal',
            dt_col='date', season_col=None, round_col=None,
        )

    def load_novo_campeonato(self) -> None:
        path = os.path.join(self.data_dir, 'novo_campeonato_brasileiro.csv')
        df = pd.read_csv(path, encoding='utf-8')
        self.novo_campeonato_df = self._standardize_match(
            df, 'Novo_Campeonato',
            home_col='Equipe_mandante', away_col='Equipe_visitante',
            hg_col='Gols_mandante', ag_col='Gols_visitante',
            dt_col='Data', season_col='Ano', round_col='Rodada',
        )

    def load_fifa(self) -> None:
        path = os.path.join(self.data_dir, 'fifa_data.csv')
        df = pd.read_csv(path, encoding='latin-1')
        df['Name'] = df['Name'].astype(str).str.strip()
        df['Club'] = df['Club'].astype(str).str.strip()
        df['Nationality'] = df['Nationality'].astype(str).str.strip()
        df['Position'] = df['Position'].astype(str).str.strip()
        df['Overall'] = pd.to_numeric(df['Overall'], errors='coerce').fillna(0).astype(int)
        df['Potential'] = pd.to_numeric(df['Potential'], errors='coerce').fillna(0).astype(int)
        self.fifa_df = df

    @property
    def all_matches(self) -> pd.DataFrame:
        """Return all matches from every dataset concatenated."""
        dfs = [
            self.brasileirao_df,
            self.brazilian_cup_df,
            self.libertadores_df,
            self.br_football_df,
            self.novo_campeonato_df,
        ]
        return pd.concat(dfs, ignore_index=True).reset_index(drop=True)


def load_all(data_dir: Optional[str] = None) -> DataLoader:
    """Helper: create a DataLoader, load everything, return it."""
    dl = DataLoader(data_dir)
    dl.load_all()
    return dl
