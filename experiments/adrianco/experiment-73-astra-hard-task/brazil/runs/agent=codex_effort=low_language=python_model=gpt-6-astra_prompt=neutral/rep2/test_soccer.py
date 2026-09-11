import json
import subprocess
import sys
import time
import unittest
from soccer import SoccerGraph, team_key, date_key
from server import Server

# Executable examples: natural language is interpreted by the connected LLM.
EXAMPLES = [
 ('Show Flamengo versus Fluminense', 'search_matches',dict(team='Flamengo',opponent='Fluminense')),
 ('Palmeiras matches in 2023','search_matches',dict(team='Palmeiras',season=2023)),
 ('Copa do Brasil finals','search_matches',dict(competition='Copa do Brasil',stage='final')),
 ('Corinthians home record in 2022','team_info',dict(team='Corinthians',season=2022,venue='home')),
 ('Most goals in Serie A 2023','standings',dict(competition='Serie A',season=2023)),
 ('Compare Palmeiras and Santos','head_to_head',dict(team='Palmeiras',opponent='Santos')),
 ('Find Brazilian players','search_players',dict(nationality='Brazil')),
 ('Highest rated Flamengo players','search_players',dict(club='Flamengo')),
 ('Sao Paulo forwards','search_players',dict(club='São Paulo FC',position='forwards')),
 ('2019 league table','standings',dict(competition='Brasileirão',season=2019)),
 ('2018 Libertadores bracket','bracket',dict(competition='Libertadores',season=2018)),
 ('Average goals in Brasileirao','statistics',dict(competition='Brasileirão')),
 ('Best away record','standings',dict(venue='away')),
 ('Biggest wins','statistics',{}),
 ('Last Flamengo Corinthians game','search_matches',dict(team='Flamengo',opponent='Corinthians',latest=True,limit=1)),
 ('Who is Gabriel Barbosa','search_players',dict(name='Gabriel Barbosa')),
 ('Flamengo roster','search_players',dict(club='Flamengo')),
 ('Derbies in 2023','search_matches',dict(derbies=True,season=2023)),
 ('Palmeiras competitions','team_info',dict(team='Palmeiras')),
 ('Best home record','standings',dict(venue='home')),
 ('Top Brazilian players','search_players',dict(nationality='Brazil',limit=10)),
 ('Compare seasons','trends',dict(competition='Brasileirão')),
 ('Individual goal scorers','top_scorers',{}),
 ('Team relationships','graph',dict(team='Flamengo')),
]

