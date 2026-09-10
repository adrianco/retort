"""Offline Brazilian soccer knowledge graph and source-backed query engine."""
from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, date as date_type, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'data' / 'kaggle'
SOURCES = {
    'Brasileirao_Matches.csv': ('Brasileirão Série A', 'CC BY 4.0', 'https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro'),
    'Brazilian_Cup_Matches.csv': ('Copa do Brasil', 'CC BY 4.0', 'https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro'),
    'Libertadores_Matches.csv': ('Copa Libertadores', 'CC BY 4.0', 'https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro'),
    'BR-Football-Dataset.csv': ('', 'CC0', 'https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches'),
    'novo_campeonato_brasileiro.csv': ('Brasileirão Série A', 'CC BY 4.0', 'https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019'),
    'fifa_data.csv': ('', 'Apache 2.0', 'https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data'),
}


def folded(value: str) -> str:
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                            if not unicodedata.combining(c)).split())


# State is retained for names shared by different clubs. Bare common names select
# the nationally known club; e.g. Botafogo-PB never becomes Botafogo-RJ.
CLUBS = {
    'Palmeiras': ('SP', ['sociedade esportiva palmeiras']),
    'Flamengo': ('RJ', ['clube de regatas do flamengo']),
    'Fluminense': ('RJ', ['fluminense football club']),
    'Corinthians': ('SP', ['sport club corinthians paulista']),
    'São Paulo': ('SP', ['sao paulo fc', 'sao paulo futebol clube']),
    'Santos': ('SP', ['santos fc', 'santos futebol clube']),
    'Vasco da Gama': ('RJ', ['vasco', 'cr vasco da gama', 'club de regatas vasco da gama']),
    'Botafogo': ('RJ', ['botafogo de futebol e regatas']),
    'Grêmio': ('RS', ['gremio foot-ball porto alegrense']),
    'Internacional': ('RS', ['sport club internacional']),
    'Atlético-MG': ('MG', ['atletico', 'atletico mineiro', 'clube atletico mineiro']),
    'Athletico-PR': ('PR', ['atletico-pr', 'atletico paranaense', 'athletico paranaense', 'athletico']),
    'Atlético-GO': ('GO', ['atletico-go', 'atletico goianiense']),
    'América-MG': ('MG', ['america', 'america mineiro']),
    'Cruzeiro': ('MG', ['cruzeiro esporte clube']),
    'Red Bull Bragantino': ('SP', ['bragantino', 'rb bragantino']),
    'Sport': ('PE', ['sport recife', 'sport club do recife']),
    'Náutico': ('PE', ['nautico']), 'Vitória': ('BA', ['vitoria']),
    'Goiás': ('GO', ['goias']), 'Avaí': ('SC', ['avai']),
    'Criciúma': ('SC', ['criciuma']), 'Ceará': ('CE', ['ceara']),
    'Cuiabá': ('MT', ['cuiaba']), 'Paraná': ('PR', ['parana']),
    'Guarani': ('SP', []), 'Juventude': ('RS', []), 'Bahia': ('BA', []),
    'Fortaleza': ('CE', ['fortaleza esporte clube']), 'Coritiba': ('PR', []),
    'Chapecoense': ('SC', []), 'Figueirense': ('SC', []),
    'Portuguesa': ('SP', []), 'Ponte Preta': ('SP', []),
    'Santa Cruz': ('PE', []), 'Joinville': ('SC', []),
    'CSA': ('AL', ['csa', 'c.s.a.']), 'CRB': ('AL', ['c.r.b.', 'c. r. b.']),
    'ABC': ('RN', ['a.b.c.']), 'ASA': ('AL', ['a.s.a.']),
    'Boavista': ('RJ', ['boavista sport club (antigo esporte clube barreira)']),
}
ALIASES = {}
for _club, (_state, _aliases) in CLUBS.items():
    for _name in [_club, *_aliases]:
        ALIASES[folded(_name)] = _club
        ALIASES[f'{folded(_name)}-{_state.lower()}'] = _club
