"""Offline Brazilian soccer knowledge graph and query service (stdlib only)."""
from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, date as Date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'data' / 'kaggle'
FILES = ('Brasileirao_Matches.csv', 'Brazilian_Cup_Matches.csv',
         'Libertadores_Matches.csv', 'novo_campeonato_brasileiro.csv',
         'BR-Football-Dataset.csv', 'fifa_data.csv')


def fold(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(value))
                           if not unicodedata.combining(c)).casefold().split())


ALIASES = {
    'america fc (minas gerais)': 'América-MG', 'ceara sporting club': 'Ceará',
    'ec bahia': 'Bahia', 'bahia': 'Bahia', 'fortaleza fc': 'Fortaleza', 'fortaleza': 'Fortaleza',
    'ec juventude': 'Juventude', 'juventude': 'Juventude', 'vasco da gama rj': 'Vasco',
    'bragantino': 'Red Bull Bragantino', 'red bull bragantino': 'Red Bull Bragantino',
    'santa cruz fc': 'Santa Cruz', 'santa cruz': 'Santa Cruz', 'csa': 'CSA', 'c.s.a.': 'CSA',
    'crb': 'CRB', 'c.r.b.': 'CRB', 'c. r. b.': 'CRB', 'abc': 'ABC', 'a.b.c.': 'ABC',
    'criciuma': 'Criciúma', 'cuiaba': 'Cuiabá',
    'flamengo pi': 'Flamengo-PI', 'flamengo do piaui': 'Flamengo-PI',
    'santos ap': 'Santos-AP', 'bragantino pa': 'Bragantino-PA',
    'internacional sc': 'Internacional-SC', 'juventude ma': 'Juventude-MA',
    'guarani ce': 'Guarani-CE', 'nautico rr': 'Náutico-RR',
    'santa cruz rn': 'Santa Cruz-RN', 'santa cruz rs': 'Santa Cruz-RS',
    'sport club corinthians paulista': 'Corinthians', 'corinthians': 'Corinthians',
    'clube de regatas do flamengo': 'Flamengo', 'flamengo': 'Flamengo',
    'sociedade esportiva palmeiras': 'Palmeiras', 'palmeiras': 'Palmeiras',
    'sao paulo fc': 'São Paulo', 'sao paulo futebol clube': 'São Paulo', 'sao paulo': 'São Paulo',
    'gremio': 'Grêmio', 'gremio foot-ball porto alegrense': 'Grêmio',
    'atletico pr': 'Athletico-PR', 'athletico pr': 'Athletico-PR', 'athletico': 'Athletico-PR',
    'atletico paranaense': 'Athletico-PR', 'athletico paranaense': 'Athletico-PR',
    'atletico mg': 'Atlético-MG', 'atletico mineiro': 'Atlético-MG',
    'atletico go': 'Atlético-GO', 'atletico goianiense': 'Atlético-GO',
    'america mg': 'América-MG', 'america mineiro': 'América-MG',
    'america rn': 'América-RN', 'botafogo rj': 'Botafogo', 'botafogo': 'Botafogo',
    'botafogo sp': 'Botafogo-SP', 'botafogo pb': 'Botafogo-PB',
    'vasco': 'Vasco', 'vasco da gama': 'Vasco', 'cr vasco da gama': 'Vasco',
    'sport': 'Sport', 'sport recife': 'Sport', 'sport club do recife': 'Sport',
    'santos fc': 'Santos', 'santos': 'Santos', 'fluminense fc': 'Fluminense',
    'fluminense': 'Fluminense', 'avai': 'Avaí', 'goias': 'Goiás',
    'vitoria': 'Vitória', 'ceara': 'Ceará', 'nautico': 'Náutico', 'parana': 'Paraná',
}
STATES = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split()


