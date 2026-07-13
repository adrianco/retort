# Brazilian Soccer MCP Server - Data Loader
# Loads and normalizes all 6 Kaggle CSV datasets into queryable data structures.
# Handles team name variations, date format normalization, and character encoding.

import os
import re
import unicodedata
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")


def normalize_team_name(name: str) -> str:
    """Normalize team names across datasets by stripping state suffixes and accents.

    Examples:
        'Palmeiras-SP' -> 'palmeiras'
        'Flamengo-RJ' -> 'flamengo'
        'Sao Paulo' -> 'sao-paulo'
        'Gre' -> 'gremio'
    """
    if not name or pd.isna(name):
        return ""
    name = str(name).strip()
    # Remove state suffix like -SP, -RJ, -MG, -PR, etc.
    # Remove parenthetical annotations FIRST (before state suffix removal)
    # e.g. 'Boavista Sport Club (antigo Esporte Clube Barreira) - RJ'
    name = re.sub(r'\(.*?\)', '', name)
    # Strip trailing spaces
    name = name.strip()
    # Then remove state suffix like -SP, -RJ, -MG, -PR, etc.
    name = re.sub(r'\s*-\s*([A-Z]{2})$', '', name)
    # Handle country codes like (URU), (EQU) for Libertadores international teams
    name = re.sub(r'\([A-Z]{3}\)', '', name)
    name = name.strip()
    # Remove accents and diacritics
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    # Replace spaces with hyphens for consistent matching
    name = name.lower().replace(' ', '-')
    name = re.sub(r'[^a-z0-9\-]', '', name)
    name = re.sub(r'-+', '-', name)
    return name.strip('-')


def parse_iso_date(date_str: str) -> Optional[datetime]:
    """Parse ISO format dates like '2023-09-24 18:30:00' or '2023-09-24'."""
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def parse_brazilian_date(date_str: str) -> Optional[datetime]:
    """Parse Brazilian date format 'DD/MM/YYYY' or 'DD/MM/YYYY HH:MM:SS'."""
    date_str = str(date_str).strip()
    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


