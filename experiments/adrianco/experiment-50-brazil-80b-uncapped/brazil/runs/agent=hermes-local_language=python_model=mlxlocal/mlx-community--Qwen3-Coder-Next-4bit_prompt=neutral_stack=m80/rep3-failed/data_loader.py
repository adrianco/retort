"""
Brazilian Soccer Data Loader
Loads and manages all soccer CSV data files
"""

import os
import re
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"


class SoccerDataLoader:
    """Load and manage all soccer data"""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.brasileirao_df = None
        self.copa_do_brasil_df = None
        self.libertadores_df = None
        self.br_football_df = None
        self.campeonato_brasileiro_df = None
        self.fifa_df = None
        self._load_all_data()

    def _load_all_data(self):
        """Load all CSV files"""
        print("Loading soccer data files...")
        
        brasileirao_path = self.data_dir / "Brasileirao_Matches.csv"
        if brasileirao_path.exists():
            self.brasileirao_df = pd.read_csv(brasileirao_path)
            self.brasileirao_df['competition'] = 'Brasileirão'
            print(f"  - Brasileirão: {len(self.brasileirao_df)} matches")

        copa_path = self.data_dir / "Brazilian_Cup_Matches.csv"
        if copa_path.exists():
            self.copa_do_brasil_df = pd.read_csv(copa_path)
            self.copa_do_brasil_df['competition'] = 'Copa do Brasil'
            print(f"  - Copa do Brasil: {len(self.copa_do_brasil_df)} matches")

        libertadores_path = self.data_dir / "Libertadores_Matches.csv"
        if libertadores_path.exists():
            self.libertadores_df = pd.read_csv(libertadores_path)
            self.libertadores_df['competition'] = 'Copa Libertadores'
            print(f"  - Copa Libertadores: {len(self.libertadores_df)} matches")

        br_football_path = self.data_dir / "BR-Football-Dataset.csv"
        if br_football_path.exists():
            self.br_football_df = pd.read_csv(br_football_path)
            print(f"  - BR Football Dataset: {len(self.br_football_df)} matches")

        campeonato_path = self.data_dir / "novo_campeonato_brasileiro.csv"
        if campeonato_path.exists():
            self.campeonato_brasileiro_df = pd.read_csv(
                campeonato_path, encoding='latin1', on_bad_lines='skip'
            )
            print(f"  - Campeonato Brasileiro 2003-2019: {len(self.campeonato_brasileiro_df)} matches")

        fifa_path = self.data_dir / "fifa_data.csv"
        if fifa_path.exists():
            self.fifa_df = pd.read_csv(fifa_path, encoding='latin1', on_bad_lines='skip')
            print(f"  - FIFA Players: {len(self.fifa_df)} players")
        
        print("Data loading complete!")

    def normalize_team_name(self, team: str) -> str:
        """Normalize team names for consistent matching"""
        if not team:
            return ""
        normalized = re.sub(r'-[A-Z]{2}$', '', str(team))
        normalized = normalized.strip()
        normalized = re.sub(r'\s*\([^)]*\)\s*$', '', normalized)
        normalized = normalized.strip()
        return normalized

    def get_team_column(self, row: pd.Series, side: str) -> str:
        """Extract team name from row"""
        for col in [f'{side}_team', side, f'Equipe_{side}']:
            if col in row.index and pd.notna(row[col]):
                return str(row[col])
        return ""

    def get_season_column(self, row: pd.Series) -> Optional[int]:
        """Extract season year from row"""
        for col in ['season', 'Ano', 'Year']:
            if col in row.index and pd.notna(row[col]):
                try:
                    val = row[col]
                    if isinstance(val, (int, float)):
                        return int(float(val))
                    if isinstance(val, str):
                        return int(float(val))
                except (ValueError, TypeError):
                    pass
        return None

    def get_date_column(self, row: pd.Series) -> Optional[str]:
        """Extract and normalize match date"""
        for col in ['datetime', 'date', 'Data']:
            if col in row.index and pd.notna(row[col]):
                try:
                    date_val = str(row[col])
                    if '/' in date_val:
                        parts = date_val.split('/')
                        if len(parts) == 3:
                            return f"{parts[2]}-{parts[1]}-{parts[0]}"
                    elif ' ' in date_val:
                        return date_val.split(' ')[0]
                    return date_val
                except Exception:
                    pass
        return None

    def get_goals_column(self, row: pd.Series, side: str) -> int:
        """Extract goals from row"""
        for col in [f'{side}_goal', f'{side.lower()}_goal', f'Gols_{side}']:
            if col in row.index:
                try:
                    val = row[col]
                    if pd.notna(val):
                        return int(float(val))
                except (ValueError, TypeError):
                    pass
        return 0

    def get_round_column(self, row: pd.Series) -> Optional[int]:
        """Extract round from row"""
        for col in ['round', 'Rodada']:
            if col in row.index:
                try:
                    val = row[col]
                    if pd.notna(val):
                        return int(float(val))
                except (ValueError, TypeError):
                    pass
        return None

    def get_stage_column(self, row: pd.Series) -> Optional[str]:
        """Extract stage from row"""
        for col in ['stage', 'Stage']:
            if col in row.index and pd.notna(row[col]):
                return str(row[col])
        return None

    def get_all_matches(self, 
                       home_team: Optional[str] = None,
                       away_team: Optional[str] = None,
                       competition: Optional[str] = None,
                       season: Optional[int] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> List[Dict]:
        """Get matches with optional filters"""
        matches = []
        dfs = [
            (self.brasileirao_df, 'Brasileirão'),
            (self.copa_do_brasil_df, 'Copa do Brasil'),
            (self.libertadores_df, 'Copa Libertadores'),
            (self.br_football_df, 'BR Football' if self.br_football_df is not None else None),
            (self.campeonato_brasileiro_df, 'Brasileirão'),
        ]
        
        for df, comp_name in dfs:
            if df is None or comp_name is None:
                continue
            for _, row in df.iterrows():
                home = self.get_team_column(row, 'home')
                away = self.get_team_column(row, 'away')
                
                if home_team:
                    h_normalized = self.normalize_team_name(home).lower()
                    if home_team.lower() not in [home.lower(), h_normalized]:
                        continue
                if away_team:
                    a_normalized = self.normalize_team_name(away).lower()
                    if away_team.lower() not in [away.lower(), a_normalized]:
                        continue
                if competition and competition.lower() not in comp_name.lower():
                    continue
                
                if season:
                    row_season = self.get_season_column(row)
                    if row_season != season:
                        continue
                
                if date_from or date_to:
                    match_date = self.get_date_column(row)
                    if match_date:
                        if date_from and match_date < date_from:
                            continue
                        if date_to and match_date > date_to:
                            continue
                
                match = self._format_match(row, comp_name)
                matches.append(match)
        
        return matches

    def _format_match(self, row: pd.Series, competition: str) -> Dict:
        """Format match data"""
        return {
            'datetime': self.get_date_column(row) or '',
            'home_team': self.get_team_column(row, 'home'),
            'away_team': self.get_team_column(row, 'away'),
            'home_goal': self.get_goals_column(row, 'home'),
            'away_goal': self.get_goals_column(row, 'away'),
            'competition': competition,
            'season': self.get_season_column(row),
            'round': self.get_round_column(row),
            'stage': self.get_stage_column(row),
        }