def normalize_team(name):
    name = ' '.join(str(name).strip().split())
    key = fold(name).replace('-', ' ')
    key = ' '.join(key.split())
    if key in ALIASES:
        return ALIASES[key]
    base = re.sub(r'\s*-\s*(' + '|'.join(STATES) + r')$', '', name, flags=re.I).strip()
    key = fold(base)
    # Preserve state qualifiers for clubs whose names are ambiguous.
    if key in {'america', 'atletico', 'athletico', 'botafogo', 'operario'} and base != name:
        return base + '-' + name[-2:].upper()
    return ALIASES.get(key, base)


def team_key(name):
    return fold(normalize_team(name))


def competition_name(name):
    key = fold(name)
    return {'serie a': 'Brasileirão', 'brasileirao': 'Brasileirão',
            'brasileirao serie a': 'Brasileirão', 'campeonato brasileiro': 'Brasileirão',
            'copa do brasil': 'Copa do Brasil', 'brazilian cup': 'Copa do Brasil',
            'copa libertadores': 'Libertadores', 'libertadores': 'Libertadores',
            'serie b': 'Serie B', 'serie c': 'Serie C'}.get(key, name)


def parse_date(value):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Unsupported date: {value!r}')


def number(value):
    if value is None or str(value).strip().lower() in ('', 'na', 'n/a', 'nan', 'none', 'null', '-'):
        return None
    f = float(value)
    if f != int(f) or f < 0:
        raise ValueError(f'Expected non-negative integer, got {value!r}')
    return int(f)


DERBIES = [tuple(map(team_key, pair)) for pair in (
    ('Flamengo', 'Fluminense'), ('Flamengo', 'Vasco'), ('Flamengo', 'Botafogo'),
    ('Fluminense', 'Vasco'), ('Fluminense', 'Botafogo'), ('Vasco', 'Botafogo'),
    ('Corinthians', 'Palmeiras'), ('Corinthians', 'São Paulo'), ('Corinthians', 'Santos'),
    ('Palmeiras', 'São Paulo'), ('Palmeiras', 'Santos'), ('São Paulo', 'Santos'),
    ('Grêmio', 'Internacional'), ('Cruzeiro', 'Atlético-MG'), ('Bahia', 'Vitória'),
    ('Athletico-PR', 'Coritiba'), ('Sport', 'Náutico'), ('Sport', 'Santa Cruz'),
    ('Ceará', 'Fortaleza'), ('Avaí', 'Figueirense'), ('Goiás', 'Vila Nova'))]


def page(rows, limit=50, offset=0):
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('limit must be an integer from 1 to 500')
    if type(offset) is not int or offset < 0:
        raise ValueError('offset must be a non-negative integer')
    return {'total': len(rows), 'offset': offset, 'items': rows[offset:offset + limit],
            'next_offset': offset + limit if offset + limit < len(rows) else None}


