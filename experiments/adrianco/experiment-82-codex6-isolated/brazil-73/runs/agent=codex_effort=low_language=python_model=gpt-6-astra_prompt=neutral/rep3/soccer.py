"""Offline Brazilian soccer knowledge graph and query engine (Python 3.10+)."""
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

FILES = ('Brasileirao_Matches.csv', 'Brazilian_Cup_Matches.csv',
         'Libertadores_Matches.csv', 'novo_campeonato_brasileiro.csv',
         'BR-Football-Dataset.csv', 'fifa_data.csv')


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value))
                   if not unicodedata.combining(c)).lower().strip()


ALIASES = {
    'botafogo rj': 'botafogo', 'vasco da gama rj': 'vasco da gama',
    'ec bahia': 'bahia', 'ec juventude': 'juventude', 'fortaleza fc': 'fortaleza',
    'santa cruz fc': 'santa cruz', 'atletico goianiense': 'atletico-go',
    'sport club corinthians paulista': 'corinthians', 'sao paulo fc': 'sao paulo',
    'sao paulo futebol clube': 'sao paulo', 'clube de regatas do flamengo': 'flamengo',
    'sociedade esportiva palmeiras': 'palmeiras', 'santos fc': 'santos',
    'vasco': 'vasco da gama', 'cr vasco da gama': 'vasco da gama',
    'atletico mineiro': 'atletico-mg', 'atletico mg': 'atletico-mg',
    'athletico-pr': 'atletico-pr', 'athletico paranaense': 'atletico-pr',
    'athletico': 'atletico-pr', 'atletico paranaense': 'atletico-pr', 'atletico pr': 'atletico-pr',
    'atletico go': 'atletico-go', 'america mg': 'america-mg',
    'america mineiro': 'america-mg', 'bragantino': 'red bull bragantino',
    'rb bragantino': 'red bull bragantino', 'sport recife': 'sport',
    'sport club do recife': 'sport', 'gremio prudente': 'barueri',
    'gremio barueri': 'barueri', 'botafogo pb': 'botafogo-pb',
}
STATES = 'ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to'.split()
DEFAULT_STATES = dict(zip(
    ['flamengo', 'botafogo', 'guarani', 'internacional', 'juventude', 'nautico', 'bragantino', 'operario', 'vitoria', 'cruzeiro', 'santa cruz'],
    ['rj', 'rj', 'sp', 'rs', 'rs', 'pe', 'sp', 'pr', 'ba', 'mg', 'pe']))


def team_key(name):
    name = re.sub(r'\s+', ' ', fold(name))
    suffix = re.fullmatch(r'(.*?)\s*-\s*(' + '|'.join(STATES) + ')', name)
    if suffix:
        base, state = suffix.groups()
        base = base.strip()
        if base in ('atletico', 'america', 'athletico'):
            name = base + '-' + state
        elif base in DEFAULT_STATES and DEFAULT_STATES[base] != state:
            name = base + '-' + state
        else:
            name = base
    return ALIASES.get(name, name)


def competition_key(value):
    key = fold(value)
    return {'serie a': 'Brasileirão Série A', 'brasileirao': 'Brasileirão Série A',
            'brasileirao serie a': 'Brasileirão Série A', 'copa do brasil': 'Copa do Brasil',
            'libertadores': 'Copa Libertadores', 'copa libertadores': 'Copa Libertadores',
            'serie b': 'Série B', 'serie c': 'Série C'}.get(key, value)


def date_key(value):
    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Invalid date: {value!r}; use YYYY-MM-DD or DD/MM/YYYY')


def number(value):
    if value is None or str(value).strip().lower() in ('', '-', 'nan', 'na', 'null'):
        return None
    n = float(value)
    if not n.is_integer() or n < 0:
        raise ValueError(f'Invalid nonnegative integer: {value}')
    return int(n)


def page(rows, limit=50, offset=0):
    if type(limit) is not int or not 1 <= limit <= 500 or type(offset) is not int or offset < 0:
        raise ValueError('limit must be 1..500 and offset must be nonnegative integers')
    return {'total': len(rows), 'offset': offset, 'items': rows[offset:offset + limit],
            'next_offset': offset + limit if offset + limit < len(rows) else None}


DERBIES = [frozenset(map(team_key, pair)) for pair in (
    ('Flamengo', 'Fluminense'), ('Corinthians', 'Palmeiras'), ('Santos', 'Sao Paulo'),
    ('Corinthians', 'Sao Paulo'), ('Palmeiras', 'Sao Paulo'), ('Santos', 'Corinthians'),
    ('Santos', 'Palmeiras'), ('Gremio', 'Internacional'), ('Atletico-MG', 'Cruzeiro'),
    ('Bahia', 'Vitoria'), ('Athletico-PR', 'Coritiba'), ('Sport', 'Santa Cruz'),
    ('Flamengo', 'Vasco'), ('Botafogo', 'Fluminense'), ('Botafogo', 'Flamengo'),
    ('Vasco', 'Fluminense'), ('Vasco', 'Botafogo'), ('Ceara', 'Fortaleza'))]


