"""Brazilian soccer knowledge graph. Standard library only; data stays local."""
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data' / 'kaggle'
FILES = ['Brasileirao_Matches.csv', 'Brazilian_Cup_Matches.csv',
         'Libertadores_Matches.csv', 'BR-Football-Dataset.csv',
         'novo_campeonato_brasileiro.csv', 'fifa_data.csv']


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value))
                   if not unicodedata.combining(c)).lower().strip()


ALIASES = {
    'sport club corinthians paulista': 'corinthians', 'corinthians paulista': 'corinthians',
    'clube de regatas do flamengo': 'flamengo', 'sao paulo fc': 'sao paulo',
    'sao paulo futebol clube': 'sao paulo', 'santos fc': 'santos',
    'sociedade esportiva palmeiras': 'palmeiras', 'vasco': 'vasco da gama',
    'vasco da gama': 'vasco da gama', 'sport recife': 'sport',
    'sport club do recife': 'sport', 'gremio foot-ball porto alegrense': 'gremio',
    'atletico mineiro': 'atletico-mg', 'atletico mg': 'atletico-mg',
    'athletico': 'athletico-pr', 'athletico-pr': 'athletico-pr',
    'atletico-pr': 'athletico-pr', 'atletico paranaense': 'athletico-pr',
    'athletico paranaense': 'athletico-pr', 'atletico goianiense': 'atletico-go',
    'america mineiro': 'america-mg', 'bragantino': 'red bull bragantino',
    'rb bragantino': 'red bull bragantino', 'botafogo rj': 'botafogo', 'america mg': 'america-mg',
    'ec bahia': 'bahia', 'ec juventude': 'juventude', 'fortaleza fc': 'fortaleza',
    'santa cruz fc': 'santa cruz', 'vasco da gama rj': 'vasco da gama',
}
STATES = 'ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to'.split()
AMBIGUOUS = {'atletico', 'america', 'botafogo', 'bragantino'}


def team_name(value):
    name = re.sub(r'\s+', ' ', fold(value)).replace('.', '')
    m = re.match(r'^(.*?)\s*-\s*(' + '|'.join(STATES) + r')$', name)
    if m:
        base, state = m.groups()
        if base in AMBIGUOUS and (base, state) not in {('botafogo', 'rj'), ('bragantino', 'sp')}:
            name = base + '-' + state
        else:
            name = base
    return ALIASES.get(name, name)


def competition_name(value):
    key = fold(value)
    return {'serie a': 'Brasileirão', 'brasileirao': 'Brasileirão',
            'brasileirao serie a': 'Brasileirão', 'campeonato brasileiro': 'Brasileirão',
            'copa do brasil': 'Copa do Brasil', 'libertadores': 'Libertadores',
            'copa libertadores': 'Libertadores', 'serie b': 'Serie B',
            'serie c': 'Serie C'}.get(key, value)


def date_value(value):
    value = value.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Invalid date: {value!r}')


def number(value):
    if value is None or fold(value) in ('', 'nan', 'na', 'none', '-'):
        return None
    n = float(value)
    if not n.is_integer() or n < 0:
        raise ValueError(f'Invalid nonnegative integer: {value}')
    return int(n)


def record():
    return dict(matches=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0, points=0)


def accumulate(stats, scored, conceded):
    stats['matches'] += 1
    stats['goals_for'] += scored
    stats['goals_against'] += conceded
    stats['wins' if scored > conceded else 'losses' if scored < conceded else 'draws'] += 1
    stats['points'] += 3 if scored > conceded else 1 if scored == conceded else 0


def finish(stats):
    return dict(stats, goal_difference=stats['goals_for'] - stats['goals_against'],
                win_rate=round(100 * stats['wins'] / stats['matches'], 2) if stats['matches'] else 0)


