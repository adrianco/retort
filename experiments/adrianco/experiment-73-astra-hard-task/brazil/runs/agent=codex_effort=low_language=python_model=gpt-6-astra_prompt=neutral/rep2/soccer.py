"""Local Brazilian football knowledge graph and dataset queries (standard library only)."""
import csv
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c)).lower().strip()


ALIASES = {
    'ec bahia': 'bahia', 'ec juventude': 'juventude', 'fortaleza fc': 'fortaleza',
    'vasco da gama rj': 'vasco', 'sport recife': 'sport', 'santa cruz fc': 'santa cruz',
    'rb bragantino': 'bragantino', 'red bull bragantino': 'bragantino',
    'sport club corinthians paulista': 'corinthians', 'corinthians paulista': 'corinthians',
    'sao paulo fc': 'sao paulo', 'sao paulo futebol clube': 'sao paulo',
    'clube de regatas do flamengo': 'flamengo', 'sociedade esportiva palmeiras': 'palmeiras',
    'santos fc': 'santos', 'vasco da gama': 'vasco', 'cr vasco da gama': 'vasco',
    'atletico mineiro': 'atletico-mg', 'atletico mg': 'atletico-mg',
    'athletico-pr': 'athletico', 'atletico-pr': 'athletico', 'athletico paranaense': 'athletico',
    'atletico paranaense': 'athletico', 'atletico goianiense': 'atletico-go',
    'america mineiro': 'america-mg', 'america mg': 'america-mg',
    'gremio porto alegre': 'gremio', 'botafogo rj': 'botafogo',
}


def team_key(name):
    name = re.sub(r'\s*-\s*', '-', fold(name))
    if name in ALIASES:
        return ALIASES[name]
    # Preserve state-qualified ambiguous club names.
    if re.match(r'^(america|atletico|operario|botafogo)-(?!rj$)', name):
        return name
    name = re.sub(r'-(ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)$', '', name)
    return ALIASES.get(name, name)


def competition_key(name):
    name = fold(name)
    return {'serie a': 'Brasileirão', 'brasileirao': 'Brasileirão', 'brasileirao serie a': 'Brasileirão',
            'copa do brasil': 'Copa do Brasil', 'libertadores': 'Libertadores',
            'copa libertadores': 'Libertadores'}.get(name, name.title())


def date_key(value):
    value = value.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%Y %H:%M'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Invalid date: {value!r}')


def number(value):
    if value is None or fold(value) in ('', 'nan', 'na', 'none', '-'): return None
    n = float(value)
    if not n.is_integer() or n < 0: raise ValueError(f'Invalid nonnegative integer: {value}')
    return int(n)


