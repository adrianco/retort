"""
Data loader for Brazilian Soccer MCP Server.
Loads and normalizes all 6 Kaggle CSV datasets into unified DataFrames.

Datasets:
1. Brasileirao_Matches.csv - Serie A matches (4180 matches)
2. Brazilian_Cup_Matches.csv - Copa do Brasil matches (1337 matches)
3. Libertadores_Matches.csv - Copa Libertadores matches (1255 matches)
4. BR-Football-Dataset.csv - Extended match statistics (10296 matches)
5. novo_campeonato_brasileiro.csv - Historical Brasileirao 2003-2019 (6886 matches)
6. fifa_data.csv - FIFA player database (18207 players)
"""

import os
import re
import pandas as pd
from typing import Optional, Dict, Any, List


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

# Common Brazilian club name mapping for normalization
# Maps various naming conventions to a canonical name
TEAM_NAME_CANONICALS = {
    # Corinthians variants
    "Corinthians-SP": "Corinthians",
    "Sport Club Corinthians Paulista": "Corinthians",
    "SC Corinthians Paulista": "Corinthians",
    "SCCP": "Corinthians",
    # Flamengo variants
    "Flamengo-RJ": "Flamengo",
    "Clube de Regatas do Flamengo": "Flamengo",
    # Fluminense variants
    "Fluminense-RJ": "Fluminense",
    "Fluminense Football Club": "Fluminense",
    # Palmeiras variants
    "Palmeiras-SP": "Palmeiras",
    "SE Palmeiras": "Palmeiras",
    "Sociedade Esportiva Palmeiras": "Palmeiras",
    # Sao Paulo variants
    "Sao Paulo-SP": "Sao Paulo",
    "Sao Paulo FC": "Sao Paulo",
    "Sao Paulo Futebol Clube": "Sao Paulo",
    # Gremio variants
    "Gremio-RS": "Gremio",
    "Gremio Foot-Ball Porto Alegrense": "Gremio",
    "Grêmio-RS": "Grêmio",
    "Grêmio Foot-Ball Porto Alegrense": "Grêmio",
    # Internacional variants
    "Internacional-RS": "Internacional",
    "SC Internacional": "Internacional",
    "Sport Club Internacional": "Internacional",
    # Santos variants
    "Santos-SP": "Santos",
    "Santos FC": "Santos",
    "Santos Futebol Clube": "Santos",
    # Cruzeiro variants
    "Cruzeiro-MG": "Cruzeiro",
    "Cruzeiro Esporte Clube": "Cruzeiro",
    # Atletico-MG variants
    "Atletico-MG": "Atletico-MG",
    "Atletico Mineiro": "Atletico-MG",
    "Clube Atletico Mineiro": "Atletico-MG",
    "Atlético-MG": "Atlético-MG",
    "Clube Atlético Mineiro": "Atlético-MG",
    # Vasco variants
    "Vasco da Gama-RJ": "Vasco",
    "Club de Regatas Vasco da Gama": "Vasco",
    # Botafogo variants
    "Botafogo-RJ": "Botafogo",
    "Botafogo de Futebol e Regatas": "Botafogo",
    # Bahia variants
    "Bahia-BA": "Bahia",
    "Esporte Clube Bahia": "Bahia",
    # Fortalezo variants
    "Fortaleza-CE": "Fortaleza",
    "Fortaleza Esporte Clube": "Fortaleza",
    # Ceara variants
    "Ceará-CE": "Ceará",
    "Ceará SC": "Ceará",
    "Ceará Sport Club": "Ceará",
    # Sport variants
    "Sport-PE": "Sport",
    "Sport Recife": "Sport",
    "Sport Club do Recife": "Sport",
    # Vitoria variants
    "Vitoria-BA": "Vitoria",
    "Esporte Clube Vitoria": "Vitoria",
    # Avai variants
    "Avaí-SC": "Avaí",
    "Avaí FC": "Avaí",
    # Figueirense variants
    "Figueirense-SC": "Figueirense",
    "Figueirense Futebol Clube": "Figueirense",
    # Coritiba variants
    "Coritiba-PR": "Coritiba",
    "Coritiba Foot Ball Club": "Coritiba",
    # Athletic Club MG variants
    "Athletic Club MG": "Athletic Club",
    "Athletic Club": "Athletic Club",
    # Athletico Paranaense variants
    "Athletico-PR": "Athletico-PR",
    "Athletico Paranaense": "Athletico-PR",
    "Athletico Paranaense - PR": "Athletico-PR",
    "Club Athletico Paranaense": "Athletico-PR",
    "Club Athletico Paranaense - PR": "Athletico-PR",
    # Goias variants
    "Goias-GO": "Goias",
    "Goiás EC": "Goiás",
    "Goiás Esporte Clube": "Goiás",
    "Goiás Esporte Clube - GO": "Goiás",
    "Goiás-Go": "Goiás",
    "Goiás": "Goiás",
    # Sao Paulo state teams
    "Ponte Preta-SP": "Ponte Preta",
    "Autonoma Ponte Preta": "Ponte Preta",
    "Ponte Preta - SP": "Ponte Preta",
    "Clube Atletico Ponte Preta": "Ponte Preta",
    "Portuguesa-SP": "Portuguesa",
    "Associação Portuguesa de Desportos": "Portuguesa",
    # Nautico variants
    "Nautico-PE": "Nautico",
    "Náutico Capibaribe": "Nautico",
    "Clube Nautico Capibaribe": "Nautico",
    # Vitoria BA
    "EC Vitoria": "Vitoria",
    # Bragantino variants
    "Red Bull Bragantino": "Bragantino",
    "RB Bragantino": "Bragantino",
    "Bragantino - SP": "Bragantino",
    "Red Bull Clubs Bragantino": "Bragantino",
    # Cuiaba variants
    "Cuiaba": "Cuiabá",
    "Cuiabá EC": "Cuiabá",
    # Ceara
    "Ceara-CE": "Ceará",
    "Ceará Sport Club": "Ceará",
    "Ceará SC - CE": "Ceará",
    # Atletico GO
    "Atletico-GO": "Atletico-GO",
    "Atletico Goianiense": "Atletico-GO",
    "Club Atletico Goianiense": "Atletico-GO",
    # Remo
    "Remo - PA": "Remo",
    "Clube do Remo": "Remo",
    # Internacional
    "SC Internacional - RS": "Internacional",
    "Internacional - RS": "Internacional",
    "Gremio - RS": "Gremio",
    "Sao Paulo - SP": "Sao Paulo",
    "Santos - SP": "Santos",
    "Fluminense - RJ": "Fluminense",
    "Flamengo - RJ": "Flamengo",
    "Botafogo - RJ": "Botafogo",
    "Vasco da Gama - RJ": "Vasco",
    "Corinthians - SP": "Corinthians",
    "Palmeiras - SP": "Palmeiras",
    "Sport Club Corinthians Paulista - SP": "Corinthians",
    # Ler variants
    "America Mineiro": "Atletico-MG",
    "América Mineiro": "Atletico-MG",
    # Botafogo-SP
    "Botafogo-SP": "Botafogo-SP",
    "Botafogo FC (SP)": "Botafogo-SP",
}


