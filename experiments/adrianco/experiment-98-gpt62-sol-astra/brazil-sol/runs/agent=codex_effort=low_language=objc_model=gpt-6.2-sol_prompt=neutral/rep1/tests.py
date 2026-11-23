"""Behavior tests through the same stdio MCP connection used by clients."""
import json
import os
import select
import subprocess
import sys
import time
import unittest

BINARY = os.path.abspath(sys.argv.pop(1))


class SoccerBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen(
            [BINARY], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            cwd=os.path.dirname(os.path.dirname(BINARY)),
        )
        cls.addClassCleanup(cls.stop_server)
        cls.request_id = 0
        cls.initialize = cls.rpc("initialize", {"protocolVersion": "2025-06-18"})
        cls.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    @classmethod
    def stop_server(cls):
        cls.process.stdin.close()
        try:
            status = cls.process.wait(timeout=5)
            if status:
                raise AssertionError(f"Server exited with status {status}")
        finally:
            if cls.process.poll() is None:
                cls.process.kill()
                cls.process.wait()
            cls.process.stdout.close()

    @classmethod
    def send(cls, message):
        cls.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        cls.process.stdin.flush()

    @classmethod
    def receive(cls, timeout=5):
        ready, _, _ = select.select([cls.process.stdout], [], [], timeout)
        if not ready:
            raise AssertionError(f"MCP response exceeded {timeout} seconds")
        line = cls.process.stdout.readline()
        if not line:
            raise AssertionError("Server closed stdout")
        return json.loads(line)

    @classmethod
    def rpc(cls, method, params=None, timeout=5):
        cls.request_id += 1
        cls.send({"jsonrpc": "2.0", "id": cls.request_id, "method": method, "params": params or {}})
        response = cls.receive(timeout)
        if response.get("id") != cls.request_id or response.get("jsonrpc") != "2.0":
            raise AssertionError(f"Unexpected MCP response: {response}")
        return response

    def query(self, tool_name, timeout=5, **args):
        response = self.rpc("tools/call", {"name": tool_name, "arguments": args}, timeout)
        result = response["result"]
        self.assertFalse(result["isError"], result["content"])
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
        return result["structuredContent"]

    def test_mcp_handshake_discovery_and_ping(self):
        result = self.initialize["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertIn("tools", result["capabilities"])
        tools = self.rpc("tools/list")["result"]["tools"]
        self.assertEqual({item["name"] for item in tools}, {
            "find_matches", "team_statistics", "competition_standings",
            "search_players", "club_profile", "dataset_coverage",
        })
        self.assertTrue(all(item["inputSchema"]["type"] == "object" for item in tools))
        self.assertEqual(self.rpc("ping")["result"], {})

    def test_source_files_are_loaded_and_individually_queryable(self):
        result = self.query("dataset_coverage", timeout=2)
        counts = {
            "Brasileirao_Matches.csv": 4180, "Brazilian_Cup_Matches.csv": 1337,
            "Libertadores_Matches.csv": 1255, "BR-Football-Dataset.csv": 10296,
            "novo_campeonato_brasileiro.csv": 6886, "fifa_data.csv": 18207,
        }
        self.assertEqual(result["rows_by_source"], counts)
        self.assertFalse(result["individual_match_scorers_available"])
        self.assertLess(result["unique_fixtures"], sum(counts.values()) - counts["fifa_data.csv"])
        for source, count in counts.items():
            with self.subTest(source=source):
                if source == "fifa_data.csv":
                    rows = self.query("search_players", timeout=2, limit=1)
                    self.assertEqual(rows["players"][0]["source"], source)
                else:
                    rows = self.query("find_matches", timeout=2, source=source, limit=1)
                    self.assertEqual(rows["matches"][0]["source"], source)
                self.assertEqual(rows["total"], count)

    def test_fla_flu_head_to_head_and_pagination(self):
        # Given loaded fixtures, when a rivalry is queried, both orientations count.
        args = {"team": "Flamengo-RJ", "opponent": "Fluminense Football Club", "limit": 2}
        first = self.query("find_matches", timeout=2, **args)
        second = self.query("find_matches", timeout=2, offset=first["next_offset"], **args)
        stats = first["head_to_head"]
        self.assertEqual(stats, second["head_to_head"])
        self.assertEqual(stats["wins"] + stats["losses"] + stats["draws"], stats["matches"])
        self.assertEqual(stats["wins"], stats["opponent_record"]["losses"])
        self.assertGreater(first["total"], 30)
        for match in first["matches"] + second["matches"]:
            self.assertEqual({match["home_id"], match["away_id"]}, {"flamengo", "fluminense"})
            self.assertTrue({"date", "home_goal", "away_goal", "competition"} <= match.keys())
        self.assertTrue(all(a["date"] >= b["date"] for a, b in zip(first["matches"], second["matches"])))

    def test_latest_flamengo_corinthians_score(self):
        results = self.query(
            "find_matches", timeout=2, team="Flamengo", opponent="Corinthians", limit=1
        )
        match = results["matches"][0]
        self.assertEqual((match["date"], match["home_goal"], match["away_goal"]), ("2023-10-08", 1, 1))

    def test_palmeiras_schedule_by_home_away_and_season(self):
        results = {}
        for side in ("home", "away", "either"):
            results[side] = self.query(
                "find_matches", timeout=2, team="Sociedade Esportiva Palmeiras", side=side,
                competition="Brasileirão", season=2023, limit=100,
            )
        self.assertEqual(results["either"]["total"], 37)
        self.assertEqual(results["home"]["total"] + results["away"]["total"], 37)
        for side in ("home", "away"):
            self.assertTrue(all(m[f"{side}_id"] == "palmeiras" for m in results[side]["matches"]))
        self.assertIn("statistics", results["either"]["matches"][0])

    def test_brazilian_date_range_and_historical_stadium(self):
        result = self.query("find_matches", timeout=2, competition="Serie A", team="Guarani",
                            **{"from": "29/03/2003", "to": "2003-03-29"})
        match, = result["matches"]
        self.assertEqual((match["date"], match["stadium"]), ("2003-03-29", "Brinco de Ouro"))
        self.assertEqual((match["home_goal"], match["away_goal"]), (4, 2))

    def test_cup_finals_and_libertadores_bracket(self):
        finals = self.query("find_matches", competition="Copa do Brasil", stage="finals", limit=100)
        self.assertEqual(finals["total"], 24)
        self.assertEqual([m["season"] for m in finals["matches"][:2]], [2023, 2023])
        self.assertEqual(sum(m["season"] == 2020 and m["date"].startswith("2021")
                             for m in finals["matches"]), 2)
        bracket = self.query("find_matches", competition="Libertadores", season=2018, stage="knockout", limit=100)
        self.assertEqual(bracket["total"], 30)
        self.assertEqual({m["stage"] for m in bracket["matches"]},
                         {"final", "semifinals", "quarterfinals", "round of 16"})

    def test_derbies_in_2023(self):
        result = self.query("find_matches", season=2023, derbies=True, limit=250)
        pairs = [{m["home_id"], m["away_id"]} for m in result["matches"]]
        self.assertIn({"flamengo", "fluminense"}, pairs)
        self.assertIn({"gremio", "internacional"}, pairs)
        self.assertNotIn({"flamengo", "gremio"}, pairs)

    def test_corinthians_home_and_palmeiras_season_records(self):
        home = self.query("team_statistics", team="Sport Club Corinthians Paulista",
                          side="home", season=2022, competition="Série A")
        self.assertEqual([home[k] for k in ("matches", "wins", "draws", "losses", "goals_for", "goals_against")],
                         [19, 12, 4, 3, 24, 11])
        self.assertAlmostEqual(home["win_rate"], 12 / 19)
        self.assertEqual(home["away"]["matches"], 0)
        season = self.query("team_statistics", team="Palmeiras", season=2023)
        self.assertGreater(season["matches"], 37)
        self.assertEqual(season["matches"], sum(season[k] for k in ("wins", "losses", "draws")))
        self.assertEqual(season["goals_for"] + season["goals_against"], season["total_goals"])

    def test_venue_rankings_and_biggest_wins(self):
        for side in ("home", "away"):
            with self.subTest(side=side):
                result = self.query("team_statistics", competition="Serie A", season=2019, side=side,
                                    group_by="team", sort="win_rate", min_matches=19, limit=20)
                rows = result["breakdown"]["groups"]
                self.assertEqual(len(rows), 20)
                self.assertTrue(all(row[side]["matches"] == 19 for row in rows))
                rates = [row["win_rate"] for row in rows]
                self.assertEqual(rates, sorted(rates, reverse=True))
        wins = self.query("find_matches", sort="margin", limit=10)["matches"]
        margins = [abs(m["home_goal"] - m["away_goal"]) for m in wins]
        self.assertEqual(margins, sorted(margins, reverse=True))
        self.assertGreaterEqual(margins[0], 8)

    def test_goals_per_match_and_2018_2019_trends(self):
        result = self.query("team_statistics", competition="Serie A", group_by="season",
                            **{"from": "2018-01-01", "to": "2019-12-31"})
        rows = result["breakdown"]["groups"]
        self.assertEqual([(r["season"], r["matches"]) for r in rows], [(2018, 380), (2019, 380)])
        self.assertEqual(result["total_goals"], sum(r["total_goals"] for r in rows))
        self.assertAlmostEqual(result["goals_per_match"], result["total_goals"] / 760)
        self.assertEqual(result["home_wins"] + result["away_wins"] + result["draws"], 760)

    def test_2019_champion_and_2020_relegation_positions(self):
        result = self.query("competition_standings", season=2019)
        self.assertTrue(result["complete"])
        self.assertEqual(result["first_place"], "Flamengo")
        self.assertEqual([(r["team"], r["points"]) for r in result["standings"][:3]],
                         [("Flamengo", 90), ("Santos", 74), ("Palmeiras", 74)])
        champion = result["standings"][0]
        self.assertEqual([champion[k] for k in ("wins", "draws", "losses")], [28, 6, 4])
        relegation = self.query("competition_standings", season=2020)["relegation_positions"]
        self.assertEqual({name.lower() for name in relegation}, {"vasco da gama", "goiás", "coritiba", "botafogo"})

    def test_partial_2023_table_and_most_goals(self):
        result = self.query("competition_standings", season=2023)
        self.assertFalse(result["complete"])
        self.assertEqual((result["completed_matches"], result["expected_matches"]), (377, 380))
        self.assertNotIn("first_place", result)
        ranking = self.query("team_statistics", competition="Serie A", season=2023,
                             group_by="team", sort="goals_for", limit=5)
        goals = [row["goals_for"] for row in ranking["breakdown"]["groups"]]
        self.assertEqual(goals, sorted(goals, reverse=True))

    def test_player_lookup_attributes_and_top_brazilians(self):
        player, = self.query("search_players", timeout=2, name="neymar jr")["players"]
        self.assertEqual((player["Name"], player["Overall"], player["Nationality"]), ("Neymar Jr", 92, "Brazil"))
        self.assertTrue({"Age", "Height", "Weight", "Position", "Club", "Finishing", "Dribbling"} <= player.keys())
        result = self.query("search_players", timeout=2, nationality="Brazilian", limit=5)
        self.assertGreater(result["total"], 500)
        self.assertEqual(result["players"][0]["Name"], "Neymar Jr")
        self.assertTrue(all(p["Nationality"] == "Brazil" for p in result["players"]))

    def test_club_roster_positions_and_domestic_player_summary(self):
        forwards = self.query("search_players", club="Santos FC", position="forwards")
        self.assertGreater(forwards["total"], 0)
        self.assertTrue(all(p["Club"] == "Santos" for p in forwards["players"]))
        self.assertTrue(all(p["Position"] in {"LS", "ST", "RS", "LW", "LF", "CF", "RF", "RW"}
                            for p in forwards["players"]))
        self.assertEqual(self.query("search_players", club="Flamengo")["total"], 0)
        clubs = self.query("search_players", nationality="Brasil", brazilian_club=True, group_by="club")
        self.assertIn("Santos", {row["club"] for row in clubs["clubs"]})
        self.assertTrue(all(0 < row["average_overall"] <= 100 for row in clubs["clubs"]))

    def test_club_profile_joins_roster_with_match_competitions(self):
        result = self.query("club_profile", team="Santos FC", season=2018, limit=25)
        self.assertGreater(result["roster"]["total"], 0)
        self.assertTrue(all(p["club_id"] == "santos" for p in result["roster"]["players"]))
        groups = result["match_record"]["breakdown"]["groups"]
        self.assertEqual({g["competition"] for g in groups},
                         {"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"})
        self.assertEqual(sum(g["matches"] for g in groups), result["match_record"]["matches"])

    def test_palmeiras_competitions_and_santos_head_to_head(self):
        competitions = self.query("team_statistics", team="Palmeiras", group_by="competition")
        self.assertTrue({"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"} <=
                        {g["competition"] for g in competitions["breakdown"]["groups"]})
        record = self.query("team_statistics", team="Palmeiras", opponent="Santos")
        reverse = self.query("team_statistics", team="Santos FC", opponent="Palmeiras-SP")
        self.assertGreater(record["matches"], 30)
        self.assertEqual(record["matches"], reverse["matches"])
        self.assertEqual(record["wins"], reverse["losses"])
        self.assertEqual(record["goals_for"], reverse["goals_against"])

    def test_conflicting_club_names_keep_their_state_identity(self):
        cup = {"competition": "Copa do Brasil", "source": "Brazilian_Cup_Matches.csv"}
        rio = self.query("find_matches", team="Botafogo-RJ", **cup)["matches"]
        paraiba = self.query("find_matches", team="Botafogo-PB", **cup)["matches"]
        self.assertTrue(rio and paraiba)
        self.assertTrue(all("botafogo" in (m["home_id"], m["away_id"]) for m in rio))
        self.assertTrue(all("botafogo pb" in (m["home_id"], m["away_id"]) for m in paraiba))

    def test_missing_player_has_an_empty_result(self):
        result = self.query("search_players", name="Gabriel Barbosa")
        self.assertEqual(result, {"total": 0, "players": []})

    def test_matches_with_missing_scores_are_excluded_from_aggregates(self):
        args = {"competition": "Libertadores", "stage": "final", "team": "Flamengo", "opponent": "Athletico"}
        matches = self.query("find_matches", **args)
        pending = [m for m in matches["matches"] if "home_goal" not in m]
        self.assertEqual(len(pending), 1)
        self.assertEqual(matches["head_to_head"]["unscored"], 1)
        self.assertEqual(matches["head_to_head"]["matches"], matches["total"] - 1)

    def test_invalid_requests_do_not_interrupt_connection(self):
        self.process.stdin.write("{bad json\n")
        self.process.stdin.flush()
        self.assertEqual(self.receive()["error"]["code"], -32700)
        self.assertEqual(self.rpc("unrecognized")["error"]["code"], -32601)
        for args in ({"from": "2023-02-29"}, {"opponent": "Santos"}, {"limit": True}, {"season": "2023"}):
            with self.subTest(args=args):
                result = self.rpc("tools/call", {"name": "find_matches", "arguments": args})["result"]
                self.assertTrue(result["isError"])
        self.assertEqual(self.rpc("ping")["result"], {})

    def test_queries_fit_performance_limits(self):
        scenarios = [
            ("find_matches", 2, {"team": "Palmeiras", "season": 2023}),
            ("search_players", 2, {"nationality": "Brazil", "name": "Neymar"}),
            ("team_statistics", 5, {"group_by": "team", "sort": "win_rate"}),
            ("competition_standings", 5, {"season": 2019}),
        ]
        for name, limit, args in scenarios:
            with self.subTest(name=name):
                start = time.monotonic()
                self.query(name, timeout=limit, **args)
                self.assertLess(time.monotonic() - start, limit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
