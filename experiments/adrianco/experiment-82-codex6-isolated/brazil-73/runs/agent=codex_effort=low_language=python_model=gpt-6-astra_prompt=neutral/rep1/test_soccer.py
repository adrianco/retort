"""Given the supplied data, when querying the graph, then results obey these contracts."""
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from soccer import SoccerGraph, team_name, date_value, FILES
from server import MCPServer, SCHEMAS


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = SoccerGraph()

    def test_all_six_sources_load_without_lost_rows(self):
        g = self.graph
        self.assertEqual(g.sources, dict(zip(FILES, [4180,1337,1255,10296,6886,18207])))
        counts = {}
        for m in g.matches:
            for s in m['sources']: counts[s['file']] = counts.get(s['file'],0)+1
        self.assertEqual(counts, {k:v for k,v in g.sources.items() if k!='fifa_data.csv'})
        for source in FILES[:-1]:
            self.assertGreater(g.search_matches(source=source)['total'],0)
        self.assertEqual(len(g.players),18207)

    def test_team_aliases_and_distinct_clubs(self):
        for a,b in [('Flamengo-RJ','Flamengo'), ('Sport Club Corinthians Paulista','Corinthians-SP'),
                    ('São Paulo FC','Sao Paulo-SP'), ('Grêmio-RS','Gremio'),
                    ('Atlético - PR','Athletico Paranaense - PR'), ('EC Bahia','Bahia-BA')]:
            self.assertEqual(team_name(a),team_name(b))
        self.assertNotEqual(team_name('América - MG'),team_name('América - RN'))
        self.assertNotEqual(team_name('Botafogo - PB'),team_name('Botafogo-RJ'))
        self.assertNotEqual(team_name('Atlético - MG'),team_name('Atlético - GO'))

    def test_dates(self):
        for value in ('2023-09-24','24/09/2023','2023-09-24 20:00:00'):
            self.assertEqual(date_value(value),'2023-09-24')
        with self.assertRaises(ValueError): date_value('31/02/2023')

    def test_find_derby_and_filters(self):
        result = self.graph.search_matches(team='Flamengo',opponent='Fluminense',season=2023,date_from='2023-01-01', date_to='2023-12-31')
        self.assertGreater(result['total'],0)
        for m in result['items']:
            self.assertEqual({m['home_team'],m['away_team']},{'flamengo','fluminense'})
            self.assertEqual(m['season'],2023)
            self.assertIn('home_goal',m)
        home = self.graph.search_matches(team='Corinthians',venue='home',season=2022,competition='Serie A')
        self.assertEqual(home['total'],19)
        self.assertTrue(all(m['home_team']=='corinthians' for m in home['items']))

    def test_standings_known_season_and_deduplication(self):
        result = self.graph.standings('Brasileirão',2019)
        self.assertTrue(result['complete_double_round_robin'])
        self.assertEqual(len(result['table']),20)
        leader = result['table'][0]
        for key,value in dict(team='flamengo',points=90,matches=38,wins=28,draws=6,losses=4,goals_for=86,goals_against=37).items():
            self.assertEqual(leader[key],value)
        self.assertEqual(sum(r['matches'] for r in result['table']),760)
        merged = self.graph.search_matches(team='Flamengo',opponent='Cruzeiro',venue='home',season=2019)['items']
        self.assertEqual(len(merged),1)
        self.assertEqual(len(merged[0]['sources']),3)
        self.assertGreater(len({s['raw'].get('date',s['raw'].get('datetime',s['raw'].get('Data'))) for s in merged[0]['sources']}),1)

    def test_stats_conservation_and_head_to_head(self):
        g=self.graph
        s=g.team_statistics('Palmeiras',season=2022)
        self.assertEqual(s['matches'],s['wins']+s['draws']+s['losses'])
        self.assertEqual(s['points'],3*s['wins']+s['draws'])
        a=g.head_to_head('Palmeiras','Santos'); b=g.head_to_head('Santos','Palmeiras')
        self.assertEqual(a['wins'],b['losses']); self.assertEqual(a['goals_for'],b['goals_against'])
        self.assertEqual(a['draws'],b['draws'])
        home=g.team_statistics('Palmeiras',season=2022,venue='home')
        away=g.team_statistics('Palmeiras',season=2022,venue='away')
        self.assertEqual(s['matches'],home['matches']+away['matches'])

    def test_finals_bracket_and_missing_results(self):
        finals=self.graph.search_matches(competition='Copa do Brasil',stage='final',season=2019)
        self.assertEqual(finals['total'],2)
        stages=self.graph.competition_bracket('Libertadores',2018)['stages']
        self.assertIn('final',stages)
        self.assertEqual(len(stages['final']),2)
        self.assertTrue(any(m['home_goal'] is None for m in self.graph.matches))
        self.assertTrue(any(m['date'] is None for m in self.graph.matches))
        self.assertTrue(all(i['error']=='Conflicting score' for i in self.graph.issues))

    def test_player_attributes_filters_and_snapshot(self):
        result=self.graph.search_players(nationality='Brazil',min_rating=85)
        self.assertGreater(result['total'],0)
        self.assertEqual(result['items'][0]['name'],'Neymar Jr')
        self.assertEqual(result['items'][0]['overall'],92)
        self.assertIn('Dribbling',result['items'][0]['attributes'])
        forwards=self.graph.search_players(club='São Paulo FC',position='forwards')['items']
        self.assertTrue(all(p['position'] in 'ST CF LF RF LW RW LS RS'.split() for p in forwards))
        self.assertEqual(self.graph.search_players(name='Neymar')['total'],1)

    def test_cross_file_and_graph_relationships(self):
        p=self.graph.team_profile('Flamengo')
        self.assertIn('Brasileirão',p['competitions'])
        self.assertGreater(p['statistics']['matches'],0)
        node=self.graph.graph_neighbors('team:flamengo',limit=500)
        self.assertEqual(node['node']['type'],'team')
        match=self.graph.graph_neighbors('match:1')
        self.assertEqual({e['relation'] for e in match['items']},{'HOME_TEAM','AWAY_TEAM','IN_COMPETITION','IN_SEASON'})
        player=self.graph.graph_neighbors('player:158023')
        self.assertEqual(player['items'][0]['relation'],'PLAYS_FOR_SNAPSHOT')

    def test_aggregations_and_empty_queries(self):
        r=self.graph.analysis(competition='Serie A',season=2019)
        self.assertEqual(r['matches'],380)
        self.assertEqual(r['matches'],r['home_wins']+r['away_wins']+r['draws'])
        self.assertGreater(r['average_goals'],2)
        self.assertEqual(self.graph.search_matches(team='Nonexistent')['total'],0)
        self.assertIsNone(self.graph.analysis(season=2099)['average_goals'])
        self.assertFalse(self.graph.standings('Serie A',2099)['complete_double_round_robin'])
        self.assertGreater(self.graph.derbies(season=2023)['total'],0)

    def test_pagination_and_invalid_inputs(self):
        a=self.graph.search_matches(limit=2); b=self.graph.search_matches(limit=2,offset=2)
        self.assertEqual(a['next_offset'],2)
        self.assertFalse({m['id'] for m in a['items']} & {m['id'] for m in b['items']})
        for args in ({'limit':0},{'offset':-1},{'venue':'bad'},{'opponent':'Santos'}, {'date_from':'2024-01-01','date_to':'2023-01-01'}):
            with self.assertRaises(ValueError): self.graph.search_matches(**args)

    def test_performance(self):
        start=time.perf_counter()
        self.graph.search_matches(team='Flamengo',opponent='Corinthians',limit=1)
        self.assertLess(time.perf_counter()-start,2)
        start=time.perf_counter()
        self.graph.analysis()
        self.assertLess(time.perf_counter()-start,5)

    def test_twenty_five_sample_questions(self):
        scenarios=json.loads(Path('sample_questions.json').read_text())
        self.assertGreaterEqual(len(scenarios),20)
        for scenario in scenarios:
            with self.subTest(question=scenario['question']):
                from server import validate
                validate(scenario['tool'],scenario['arguments'])
                answer=getattr(self.graph,scenario['tool'])(**scenario['arguments'])
                self.assertIsInstance(answer,dict)
                json.dumps(answer,allow_nan=False)


class ProtocolScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.graph=SoccerGraph()

    def test_handshake_discovery_errors_and_calls(self):
        server=MCPServer(self.graph)
        def send(method,params=None): return server.handle(dict(jsonrpc='2.0',id=1,method=method,params=params or {}))
        self.assertIn('error',send('tools/list'))
        r=send('initialize',dict(protocolVersion='2025-11-25',capabilities={},clientInfo={'name':'test','version':'1'}))
        self.assertIn('tools',r['result']['capabilities'])
        self.assertIsNone(server.handle(dict(jsonrpc='2.0',method='notifications/initialized')))
        self.assertEqual(len(send('tools/list')['result']['tools']),len(SCHEMAS))
        for args in ({'team':'Flamengo','season':'2023'},{'limit':True},{'extra':1}):
            self.assertTrue(send('tools/call',{'name':'search_matches','arguments':args})['result']['isError'])
        self.assertEqual(send('missing')['error']['code'],-32601)
        self.assertEqual(send('tools/call',{'name':'missing'})['error']['code'],-32602)
        r=send('tools/call',{'name':'team_statistics','arguments':{'team':'Flamengo','season':2019,'competition':'Serie A'}})
        self.assertEqual(json.loads(r['result']['content'][0]['text'])['points'],90)

    def test_real_stdio_process(self):
        messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'search_players','arguments':{'name':'Neymar'}}}]
        result=subprocess.run([sys.executable,'server.py'],input='invalid json\n'+'\n'.join(map(json.dumps,messages))+'\n',text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        responses=[json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses),3)
        self.assertEqual(responses[0]['error']['code'],-32700)
        self.assertEqual(json.loads(responses[2]['result']['content'][0]['text'])['total'],1)


if __name__=='__main__': unittest.main()
