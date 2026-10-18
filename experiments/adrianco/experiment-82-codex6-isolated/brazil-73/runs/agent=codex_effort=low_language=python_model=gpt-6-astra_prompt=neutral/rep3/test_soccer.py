"""Given/When/Then scenarios covering real CSVs and independently calculated fixtures."""
import io
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from soccer import SoccerGraph, team_key, date_key, number, FILES
from server import MCPServer


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = SoccerGraph()

    def test_all_source_rows_preserved(self):
        g = self.graph
        self.assertEqual(g.sources, dict(zip(FILES, (4180, 1337, 1255, 6886, 10296, 18207))))
        self.assertEqual(sum(len(m['sources']) for m in g.matches), sum(g.sources[f] for f in FILES[:-1]))
        for source in FILES[:-1]:
            self.assertGreater(g.search_matches(source=source)['total'], 0)
        self.assertEqual(len(g.players), 18207)

    def test_aliases_and_ambiguity(self):
        for alias, canonical in [('São Paulo-SP', 'sao paulo'), ('São Paulo FC', 'sao paulo'),
                                 ('Sport Club Corinthians Paulista', 'corinthians'),
                                 ('Flamengo - RJ', 'flamengo'), ('Athletico Paranaense - PR', 'atletico-pr'),
                                 ('EC Bahia', 'bahia')]:
            self.assertEqual(team_key(alias), canonical)
        self.assertNotEqual(team_key('Botafogo-PB'), team_key('Botafogo-RJ'))
        self.assertNotEqual(team_key('América-MG'), team_key('América-RN'))

    def test_dates_missing_scores(self):
        self.assertEqual(date_key('29/03/2003'), '2003-03-29')
        self.assertEqual(date_key('2012-05-19 18:30:00'), '2012-05-19')
        self.assertIsNone(number('-'))
        self.assertIsNone(number('NA'))
        self.assertEqual(number('2.0'), 2)
        with self.assertRaises(ValueError):
            date_key('2023-02-30')

    def test_given_fixtures_when_record_then_exact_arithmetic(self):
        rows = [dict(home_team='a', away_team='b', home_goal=x, away_goal=y) for x, y in [(2, 0), (1, 1), (0, 3), (None, None)]]
        r = self.graph._record('a', rows)
        self.assertEqual([r[k] for k in ('played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against', 'points')], [3, 1, 1, 1, 3, 4, 4])
        self.assertEqual(self.graph._record('b', rows)['goal_difference'], 1)

    def test_given_2019_when_standings_then_known_flamengo_record(self):
        first = self.graph.standings('Serie A', 2019)['table'][0]
        self.assertEqual((first['team'], first['played'], first['points'], first['wins']), ('flamengo', 38, 90, 28))

    def test_head_to_head_filters_and_pagination(self):
        g = self.graph
        matches = g.search_matches(team='Flamengo', opponent='Fluminense', limit=2)
        self.assertGreater(matches['total'], 2)
        self.assertEqual(matches['next_offset'], 2)
        self.assertNotEqual(matches['items'][0]['id'], g.search_matches(team='Flamengo', opponent='Fluminense', offset=2, limit=2)['items'][0]['id'])
        for m in matches['items']:
            self.assertEqual({m['home_team'], m['away_team']}, {'flamengo', 'fluminense'})
        h = g.head_to_head('Flamengo', 'Fluminense')
        self.assertEqual(h['team']['wins'], h['opponent']['losses'])
        home = g.search_matches(team='Corinthians', venue='home', season=2022, start_date='2022-01-01', end_date='2022-12-31')
        self.assertTrue(all(m['home_team'] == 'corinthians' and m['season'] == 2022 for m in home['items']))

    def test_players_roster_and_graph_links(self):
        g = self.graph
        p = g.search_players(nationality='Brazil', limit=5)['items']
        self.assertTrue(all(x['nationality'] == 'Brazil' for x in p))
        self.assertEqual([x['overall'] for x in p], sorted([x['overall'] for x in p], reverse=True))
        edges = g.graph_neighbors(p[0]['id'])['items']
        self.assertEqual(edges[0]['target'], 'team:' + p[0]['club'])
        self.assertIn('roster', g.team_stats('Flamengo'))
        self.assertGreater(g.graph_neighbors('team:flamengo')['total'], 0)

    def test_stage_is_exact(self):
        finals = self.graph.search_matches(competition='Libertadores', stage='final', limit=500)
        self.assertGreater(finals['total'], 0)
        self.assertTrue(all(m['stage'] == 'final' for m in finals['items']))

    def test_bad_inputs_and_empty_results(self):
        for args in ({'limit': 0}, {'venue': 'x'}, {'start_date': '2024-01-01', 'end_date': '2023-01-01'}, {'opponent': 'santos'}):
            with self.assertRaises(ValueError):
                self.graph.search_matches(**args)
        self.assertEqual(self.graph.search_matches(team='no such team')['total'], 0)
        self.assertEqual(self.graph.team_stats('no such team')['played'], 0)
        with self.assertRaises(ValueError):
            self.graph.standings('Copa do Brasil', 2020)

    def test_twenty_four_question_routes_and_performance(self):
        # The LLM translates each question into these structured tool calls.
        cases = [
            ('Show Flamengo vs Fluminense', 'search_matches', {'team': 'Flamengo', 'opponent': 'Fluminense'}),
            ('Palmeiras in 2023', 'search_matches', {'team': 'Palmeiras', 'season': 2023}),
            ('Libertadores finals', 'search_matches', {'competition': 'Libertadores', 'stage': 'final'}),
            ('Corinthians home record 2022', 'team_stats', {'team': 'Corinthians', 'season': 2022, 'venue': 'home'}),
            ('Most goals in Serie A 2023', 'standings', {'competition': 'Serie A', 'season': 2023}),
            ('Compare Palmeiras and Santos', 'head_to_head', {'team': 'Palmeiras', 'opponent': 'Santos'}),
            ('Brazilian players', 'search_players', {'nationality': 'Brazil'}),
            ('Best Flamengo players', 'search_players', {'club': 'Flamengo'}),
            ('Sao Paulo forwards', 'search_players', {'club': 'São Paulo FC', 'position': 'forward'}),
            ('2019 league winner', 'standings', {'competition': 'Brasileirão', 'season': 2019}),
            ('2018 Libertadores bracket', 'competition_results', {'competition': 'Libertadores', 'season': 2018}),
            ('Bottom teams in 2020', 'standings', {'competition': 'Serie A', 'season': 2020}),
            ('Average goals in league', 'analysis', {'competition': 'Serie A'}),
            ('Best away record', 'analysis', {'venue': 'away'}),
            ('Biggest wins', 'analysis', {}),
            ('Latest Flamengo Corinthians match', 'search_matches', {'team': 'Flamengo', 'opponent': 'Corinthians', 'limit': 1}),
            ('Gabriel Barbosa player profile', 'search_players', {'name': 'Gabriel Barbosa'}),
            ('Derbies in 2023', 'search_matches', {'derbies': True, 'season': 2023}),
            ('Palmeiras competitions', 'team_stats', {'team': 'Palmeiras'}),
            ('Best home record', 'analysis', {'venue': 'home'}),
            ('Compare 2018 and 2019', 'analysis', {'competition': 'Serie A'}),
            ('Matches in September 2023', 'search_matches', {'start_date': '2023-09-01', 'end_date': '2023-09-30'}),
            ('Dataset availability', 'coverage', {}),
            ('Flamengo relationships', 'graph_neighbors', {'entity_id': 'team:flamengo'}),
        ]
        for question, method, args in cases:
            with self.subTest(question=question):
                start = time.perf_counter()
                result = getattr(self.graph, method)(**args)
                self.assertIsInstance(result, dict)
                self.assertLess(time.perf_counter() - start, 2 if method.startswith('search') else 5)
                json.dumps(result, allow_nan=False)

    def test_protocol_and_validation(self):
        server = MCPServer(self.graph)
        def call(method, params=None):
            return server.handle({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})
        self.assertEqual(call('initialize', {'protocolVersion': '2025-06-18'})['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(len(call('tools/list')['result']['tools']), 9)
        self.assertEqual(call('missing')['error']['code'], -32601)
        self.assertTrue(call('tools/call', {'name': 'search_matches', 'arguments': {'limit': True}})['result']['isError'])
        self.assertTrue(call('tools/call', {'name': 'team_stats', 'arguments': {}})['result']['isError'])
        self.assertFalse(call('tools/call', {'name': 'search_players', 'arguments': {'nationality': 'Brazil', 'limit': 1}})['result']['isError'])
        stream = io.StringIO('{bad\n' + json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
        output = io.StringIO()
        server.serve(stream, output)
        self.assertEqual(json.loads(output.getvalue())['error']['code'], -32700)

    def test_stdio_subprocess(self):
        request = {'jsonrpc': '2.0', 'id': 42, 'method': 'tools/call', 'params': {'name': 'search_matches', 'arguments': {'limit': 1}}}
        proc = subprocess.run([sys.executable, str(Path(__file__).with_name('server.py'))], input=json.dumps(request) + '\n', text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result['id'], 42)
        self.assertEqual(len(result['result']['structuredContent']['items']), 1)


if __name__ == '__main__':
    unittest.main()
