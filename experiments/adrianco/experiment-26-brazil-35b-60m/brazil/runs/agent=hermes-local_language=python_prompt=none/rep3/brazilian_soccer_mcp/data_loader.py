"""Data loading module for Brazilian soccer datasets."""

import re
from pathlib import Path
from typing import Optional

import pandas as pd


DATA_DIR = Path(__file__).parent.parent / "data" / "kaggle"


# Normalize team names: strip state suffixes and clean up
def normalize_team_name(name: str) -> str:
    """Normalize team names by removing state suffixes and cleaning up."""
    if not name or not isinstance(name, str):
        return ""
    name = name.strip()
    # Remove state suffixes like -SP, -RJ, -MG, etc.
    name = re.sub(r'-(?:[A-Z]{2})$', '', name)
    # Remove parenthetical state descriptions like " - MG"
    name = re.sub(r'\s*-?\s*[A-Z]{2}\s*$', '', name)
    # Remove content like "(antigo Esporte Clube Barreira) - RJ"
    name = re.sub(r'\(.*?\)\s*-?\s*[A-Z]{2}?\s*$', '', name)
    name = re.sub(r'\(.*?\)\s*$', '', name)
    # Remove "Sport Club (antigo ...)" prefix patterns but keep team names
    name = re.sub(r'^\w+\s+(?:Sport\s+Club|Esporte\s+Clube|Futebol\s+Clube)\s*\(.*?\)\s*-\s*\w+\s*$', '', name, flags=re.IGNORECASE)
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# Portuguese date parsing
def parse_brazilian_date(date_str: str) -> Optional[str]:
    """Parse Brazilian date format DD/MM/YYYY to ISO format."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    # Try Brazilian format: DD/MM/YYYY or DD.MM.YYYY
    for fmt in ['%d/%m/%Y', '%d.%m.%Y']:
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    # Try ISO format
    try:
        from datetime import datetime
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return None


def load_brasileirao_matches() -> pd.DataFrame:
    """Load Brasileirao Serie A matches from CSV."""
    filepath = DATA_DIR / "Brasileirao_Matches.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    # Rename columns for consistency
    df = df.rename(columns={
        'datetime': 'date',
        'home_team': 'home_team',
        'home_team_state': 'home_team_state',
        'away_team': 'away_team',
        'away_team_state': 'away_team_state',
        'home_goal': 'home_goal',
        'away_goal': 'away_goal',
        'season': 'season',
        'round': 'round',
    })
    df['competition'] = 'Brasileirao'
    df['source'] = 'Brasileirao_Matches'
    df['stage'] = None
    # Parse dates
    df['date'] = pd.to_datetime(df['date'])
    df['home_team'] = df['home_team'].astype(str).str.strip()
    df['away_team'] = df['away_team'].astype(str).str.strip()
    df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
    df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
    df['round'] = df['round'].astype(int)
    return df


def load_copa_brasil_matches() -> pd.DataFrame:
    """Load Copa do Brasil matches from CSV."""
    filepath = DATA_DIR / "Brazilian_Cup_Matches.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    df = df.rename(columns={
        'datetime': 'date',
        'home_team': 'home_team',
        'away_team': 'away_team',
        'home_goal': 'home_goal',
        'away_goal': 'away_goal',
        'season': 'season',
        'round': 'round',
    })
    df['competition'] = 'Copa do Brasil'
    df['source'] = 'Brazilian_Cup_Matches'
    df['stage'] = None
    df['date'] = pd.to_datetime(df['date'])
    df['home_team'] = df['home_team'].astype(str).str.strip()
    df['away_team'] = df['away_team'].astype(str).str.strip()
    df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
    df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
    return df


def load_libertadores_matches() -> pd.DataFrame:
    """Load Copa Libertadores matches from CSV."""
    filepath = DATA_DIR / "Libertadores_Matches.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    df = df.rename(columns={
        'datetime': 'date',
        'home_team': 'home_team',
        'away_team': 'away_team',
        'home_goal': 'home_goal',
        'away_goal': 'away_goal',
        'season': 'season',
        'stage': 'stage',
    })
    df['competition'] = 'Libertadores'
    df['source'] = 'Libertadores_Matches'
    df['round'] = None
    df['date'] = pd.to_datetime(df['date'])
    df['home_team'] = df['home_team'].astype(str).str.strip()
    df['away_team'] = df['away_team'].astype(str).str.strip()
    df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
    df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
    return df


def load_extended_match_stats() -> pd.DataFrame:
    """Load extended match statistics from CSV."""
    filepath = DATA_DIR / "BR-Football-Dataset.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    # Map columns to standard format
    df = df.rename(columns={
        'home': 'home_team',
        'away': 'away_team',
        'home_goal': 'home_goal',
        'away_goal': 'away_goal',
    })
    # Combine date and time
    if 'date' in df.columns and 'time' in df.columns:
        df['date'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str).str.strip())
    
    df['competition'] = df.get('tournament', 'Unknown').astype(str)
    df['source'] = 'BR-Football-Dataset'
    df['stage'] = None
    df['season'] = pd.to_datetime(df['date']).dt.year
    df['round'] = None
    df['home_team'] = df['home_team'].astype(str).str.strip()
    df['away_team'] = df['away_team'].astype(str).str.strip()
    df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
    df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
    return df


def load_historical_campeonato() -> pd.DataFrame:
    """Load historical Campeonato Brasileiro (2003-2019) from CSV."""
    filepath = DATA_DIR / "novo_campeonato_brasileiro.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    df = df.rename(columns={
        'Equipe_mandante': 'home_team',
        'Equipe_visitante': 'away_team',
        'Gols_mandante': 'home_goal',
        'Gols_visitante': 'away_goal',
        'Ano': 'season',
        'Rodada': 'round',
        'Vencedor': 'winner',
        'Arena': 'stadium',
    })
    
    # Parse Brazilian date format
    df['date'] = df['Data'].apply(parse_brazilian_date)
    df['date'] = pd.to_datetime(df['date'])
    
    df['competition'] = 'Campeonato Historico'
    df['source'] = 'novo_campeonato_brasileiro'
    df['stage'] = None
    df['home_team'] = df['home_team'].astype(str).str.strip()
    df['away_team'] = df['away_team'].astype(str).str.strip()
    df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
    df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
    df['home_team_state'] = df.get('Mandante_UF', '')
    df['away_team_state'] = df.get('Visitante_UF', '')
    return df


def load_fifa_players() -> pd.DataFrame:
    """Load FIFA player database from CSV."""
    filepath = DATA_DIR / "fifa_data.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath, index_col=0)
    
    # Map columns
    df = df.rename(columns={
        'Name': 'name',
        'Age': 'age',
        'Nationality': 'nationality',
        'Overall': 'overall',
        'Potential': 'potential',
        'Club': 'club',
        'Position': 'position',
        'Jersey Number': 'jersey_number',
        'Height': 'height',
        'Weight': 'weight',
    })
    
    # Clean data types
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df['overall'] = pd.to_numeric(df['overall'], errors='coerce')
    df['potential'] = pd.to_numeric(df['potential'], errors='coerce')
    df['name'] = df['name'].astype(str).str.strip()
    df['nationality'] = df['nationality'].astype(str).str.strip()
    df['club'] = df['club'].astype(str).str.strip()
    df['position'] = df['position'].astype(str).str.strip()
    return df


class DataLoader:
    """Central data loader for all Brazilian soccer datasets."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is not None:
            global DATA_DIR
            DATA_DIR = data_dir
        self._brasileirao: Optional[pd.DataFrame] = None
        self._copa_brasil: Optional[pd.DataFrame] = None
        self._libertadores: Optional[pd.DataFrame] = None
        self._extended_stats: Optional[pd.DataFrame] = None
        self._historical: Optional[pd.DataFrame] = None
        self._players: Optional[pd.DataFrame] = None
    
    @property
    def brasileirao(self) -> pd.DataFrame:
        if self._brasileirao is None:
            self._brasileirao = load_brasileirao_matches()
        return self._brasileirao
    
    @property
    def copa_brasil(self) -> pd.DataFrame:
        if self._copa_brasil is None:
            self._copa_brasil = load_copa_brasil_matches()
        return self._copa_brasil
    
    @property
    def libertadores(self) -> pd.DataFrame:
        if self._libertadores is None:
            self._libertadores = load_libertadores_matches()
        return self._libertadores
    
    @property
    def extended_stats(self) -> pd.DataFrame:
        if self._extended_stats is None:
            self._extended_stats = load_extended_match_stats()
        return self._extended_stats
    
    @property
    def historical(self) -> pd.DataFrame:
        if self._historical is None:
            self._historical = load_historical_campeonato()
        return self._historical
    
    @property
    def players(self) -> pd.DataFrame:
        if self._players is None:
            self._players = load_fifa_players()
        return self._players
    
    def all_matches(self) -> pd.DataFrame:
        """Return all matches from all sources combined."""
        frames = [
            self.brasileirao,
            self.copa_brasil,
            self.libertadores,
            self.extended_stats,
            self.historical,
        ]
        return pd.concat(frames, ignore_index=True)
    
    def search_teams(self, query: str) -> list[str]:
        """Search for teams across all match data."""
        all_matches = self.all_matches()
        teams = set()
        for col in ['home_team', 'away_team']:
            mask = all_matches[col].str.contains(query, case=False, na=False, regex=False)
            for team in all_matches.loc[mask, col]:
                teams.add(team)
        return sorted(teams)
