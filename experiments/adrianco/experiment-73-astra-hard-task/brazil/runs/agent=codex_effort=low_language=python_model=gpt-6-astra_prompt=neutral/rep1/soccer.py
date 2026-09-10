"""Offline Brazilian soccer knowledge graph and read-only query service."""
from __future__ import annotations

import csv
import hashlib
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'data' / 'kaggle'
FILES = ('Brasileirao_Matches.csv', 'Brazilian_Cup_Matches.csv',
         'Libertadores_Matches.csv', 'novo_campeonato_brasileiro.csv',
         'BR-Football-Dataset.csv', 'fifa_data.csv')
STATES = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.lower().split()


def fold(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(value))
                            if not unicodedata.combining(c)).casefold().split())


ALIASES = {
    'sport club corinthians paulista': 'corinthians', 'corinthians paulista': 'corinthians',
    'clube de regatas do flamengo': 'flamengo', 'cr flamengo': 'flamengo',
    'sociedade esportiva palmeiras': 'palmeiras', 'sao paulo fc': 'sao paulo',
    'sao paulo futebol clube': 'sao paulo', 'santos fc': 'santos',
    'gremio foot ball porto alegrense': 'gremio', 'gremio fbpa': 'gremio',
    'sport club internacional': 'internacional', 'sc internacional': 'internacional',
    'vasco': 'vasco da gama', 'vasco da gama': 'vasco da gama',
    'cr vasco da gama': 'vasco da gama', 'clube de regatas vasco da gama': 'vasco da gama',
    'atletico mineiro': 'atletico-mg', 'clube atletico mineiro': 'atletico-mg',
    'atletico mg': 'atletico-mg', 'atletico pr': 'athletico-pr',
    'atletico-pr': 'athletico-pr', 'athletico': 'athletico-pr',
    'athletico pr': 'athletico-pr', 'athletico paranaense': 'athletico-pr',
    'atletico paranaense': 'athletico-pr', 'atletico goianiense': 'atletico-go',
    'atletico go': 'atletico-go', 'america mineiro': 'america-mg',
    'america mg': 'america-mg', 'america rn': 'america-rn',
    'bragantino': 'red bull bragantino', 'rb bragantino': 'red bull bragantino',
    'sport recife': 'sport', 'sport club do recife': 'sport',
    'nautico capibaribe': 'nautico', 'botafogo rj': 'botafogo',
    'botafogo fr': 'botafogo', 'botafogo pb': 'botafogo-pb',
    'botafogo sp': 'botafogo-sp', 'boa esporte': 'boa',
    'boavista sport club (antigo esporte clube barreira)': 'boavista',
    'a.b.c.': 'abc', 'a.s.a.': 'asa', 'c.r.b.': 'crb', 'c. r. b.': 'crb',
    'c.s.a.': 'csa', 'c.r.a.c.': 'crac', 'brasil de pelotas': 'brasil',
}
ALIASES.update({'ec bahia': 'bahia', 'ec juventude': 'juventude', 'fortaleza fc': 'fortaleza',
                'fortaleza ec': 'fortaleza', 'santa cruz fc': 'santa cruz', 'vasco da gama rj': 'vasco da gama',
                'botafogo-rj': 'botafogo', 'bahia-bh': 'bahia', 'ec vitoria': 'vitoria',
                'gremio rs': 'gremio', 'internacional rs': 'internacional', 'guarani sp': 'guarani',
                'fluminense rj': 'fluminense', 'bragantino pa': 'bragantino-pa'})
DISPLAY = {'sao paulo': 'São Paulo', 'gremio': 'Grêmio', 'avai': 'Avaí',
           'atletico-mg': 'Atlético-MG', 'athletico-pr': 'Athletico-PR',
           'atletico-go': 'Atlético-GO', 'america-mg': 'América-MG',
           'america-rn': 'América-RN', 'ceara': 'Ceará', 'goias': 'Goiás',
           'vitoria': 'Vitória', 'cuiaba': 'Cuiabá', 'criciuma': 'Criciúma',
           'nautico': 'Náutico', 'parana': 'Paraná', 'abc': 'ABC', 'crb': 'CRB', 'csa': 'CSA'}


