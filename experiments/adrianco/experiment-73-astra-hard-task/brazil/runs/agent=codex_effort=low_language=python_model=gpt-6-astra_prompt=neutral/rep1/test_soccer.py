"""Behavior-oriented tests against hand-calculated fixtures and all supplied data."""
import csv
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from soccer import DATA_DIR, FILES, SoccerGraph, parse_date, team_key
from server import MCPServer, TOOLS, validate_arguments


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for name in FILES:
            with (DATA_DIR / name).open(encoding='utf-8-sig') as f:
                header = next(csv.reader(f))
            with (root / name).open('w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(header)
        self.root = root

    def write(self, filename, **row):
        with (self.root / filename).open(encoding='utf-8') as f:
            fields = next(csv.reader(f))
        with (self.root / filename).open('a', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fields).writerow(row)

    def match(self, date, home, away, hg, ag, **extra):
        self.write(FILES[0], datetime=date, home_team=home, away_team=away,
                   home_goal=hg, away_goal=ag, season=2023, round=1, **extra)

    def test_given_three_results_when_aggregated_then_records_are_exact(self):
        self.match('2023-01-01', 'Flamengo-RJ', 'Palmeiras-SP', 2, 0)
        self.match('2023-02-01', 'Palmeiras', 'Flamengo', 1, 1)
        self.match('2023-03-01', 'Flamengo', 'Palmeiras', 0, 3)
        g = SoccerGraph(self.root)
        result = g.team_statistics('Clube de Regatas do Flamengo', season=2023)
        self.assertEqual([result[k] for k in ('played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against', 'points')], [3, 1, 1, 1, 3, 4, 4])
        self.assertEqual(result['home']['wins'], 1)
        self.assertEqual(result['away']['draws'], 1)
        h = g.head_to_head('Flamengo', 'Palmeiras')
        self.assertEqual(h['latest_match']['date'], '2023-03-01')
        self.assertEqual(h['team_record']['goals_for'], h['opponent_record']['goals_against'])
        stats = g.statistics()
        self.assertEqual(stats['goals_per_match'], round(7 / 3, 4))
        self.assertEqual(stats['biggest_victories'][0]['away_goal'], 3)
        table = g.standings('Serie A', 2023)
        self.assertEqual(table['table'][0]['team'], 'Palmeiras')
        self.assertFalse(table['complete_round_robin'])
        self.assertEqual(table['relegation_candidates'], [])

    def test_given_overlapping_sources_when_loaded_then_deduplicate_keep_provenance(self):
        self.match('2023-01-01 23:00:00', 'São Paulo-SP', 'Flamengo-RJ', 2, 1)
        self.write('BR-Football-Dataset.csv', date='2023-01-02', tournament='Serie A', home='Sao Paulo', away='Flamengo', home_goal='2.0', away_goal='1.0', home_corner='4.0')
        g = SoccerGraph(self.root)
        self.assertEqual(len(g.matches), 1)
        self.assertEqual(len(g.matches[0]['sources']), 2)
        self.assertEqual(g.matches[0]['statistics']['home_corner'], 4)
        self.assertEqual(g.search_matches(source='BR-Football-Dataset.csv')['total'], 1)
        self.assertIn('raw', g.get_match(g.matches[0]['id'])['sources'][0])

    def test_given_conflicting_scores_when_loaded_then_first_source_wins_and_issue_is_reported(self):
        self.match('2023-01-01', 'Flamengo', 'Palmeiras', 2, 1)
        self.write('BR-Football-Dataset.csv', date='2023-01-01', tournament='Serie A', home='Flamengo', away='Palmeiras', home_goal=1, away_goal=1)
        g = SoccerGraph(self.root)
        self.assertEqual(len(g.matches), 1)
        self.assertEqual(g.matches[0]['home_goal'], 2)
        self.assertEqual(g.issues[0]['reason'], 'Conflicting score')

    def test_given_same_pair_different_competition_then_never_merge(self):
        self.match('2023-01-01', 'Flamengo', 'Palmeiras', 2, 1)
        self.write('BR-Football-Dataset.csv', date='2023-01-01', tournament='Copa do Brasil', home='Flamengo', away='Palmeiras', home_goal=2, away_goal=1)
        self.assertEqual(len(SoccerGraph(self.root).matches), 2)

    def test_missing_score_is_not_a_draw_and_invalid_row_is_reported(self):
        self.match('2023-01-01', 'Flamengo', 'Palmeiras', '', '')
        self.match('not a date', 'Flamengo', 'Palmeiras', 2, 1)
        g = SoccerGraph(self.root)
        r = g.team_statistics('Flamengo')
        self.assertEqual((r['matches'], r['played'], r['draws']), (1, 0, 0))
        self.assertEqual(g.sources[FILES[0]]['rejected'], 1)
        self.assertIsNone(g.statistics()['goals_per_match'])

    def test_missing_files_fail_clearly(self):
        (self.root / FILES[0]).unlink()
        with self.assertRaises(FileNotFoundError):
            SoccerGraph(self.root)


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        start = time.perf_counter()
        cls.graph = SoccerGraph()
        cls.load_seconds = time.perf_counter() - start

    def test_all_six_sources_loaded_and_queryable(self):
        expected = {'Brasileirao_Matches.csv': 4180, 'Brazilian_Cup_Matches.csv': 1337,
                    'Libertadores_Matches.csv': 1255, 'BR-Football-Dataset.csv': 10296,
                    'novo_campeonato_brasileiro.csv': 6886, 'fifa_data.csv': 18207}
        self.assertEqual({k: v['loaded'] for k, v in self.graph.sources.items()}, expected)
        self.assertTrue(all(v['rejected'] == 0 for v in self.graph.sources.values()))
        for source in FILES[:-1]:
            self.assertGreater(self.graph.search_matches(source=source, limit=1)['total'], 0)

    def test_normalization_and_dates(self):
        for variant in ('Sao Paulo-SP', 'São Paulo FC', 'São Paulo Futebol Clube', 'São Paulo'):
            self.assertEqual(team_key(variant), 'sao paulo')
        self.assertEqual(team_key('Sport Club Corinthians Paulista'), 'corinthians')
        self.assertEqual(team_key('Atlético Paranaense - PR'), team_key('Athletico'))
        self.assertNotEqual(team_key('Atlético - MG'), team_key('Atlético - PR'))
        self.assertNotEqual(team_key('Botafogo - PB'), team_key('Botafogo - RJ'))
        self.assertNotEqual(team_key('Bragantino - PA'), team_key('Bragantino - SP'))
        for date in ('2023-09-24', '24/09/2023', '2023-09-24 20:00:00'):
            self.assertEqual(parse_date(date), '2023-09-24')

    def test_2019_standings_are_not_inflated_by_overlapping_sources(self):
        result = self.graph.standings('Brasileirão', 2019)
        self.assertTrue(result['complete_round_robin'])
        self.assertEqual(len(result['table']), 20)
        leader = result['table'][0]
        self.assertEqual((leader['team'], leader['points'], leader['wins'], leader['draws'], leader['played']), ('Flamengo', 90, 28, 6, 38))
        self.assertEqual(sum(r['goals_for'] for r in result['table']), sum(r['goals_against'] for r in result['table']))

    def test_2020_season_includes_matches_played_in_2021(self):
        result = self.graph.search_matches(competition='Serie A', season=2020, date_from='2021-01-01', limit=500)
        self.assertGreater(result['total'], 0)
        self.assertEqual(self.graph.standings('Serie A', 2020)['table'][0]['points'], 71)

    def test_cup_final_rounds_and_brackets(self):
        for season in (2012, 2013, 2016, 2019):
            finals = self.graph.search_matches(competition='Copa do Brasil', season=season, stage='final')
            self.assertEqual(finals['total'], 2, season)
        bracket = self.graph.competition_bracket('Libertadores', 2018)
        self.assertIn('final', bracket['stages'])
        self.assertEqual(len(bracket['stages']['final'][0]['matches']), 2)
        with self.assertRaises(ValueError):
            self.graph.standings('Libertadores', 2018)

    def test_unknown_fixture_is_preserved(self):
        unknown = [m for m in self.graph.matches if m['date'] is None]
        self.assertEqual(len(unknown), 1)
        self.assertIsNone(unknown[0]['home_goal'])
        self.assertNotIn(unknown[0], self.graph._select(date_from='2000-01-01'))

    def test_match_filters_and_pagination(self):
        a = self.graph.search_matches(team='Flamengo', opponent='Fluminense', limit=1)
        b = self.graph.search_matches(team='Flamengo', opponent='Fluminense', limit=1, offset=1)
        self.assertGreater(a['total'], 1)
        self.assertNotEqual(a['items'][0]['id'], b['items'][0]['id'])
        self.assertEqual(a['next_offset'], 1)
        home = self.graph.search_matches(team='Corinthians', venue='home', season=2022, competition='Serie A', limit=500)
        self.assertTrue(all(m['home_team'] == 'Corinthians' for m in home['items']))
        for kwargs in ({'venue': 'bad'}, {'limit': 0}, {'offset': -1}, {'season': '2023'}, {'date_from': '2024-01-01', 'date_to': '2023-01-01'}, {'source': 'missing'}, {'opponent': 'Santos'}):
            with self.assertRaises(ValueError):
                self.graph.search_matches(**kwargs)
        self.assertEqual(self.graph.search_matches(team='No such club')['total'], 0)

    def test_player_search_and_cross_file_graph(self):
        result = self.graph.search_players(nationality='Brazilian', limit=500)
        self.assertGreater(result['total'], 500)
        self.assertTrue(all(p['nationality'] == 'Brazil' for p in result['items']))
        self.assertEqual(result['items'][0]['name'], 'Neymar Jr')
        self.assertIn('Dribbling', result['items'][0]['attributes'])
        g = self.graph.graph_neighbors('Flamengo', limit=500)
        ids = {n['id'] for n in g['nodes']}
        self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in g['edges']))
        self.assertIn('IN_COMPETITION', {e['relation'] for e in g['edges']})
        self.assertGreater(self.graph.team_statistics('Flamengo')['played'], 0)
        # FIFA may have no Flamengo players; use a represented club to prove player edges.
        g = self.graph.graph_neighbors('FC Barcelona')
        self.assertIn('PLAYS_FOR_SNAPSHOT', {e['relation'] for e in g['edges']})

    def test_performance_on_full_dataset(self):
        start = time.perf_counter()
        self.graph.search_matches(team='Palmeiras', season=2023)
        self.graph.search_players(name='Neymar')
        self.assertLess(time.perf_counter() - start, 2)
        start = time.perf_counter()
        self.graph.statistics(competition='Brasileirão')
        self.assertLess(time.perf_counter() - start, 5)

    def test_sample_questions(self):
        examples = json.loads(Path('sample_questions.json').read_text())
        self.assertGreaterEqual(len(examples), 20)
        for example in examples:
            with self.subTest(question=example['question']):
                validate_arguments(example['tool'], example['arguments'])
                result = getattr(self.graph, example['tool'])(**example['arguments'])
                self.assertIsInstance(result, dict)
                self.assertTrue(result)


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = SoccerGraph()

    def setUp(self):
        self.server = MCPServer(self.graph)

    def request(self, method, params=None, rid=1):
        return self.server.handle({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params or {}})

    def initialize(self):
        reply = self.request('initialize', {'protocolVersion': '2025-11-25', 'clientInfo': {'name': 'test', 'version': '1'}, 'capabilities': {}})
        self.assertIn('tools', reply['result']['capabilities'])
        self.assertIsNone(self.server.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'}))

    def test_lifecycle_discovery_and_call(self):
        self.assertIn('error', self.request('tools/list'))
        self.initialize()
        tools = self.request('tools/list')['result']['tools']
        self.assertEqual({t['name'] for t in tools}, set(TOOLS))
        r = self.request('tools/call', {'name': 'search_matches', 'arguments': {'team': 'Flamengo', 'limit': 1}})['result']
        self.assertFalse(r['isError'])
        self.assertEqual(len(r['structuredContent']['items']), 1)
        self.assertIn('Flamengo', r['content'][0]['text'])
        self.assertEqual(self.request('ping')['result'], {})

    def test_invalid_requests_and_arguments_do_not_crash(self):
        self.initialize()
        for value in ([], None, 42, {'jsonrpc': '1.0'}, {'jsonrpc': '2.0', 'method': 'ping', 'id': []}):
            self.assertEqual(self.server.handle(value)['error']['code'], -32600)
        self.assertEqual(self.request('missing')['error']['code'], -32601)
        self.assertEqual(self.request('tools/call', {'name': '__init__'})['error']['code'], -32602)
        for args in ({'limit': True}, {'limit': 9999}, {'team': []}, {'x': 1}, {'date_from': 'yesterday'}):
            r = self.request('tools/call', {'name': 'search_matches', 'arguments': args})
            self.assertTrue(r['result']['isError'])
        r = self.request('tools/call', {'name': 'head_to_head', 'arguments': {}})
        self.assertTrue(r['result']['isError'])

    def test_built_zipapp_serves_real_tool_calls(self):
        from build import build
        with tempfile.TemporaryDirectory() as temporary:
            artifact = build(Path(temporary) / 'soccer.pyz')
            requests = [
                {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'head_to_head', 'arguments': {'team': 'Flamengo', 'opponent': 'Fluminense'}}},
            ]
            process = subprocess.run([sys.executable, str(artifact), '--data-dir', str(DATA_DIR)],
                                     input='\n'.join(map(json.dumps, requests)) + '\n',
                                     text=True, capture_output=True, timeout=10, cwd=temporary)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout.splitlines()[-1])['result']
            self.assertFalse(result['isError'])
            self.assertGreater(result['structuredContent']['team_record']['played'], 0)

    def test_stdio_subprocess_emits_only_json_and_recovers_after_parse_error(self):
        messages = [
            '{bad json',
            json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}}),
            json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}),
            json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}),
            json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'standings', 'arguments': {'competition': 'Brasileirão', 'season': 2019}}}),
        ]
        proc = subprocess.run([sys.executable, 'server.py'], input='\n'.join(messages) + '\n', text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        replies = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(replies), 4)
        self.assertEqual(replies[0]['error']['code'], -32700)
        self.assertEqual(replies[-1]['result']['structuredContent']['table'][0]['points'], 90)
        self.assertEqual(proc.stderr, '')


if __name__ == '__main__':
    unittest.main()
