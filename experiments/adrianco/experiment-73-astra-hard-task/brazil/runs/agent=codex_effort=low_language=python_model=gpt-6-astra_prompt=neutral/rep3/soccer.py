"""Offline Brazilian football knowledge graph and query engine (Python 3.10+)."""
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c)).casefold().strip()


ALIASES = {
    'sport club corinthians paulista': 'corinthians', 'sao paulo fc': 'sao paulo',
    'sao paulo futebol clube': 'sao paulo', 'clube de regatas do flamengo': 'flamengo',
    'sociedade esportiva palmeiras': 'palmeiras', 'santos fc': 'santos',
    'vasco da gama': 'vasco', 'cr vasco da gama': 'vasco',
    'atletico mineiro': 'atletico-mg', 'atletico mg': 'atletico-mg',
    'athletico paranaense': 'atletico-pr', 'atletico paranaense': 'atletico-pr',
    'athletico-pr': 'atletico-pr', 'atletico pr': 'atletico-pr',
    'america mg': 'america-mg', 'botafogo rj': 'botafogo', 'gremio fbpa': 'gremio',
    'ec bahia': 'bahia', 'fortaleza fc': 'fortaleza', 'vasco da gama rj': 'vasco',
    'sport recife': 'sport', 'sport club do recife': 'sport',
}


def team_name(value):
    name = re.sub(r'\s+', ' ', fold(value))
    name = re.sub(r'\s*-\s*', '-', name)
    # Preserve state identifiers for ambiguous club names.
    name = ALIASES.get(name, name)
    if not re.match(r'^(atletico|america|operario|botafogo)-(?!rj)', name):
        name = re.sub(r'-(?:ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)$', '', name)
    return ALIASES.get(name, name)


def competition_name(value):
    name = fold(value)
    return {'serie a': 'Brasileirão', 'brasileirao': 'Brasileirão', 'brasileirao serie a': 'Brasileirão',
            'copa do brasil': 'Copa do Brasil', 'libertadores': 'Libertadores',
            'copa libertadores': 'Libertadores', 'serie b': 'Serie B', 'serie c': 'Serie C'}.get(name, value)


def date_value(value):
    if fold(value) in ('na', '', 'nan'): return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Unsupported date: {value!r}')


def number(value):
    if value is None or fold(value) in ('', 'na', 'nan', 'none', 'null', '-'):
        return None
    n = float(value)
    if not n.is_integer() or n < 0:
        raise ValueError(f'Invalid nonnegative integer: {value}')
    return int(n)


FILES = ['Brasileirao_Matches.csv', 'Brazilian_Cup_Matches.csv', 'Libertadores_Matches.csv',
         'BR-Football-Dataset.csv', 'novo_campeonato_brasileiro.csv', 'fifa_data.csv']
DERBIES = [set(map(team_name, pair)) for pair in [('Flamengo', 'Fluminense'), ('Corinthians', 'Palmeiras'),
           ('Santos', 'São Paulo'), ('Grêmio', 'Internacional'), ('Cruzeiro', 'Atlético-MG'),
           ('Vasco', 'Flamengo'), ('Botafogo', 'Flamengo'), ('Bahia', 'Vitória'), ('Sport', 'Santa Cruz')]]