def team_key(name):
    key = fold(name)
    match = re.search(r'\s*-\s*(' + '|'.join(STATES) + r')$', key)
    if match:
        state, base = match.group(1), key[:match.start()].strip()
        # Homonymous clubs must not be merged across states.
        if base in ('atletico', 'america'):
            key = base + '-' + state
        elif (base == 'botafogo' and state != 'rj') or (base == 'bragantino' and state != 'sp'):
            key = base + '-' + state
        else:
            key = base
    return ALIASES.get(key, key)


def team_name(name):
    key = team_key(name)
    return DISPLAY.get(key, key.title())


def competition_name(value):
    key = fold(value)
    if key in ('brasileirao', 'brasileirao serie a', 'serie a', 'campeonato brasileiro', 'brazil serie a'):
        return 'Brasileirão'
    if key in ('libertadores', 'copa libertadores', 'copa libertadores da america'):
        return 'Libertadores'
    if key in ('copa do brasil', 'brazilian cup'):
        return 'Copa do Brasil'
    return str(value).strip()


def parse_date(value):
    value = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Invalid date: {value!r}; use YYYY-MM-DD or DD/MM/YYYY')


def number(value):
    if value is None or fold(value) in ('', 'nan', 'na', 'n/a', 'null', 'none', '-'):
        return None
    n = float(value)
    if not math.isfinite(n):
        return None
    return int(n) if n.is_integer() else n


def page(items, limit=50, offset=0):
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('limit must be an integer between 1 and 500')
    if type(offset) is not int or offset < 0:
        raise ValueError('offset must be a nonnegative integer')
    return {'total': len(items), 'offset': offset, 'limit': limit,
            'items': items[offset:offset + limit],
            'next_offset': offset + limit if offset + limit < len(items) else None}


