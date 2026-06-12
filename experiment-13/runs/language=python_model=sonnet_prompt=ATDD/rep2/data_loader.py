"""Data loading and normalization for Brazilian soccer datasets."""
import re
from pathlib import Path
import pandas as pd

STATE_CODES = {
    'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT',
    'PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO'
}

# Maps competition name variants to a canonical name
COMPETITION_ALIASES = {
    'brasileirao': 'Brasileirao',
    'brasileirão': 'Brasileirao',
    'serie a': 'Brasileirao',
    'série a': 'Brasileirao',
    'copa do brasil': 'Copa do Brasil',
    'copa brasil': 'Copa do Brasil',
    'libertadores': 'Copa Libertadores',
    'copa libertadores': 'Copa Libertadores',
    'libertadoras': 'Copa Libertadores',
}


def normalize_team_name(name: str) -> str:
    """Remove state suffix and clean team name for consistent matching."""
    if not isinstance(name, str):
        return str(name)
    name = name.strip()
    # Match " - STATE" or "-STATE" at end of string
    m = re.match(r'^(.+?)\s*-\s*([A-Z]{2})\s*$', name)
    if m and m.group(2) in STATE_CODES:
        return m.group(1).strip()
    return name


def canonical_competition(query: str) -> str | None:
    """Return canonical competition name for a user query, or None if unknown."""
    if not query:
        return None
    return COMPETITION_ALIASES.get(query.lower().strip(), query)


def _team_matches(norm_col: pd.Series, query: str) -> pd.Series:
    """Return boolean mask where normalized team name contains the query."""
    q = normalize_team_name(query).lower()
    return norm_col.str.lower().str.contains(q, na=False, regex=False)


