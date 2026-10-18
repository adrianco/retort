"""Given/When/Then scenarios, run with python -m unittest -v."""
import csv
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from soccer import DATA_DIR, FILES, SoccerGraph, normalize_team, parse_date, team_key
from server import MCPServer, SCHEMAS, validate


class DataScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = SoccerGraph()

    def test_given_all_sources_when_loaded_then_every_row_is_preserved(self):
        g = self.graph
        expected = dict(zip(FILES, (4180, 1337, 1255, 6886, 10296, 18207)))
        self.assertEqual(g.sources, expected)
        self.assertEqual(sum(len(m['sources']) for m in g.matches), sum(expected.values()) - 18207)
        self.assertEqual(len(g.players), 18207)
        for source in FILES[:-1]:
            self.assertGreater(g.search_matches(source=source)['total'], 0)

    def test_given_aliases_when_normalized_then_same_team_without_collisions(self):
        for a, b in [('Palmeiras-SP', 'Palmeiras'), ('Flamengo - RJ', 'Flamengo'),
                     ('Sport Club Corinthians Paulista', 'Corinthians'), ('Sao Paulo FC', 'São Paulo'),
                     ('Atletico Paranaense', 'Athletico-PR'), ('EC Bahia', 'Bahia')]:
            self.assertEqual(team_key(a), team_key(b))
        for a, b in [('América-MG', 'América-RN'), ('Botafogo-SP', 'Botafogo-RJ'),
                     ('Flamengo-PI', 'Flamengo-RJ'), ('Bragantino-PA', 'Bragantino-SP')]:
            self.assertNotEqual(team_key(a), team_key(b))

    def test_given_date_formats_when_parsed_then_iso_dates(self):
        for value in ('2023-09-24', '24/09/2023', '2023-09-24 18:30:00'):
            self.assertEqual(parse_date(value), '2023-09-24')
        with self.assertRaises(ValueError):
            parse_date('2023-02-30')

    def test_given_matches_when_searching_derby_then_both_orientations(self):
        found = self.graph.search_matches(team='Flamengo', opponent='Fluminense', limit=500)
        self.assertGreater(found['total'], 20)
        for m in found['items']:
            self.assertEqual({m['home_team'], m['away_team']}, {'Flamengo', 'Fluminense'})
            self.assertIn('date', m)
            self.assertIn('home_goal', m)
            self.assertIn('competition', m)
        self.assertEqual({m['home_team'] for m in found['items']}, {'Flamengo', 'Fluminense'})

    def test_given_filters_when_combined_then_only_requested_home_matches(self):
        result = self.graph.search_matches(team='Corinthians', venue='home', season=2022,
                    competition='Serie A', date_from='01/01/2022', date_to='2022-12-31')
        self.assertEqual(result['total'], 19)
        self.assertTrue(all(m['home_team'] == 'Corinthians' for m in result['items']))

    def test_given_complete_2019_when_standings_then_flamengo_has_90_points(self):
        table = self.graph.standings('Serie A', 2019)
        self.assertTrue(table['complete_double_round_robin'])
        first = table['table'][0]
        self.assertEqual((first['team'], first['points'], first['wins'], first['draws'], first['losses']),
                         ('Flamengo', 90, 28, 6, 4))
        self.assertEqual(len(table['table']), 20)
        self.assertTrue(all(row['matches'] == 38 for row in table['table']))
        self.assertEqual(sum(row['goals_for'] for row in table['table']),
                         sum(row['goals_against'] for row in table['table']))

    def test_given_2020_when_standings_then_season_spills_into_2021(self):
        g = self.graph
        table = g.standings('Brasileirão', 2020)
        self.assertTrue(table['complete_double_round_robin'])
        self.assertEqual(table['table'][0]['points'], 71)
        self.assertEqual(set(table['relegation_candidates']), {'Vasco', 'Goiás', 'Coritiba', 'Botafogo'})
        self.assertTrue(any(m['date'].startswith('2021') for m in g._select(competition='Brasileirão', season=2020)))

    def test_given_h2h_when_aggregated_then_records_are_symmetric(self):
        result = self.graph.head_to_head('Palmeiras', 'Santos')
        a, b = result['team'], result['opponent']
        self.assertEqual(a['wins'], b['losses'])
        self.assertEqual(a['draws'], b['draws'])
        self.assertEqual(a['goals_for'], b['goals_against'])

    def test_given_snapshot_when_players_filtered_then_ratings_and_attributes(self):
        rows = self.graph.search_players(nationality='Brazil')['items']
        self.assertTrue(all(p['nationality'] == 'Brazil' for p in rows))
        self.assertEqual(rows[0]['name'], 'Neymar Jr')
        self.assertGreaterEqual(rows[0]['overall'], rows[-1]['overall'])
        self.assertIn('Dribbling', rows[0]['attributes'])
        forwards = self.graph.search_players(position='forward', min_rating=80)['items']
        self.assertTrue(forwards)
        self.assertTrue(all(p['position'] in {'ST', 'CF', 'LW', 'RW', 'LF', 'RF', 'LS', 'RS'} for p in forwards))
        self.assertTrue(self.graph.search_players(name='Neymar')['items'])
        club = self.graph.search_players(club='Sport Club do Recife')['items']
        self.assertTrue(club)
        self.assertTrue(all(team_key(p['club']) == team_key('Sport') for p in club))

    def test_given_cups_when_requesting_finals_then_semifinals_excluded(self):
        finals = self.graph.search_matches(competition='Libertadores', stage='final', limit=500)['items']
        self.assertTrue(finals)
        self.assertTrue(all(m['stage'] == 'final' for m in finals))
        self.assertTrue(any(m['date'] is None for m in finals))
        cup = self.graph.search_matches(competition='Copa do Brasil', season=2019, stage='final')
        self.assertEqual(cup['total'], 2)
        self.assertTrue(all({m['home_team'],m['away_team']} == {'Internacional', 'Athletico-PR'} for m in cup['items']))
        self.assertIn('semifinals', self.graph.bracket('Libertadores', 2018)['stages'])
        with self.assertRaises(ValueError):
            self.graph.standings('Libertadores', 2018)

    def test_given_statistics_when_aggregated_then_rates_and_scores_consistent(self):
        result = self.graph.analysis(competition='Brasileirão', season=2019)
        self.assertEqual(result['matches'], 380)
        self.assertAlmostEqual(sum(result[k] for k in ('home_win_rate','away_win_rate','draw_rate')), 100)
        self.assertAlmostEqual(result['average_goals'], 876 / 380)
        self.assertFalse(result['individual_top_scorers']['available'])
        margins = [abs(m['home_goal'] - m['away_goal']) for m in result['biggest_wins']['items']]
        self.assertEqual(margins, sorted(margins, reverse=True))

    def test_given_pagination_when_following_offset_then_no_overlap(self):
        a = self.graph.search_matches(limit=3)
        b = self.graph.search_matches(limit=3, offset=a['next_offset'])
        self.assertFalse({m['id'] for m in a['items']} & {m['id'] for m in b['items']})
        self.assertIsNone(self.graph.search_matches(offset=a['total'])['next_offset'])
        with self.assertRaises(ValueError):
            self.graph.search_matches(limit=0)
        with self.assertRaises(ValueError):
            self.graph.search_matches(date_from='2023-12-31', date_to='2023-01-01')

    def test_given_absent_data_when_queried_then_empty_not_fabricated(self):
        self.assertEqual(self.graph.search_matches(team='Unlisted Team')['total'], 0)
        self.assertEqual(self.graph.search_players(name='Imaginary Player')['total'], 0)
        self.assertEqual(self.graph.team_statistics('Unlisted Team')['matches'], 0)
        self.assertIsNone(self.graph.analysis(season=2099)['average_goals'])
        self.assertEqual(self.graph.standings('Brasileirão', 2099)['table'], [])

    def test_given_graph_when_traversed_then_cross_file_relationships(self):
        edges = self.graph.graph_neighbors('team', 'São Paulo', limit=500, offset=500)
        self.assertGreater(edges['total'], 0)
        stats = self.graph.team_statistics('Santos', season=2019)
        self.assertGreater(stats['players']['total'], 0)
        self.assertGreater(stats['matches'], 0)
        self.assertGreater(self.graph.graph_neighbors('player', 'Neymar')['total'], 0)
        self.assertGreater(self.graph.graph_neighbors('competition', 'Libertadores')['total'], 0)

    def test_given_twenty_sample_questions_when_tools_called_then_serializable_answers(self):
        samples = json.loads(Path('sample_questions.json').read_text())
        self.assertGreaterEqual(len(samples), 20)
        for sample in samples:
            with self.subTest(question=sample['question']):
                validate(sample['tool'], sample['arguments'])
                result = getattr(self.graph, sample['tool'])(**sample['arguments'])
                self.assertIsInstance(result, dict)
                json.dumps(result, allow_nan=False)

    def test_given_loaded_data_when_queries_run_then_within_latency_budget(self):
        start = time.perf_counter()
        self.graph.search_matches(team='Flamengo', season=2019)
        self.assertLess(time.perf_counter() - start, 2)
        start = time.perf_counter()
        self.graph.analysis()
        self.assertLess(time.perf_counter() - start, 5)


