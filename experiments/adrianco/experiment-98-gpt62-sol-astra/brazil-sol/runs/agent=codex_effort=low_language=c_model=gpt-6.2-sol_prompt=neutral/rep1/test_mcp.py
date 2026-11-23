"""Given the bundled data, exercise questions through the public MCP interface."""

import json
from pathlib import Path
import select
import subprocess
import time
import unittest


ROOT = Path(__file__).resolve().parent
EXPECTED_ROWS = {
    "Brasileirao_Matches.csv": 4180,
    "Brazilian_Cup_Matches.csv": 1337,
    "Libertadores_Matches.csv": 1255,
    "novo_campeonato_brasileiro.csv": 6886,
    "BR-Football-Dataset.csv": 10296,
    "fifa_data.csv": 18207,
}


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen(
            [str(ROOT / "soccer-mcp"), str(ROOT / "data/kaggle")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        cls.next_id = 0
        cls.initialization = cls.rpc("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "integration-tests", "version": "1"},
        })
        cls.server.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        cls.server.stdin.flush()

    @classmethod
    def tearDownClass(cls):
        cls.server.stdin.close()
        code = cls.server.wait(timeout=5)
        stderr = cls.server.stderr.read()
        cls.server.stdout.close()
        cls.server.stderr.close()
        if code or stderr:
            raise AssertionError(f"Server exit {code}: {stderr}")

    @classmethod
    def exchange(cls, line):
        cls.server.stdin.write(line + "\n")
        cls.server.stdin.flush()
        if not select.select([cls.server.stdout], [], [], 5)[0]:
            raise AssertionError("Server did not reply within 5 seconds")
        response = cls.server.stdout.readline()
        if not response:
            raise AssertionError("Server closed stdout without replying")
        return json.loads(response)

    @classmethod
    def rpc(cls, method, params=None):
        cls.next_id += 1
        message = {"jsonrpc": "2.0", "id": cls.next_id, "method": method}
        if params is not None:
            message["params"] = params
        response = cls.exchange(json.dumps(message, ensure_ascii=False))
        if response["id"] != cls.next_id or response["jsonrpc"] != "2.0":
            raise AssertionError(f"Incorrect RPC response: {response}")
        return response

    def query(self, tool, budget=2, **arguments):
        start = time.monotonic()
        response = self.rpc("tools/call", {"name": tool, "arguments": arguments})
        self.assertLess(time.monotonic() - start, budget)
        result = response["result"]
        self.assertFalse(result.get("isError"), result)
        self.assertEqual(result["content"][0]["type"], "text")
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
        return result["structuredContent"]

    def test_tools_are_discoverable_by_an_mcp_client(self):
        self.assertEqual(self.initialization["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", self.initialization["result"]["capabilities"])
        tools = {t["name"]: t["inputSchema"] for t in self.rpc("tools/list")["result"]["tools"]}
        self.assertEqual(set(tools), {
            "search_matches", "team_stats", "standings", "search_players",
            "competition_stats", "club_profile", "top_scorers", "data_coverage",
        })
        self.assertEqual(tools["standings"]["required"], ["season"])
        self.assertEqual(self.rpc("ping")["result"], {})

    def test_all_six_sources_are_loaded_and_queryable(self):
        coverage = self.query("data_coverage")
        self.assertEqual(coverage["source_rows"], EXPECTED_ROWS)
        self.assertLess(coverage["combined_matches"], sum(list(EXPECTED_ROWS.values())[:-1]))
        for source, count in EXPECTED_ROWS.items():
            with self.subTest(source=source):
                if source == "fifa_data.csv":
                    self.assertEqual(self.query("search_players", limit=1)["total"], count)
                else:
                    page = self.query("search_matches", source=source, limit=1)
                    self.assertEqual(page["total"], count)
                    self.assertEqual(page["matches"][0]["sources"], [source])

    def test_flamengo_fluminense_match_list_and_head_to_head(self):
        result = self.query("search_matches", team="Flamengo-RJ", opponent="Fluminense", limit=100)
        self.assertGreater(result["total"], 20)
        for match in result["matches"]:
            self.assertEqual({match["home_team"], match["away_team"]}, {"Flamengo", "Fluminense"})
            self.assertRegex(match["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIsInstance(match["home_goals"], int)
            self.assertIsInstance(match["away_goals"], int)
            self.assertTrue(match["competition"])
        record = result["head_to_head"]
        self.assertEqual(record["matches"], record["wins"] + record["draws"] + record["opponent_wins"])

    def test_latest_flamengo_corinthians_score(self):
        match = self.query("search_matches", team="Flamengo", opponent="Corinthians", limit=1)["matches"][0]
        self.assertEqual((match["date"], match["home_team"], match["away_team"]),
                         ("2023-10-08", "Corinthians", "Flamengo"))
        self.assertEqual((match["home_goals"], match["away_goals"]), (1, 1))

    def test_palmeiras_matches_in_2023(self):
        result = self.query("search_matches", team="Sociedade Esportiva Palmeiras", season=2023, limit=2)
        self.assertGreater(result["total"], 37)
        self.assertTrue(all(m["season"] == 2023 for m in result["matches"]))
        next_page = self.query("search_matches", team="Palmeiras-SP", season=2023,
                               limit=2, offset=result["next_offset"])
        self.assertNotEqual(result["matches"], next_page["matches"])

    def test_brazilian_date_range_and_historical_stadium(self):
        result = self.query("search_matches", date_from="29/03/2003", date_to="2003-03-29",
                            team="Guarani", side="home")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["matches"][0]["stadium"], "Brinco de Ouro")
        self.assertEqual(result["matches"][0]["historical_id"], "2003.01.0001")

    def test_copa_do_brasil_finals_include_both_legs(self):
        result = self.query("search_matches", competition="Copa do Brasil", stage="finals", limit=100)
        self.assertEqual(result["total"], 24)
        self.assertEqual({m["stage"] for m in result["matches"]}, {"final"})
        for year in range(2012, 2024):
            self.assertEqual(sum(m["season"] == year for m in result["matches"]), 2)

    def test_libertadores_knockout_bracket_in_2018(self):
        result = self.query("search_matches", competition="Libertadores", season=2018,
                            stage="knockout", sort="earliest", limit=35)
        self.assertEqual(result["total"], 30)
        for stage, count in (("round of 16", 16), ("quarterfinals", 8),
                             ("semifinals", 4), ("final", 2)):
            self.assertEqual(sum(m["stage"] == stage for m in result["matches"]), count)

    def test_2023_derbies(self):
        result = self.query("search_matches", season=2023, derbies_only=True, limit=500)
        self.assertGreater(result["total"], 10)
        self.assertTrue(any(
            {m["home_team"], m["away_team"]} == {"Flamengo", "Fluminense"}
            for m in result["matches"]
        ))

    def test_corinthians_home_record_in_2022(self):
        result = self.query("team_stats", team="Sport Club Corinthians Paulista",
                            season=2022, side="home", competition="Serie A", budget=5)
        self.assertEqual([result[k] for k in ("matches", "wins", "draws", "losses",
                                              "goals_for", "goals_against")],
                         [19, 12, 4, 3, 24, 11])
        self.assertAlmostEqual(result["win_rate"], 1200 / 19)
        self.assertEqual(result["away"]["matches"], 0)

    def test_team_with_most_goals_in_serie_a_2023(self):
        rows = self.query("team_stats", competition="Serie A", season=2023,
                          sort="goals", limit=20, budget=5)["teams"]
        self.assertEqual(len(rows), 20)
        self.assertEqual([r["goals_for"] for r in rows],
                         sorted((r["goals_for"] for r in rows), reverse=True))
        season = self.query("competition_stats", competition="Serie A", season=2023, budget=5)
        self.assertEqual(sum(r["goals_for"] for r in rows), season["goals"])

    def test_compare_palmeiras_and_santos(self):
        a = self.query("team_stats", team="Palmeiras", opponent="Santos", budget=5)
        b = self.query("team_stats", team="Santos-SP", opponent="Palmeiras-SP", budget=5)
        self.assertGreater(a["matches"], 30)
        self.assertEqual((a["wins"], a["losses"], a["draws"], a["goals_for"]),
                         (b["losses"], b["wins"], b["draws"], b["goals_against"]))

    def test_palmeiras_competition_history(self):
        result = self.query("team_stats", team="Palmeiras", budget=5)
        self.assertTrue({"Copa Libertadores", "Copa do Brasil", "Brasileirão Série A"}
                        <= {r["competition"] for r in result["competitions"]})
        self.assertEqual(sum(r["matches"] for r in result["competitions"]), result["matches"])

    def test_2019_title_and_final_table(self):
        result = self.query("standings", season=2019, budget=5)
        self.assertTrue(result["complete"])
        self.assertEqual(result["champion"], "Flamengo")
        self.assertEqual(result["fixture_count"], 380)
        self.assertEqual([r["points"] for r in result["teams"][:3]], [90, 74, 74])
        self.assertEqual({r["matches"] for r in result["teams"]}, {38})

    def test_2020_relegation_candidates(self):
        result = self.query("standings", season=2020, budget=5)
        self.assertEqual(result["relegation_candidates"],
                         ["Vasco da Gama", "Goiás", "Coritiba", "Botafogo"])

    def test_2023_standings_flag_partial_coverage(self):
        result = self.query("standings", season=2023, budget=5)
        self.assertFalse(result["complete"])
        self.assertEqual((result["fixture_count"], result["expected_matches"]), (377, 380))
        self.assertNotIn("champion", result)

    def test_brazilian_players_sorted_by_rating(self):
        result = self.query("search_players", nationality="Brazilian", limit=20)
        self.assertGreater(result["total"], 500)
        self.assertEqual(result["players"][0]["Name"], "Neymar Jr")
        self.assertEqual(result["players"][0]["Overall"], 92)
        self.assertTrue(all(p["Nationality"] == "Brazil" for p in result["players"]))
        self.assertEqual([p["Overall"] for p in result["players"]],
                         sorted((p["Overall"] for p in result["players"]), reverse=True))

    def test_player_lookup_returns_attributes(self):
        player = self.query("search_players", name="Néymar")["players"][0]
        self.assertEqual(player["Position"], "LW")
        self.assertGreater(player["Dribbling"], 90)
        self.assertIn("Height", player)
        self.assertIn("Jersey Number", player)

    def test_missing_snapshot_roster_and_player(self):
        for args in ({"club": "Flamengo"}, {"club": "São Paulo FC", "position": "forwards"},
                     {"name": "Gabriel Barbosa"}):
            with self.subTest(args=args):
                self.assertEqual(self.query("search_players", **args)["total"], 0)

    def test_forward_positions_and_brazilian_club_ratings(self):
        result = self.query("search_players", club="Gremio", position="forwards",
                            nationality="Brazil", brazilian_clubs_only=True)
        self.assertGreater(result["total"], 0)
        self.assertTrue(all(p["Position"] in {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
                            for p in result["players"]))
        group, = result["club_ratings"]
        self.assertEqual(group["club"], "Grêmio")
        self.assertAlmostEqual(group["average_overall"],
                               sum(p["Overall"] for p in result["players"]) / result["total"])

    def test_cross_file_club_profile(self):
        result = self.query("club_profile", team="Grêmio-RS", season=2018, limit=2, budget=5)
        self.assertEqual(result["team"], "Grêmio")
        self.assertGreater(result["roster"]["total"], 0)
        self.assertGreater(result["match_history"]["total"], 38)
        self.assertEqual(result["record"]["fixtures"], result["match_history"]["total"])

    def test_average_goals_and_home_win_rate(self):
        result = self.query("competition_stats", competition="Brasileirão", budget=5)
        self.assertGreater(result["matches"], 8000)
        self.assertAlmostEqual(result["goals_per_match"], result["goals"] / result["matches"])
        self.assertAlmostEqual(result["home_win_rate"], 100 * result["home_wins"] / result["matches"])
        self.assertEqual(result["matches"], result["home_wins"] + result["away_wins"] + result["draws"])

    def test_rank_home_and_away_records(self):
        for side in ("home", "away"):
            with self.subTest(side=side):
                result = self.query("team_stats", competition="Serie A", season=2019,
                                    side=side, sort="win_rate", min_matches=10, budget=5)
                self.assertEqual(result["total"], 20)
                values = [r["win_rate"] for r in result["teams"]]
                self.assertEqual(values, sorted(values, reverse=True))
                self.assertEqual({r["matches"] for r in result["teams"]}, {19})

    def test_biggest_wins_are_sorted_by_margin(self):
        result = self.query("search_matches", sort="margin", limit=20)
        margins = [m["margin"] for m in result["matches"]]
        self.assertEqual(margins, sorted(margins, reverse=True))
        self.assertGreaterEqual(margins[0], 8)

    def test_compare_palmeiras_across_two_seasons(self):
        result = self.query("competition_stats", competition="Serie A", team="Palmeiras",
                            season_from=2018, season_to=2019, budget=5)
        self.assertEqual([r["season"] for r in result["seasons"]], [2018, 2019])
        self.assertEqual([r["team_record"]["matches"] for r in result["seasons"]], [38, 38])
        self.assertEqual([r["team_record"]["points"] for r in result["seasons"]], [80, 74])

    def test_combined_matches_provide_extended_stats_and_provenance(self):
        result = self.query("search_matches", competition="Serie A", season=2019,
                            team="Flamengo", opponent="Santos", side="home")
        self.assertEqual(result["total"], 1)
        match = result["matches"][0]
        self.assertEqual(set(match["sources"]), {
            "Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv",
        })
        self.assertIn("home_shots", match["statistics"])
        self.assertTrue(match["stadium"])

    def test_unscored_fixtures_are_excluded_from_aggregates(self):
        args = {"season": 2022, "source": "Brasileirao_Matches.csv", "team": "Corinthians"}
        matches = self.query("search_matches", **args, limit=38)
        self.assertTrue(any(m["home_goals"] is None for m in matches["matches"]))
        summary = self.query("team_stats", **args, budget=5)
        self.assertEqual(summary["fixtures"], 38)
        self.assertLess(summary["matches"], 38)

    def test_confusable_clubs_remain_distinct(self):
        result = self.query("search_matches", team="Botafogo-PB", limit=100)
        self.assertGreater(result["total"], 0)
        self.assertTrue(all("botafogo pb" in m["home_team"].lower().replace("-", " ") or
                            "botafogo pb" in m["away_team"].lower().replace("-", " ")
                            for m in result["matches"]))

    def test_top_scorers_report_missing_goal_attribution(self):
        result = self.query("top_scorers", competition="Serie A", season=2019)
        self.assertFalse(result["available"])
        self.assertIn("individual players", result["reason"])

    def test_invalid_requests_leave_the_server_usable(self):
        self.assertEqual(self.exchange("{")["error"]["code"], -32700)
        self.assertEqual(self.rpc("missing")["error"]["code"], -32601)
        self.assertEqual(self.rpc("tools/call", {"name": "missing"})["error"]["code"], -32602)
        for args in ({"limit": 501}, {"date_from": "2023-02-29"}, {"opponent": "Santos"}):
            with self.subTest(args=args):
                result = self.rpc("tools/call", {
                    "name": "search_matches", "arguments": args,
                })["result"]
                self.assertTrue(result["isError"])
        self.assertEqual(self.rpc("ping")["result"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