class MatchDataset:
    """Holds all match data from all CSV files with normalization."""

    def __init__(self):
        self.brasileirao: pd.DataFrame = pd.DataFrame()
        self.copa_brasil: pd.DataFrame = pd.DataFrame()
        self.libertadores: pd.DataFrame = pd.DataFrame()
        self.extended_stats: pd.DataFrame = pd.DataFrame()
        self.historic: pd.DataFrame = pd.DataFrame()
        self.fifa_players: pd.DataFrame = pd.DataFrame()

        # All matches combined into a normalized format
        self.all_matches: List[Dict] = []
        # Unique normalized team names across all data
        self.all_teams: set = set()
        # Player data
        self.all_players: List[Dict] = []

    def load_all(self, data_dir: str = DATA_DIR):
        """Load all CSV datasets."""
        self._load_brasileirao(data_dir)
        self._load_copa_brasil(data_dir)
        self._load_libertadores(data_dir)
        self._load_extended_stats(data_dir)
        self._load_historic(data_dir)
        self._load_fifa_players(data_dir)
        self._build_all_matches()
        self._build_all_teams()
        self._build_all_players()

    def _load_brasileirao(self, data_dir: str):
        """Load Brasileirao Serie A Matches (4,180 matches)."""
        path = os.path.join(data_dir, 'Brasileirao_Matches.csv')
        if not os.path.exists(path):
            return
        df = pd.read_csv(path, encoding='utf-8')
        df['home_team'] = df['home_team'].fillna('')
        df['away_team'] = df['away_team'].fillna('')
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        df['season'] = pd.to_numeric(df['season'], errors='coerce').fillna(0).astype(int)
        df['round'] = pd.to_numeric(df['round'], errors='coerce').fillna(0).astype(int)
        df['competition'] = 'Brasileirao'
        df['datetime_parsed'] = df['datetime'].apply(parse_iso_date)
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
        self.brasileirao = df

    def _load_copa_brasil(self, data_dir: str):
        """Load Copa do Brasil Matches (1,337 matches)."""
        path = os.path.join(data_dir, 'Brazilian_Cup_Matches.csv')
        if not os.path.exists(path):
            return
        df = pd.read_csv(path, encoding='utf-8')
        df['home_team'] = df['home_team'].fillna('')
        df['away_team'] = df['away_team'].fillna('')
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        df['season'] = pd.to_numeric(df['season'], errors='coerce').fillna(0).astype(int)
        df['competition'] = 'Copa do Brasil'
        df['datetime_parsed'] = df['datetime'].apply(parse_iso_date)
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
        df['round'] = df['round'].astype(str)
        self.copa_brasil = df

    def _load_libertadores(self, data_dir: str):
        """Load Copa Libertadores Matches (1,255 matches)."""
        path = os.path.join(data_dir, 'Libertadores_Matches.csv')
        if not os.path.exists(path):
            return
        df = pd.read_csv(path, encoding='utf-8')
        df['home_team'] = df['home_team'].fillna('')
        df['away_team'] = df['away_team'].fillna('')
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        df['season'] = pd.to_numeric(df['season'], errors='coerce').fillna(0).astype(int)
        df['competition'] = 'Libertadores'
        df['datetime_parsed'] = df['datetime'].apply(parse_iso_date)
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
        self.libertadores = df

    def _load_extended_stats(self, data_dir: str):
        """Load Extended Match Statistics (10,296 matches)."""
        path = os.path.join(data_dir, 'BR-Football-Dataset.csv')
        if not os.path.exists(path):
            return
        df = pd.read_csv(path, encoding='utf-8')
        df['home'] = df['home'].fillna('')
        df['away'] = df['away'].fillna('')
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        df['home_corner'] = pd.to_numeric(df['home_corner'], errors='coerce').fillna(0)
        df['away_corner'] = pd.to_numeric(df['away_corner'], errors='coerce').fillna(0)
        df['home_attack'] = pd.to_numeric(df['home_attack'], errors='coerce').fillna(0)
        df['away_attack'] = pd.to_numeric(df['away_attack'], errors='coerce').fillna(0)
        df['home_shots'] = pd.to_numeric(df['home_shots'], errors='coerce').fillna(0)
        df['away_shots'] = pd.to_numeric(df['away_shots'], errors='coerce').fillna(0)
        df['total_corners'] = pd.to_numeric(df['total_corners'], errors='coerce').fillna(0)
        df['competition'] = df['tournament'].fillna('Unknown')
        df['datetime_parsed'] = df['date'].apply(parse_iso_date)
        df['home_team_norm'] = df['home'].apply(normalize_team_name)
        df['away_team_norm'] = df['away'].apply(normalize_team_name)
        self.extended_stats = df

    def _load_historic(self, data_dir: str):
        """Load Historical Brasileirao 2003-2019 (6,886 matches)."""
        path = os.path.join(data_dir, 'novo_campeonato_brasileiro.csv')
        if not os.path.exists(path):
            return
        df = pd.read_csv(path, encoding='utf-8')
        df['Equipe_mandante'] = df['Equipe_mandante'].fillna('')
        df['Equipe_visitante'] = df['Equipe_visitante'].fillna('')
        df['Gols_mandante'] = pd.to_numeric(df['Gols_mandante'], errors='coerce').fillna(0).astype(int)
        df['Gols_visitante'] = pd.to_numeric(df['Gols_visitante'], errors='coerce').fillna(0).astype(int)
        df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce').fillna(0).astype(int)
        df['Rodada'] = pd.to_numeric(df['Rodada'], errors='coerce').fillna(0).astype(int)
        # Normalize column names to match other datasets
        df['home_goal'] = df['Gols_mandante']
        df['away_goal'] = df['Gols_visitante']
        df['competition'] = 'Brasileirao (Historic)'
        df['datetime_parsed'] = df['Data'].apply(parse_brazilian_date)
        df['home_team_norm'] = df['Equipe_mandante'].apply(normalize_team_name)
        df['away_team_norm'] = df['Equipe_visitante'].apply(normalize_team_name)
        self.historic = df

    def _load_fifa_players(self, data_dir: str):
        """Load FIFA Player Database (18,207 players)."""
        path = os.path.join(data_dir, 'fifa_data.csv')
        if not os.path.exists(path):
            return
        df = pd.read_csv(path, encoding='utf-8', encoding_errors='replace', low_memory=False)
        # First column is unnamed index, drop it
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        # Parse columns
        df['Name'] = df['Name'].fillna('').astype(str)
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(0).astype(int)
        df['Nationality'] = df['Nationality'].fillna('').astype(str)
        df['Overall'] = pd.to_numeric(df['Overall'], errors='coerce').fillna(0).astype(int)
        df['Potential'] = pd.to_numeric(df['Potential'], errors='coerce').fillna(0).astype(int)
        df['Club'] = df['Club'].fillna('').astype(str)
        df['Position'] = df['Position'].fillna('').astype(str)
        df['Jersey Number'] = pd.to_numeric(df['Jersey Number'], errors='coerce').fillna(0).astype(int)
        df['height'] = df['Height'].fillna('').astype(str)
        df['weight'] = df['Weight'].fillna('').astype(str)

        def extract_rating(val):
            if pd.isna(val) or val == '':
                return 0
            val = str(val)
            match = re.match(r'(\d+)(\+\d+)?', val)
            if match:
                return int(match.group(1))
            return 0

        skill_cols = ['Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys',
                       'Dribbling', 'Curve', 'FKAccuracy', 'LongPassing', 'BallControl',
                       'Acceleration', 'SprintSpeed', 'Agility', 'Reactions', 'Balance',
                       'ShotPower', 'Jumping', 'Stamina', 'Strength', 'LongShots',
                       'Aggression', 'Interceptions', 'Positioning', 'Vision', 'Penalties',
                       'Composure', 'Marking', 'StandingTackle', 'SlidingTackle',
                       'GKDiving', 'GKHandling', 'GKPositioning', 'GKReflexes']

        for col in skill_cols:
            if col in df.columns:
                df[col] = df[col].apply(extract_rating)

        self.fifa_players = df

    def _build_all_matches(self):
        """Build a unified list of all matches with normalized team names."""
        self.all_matches = []
        for df, h_col, a_col in [
            (self.brasileirao, 'home_team_norm', 'away_team_norm'),
            (self.copa_brasil, 'home_team_norm', 'away_team_norm'),
            (self.libertadores, 'home_team_norm', 'away_team_norm'),
            (self.extended_stats, 'home_team_norm', 'away_team_norm'),
            (self.historic, 'home_team_norm', 'away_team_norm'),
        ]:
            if df.empty:
                continue
            for _, row in df.iterrows():
                match = {
                    'date': row['datetime_parsed'].isoformat() if pd.notna(row['datetime_parsed']) else None,
                    'home_team': str(row[h_col]),
                    'away_team': str(row[a_col]),
                    'home_goals': int(row['home_goal']),
                    'away_goals': int(row['away_goal']),
                    'competition': str(row.get('competition', '')),
                    'season': int(row.get('season', 0)) if pd.notna(row.get('season', float('nan'))) else None,
                    'round': str(row.get('round', '')) if pd.notna(row.get('round', float('nan'))) else None,
                    'stage': str(row.get('stage', '')) if 'stage' in row.index and pd.notna(row.get('stage', float('nan'))) else None,
                }
                if 'home_corners' in row.index:
                    match['home_corners'] = int(row['home_corners']) if pd.notna(row['home_corners']) else 0
                    match['away_corners'] = int(row['away_corners']) if pd.notna(row['away_corners']) else 0
                    match['home_shots'] = int(row['home_shots']) if pd.notna(row['home_shots']) else 0
                    match['away_shots'] = int(row['away_shots']) if pd.notna(row['away_shots']) else 0
                self.all_matches.append(match)

    def _build_all_teams(self):
        """Extract all unique team names."""
        self.all_teams = set()
        for match in self.all_matches:
            self.all_teams.add(match['home_team'])
            self.all_teams.add(match['away_team'])

    def _build_all_players(self):
        """Build a unified list of all FIFA players."""
        self.all_players = []
        if self.fifa_players.empty:
            return
        for _, row in self.fifa_players.iterrows():
            player = {
                'id': int(row.get('ID', 0)),
                'name': str(row['Name']).strip(),
                'age': int(row['Age']),
                'nationality': str(row['Nationality']).strip(),
                'overall': int(row['Overall']),
                'potential': int(row['Potential']),
                'club': str(row['Club']).strip(),
                'position': str(row['Position']).strip(),
                'jersey_number': int(row.get('Jersey Number', 0)),
                'height': str(row.get('height', '')),
                'weight': str(row.get('weight', '')),
                'preferred_foot': str(row.get('Preferred Foot', '')),
                'crossing': int(row.get('Crossing', 0)),
                'finishing': int(row.get('Finishing', 0)),
                'dribbling': int(row.get('Dribbling', 0)),
                'passing': int(row.get('ShortPassing', 0)),
                'pace': int(row.get('Acceleration', 0)),
            }
            self.all_players.append(player)

    def get_match_by_criteria(
        self,
        team: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> List[Dict]:
        """Query matches by various criteria."""
        results = list(self.all_matches)

        if team:
            team_norm = normalize_team_name(team)
            results = [m for m in results if m['home_team'] == team_norm or m['away_team'] == team_norm]

        if date_from:
            results = [m for m in results if m['date'] and m['date'] >= date_from]

        if date_to:
            results = [m for m in results if m['date'] and m['date'] <= date_to]

        if competition:
            comp_lower = competition.lower()
            results = [m for m in results if comp_lower in m['competition'].lower()]

        if season is not None:
            results = [m for m in results if m['season'] == season]

        return results

    def get_team_statistics(self, team: str, competition: Optional[str] = None) -> Dict:
        """Calculate team statistics from match data."""
        team_norm = normalize_team_name(team)
        matches = []

        for df in [self.brasileirao, self.copa_brasil, self.libertadores, self.extended_stats, self.historic]:
            if df.empty:
                continue
            h_col = 'home_team_norm' if 'home_team_norm' in df.columns else 'home_team'
            a_col = 'away_team_norm' if 'away_team_norm' in df.columns else 'away_team'
            for _, row in df.iterrows():
                h = str(row.get(h_col, ''))
                a = str(row.get(a_col, ''))
                if h == team_norm or a == team_norm:
                    comp = str(row.get('competition', ''))
                    if competition and competition.lower() not in comp.lower():
                        continue
                    if h == team_norm:
                        gf, ga = int(row['home_goal']), int(row['away_goal'])
                    else:
                        gf, ga = int(row['away_goal']), int(row['home_goal'])
                    matches.append({'goals_for': gf, 'goals_against': ga})

        if not matches:
            return {
                'team': team, 'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                'goals_for': 0, 'goals_against': 0, 'win_rate': 0.0,
            }

        wins = sum(1 for m in matches if m['goals_for'] > m['goals_against'])
        draws = sum(1 for m in matches if m['goals_for'] == m['goals_against'])
        losses = sum(1 for m in matches if m['goals_for'] < m['goals_against'])
        goals_for = sum(m['goals_for'] for m in matches)
        goals_against = sum(m['goals_against'] for m in matches)
        total = len(matches)

        return {
            'team': team, 'matches': total, 'wins': wins, 'draws': draws, 'losses': losses,
            'goals_for': goals_for, 'goals_against': goals_against,
            'win_rate': round(wins / total * 100, 1) if total > 0 else 0.0,
        }

    def get_head_to_head(self, team1: str, team2: str, competition: Optional[str] = None) -> Dict:
        """Calculate head-to-head statistics between two teams."""
        t1 = normalize_team_name(team1)
        t2 = normalize_team_name(team2)

        sources = [
            (self.brasileirao, 'home_team_norm', 'away_team_norm'),
            (self.copa_brasil, 'home_team_norm', 'away_team_norm'),
            (self.libertadores, 'home_team_norm', 'away_team_norm'),
            (self.extended_stats, 'home_team_norm', 'away_team_norm'),
            (self.historic, 'home_team_norm', 'away_team_norm'),
        ]

        matches = []
        for df, h_col, a_col in sources:
            if df.empty:
                continue
            for _, row in df.iterrows():
                h = str(row[h_col])
                a = str(row[a_col])
                if (h == t1 and a == t2) or (h == t2 and a == t1):
                    comp = str(row.get('competition', ''))
                    if competition and competition.lower() not in comp.lower():
                        continue
                    matches.append({
                        'date': str(row.get('datetime_parsed', '')),
                        'home': h, 'away': a,
                        'home_goals': int(row['home_goal']),
                        'away_goals': int(row['away_goal']),
                        'competition': comp,
                    })

        if not matches:
            return {
                'team1': team1, 'team2': team2, 'total_matches': 0,
                'team1_wins': 0, 'team2_wins': 0, 'draws': 0, 'matches': [],
            }

        t1_wins = t2_wins = draws = 0
        for m in matches:
            if m['home'] == t1:
                if m['home_goals'] > m['away_goals']: t1_wins += 1
                elif m['home_goals'] < m['away_goals']: t2_wins += 1
                else: draws += 1
            else:
                if m['away_goals'] > m['home_goals']: t1_wins += 1
                elif m['away_goals'] < m['home_goals']: t2_wins += 1
                else: draws += 1

        return {
            'team1': team1, 'team2': team2, 'total_matches': len(matches),
            'team1_wins': t1_wins, 'team2_wins': t2_wins, 'draws': draws, 'matches': matches,
        }

    def get_players_by_filter(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_results: int = 20,
    ) -> List[Dict]:
        """Search FIFA player data with filters."""
        results = list(self.all_players)

        if nationality:
            nat_lower = nationality.lower()
            results = [p for p in results if nat_lower in p['nationality'].lower()]

        if club:
            club_lower = club.lower()
            results = [p for p in results if club_lower in p['club'].lower()]

        if position:
            pos_lower = position.lower()
            results = [p for p in results if pos_lower in p['position'].lower()]

        if min_overall:
            results = [p for p in results if p['overall'] >= min_overall]

        results.sort(key=lambda p: p['overall'], reverse=True)
        return results[:max_results]

    def get_top_scorers_per_match(self) -> List[Dict]:
        """Find matches with the highest total goals."""
        scored = []
        for m in self.all_matches:
            total = m['home_goals'] + m['away_goals']
            scored.append({
                'date': m['date'], 'home_team': m['home_team'],
                'away_team': m['away_team'],
                'home_goals': m['home_goals'], 'away_goals': m['away_goals'],
                'total_goals': total, 'competition': m['competition'],
            })
        scored.sort(key=lambda x: x['total_goals'], reverse=True)
        return scored[:20]

    def get_average_goals_per_match(self) -> Dict:
        """Calculate average goals per match across all datasets."""
        total_goals = total_matches = home_wins = away_wins = draws = 0

        for m in self.all_matches:
            total_goals += m['home_goals'] + m['away_goals']
            total_matches += 1
            if m['home_goals'] > m['away_goals']: home_wins += 1
            elif m['home_goals'] < m['away_goals']: away_wins += 1
            else: draws += 1

        return {
            'total_matches': total_matches, 'total_goals': total_goals,
            'average_goals_per_match': round(total_goals / total_matches, 2) if total_matches else 0,
            'home_win_rate': round(home_wins / total_matches * 100, 1) if total_matches else 0,
            'away_win_rate': round(away_wins / total_matches * 100, 1) if total_matches else 0,
            'draw_rate': round(draws / total_matches * 100, 1) if total_matches else 0,
        }

    def get_standings_by_season(self, season: int, competition: str = 'Brasileirao') -> List[Dict]:
        """Calculate standings for a season based on match results."""
        team_stats: Dict[str, Dict] = {}

        for df in [self.brasileirao, self.historic]:
            if df.empty:
                continue
            for _, row in df.iterrows():
                comp = str(row.get('competition', ''))
                if competition.lower() not in comp.lower():
                    continue
                s = int(row.get('season', 0))
                if s != season:
                    continue

                h = str(row['home_team_norm'])
                a = str(row['away_team_norm'])
                hg = int(row['home_goal'])
                ag = int(row['away_goal'])

                for tk in [h, a]:
                    if tk not in team_stats:
                        team_stats[tk] = {
                            'team': tk, 'matches': 0, 'wins': 0, 'draws': 0,
                            'losses': 0, 'goals_for': 0, 'goals_against': 0, 'points': 0,
                        }

                if h == tk:
                    team_stats[h]['matches'] += 1
                    team_stats[h]['goals_for'] += hg
                    team_stats[h]['goals_against'] += ag
                    if hg > ag: team_stats[h]['wins'] += 1; team_stats[h]['points'] += 3
                    elif hg == ag: team_stats[h]['draws'] += 1; team_stats[h]['points'] += 1
                    else: team_stats[h]['losses'] += 1
                else:
                    team_stats[a]['matches'] += 1
                    team_stats[a]['goals_for'] += ag
                    team_stats[a]['goals_against'] += hg
                    if ag > hg: team_stats[a]['wins'] += 1; team_stats[a]['points'] += 3
                    elif ag == hg: team_stats[a]['draws'] += 1; team_stats[a]['points'] += 1
                    else: team_stats[a]['losses'] += 1

        return sorted(team_stats.values(), key=lambda x: x['points'], reverse=True)
