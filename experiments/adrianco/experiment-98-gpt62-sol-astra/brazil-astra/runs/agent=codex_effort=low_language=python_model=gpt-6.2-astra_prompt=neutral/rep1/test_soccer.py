"""Executable scenarios against the six distributed CSVs and the MCP transport."""
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

from soccer import Graph, FILES, LEAGUE, CUP, LIB, club


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = Graph()

    def test_given_all_match_sources_when_filtered_then_each_is_represented(self):
        for source in FILES:
            with self.subTest(source=source):
                row = self.graph.find_matches(source=source, limit=1)["results"][0]
                self.assertIn(source, row["sources"])
        self.assertEqual(self.graph.find_players()["total"], 18207)

    def test_given_derby_rivals_when_searching_then_both_venues_and_scores_are_available(self):
        criteria = dict(team="Clube de Regatas do Flamengo", opponent="Fluminense-RJ", derby=True)
        matches = self.graph.find_matches(**criteria, limit=200)
        self.assertEqual({m["home"] for m in matches["results"]}, {"fluminense","flamengo"})
        for m in matches["results"]:
            self.assertTrue({"date", "competition", "home_goal", "away_goal"} <= m.keys())
        first = matches["results"][0]
        self.assertEqual(first, self.graph.find_matches(**criteria, start=first["date"],
                                                       end=first["date"])["results"][0])
        record = self.graph.statistics(**criteria)["results"][0]
        self.assertEqual(record["matches"], record["wins"] + record["draws"] + record["losses"])

    def test_given_overlapping_league_sources_when_ranked_then_fixtures_count_once(self):
        for y in range(2012, 2023):
            self.assertEqual(self.graph.find_matches(competition_name="Serie A",season=y)["total"], 380)
        table = self.graph.statistics(competition_name=LEAGUE, season=2019)
        champ = table["results"][0]
        self.assertEqual((champ["team"],champ["points"],champ["matches"]), ("flamengo",90,38))
        bottom = self.graph.statistics(competition_name=LEAGUE, season=2020)["results"][-4:]
        self.assertEqual({r["team"] for r in bottom}, {"botafogo","vasco","coritiba","goias"})

    def test_given_home_away_and_ranking_questions_when_aggregated_then_totals_agree(self):
        filters = dict(team="Sport Club Corinthians Paulista", competition_name="serie a", season=2022)
        records = [self.graph.statistics(**filters, venue=v)["results"][0] for v in ("home","away","either")]
        for key in ("matches","wins","losses","draws","goals_for","goals_against"):
            self.assertEqual(records[0][key]+records[1][key], records[2][key])
        for key in ("goals_for","wins","win_rate"):
            rows = self.graph.statistics(season=2023,venue="away",rank_by=key)["results"]
            self.assertEqual([r[key] for r in rows],sorted((r[key] for r in rows), reverse=True))

    def test_given_knockout_queries_when_filtering_then_return_rounds_and_finals(self):
        finals = self.graph.find_matches(competition_name=CUP,stage="final",limit=100)
        self.assertEqual(finals["total"],24)
        bracket = self.graph.find_matches(competition_name=LIB,season=2018,stage="quarterfinals")
        self.assertEqual(bracket["total"],8)

    def test_given_a_fifa_club_when_joining_players_then_match_history_is_available(self):
        squad = self.graph.find_players(team="Grêmio",nationality="Brazilian",position="forwards",details=True)
        player = squad["results"][0]
        self.assertIn("Finishing",player)
        self.assertGreater(self.graph.find_matches(team=player["Club"])["total"],0)
        self.assertEqual(self.graph.find_players(name="Neymar",nationality="Brazil")["results"][0]["Name"],"Neymar Jr")
        self.assertNotEqual(club("Atlético-MG"),club("Atlético-PR"))
        self.assertNotEqual(club("Botafogo-PB"),club("Botafogo RJ"))

    def test_given_pagination_and_missing_results_when_querying_then_no_invented_scores(self):
        matches = self.graph.find_matches(team="Palmeiras",season=2023,limit=2)["results"]
        self.assertEqual(matches[1],self.graph.find_matches(team="Palmeiras",season=2023,offset=1)["results"][0])
        self.assertEqual(self.graph.find_players(name="unlisted name")["total"],0)
        fixture = next(m for m in self.graph.matches if m["home_goal"] is None)
        self.assertIsNone(fixture["away_goal"])
        wins = self.graph.find_matches(biggest_wins=True)["results"]
        margins = [abs(m["home_goal"]-m["away_goal"]) for m in wins]
        self.assertEqual(margins,sorted(margins,reverse=True))

    def test_given_loaded_graph_when_querying_then_latency_is_within_budget(self):
        start = time.perf_counter()
        self.graph.find_players(nationality="Brazil")
        self.assertLess(time.perf_counter()-start,2)
        start = time.perf_counter()
        self.graph.statistics()
        self.assertLess(time.perf_counter()-start,5)

    def test_given_stdio_client_when_discovering_and_calling_tools_then_session_survives_errors(self):
        messages = [("initialize",{"protocolVersion":"2025-06-18"}),("notifications/initialized",{}),
                    ("tools/list",{}),("tools/call",{"name":"statistics","arguments":{"season":"wrong"}}),
                    ("tools/call",{"name":"statistics","arguments":{"competition_name":"Serie A","season":2019}})]
        lines = [dict(jsonrpc="2.0",method=m,params=p,**({} if i==1 else {"id":i})) for i,(m,p) in enumerate(messages)]
        data = "\n".join(json.dumps(r) for r in lines)
        proc = subprocess.run([sys.executable,str(Path(__file__).with_name("server.py"))],input=data,text=True,
                              capture_output=True,check=True,timeout=10)
        init, catalog, bad, good = map(json.loads, proc.stdout.splitlines())
        self.assertIn("tools",init["result"]["capabilities"])
        self.assertEqual(len(catalog["result"]["tools"]),3)
        self.assertTrue(bad["result"]["isError"])
        self.assertEqual(json.loads(good["result"]["content"][0]["text"])["matches"],380)


if __name__ == "__main__":
    unittest.main()