class SoccerGraph:
    """Load six sources once. Match IDs link teams, competitions and source rows.

    Duplicate identity is competition, calendar date and ordered team pair;
    identical-score cross-source records within one day also merge.
    The first source wins conflicting results; all raw evidence is retained.
    """

    def __init__(self, data_dir=DATA_DIR):
        self.matches = []
        self.players = []
        self.sources = {}
        self.issues = []
        self.teams = {}
        index = {}
        for filename in FILES:
            path = Path(data_dir) / filename
            with path.open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.sources[filename] = {'rows': len(rows), 'loaded': 0, 'rejected': 0}
            for line, row in enumerate(rows, 2):
                try:
                    if filename == 'fifa_data.csv':
                        self._player(row, filename, line)
                    else:
                        item = self._match(row, filename, line)
                        key = (item['competition'], item['date'], item['home_team'], item['away_team'])
                        old = index.get(key)
                        # Cross-source midnight timezone shifts: merge only the same
                        # ordered pair and score within one day, never same-source games.
                        if old is None and item['date']:
                            for delta in (-1, 1):
                                nearby = (datetime.fromisoformat(item['date']) + timedelta(days=delta)).date().isoformat()
                                candidate = index.get((item['competition'], nearby, item['home_team'], item['away_team']))
                                if (candidate and not any(s['file'] == filename for s in candidate['sources'])
                                        and (candidate['home_goal'], candidate['away_goal']) == (item['home_goal'], item['away_goal'])):
                                    old = candidate
                                    break
                        if old:
                            if (old['home_goal'], old['away_goal']) != (item['home_goal'], item['away_goal']):
                                if old['home_goal'] is None or old['away_goal'] is None:
                                    old['home_goal'], old['away_goal'] = item['home_goal'], item['away_goal']
                                else:
                                    self.issues.append({'source': filename, 'line': line, 'reason': 'Conflicting score', 'match_id': old['id']})
                            old['sources'].extend(item['sources'])
                            old['statistics'].update(item['statistics'])
                            for field in ('round', 'stage', 'stadium'):
                                if not old.get(field):
                                    old[field] = item.get(field)
                        else:
                            index[key] = item
                            self.matches.append(item)
                    self.sources[filename]['loaded'] += 1
                except (ValueError, KeyError) as exc:
                    self.sources[filename]['rejected'] += 1
                    self.issues.append({'source': filename, 'line': line, 'reason': str(exc)})
        self.matches.sort(key=lambda m: (m['date'] or '', m['id']), reverse=True)
        self.by_team = defaultdict(list)
        self.by_id = {}
        for m in self.matches:
            self.by_id[m['id']] = m
            for side in ('home_team', 'away_team'):
                self.by_team[team_key(m[side])].append(m)
        self._cup_stages()

    def _register(self, name):
        if not str(name).strip():
            raise ValueError('Missing team name')
        key = team_key(name)
        self.teams.setdefault(key, {'id': 'team:' + key, 'name': team_name(name), 'aliases': set()})['aliases'].add(name)
        return self.teams[key]['name']

    def _player(self, row, filename, line):
        self.players.append({'id': 'player:' + row['ID'], 'name': row['Name'],
                             'age': number(row['Age']), 'nationality': row['Nationality'],
                             'overall': number(row['Overall']), 'potential': number(row['Potential']),
                             'club': self._register(row['Club']) if row['Club'].strip() else None,
                             'position': row['Position'], 'attributes': {k: v for k, v in row.items() if k},
                             'source': {'file': filename, 'line': line}})

    def _match(self, r, filename, line):
        stats = {}
        stadium = None
        stage = r.get('stage')
        rnd = r.get('round')
        if filename == 'novo_campeonato_brasileiro.csv':
            date, season, home, away = r['Data'], r['Ano'], r['Equipe_mandante'], r['Equipe_visitante']
            # State data disambiguates América and Atlético.
            home += '-' + r['Mandante_UF'] if r['Mandante_UF'] and not re.search(r'-[A-Za-z]{2}$', home) else ''
            away += '-' + r['Visitante_UF'] if r['Visitante_UF'] and not re.search(r'-[A-Za-z]{2}$', away) else ''
            hg, ag, rnd, stadium = r['Gols_mandante'], r['Gols_visitante'], r['Rodada'], r['Arena']
            comp = 'Brasileirão'
        elif filename == 'BR-Football-Dataset.csv':
            date, home, away, hg, ag = r['date'], r['home'], r['away'], r['home_goal'], r['away_goal']
            season = parse_date(date)[:4]
            comp = competition_name(r['tournament'])
            stats = {k: number(r[k]) for k in ('home_corner', 'away_corner', 'home_attack', 'away_attack', 'home_shots', 'away_shots', 'total_corners')}
            stats.update({k: r[k] for k in ('ht_result', 'at_result', 'time')})
        else:
            date, season, home, away = r['datetime'], r['season'], r['home_team'], r['away_team']
            hg, ag = r['home_goal'], r['away_goal']
            comp = {'Brasileirao_Matches.csv': 'Brasileirão', 'Brazilian_Cup_Matches.csv': 'Copa do Brasil',
                    'Libertadores_Matches.csv': 'Libertadores'}[filename]
        date = None if fold(date) in ('na', '', 'nan') else parse_date(date)
        hg, ag = number(hg), number(ag)
        if any(x is not None and (not isinstance(x, int) or x < 0) for x in (hg, ag)):
            raise ValueError('Goals must be nonnegative integers or missing')
        home, away = self._register(home), self._register(away)
        identity = '|'.join((comp, date or 'unknown', home, away))
        return {'id': 'match:' + hashlib.sha256(identity.encode()).hexdigest()[:20],
                'date': date, 'season': int(season) if number(season) is not None else None, 'competition': comp, 'home_team': home,
                'away_team': away, 'home_goal': hg, 'away_goal': ag, 'round': rnd,
                'stage': stage, 'stadium': stadium, 'statistics': stats,
                'sources': [{'file': filename, 'line': line, 'raw': r}]}

    def _cup_stages(self):
        # Dataset round codes include preliminary ties in 2013–15; 2021 is incomplete.
        for m in self.matches:
            if m['competition'] == 'Copa do Brasil' and m['round'] and not m['stage']:
                final_round = 6 if m['season'] == 2012 else 7 if m['season'] == 2016 or m['season'] >= 2021 else 8
                try:
                    distance = final_round - int(m['round'])
                except ValueError:
                    continue
                m['stage'] = {0: 'final', 1: 'semifinals', 2: 'quarterfinals', 3: 'round of 16'}.get(distance, 'early round')

    @staticmethod
    def _public(m):
        return {**m, 'sources': [{k: v for k, v in s.items() if k != 'raw'} for s in m['sources']]}

    def _select(self, team=None, opponent=None, venue='either', competition=None, season=None,
                date_from=None, date_to=None, stage=None, source=None):
        if venue not in ('home', 'away', 'either'):
            raise ValueError('venue must be home, away, or either')
        if opponent and not team:
            raise ValueError('opponent requires team')
        if season is not None and (type(season) is not int or not 1800 <= season <= 2200):
            raise ValueError('season must be an integer year')
        start, end = parse_date(date_from) if date_from else None, parse_date(date_to) if date_to else None
        if start and end and start > end:
            raise ValueError('date_from must not exceed date_to')
        if source and source not in FILES[:-1]:
            raise ValueError('Unknown match source')
        tk, ok = team_key(team) if team else None, team_key(opponent) if opponent else None
        comp = competition_name(competition) if competition else None
        candidates = self.by_team.get(tk, []) if tk else self.matches
        result = []
        for m in candidates:
            hk, ak = team_key(m['home_team']), team_key(m['away_team'])
            if tk and ((venue == 'home' and hk != tk) or (venue == 'away' and ak != tk)):
                continue
            if ok and not ((hk == tk and ak == ok) or (ak == tk and hk == ok)):
                continue
            if comp and fold(m['competition']) != fold(comp) or season is not None and m['season'] != season:
                continue
            if (start or end) and m['date'] is None:
                continue
            if start and m['date'] < start or end and m['date'] > end:
                continue
            if stage and fold(m['stage'] or '') != fold(stage):
                continue
            if source and not any(s['file'] == source for s in m['sources']):
                continue
            result.append(m)
        return result

    def search_matches(self, team=None, opponent=None, venue='either', competition=None, season=None,
                       date_from=None, date_to=None, stage=None, source=None, limit=50, offset=0):
        """Find results/schedules, newest first. Dates are inclusive. Use opponent for head-to-head; stage='final' for cup finals. Paginate to retrieve all results."""
        matches = self._select(team, opponent, venue, competition, season, date_from, date_to, stage, source)
        result = page(matches, limit, offset)
        result['items'] = [self._public(m) for m in result['items']]
        return result

    def get_match(self, match_id):
        """Get one match including original source rows, extended statistics and provenance."""
        if match_id not in self.by_id:
            raise ValueError('Unknown match_id')
        return self.by_id[match_id]

    @staticmethod
    def _record(matches, team):
        result = dict(matches=0, played=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0, points=0)
        for m in matches:
            result['matches'] += 1
            if m['home_goal'] is None or m['away_goal'] is None:
                continue
            gf, ga = (m['home_goal'], m['away_goal']) if team_key(m['home_team']) == team_key(team) else (m['away_goal'], m['home_goal'])
            result['played'] += 1
            result['goals_for'] += gf
            result['goals_against'] += ga
            result['wins' if gf > ga else 'draws' if gf == ga else 'losses'] += 1
        result['points'] = result['wins'] * 3 + result['draws']
        result['goal_difference'] = result['goals_for'] - result['goals_against']
        result['win_rate'] = round(100 * result['wins'] / result['played'], 2) if result['played'] else 0.0
        return result

    def team_statistics(self, team, competition=None, season=None, venue='either'):
        """Win/draw/loss, goals and home/away splits; includes competition breakdown and historical FIFA club players."""
        matches = self._select(team=team, competition=competition, season=season, venue=venue)
        comps = sorted({m['competition'] for m in matches})
        return {'team': team_name(team), 'season': season, 'venue': venue, **self._record(matches, team),
                'by_competition': {c: self._record([m for m in matches if m['competition'] == c], team) for c in comps},
                'home': self._record([m for m in matches if team_key(m['home_team']) == team_key(team)], team),
                'away': self._record([m for m in matches if team_key(m['away_team']) == team_key(team)], team),
                'players': self.search_players(club=team, limit=50),
                'note': 'Records reflect deduplicated dataset matches; FIFA club membership is a historical snapshot, not a current roster.'}

    def head_to_head(self, team, opponent, competition=None, season=None):
        """Compare both teams across both home/away orientations, with latest result."""
        if team_key(team) == team_key(opponent):
            raise ValueError('Choose two different teams')
        matches = self._select(team=team, opponent=opponent, competition=competition, season=season)
        return {'team': team_name(team), 'opponent': team_name(opponent),
                'team_record': self._record(matches, team), 'opponent_record': self._record(matches, opponent),
                'latest_match': self._public(matches[0]) if matches else None}

    def search_players(self, name=None, nationality=None, club=None, position=None, min_overall=None, limit=50, offset=0):
        """Search FIFA snapshot by name substring, nationality, club or position; sorted by overall. 'forward' includes ST/CF/LW/RW/LF/RF/LS/RS. Raw attributes are included. No real-life goal scorer data."""
        if min_overall is not None and (type(min_overall) is not int or not 0 <= min_overall <= 100):
            raise ValueError('min_overall must be between 0 and 100')
        positions = {'forward': {'ST', 'CF', 'LW', 'RW', 'LF', 'RF', 'LS', 'RS'},
                     'midfielder': {'CAM', 'CM', 'CDM', 'LM', 'RM', 'LCM', 'RCM', 'LDM', 'RDM', 'LAM', 'RAM'},
                     'defender': {'CB', 'LB', 'RB', 'LCB', 'RCB', 'LWB', 'RWB'}, 'goalkeeper': {'GK'}}
        pos = positions.get(fold(position).rstrip('s'), {position.upper()}) if position else None
        nation = 'brazil' if nationality and fold(nationality) in ('brazilian', 'brasileiro', 'brasil') else fold(nationality or '')
        items = [p for p in self.players if
                 (not name or fold(name) in fold(p['name'])) and
                 (not nationality or nation == fold(p['nationality'])) and
                 (not club or team_key(club) in team_key(p['club'] or '')) and
                 (not pos or p['position'] in pos) and
                 (min_overall is None or p['overall'] is not None and p['overall'] >= min_overall)]
        items.sort(key=lambda p: (-(p['overall'] or 0), p['name'], p['id']))
        return {**page(items, limit, offset), 'note': 'Historical FIFA snapshot; ratings are not match performance or current roster data.'}

    def standings(self, competition, season, venue='either'):
        """Calculate league tables (3 points/win), sorted points, wins, GD, goals. Cup tables are not league standings. No official deductions or unobserved tie-breaks are inferred."""
        comp = competition_name(competition)
        if comp in ('Copa do Brasil', 'Libertadores'):
            raise ValueError('Knockout competitions do not have an overall league table; use competition_bracket')
        matches = self._select(competition=comp, season=season, venue=venue)
        teams = sorted({m[s] for m in matches for s in ('home_team', 'away_team')})
        rows = []
        for team in teams:
            selected = [m for m in matches if (venue != 'away' and m['home_team'] == team) or (venue != 'home' and m['away_team'] == team)]
            rows.append({'team': team, **self._record(selected, team)})
        rows.sort(key=lambda r: (-r['points'], -r['wins'], -r['goal_difference'], -r['goals_for'], r['team']))
        for rank, row in enumerate(rows, 1):
            row['rank'] = rank
        expected = len(teams) * (len(teams) - 1)
        complete = comp == 'Brasileirão' and venue == 'either' and len(teams) in (20, 22, 24) and len(matches) == expected and all(r['played'] == 2 * (len(teams) - 1) for r in rows) and len({(m['home_team'], m['away_team']) for m in matches}) == expected
        return {'competition': comp, 'season': season, 'table': rows, 'complete_round_robin': complete,
                'calculated_leader': rows[0]['team'] if rows else None,
                'relegation_candidates': [r['team'] for r in rows[-4:]] if complete and season >= 2006 else [],
                'note': 'Calculated from dataset results, not official standings. Ties beyond goals scored use alphabetical order. Deductions, disciplinary tie-breaks and historical relegation rules are not modeled.'}

    def competition_bracket(self, competition, season):
        """Group observed cup matches by stage and two-team ties. Aggregate goals do not prove advancement (penalties/away-goal rules absent)."""
        matches = self._select(competition=competition, season=season)
        stages = defaultdict(lambda: defaultdict(list))
        for m in matches:
            stages[m['stage'] or 'unknown stage'][' vs '.join(sorted((m['home_team'], m['away_team'])))].append(m)
        output = {}
        for stage, ties in stages.items():
            output[stage] = []
            for pair, legs in sorted(ties.items()):
                totals = Counter()
                for m in legs:
                    if m['home_goal'] is not None and m['away_goal'] is not None:
                        totals[m['home_team']] += m['home_goal']
                        totals[m['away_team']] += m['away_goal']
                output[stage].append({'pair': pair, 'aggregate_goals': dict(totals), 'matches': [self._public(m) for m in sorted(legs, key=lambda m: m['date'] or '')]})
        return {'competition': competition_name(competition), 'season': season, 'stages': output,
                'note': 'Observed stage/tie results only. Missing stages, penalties and advancement are not inferred. Numeric Copa do Brasil stages use the season format.'}

    def statistics(self, competition=None, season=None, team=None, limit=10):
        """Goals/game, home wins, biggest victories, and team rankings by goals and home/away win rate."""
        matches = self._select(team=team, competition=competition, season=season)
        played = [m for m in matches if m['home_goal'] is not None and m['away_goal'] is not None]
        goals = sum(m['home_goal'] + m['away_goal'] for m in played)
        biggest = sorted([m for m in played if m['home_goal'] != m['away_goal']], key=lambda m: (-abs(m['home_goal'] - m['away_goal']), m['date'] or ''))
        teams = sorted({m[s] for m in played for s in ('home_team', 'away_team')})
        ranked = {}
        for venue in ('either', 'home', 'away'):
            rows = []
            for t in teams:
                ms = [m for m in played if (venue != 'away' and m['home_team'] == t) or (venue != 'home' and m['away_team'] == t)]
                if ms:
                    rows.append({'team': t, **self._record(ms, t)})
            rows.sort(key=lambda r: (-(r['goals_for'] if venue == 'either' else r['win_rate']), -r['points'], r['team']))
            ranked[venue] = page(rows, limit)['items']
        return {'matches': len(matches), 'played': len(played), 'total_goals': goals,
                'goals_per_match': round(goals / len(played), 4) if played else None,
                'home_win_rate': round(100 * sum(m['home_goal'] > m['away_goal'] for m in played) / len(played), 2) if played else None,
                'biggest_victories': [self._public(m) for m in page(biggest, limit)['items']],
                'rankings': ranked, 'note': 'Home/away rankings use win percentage; sample sizes are included. Individual top scorers cannot be inferred from team scores.'}

    def season_trends(self, competition, seasons, team=None):
        """Compare goals/game and results across selected seasons, optionally for one team."""
        if not isinstance(seasons, list) or not 1 <= len(seasons) <= 30:
            raise ValueError('seasons must contain 1 to 30 years')
        return {'seasons': [{'season': year, **(self.team_statistics(team, competition, year) if team else self.statistics(competition, year))} for year in seasons]}

    def derbies(self, season=None, competition=None, limit=50, offset=0):
        """Find a curated set of traditional rivalries; not an exhaustive derby taxonomy."""
        pairs = [('Flamengo', 'Fluminense'), ('Flamengo', 'Vasco'), ('Fluminense', 'Vasco'),
                 ('Botafogo', 'Flamengo'), ('Botafogo', 'Fluminense'), ('Botafogo', 'Vasco'),
                 ('Corinthians', 'Palmeiras'), ('Santos', 'São Paulo'), ('Corinthians', 'São Paulo'),
                 ('Corinthians', 'Santos'), ('Palmeiras', 'Santos'), ('Palmeiras', 'São Paulo'),
                 ('Grêmio', 'Internacional'), ('Cruzeiro', 'Atlético-MG'), ('Athletico-PR', 'Coritiba'),
                 ('Bahia', 'Vitória'), ('Ceará', 'Fortaleza'), ('Sport', 'Náutico'), ('Sport', 'Santa Cruz')]
        keys = {frozenset(map(team_key, pair)) for pair in pairs}
        items = [self._public(m) for m in self._select(season=season, competition=competition)
                 if frozenset((team_key(m['home_team']), team_key(m['away_team']))) in keys]
        return {**page(items, limit, offset), 'note': 'Curated traditional rivalries; dataset coverage only.'}

    def competitions(self, team=None):
        """List observed competitions, seasons and counts, optionally for a team."""
        matches = self._select(team=team)
        return {'competitions': [{'name': c, 'seasons': sorted({m['season'] for m in matches if m['competition'] == c and m['season'] is not None}),
                                   'matches': sum(m['competition'] == c for m in matches)} for c in sorted({m['competition'] for m in matches})]}

    def graph_neighbors(self, team, limit=50, offset=0):
        """Knowledge graph: team --PLAYED_HOME/AWAY--> match --IN_COMPETITION--> competition; player --PLAYS_FOR_SNAPSHOT--> team."""
        key = team_key(team)
        if key not in self.teams:
            return {'nodes': [], 'edges': [], 'total': 0, 'next_offset': None}
        root = {'id': 'team:' + key, 'type': 'team', 'name': self.teams[key]['name'], 'aliases': sorted(self.teams[key]['aliases'])}
        relations = []
        for m in self.by_team.get(key, []):
            relations.append(({'id': m['id'], 'type': 'match', **self._public(m)}, {'source': root['id'], 'relation': 'PLAYED_HOME' if team_key(m['home_team']) == key else 'PLAYED_AWAY', 'target': m['id']}))
        for p in self.players:
            if p['club'] and team_key(p['club']) == key:
                relations.append(({'id': p['id'], 'type': 'player', 'name': p['name']}, {'source': p['id'], 'relation': 'PLAYS_FOR_SNAPSHOT', 'target': root['id']}))
        result = page(relations, limit, offset)
        nodes, edges = {root['id']: root}, []
        for node, edge in result.pop('items'):
            nodes[node['id']] = node
            edges.append(edge)
            if node['type'] == 'match':
                cid = 'competition:' + node['competition']
                nodes[cid] = {'id': cid, 'type': 'competition', 'name': node['competition']}
                edges.append({'source': node['id'], 'relation': 'IN_COMPETITION', 'target': cid})
                for side in ('home_team', 'away_team'):
                    tid = 'team:' + team_key(node[side])
                    nodes.setdefault(tid, {'id': tid, 'type': 'team', 'name': node[side]})
                    if tid != root['id']:
                        edges.append({'source': tid, 'relation': 'PLAYED_HOME' if side == 'home_team' else 'PLAYED_AWAY', 'target': node['id']})
        return {**result, 'nodes': list(nodes.values()), 'edges': edges}

    def data_status(self):
        """Report all six files, rejected records, deduplication, conflicts and temporal coverage."""
        return {'sources': self.sources, 'unique_matches': len(self.matches), 'players': len(self.players),
                'teams': len(self.teams), 'date_from': min((m['date'] for m in self.matches if m['date']), default=None),
                'date_to': max((m['date'] for m in self.matches if m['date']), default=None), 'issues': self.issues,
                'limitations': ['Offline datasets only; no live scores.', 'FIFA snapshot is not a current roster.',
                                'No individual goal events, penalties or official points deductions.',
                                'Deduplicated by competition/date/home/away; identical-score cross-source matches within one day also merge. Earlier source wins conflicts.']}
