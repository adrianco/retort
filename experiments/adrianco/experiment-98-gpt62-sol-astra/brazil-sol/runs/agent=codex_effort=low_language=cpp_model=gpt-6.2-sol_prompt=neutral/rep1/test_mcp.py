"""End-to-end soccer scenarios through the MCP stdio transport."""
import json
import math
import subprocess
import sys
import time
import unittest


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Given the server starts with the six bundled datasets.
        started = time.perf_counter()
        cls.server = subprocess.Popen(
            [sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding="utf-8"
        )
        cls.addClassCleanup(cls.stop_server)
        cls.request_id = 0
        initialized = cls.request("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "soccer-scenarios", "version": "1"},
        })["result"]
        cls.startup_time = time.perf_counter() - started
        cls.initialized = initialized
        cls.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    @classmethod
    def stop_server(cls):
        cls.server.stdin.close()
        try:
            cls.server.wait(timeout=3)
        finally:
            if cls.server.poll() is None:
                cls.server.kill()
                cls.server.wait()
            cls.server.stdout.close()
        if cls.server.returncode:
            raise AssertionError(f"Server exited with code {cls.server.returncode}")

    @classmethod
    def send(cls, message):
        cls.server.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        cls.server.stdin.flush()

    @classmethod
    def request(cls, method, params=None):
        cls.request_id += 1
        request = {"jsonrpc": "2.0", "id": cls.request_id, "method": method}
        if params is not None:
            request["params"] = params
        cls.send(request)
        response = json.loads(cls.server.stdout.readline())
        if (response.get("id"), response.get("jsonrpc")) != (cls.request_id, "2.0"):
            raise AssertionError(f"Unexpected response envelope: {response}")
        return response

    def tool(self, tool, *, seconds=2, **arguments):
        started = time.perf_counter()
        result = self.request("tools/call", {"name": tool, "arguments": arguments})["result"]
        self.assertLess(time.perf_counter() - started, seconds)
        self.assertFalse(result["isError"], result)
        self.assertEqual(result["content"][0]["type"], "text")
        structured = result["structuredContent"]
        self.assertEqual(json.loads(result["content"][0]["text"]), structured)
        return structured

    def test_client_discovers_tools_and_recovers_from_errors(self):
        self.assertLess(self.startup_time, 2)
        self.assertEqual(self.initialized["protocolVersion"], "2025-11-25")
        self.assertIn("tools", self.initialized["capabilities"])
        tools = self.request("tools/list")["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, {
            "dataset_coverage", "search_matches", "search_players", "team_stats",
            "head_to_head", "team_profile", "competition_data", "analyze_matches",
        })
        for tool in tools:
            self.assertEqual(tool["inputSchema"]["type"], "object")
        self.server.stdin.write("{\n")
        self.server.stdin.flush()
        self.assertEqual(json.loads(self.server.stdout.readline())["error"]["code"], -32700)
        self.assertEqual(self.request("unknown/method")["error"]["code"], -32601)
        self.assertEqual(self.request("tools/call", {"name": "unknown"})["error"]["code"], -32602)
        for args in ({"season": "2023"}, {"date_from": "2023-02-29"}, {"venue": "away"},
                     {"date_from": "2023-12-31", "date_to": "2023-01-01"}, {"limit": 0}):
            result = self.request("tools/call", {"name": "search_matches", "arguments": args})["result"]
            self.assertTrue(result["isError"], result)
        self.assertEqual(self.request("ping")["result"], {})

    def test_all_sources_are_queryable(self):
        expected = {
            "Brasileirao_Matches.csv": 4180, "Brazilian_Cup_Matches.csv": 1337,
            "Libertadores_Matches.csv": 1255, "BR-Football-Dataset.csv": 10296,
            "novo_campeonato_brasileiro.csv": 6886, "fifa_data.csv": 18207,
        }
        coverage = self.tool("dataset_coverage")
        self.assertEqual(coverage["source_rows"], expected)
        self.assertLess(coverage["unique_fixtures"], sum(expected.values()) - coverage["players"])
        for filename in expected.keys() - {"fifa_data.csv"}:
            with self.subTest(filename=filename):
                sample = self.tool("search_matches", source=filename, limit=1)["matches"][0]
                self.assertIn(filename, sample["sources"])
        self.assertEqual(self.tool("search_players", limit=1)["total"], 18207)

    def test_fla_flu_matches_and_pagination(self):
        # When I search for Flamengo and Fluminense.
        args = {"team": "Clube de Regatas do Flamengo", "opponent": "Fluminense-RJ"}
        first = self.tool("search_matches", **args, limit=3)
        second = self.tool("search_matches", **args, limit=3, offset=first["next_offset"])
        # Then the results are ordered and include both teams, dates, scores and competition.
        self.assertGreater(first["total"], 6)
        self.assertTrue({m["date"] for m in first["matches"]}.isdisjoint(
            m["date"] for m in second["matches"]
        ))
        for m in first["matches"] + second["matches"]:
            self.assertEqual({m["home_team"], m["away_team"]}, {"Flamengo", "Fluminense"})
            self.assertRegex(m["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(m["competition"])
            self.assertIsInstance(m["home_goal"], int)
            self.assertIsInstance(m["away_goal"], int)

    def test_palmeiras_2023_and_corinthians_home_record(self):
        season = self.tool("team_stats", team="Palmeiras-SP", season=2023, seconds=5)
        league = season["by_competition"]["Brasileirão Série A"]["overall"]
        self.assertEqual(league["played"], 37)
        self.assertEqual(league["played"], league["wins"] + league["draws"] + league["losses"])
        self.assertGreater(league["goals_for"], league["goals_against"])
        home = self.tool("team_stats", team="Sport Club Corinthians Paulista", season=2022,
                         venue="home", competition="Brasileirão", seconds=5)
        record = home["record"]["home"]
        self.assertEqual([record[k] for k in ("played", "wins", "draws", "losses",
                                               "goals_for", "goals_against")], [19, 12, 4, 3, 24, 11])
        self.assertEqual(home["record"]["away"]["played"], 0)

    def test_latest_score_head_to_head_and_derbies(self):
        latest = self.tool("search_matches", team="Flamengo", opponent="Corinthians", limit=1)["matches"][0]
        self.assertEqual((latest["date"], latest["home_goal"], latest["away_goal"]), ("2023-10-08", 1, 1))
        h2h = self.tool("head_to_head", team="Palmeiras", opponent="Santos-SP", limit=2, seconds=5)
        a, b = h2h["record"]["overall"], h2h["opponent_record"]["overall"]
        self.assertEqual((a["wins"], a["draws"], a["goals_for"]),
                         (b["losses"], b["draws"], b["goals_against"]))
        self.assertEqual(len(h2h["history"]["matches"]), 2)
        derbies = self.tool("search_matches", derbies=True, season=2023, limit=500)["matches"]
        self.assertTrue(any({m["home_team"], m["away_team"]} == {"Flamengo", "Fluminense"} for m in derbies))
        self.assertTrue(all(m["season"] == 2023 for m in derbies))
        self.assertTrue(all(m["home_team"] != "Flamengo" for m in
                           self.tool("search_matches", team="Flamengo-PI", limit=500)["matches"]))

    def test_brazilian_dates_and_merged_statistics(self):
        games = self.tool("search_matches", date_from="29/03/2003", date_to="2003-03-29 23:59:00",
                          competition="Serie A", team="Grêmio")["matches"]
        self.assertEqual(len(games), 1)
        self.assertEqual((games[0]["date"], games[0]["stadium"]), ("2003-03-29", "Arena da Baixada"))
        match = self.tool("search_matches", team="São Paulo FC", opponent="Flamengo",
                          competition="Copa do Brasil", season=2023, venue="home")["matches"][0]
        self.assertEqual(match["statistics"]["total_corners"], 6)
        games = self.tool("search_matches", competition="Serie A", season=2019,
                          team="Flamengo", limit=50)["matches"]
        self.assertEqual(len(games), 38)
        self.assertTrue(any(len(m["sources"]) == 3 and m["stadium"] and m["statistics"] for m in games))

    def test_player_ratings_filters_and_cross_file_profile(self):
        top = self.tool("search_players", nationality="Brazilian", limit=3, include_attributes=True)
        self.assertEqual(top["total"], 827)
        self.assertEqual(top["players"][0]["name"], "Neymar Jr")
        self.assertEqual(top["players"][0]["overall"], 92)
        self.assertIn("Dribbling", top["players"][0]["attributes"])
        self.assertEqual(self.tool("search_players", name="Neymar")["players"][0]["id"], 190871)
        self.assertEqual(self.tool("search_players", club="Flamengo")["total"], 0)
        self.assertEqual(self.tool("search_players", name="Gabriel Barbosa")["total"], 0)
        forwards = self.tool("search_players", club="Santos FC", position="forwards")["players"]
        self.assertTrue(forwards)
        self.assertTrue(all(p["club"] == "Santos" and p["position"] in
                            {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"} for p in forwards))
        clubs = self.tool("search_players", nationality="Brazil", brazilian_clubs_only=True,
                          group_by_club=True, limit=100)["clubs"]
        self.assertTrue(any(c["players"] == 20 and 0 < c["average_overall"] < 100 for c in clubs))
        self.assertFalse(any(c["club"] == "Paris Saint-Germain" for c in clubs))
        profile = self.tool("team_profile", team="Gre\u0302mio-RS", season=2019, limit=1)
        self.assertEqual(profile["squad"]["players"][0]["club"], "Grêmio")
        self.assertEqual(len(profile["by_competition"]), 3)
        self.assertEqual(profile["history"]["matches"][0]["season"], 2019)

    def test_competition_tables_brackets_and_schedules(self):
        def competition(name, season, **args):
            return self.tool("competition_data", competition=name, season=season, seconds=5, **args)

        table = competition("Brasileirão Série A", 2019)
        self.assertTrue(table["complete"])
        leader = table["standings"][0]
        self.assertEqual((leader["team"], leader["points"], leader["status"]), ("Flamengo", 90, "champion"))
        table = competition("Serie A", 2020)
        self.assertEqual({r["team"] for r in table["standings"] if r.get("status") == "relegated"},
                         {"Vasco da Gama", "Goias", "Coritiba", "Botafogo"})
        incomplete = competition("Serie A", 2023)
        self.assertFalse(incomplete["complete"])
        self.assertEqual(sum(r["played"] for r in incomplete["standings"]) // 2, 377)
        self.assertFalse(any("status" in r for r in incomplete["standings"]))
        schedule = competition("Serie A", 2022, mode="schedule", round="38", limit=20)
        self.assertEqual(schedule["total"], 10)
        bracket = competition("Libertadores", 2018, mode="bracket", limit=50)["matches"]
        self.assertEqual(len(bracket), 30)
        self.assertEqual(sum(m["stage"] == "final" for m in bracket), 2)
        groups = competition("Libertadores", 2018, stage="group stage")["groups"]
        self.assertEqual(len(groups), 8)
        self.assertTrue(all(g["complete"] for g in groups))
        finals = self.tool("search_matches", competition="Copa do Brasil", stage="final",
                           limit=100)["matches"]
        self.assertEqual(len(finals), 24)
        self.assertEqual(sum(m["season"] == 2023 for m in finals), 2)
        self.assertFalse(competition("Libertadores", 2018, mode="top_scorers")["available"])

    def test_analysis_and_unscored_matches(self):
        def analyze(**args):
            return self.tool("analyze_matches", seconds=5, **args)

        summary = analyze(competition="Brasileirão")
        self.assertGreater(summary["played"], 7000)
        self.assertEqual(summary["played"], summary["home_wins"] + summary["away_wins"] + summary["draws"])
        self.assertTrue(math.isclose(summary["goals_per_match"], summary["goals"] / summary["played"]))
        wins = analyze(mode="biggest_wins", limit=5)["matches"]
        margins = [m["winning_margin"] for m in wins]
        self.assertEqual(margins, sorted(margins, reverse=True))
        self.assertGreaterEqual(margins[0], 8)
        trends = analyze(mode="season_trends", seasons=[2019, 2018], team="Palmeiras",
                         competition="Serie A")["seasons"]
        self.assertEqual([r["season"] for r in trends], [2018, 2019])
        self.assertTrue(all(r["team_record"]["overall"]["played"] == 38 for r in trends))
        for venue in ("home", "away"):
            ranks = analyze(mode="team_rankings", rank_venue=venue, min_matches=19,
                            competition="Serie A", season=2019)["teams"]
            self.assertEqual(len(ranks), 20)
            self.assertEqual(sorted(ranks, key=lambda r: -r["win_rate_percent"]), ranks)
        ranks = analyze(mode="team_rankings", metric="goals_for", competition="Serie A",
                        season=2023, limit=1)["teams"]
        self.assertGreater(ranks[0]["goals_for"], 50)
        unscored = self.tool("search_matches", status="unscored", limit=1)
        self.assertGreater(unscored["total"], 0)
        sample = unscored["matches"][0]
        self.assertTrue(sample["home_goal"] is None or sample["away_goal"] is None)
        self.assertIsNone(analyze(status="unscored")["goals_per_match"])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