# These bare names need their suffix to select a different Atlético.
ALIASES.update({'atletico-pr': 'Athletico-PR', 'atletico-go': 'Atlético-GO'})
ALIASES.update({'america mg': 'América-MG', 'botafogo rj': 'Botafogo',
                'vasco da gama rj': 'Vasco da Gama', 'ec bahia': 'Bahia',
                'ec juventude': 'Juventude', 'fortaleza fc': 'Fortaleza',
                'santa cruz fc': 'Santa Cruz', 'america fc (minas gerais)': 'América-MG',
                'ceara sporting club': 'Ceará'})
STATES = 'ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to'.split()


def team_name(value: str) -> str:
    value = ' '.join(value.strip().split())
    key = folded(value)
    key = re.sub(r'\s*-\s*', '-', key)
    suffix = re.search(r'-(' + '|'.join(STATES) + r')$', key)
    if suffix:
        base, state = key[:suffix.start()], suffix.group(1).upper()
        candidate = ALIASES.get(key) or ALIASES.get(base)
        if candidate and CLUBS[candidate][0] == state:
            return candidate
        # Canonical accents/case are stored by the graph on first ingestion.
        return f'{base.title()}-{state}'
    return ALIASES.get(key, value)


def team_key(value: str) -> str:
    return folded(team_name(value))


def competition_name(value: str) -> str:
    key = folded(value)
    if key in {'serie a', 'brasileirao', 'brasileirao serie a', 'campeonato brasileiro', 'brasileirao serie a matches'}:
        return 'Brasileirão Série A'
    if key in {'libertadores', 'copa libertadores'}:
        return 'Copa Libertadores'
    if key in {'copa do brasil', 'brazilian cup'}:
        return 'Copa do Brasil'
    if key in {'serie b', 'serie c'}:
        return 'Brasileirão Série ' + key[-1].upper()
    return value.strip()


def parse_date(value: str) -> str:
    value = value.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Invalid date: {value!r}; use YYYY-MM-DD or DD/MM/YYYY')


def integer(value):
    if value is None or str(value).strip().lower() in {'', 'nan', 'na', 'null', 'none', '-'}:
        return None
    n = float(value)
    if not n.is_integer() or n < 0:
        raise ValueError(f'Expected nonnegative integer, got {value!r}')
    return int(n)


RIVALRIES = [('Flamengo', 'Fluminense'), ('Flamengo', 'Vasco da Gama'),
             ('Fluminense', 'Botafogo'), ('Flamengo', 'Botafogo'),
             ('Vasco da Gama', 'Fluminense'), ('Vasco da Gama', 'Botafogo'),
             ('Corinthians', 'Palmeiras'), ('Corinthians', 'São Paulo'),
             ('Santos', 'São Paulo'), ('Palmeiras', 'São Paulo'), ('Santos', 'Palmeiras'),
             ('Santos', 'Corinthians'), ('Grêmio', 'Internacional'),
             ('Atlético-MG', 'Cruzeiro'), ('Athletico-PR', 'Coritiba'),
             ('Bahia', 'Vitória'), ('Sport', 'Náutico'), ('Sport', 'Santa Cruz'),
             ('Náutico', 'Santa Cruz'), ('Ceará', 'Fortaleza'), ('Avaí', 'Figueirense')]
DERBIES = {frozenset(map(team_key, pair)) for pair in RIVALRIES}


