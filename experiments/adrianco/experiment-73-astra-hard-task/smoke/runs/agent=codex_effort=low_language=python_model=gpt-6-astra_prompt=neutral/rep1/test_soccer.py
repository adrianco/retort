"""Behavior scenarios covering fixtures, real datasets, performance and MCP stdio."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from soccer import DATA_DIR, SOURCES, SoccerGraph, parse_date, team_key, team_name
from server import MCPServer, TOOLS
from sample_queries import SAMPLE_QUERIES


class NormalizationTests(unittest.TestCase):
    def test_team_aliases_accents_and_state_suffixes(self):
        for a, b in [('Palmeiras-SP', 'Palmeiras'), ('Flamengo - RJ', 'Flamengo'),
                     ('Sport Club Corinthians Paulista', 'Corinthians'),
                     ('Sao Paulo FC', 'São Paulo-SP'), ('Atletico-PR', 'Athletico Paranaense'),
                     ('EC Bahia', 'Bahia-BA'), ('Vasco Da Gama RJ', 'Vasco'),
                     ('Fortaleza FC', 'Fortaleza'), ('America MG', 'América-MG')]:
            with self.subTest(a=a, b=b):
                self.assertEqual(team_key(a), team_key(b))
        for a, b in [('Botafogo-PB', 'Botafogo-RJ'), ('America-RN', 'America-MG'),
                     ('Atletico-GO', 'Atletico-MG'), ('Flamengo-PI', 'Flamengo-RJ')]:
            self.assertNotEqual(team_key(a), team_key(b))

    def test_dates(self):
        for date in ('2023-09-24', '24/09/2023', '2023-09-24 18:00:00', '2023-09-24T18:00:00'):
            self.assertEqual(parse_date(date), '2023-09-24')
        for date in ('2023-02-30', 'yesterday', ''):
            with self.assertRaises(ValueError):
                parse_date(date)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.headers = {}
        for name in SOURCES:
            with (DATA_DIR / name).open() as f:
                self.headers[name] = next(csv.reader(f))
            self.write(name, [])

    def write(self, name, rows):
        with (self.root / name).open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, self.headers[name])
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def match(date, home, away, hg, ag):
        return dict(datetime=date, home_team=home, away_team=away, home_goal=hg,
                    away_goal=ag, season='2023', round='1')

    def load_fixture(self):
        self.write('Brasileirao_Matches.csv', [
            self.match('2023-01-01 21:00:00', 'Flamengo-RJ', 'Palmeiras-SP', '2', '0'),
            self.match('2023-02-01', 'Palmeiras-SP', 'Flamengo-RJ', '1', '1'),
            self.match('2023-03-01', 'Flamengo-RJ', 'Santos-SP', '0', '3'),
            self.match('2023-04-01', 'Flamengo-RJ', 'Santos-SP', '', ''),
        ])
        self.write('BR-Football-Dataset.csv', [dict(tournament='Serie A', date='2023-01-02', time='00:00:00',
                    home='Flamengo', away='Palmeiras', home_goal='2.0', away_goal='0.0', home_corner='4.0')])
        self.write('novo_campeonato_brasileiro.csv', [dict(ID='x', Data='01/01/2023', Ano='2023', Rodada='1',
                    Equipe_mandante='Flamengo', Equipe_visitante='Palmeiras', Gols_mandante='3', Gols_visitante='0',
                    Mandante_UF='RJ', Visitante_UF='SP', Arena='Maracanã')])
        self.write('fifa_data.csv', [dict(ID='1', Name='João', Age='20', Nationality='Brazil', Overall='80',
                    Potential='85', Club='Flamengo', Position='ST', Finishing='90')])
        return SoccerGraph(self.root)

    def test_given_overlapping_sources_when_loaded_then_deduplicate_and_keep_evidence(self):
        g = self.load_fixture()
        self.assertEqual(len(g._matches), 4)
        m = g.matches({'start_date': '2023-01-01', 'end_date': '2023-01-01'})['items'][0]
        detail = g.match_detail(m['id'])
        self.assertEqual(len(detail['sources']), 3)
        self.assertEqual(detail['home_goal'], 2)
        self.assertEqual(detail['conflicts'][0]['home_goal'], 3)
        self.assertEqual(detail['stadium'], 'Maracanã')
        self.assertEqual(detail['statistics']['BR-Football-Dataset.csv']['home_corner'], '4.0')
        self.assertEqual(g.matches({'source': 'BR-Football-Dataset.csv'})['total'], 1)

    def test_given_results_when_stats_requested_then_exact_record_and_unplayed_exclusion(self):
        g = self.load_fixture()
        r = g.team_stats('Flamengo')
        for k, v in dict(matches=3, scheduled=1, wins=1, draws=1, losses=1, goals_for=3,
                         goals_against=4, points=4, win_rate=33.33).items():
            self.assertEqual(r[k], v, k)
        self.assertEqual(r['by_venue']['home']['losses'], 1)
        h = g.head_to_head('Palmeiras', 'Flamengo')['record']
        self.assertEqual((h['matches'], h['wins'], h['draws'], h['losses']), (2, 0, 1, 1))
        a = g.analysis()
        self.assertEqual(a['average_goals'], 2.3333)
        self.assertEqual(a['biggest_wins'][0]['away_team'], 'Santos')
        self.assertEqual(a['home_win_rate'], 33.33)
        self.assertEqual(a['away_win_rate'], 33.33)

    def test_given_team_when_graph_explored_then_players_and_matches_share_entity(self):
        g = self.load_fixture()
        result = g.graph('Flamengo')
        relations = {e['relation'] for e in result['edges']['items']}
        self.assertEqual(relations, {'HOME_TEAM', 'AWAY_TEAM', 'PLAYS_FOR_SNAPSHOT'})
        p = g.players(club='Flamengo-RJ', position='forward')['items'][0]
        self.assertEqual(p['attributes']['Finishing'], '90')
        self.assertEqual(g.team_info('Flamengo')['players']['total'], 1)

    def test_same_source_adjacent_matches_and_reverse_legs_are_not_merged(self):
        self.write('Brasileirao_Matches.csv', [self.match('2023-01-01', 'A', 'B', '1', '0'),
                                              self.match('2023-01-02', 'A', 'B', '1', '0'),
                                              self.match('2023-01-01', 'B', 'A', '1', '0')])
        self.assertEqual(len(SoccerGraph(self.root)._matches), 3)

    def test_different_scores_on_adjacent_days_not_merged(self):
        self.write('Brasileirao_Matches.csv', [self.match('2023-01-01', 'A', 'B', '1', '0')])
        self.write('BR-Football-Dataset.csv', [dict(tournament='Serie A', date='2023-01-02', home='A', away='B', home_goal='2', away_goal='0')])
        self.assertEqual(len(SoccerGraph(self.root)._matches), 2)

    def test_postponed_season_uses_explicit_year_not_calendar_year(self):
        row = self.match('2021-02-25', 'Flamengo', 'Santos', '2', '0')
        row['season'] = '2020'
        self.write('Brasileirao_Matches.csv', [row])
        self.write('BR-Football-Dataset.csv', [dict(tournament='Serie A', date='2021-02-26',
                    home='Flamengo', away='Santos', home_goal='2', away_goal='0')])
        g = SoccerGraph(self.root)
        self.assertEqual(g.matches({'season': 2020})['total'], 1)
        self.assertEqual(g.matches({'season': 2021})['total'], 0)
        self.assertEqual(g.coverage()['duplicates_merged'], 1)

    def test_bad_row_reported_and_missing_file_fails_clearly(self):
        self.write('Brasileirao_Matches.csv', [self.match('garbage', 'A', 'B', '1', '0')])
        g = SoccerGraph(self.root)
        self.assertEqual(g.errors[0]['line'], 2)
        self.assertEqual(g.errors[0]['file'], 'Brasileirao_Matches.csv')
        (self.root / 'fifa_data.csv').unlink()
        with self.assertRaisesRegex(FileNotFoundError, 'fifa_data.csv'):
            SoccerGraph(self.root)

    def test_unknown_date_and_score_retained_not_counted_as_draw(self):
        self.write('Libertadores_Matches.csv', [dict(datetime='NA', home_team='A', away_team='B',
                    home_goal='-', away_goal='-', season='NA', stage='final')])
        g = SoccerGraph(self.root)
        self.assertEqual(g.matches()['total'], 1)
        self.assertIsNone(g.matches()['items'][0]['date'])
        self.assertEqual(g.team_stats('A')['scheduled'], 1)
        self.assertEqual(g.team_stats('A')['draws'], 0)
        self.assertEqual(g.matches({'start_date': '2000-01-01'})['total'], 0)

    def test_invalid_filters_and_pagination(self):
        g = self.load_fixture()
        for filters in ({'start_date': 'bad'}, {'start_date': '2024-01-01', 'end_date': '2020-01-01'},
                        {'venue': 'neutral'}, {'venue': 'home'}, {'opponent': 'A'},
                        {'team': 'A', 'opponent': 'A'}, {'source': 'unknown'}):
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                g.matches(filters)
        for limit in (0, -1, 1001, True):
            with self.assertRaises(ValueError):
                g.matches(limit=limit)
        self.assertEqual(g.matches(limit=1)['next_offset'], 1)
        self.assertEqual(g.matches(limit=1, offset=3)['next_offset'], None)
        self.assertEqual(g.matches({'team': 'missing'})['items'], [])


class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = SoccerGraph()

    def test_all_six_datasets_fully_accounted_for(self):
        c = self.graph.coverage()
        counts = {'Brasileirao_Matches.csv': 4180, 'Brazilian_Cup_Matches.csv': 1337,
                  'Libertadores_Matches.csv': 1255, 'BR-Football-Dataset.csv': 10296,
                  'novo_campeonato_brasileiro.csv': 6886, 'fifa_data.csv': 18207}
        self.assertEqual({n: s['rows'] for n, s in c['sources'].items()}, counts)
        self.assertEqual(c['players'], 18207)
        self.assertEqual(c['rejected_rows'], [])
        self.assertEqual(c['matches'] + c['duplicates_merged'], sum(counts.values())-18207)
        for source in set(SOURCES)-{'fifa_data.csv'}:
            self.assertGreater(self.graph.matches({'source': source})['total'], 0)

    def test_2019_standings_do_not_double_count_sources(self):
        r = self.graph.standings('Serie A', 2019)
        self.assertEqual(r['played_matches'], 380)
        self.assertTrue(r['complete_double_round_robin'])
        self.assertEqual([(t['team'], t['points']) for t in r['table'][:3]],
                         [('Flamengo', 90), ('Santos', 74), ('Palmeiras', 74)])
        self.assertEqual(r['table'][0]['matches'], 38)
        self.assertEqual(sum(t['goals_for'] for t in r['table']), sum(t['goals_against'] for t in r['table']))

    def test_all_27_natural_language_examples_have_executable_tool_answers(self):
        self.assertGreaterEqual(len(SAMPLE_QUERIES), 20)
        server = MCPServer(self.graph)
        initialize(server)
        for i, (question, name, args) in enumerate(SAMPLE_QUERIES):
            with self.subTest(question=question):
                result = server.handle({'jsonrpc': '2.0', 'id': i+10, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}})
                self.assertNotIn('error', result)
                self.assertFalse(result['result']['isError'])
                self.assertTrue(result['result']['structuredContent'])

    def test_match_criteria_and_derbies(self):
        r = self.graph.matches({'team': 'Palmeiras-SP', 'venue': 'away', 'competition': 'Serie A', 'season': 2023}, 1000)
        self.assertTrue(r['items'])
        for m in r['items']:
            self.assertEqual(m['away_team'], 'Palmeiras')
            self.assertEqual(m['season'], 2023)
            self.assertEqual(m['competition'], 'Brasileirão Série A')
        d = self.graph.matches({'derbies': True, 'season': 2023})
        self.assertGreater(d['total'], 0)
        h = self.graph.head_to_head('Flamengo', 'Fluminense', limit=1000)
        self.assertEqual(h['matches']['total'], h['record']['matches'])
        self.assertEqual(h['latest']['date'], max(m['date'] for m in h['matches']['items']))

    def test_player_filters_and_sorting(self):
        r = self.graph.players(nationality='Brazilian', limit=1000)
        with (DATA_DIR / 'fifa_data.csv').open() as f:
            expected = sum(row['Nationality'] == 'Brazil' for row in csv.DictReader(f))
        self.assertEqual(r['total'], expected)
        self.assertTrue(all(p['nationality'] == 'Brazil' for p in r['items']))
        self.assertEqual([p['overall'] for p in r['items']], sorted([p['overall'] for p in r['items']], reverse=True))
        self.assertTrue(self.graph.players(name='Neymar')['items'])
        self.assertEqual(self.graph.players(name='No such player xyz')['total'], 0)
        p = self.graph.players(club='Santos FC', position='forward')
        self.assertTrue(p['items'])
        self.assertTrue(all(p['club'] == 'Santos' for p in p['items']))
        self.assertEqual(self.graph.players(club='Sao Paulo FC')['total'], 0)

    def test_real_cross_file_player_club_and_match_relationships(self):
        info = self.graph.team_info('Santos FC', 2019)
        self.assertGreater(info['players']['total'], 0)
        self.assertGreater(info['stats']['matches'], 0)
        self.assertIn('Brasileirão Série A', info['competitions'])
        player = info['players']['items'][0]
        links = self.graph.graph(player['id'])['edges']['items']
        self.assertIn({'source': player['id'], 'target': 'team:santos', 'relation': 'PLAYS_FOR_SNAPSHOT'}, links)

    def test_finals_not_semifinals_and_missing_bracket_scorers_honest(self):
        r = self.graph.matches({'competition': 'Copa do Brasil', 'stage': 'final'}, 1000)
        self.assertTrue(r['items'])
        self.assertTrue(all(m['stage'] == 'final' and 'stage_note' in m for m in r['items']))
        c = self.graph.competition_info('Libertadores', 2018)
        self.assertIn('final', c['stages'])
        self.assertIsNone(c['top_scorers'])
        self.assertIsNone(c['bracket_advancement'])
        with self.assertRaises(ValueError):
            self.graph.standings('Copa do Brasil', 2018)

    def test_simple_and_aggregate_performance_targets(self):
        start = time.perf_counter()
        self.graph.matches({'team': 'Flamengo'})
        self.assertLess(time.perf_counter()-start, 2)
        start = time.perf_counter()
        self.graph.players(name='Neymar')
        self.assertLess(time.perf_counter()-start, 2)
        start = time.perf_counter()
        self.graph.analysis()
        self.assertLess(time.perf_counter()-start, 5)
        start = time.perf_counter()
        self.graph.standings('Serie A', 2019)
        self.assertLess(time.perf_counter()-start, 5)


def initialize(server, version='2025-06-18'):
    r = server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
        'protocolVersion': version, 'capabilities': {}, 'clientInfo': {'name': 'tests', 'version': '1.0'}}})
    server.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    return r


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = SoccerGraph()

    def setUp(self):
        self.server = MCPServer(self.graph)

    def call(self, method, params=None, id_=2):
        return self.server.handle({'jsonrpc': '2.0', 'id': id_, 'method': method, 'params': params or {}})

    def test_handshake_tools_and_resources(self):
        self.assertIn('error', self.call('tools/list'))
        r = initialize(self.server)
        self.assertEqual(r['result']['protocolVersion'], '2025-06-18')
        t = self.call('tools/list')['result']['tools']
        self.assertEqual({x['name'] for x in t}, set(TOOLS))
        self.assertTrue(all(x['inputSchema']['type'] == 'object' for x in t))
        self.assertEqual(self.call('ping')['result'], {})
        r = self.call('resources/read', {'uri': 'soccer://coverage'})
        self.assertIn('sources', json.loads(r['result']['contents'][0]['text']))
        self.assertEqual(len(self.call('resources/list')['result']['resources']), 2)

    def test_protocol_negotiation_and_legacy_response(self):
        self.assertEqual(initialize(self.server, 'future')['result']['protocolVersion'], '2025-06-18')
        initialize(self.server, '2024-11-05')
        r = self.call('tools/call', {'name': 'coverage'})['result']
        self.assertNotIn('structuredContent', r)
        self.assertIn('sources', json.loads(r['content'][0]['text']))

    def test_notifications_no_response_and_errors_do_not_break_server(self):
        initialize(self.server)
        self.assertIsNone(self.server.handle({'jsonrpc': '2.0', 'method': 'notifications/cancelled', 'params': {'requestId': 3}}))
        self.assertEqual(self.server.handle([])['error']['code'], -32600)
        self.assertEqual(self.call('missing')['error']['code'], -32601)
        for params in ({'name': 'missing'}, {'name': 'players', 'arguments': {'limit': True}},
                       {'name': 'team_stats', 'arguments': {}},
                       {'name': 'matches', 'arguments': {'filters': {'drop': 'tables'}}},
                       {'name': 'matches', 'arguments': {'filters': {'season': '2023'}}}):
            with self.subTest(params=params):
                self.assertEqual(self.call('tools/call', params)['error']['code'], -32602)
        r = self.call('tools/call', {'name': 'matches', 'arguments': {'filters': {'start_date': 'wrong'}}})
        self.assertTrue(r['result']['isError'])
        self.assertIn('result', self.call('tools/call', {'name': 'coverage'}))

    def test_invalid_json_and_line_delimited_output(self):
        output = io.StringIO()
        self.server.run(io.StringIO('bad json\n' + json.dumps({'jsonrpc': '2.0', 'id': 7, 'method': 'ping'})+'\n'), output)
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(rows[0]['error']['code'], -32700)
        self.assertEqual(rows[1]['id'], 7)

    def test_real_stdio_subprocess_from_different_working_directory(self):
        requests = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'smoke', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'players', 'arguments': {'name': 'Neymar'}}}]
        result = subprocess.run([sys.executable, str(Path(__file__).parent / 'server.py')],
                                input='\n'.join(map(json.dumps, requests))+'\n', text=True,
                                capture_output=True, cwd=tempfile.gettempdir(), timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertIn('Neymar', rows[1]['result']['structuredContent']['items'][0]['name'])


if __name__ == '__main__':
    unittest.main()