class SoccerGraph:
    FILES = ('Brasileirao_Matches.csv', 'Brazilian_Cup_Matches.csv', 'Libertadores_Matches.csv',
             'BR-Football-Dataset.csv', 'novo_campeonato_brasileiro.csv', 'fifa_data.csv')

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / 'data/kaggle'
        self.matches, self.players, self.issues, self.counts = [], [], [], {}
        fixtures = {}
        for filename in self.FILES:
            with (self.data_dir / filename).open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.counts[filename] = len(rows)
            for line, row in enumerate(rows, 2):
                try:
                    if filename == 'fifa_data.csv':
                        self.players.append(dict(id=row['ID'], name=row['Name'], club=row['Club'],
                            team=team_key(row['Club']), nationality=row['Nationality'], position=row['Position'],
                            overall=number(row['Overall']), potential=number(row['Potential']), attributes=row))
                        continue
                    historical = filename.startswith('novo_')
                    extended = filename.startswith('BR-')
                    def get(regular, historic, ext): return row.get(historic if historical else ext if extended else regular, '')
                    competition = competition_key(row['tournament']) if extended else (
                        'Copa do Brasil' if filename.startswith('Brazilian_Cup') else
                        'Libertadores' if filename.startswith('Libertadores') else 'Brasileirão')
                    date = date_key(get('datetime', 'Data', 'date'))
                    home, away = get('home_team', 'Equipe_mandante', 'home'), get('away_team', 'Equipe_visitante', 'away')
                    hk, ak = team_key(home), team_key(away)
                    # Historical bare ambiguous names can be disambiguated with state columns.
                    if historical:
                        if hk in ('america', 'atletico', 'operario'): hk = team_key(home+'-'+row['Mandante_UF'])
                        if ak in ('america', 'atletico', 'operario'): ak = team_key(away+'-'+row['Visitante_UF'])
                    match = dict(date=date, home_team=hk, away_team=ak, competition=competition,
                        season=number(get('season','Ano','season')) or int(date[:4]),
                        home_goal=number(get('home_goal','Gols_mandante','home_goal')),
                        away_goal=number(get('away_goal','Gols_visitante','away_goal')),
                        round=get('round','Rodada','round'), stage=row.get('stage',''),
                        stadium=row.get('Arena',''), sources=[filename], source_rows={filename:row})
                    key = (date, hk, ak, competition)
                    # Reconcile adjacent-day cross-source timestamps only with equal scores.
                    if key not in fixtures:
                        for delta in (-1, 1):
                            alternate = ((datetime.fromisoformat(date)+timedelta(days=delta)).date().isoformat(), hk, ak, competition)
                            candidate = fixtures.get(alternate)
                            if candidate and filename not in candidate['sources'] and candidate['season']==match['season'] and (candidate['home_goal'], candidate['away_goal']) == (match['home_goal'], match['away_goal']):
                                key = alternate
                                break
                    if key in fixtures:
                        old = fixtures[key]
                        old['sources'].append(filename); old['source_rows'][filename] = row
                        for field in ('round', 'stage', 'stadium', 'home_goal', 'away_goal'):
                            if old[field] in ('', None): old[field] = match[field]
                        if (old['home_goal'], old['away_goal']) != (match['home_goal'], match['away_goal']):
                            self.issues.append(f'{filename}:{line}: conflicting score; retained first source for {key}')
                    else: fixtures[key] = match
                except (ValueError, KeyError) as exc:
                    self.issues.append(f'{filename}:{line}: {exc}')
        self.matches = sorted(fixtures.values(), key=lambda m: (m['date'], m['home_team']))
        self.teams = sorted({m[k] for m in self.matches for k in ('home_team', 'away_team')})

    def _matches(self, team=None, opponent=None, venue='either', competition=None, season=None,
                 date_from=None, date_to=None, stage=None, source=None, derbies=False):
        if venue not in ('home','away','either'): raise ValueError('venue must be home, away, or either')
        if opponent and not team: raise ValueError('opponent requires team')
        team = team_key(team) if team else None
        opponent = team_key(opponent) if opponent else None
        comp = competition_key(competition) if competition else None
        start, end = date_key(date_from) if date_from else '', date_key(date_to) if date_to else '9999'
        if start > end: raise ValueError('date_from must precede date_to')
        rivalry = [set(x) for x in [('flamengo','fluminense'),('palmeiras','corinthians'),('santos','sao paulo'),
                     ('gremio','internacional'),('atletico-mg','cruzeiro'),('vasco','flamengo'),('bahia','vitoria')]]
        result = []
        for m in self.matches:
            h,a = m['home_team'],m['away_team']
            if team and team not in ([h] if venue=='home' else [a] if venue=='away' else [h,a]): continue
            if opponent and {h,a} != {team,opponent}: continue
            if comp and m['competition'] != comp: continue
            if season is not None and m['season'] != int(season): continue
            if not start <= m['date'] <= end: continue
            if source and source not in m['sources']: continue
            if derbies and {h,a} not in rivalry: continue
            if stage:
                if fold(stage) == 'final' and m['competition']=='Copa do Brasil':
                    # Stage numbers vary by season; the highest observed round is the final.
                    rounds = [int(x['round']) for x in self.matches if x['competition']==m['competition'] and x['season']==m['season'] and str(x['round']).isdigit()]
                    if not rounds or m['round'] != str(max(rounds)): continue
                elif fold(stage) not in (fold(m['stage']), fold(m['round'])): continue
            result.append(m)
        return result

    @staticmethod
    def _page(rows, limit=50, offset=0):
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1 <= limit <= 500: raise ValueError('limit must be 1..500')
        if isinstance(offset,bool) or not isinstance(offset,int) or offset < 0: raise ValueError('offset must be nonnegative')
        return dict(total=len(rows), offset=offset, results=rows[offset:offset+limit])

    def search_matches(self, limit=50, offset=0, latest=False, **filters):
        rows = self._matches(**filters)
        return self._page(list(reversed(rows)) if latest else rows, limit, offset)

    def search_players(self, name=None, nationality=None, club=None, position=None, limit=50, offset=0):
        forwards = {'ST','CF','LF','RF','LW','RW','LS','RS'}
        rows = [p for p in self.players if (not name or fold(name) in fold(p['name']))
                and (not nationality or fold(nationality)==fold(p['nationality']))
                and (not club or team_key(club) in p['team'])
                and (not position or (p['position'] in forwards if fold(position) in ('forward','forwards') else p['position']==position.upper()))]
        return self._page(sorted(rows, key=lambda p: (-(p['overall'] or 0), p['name'])),limit,offset)

    def standings(self, **filters):
        records = {}
        for m in self._matches(**filters):
            if m['home_goal'] is None or m['away_goal'] is None: continue
            for team,gf,ga in [(m['home_team'],m['home_goal'],m['away_goal']), (m['away_team'],m['away_goal'],m['home_goal'])]:
                if filters.get('team') and team != team_key(filters['team']): continue
                if filters.get('venue')=='home' and team!=m['home_team']: continue
                if filters.get('venue')=='away' and team!=m['away_team']: continue
                r = records.setdefault(team,dict(team=team,played=0,wins=0,draws=0,losses=0,goals_for=0,goals_against=0,points=0))
                r['played']+=1; r['goals_for']+=gf; r['goals_against']+=ga
                r['wins']+=gf>ga; r['draws']+=gf==ga; r['losses']+=gf<ga
                r['points']+=3 if gf>ga else 1 if gf==ga else 0
        for r in records.values():
            r['goal_difference']=r['goals_for']-r['goals_against']; r['win_rate']=round(100*r['wins']/r['played'],2)
        rows=sorted(records.values(),key=lambda r:(-r['points'],-r['wins'],-r['goal_difference'],-r['goals_for'],r['team']))
        for rank,r in enumerate(rows,1): r['rank']=rank
        return dict(results=rows, note='Calculated from available results; points, wins, goal difference, goals, name. Not official standings; deductions, complete coverage and all tie-breakers are unavailable. Cup tables are aggregates, not champions or relegation decisions.')

    def team_info(self, team, **filters):
        matches=self._matches(team=team,**filters)
        return dict(team=team_key(team), record=self.standings(team=team,**filters)['results'],
                    competitions=sorted({m['competition'] for m in matches}),
                    players=self.search_players(club=team),
                    note='FIFA club membership is a historical snapshot, not the current roster.')

    def head_to_head(self, team, opponent, **filters):
        return dict(team=team_key(team), opponent=team_key(opponent),
                    record=self.standings(team=team,opponent=opponent,**filters)['results'],
                    matches=self.search_matches(team=team,opponent=opponent,**filters))

    def statistics(self, **filters):
        matches=self._matches(**filters)
        played=[m for m in matches if m['home_goal'] is not None and m['away_goal'] is not None]
        n=len(played)
        return dict(matches=len(matches), played=n, average_goals=round(sum(m['home_goal']+m['away_goal'] for m in played)/n,4) if n else None,
                    home_win_rate=round(100*sum(m['home_goal']>m['away_goal'] for m in played)/n,2) if n else None,
                    biggest_wins=sorted((m for m in played if m['home_goal']!=m['away_goal']),key=lambda m:-abs(m['home_goal']-m['away_goal']))[:10])

    def trends(self, team=None, competition=None):
        return {str(s):self.statistics(team=team,competition=competition,season=s) for s in sorted({m['season'] for m in self._matches(team=team,competition=competition)})}

    def bracket(self, competition, season):
        stages=defaultdict(list)
        for m in self._matches(competition=competition,season=season): stages[m['stage'] or m['round'] or 'unknown'].append(m)
        return dict(stages=dict(stages),note='Recorded fixtures grouped by stage/round. Advancement, penalties and missing legs cannot be inferred reliably.')

    def top_scorers(self):
        return dict(available=False,reason='The datasets contain team scores but no player goal events. Individual top scorers cannot be inferred from FIFA ratings.')

    def graph(self, team, limit=50):
        info=self.team_info(team)
        matches=self.search_matches(team=team,limit=limit,latest=True)
        node='team:'+team_key(team)
        edges=[dict(source='player:'+p['id'],relation='PLAYS_FOR_SNAPSHOT',target=node) for p in info['players']['results']]
        edges += [dict(source=node,relation='PARTICIPATED_IN',target='competition:'+c) for c in info['competitions']]
        nodes=[dict(id=node,type='team',name=team_key(team))]
        nodes += [dict(id='player:'+p['id'],type='player',name=p['name']) for p in info['players']['results']]
        nodes += [dict(id='competition:'+c,type='competition',name=c) for c in info['competitions']]
        for m in matches['results']:
            mid='match:'+':'.join([m['competition'],m['date'],m['home_team'],m['away_team']])
            nodes.append(dict(id=mid,type='match',data=m))
            for side in ('home','away'):
                tid='team:'+m[side+'_team']
                nodes.append(dict(id=tid,type='team',name=m[side+'_team']))
                edges.append(dict(source=tid,relation=side.upper()+'_TEAM',target=mid))
            edges.append(dict(source=mid,relation='IN_COMPETITION',target='competition:'+m['competition']))
        return dict(nodes=list({n['id']:n for n in nodes}.values()),edges=edges,total_matches=matches['total'])

    def coverage(self):
        return dict(source_rows=self.counts,unique_matches=len(self.matches),players=len(self.players),
                    issues=self.issues,dates=[self.matches[0]['date'],self.matches[-1]['date']] if self.matches else [],
                    note='Historical datasets only. Duplicate date/team/competition fixtures merge; first source takes precedence, raw rows retained. No live results.')