class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.g=SoccerGraph();cls.server=Server(cls.g)

    def test_all_sources_loaded_and_queryable(self):
        self.assertEqual(list(self.g.counts.values()),[4180,1337,1255,10296,6886,18207])
        for source in self.g.FILES[:-1]: self.assertGreater(self.g.search_matches(source=source)['total'],0)
        self.assertEqual(len(self.g.players),18207)
        self.assertTrue(any('Invalid date' in x for x in self.g.issues))

    def test_normalization(self):
        for name in ['São Paulo-SP','Sao Paulo','São Paulo FC']: self.assertEqual(team_key(name),'sao paulo')
        self.assertEqual(team_key('Sport Club Corinthians Paulista'),'corinthians')
        self.assertNotEqual(team_key('America-MG'),team_key('America-RN'))
        self.assertEqual(date_key('29/03/2003'),'2003-03-29')
        with self.assertRaises(ValueError): date_key('bad')

    def test_match_filters_and_paging(self):
        args=dict(team='Flamengo-RJ',opponent='Fluminense',season=2023,date_from='01/01/2023',date_to='2023-12-31')
        rows=self.g.search_matches(**args)['results'];self.assertTrue(rows)
        for m in rows:
            self.assertEqual({m['home_team'],m['away_team']},{'flamengo','fluminense'})
            self.assertEqual(m['season'],2023)
        self.assertEqual(self.g.search_matches(**args,limit=1,offset=1)['results'],rows[1:2])
        self.assertEqual(self.g.search_matches(**args,limit=1,latest=True)['results'],rows[-1:])
        with self.assertRaises(ValueError): self.g.search_matches(limit=0)
        with self.assertRaises(ValueError): self.g.search_matches(date_from='2024-01-01',date_to='2023-01-01')

    def test_deduplicated_2019_results(self):
        table=self.g.standings(competition='Serie A',season=2019)['results']
        self.assertEqual(len(table),20)
        self.assertEqual(sum(r['played'] for r in table),760)
        self.assertEqual((table[0]['team'],table[0]['points'],table[0]['played']),('flamengo',90,38))
        for r in table:
            self.assertEqual(r['played'],r['wins']+r['draws']+r['losses'])
            self.assertEqual(r['points'],3*r['wins']+r['draws'])
        self.assertEqual(sum(r['goals_for'] for r in table),sum(r['goals_against'] for r in table))

    def test_home_away_and_h2h(self):
        whole=self.g.team_info('Corinthians',season=2022)['record'][0]
        home=self.g.team_info('Corinthians',season=2022,venue='home')['record'][0]
        away=self.g.team_info('Corinthians',season=2022,venue='away')['record'][0]
        self.assertEqual(whole['played'],home['played']+away['played'])
        a=self.g.head_to_head('Palmeiras','Santos')['record'][0]
        b=self.g.head_to_head('Santos','Palmeiras')['record'][0]
        self.assertEqual(a['wins'],b['losses']); self.assertEqual(a['goals_for'],b['goals_against'])

    def test_players_graph_empty(self):
        players=self.g.search_players(nationality='Brazil')['results']
        self.assertTrue(players);self.assertTrue(all(p['nationality']=='Brazil' for p in players))
        self.assertEqual(players,sorted(players,key=lambda p:(-p['overall'],p['name'])))
        graph=self.g.graph('Flamengo');ids={n['id'] for n in graph['nodes']}
        for edge in graph['edges']: self.assertIn(edge['source'],ids);self.assertIn(edge['target'],ids)
        self.assertIsNone(self.g.statistics(team='nonexistent')['average_goals'])
        self.assertFalse(self.g.top_scorers()['available'])

    def test_24_sample_questions_and_performance(self):
        for question,tool,args in EXAMPLES:
            with self.subTest(question=question):
                start=time.perf_counter()
                result=self.server.handle(dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name=tool,arguments=args)))
                self.assertFalse(result['result']['isError'])
                self.assertLess(time.perf_counter()-start,2 if tool.startswith('search') else 5)
                json.loads(result['result']['content'][0]['text'])

    def test_protocol_errors(self):
        self.assertIsNone(self.server.handle(dict(jsonrpc='2.0',method='notifications/initialized')))
        self.assertEqual(self.server.handle([])['error']['code'],-32600)
        for args in [dict(limit=-1),dict(limit=True),dict(unknown='x')]:
            r=self.server.handle(dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='search_matches',arguments=args)))
            self.assertTrue(r['result']['isError'])

    def test_stdio_integration(self):
        messages=[dict(jsonrpc='2.0',id=1,method='initialize',params={'protocolVersion':'2025-06-18'}),
                  dict(jsonrpc='2.0',method='notifications/initialized'),
                  dict(jsonrpc='2.0',id=2,method='tools/list'),
                  dict(jsonrpc='2.0',id=3,method='tools/call',params={'name':'coverage'})]
        proc=subprocess.run([sys.executable,'server.py'],input='\n'.join(map(json.dumps,messages))+'\n',text=True,capture_output=True,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr)
        replies=list(map(json.loads,proc.stdout.splitlines()))
        self.assertEqual(len(replies),3);self.assertEqual(len(replies[1]['result']['tools']),11)
        self.assertFalse(replies[2]['result']['isError'])

if __name__=='__main__': unittest.main()
