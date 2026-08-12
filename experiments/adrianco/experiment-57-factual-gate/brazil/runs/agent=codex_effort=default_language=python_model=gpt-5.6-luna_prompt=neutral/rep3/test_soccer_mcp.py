import unittest
from soccer_mcp import SoccerDatabase, _key, _mcp_result


class SoccerDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SoccerDatabase()

    def test_all_datasets_are_loaded(self):
        self.assertEqual(len(self.db.matches), 23954)
        self.assertGreater(len(self.db.players), 18000)

    def test_team_normalization_and_match_search(self):
        self.assertEqual(_key("São Paulo-SP"), "sao paulo")
        matches = self.db.search_matches(team="Palmeiras", season=2012, limit=3)
        self.assertTrue(matches)
        self.assertTrue(any("Palmeiras" in m["home_team"] for m in matches))

    def test_team_stats(self):
        stats = self.db.team_stats("Corinthians", season=2019, competition="Brasileirão")
        self.assertGreater(stats["matches"], 0)
        self.assertEqual(stats["matches"], stats["wins"] + stats["draws"] + stats["losses"])
        self.assertGreaterEqual(stats["points"], 0)

    def test_head_to_head(self):
        result = self.db.head_to_head("Flamengo", "Fluminense")
        self.assertGreater(result["matches"], 0)
        self.assertEqual(result["matches"], result["team_a_wins"] + result["team_b_wins"] + result["draws"])

    def test_player_search_and_sorting(self):
        players = self.db.search_players(nationality="Brazil", limit=10)
        self.assertEqual(len(players), 10)
        self.assertTrue(all(p["Nationality"] == "Brazil" for p in players))
        self.assertEqual(players, sorted(players, key=lambda p: p["Overall"], reverse=True))

    def test_standings_and_statistics(self):
        table = self.db.standings(2019)
        self.assertTrue(table)
        self.assertEqual(len(table), 20)
        self.assertEqual({row["team"] for row in table}.__len__(), 20)
        self.assertGreaterEqual(table[0]["points"], table[-1]["points"])
        stats = self.db.statistics(competition="Brasileirão", season=2019)
        self.assertEqual(stats["matches"], 380)
        self.assertGreater(stats["average_goals"], 0)

    def test_natural_language_query(self):
        answer = self.db.query("When did Flamengo last play Corinthians in 2019?")
        self.assertEqual(answer["type"], "head_to_head")
        self.assertTrue(answer["results"]["matches"] > 0)

    def test_atletico_variants_remain_distinct(self):
        mineiro = self.db.team_stats("Atletico-MG", season=2019, competition="Brasileirão")
        paranaense = self.db.team_stats("Atletico-PR", season=2019, competition="Brasileirão")
        self.assertEqual(mineiro["matches"], 38)
        self.assertEqual(paranaense["matches"], 38)
        self.assertNotEqual(mineiro["goals_for"], paranaense["goals_for"])

    def test_date_range_is_inclusive_and_pair_search_can_omit_team(self):
        matches = self.db.search_matches(opponent="Flamengo", start_date="2019-01-01", end_date="2019-12-31")
        self.assertTrue(matches)
        self.assertTrue(all("Flamengo" in (m["home_team"] + m["away_team"]) for m in matches))

    def test_mcp_tools_and_resources(self):
        listing = _mcp_result({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, self.db)
        names = {tool["name"] for tool in listing["result"]["tools"]}
        self.assertTrue({"search_matches", "standings", "search_players"} <= names)
        resources = _mcp_result({"jsonrpc": "2.0", "id": 2, "method": "resources/list"}, self.db)
        self.assertEqual(len(resources["result"]["resources"]), 6)
        uri = resources["result"]["resources"][0]["uri"]
        read = _mcp_result({"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": uri}}, self.db)
        self.assertTrue(read["result"]["contents"][0]["text"])


if __name__ == "__main__": unittest.main()