def normalize_team_name(name: str) -> str:
    """
    Normalize a team name to a canonical form.
    Handles state suffixes (-SP, -RJ, -MG, etc.) and full club names.
    """
    if not name or pd.isna(name):
        return ""
    name = name.strip()
    # Check exact match in canonicals first
    if name in TEAM_NAME_CANONICALS:
        return TEAM_NAME_CANONICALS[name]
    # Check if any key is contained in the name
    for key, value in TEAM_NAME_CANONICALS.items():
        if key in name:
            return value
    # Remove state suffix for basic normalization
    name = re.sub(r'\s*[-–]\s*[A-Z]{2}\s*$', '', name).strip()
    return name


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse various date formats into ISO format (YYYY-MM-DD).
    Supports: ISO, Brazilian (DD/MM/YYYY), and mixed formats.
    """
    if not date_str or pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    # Already ISO format: 2023-09-24 or 2023-09-24 18:30:00
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return date_str[:10]
    
    # Brazilian format: 29/03/2003
    match = re.match(r'(\d{2})/(\d{2})/(\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    
    return date_str[:10] if len(date_str) >= 10 else None


def load_brasileirao() -> pd.DataFrame:
    """Load Brasileirão Serie A matches."""
    df = pd.read_csv(os.path.join(DATA_DIR, "Brasileirao_Matches.csv"))
    df['competition'] = 'Brasileirão Serie A'
    df['source'] = 'Brasileirao_Matches'
    return df


def load_brazilian_cup() -> pd.DataFrame:
    """Load Copa do Brasil matches."""
    df = pd.read_csv(os.path.join(DATA_DIR, "Brazilian_Cup_Matches.csv"))
    df['competition'] = 'Copa do Brasil'
    df['source'] = 'Brazilian_Cup_Matches'
    return df


def load_libertadores() -> pd.DataFrame:
    """Load Copa Libertadores matches."""
    df = pd.read_csv(os.path.join(DATA_DIR, "Libertadores_Matches.csv"))
    df['competition'] = 'Copa Libertadores'
    df['source'] = 'Libertadores_Matches'
    return df


def load_br_football() -> pd.DataFrame:
    """Load extended match statistics."""
    df = pd.read_csv(os.path.join(DATA_DIR, "BR-Football-Dataset.csv"))
    df['source'] = 'BR_Football_Dataset'
    return df


def load_novo_campeonato() -> pd.DataFrame:
    """Load historical Brasileirão matches (2003-2019)."""
    df = pd.read_csv(os.path.join(DATA_DIR, "novo_campeonato_brasileiro.csv"))
    df['source'] = 'novo_campeonato_brasileiro'
    return df


def load_fifa_players() -> pd.DataFrame:
    """Load FIFA player database."""
    df = pd.read_csv(os.path.join(DATA_DIR, "fifa_data.csv"))
    return df


def normalize_match_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Normalize a match DataFrame to a common schema:
    - datetime, date, home_team, away_team, home_goal, away_goal, season, round, competition
    """
    result = pd.DataFrame()
    result['competition'] = df.get('competition', pd.Series([source] * len(df)))
    result['source'] = source
    
    # Home team
    if 'home' in df.columns:
        result['home_team'] = df['home'].apply(normalize_team_name)
    elif 'Equipe_mandante' in df.columns:
        result['home_team'] = df['Equipe_mandante'].apply(normalize_team_name)
    else:
        result['home_team'] = df.get('home_team', pd.Series([''] * len(df))).apply(normalize_team_name)
    
    # Away team
    if 'away' in df.columns:
        result['away_team'] = df['away'].apply(normalize_team_name)
    elif 'Equipe_visitante' in df.columns:
        result['away_team'] = df['Equipe_visitante'].apply(normalize_team_name)
    else:
        result['away_team'] = df.get('away_team', pd.Series([''] * len(df))).apply(normalize_team_name)
    
    # Goals
    if 'home_goal' in df.columns:
        result['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce')
    elif 'Gols_mandante' in df.columns:
        result['home_goal'] = pd.to_numeric(df['Gols_mandante'], errors='coerce')
    else:
        result['home_goal'] = pd.Series([0] * len(df))
    
    if 'away_goal' in df.columns:
        result['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce')
    elif 'Gols_visitante' in df.columns:
        result['away_goal'] = pd.to_numeric(df['Gols_visitante'], errors='coerce')
    else:
        result['away_goal'] = pd.Series([0] * len(df))
    
    # Date/time
    if 'datetime' in df.columns:
        result['date'] = df['datetime'].apply(parse_date)
    elif 'Data' in df.columns:
        result['date'] = df['Data'].apply(parse_date)
    elif 'date' in df.columns:
        result['date'] = df['date'].apply(parse_date)
    else:
        result['date'] = pd.Series([None] * len(df))
    
    # Season
    if 'season' in df.columns:
        result['season'] = df['season'].astype(str)
    elif 'Ano' in df.columns:
        result['season'] = df['Ano'].astype(str)
    elif result['date'].notna().any():
        result['season'] = result['date'].str[:4]
    else:
        result['season'] = pd.Series([None] * len(df))
    
    # Round
    if 'round' in df.columns:
        result['round'] = df['round'].astype(str)
    elif 'Rodada' in df.columns:
        result['round'] = df['Rodada'].astype(str)
    else:
        result['round'] = pd.Series([None] * len(df))
    
    # Stage (for Libertadores)
    if 'stage' in df.columns:
        result['stage'] = df['stage']
    else:
        result['stage'] = None
    
    return result


