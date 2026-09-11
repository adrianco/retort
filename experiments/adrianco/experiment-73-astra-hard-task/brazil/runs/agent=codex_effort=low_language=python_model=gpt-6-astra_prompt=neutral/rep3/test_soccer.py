import json
import subprocess
import sys
import time
import unittest
from collections import defaultdict
from soccer import SoccerGraph, FILES, team_name, date_value, number
from server import MCPServer, TOOLS

# Executable natural-language examples: an attached LLM translates to these calls.
EXAMPLES = [
 ('Show Flamengo vs Fluminense matches','search_matches',{'team':'Flamengo','opponent':'Fluminense'}),
 ('What did Palmeiras play in 2023?','search_matches',{'team':'Palmeiras','season':2023}),
 ('Find Libertadores finals','search_matches',{'competition':'Libertadores','stage':'final'}),
 ('Corinthians home record in 2022','team_statistics',{'team':'Corinthians','season':2022,'venue':'home'}),
 ('Most goals in Serie A 2023','standings',{'competition':'Serie A','season':2023}),
 ('Compare Palmeiras and Santos','head_to_head',{'team':'Palmeiras','opponent':'Santos'}),
 ('All Brazilian players','search_players',{'nationality':'Brazil'}),
 ('Highest rated Flamengo players','search_players',{'club':'Flamengo'}),
 ('São Paulo forwards','search_players',{'club':'São Paulo FC','position':'forward'}),
 ('2019 Brasileirão calculated leader','standings',{'competition':'Brasileirão','season':2019}),
 ('2018 Libertadores bracket fixtures','competition_results',{'competition':'Libertadores','season':2018}),
 ('2020 bottom league places','standings',{'competition':'Brasileirão','season':2020}),
 ('Average Brasileirão goals','analysis',{'competition':'Brasileirão'}),
 ('Best away record','standings',{'competition':'Brasileirão','season':2022,'venue':'away'}),
 ('Biggest wins','analysis',{}),
 ('Latest Flamengo Corinthians score','search_matches',{'team':'Flamengo','opponent':'Corinthians','limit':1}),
 ('Who is Gabriel Barbosa?','search_players',{'name':'Gabriel'}),
 ('Flamengo roster and history','team_profile',{'team':'Flamengo'}),
 ('Derbies in 2023','search_matches',{'season':2023,'derbies':True}),
 ('Palmeiras competitions','team_profile',{'team':'Palmeiras'}),
 ('Compare seasons','trends',{'competition':'Brasileirão'}),
 ('Individual top scorers','top_scorers',{}),
 ('Matches during May 2019','search_matches',{'start_date':'01/05/2019','end_date':'31/05/2019'}),
]

class SoccerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.g = SoccerGraph()

    def test_all_sources(self):
        self.assertEqual(dict(self.g.sources),dict(zip(FILES,[4180,1337,1255,10296,6886,18207])))
        for source in FILES[:-1]: self.assertGreater(self.g.search_matches(source=source)['total'],0)
        self.assertEqual(len(self.g.players),18207)

    def test_normalization(self):
        for a,b in [('São Paulo-SP','Sao Paulo FC'),('Flamengo - RJ','Flamengo'),('Sport Club Corinthians Paulista','Corinthians'),('Grêmio-RS','Gremio')]:
            self.assertEqual(team_name(a),team_name(b))
        self.assertNotEqual(team_name('América-MG'),team_name('América-RN'))
        self.assertEqual(date_value('29/03/2003'),'2003-03-29')
        self.assertEqual(date_value('2012-05-19 18:30:00'),'2012-05-19')
        self.assertIsNone(number('NA'))
        with self.assertRaises(ValueError): date_value('nonsense')

    def test_filters_and_pagination(self):
        result = self.g.search_matches(team='Flamengo',opponent='Fluminense',season=2023)
        self.assertGreater(result['total'],0)
        for m in result['results']:
            self.assertEqual({m['home_team'],m['away_team']},{'flamengo','fluminense'})
            self.assertEqual(m['season'],2023)
        self.assertEqual(self.g.search_matches(limit=1,offset=1)['results'][0],self.g.search_matches(limit=2)['results'][1])
        self.assertEqual(self.g.search_matches(team='does not exist')['total'],0)
        for args in ({'venue':'bad'},{'limit':-1},{'start_date':'2023-01-02','end_date':'2023-01-01'}):
            with self.assertRaises(ValueError): self.g.search_matches(**args)

    def test_known_season_regression(self):
        r = self.g.team_statistics('Flamengo',competition='Brasileirão',season=2019)
        self.assertEqual([r[k] for k in ('matches','wins','draws','losses','points','goals_for','goals_against')],[38,28,6,4,90,86,37])
        self.assertEqual(self.g.standings('Serie A',2019)['table'][0]['team'],'flamengo')
        self.assertTrue(any(len(m['sources']) >= 3 for m in self.g.matches))

    def test_independent_arithmetic(self):
        g = SoccerGraph.__new__(SoccerGraph)
        g.matches=[]; g.teams=defaultdict(list)
        for i,(h,a,hg,ag) in enumerate([('a','b',2,0),('b','a',1,1),('a','b',0,3),('a','b',None,None)]):
            m=dict(id=str(i),date='2020-01-01',home_team=h,away_team=a,home_goal=hg,away_goal=ag,competition='Brasileirão',season=2020)
            g.matches.append(m);g.teams[h].append(m);g.teams[a].append(m)
        r=g.team_statistics('a')
        self.assertEqual((r['matches'],r['wins'],r['draws'],r['losses'],r['goals_for'],r['goals_against']),(3,1,1,1,3,4))
        self.assertAlmostEqual(g.analysis()['average_goals'],7/3)
        self.assertEqual(g.head_to_head('a','b')['record']['points'],4)

    def test_players_graph_and_limits(self):
        p=self.g.search_players(nationality='Brazil',position='forward')['results']
        self.assertTrue(p)
        self.assertEqual(p,sorted(p,key=lambda p: (-(p['overall'] or 0),p['name'])))
        self.assertTrue(self.g.neighbors('Flamengo')['results'])
        self.assertTrue(self.g.neighbors('158023',kind='player')['results'])
        self.assertFalse(self.g.top_scorers()['available'])
        with self.assertRaises(ValueError): self.g.standings('Copa do Brasil',2019)

    def test_sample_questions_and_performance(self):
        for question,name,args in EXAMPLES:
            with self.subTest(question=question):
                start=time.perf_counter(); result=getattr(self.g,name)(**args)
                self.assertIsInstance(result,dict)
                self.assertLess(time.perf_counter()-start,2 if name.startswith('search') else 5)
                json.dumps(result,allow_nan=False)

    def test_protocol(self):
        s=MCPServer(self.g)
        def call(method,params={}): return s.handle({'jsonrpc':'2.0','id':1,'method':method,'params':params})
        self.assertIn('error',call('tools/list'))
        self.assertEqual(call('initialize',{'protocolVersion':'2025-11-25'})['result']['protocolVersion'],'2025-11-25')
        self.assertIsNone(s.handle({'jsonrpc':'2.0','method':'notifications/initialized'}))
        self.assertEqual(len(call('tools/list')['result']['tools']),len(TOOLS))
        self.assertFalse(call('tools/call',{'name':'coverage'})['result']['isError'])
        self.assertEqual(call('tools/call',{'name':'search_matches','arguments':{'limit':True}})['error']['code'],-32602)
        self.assertTrue(call('tools/call',{'name':'search_matches','arguments':{'limit':-1}})['result']['isError'])
        self.assertEqual(call('nonexistent')['error']['code'],-32601)

    def test_stdio_subprocess(self):
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'team_statistics','arguments':{'team':'Flamengo','season':2019,'competition':'Brasileirão'}}}]
        proc=subprocess.run([sys.executable,'server.py'],input='invalid\n'+'\n'.join(map(json.dumps,requests))+'\n',text=True,capture_output=True,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        responses=[json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(responses),3)
        self.assertEqual(responses[0]['error']['code'],-32700)
        self.assertEqual(json.loads(responses[-1]['result']['content'][0]['text'])['points'],90)

if __name__ == '__main__': unittest.main()
