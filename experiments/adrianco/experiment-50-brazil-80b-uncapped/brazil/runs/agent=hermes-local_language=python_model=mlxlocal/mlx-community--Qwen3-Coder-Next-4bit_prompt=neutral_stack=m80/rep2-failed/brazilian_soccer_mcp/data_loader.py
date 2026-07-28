"""Data loading and management for Brazilian soccer datasets."""

import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd


class DataFileManager:
    """Manages loading and accessing all Brazilian soccer datasets."""
    
    def __init__(self, data_dir: str = None):
        """Initialize with path to data directory."""
        if data_dir is None:
            # Default to data/kaggle relative to this module
            module_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(module_dir, '..', 'data', 'kaggle')
        
        self.data_dir = os.path.abspath(data_dir)
        self._dataframes = {}
        self._team_name_map = {}  # Maps variations to canonical names
        self._load_team_mappings()
    
    def _load_team_mappings(self):
        """Load team name normalization mappings."""
        # Common Brazilian team name variations
        self._team_name_map = {
            # Flamengo
            'flamengo': 'Flamengo',
            'flamengo-rj': 'Flamengo',
            'flamengo RJ': 'Flamengo',
            # Fluminense
            'fluminense': 'Fluminense',
            'fluminense-rj': 'Fluminense',
            'fluminense RJ': 'Fluminense',
            # Palmeiras
            'palmeiras': 'Palmeiras',
            'palmeiras-sp': 'Palmeiras',
            'palmeiras SP': 'Palmeiras',
            # São Paulo
            'são paulo': 'São Paulo',
            'sao paulo': 'São Paulo',
            'sao paulo-sp': 'São Paulo',
            'sao paulo SP': 'São Paulo',
            # Corinthians
            'corinthians': 'Corinthians',
            'corinthians-sp': 'Corinthians',
            'corinthians SP': 'Corinthians',
            'sport club corinthians paulista': 'Corinthians',
            # Santos
            'santos': 'Santos',
            'santos-sp': 'Santos',
            'santos SP': 'Santos',
            # Palmeiras variations
            'ec palmeiras': 'Palmeiras',
            # Grêmio
            'grêmio': 'Grêmio',
            'gremio': 'Grêmio',
            'grêmio-rs': 'Grêmio',
            'gremio-rs': 'Grêmio',
            # Internacional
            'internacional': 'Internacional',
            'internacional-rs': 'Internacional',
            # Cruzeiro
            'cruzeiro': 'Cruzeiro',
            'cruzeiro-mg': 'Cruzeiro',
            'cruzeiro MG': 'Cruzeiro',
            # Atlético-MG
            'atletico-mg': 'Atlético-MG',
            'atletico mg': 'Atlético-MG',
            'atlético-mg': 'Atlético-MG',
            'atlético MG': 'Atlético-MG',
            # Vasco
            'vasco': 'Vasco',
            'vasco da gama': 'Vasco',
            # Botafogo
            'botafogo': 'Botafogo',
            'botafogo-rj': 'Botafogo',
            'botafogo RJ': 'Botafogo',
            # Fluminense
            'fluminense fc': 'Fluminense',
            # Bahia
            'bahia': 'Bahia',
            'bahia de feira': 'Bahia',
            # Ponte Preta
            'ponte preta': 'Ponte Preta',
            'ponte preta-sp': 'Ponte Preta',
            # Athletico-PR
            'athletico-pr': 'Athletico-PR',
            'athletico pr': 'Athletico-PR',
            'athletico paranaense': 'Athletico-PR',
            # Cruzeiro
            'cruzeiro esporte clube': 'Cruzeiro',
            # Avaí
            'avaí': 'Avaí',
            'avai': 'Avaí',
            # Juventude
            'juventude': 'Juventude',
            'juventude-rs': 'Juventude',
        }
    
    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team names for consistent matching."""
        if not team_name:
            return ""
        
        # Remove state suffix if present (e.g., "-SP", "-RJ")
        normalized = re.sub(r'-[A-Z]{2}$', '', str(team_name).strip())
        normalized = re.sub(r' [A-Z]{2}$', '', normalized)
        
        # Convert to title case for lookup
        lookup_name = normalized.lower()
        
        # Check in our mapping
        if lookup_name in self._team_name_map:
            return self._team_name_map[lookup_name]
        
        # Return normalized version
        return normalized.strip()
    
    def load_dataframe(self, filename: str) -> pd.DataFrame:
        """Load a CSV file into a DataFrame."""
        if filename in self._dataframes:
            return self._dataframes[filename]
        
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Determine encoding and read
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
        except UnicodeDecodeError:
            # Try with latin-1 for Brazilian Portuguese characters
            df = pd.read_csv(filepath, encoding='latin-1')
        
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        
        self._dataframes[filename] = df
        return df
    
    def get_brasileirao_matches(self) -> pd.DataFrame:
        """Load Brasileirão Serie A matches."""
        return self.load_dataframe('Brasileirao_Matches.csv')
    
    def get_copa_do_brasil_matches(self) -> pd.DataFrame:
        """Load Copa do Brasil matches."""
        return self.load_dataframe('Brazilian_Cup_Matches.csv')
    
    def get_libertadores_matches(self) -> pd.DataFrame:
        """Load Copa Libertadores matches."""
        return self.load_dataframe('Libertadores_Matches.csv')
    
    def get_extended_matches(self) -> pd.DataFrame:
        """Load extended match statistics."""
        return self.load_dataframe('BR-Football-Dataset.csv')
    
    def get_historical_brasileirao(self) -> pd.DataFrame:
        """Load historical Brasileirão data (2003-2019)."""
        return self.load_dataframe('novo_campeonato_brasileiro.csv')
    
    def get_fifa_players(self) -> pd.DataFrame:
        """Load FIFA player data."""
        return self.load_dataframe('fifa_data.csv')
    
    def get_all_matches(self) -> pd.DataFrame:
        """Load and combine all match data."""
        dfs = []
        
        # Brasileirão
        try:
            df = self.get_brasileirao_matches()
            df['competition'] = 'Brasileirão'
            dfs.append(df)
        except Exception:
            pass
        
        # Copa do Brasil
        try:
            df = self.get_copa_do_brasil_matches()
            df['competition'] = 'Copa do Brasil'
            dfs.append(df)
        except Exception:
            pass
        
        # Libertadores
        try:
            df = self.get_libertadores_matches()
            df['competition'] = 'Copa Libertadores'
            dfs.append(df)
        except Exception:
            pass
        
        # Extended matches
        try:
            df = self.get_extended_matches()
            dfs.append(df)
        except Exception:
            pass
        
        # Historical Brasileirão
        try:
            df = self.get_historical_brasileirao()
            dfs.append(df)
        except Exception:
            pass
        
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats found in the datasets."""
    if pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    # Try different formats
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2023-09-24 18:30:00
        '%Y-%m-%d',           # 2023-09-24
        '%d/%m/%Y',           # 29/03/2003
        '%Y/%m/%d',           # 2023/09/24
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.split()[0], fmt)
        except ValueError:
            continue
    
    return None


def normalize_team_name(df: pd.DataFrame, team_columns: List[str]) -> pd.DataFrame:
    """Normalize team names in specified columns."""
    dfm = DataFileManager()
    for col in team_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: dfm.normalize_team_name(str(x)) if pd.notna(x) else x)
    return df
