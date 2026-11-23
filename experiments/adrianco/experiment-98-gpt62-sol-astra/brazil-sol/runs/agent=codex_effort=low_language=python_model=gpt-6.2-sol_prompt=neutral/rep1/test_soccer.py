import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import unittest

from soccer import CUP, CUP_FILE, EXTENDED, FIFA, HISTORICAL, LEAGUE, LIB_FILE, SERIE_A, Soccer


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.soccer = Soccer()

    def test_all_sources_are_queryable(self):
        counts = {SERIE_A: 4180, HISTORICAL: 6886, CUP_FILE: 1337,
                  LIB_FILE: 1255, EXTENDED: 10296, FIFA: 18207}
        self.assertEqual(self.soccer.coverage()["sources"], counts)
        for filename, total in counts.items():
            with self.subTest(filename=filename):
                result = (self.soccer.search_players(limit=1) if filename == FIFA
                          else self.soccer.search_matches(source=filename, limit=1))
                self.assertEqual(result["total"], total)

    def test_find_fla_flu_matches_in_both_orientations(self):
        result = self.soccer.search_matches("Flamengo-RJ", "Fluminense", limit=200)
        games = result["matches"]
        self.assertEqual({match["home_team"] for match in games}, {"Flamengo", "Fluminense"})
        for match in games:
            self.assertTrue(match["date"])
            self.assertIsInstance(match["home_goal"], int)
            self.assertIsInstance(match["away_goal"], int)
            self.assertTrue(match["competition"])

    def test_latest_flamengo_corinthians_score(self):
        game, = self.soccer.search_matches("Flamengo", "Corinthians", limit=1)["matches"]
        self.assertEqual((game["date"], game["home_goal"], game["away_goal"]),
                         ("2023-10-08", 1, 1))

    def test_find_palmeiras_2023_schedule_and_points_breakdown(self):
        matches = self.soccer.search_matches("Palmeiras", season=2023)
        stats = self.soccer.team_stats("Palmeiras", 2023)
        self.assertEqual(matches["total"], stats["fixtures"])
        self.assertEqual(stats["matches"], stats["wins"] + stats["losses"] + stats["draws"])
        self.assertGreater(stats["goals_for"], 0)
        self.assertGreater(stats["goals_against"], 0)

    def test_find_cup_finals(self):
        finals = self.soccer.search_matches(competition=CUP, stage="finals")["matches"]
        self.assertEqual(len(finals), 24)
        self.assertEqual({m["season"] for m in finals}, set(range(2012, 2024)))
        self.assertTrue(all(m["stage"] == "final" for m in finals))

    def test_corinthians_home_record(self):
        actual = self.soccer.team_stats("Sport Club Corinthians Paulista", 2022, LEAGUE, "home")
        self.assertEqual([actual[k] for k in ("matches", "wins", "draws", "losses", "goals_for")],
                         [19, 12, 4, 3, 24])

    def test_compare_palmeiras_santos(self):
        records = self.soccer.head_to_head("SE Palmeiras", "Santos FC")["records"]
        a, b = records["Palmeiras"], records["Santos"]
        self.assertEqual(a["wins"], b["losses"])
        self.assertEqual(a["goals_for"], b["goals_against"])
        self.assertEqual(a["draws"], b["draws"])

    def test_date_ranges_accept_portuguese_and_iso_dates(self):
        result = self.soccer.search_matches(start_date="29/03/2003", end_date="2003-03-29",
                                            competition="Série A")
        self.assertEqual(result["total"], 2)
        self.assertEqual({x["date"] for x in result["matches"]}, {"2003-03-29"})

    def test_extended_statistics_are_linked_to_season_and_round(self):
        result = self.soccer.search_matches(competition=LEAGUE, season=2019, limit=500)
        match = next(match for match in result["matches"]
                     if set(match["sources"]) == {EXTENDED, HISTORICAL, SERIE_A})
        self.assertIn("home_corner", match["extended_statistics"])
        self.assertTrue(match["stadium"])
        self.assertIsInstance(match["round"], int)
        self.assertEqual(result["total"], 380)

    def test_same_name_clubs_keep_state_identity(self):
        rj = self.soccer.search_matches("Botafogo", venue="home", limit=500)["matches"]
        sp = self.soccer.search_matches("Botafogo-SP", venue="home", limit=500)["matches"]
        self.assertEqual({m["home_team"] for m in rj}, {"Botafogo-RJ"})
        self.assertEqual({m["home_team"] for m in sp}, {"Botafogo-SP"})

    def test_derbies(self):
        result = self.soccer.search_matches("Flamengo", season=2023, derbies=True)
        pairs = [{match["home_team"], match["away_team"]} - {"Flamengo"}
                 for match in result["matches"]]
        self.assertEqual(set.union(*pairs), {"Fluminense", "Vasco da Gama", "Botafogo-RJ"})

    def test_palmeiras_competitions(self):
        competitions = self.soccer.team_stats("Palmeiras")["by_competition"]
        self.assertTrue({LEAGUE, CUP, "Copa Libertadores"}.issubset(competitions))

    def test_top_brazilian_players(self):
        result = self.soccer.search_players(nationality="Brasíl", limit=3)
        players = result["players"]
        self.assertGreater(result["total"], 500)
        self.assertEqual(players[0]["Name"], "Neymar Jr")
        self.assertEqual({p["Nationality"] for p in players}, {"Brazil"})
        self.assertEqual([p["Overall"] for p in players],
                         sorted((p["Overall"] for p in players), reverse=True))

    def test_player_name_and_attributes(self):
        player, = self.soccer.search_players(name="Neymar Jr")["players"]
        self.assertEqual(player["Overall"], 92)
        self.assertTrue(player["Dribbling"])
        self.assertTrue(player["Height"])

    def test_missing_player_and_club_return_empty_results(self):
        self.assertEqual(self.soccer.search_players(name="Gabriel Barbosa")["total"], 0)
        self.assertEqual(self.soccer.search_players(club="Flamengo")["total"], 0)

    def test_club_and_position_filter(self):
        players = self.soccer.search_players(club="Santos FC", position="forwards")["players"]
        self.assertTrue(players)
        self.assertTrue(all(p["Club"] == "Santos" for p in players))
        self.assertTrue(all(p["Position"] in {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"}
                            for p in players))

    def test_club_profile_joins_fifa_and_results(self):
        profile = self.soccer.club_profile("Gremio-RS", 2019, player_limit=2)
        self.assertGreater(profile["record"]["wins"], 0)
        self.assertEqual(profile["record"]["team"], "Grêmio")
        self.assertEqual({p["Club"] for p in profile["fifa_snapshot"]["players"]}, {"Grêmio"})

    def test_2019_standings(self):
        result = self.soccer.standings(2019)
        first, second, third = result["teams"][:3]
        self.assertEqual([(r["team"], r["points"]) for r in (first, second, third)],
                         [("Flamengo", 90), ("Santos", 74), ("Palmeiras", 74)])
        self.assertTrue(result["double_round_robin_complete"])

    def test_2020_relegation_and_delayed_fixtures(self):
        table = self.soccer.standings(2020)
        self.assertEqual(table["played_fixtures"], 380)
        self.assertEqual(table["relegation_places"],
                         ["Vasco da Gama", "Goiás", "Coritiba", "Botafogo-RJ"])
        recent = self.soccer.search_matches(season=2020, competition=LEAGUE, limit=1)
        self.assertTrue(recent["matches"][0]["date"].startswith("2021"))

    def test_incomplete_2023_table_and_goals_ranking(self):
        self.assertFalse(self.soccer.standings(2023)["double_round_robin_complete"])
        ranking = self.soccer.team_rankings(LEAGUE, 2023, sort_by="goals_for", limit=1)
        self.assertEqual(ranking["teams"][0]["goals_for"], 63)

    def test_2018_libertadores_bracket(self):
        result = self.soccer.tournament_bracket(2018)
        self.assertEqual(set(result["rounds"]), {"round of 16", "quarterfinals", "semifinals", "final"})
        self.assertEqual(len(result["rounds"]["final"]), 2)

    def test_season_comparison_and_goal_average(self):
        result = self.soccer.match_statistics(LEAGUE, biggest_wins_limit=3)
        for year in ("2018", "2019"):
            stats = result["by_season"][year]
            self.assertEqual(stats["matches"], 380)
            self.assertAlmostEqual(stats["average_goals"], stats["goals"] / stats["matches"], places=3)
        margins = [m["margin"] for m in result["biggest_wins"]]
        self.assertEqual(margins, sorted(margins, reverse=True))
        self.assertGreater(result["home_win_rate"], result["away_win_rate"])

    def test_home_and_away_rankings_support_minimum_sample(self):
        for venue in ("home", "away"):
            result = self.soccer.team_rankings(LEAGUE, 2019, venue, "win_rate", 19, limit=2)
            top, next_team = result["teams"]
            self.assertGreaterEqual(top["win_rate"], next_team["win_rate"])
            self.assertEqual(top["matches"], 19)

    def test_no_individual_goal_data(self):
        result = self.soccer.top_scorers("Libertadores", 2018)
        self.assertFalse(result["available"])
        self.assertEqual(result["scorers"], [])

    def test_pagination_and_invalid_filters(self):
        first = self.soccer.search_matches(limit=2)
        second = self.soccer.search_matches(limit=2, offset=first["next_offset"])
        self.assertEqual(first["total"], second["total"])
        self.assertNotEqual(first["matches"], second["matches"])
        with self.assertRaises(ValueError):
            self.soccer.search_matches(venue="home")
        with self.assertRaises(ValueError):
            self.soccer.search_matches(start_date="2020-03-01", end_date="2020-01-01")

    def test_query_time_budgets(self):
        start = perf_counter()
        self.soccer.search_matches("Flamengo", "Corinthians")
        self.assertLess(perf_counter() - start, 2)
        start = perf_counter()
        self.soccer.team_rankings(sort_by="win_rate")
        self.soccer.match_statistics()
        self.assertLess(perf_counter() - start, 5)


class MCPScenarios(unittest.TestCase):
    def test_stdio_handshake_discovery_and_calls(self):
        def request(method, request_id=None, **params):
            message = {"jsonrpc": "2.0", "method": method, "params": params}
            if request_id is not None:
                message["id"] = request_id
            return json.dumps(message)

        requests = [
            request("initialize", 1, protocolVersion="2025-11-25", capabilities={},
                    clientInfo={"name": "test", "version": "1"}),
            request("notifications/initialized"),
            request("tools/list", 2),
            request("tools/call", 3, name="search_matches",
                    arguments={"team": "São Paulo FC", "limit": 1}),
            request("tools/call", 4, name="standings", arguments={"season": True}),
            request("ping", 5),
        ]
        script = Path(__file__).resolve().with_name("server.py")
        completed = subprocess.run([sys.executable, str(script)], cwd=script.parent / "data",
                                   input="\n".join(requests) + "\n", capture_output=True,
                                   encoding="utf-8", check=True, timeout=10)
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual([r["id"] for r in responses], [1, 2, 3, 4, 5])
        self.assertEqual(responses[0]["result"]["capabilities"], {"tools": {}})
        tools = {t["name"]: t for t in responses[1]["result"]["tools"]}
        self.assertEqual(tools["standings"]["inputSchema"]["required"], ["season"])
        result = responses[2]["result"]
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
        game, = result["structuredContent"]["matches"]
        self.assertIn("São Paulo", [game["home_team"], game["away_team"]])
        self.assertTrue(responses[3]["result"]["isError"])
        self.assertEqual(responses[4]["result"], {})


if __name__ == "__main__":
    unittest.main()
