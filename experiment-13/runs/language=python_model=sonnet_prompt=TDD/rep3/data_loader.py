"""Load and normalize Brazilian soccer CSV datasets."""
import os
import re
import pandas as pd
from datetime import datetime
from functools import cached_property


def normalize_team_name(name: str | None) -> str | None:
    """Strip trailing state suffix (e.g. '-SP', '- RJ') from team names."""
    if name is None:
        return None
    # Strip ' - XX' or '-XX' at end where XX is 2 uppercase letters
    cleaned = re.sub(r"\s*-\s*[A-Z]{2}$", "", str(name).strip())
    return cleaned


def parse_date(value: str) -> datetime | None:
    """Parse date strings in various formats used by the datasets."""
    if not value or not isinstance(value, str):
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


class DataLoader:
    """Loads all 6 CSV datasets and exposes them as normalized DataFrames."""

    def __init__(self, data_dir: str):
        self._data_dir = data_dir

    def _path(self, filename: str) -> str:
        return os.path.join(self._data_dir, filename)

    @cached_property
    def brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Brasileirao_Matches.csv"))
        df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
        df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
        df["competition"] = "Brasileirão"
        return df

    @cached_property
    def cup(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Brazilian_Cup_Matches.csv"))
        df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
        df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
        df["competition"] = "Copa do Brasil"
        return df

    @cached_property
    def libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Libertadores_Matches.csv"))
        df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
        df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
        df["competition"] = "Copa Libertadores"
        return df

    @cached_property
    def extended_stats(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("BR-Football-Dataset.csv"))
        df["home_team_norm"] = df["home"].apply(normalize_team_name)
        df["away_team_norm"] = df["away"].apply(normalize_team_name)
        return df

    @cached_property
    def historical(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("novo_campeonato_brasileiro.csv"))
        # Rename Portuguese columns to English
        rename_map = {
            "Equipe_mandante": "home_team",
            "Equipe_visitante": "away_team",
            "Gols_mandante": "home_goal",
            "Gols_visitante": "away_goal",
            "Ano": "season",
            "Rodada": "round",
            "Vencedor": "winner",
            "Arena": "arena",
            "Data": "datetime",
            "Mandante_UF": "home_team_state",
            "Visitante_UF": "away_team_state",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
        df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
        df["competition"] = "Brasileirão"
        return df

    @cached_property
    def fifa(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("fifa_data.csv"), low_memory=False)
        # Strip BOM from first column if present
        df.columns = [c.lstrip("﻿").strip() for c in df.columns]
        return df

    @cached_property
    def all_matches(self) -> pd.DataFrame:
        """Combined DataFrame from brasileirao, cup, libertadores, and historical."""
        shared_cols = ["home_team", "away_team", "home_team_norm", "away_team_norm",
                       "home_goal", "away_goal", "season", "competition", "datetime"]
        frames = []
        for df in (self.brasileirao, self.cup, self.libertadores, self.historical):
            available = [c for c in shared_cols if c in df.columns]
            frames.append(df[available])
        combined = pd.concat(frames, ignore_index=True)
        return combined