class SoccerGraph:
    """Canonical entities linked through fixtures, roster membership and provenance."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir or Path(__file__).parent / 'data/kaggle')
        self.matches = []
        self.players = []
        self.sources = {}
        self.warnings = []
        identities = {}
        pair_index = defaultdict(list)
        for filename in FILES:
            with (self.data_dir / filename).open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.sources[filename] = len(rows)
            if filename == 'fifa_data.csv':
                for r in rows:
                    self.players.append({'id': 'player:' + r['ID'], 'name': r['Name'],
                                         'nationality': r['Nationality'], 'club': team_key(r['Club']),
                                         'overall': number(r['Overall']), 'potential': number(r['Potential']),
                                         'position': r['Position'], 'attributes': {k: v for k, v in r.items() if k}})
                continue
            for line, r in enumerate(rows, 2):
                try:
                    m = self._convert(filename, r)
                except (ValueError, KeyError) as exc:
                    raise ValueError(f'{filename}:{line}: {exc}') from exc
                # Calendar date is insufficient for overlapping pandemic seasons;
                # official season/round is preferred when present.
                identity = (m['competition'], m['date'], m['home_team'], m['away_team'])
                pair = (m['competition'], m['home_team'], m['away_team'])
                if identity not in identities and m['date']:
                    for candidate in pair_index[pair]:
                        if (candidate['date'] and
                            not any(s['file'] == filename for s in candidate['sources']) and
                            (candidate['home_goal'], candidate['away_goal']) == (m['home_goal'], m['away_goal']) and
                            abs((datetime.fromisoformat(candidate['date']) - datetime.fromisoformat(m['date'])).days) <= 1):
                            identities[identity] = candidate
                            break
                origin = {'file': filename, 'line': line, 'record': r}
                if identity in identities:
                    old = identities[identity]
                    if (old['home_goal'], old['away_goal']) != (m['home_goal'], m['away_goal']):
                        self.warnings.append(f'Score conflict: {old["id"]}; retained first source')
                    old['sources'].append(origin)
                    old['statistics'].update(m['statistics'])
                    for field in ('stage', 'round', 'stadium'):
                        if not old[field]:
                            old[field] = m[field]
                else:
                    m['id'] = f'match:{len(self.matches) + 1}'
                    m['sources'] = [origin]
                    identities[identity] = m
                    self.matches.append(m)
                    pair_index[pair].append(m)
        self.matches.sort(key=lambda m: (m['date'], m['id']), reverse=True)
        self.by_team = defaultdict(list)
        for m in self.matches:
            for team in (m['home_team'], m['away_team']):
                self.by_team[team].append(m)

    @staticmethod
    def _convert(filename, r):
        historical = filename == FILES[3]
        extended = filename == FILES[4]
        raw_date = r['Data'] if historical else r['date'] if extended else r['datetime']
        date = '' if fold(raw_date) in ('na', '', '-') else date_key(raw_date)
        home = r['Equipe_mandante'] if historical else r['home'] if extended else r['home_team']
        away = r['Equipe_visitante'] if historical else r['away'] if extended else r['away_team']
        competition = (r['tournament'] if extended else 'Copa do Brasil' if filename == FILES[1]
                       else 'Copa Libertadores' if filename == FILES[2] else 'Serie A')
        return {'date': date, 'home_team': team_key(home), 'away_team': team_key(away),
                'home_goal': number(r.get('Gols_mandante') if historical else r.get('home_goal')),
                'away_goal': number(r.get('Gols_visitante') if historical else r.get('away_goal')),
                'competition': competition_key(competition),
                'season': number(r['Ano'] if historical else r.get('season', date[:4])),
                'season_inferred': extended, 'round': r.get('Rodada', r.get('round', '')),
                'stage': r.get('stage', ''), 'stadium': r.get('Arena', ''),
                'statistics': {k: v for k, v in r.items() if extended and k not in
                               ('home', 'away', 'home_goal', 'away_goal', 'date', 'tournament')}}

    def _select(self, team=None, opponent=None, venue='either', competition=None, season=None,
                start_date=None, end_date=None, stage=None, derbies=False, source=None):
        if venue not in ('either', 'home', 'away'):
            raise ValueError('venue must be either, home or away')
        if opponent and not team:
            raise ValueError('opponent requires team')
        if season is not None and (type(season) is not int or season < 1800):
            raise ValueError('season must be an integer year')
        team = team_key(team) if team else None
        opponent = team_key(opponent) if opponent else None
        competition = competition_key(competition) if competition else None
        start = date_key(start_date) if start_date else ''
        end = date_key(end_date) if end_date else '9999'
        if start > end:
            raise ValueError('start_date must not follow end_date')
        if source and source not in self.sources:
            raise ValueError('Unknown source filename')
        result = []
        for m in self.by_team.get(team, []) if team else self.matches:
            if team and venue != 'either' and m[venue + '_team'] != team:
                continue
            if opponent and {team, opponent} != {m['home_team'], m['away_team']}:
                continue
            if competition and m['competition'] != competition or season is not None and m['season'] != season:
                continue
            if not start <= m['date'] <= end:
                continue
            if stage and fold(stage) not in (fold(m['stage']), fold(m['round'])):
                continue
            if derbies and frozenset((m['home_team'], m['away_team'])) not in DERBIES:
                continue
            if source and not any(s['file'] == source for s in m['sources']):
                continue
            result.append(m)
        return result

    def search_matches(self, limit=50, offset=0, **filters):
        """Find fixtures, newest first; opponent matches both directions. Stage is exact."""
        return page(self._select(**filters), limit, offset)

    @staticmethod
    def _record(team, matches):
        record = dict(team=team, played=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0)
        for m in matches:
            if m['home_goal'] is None or m['away_goal'] is None:
                continue
            home = m['home_team'] == team
            gf, ga = (m['home_goal'], m['away_goal']) if home else (m['away_goal'], m['home_goal'])
            record['played'] += 1
            record['goals_for'] += gf
            record['goals_against'] += ga
            record['wins' if gf > ga else 'losses' if gf < ga else 'draws'] += 1
        record.update(points=record['wins'] * 3 + record['draws'],
                      goal_difference=record['goals_for'] - record['goals_against'],
                      win_rate=round(100 * record['wins'] / record['played'], 2) if record['played'] else 0)
        return record

    def team_stats(self, team, **filters):
        """Dataset W/D/L and goals, with competition breakdown and historical FIFA roster."""
        team = team_key(team)
        matches = self._select(team=team, **filters)
        return {**self._record(team, matches), 'by_competition': {
            c: self._record(team, [m for m in matches if m['competition'] == c])
            for c in sorted({m['competition'] for m in matches})},
            'roster': self.search_players(club=team), 'note': 'Roster is the FIFA snapshot, not a current roster.'}

    def head_to_head(self, team, opponent, **filters):
        """Compare two teams across both home/away orientations."""
        if team_key(team) == team_key(opponent):
            raise ValueError('Choose two different teams')
        matches = self._select(team=team, opponent=opponent, **filters)
        return {'team': self._record(team_key(team), matches),
                'opponent': self._record(team_key(opponent), matches), 'latest': matches[:1]}

    def search_players(self, name=None, nationality=None, club=None, position=None, min_rating=0, limit=50, offset=0):
        """Search the historical FIFA snapshot; position='forward' includes attacking positions."""
        positions = {'ST', 'CF', 'LF', 'RF', 'LW', 'RW', 'LS', 'RS'} if position and fold(position) in ('forward', 'forwards') else {str(position).upper()}
        rows = [p for p in self.players if
                (not name or fold(name) in fold(p['name'])) and
                (not nationality or fold(nationality) == fold(p['nationality'])) and
                (not club or team_key(club) == p['club']) and
                (not position or p['position'] in positions) and (p['overall'] or 0) >= min_rating]
        return page(sorted(rows, key=lambda p: (-(p['overall'] or 0), p['name'])), limit, offset)

    def standings(self, competition, season, venue='either'):
        """Calculated league table. Cup results cannot establish a league champion."""
        competition = competition_key(competition)
        if competition not in ('Brasileirão Série A', 'Série B', 'Série C'):
            raise ValueError('Use competition_results for cup stages; league standings do not apply')
        matches = self._select(competition=competition, season=season, venue=venue)
        teams = {m[k] for m in matches for k in ('home_team', 'away_team')}
        rows = [self._record(t, [m for m in matches if
                (t in (m['home_team'], m['away_team']) if venue == 'either' else m[venue + '_team'] == t)]) for t in teams]
        rows.sort(key=lambda r: (-r['points'], -r['wins'], -r['goal_difference'], -r['goals_for'], r['team']))
        for i, r in enumerate(rows, 1):
            r['rank'] = i
        return {'table': rows, 'competition': competition, 'season': season,
                'note': 'Dataset-derived ranking: points, wins, goal difference, goals for, name. '
                        'May include partial seasons or conflicting source fixtures; no disciplinary deductions '
                        'or remaining official tiebreakers. First/last places are not certified champions/relegations.'}

    def competition_results(self, competition, season, stage=None, limit=50, offset=0):
        """Results/stages for reconstructing brackets. Numeric cup rounds are preserved, not guessed."""
        matches = self._select(competition=competition, season=season, stage=stage)
        return {**page(matches, limit, offset), 'stages': dict(Counter(m['stage'] or m['round'] or 'unknown' for m in matches)),
                'note': 'No scorer events, penalty shootouts or reliable round-to-stage mapping in cup CSV. '
                        'Numeric rounds cannot safely identify finals; progression is not inferred.'}

    def analysis(self, competition=None, season=None, team=None, venue='either', limit=10):
        """Goals averages, biggest wins, team home/away rankings and season trends."""
        page([], limit)
        matches = self._select(competition=competition, season=season, team=team, venue=venue)
        played = [m for m in matches if m['home_goal'] is not None and m['away_goal'] is not None]
        def aggregate(ms):
            n = len(ms)
            return {'matches': n, 'average_goals': sum(m['home_goal'] + m['away_goal'] for m in ms) / n if n else 0,
                    'home_win_rate': 100 * sum(m['home_goal'] > m['away_goal'] for m in ms) / n if n else 0}
        teams = {m[k] for m in played for k in ('home_team', 'away_team')}
        rankings = [self._record(t, [m for m in played if
                    (t in (m['home_team'], m['away_team']) if venue == 'either' else m[venue + '_team'] == t)]) for t in teams]
        rankings.sort(key=lambda r: (-r['win_rate'], -r['played'], r['team']))
        return {**aggregate(played), 'biggest_wins': sorted(
            [m for m in played if m['home_goal'] != m['away_goal']],
            key=lambda m: -abs(m['home_goal'] - m['away_goal']))[:limit],
                'rankings': rankings[:limit], 'seasons': {str(s): aggregate([m for m in played if m['season'] == s]) for s in sorted({m['season'] for m in played})},
                'note': 'Rankings use win rate, then games played; small samples may lead. Individual scorers unavailable.'}

    def graph_neighbors(self, entity_id, limit=50, offset=0):
        """Traverse team:<normalized name>, match:<id>, or player:<FIFA ID> nodes."""
        edges = []
        kind, _, key = entity_id.partition(':')
        if kind == 'team':
            key = team_key(key)
            edges += [{'relation': 'PLAYED_IN', 'target': m['id']} for m in self.by_team.get(key, [])]
            edges += [{'relation': 'HAS_PLAYER', 'target': p['id']} for p in self.players if p['club'] == key]
            edges += [{'relation': 'COMPETES_IN', 'target': 'competition:' + c} for c in sorted({m['competition'] for m in self.by_team.get(key, [])})]
        elif kind == 'match':
            for m in self.matches:
                if m['id'] == entity_id:
                    edges = [{'relation': side.upper(), 'target': 'team:' + m[side + '_team']} for side in ('home', 'away')]
                    edges.append({'relation': 'PART_OF', 'target': 'competition:' + m['competition']})
        elif kind == 'player':
            edges = [{'relation': 'PLAYS_FOR', 'target': 'team:' + p['club']} for p in self.players if p['id'] == entity_id and p['club']]
        elif kind == 'competition':
            edges = [{'relation': 'HAS_MATCH', 'target': m['id']} for m in self.matches if m['competition'] == competition_key(key)]
        else:
            raise ValueError('Expected team:, player:, match: or competition: entity ID')
        return page(edges, limit, offset)

    def coverage(self):
        """Report provenance, date/season coverage, source conflicts and limitations."""
        return {'sources': self.sources, 'matches': len(self.matches), 'players': len(self.players),
                'competitions': {c: {'matches': len(ms), 'seasons': sorted({m['season'] for m in ms if m['season'] is not None}),
                                     'first_date': min(m['date'] for m in ms), 'last_date': max(m['date'] for m in ms)}
                                 for c in sorted({m['competition'] for m in self.matches})
                                 for ms in [[m for m in self.matches if m['competition'] == c]]},
                'warnings': self.warnings,
                'limitations': ['Historical FIFA roster; no individual goal events.',
                               'Same competition/teams/date merged; matching scores within one day merged across sources. First source wins conflicts.',
                               'Larger date discrepancies remain separate and can inflate aggregates.',
                               'Extended-only fixtures infer season from calendar year, including pandemic seasons.',
                               'Cup round numbers retained; final labels cannot be reliably inferred.']}