class SoccerGraph:
    """Entities linked by match participation, competition membership and FIFA club."""
    def __init__(self, data_dir=None):
        self.matches = []
        self.players = []
        self.sources = Counter()
        self.errors = []
        self.teams = defaultdict(list)
        self._load(Path(data_dir) if data_dir else Path(__file__).parent / 'data' / 'kaggle')
        for match in self.matches:
            self.teams[match['home_team']].append(match)
            self.teams[match['away_team']].append(match)

    def _load(self, directory):
        seen = {}
        for filename in FILES:
            with (directory / filename).open(encoding='utf-8-sig', newline='') as stream:
                for line, row in enumerate(csv.DictReader(stream), 2):
                    self.sources[filename] += 1
                    try:
                        if filename == 'fifa_data.csv':
                            self.players.append({'id': row['ID'], 'name': row['Name'], 'club': team_name(row['Club']),
                                'nationality': row['Nationality'], 'position': row['Position'],
                                'overall': number(row['Overall']), 'potential': number(row['Potential']),
                                'age': number(row['Age']), 'attributes': row, 'source': filename})
                            continue
                        historical = filename.startswith('novo_')
                        extended = filename.startswith('BR-')
                        comp = ('Brasileirão' if historical else competition_name(row['tournament']) if extended else
                                {'Brasileirao_Matches.csv': 'Brasileirão', 'Brazilian_Cup_Matches.csv': 'Copa do Brasil',
                                 'Libertadores_Matches.csv': 'Libertadores'}[filename])
                        date = date_value(row['Data'] if historical else row['date'] if extended else row['datetime'])
                        home = team_name(row['Equipe_mandante'] if historical else row['home'] if extended else row['home_team'])
                        away = team_name(row['Equipe_visitante'] if historical else row['away'] if extended else row['away_team'])
                        hg = number(row['Gols_mandante'] if historical else row['home_goal'])
                        ag = number(row['Gols_visitante'] if historical else row['away_goal'])
                        key = (comp, date, home, away)
                        record = {'source': filename, 'row': line, 'raw': row}
                        # Resolve observed UTC/local-day differences only across sources,
                        # with identical teams and score and one unambiguous candidate.
                        if key not in seen and date and hg is not None and ag is not None:
                            candidates = []
                            for delta in (-1, 1):
                                nearby = (datetime.fromisoformat(date) + timedelta(days=delta)).date().isoformat()
                                candidate = seen.get((comp, nearby, home, away))
                                if candidate and (candidate['home_goal'], candidate['away_goal']) == (hg, ag) and not any(s['source'] == filename for s in candidate['sources']):
                                    candidates.append(candidate)
                            if len(candidates) == 1:
                                seen[key] = candidates[0]
                        if key in seen:
                            match = seen[key]
                            match['sources'].append(record)
                            if match['home_goal'] is None and match['away_goal'] is None and hg is not None and ag is not None:
                                match['home_goal'], match['away_goal'] = hg, ag
                            if hg is not None and ag is not None and (hg, ag) != (match['home_goal'], match['away_goal']):
                                match.setdefault('conflicts', []).append({'source': filename, 'score': [hg, ag]})
                            if extended:
                                match['statistics'] = row
                            if historical:
                                match['stadium'] = row.get('Arena')
                            continue
                        match = dict(id=f'match:{len(self.matches)+1}', date=date, home_team=home, away_team=away,
                            home_goal=hg, away_goal=ag, competition=comp,
                            season=number(row.get('season') or row.get('Ano') or (date[:4] if date else None)),
                            round=row.get('round') or row.get('Rodada'), stage=row.get('stage'),
                            stadium=row.get('Arena'), sources=[record], statistics=row if extended else {})
                        seen[key] = match
                        self.matches.append(match)
                    except (ValueError, KeyError) as exc:
                        self.errors.append({'source': filename, 'row': line, 'error': str(exc)})
        self.matches.sort(key=lambda m: (m['date'] or '', m['id']), reverse=True)

    def _select(self, team=None, opponent=None, venue='either', competition=None, season=None,
                start_date=None, end_date=None, stage=None, source=None, derbies=False):
        if venue not in ('home', 'away', 'either'):
            raise ValueError('venue must be home, away, or either')
        if opponent and not team:
            raise ValueError('opponent requires team')
        start = date_value(start_date) if start_date else None
        end = date_value(end_date) if end_date else None
        if start and end and start > end:
            raise ValueError('start_date must precede end_date')
        t, o = team_name(team) if team else None, team_name(opponent) if opponent else None
        comp = competition_name(competition) if competition else None
        for m in self.teams.get(t, []) if t else self.matches:
            h, a = m['home_team'], m['away_team']
            if t and (t != h if venue == 'home' else t != a if venue == 'away' else t not in (h, a)): continue
            if o and {h, a} != {t, o}: continue
            if comp and comp != m['competition']: continue
            if season is not None and int(season) != m['season']: continue
            if (start or end) and not m['date']: continue
            if start and m['date'] < start or end and m['date'] > end: continue
            if source and not any(s['source'] == source for s in m['sources']): continue
            if stage and fold(stage) != fold(m['stage'] or m['round'] or ''): continue
            if derbies and {h, a} not in DERBIES: continue
            yield m

    @staticmethod
    def _page(rows, limit, offset):
        if type(limit) is not int or not 1 <= limit <= 500 or type(offset) is not int or offset < 0:
            raise ValueError('limit must be 1..500 and offset must be nonnegative integers')
        return {'total': len(rows), 'offset': offset, 'results': rows[offset:offset+limit]}

    def search_matches(self, limit=50, offset=0, **filters):
        """Search results newest first; use opponent for head-to-head, source for provenance."""
        rows = sorted(self._select(**filters), key=lambda m: (m['date'] or '', m['id']), reverse=True)
        return self._page(rows, limit, offset)

    def search_players(self, name=None, nationality=None, club=None, position=None, min_rating=0, limit=50, offset=0):
        """FIFA snapshot only: attributes and club are historical, not live rosters."""
        positions = {'forward': {'ST','CF','LF','RF','LW','RW','LS','RS'},
                     'midfielder': {'CM','CAM','CDM','LM','RM','LCM','RCM','LDM','RDM','LAM','RAM'},
                     'defender': {'CB','LB','RB','LWB','RWB','LCB','RCB'}, 'goalkeeper': {'GK'}}
        allowed = positions.get(fold(position), {str(position).upper()}) if position else None
        rows = [p for p in self.players if (not name or fold(name) in fold(p['name']))
                and (not nationality or fold(nationality) == fold(p['nationality']))
                and (not club or team_name(club) == p['club'])
                and (not allowed or p['position'] in allowed) and (p['overall'] or 0) >= min_rating]
        rows.sort(key=lambda p: (-(p['overall'] or 0), p['name']))
        return self._page(rows, limit, offset)

    def team_statistics(self, team, **filters):
        t = team_name(team)
        record = dict(team=t, matches=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0)
        for m in self._select(team=t, **filters):
            if m['home_goal'] is None or m['away_goal'] is None: continue
            gf, ga = (m['home_goal'], m['away_goal']) if m['home_team'] == t else (m['away_goal'], m['home_goal'])
            record['matches'] += 1
            record['goals_for'] += gf
            record['goals_against'] += ga
            record['wins' if gf > ga else 'losses' if gf < ga else 'draws'] += 1
        record['points'] = record['wins'] * 3 + record['draws']
        record['goal_difference'] = record['goals_for'] - record['goals_against']
        record['win_rate'] = round(100 * record['wins'] / record['matches'], 2) if record['matches'] else 0
        return record

    def head_to_head(self, team, opponent, **filters):
        return {'record': self.team_statistics(team, opponent=opponent, **filters),
                'opponent': team_name(opponent), 'matches': self.search_matches(team=team, opponent=opponent, **filters)}

    def standings(self, competition, season, venue='either'):
        comp = competition_name(competition)
        if comp not in ('Brasileirão', 'Serie B', 'Serie C'):
            raise ValueError('Knockout competitions have no league table; use competition_results')
        teams = {m[k] for m in self._select(competition=comp, season=season) for k in ('home_team','away_team')}
        rows = [self.team_statistics(t, competition=comp, season=season, venue=venue) for t in teams]
        rows.sort(key=lambda r: (-r['points'], -r['wins'], -r['goal_difference'], -r['goals_for'], r['team']))
        for rank, row in enumerate(rows, 1): row['rank'] = rank
        return {'table': rows, 'note': 'Calculated from available results: 3 points/win, 1/draw. Ties ordered by wins, goal difference, goals for, then name. No deductions or official tie-breaks; incomplete coverage and group formats may apply. Not an official champion/relegation determination.'}

    def analysis(self, limit=10, **filters):
        rows = [m for m in self._select(**filters) if m['home_goal'] is not None and m['away_goal'] is not None]
        n = len(rows)
        biggest = sorted((m for m in rows if m['home_goal'] != m['away_goal']), key=lambda m: -abs(m['home_goal']-m['away_goal']))
        return {'matches': n, 'average_goals': sum(m['home_goal']+m['away_goal'] for m in rows)/n if n else None,
                'home_win_rate': 100*sum(m['home_goal']>m['away_goal'] for m in rows)/n if n else None,
                'biggest_wins': self._page(biggest, limit, 0)['results']}

    def team_profile(self, team):
        t = team_name(team)
        return {'team': t, 'statistics': self.team_statistics(t),
                'competitions': sorted({m['competition'] for m in self.teams.get(t, [])}),
                'players': self.search_players(club=t), 'note': 'Players are from the FIFA snapshot; no historical transfer inference.'}

    def trends(self, team=None, competition=None):
        seasons = sorted({m['season'] for m in self._select(team=team, competition=competition) if m['season'] is not None})
        return {str(s): self.team_statistics(team, season=s, competition=competition) if team else
                self.analysis(season=s, competition=competition) for s in seasons}

    def competition_results(self, competition, season):
        groups = defaultdict(list)
        for m in self._select(competition=competition, season=season):
            groups[m['stage'] or m['round'] or 'unknown'].append(m)
        return {'stages': dict(groups), 'note': 'Observed fixtures grouped by recorded stage/round. Cup numeric rounds are preserved without assuming a final. Missing penalty scores and draw links prevent a definitive knockout bracket.'}

    def top_scorers(self):
        return {'available': False, 'reason': 'These files contain team goals, not individual scoring events. FIFA finishing ratings are not goal counts.'}

    def coverage(self):
        return {'source_rows': dict(self.sources), 'unique_matches': len(self.matches), 'players': len(self.players),
                'date_min': min(m['date'] for m in self.matches if m['date']), 'date_max': max(m['date'] for m in self.matches if m['date']),
                'errors': self.errors, 'conflicting_matches': sum('conflicts' in m for m in self.matches)}

    def neighbors(self, entity, kind='team', limit=50, offset=0):
        """Explore explicit graph relations for a team, player ID, competition or match ID."""
        edges = []
        if kind == 'team':
            t = team_name(entity)
            edges = [{'relation': 'participated_in', 'target': m['id']} for m in self.teams.get(t, [])]
            edges += [{'relation': 'has_player', 'target': 'player:'+p['id']} for p in self.players if p['club'] == t]
        elif kind == 'player':
            edges = [{'relation': 'plays_for', 'target': p['club']} for p in self.players if p['id'] == entity.removeprefix('player:')]
        elif kind == 'competition':
            edges = [{'relation': 'has_match', 'target': m['id']} for m in self._select(competition=entity)]
        elif kind == 'match':
            for m in self.matches:
                if m['id'] == entity:
                    edges = [{'relation': k, 'target': m[k]} for k in ('home_team', 'away_team', 'competition')]
        else: raise ValueError('kind must be team, player, competition, or match')
        return self._page(edges, limit, offset)