class SoccerGraph:
    """Canonical entities with match/team/competition and player/club relationships.

    Source records remain attached to merged fixtures. Queries use canonical fixtures
    once, with the first listed file taking priority on conflicting scores.
    """

    def __init__(self, data_dir=DATA_DIR):
        self.matches = []
        self.players = []
        self.sources = {}
        self.warnings = []
        fixtures = {}
        canonical_names = {}
        by_pair = defaultdict(list)
        for filename in FILES:
            path = Path(data_dir) / filename
            with path.open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.sources[filename] = len(rows)
            for line, row in enumerate(rows, 2):
                try:
                    if filename == 'fifa_data.csv':
                        self.players.append({
                            'id': 'player:' + row['ID'], 'name': row['Name'],
                            'age': number(row['Age']), 'nationality': row['Nationality'],
                            'overall': number(row['Overall']), 'potential': number(row['Potential']),
                            'club': normalize_team(row['Club']) if row['Club'] else None,
                            'position': row['Position'], 'attributes': {k: v for k, v in row.items() if k},
                            'source': filename})
                        continue
                    m = self._match(row, filename)
                    for field in ('home_team', 'away_team'):
                        m[field] = canonical_names.setdefault(team_key(m[field]), m[field])
                    key = (m['date'], m['competition'], team_key(m['home_team']), team_key(m['away_team']))
                    provenance = {'file': filename, 'line': line, 'record': row}
                    pair = key[1:]
                    if key not in fixtures and m['date']:
                        # Some feeds express evening kick-offs on the next UTC calendar day.
                        nearby = [old_key for old_key in by_pair[pair]
                                  if old_key[0] and abs((Date.fromisoformat(old_key[0]) - Date.fromisoformat(m['date'])).days) <= 1
                                  and not any(s['file'] == filename for s in fixtures[old_key]['sources'])
                                  and ((fixtures[old_key]['home_goal'], fixtures[old_key]['away_goal']) == (m['home_goal'], m['away_goal'])
                                       or fixtures[old_key]['home_goal'] is None or fixtures[old_key]['away_goal'] is None
                                       or m['home_goal'] is None or m['away_goal'] is None)]
                        if len(nearby) == 1:
                            key = nearby[0]
                    if key in fixtures:
                        old = fixtures[key]
                        old['sources'].append(provenance)
                        if (old['home_goal'], old['away_goal']) != (m['home_goal'], m['away_goal']):
                            if old['home_goal'] is None or old['away_goal'] is None:
                                old['home_goal'], old['away_goal'] = m['home_goal'], m['away_goal']
                            else:
                                self.warnings.append(f'Conflicting score: {old["id"]} in {filename}:{line}; first source retained')
                        for field in ('stage', 'round', 'stadium'):
                            if not old[field]:
                                old[field] = m[field]
                        old['statistics'].update(m['statistics'])
                    else:
                        m['id'] = 'match:' + hashlib.sha256('|'.join(str(k) for k in key).encode()).hexdigest()[:16]
                        m['sources'] = [provenance]
                        fixtures[key] = m
                        by_pair[pair].append(key)
                except (ValueError, KeyError) as exc:
                    raise ValueError(f'{filename}:{line}: {exc}') from exc
        self.matches = sorted(fixtures.values(), key=lambda m: (m['date'] or '', m['id']), reverse=True)
        self.by_team = defaultdict(list)
        self.teams = {}
        for m in self.matches:
            for name in (m['home_team'], m['away_team']):
                self.by_team[team_key(name)].append(m)
                self.teams[team_key(name)] = name
        for p in self.players:
            if p['club']:
                self.teams.setdefault(team_key(p['club']), p['club'])

    @staticmethod
    def _match(r, source):
        historical = source == 'novo_campeonato_brasileiro.csv'
        extended = source == 'BR-Football-Dataset.csv'
        raw_date = r['Data'] if historical else r['date'] if extended else r['datetime']
        date = None if raw_date.strip().lower() in ('', 'na', 'nan') else parse_date(raw_date)
        home = r['Equipe_mandante'] if historical else r['home'] if extended else r['home_team']
        away = r['Equipe_visitante'] if historical else r['away'] if extended else r['away_team']
        comp = (competition_name(r['tournament']) if extended else
                'Copa do Brasil' if source == 'Brazilian_Cup_Matches.csv' else
                'Libertadores' if source == 'Libertadores_Matches.csv' else 'Brasileirão')
        return {'date': date, 'datetime': r.get('datetime', (date or '') + (' ' + r['time'] if extended else '')),
                'home_team': normalize_team(home), 'away_team': normalize_team(away),
                'home_goal': number(r['Gols_mandante'] if historical else r['home_goal']),
                'away_goal': number(r['Gols_visitante'] if historical else r['away_goal']),
                'competition': comp, 'season': number(r.get('Ano', r.get('season', date[:4] if date else None))),
                'round': r.get('Rodada', r.get('round', '')), 'stage': r.get('stage', ''),
                'stadium': r.get('Arena', ''),
                'statistics': {k: v for k, v in r.items() if extended and k not in
                               {'date', 'time', 'home', 'away', 'home_goal', 'away_goal', 'tournament'}}}

    def _select(self, team=None, opponent=None, venue='either', competition=None,
                season=None, date_from=None, date_to=None, stage=None, derbies=False, source=None):
        if venue not in ('home', 'away', 'either'):
            raise ValueError('venue must be home, away, or either')
        if opponent and not team:
            raise ValueError('opponent requires team')
        start = parse_date(date_from) if date_from else None
        end = parse_date(date_to) if date_to else None
        if start and end and start > end:
            raise ValueError('date_from must not be later than date_to')
        comp = competition_name(competition) if competition else None
        candidates = self.by_team.get(team_key(team), []) if team else self.matches
        result = []
        for m in candidates:
            h, a = team_key(m['home_team']), team_key(m['away_team'])
            if team and venue != 'either' and team_key(team) != (h if venue == 'home' else a):
                continue
            if opponent and team_key(opponent) != (a if h == team_key(team) else h):
                continue
            if comp and m['competition'] != comp or season is not None and m['season'] != int(season):
                continue
            if (start or end) and not m['date']:
                continue
            if start and m['date'] < start or end and m['date'] > end:
                continue
            if source and not any(s['file'] == source for s in m['sources']):
                continue
            if derbies and not any({h, a} == set(pair) for pair in DERBIES):
                continue
            if stage:
                actual = m['stage'] or m['round']
                if fold(stage) == 'final' and m['competition'] == 'Copa do Brasil':
                    # Primary cup dataset uses seven rounds through 2016 and eight from 2017.
                    actual = 'final' if m['round'] == ('8' if m['season'] >= 2017 else '7') else actual
                if fold(actual) != fold(stage):
                    continue
            result.append(m)
        return result

    def search_matches(self, team=None, opponent=None, venue='either', competition=None,
                       season=None, date_from=None, date_to=None, stage=None, derbies=False,
                       source=None, limit=50, offset=0):
        """Find results or fixtures, newest first. Opponent matches either orientation.

        stage='final' selects finals, not semifinals. source selects provenance file.
        """
        return page(self._select(team, opponent, venue, competition, season, date_from,
                                 date_to, stage, derbies, source), limit, offset)

    @staticmethod
    def _record(team, matches):
        record = dict(team=normalize_team(team), matches=0, wins=0, draws=0, losses=0,
                      goals_for=0, goals_against=0, points=0)
        for m in matches:
            if m['home_goal'] is None or m['away_goal'] is None:
                continue
            gf, ga = m['home_goal'], m['away_goal']
            if team_key(m['away_team']) == team_key(team):
                gf, ga = ga, gf
            record['matches'] += 1
            record['goals_for'] += gf
            record['goals_against'] += ga
            record['wins' if gf > ga else 'losses' if gf < ga else 'draws'] += 1
        record['points'] = record['wins'] * 3 + record['draws']
        record['goal_difference'] = record['goals_for'] - record['goals_against']
        record['win_rate'] = round(100 * record['wins'] / record['matches'], 2) if record['matches'] else 0.0
        return record

    def team_statistics(self, team: str, competition=None, season=None, venue='either'):
        """W/D/L, goals and win percentage, grouped by competition; snapshot players included."""
        matches = self._select(team=team, competition=competition, season=season, venue=venue)
        return {**self._record(team, matches), 'competition': competition, 'season': season, 'venue': venue,
                'by_competition': {c: self._record(team, [m for m in matches if m['competition'] == c])
                                   for c in sorted({m['competition'] for m in matches})},
                'players': self.search_players(club=team),
                'note': 'Player clubs are FIFA snapshot affiliations, not historical match rosters.'}

    def head_to_head(self, team: str, opponent: str, competition=None, season=None):
        """Compare teams in both home/away orientations, across all matching fixtures."""
        if team_key(team) == team_key(opponent):
            raise ValueError('Choose two different teams')
        matches = self._select(team=team, opponent=opponent, competition=competition, season=season)
        return {'team': self._record(team, matches), 'opponent': self._record(opponent, matches),
                'latest_match': matches[0] if matches else None}

    def search_players(self, name=None, nationality=None, club=None, position=None, min_rating=None,
                       limit=50, offset=0):
        """Search FIFA snapshot; ratings descending. position='forward' includes ST/CF/LW/RW/LF/RF."""
        rows = []
        for p in self.players:
            if name and fold(name) not in fold(p['name']):
                continue
            if nationality and fold(nationality) != fold(p['nationality']):
                continue
            if club and (not p['club'] or (team_key(club) != team_key(p['club']) if team_key(club) in self.teams else team_key(club) not in team_key(p['club']))):
                continue
            positions = {'ST', 'CF', 'LW', 'RW', 'LF', 'RF', 'LS', 'RS'} if fold(position or '') in ('forward', 'forwards') else {str(position).upper()}
            if position and p['position'] not in positions:
                continue
            if min_rating is not None and (p['overall'] is None or p['overall'] < min_rating):
                continue
            rows.append(p)
        rows.sort(key=lambda p: (-(p['overall'] or 0), p['name'], p['id']))
        return {**page(rows, limit, offset), 'note': 'Historical FIFA snapshot; not current squads. No individual match goals are provided.'}

    def standings(self, competition: str, season: int):
        """Calculate league points (3/1/0), wins and goal difference. No official deductions applied."""
        competition = competition_name(competition)
        if competition not in ('Brasileirão', 'Serie B'):
            raise ValueError('League standings only support Brasileirão and Serie B; use bracket for cups. Serie C includes groups.')
        matches = self._select(competition=competition, season=season)
        teams = sorted({m[k] for m in matches for k in ('home_team', 'away_team')})
        rows = [self._record(t, [m for m in matches if t in (m['home_team'], m['away_team'])]) for t in teams]
        rows.sort(key=lambda r: (-r['points'], -r['wins'], -r['goal_difference'], -r['goals_for'], r['team']))
        pairs = Counter((m['home_team'], m['away_team']) for m in matches if m['home_goal'] is not None and m['away_goal'] is not None)
        complete = bool(rows) and len(pairs) == len(teams) * (len(teams) - 1) and all(n == 1 for n in pairs.values())
        for i, r in enumerate(rows, 1):
            r['rank'] = i
        return {'competition': competition, 'season': season, 'table': rows,
                'complete_double_round_robin': complete,
                'calculated_leader': rows[0]['team'] if rows else None,
                'relegation_candidates': [r['team'] for r in rows[-4:]] if complete and season >= 2006 else [],
                'note': 'Calculated from available results; not official standings. Deductions, disciplinary and head-to-head tie-breakers unavailable. Alphabetical order breaks remaining ties. Relegation candidates assume four relegation places from 2006.'}

    def bracket(self, competition: str, season: int):
        """Group cup fixtures by stage/round. Does not invent advancement or penalty results."""
        competition = competition_name(competition)
        if competition not in ('Copa do Brasil', 'Libertadores'):
            raise ValueError('bracket requires Copa do Brasil or Libertadores')
        groups = defaultdict(list)
        for m in self._select(competition=competition, season=season):
            groups[m['stage'] or m['round'] or 'unknown'].append(m)
        return {'competition': competition, 'season': season, 'stages': dict(groups),
                'note': 'Stage-grouped fixtures, not inferred advancement. Penalty shootouts and aggregate tie-breakers unavailable. Cup round 7 (through 2016) / 8 (from 2017) is interpreted as final where present.'}

    def analysis(self, competition=None, season=None, team=None, venue='either', limit=10):
        """Goal averages, biggest wins, home/away win rates and ranked team records."""
        matches = self._select(team=team, competition=competition, season=season, venue=venue)
        played = [m for m in matches if m['home_goal'] is not None and m['away_goal'] is not None]
        n = len(played)
        grouped = defaultdict(list)
        for m in played:
            if venue in ('home', 'either'):
                grouped[m['home_team']].append(m)
            if venue in ('away', 'either'):
                grouped[m['away_team']].append(m)
        records = [self._record(t, games) for t, games in grouped.items()]
        records.sort(key=lambda r: (-r['win_rate'], -r['points'], r['team']))
        biggest = sorted([m for m in played if m['home_goal'] != m['away_goal']],
                         key=lambda m: (-abs(m['home_goal'] - m['away_goal']), m['date'] or ''))
        return {'matches': n, 'average_goals': sum(m['home_goal'] + m['away_goal'] for m in played) / n if n else None,
                'home_win_rate': 100 * sum(m['home_goal'] > m['away_goal'] for m in played) / n if n else None,
                'away_win_rate': 100 * sum(m['home_goal'] < m['away_goal'] for m in played) / n if n else None,
                'draw_rate': 100 * sum(m['home_goal'] == m['away_goal'] for m in played) / n if n else None,
                'team_records': page(records, limit), 'biggest_wins': page(biggest, limit),
                'highest_scoring_teams': page(sorted(records, key=lambda r: (-r['goals_for'], r['team'])), limit),
                'individual_top_scorers': {'available': False, 'reason': 'No scorer events or individual match goal totals in the provided datasets.'}}

    def season_comparison(self, seasons: list[int], competition='Brasileirão', team=None):
        """Compare aggregate season statistics, or a team's season-by-season performance."""
        if not seasons or len(seasons) > 30:
            raise ValueError('Provide 1 to 30 seasons')
        return {str(s): self.team_statistics(team, competition, s) if team else
                self.analysis(competition, s) for s in seasons}

    def graph_neighbors(self, entity_type: str, entity: str, limit=50, offset=0):
        """Traverse team -> played match, player -> affiliated club, competition -> match edges."""
        edges = []
        if entity_type == 'team':
            key = team_key(entity)
            edges = [{'subject': 'team:' + key, 'relation': 'PLAYED_IN', 'object': m['id']}
                     for m in self.by_team.get(key, [])]
            edges += [{'subject': p['id'], 'relation': 'AFFILIATED_WITH', 'object': 'team:' + key}
                      for p in self.players if p['club'] and team_key(p['club']) == key]
            edges += [{'subject': 'team:' + key, 'relation': 'COMPETED_IN', 'object': c}
                      for c in sorted({m['competition'] for m in self.by_team.get(key, [])})]
        elif entity_type == 'player':
            edges = [{'subject': p['id'], 'relation': 'AFFILIATED_WITH', 'object': 'team:' + team_key(p['club'])}
                     for p in self.players if p['club'] and (p['id'] == entity or fold(entity) in fold(p['name']))]
        elif entity_type == 'competition':
            edges = [{'subject': m['id'], 'relation': 'PART_OF', 'object': m['competition']}
                     for m in self._select(competition=entity)]
        else:
            raise ValueError('entity_type must be team, player or competition')
        return page(edges, limit, offset)

    def dataset_info(self):
        """Coverage, source row counts and data quality warnings. Use before claims of completeness."""
        return {'source_rows': self.sources, 'unique_matches': len(self.matches), 'players': len(self.players),
                'undated_matches': sum(m['date'] is None for m in self.matches),
                'matches_without_result': sum(m['home_goal'] is None or m['away_goal'] is None for m in self.matches),
                'competitions': {c: {'seasons': sorted({m['season'] for m in self.matches if m['competition'] == c and m['season'] is not None}),
                                     'matches': sum(m['competition'] == c for m in self.matches)}
                                 for c in sorted({m['competition'] for m in self.matches})},
                'date_range': [min((m['date'] for m in self.matches if m['date']), default=None), max((m['date'] for m in self.matches if m['date']), default=None)] if self.matches else [],
                'warnings': self.warnings, 'deduplication': 'Same competition and normalized home/away teams on the same date; cross-source one-day date differences merge only with matching or missing scores and one candidate. First source wins conflicts and supplies the season.',
                'limitations': ['Historical snapshots, not live data.', 'No individual scorers or penalty shootout results.',
                                'Missing fixtures and unresolved naming variations may affect totals.',
                                'Traditional derbies use a curated, non-exhaustive list.']}