class SyntheticScenarios(unittest.TestCase):
    def test_given_duplicate_and_unplayed_rows_when_loaded_then_count_only_played_once(self):
        with tempfile.TemporaryDirectory() as directory:
            for filename in FILES:
                with (DATA_DIR / filename).open() as f:
                    headers = next(csv.reader(f))
                with (Path(directory) / filename).open('w', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=headers)
                    w.writeheader()
                    if filename == 'Brasileirao_Matches.csv':
                        w.writerow(dict(datetime='2023-01-01 23:00:00',home_team='Palmeiras-SP',away_team='Santos-SP',home_goal=2,away_goal=0,season=2023,round=1))
                        w.writerow(dict(datetime='2023-02-01',home_team='Santos-SP',away_team='Palmeiras-SP',home_goal='NA',away_goal='NA',season=2023,round=2))
                    elif filename == 'BR-Football-Dataset.csv':
                        w.writerow(dict(date='2023-01-02',time='02:00:00',home='Palmeiras',away='Santos',home_goal='2.0',away_goal='0.0',tournament='Serie A',home_corner='5'))
            g = SoccerGraph(directory)
            self.assertEqual(len(g.matches), 2)
            self.assertEqual(g.team_statistics('Palmeiras')['matches'], 1)
            self.assertEqual(g.analysis()['average_goals'], 2)
            self.assertEqual(g.search_matches(source='BR-Football-Dataset.csv')['total'], 1)
            self.assertEqual(g.matches[1]['statistics']['home_corner'], '5')


class ProtocolScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = SoccerGraph()

    def setUp(self):
        self.server = MCPServer(self.graph)

    def request(self, method, params=None, rid=1):
        return self.server.handle(dict(jsonrpc='2.0', id=rid, method=method, params=params or {}))

    def initialize(self):
        result = self.request('initialize', dict(protocolVersion='2025-06-18', capabilities={}, clientInfo={'name':'test','version':'1'}))
        self.assertIn('tools', result['result']['capabilities'])
        self.server.handle({'jsonrpc':'2.0','method':'notifications/initialized'})

    def test_given_client_when_initialized_then_tools_can_be_discovered_and_called(self):
        self.assertIn('error', self.request('tools/list'))
        self.initialize()
        self.assertEqual(len(self.request('tools/list')['result']['tools']), len(SCHEMAS))
        response = self.request('tools/call', {'name':'head_to_head','arguments':{'team':'Flamengo','opponent':'Fluminense'}})
        self.assertFalse(response['result']['isError'])
        self.assertIn('structuredContent', response['result'])
        self.assertEqual(json.loads(response['result']['content'][0]['text']), response['result']['structuredContent'])

    def test_given_bad_requests_when_handled_then_errors_and_notifications_are_correct(self):
        self.initialize()
        self.assertEqual(self.request('missing')['error']['code'], -32601)
        self.assertEqual(self.request('tools/call', {'name':'missing'})['error']['code'], -32602)
        for args in ({'season':True}, {'limit':-1}, {'venue':'sideways'}, {'oops':1}):
            self.assertTrue(self.request('tools/call', {'name':'search_matches','arguments':args})['result']['isError'])
        self.assertEqual(self.server.handle([])['error']['code'], -32600)
        self.assertIsNone(self.server.handle({'jsonrpc':'2.0','method':'notifications/cancelled'}))
        output = io.StringIO()
        self.server.serve(io.StringIO('{broken\n{"jsonrpc":"2.0","id":2,"method":"ping"}\n'),output)
        responses = list(map(json.loads, output.getvalue().splitlines()))
        self.assertEqual(responses[0]['error']['code'], -32700)
        self.assertEqual(responses[1]['result'], {})

    def test_given_stdio_subprocess_when_client_connects_then_clean_json_lines(self):
        requests = [dict(jsonrpc='2.0',id=1,method='initialize',params=dict(protocolVersion='2025-06-18', capabilities={}, clientInfo={'name':'test','version':'1'})),
                    dict(jsonrpc='2.0',method='notifications/initialized'),
                    dict(jsonrpc='2.0',id=2,method='tools/call',params={'name':'dataset_info'})]
        proc = subprocess.run([sys.executable, str(Path('server.py').resolve())], cwd=tempfile.gettempdir(),
                    input='\n'.join(map(json.dumps,requests))+'\n',text=True,capture_output=True,timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        responses = list(map(json.loads, proc.stdout.splitlines()))
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[1]['result']['structuredContent']['players'], 18207)


if __name__ == '__main__':
    unittest.main()
