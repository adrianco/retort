import unittest

from brazilian_soccer_mcp import DATA_DIR, SoccerDataService, normalize_name


class SoccerDataServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = SoccerDataService(DATA_DIR)

    def test_all_provided_files_are_loaded(self):
        sources = {m["source"] for m in self.service.matches}
        self.assertEqual(len(sources), 5)
        self.assertGreater(len(self.service.players), 1000)

    def test_normalizes_accents_and_state_suffixes(self):
        self.assertEqual(normalize_name("São Paulo-SP"), "sao paulo")
        matches = self.service.search_matches(team="Flamengo-RJ", season=2023)
        self.assertTrue(matches)
        self.assertTrue(all("flamengo" in (normalize_name(m["home_team"]) + normalize_name(m["away_team"])) for m in matches))

    def test_match_search_and_stats(self):
        matches = self.service.search_matches(team="Palmeiras", competition="Brasileirão", season=2023)
        self.assertTrue(matches)
        stats = self.service.team_statistics("Palmeiras", season=2023, competition="Brasileirão")
        self.assertEqual(stats["matches"], stats["wins"] + stats["draws"] + stats["losses"])

    def test_head_to_head_returns_only_both_teams(self):
        result = self.service.head_to_head("Flamengo", "Fluminense")
        self.assertGreater(result["matches"], 0)
        for match in result["recent_matches"]:
            names = {normalize_name(match["home_team"]), normalize_name(match["away_team"])}
            self.assertIn("flamengo", names); self.assertIn("fluminense", names)

    def test_player_search_and_standings(self):
        self.assertTrue(self.service.search_players(nationality="Brazil", limit=3))
        table = self.service.standings(2019)
        self.assertTrue(table)
        self.assertGreaterEqual(table[0]["points"], table[-1]["points"])
        self.assertEqual(table[0]["team"], "Flamengo")
        self.assertEqual(table[0]["points"], 90)


if __name__ == "__main__":
    unittest.main()