class DataStore:
    """Loads and indexes all Brazilian soccer CSV datasets."""

    def __init__(self, data_dir: str = "data/kaggle"):
        self.data_dir = Path(data_dir)
        self._load_all()

    def _load_all(self):
        self.brasileirao = self._load_brasileirao()
        self.copa_do_brasil = self._load_copa_do_brasil()
        self.libertadores = self._load_libertadores()
        self.br_football = self._load_br_football()
        self.historico = self._load_historico()
        self.players = self._load_players()
        self.all_matches = self._build_unified_matches()

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / 'Brasileirao_Matches.csv')
        df['competition'] = 'Brasileirao'
        df['source'] = 'brasileirao'
        df['date'] = pd.to_datetime(df['datetime'], errors='coerce').dt.date
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        df['season'] = df['season'].astype(int)
        df['norm_home'] = df['home_team'].apply(normalize_team_name)
        df['norm_away'] = df['away_team'].apply(normalize_team_name)
        df['round_info'] = df['round'].astype(str)
        return df

    def _load_copa_do_brasil(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / 'Brazilian_Cup_Matches.csv')
        df['competition'] = 'Copa do Brasil'
        df['source'] = 'copa_do_brasil'
        df['date'] = pd.to_datetime(df['datetime'], errors='coerce').dt.date
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        df['season'] = pd.to_numeric(df['season'], errors='coerce').fillna(0).astype(int)
        df['norm_home'] = df['home_team'].apply(normalize_team_name)
        df['norm_away'] = df['away_team'].apply(normalize_team_name)
        df['round_info'] = df['round'].astype(str)
        return df

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / 'Libertadores_Matches.csv')
        df['competition'] = 'Copa Libertadores'
        df['source'] = 'libertadores'
        df['date'] = pd.to_datetime(df['datetime'], errors='coerce').dt.date
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        df['season'] = pd.to_numeric(df['season'], errors='coerce').fillna(0).astype(int)
        df['norm_home'] = df['home_team'].apply(normalize_team_name)
        df['norm_away'] = df['away_team'].apply(normalize_team_name)
        df['round_info'] = df.get('stage', pd.Series([''] * len(df))).fillna('').astype(str)
        return df

    def _load_br_football(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / 'BR-Football-Dataset.csv')
        df['source'] = 'br_football'
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        df['home_goal'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)
        # Derive season from date
        df['season'] = pd.to_datetime(df['date'], errors='coerce').dt.year.fillna(0).astype(int)
        df['competition'] = df['tournament'].fillna('Unknown')
        df['norm_home'] = df['home'].apply(normalize_team_name)
        df['norm_away'] = df['away'].apply(normalize_team_name)
        df['home_team'] = df['home']
        df['away_team'] = df['away']
        return df

    def _load_historico(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / 'novo_campeonato_brasileiro.csv', encoding='utf-8-sig')
        df['source'] = 'historico'
        df['competition'] = 'Brasileirao'
        df['date'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').dt.date
        df['home_team'] = df['Equipe_mandante']
        df['away_team'] = df['Equipe_visitante']
        df['home_goal'] = pd.to_numeric(df['Gols_mandante'], errors='coerce').fillna(0).astype(int)
        df['away_goal'] = pd.to_numeric(df['Gols_visitante'], errors='coerce').fillna(0).astype(int)
        df['season'] = df['Ano'].astype(int)
        df['norm_home'] = df['home_team'].apply(normalize_team_name)
        df['norm_away'] = df['away_team'].apply(normalize_team_name)
        df['round_info'] = df['Rodada'].astype(str)
        return df

    def _load_players(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / 'fifa_data.csv', encoding='utf-8-sig')
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])
        df['Overall'] = pd.to_numeric(df['Overall'], errors='coerce')
        return df

    def _build_unified_matches(self) -> pd.DataFrame:
        """Combine all match sources into a single DataFrame with standardized columns.

        The brasileirao file covers 2012-2022; historico covers 2003-2019.
        To avoid double-counting, only use historico for seasons before 2012
        (seasons not covered by the brasileirao file).
        """
        cols = ['date', 'home_team', 'away_team', 'norm_home', 'norm_away',
                'home_goal', 'away_goal', 'competition', 'season', 'source']

        brasileirao_min_season = int(self.brasileirao['season'].min())
        historico_only = self.historico[self.historico['season'] < brasileirao_min_season].copy()

        frames = []
        for df in [self.brasileirao, self.copa_do_brasil, self.libertadores, historico_only]:
            sub = df.copy()
            for col in cols:
                if col not in sub.columns:
                    sub[col] = ''
            frames.append(sub[cols])

        unified = pd.concat(frames, ignore_index=True)
        return unified

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> pd.DataFrame:
        df = self.all_matches.copy()

        if competition:
            canon = canonical_competition(competition)
            df = df[df['competition'].str.lower().str.contains(canon.lower(), na=False, regex=False)]

        if season:
            df = df[df['season'] == int(season)]

        if date_from:
            try:
                from datetime import date as dt
                d = pd.to_datetime(date_from).date()
                df = df[df['date'] >= d]
            except Exception:
                pass

        if date_to:
            try:
                d = pd.to_datetime(date_to).date()
                df = df[df['date'] <= d]
            except Exception:
                pass

        if team and opponent:
            team_q = normalize_team_name(team).lower()
            opp_q = normalize_team_name(opponent).lower()
            mask = (
                (df['norm_home'].str.lower().str.contains(team_q, na=False, regex=False) &
                 df['norm_away'].str.lower().str.contains(opp_q, na=False, regex=False)) |
                (df['norm_home'].str.lower().str.contains(opp_q, na=False, regex=False) &
                 df['norm_away'].str.lower().str.contains(team_q, na=False, regex=False))
            )
            df = df[mask]
        elif team:
            q = normalize_team_name(team).lower()
            mask = (
                df['norm_home'].str.lower().str.contains(q, na=False, regex=False) |
                df['norm_away'].str.lower().str.contains(q, na=False, regex=False)
            )
            df = df[mask]

        return df.sort_values('date', ascending=False, na_position='last')

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_rating: int | None = None,
    ) -> pd.DataFrame:
        df = self.players.copy()

        if name:
            df = df[df['Name'].str.contains(name, case=False, na=False)]

        if nationality:
            df = df[df['Nationality'].str.contains(nationality, case=False, na=False)]

        if club:
            df = df[df['Club'].str.contains(club, case=False, na=False)]

        if position:
            df = df[df['Position'].str.contains(position, case=False, na=False)]

        if min_rating is not None:
            df = df[df['Overall'] >= min_rating]

        return df.sort_values('Overall', ascending=False)

    def compute_standings(self, competition: str, season: int) -> pd.DataFrame:
        """Compute league standings (points table) from match results.

        Uses original team names (with state suffix) as keys so that
        'Atletico-MG' and 'Atletico-PR' are counted as separate teams.
        Display name has state suffix removed for readability.
        """
        df = self.search_matches(competition=competition, season=season)

        records: dict[str, dict] = {}

        def record(team_key: str, display: str):
            if team_key not in records:
                records[team_key] = {
                    'team': display, 'P': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0
                }
            return records[team_key]

        for _, row in df.iterrows():
            # Use original names as keys (preserve state for disambiguation),
            # but show normalized names for display
            h_key = str(row['home_team'])
            a_key = str(row['away_team'])
            h_disp = str(row['norm_home'])
            a_disp = str(row['norm_away'])
            hg, ag = int(row['home_goal']), int(row['away_goal'])
            rh = record(h_key, h_disp)
            ra = record(a_key, a_disp)
            rh['P'] += 1; ra['P'] += 1
            rh['GF'] += hg; rh['GA'] += ag
            ra['GF'] += ag; ra['GA'] += hg
            if hg > ag:
                rh['W'] += 1; ra['L'] += 1
            elif ag > hg:
                ra['W'] += 1; rh['L'] += 1
            else:
                rh['D'] += 1; ra['D'] += 1

        if not records:
            return pd.DataFrame()

        standings = pd.DataFrame(list(records.values()))
        standings['Pts'] = standings['W'] * 3 + standings['D']
        standings['GD'] = standings['GF'] - standings['GA']
        standings = standings.sort_values(['Pts', 'W', 'GD', 'GF'], ascending=False).reset_index(drop=True)
        standings.index += 1
        return standings

    def compute_team_stats(
        self, team: str, competition: str | None = None, season: int | None = None
    ) -> dict:
        """Compute win/draw/loss record and goal tallies for a team."""
        df = self.search_matches(team=team, competition=competition, season=season)
        q = normalize_team_name(team).lower()

        total = home = away = 0
        stats = {'home_W':0,'home_D':0,'home_L':0,'home_GF':0,'home_GA':0,
                 'away_W':0,'away_D':0,'away_L':0,'away_GF':0,'away_GA':0}

        for _, row in df.iterrows():
            hg, ag = int(row['home_goal']), int(row['away_goal'])
            is_home = q in str(row['norm_home']).lower()
            total += 1
            if is_home:
                home += 1
                stats['home_GF'] += hg; stats['home_GA'] += ag
                if hg > ag: stats['home_W'] += 1
                elif hg == ag: stats['home_D'] += 1
                else: stats['home_L'] += 1
            else:
                away += 1
                stats['away_GF'] += ag; stats['away_GA'] += hg
                if ag > hg: stats['away_W'] += 1
                elif ag == hg: stats['away_D'] += 1
                else: stats['away_L'] += 1

        stats.update({
            'total': total, 'home': home, 'away': away,
            'W': stats['home_W'] + stats['away_W'],
            'D': stats['home_D'] + stats['away_D'],
            'L': stats['home_L'] + stats['away_L'],
            'GF': stats['home_GF'] + stats['away_GF'],
            'GA': stats['home_GA'] + stats['away_GA'],
        })
        return stats

    def compute_head_to_head(
        self, team1: str, team2: str, competition: str | None = None
    ) -> dict:
        """Compute H2H record between two teams."""
        df = self.search_matches(team=team1, opponent=team2, competition=competition)
        t1_q = normalize_team_name(team1).lower()

        t1_w = t2_w = draws = 0
        for _, row in df.iterrows():
            hg, ag = int(row['home_goal']), int(row['away_goal'])
            t1_home = t1_q in str(row['norm_home']).lower()
            if hg == ag:
                draws += 1
            elif t1_home and hg > ag:
                t1_w += 1
            elif not t1_home and ag > hg:
                t1_w += 1
            else:
                t2_w += 1

        return {'total': len(df), 'team1_wins': t1_w, 'team2_wins': t2_w, 'draws': draws, 'matches': df}