class SoccerGraph:
    """Nodes and typed edges link teams, matches, players, competitions and seasons."""
    def __init__(self, data_dir=DATA):
        self.matches = []
        self.players = []
        self.sources = {}
        self.issues = []
        self.nodes = {}
        self.edges = defaultdict(list)
        fixtures = {}
        for filename in FILES:
            with (Path(data_dir) / filename).open(encoding='utf-8-sig', newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.sources[filename] = len(rows)
            if filename == 'fifa_data.csv':
                for row in rows:
                    p = dict(id=row['ID'], name=row['Name'], nationality=row['Nationality'],
                             club=team_name(row['Club']), position=row['Position'],
                             overall=number(row['Overall']), potential=number(row['Potential']),
                             age=number(row['Age']), attributes={k: v for k, v in row.items() if k},
                             source=filename)
                    self.players.append(p)
                continue
            for line, row in enumerate(rows, 2):
                try:
                    m = self._match(filename, row)
                except (ValueError, KeyError) as exc:
                    self.issues.append(dict(source=filename, line=line, error=str(exc)))
                    continue
                key = (m['competition'], m['date'], m['home_team'], m['away_team'])
                # Cross-source dates can differ by one day because of time zones.
                if key not in fixtures and m['date']:
                    for delta in (-1, 1):
                        adjacent = (datetime.fromisoformat(m['date']) + timedelta(days=delta)).date().isoformat()
                        candidate = (m['competition'], adjacent, m['home_team'], m['away_team'])
                        old = fixtures.get(candidate)
                        if old and not any(s['file'] == filename for s in old['sources']) and all(old[k] is None or m[k] is None or old[k] == m[k] for k in ('home_goal', 'away_goal')):
                            key = candidate
                            break
                provenance = dict(file=filename, line=line, raw=row)
                if key in fixtures:
                    old = fixtures[key]
                    if any(old[k] is not None and m[k] is not None and old[k] != m[k] for k in ('home_goal', 'away_goal')):
                        self.issues.append(dict(source=filename, line=line, error='Conflicting score', match_id=old['id']))
                    for field in ('home_goal', 'away_goal'):
                        if old[field] is None: old[field] = m[field]
                    for field in ('stage', 'round', 'stadium'):
                        if not old[field]: old[field] = m[field]
                    old['statistics'].update(m['statistics'])
                    old['sources'].append(provenance)
                else:
                    m.update(id=f'match:{len(self.matches)+1}', sources=[provenance])
                    fixtures[key] = m
                    self.matches.append(m)
        # Cup round numbering changes by year. Infer finals only where the last round has two legs.
        cup = defaultdict(list)
        for m in self.matches:
            if m['competition'] == 'Copa do Brasil' and m['round'].isdigit():
                cup[m['season']].append(m)
        for matches in cup.values():
            last = max(int(m['round']) for m in matches)
            final = [m for m in matches if int(m['round']) == last]
            if len(final) == 2 and len({t for m in final for t in (m['home_team'], m['away_team'])}) == 2:
                for m in final:
                    m['stage'] = 'final'
                    m['stage_inferred'] = True
        for m in self.matches:
            self.nodes[m['id']] = {'type': 'match', 'date': m['date']}
            for relation, ident, kind in [('HOME_TEAM', 'team:'+m['home_team'], 'team'),
                                          ('AWAY_TEAM', 'team:'+m['away_team'], 'team'),
                                          ('IN_COMPETITION', 'competition:'+m['competition'], 'competition'),
                                          ('IN_SEASON', 'season:'+str(m['season']), 'season')]:
                self.nodes.setdefault(ident, {'type': kind, 'name': ident.split(':', 1)[1]})
                self.edges[m['id']].append((relation, ident))
                self.edges[ident].append(('HAS_MATCH', m['id']))
        for p in self.players:
            ident = 'player:'+p['id']
            self.nodes[ident] = {'type': 'player', 'name': p['name']}
            if p['club']:
                club = 'team:'+p['club']
                self.nodes.setdefault(club, {'type': 'team', 'name': p['club']})
                self.edges[ident].append(('PLAYS_FOR_SNAPSHOT', club))
                self.edges[club].append(('HAS_PLAYER_SNAPSHOT', ident))

    @staticmethod
    def _match(filename, row):
        historical = filename.startswith('novo_')
        extended = filename.startswith('BR-')
        get = lambda a, b, c: row.get(c if historical else b if extended else a, '')
        raw_date = get('datetime', 'date', 'Data')
        day = None if fold(raw_date) in ('', 'na', 'nan') else date_value(raw_date)
        competition = {'Brasileirao_Matches.csv': 'Brasileirão', 'Brazilian_Cup_Matches.csv': 'Copa do Brasil',
                       'Libertadores_Matches.csv': 'Libertadores', 'novo_campeonato_brasileiro.csv': 'Brasileirão'}.get(filename)
        return dict(date=day, home_team=team_name(get('home_team', 'home', 'Equipe_mandante')),
                    away_team=team_name(get('away_team', 'away', 'Equipe_visitante')),
                    home_goal=number(get('home_goal', 'home_goal', 'Gols_mandante')),
                    away_goal=number(get('away_goal', 'away_goal', 'Gols_visitante')),
                    season=number(get('season', 'season', 'Ano')) or (int(day[:4]) if day else None),
                    competition=competition or competition_name(row['tournament']),
                    round=get('round', 'round', 'Rodada'), stage=row.get('stage', ''),
                    stadium=row.get('Arena', ''), statistics={k: v for k, v in row.items()
                    if extended and k not in ('home', 'away', 'date', 'tournament')})

    def _select(self, team=None, opponent=None, venue='either', competition=None, season=None,
                date_from=None, date_to=None, stage=None, source=None):
        if venue not in ('home', 'away', 'either'): raise ValueError('venue must be home, away or either')
        if opponent and not team: raise ValueError('opponent requires team')
        team, opponent = team_name(team) if team else None, team_name(opponent) if opponent else None
        competition = competition_name(competition) if competition else None
        start, end = date_value(date_from) if date_from else None, date_value(date_to) if date_to else None
        if start and end and start > end: raise ValueError('date_from must be <= date_to')
        if source and source not in self.sources: raise ValueError('Unknown source file')
        for m in self.matches:
            h, a = m['home_team'], m['away_team']
            if team and (team not in (h, a) or venue == 'home' and team != h or venue == 'away' and team != a): continue
            if opponent and not ((h == team and a == opponent) or (a == team and h == opponent)): continue
            if competition and m['competition'] != competition: continue
            if season is not None and m['season'] != season: continue
            if (start or end) and not m['date']: continue
            if start and m['date'] < start or end and m['date'] > end: continue
            if stage and fold(m['stage']) != fold(stage): continue
            if source and not any(s['file'] == source for s in m['sources']): continue
            yield m

    @staticmethod
    def _page(items, limit, offset):
        if type(limit) is not int or not 1 <= limit <= 500: raise ValueError('limit must be 1..500')
        if type(offset) is not int or offset < 0: raise ValueError('offset must be nonnegative')
        return dict(total=len(items), items=items[offset:offset+limit],
                    next_offset=offset+limit if offset+limit < len(items) else None)

    def search_matches(self, limit=50, offset=0, **filters):
        """Search all five match sources; newest first. Finals use stage='final'."""
        return self._page(sorted(self._select(**filters), key=lambda m: (m['date'] or '', m['id']), reverse=True), limit, offset)

    def team_statistics(self, team, **filters):
        """W/D/L, goals, points and win rate, optionally filtered by venue/season/competition."""
        stats, by_comp = record(), defaultdict(record)
        for m in self._select(team=team, **filters):
            if m['home_goal'] is None or m['away_goal'] is None: continue
            gf, ga = (m['home_goal'], m['away_goal']) if m['home_team'] == team_name(team) else (m['away_goal'], m['home_goal'])
            accumulate(stats, gf, ga)
            accumulate(by_comp[m['competition']], gf, ga)
        return dict(team=team_name(team), **finish(stats), by_competition={k: finish(v) for k,v in by_comp.items()})

    def head_to_head(self, team, opponent, **filters):
        """Results from team's perspective; matches are counted once across sources."""
        return dict(opponent=team_name(opponent), **self.team_statistics(team, opponent=opponent, **filters))

    def search_players(self, name=None, nationality=None, club=None, position=None, min_rating=0, limit=50, offset=0):
        """FIFA snapshot, not live rosters. Position accepts exact codes or forwards/midfielders/defenders/goalkeepers."""
        groups = {'forwards': 'ST CF LF RF LW RW LS RS', 'midfielders': 'CM CAM CDM LM RM LCM RCM LAM RAM LDM RDM',
                  'defenders': 'CB LB RB LWB RWB LCB RCB', 'goalkeepers': 'GK'}
        positions = groups.get(fold(position), position.upper()).split() if position else None
        rows = [p for p in self.players if (not name or fold(name) in fold(p['name']))
                and (not nationality or fold(nationality) == fold(p['nationality']))
                and (not club or team_name(club) == p['club']) and (not positions or p['position'] in positions)
                and (p['overall'] or 0) >= min_rating]
        rows.sort(key=lambda p: (-(p['overall'] or 0), p['name']))
        return dict(self._page(rows, limit, offset), note='Historical FIFA snapshot; club and age are not current.')

    def standings(self, competition, season, venue='either'):
        """Calculated table ordered by points, wins, goal difference, goals for. Not official tie-breaking."""
        table = defaultdict(record)
        matches = list(self._select(competition=competition, season=season))
        if venue not in ('home', 'away', 'either'): raise ValueError('Invalid venue')
        for m in matches:
            h, a = m['home_goal'], m['away_goal']
            if h is None or a is None: continue
            if venue != 'away': accumulate(table[m['home_team']], h, a)
            if venue != 'home': accumulate(table[m['away_team']], a, h)
        rows = [dict(team=k, **finish(v)) for k, v in table.items()]
        rows.sort(key=lambda r: (-r['points'], -r['wins'], -r['goal_difference'], -r['goals_for'], r['team']))
        for rank, row in enumerate(rows, 1): row['rank'] = rank
        complete = bool(rows) and venue == 'either' and competition_name(competition) == 'Brasileirão' and len(matches) == len(rows)*(len(rows)-1) and all(r['matches'] == 2*(len(rows)-1) for r in rows)
        return dict(competition=competition_name(competition), season=season, table=rows,
                    complete_double_round_robin=complete,
                    note='Calculated from available results; no disciplinary deductions or official tie-break adjudication. Cup tables do not determine champions; relegation is not inferred.')

    def analysis(self, team=None, competition=None, season=None, **filters):
        """Goal averages, home/away wins, biggest victories and season trends."""
        rows = [m for m in self._select(team=team, competition=competition, season=season, **filters)
                if m['home_goal'] is not None and m['away_goal'] is not None]
        def summary(ms):
            n = len(ms)
            return dict(matches=n, average_goals=round(sum(m['home_goal']+m['away_goal'] for m in ms)/n, 4) if n else None,
                        home_wins=sum(m['home_goal'] > m['away_goal'] for m in ms),
                        away_wins=sum(m['home_goal'] < m['away_goal'] for m in ms),
                        draws=sum(m['home_goal'] == m['away_goal'] for m in ms),
                        home_win_rate=round(100*sum(m['home_goal'] > m['away_goal'] for m in ms)/n, 2) if n else None)
        years = sorted({m['season'] for m in rows})
        return dict(**summary(rows), by_season={str(y): summary([m for m in rows if m['season']==y]) for y in years},
                    team_trends={str(y): self.team_statistics(team, season=y, competition=competition, **filters) for y in years} if team else {},
                    biggest_wins=sorted([m for m in rows if m['home_goal'] != m['away_goal']], key=lambda m: abs(m['home_goal']-m['away_goal']), reverse=True)[:20])

    def team_profile(self, team):
        """Cross-file team statistics, competitions, and FIFA snapshot players."""
        return dict(statistics=self.team_statistics(team), players=self.search_players(club=team),
                    competitions=sorted({m['competition'] for m in self._select(team=team)}))

    def competition_bracket(self, competition, season):
        """Available fixtures grouped by stage; no invented progression or penalty winners."""
        stages = defaultdict(list)
        for m in self._select(competition=competition, season=season):
            stages[m['stage'] or ('round '+m['round'] if m['round'] else 'unknown')].append(m)
        return dict(stages={k: sorted(v, key=lambda m: m['date'] or '') for k,v in stages.items()},
                    note='Stage-grouped fixtures; penalties, aggregate away-goal rules and progression are not available.')

    def derbies(self, season=None, limit=50, offset=0):
        """Curated traditional rivalries, not an exhaustive derby registry."""
        pairs = [('flamengo','fluminense'), ('corinthians','palmeiras'), ('santos','sao paulo'),
                 ('corinthians','sao paulo'), ('santos','palmeiras'), ('palmeiras','sao paulo'),
                 ('santos','corinthians'), ('gremio','internacional'), ('atletico-mg','cruzeiro'),
                 ('bahia','vitoria'), ('athletico-pr','coritiba'), ('sport','nautico'),
                 ('flamengo','vasco da gama'), ('botafogo','flamengo')]
        pairs = {frozenset(p) for p in pairs}
        return self._page(sorted([m for m in self._select(season=season) if frozenset((m['home_team'],m['away_team'])) in pairs], key=lambda m:m['date'] or '', reverse=True), limit, offset)

    def graph_neighbors(self, node_id, limit=50, offset=0):
        """Traverse typed graph edges; IDs: team:flamengo, player:158023, match:1, competition:Brasileirão."""
        edges = [dict(relation=r, target=t, node=self.nodes[t]) for r,t in self.edges.get(node_id, [])]
        return dict(node=self.nodes.get(node_id), **self._page(edges, limit, offset))

    def coverage(self):
        """Data provenance, coverage, import issues and limits. Individual scorers are unavailable."""
        return dict(sources=self.sources, unique_matches=len(self.matches), players=len(self.players),
                    nodes=len(self.nodes), edges=sum(map(len, self.edges.values())),
                    competitions={c: dict(matches=len(ms), first=min(m['date'] for m in ms if m['date']), last=max(m['date'] for m in ms if m['date']))
                    for c in sorted({m['competition'] for m in self.matches})
                    for ms in [[m for m in self.matches if m['competition']==c]]},
                    issues=self.issues, limitations=['No individual goal events: player top scorers cannot be inferred.',
                    'Historical snapshots only; missing seasons are not zero-match seasons.',
                    'Duplicate key: competition, date, canonical home and away team; matching-score cross-source fixtures within one day are merged for timezone differences. First source score wins conflicts; raw records retained.'])