class SoccerGraph:
    """In-memory entity graph. Each match holds normalized entity IDs and all sources.

    First source wins a conflicting score; the conflict and original row remain
    queryable. Same-day/competition/home/away records merge, never reversed legs.
    """

    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        self._matches = []
        self._players = []
        self.teams = {}
        self.nodes = {}
        self.edges = defaultdict(list)
        self.sources = {}
        self.errors = []
        unique = {}
        for filename, (competition, license_, url) in SOURCES.items():
            path = self.data_dir / filename
            if not path.is_file():
                raise FileNotFoundError(f'Required dataset missing: {path}')
            count = 0
            with path.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                for line, row in enumerate(reader, 2):
                    count += 1
                    try:
                        if filename == 'fifa_data.csv':
                            self._load_player(row, filename, line)
                            continue
                        m = self._load_match(row, filename, competition)
                        key = (m['date'] or f'undated:{filename}:{line}', m['competition'], m['home_id'], m['away_id'])
                        record = {'file': filename, 'line': line, 'raw': row}
                        # The extended feed records some late kickoffs on the next
                        # calendar day. Merge only an unambiguous cross-source
                        # neighbor with identical scores/season and orientation.
                        if key not in unique and m['date'] and m['home_goal'] is not None and m['away_goal'] is not None:
                            candidates = []
                            for delta in (-1, 1):
                                day = (date_type.fromisoformat(m['date']) + timedelta(days=delta)).isoformat()
                                adjacent = (day, *key[1:])
                                old = unique.get(adjacent)
                                if old and (old['season'] == m['season'] or old['season_inferred'] or m['season_inferred']) and all(old[s] == m[s] for s in ('home_goal', 'away_goal')) and not any(s['file'] == filename for s in old['sources']):
                                    candidates.append(adjacent)
                            if len(candidates) == 1:
                                key = candidates[0]
                                record['date_note'] = 'Adjacent-day cross-source match with identical teams, competition and scores; explicit season takes precedence over calendar year.'
                        if key in unique:
                            old = unique[key]
                            if old['season_inferred'] and not m['season_inferred']:
                                old['season'] = m['season']
                                old['season_inferred'] = False
                            scores = ('home_goal', 'away_goal')
                            if any(old[s] is not None and m[s] is not None and old[s] != m[s] for s in scores):
                                old['conflicts'].append({'file': filename, 'home_goal': m['home_goal'], 'away_goal': m['away_goal']})
                            for s in (*scores, 'round', 'stage', 'stadium'):
                                if old[s] is None:
                                    old[s] = m[s]
                            old['statistics'].update({filename: m['statistics'][filename]} if filename in m['statistics'] else {})
                            old['sources'].append(record)
                        else:
                            m.update(id='match:' + hashlib.sha256('|'.join(key).encode()).hexdigest()[:20],
                                     sources=[record], conflicts=[])
                            unique[key] = m
                    except (ValueError, KeyError, TypeError) as exc:
                        self.errors.append({'file': filename, 'line': line, 'error': str(exc)})
            self.sources[filename] = {'rows': count, 'license': license_, 'url': url}
        self._matches = sorted(unique.values(), key=lambda m: (m['date'] or '', m['id']), reverse=True)
        self._infer_cup_stages()
        for m in self._matches:
            self.nodes[m['id']] = {'id': m['id'], 'type': 'match', 'date': m['date']}
            cid = 'competition:' + folded(m['competition'])
            self.nodes[cid] = {'id': cid, 'type': 'competition', 'name': m['competition']}
            sid = f'{cid}:{m["season"]}'
            self.nodes[sid] = {'id': sid, 'type': 'season', 'season': m['season']}
            self._edge(m['id'], cid, 'IN_COMPETITION')
            self._edge(m['id'], sid, 'IN_SEASON')
            self._edge(sid, cid, 'SEASON_OF')
            self._edge(m['id'], m['home_id'], 'HOME_TEAM')
            self._edge(m['id'], m['away_id'], 'AWAY_TEAM')
        for p in self._players:
            self.nodes[p['id']] = {'id': p['id'], 'type': 'player', 'name': p['name']}
            if p['club_id']:
                self._edge(p['id'], p['club_id'], 'PLAYS_FOR_SNAPSHOT')

    def _edge(self, source, target, relation):
        edge = {'source': source, 'target': target, 'relation': relation}
        # Season links repeat across matches; store each relationship once.
        if relation == 'SEASON_OF' and edge in self.edges[source]:
            return
        self.edges[source].append(edge)
        self.edges[target].append(edge)

    def _team(self, name):
        if not name or not name.strip():
            raise ValueError('Team name is empty')
        key = 'team:' + team_key(name)
        if key not in self.teams:
            self.teams[key] = team_name(name)
            self.nodes[key] = {'id': key, 'type': 'team', 'name': self.teams[key]}
        return key

    def _load_match(self, r, filename, competition):
        if filename == 'novo_campeonato_brasileiro.csv':
            home, away = r['Equipe_mandante'], r['Equipe_visitante']
            # This source labels Bahia as BH and Vitória as ES in Série A.
            # Correct only this adapter; Vitória-ES remains a separate cup club.
            home_state, away_state = r.get('Mandante_UF'), r.get('Visitante_UF')
            if folded(home) == 'bahia' and home_state == 'BH' or folded(home) == 'vitoria' and home_state == 'ES':
                home_state = 'BA'
            if folded(away) == 'bahia' and away_state == 'BH' or folded(away) == 'vitoria' and away_state == 'ES':
                away_state = 'BA'
            home += '-' + home_state if home_state else ''
            away += '-' + away_state if away_state else ''
            date, season, round_ = r['Data'], r['Ano'], r['Rodada']
            hg, ag = r['Gols_mandante'], r['Gols_visitante']
        elif filename == 'BR-Football-Dataset.csv':
            home, away, date = r['home'], r['away'], r['date']
            season, round_ = parse_date(date)[:4], None
            hg, ag, competition = r['home_goal'], r['away_goal'], competition_name(r['tournament'])
        else:
            home, away, date = r['home_team'], r['away_team'], r['datetime']
            hg, ag, season, round_ = r['home_goal'], r['away_goal'], r['season'], r.get('round')
        home_id, away_id = self._team(home), self._team(away)
        stats = {filename: {k: v for k, v in r.items() if any(x in k for x in ('corner', 'attack', 'shots', 'result', 'diff'))}} if filename == 'BR-Football-Dataset.csv' else {}
        parsed_date = None if date.strip().lower() in {'na', 'nan', '', '-'} else parse_date(date)
        return dict(date=parsed_date, datetime=date, season=integer(season),
                    season_inferred=filename == 'BR-Football-Dataset.csv',
                    competition=competition_name(competition), home_team=self.teams[home_id],
                    away_team=self.teams[away_id], home_id=home_id, away_id=away_id,
                    home_goal=integer(hg), away_goal=integer(ag), round=round_ or None,
                    stage=r.get('stage') or None, stadium=r.get('Arena') or None, statistics=stats)

    def _load_player(self, r, filename, line):
        if not r.get('ID') or not r.get('Name'):
            raise ValueError('Player ID and Name are required')
        cid = self._team(r['Club']) if r.get('Club') else None
        self._players.append(dict(id='player:' + r['ID'], name=r['Name'], age=integer(r['Age']),
                                  nationality=r['Nationality'], overall=integer(r['Overall']),
                                  potential=integer(r['Potential']), club=self.teams[cid] if cid else None,
                                  club_id=cid, position=r.get('Position') or None,
                                  attributes={k: v for k, v in r.items() if k},
                                  source={'file': filename, 'line': line},
                                  note='Historical FIFA snapshot; club and ratings are not current.'))

    def _infer_cup_stages(self):
        # Round numbering changes by year. Only label the latest numbered round
        # as an inferred final when it contains exactly two teams and 1–2 legs.
        grouped = defaultdict(list)
        for m in self._matches:
            if m['competition'] == 'Copa do Brasil' and m['round'] and str(m['round']).isdigit():
                grouped[m['season']].append(m)
        for rows in grouped.values():
            last = max(int(m['round']) for m in rows)
            finals = [m for m in rows if int(m['round']) == last]
            if len(finals) in (1, 2) and len({m[k] for m in finals for k in ('home_id', 'away_id')}) == 2:
                for m in finals:
                    m['stage'] = 'final'
                    m['stage_note'] = 'Inferred from highest numbered round and two remaining teams; not an official bracket.'

    def _select(self, team=None, opponent=None, venue='either', competition=None,
                season=None, start_date=None, end_date=None, stage=None, source=None,
                derbies=False):
        if venue not in ('home', 'away', 'either'):
            raise ValueError('venue must be home, away, or either')
        if venue != 'either' and not team:
            raise ValueError('A home/away venue filter requires team')
        if opponent and not team:
            raise ValueError('opponent requires team')
        if source and source not in SOURCES:
            raise ValueError('Unknown source file')
        start = parse_date(start_date) if start_date else None
        end = parse_date(end_date) if end_date else None
        if start and end and start > end:
            raise ValueError('start_date must be on or before end_date')
        tid = 'team:' + team_key(team) if team else None
        oid = 'team:' + team_key(opponent) if opponent else None
        if tid and tid == oid:
            raise ValueError('Head-to-head needs two different teams')
        comp = folded(competition_name(competition)) if competition else None
        season = integer(season) if season is not None else None
        for m in self._matches:
            if tid and ((venue == 'home' and m['home_id'] != tid) or
                        (venue == 'away' and m['away_id'] != tid) or
                        (venue == 'either' and tid not in (m['home_id'], m['away_id']))):
                continue
            if oid and oid not in (m['home_id'], m['away_id']):
                continue
            if comp and folded(m['competition']) != comp or season is not None and m['season'] != season:
                continue
            if (start or end) and m['date'] is None:
                continue
            if start and m['date'] < start or end and m['date'] > end:
                continue
            if stage and folded(m['stage'] or '') != folded(stage) and folded(str(m['round'] or '')) != folded(stage):
                continue
            if source and not any(s['file'] == source for s in m['sources']):
                continue
            if derbies and frozenset((m['home_id'][5:], m['away_id'][5:])) not in DERBIES:
                continue
            yield m

    @staticmethod
    def _page(rows, limit, offset):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('limit must be an integer between 1 and 1000')
        if type(offset) is not int or offset < 0:
            raise ValueError('offset must be a nonnegative integer')
        return {'total': len(rows), 'offset': offset, 'limit': limit,
                'items': rows[offset:offset + limit],
                'next_offset': offset + limit if offset + limit < len(rows) else None}

    @staticmethod
    def _public(m):
        return {**{k: v for k, v in m.items() if k != 'sources'},
                'sources': [{k: s[k] for k in ('file', 'line')} for s in m['sources']]}

    def matches(self, filters: dict | None = None, limit: int = 50, offset: int = 0) -> dict:
        """Find results/schedules, latest first. filters: team, opponent, venue (home/away/either), competition, season, start_date, end_date, stage, source, derbies. Dates inclusive. Use stage=final (not semifinals)."""
        return self._page([self._public(m) for m in self._select(**(filters or {}))], limit, offset)

    @staticmethod
    def _record(rows, tid):
        wins = draws = losses = gf = ga = unplayed = 0
        for m in rows:
            if m['home_goal'] is None or m['away_goal'] is None:
                unplayed += 1
                continue
            a, b = (m['home_goal'], m['away_goal']) if m['home_id'] == tid else (m['away_goal'], m['home_goal'])
            gf += a
            ga += b
            wins += a > b
            draws += a == b
            losses += a < b
        n = wins + draws + losses
        return dict(matches=n, scheduled=unplayed, wins=wins, draws=draws, losses=losses,
                    goals_for=gf, goals_against=ga, goal_difference=gf-ga, points=wins*3+draws,
                    win_rate=round(100*wins/n, 2) if n else 0.0)

    def team_stats(self, team: str, filters: dict | None = None) -> dict:
        """Win/draw/loss, goals and home/away/competition splits from deduplicated dataset matches."""
        f = {**(filters or {}), 'team': team}
        rows = list(self._select(**f))
        tid = 'team:' + team_key(team)
        return dict(team=self.teams.get(tid, team_name(team)), **self._record(rows, tid),
                    by_venue={v: self._record([m for m in rows if m[v+'_id'] == tid], tid) for v in ('home', 'away')},
                    by_competition={c: self._record([m for m in rows if m['competition'] == c], tid) for c in sorted({m['competition'] for m in rows})},
                    note='Calculated from available matches; no official deductions or disciplinary tie-breakers.')

    def head_to_head(self, team: str, opponent: str, filters: dict | None = None, limit: int = 50) -> dict:
        """Compare two teams in either orientation, including latest result and full aggregate record."""
        f = {**(filters or {}), 'team': team, 'opponent': opponent}
        rows = list(self._select(**f))
        return dict(team=team_name(team), opponent=team_name(opponent),
                    record=self._record(rows, 'team:' + team_key(team)),
                    matches=self.matches(f, limit), latest=self._public(rows[0]) if rows else None)

    def players(self, name: str = '', nationality: str = '', club: str = '', position: str = '',
                min_rating: int = 0, limit: int = 50, offset: int = 0) -> dict:
        """Search historical FIFA players; sort by overall descending. position supports forward, midfielder, defender, goalkeeper or exact FIFA codes. Full source attributes returned."""
        groups = {'forward': {'ST', 'CF', 'LF', 'RF', 'LW', 'RW', 'LS', 'RS'},
                  'midfielder': {'CAM', 'CM', 'CDM', 'LM', 'RM', 'LAM', 'RAM', 'LCM', 'RCM', 'LDM', 'RDM'},
                  'defender': {'CB', 'LB', 'RB', 'LWB', 'RWB', 'LCB', 'RCB'}, 'goalkeeper': {'GK'}}
        positions = groups.get(position.lower().rstrip('s'), {position.upper()})
        nat = 'brazil' if folded(nationality) in {'brazilian', 'brasileiro', 'brasileira'} else folded(nationality)
        if type(min_rating) is not int or not 0 <= min_rating <= 100:
            raise ValueError('min_rating must be an integer between 0 and 100')
        club_id = 'team:' + team_key(club) if club else None
        rows = [p for p in self._players if
                (not name or folded(name) in folded(p['name'])) and
                (not nat or folded(p['nationality']) == nat) and
                (not club or p['club_id'] == club_id or (club_id not in self.teams and folded(club) in folded(p['club'] or ''))) and
                (not position or p['position'] in positions) and (p['overall'] or 0) >= min_rating]
        rows.sort(key=lambda p: (-(p['overall'] or 0), folded(p['name']), p['id']))
        return {**self._page(rows, limit, offset), 'note': 'FIFA historical snapshot, not live rosters. No match-level scorer data.'}

    def standings(self, competition: str, season: int, venue: str = 'either', source: str = '') -> dict:
        """Calculate league table: points, wins, goal difference, goals for. Does not assert official champions/relegation from potentially incomplete data."""
        comp = competition_name(competition)
        if comp not in {'Brasileirão Série A', 'Brasileirão Série B', 'Brasileirão Série C'}:
            raise ValueError('Knockout competitions do not have a single league table; use competition_info')
        if comp == 'Brasileirão Série C':
            raise ValueError('Série C includes groups/phases not identified in this data; use analysis')
        if venue not in ('home', 'away', 'either'):
            raise ValueError('venue must be home, away, or either')
        rows = list(self._select(competition=comp, season=season, source=source or None))
        teams = sorted({m[k] for m in rows for k in ('home_id', 'away_id')})
        table = []
        for tid in teams:
            games = [m for m in rows if tid in (m['home_id'], m['away_id']) and
                     (venue == 'either' or m[venue+'_id'] == tid)]
            table.append({'team': self.teams[tid], **self._record(games, tid)})
        table.sort(key=lambda t: (-t['points'], -t['wins'], -t['goal_difference'], -t['goals_for'], folded(t['team'])))
        for rank, row in enumerate(table, 1):
            row['rank'] = rank
        played = sum(m['home_goal'] is not None and m['away_goal'] is not None for m in rows)
        pair_counts = Counter((m['home_id'], m['away_id']) for m in rows if m['home_goal'] is not None and m['away_goal'] is not None)
        complete = len(teams) > 1 and all(pair_counts[a, b] == 1 for a in teams for b in teams if a != b)
        return dict(competition=comp, season=season, venue=venue, source=source or 'all', table=table, played_matches=played,
                    complete_double_round_robin=complete,
                    dataset_leader=table[0]['team'] if table else None,
                    note='Calculated dataset standings only. Official sanctions and full tie-breakers unavailable; no automatic champion/relegation claims.')

    def analysis(self, filters: dict | None = None, limit: int = 10) -> dict:
        """Goals averages, home/away win rates, biggest wins and team performance rankings; use season filters for trends."""
        rows = list(self._select(**(filters or {})))
        played = [m for m in rows if m['home_goal'] is not None and m['away_goal'] is not None]
        n = len(played)
        teams = {m[k] for m in rows for k in ('home_id', 'away_id')}
        ranking = []
        for tid in teams:
            games = [m for m in rows if tid in (m['home_id'], m['away_id'])]
            ranking.append({'team': self.teams[tid], **self._record(games, tid),
                            'home': self._record([m for m in games if m['home_id'] == tid], tid),
                            'away': self._record([m for m in games if m['away_id'] == tid], tid)})
        ranking.sort(key=lambda t: (-t['goals_for'], t['team']))
        biggest = sorted([m for m in played if m['home_goal'] != m['away_goal']],
                         key=lambda m: (-abs(m['home_goal']-m['away_goal']), m['date'] or '', m['id']))
        self._page([], limit, 0)
        return dict(matches=n, scheduled=len(rows)-n,
                    average_goals=round(sum(m['home_goal']+m['away_goal'] for m in played)/n, 4) if n else 0,
                    home_win_rate=round(100*sum(m['home_goal']>m['away_goal'] for m in played)/n, 2) if n else 0,
                    away_win_rate=round(100*sum(m['away_goal']>m['home_goal'] for m in played)/n, 2) if n else 0,
                    draws=sum(m['home_goal']==m['away_goal'] for m in played),
                    biggest_wins=[self._public(m) for m in biggest[:limit]],
                    teams_by_goals=ranking[:limit],
                    best_home=sorted(ranking, key=lambda t: (-t['home']['win_rate'], -t['home']['matches'], t['team']))[:limit],
                    best_away=sorted(ranking, key=lambda t: (-t['away']['win_rate'], -t['away']['matches'], t['team']))[:limit],
                    note='Ranks include sample sizes; small samples may have high win rates.')

    def compare_seasons(self, seasons: list[int], competition: str = 'Brasileirão Série A', team: str = '') -> dict:
        """Compare goal averages and team records across up to 20 seasons."""
        if not isinstance(seasons, list) or not 1 <= len(seasons) <= 20 or any(type(s) is not int for s in seasons):
            raise ValueError('seasons must contain 1 to 20 integers')
        return {'seasons': {str(s): (self.team_stats(team, {'season': s, 'competition': competition}) if team
                            else self.analysis({'season': s, 'competition': competition}, 5)) for s in seasons}}

    def team_info(self, team: str, season: int | None = None) -> dict:
        """Cross-file team profile: competitions, match record, and FIFA roster (separate historical snapshot)."""
        filters = {'season': season} if season is not None else {}
        stats = self.team_stats(team, filters)
        return {'team': stats['team'], 'stats': stats, 'competitions': list(stats['by_competition']),
                'players': self.players(club=team), 'recent_matches': self.matches({**filters, 'team': team}, 10)}

    def competition_info(self, competition: str, season: int) -> dict:
        """Season results grouped by recorded stage, including cup final inference. Bracket advancement and individual scorers unavailable."""
        rows = list(self._select(competition=competition, season=season))
        groups = defaultdict(list)
        for m in rows:
            groups[m['stage'] or ('round ' + str(m['round']) if m['round'] else 'unknown stage')].append(self._public(m))
        return dict(competition=competition_name(competition), season=season, matches=len(rows), stages=dict(groups),
                    top_scorers=None, bracket_advancement=None,
                    note='No individual goal events, penalty shootouts or reliable progression links. Stage-grouped results are not a verified bracket; inferred finals are marked.')

    def graph(self, entity: str, limit: int = 50, offset: int = 0) -> dict:
        """Explore graph neighbors by entity ID or team name. Edges link matches, teams, competition seasons and FIFA player snapshots."""
        eid = entity if entity in self.nodes else 'team:' + team_key(entity)
        if eid not in self.nodes:
            return {'node': None, 'edges': self._page([], limit, offset), 'neighbors': []}
        page = self._page(self.edges[eid], limit, offset)
        neighbors = {e['target'] if e['source'] == eid else e['source'] for e in page['items']}
        return {'node': self.nodes[eid], 'edges': page, 'neighbors': [self.nodes[n] for n in sorted(neighbors)]}

    def match_detail(self, match_id: str) -> dict:
        """Return a match and all original source rows, extended stats, provenance and score conflicts."""
        for m in self._matches:
            if m['id'] == match_id:
                return m
        raise ValueError('Unknown match_id')

    def coverage(self) -> dict:
        """Report dataset coverage, licenses, rejected rows and deduplication diagnostics."""
        comps = defaultdict(list)
        for m in self._matches:
            comps[m['competition']].append(m)
        return dict(sources=self.sources, matches=len(self._matches), players=len(self._players), teams=len(self.teams),
                    duplicates_merged=sum(len(m['sources'])-1 for m in self._matches),
                    score_conflicts=sum(bool(m['conflicts']) for m in self._matches), rejected_rows=self.errors,
                    competitions={c: {'matches': len(ms), 'seasons': sorted({m['season'] for m in ms if m['season'] is not None}),
                                       'first_date': min((m['date'] for m in ms if m['date']), default=None),
                                       'last_date': max((m['date'] for m in ms if m['date']), default=None)} for c, ms in comps.items()},
                    note='Offline historical dataset. Missing results are not evidence that a match never happened.')
