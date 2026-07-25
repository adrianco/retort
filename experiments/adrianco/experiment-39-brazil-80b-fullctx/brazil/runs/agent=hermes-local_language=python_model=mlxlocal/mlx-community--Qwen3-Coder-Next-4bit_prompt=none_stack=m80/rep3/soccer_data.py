"""Brazilian Soccer MCP Server - Data Loading Module."""

import pandas as pd
import os
from typing import Dict, List, Optional
from datetime import datetime


class SoccerDataLoader:
    """Load and manage Brazilian soccer datasets."""
    
    def __init__(self, data_dir: str = "data/kaggle"):
        """Initialize the data loader with the path to CSV files."""
        self.data_dir = data_dir
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.team_name_mappings: Dict[str, str] = {}
        self._load_team_mappings()
    
    def _load_team_mappings(self):
        """Create team name mappings for normalization."""
        # Common Brazilian team name variations
        self.team_name_mappings = {
            # Palmeiras
            "Palmeiras": "Palmeiras",
            "Palmeiras-SP": "Palmeiras",
            "Sociedade Esportiva Palmeiras": "Palmeiras",
            
            # Flamengo
            "Flamengo": "Flamengo",
            "Flamengo-RJ": "Flamengo",
            "Clube de Regatas do Flamengo": "Flamengo",
            
            # São Paulo
            "São Paulo": "São Paulo",
            "Sao Paulo": "São Paulo",
            "São Paulo-SP": "São Paulo",
            "Sport Club São Paulo": "São Paulo",
            
            # Corinthians
            "Corinthians": "Corinthians",
            "Corinthians-SP": "Corinthians",
            "Sport Club Corinthians Paulista": "Corinthians",
            
            # Santos
            "Santos": "Santos",
            "Santos-SP": "Santos",
            "Santos Futebol Clube": "Santos",
            
            # Palmeiras variations
            "Palmeiras SP": "Palmeiras",
            "Palmeiras SP.": "Palmeiras",
            
            # São Paulo variations
            "Sao Paulo SP": "São Paulo",
            "São Paulo SP": "São Paulo",
            
            # Fluminense
            "Fluminense": "Fluminense",
            "Fluminense-RJ": "Fluminense",
            
            # Botafogo
            "Botafogo": "Botafogo",
            "Botafogo-RJ": "Botafogo",
            
            # Vasco
            "Vasco": "Vasco",
            "Vasco da Gama": "Vasco",
            "Vasco da Gama-RJ": "Vasco",
            
            # Grêmio
            "Grêmio": "Grêmio",
            "Grêmio-RS": "Grêmio",
            "Grêmio Foot-Ball Porto Alegrense": "Grêmio",
            
            # Internacional
            "Internacional": "Internacional",
            "Internacional-RS": "Internacional",
            "Sport Club Internacional": "Internacional",
            
            # Cruzeiro
            "Cruzeiro": "Cruzeiro",
            "Cruzeiro-MG": "Cruzeiro",
            "Cruzeiro Esporte Clube": "Cruzeiro",
            
            # Atlético Mineiro
            "Atlético-MG": "Atlético-MG",
            "Atletico-MG": "Atlético-MG",
            "Atlético Mineiro": "Atlético-MG",
            "Clube Atletico Mineiro": "Atlético-MG",
            
            # Goiás
            "Goiás": "Goiás",
            "Goias": "Goiás",
            
            # Avaí
            "Avaí": "Avaí",
            "Avaí FC": "Avaí",
            
            # Vasco da Gama variations
            "Vasco da Gama RJ": "Vasco",
            "Vasco da Gama - RJ": "Vasco",
        }
    
    def _normalize_team_name(self, team: str) -> str:
        """Normalize team names to a standard format."""
        if pd.isna(team):
            return team
        team = str(team).strip()
        return self.team_name_mappings.get(team, team)
    
    def load_brasileirao_matches(self) -> pd.DataFrame:
        """Load Brasileirão Serie A matches."""
        file_path = os.path.join(self.data_dir, "Brasileirao_Matches.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        df['competition'] = 'Brasileirão'
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['home_team_normalized'] = df['home_team'].apply(self._normalize_team_name)
        df['away_team_normalized'] = df['away_team'].apply(self._normalize_team_name)
        self.dataframes['brasileirao'] = df
        return df
    
    def load_copa_do_brasil_matches(self) -> pd.DataFrame:
        """Load Copa do Brasil matches."""
        file_path = os.path.join(self.data_dir, "Brazilian_Cup_Matches.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        df['competition'] = 'Copa do Brasil'
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['home_team_normalized'] = df['home_team'].apply(self._normalize_team_name)
        df['away_team_normalized'] = df['away_team'].apply(self._normalize_team_name)
        self.dataframes['copa_brasil'] = df
        return df
    
    def load_libertadores_matches(self) -> pd.DataFrame:
        """Load Copa Libertadores matches."""
        file_path = os.path.join(self.data_dir, "Libertadores_Matches.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        df['competition'] = 'Copa Libertadores'
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['home_team_normalized'] = df['home_team'].apply(self._normalize_team_name)
        df['away_team_normalized'] = df['away_team'].apply(self._normalize_team_name)
        self.dataframes['libertadores'] = df
        return df
    
    def load_br_football_dataset(self) -> pd.DataFrame:
        """Load Extended Match Statistics (BR Football Dataset)."""
        file_path = os.path.join(self.data_dir, "BR-Football-Dataset.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        df['home_team_normalized'] = df['home'].apply(self._normalize_team_name)
        df['away_team_normalized'] = df['away'].apply(self._normalize_team_name)
        self.dataframes['br_football'] = df
        return df
    
    def load_novo_campeonato(self) -> pd.DataFrame:
        """Load Historical Brasileirão (2003-2019)."""
        file_path = os.path.join(self.data_dir, "novo_campeonato_brasileiro.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        # Convert Brazilian date format DD/MM/YYYY
        df['datetime'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
        df['competition'] = 'Brasileirão'
        df['home_team_normalized'] = df['Equipe_mandante'].apply(self._normalize_team_name)
        df['away_team_normalized'] = df['Equipe_visitante'].apply(self._normalize_team_name)
        df['round'] = df['Rodada']
        df['season'] = df['Ano']
        df['home_goal'] = df['Gols_mandante']
        df['away_goal'] = df['Gols_visitante']
        self.dataframes['novo_campeonato'] = df
        return df
    
    def load_fifa_players(self) -> pd.DataFrame:
        """Load FIFA Player Database."""
        file_path = os.path.join(self.data_dir, "fifa_data.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        self.dataframes['fifa_players'] = df
        return df
    
    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all datasets."""
        self.load_brasileirao_matches()
        self.load_copa_do_brasil_matches()
        self.load_libertadores_matches()
        self.load_br_football_dataset()
        self.load_novo_campeonato()
        self.load_fifa_players()
        return self.dataframes


def get_loader() -> SoccerDataLoader:
    """Get or create a singleton data loader instance."""
    if not hasattr(get_loader, "instance"):
        get_loader.instance = SoccerDataLoader()
    return get_loader.instance
