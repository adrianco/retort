import unittest

from soccer_mcp import SoccerDatabase, _key


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
        self.assertGreaterEqual(table[0]["points"], table[-1]["points"])
        stats = self.db.statistics(competition="Brasileirão", season=2019)
        self.assertEqual(stats["matches"], 380)
        self.assertGreater(stats["average_goals"], 0)

    def test_natural_language_query(self):
        answer = self.db.query("When did Flamengo last play Corinthians in 2019?")
        self.assertEqual(answer["type"], "head_to_head")
        self.assertTrue(answer["results"]["matches"] > 0)


if __name__ == "__main__": unittest.main()