def load_all_data() -> Dict[str, pd.DataFrame]:
    """
    Load all datasets and return as a dictionary keyed by source.
    Also returns a unified matches DataFrame with all match data normalized.
    """
    # Load raw match datasets
    df_br = load_brasileirao()
    df_cup = load_brazilian_cup()
    df_lib = load_libertadores()
    df_br_ext = load_br_football()
    df_novo = load_novo_campeonato()
    
    # Load FIFA data (separate table)
    df_fifa = load_fifa_players()
    
    # Normalize all match data to common schema
    df_br_norm = normalize_match_df(df_br, 'Brasileirao_Matches')
    df_cup_norm = normalize_match_df(df_cup, 'Brazilian_Cup_Matches')
    df_lib_norm = normalize_match_df(df_lib, 'Libertadores_Matches')
    df_br_ext_norm = normalize_match_df(df_br_ext, 'BR_Football_Dataset')
    df_novo_norm = normalize_match_df(df_novo, 'novo_campeonato_brasileiro')
    
    # Concatenate all match data
    all_matches = pd.concat([
        df_br_norm, df_cup_norm, df_lib_norm, df_br_ext_norm, df_novo_norm
    ], ignore_index=True)
    
    return {
        'matches': all_matches,
        'brasileirao': df_br_norm,
        'brazilian_cup': df_cup_norm,
        'libertadores': df_lib_norm,
        'br_football': df_br_ext_norm,
        'novo_campeonato': df_novo_norm,
        'players': df_fifa,
    }
