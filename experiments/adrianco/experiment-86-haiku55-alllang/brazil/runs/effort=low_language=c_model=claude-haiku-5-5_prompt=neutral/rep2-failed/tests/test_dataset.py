"""BDD-style scenarios for match, team, competition and player queries."""

import unittest
from datetime import date

from brazil_soccer_mcp.dataset import Dataset
from brazil_soccer_mcp.loaders import CUP, LIBERTADORES

from .helpers import match, player


def sample_dataset() -> Dataset:
    matches = [
        match("2023-05-28", "Fluminense", "Flamengo", 1, 0, season=2023, home_state="RJ", away_state="RJ"),
        match("2023-09-03", "Flamengo", "Fluminense", 2, 1, season=2023, home_state="RJ", away_state="RJ"),
        match("2023-08-01", "Palmeiras-SP", "Santos-SP", 3, 0, season=2023),
        match("2023-08-15", "Santos-SP", "Palmeiras-SP", 1, 1, season=2023),
        match("2023-10-01", "Palmeiras-SP", "Corinthians-SP", 2, 1, season=2023),
        match("2022-04-10", "Palmeiras-SP", "Corinthians-SP", 0, 0, season=2022),
        match("2022-11-20", "Corinthians-SP", "Palmeiras-SP", 3, 0, season=2022),
        match("2022-06-01", "Corinthians-SP", "Santos-SP", 2, 2, season=2022),
        match("2023-06-06", "Flamengo", "Palmeiras-SP", 1, 0, competition=LIBERTADORES, season=2023),
        match("2023-07-07", "Corinthians-SP", "Flamengo", 1, 1, competition=CUP, season=2023),
    ]
    players = [
        player(1, "Gabriel Barbosa", "Flamengo", 85, position="ST"),
        player(2, "Gabriel Jesus", "Manchester City", 88, position="ST"),
        player(3, "Alisson", "Liverpool", 89, position="GK"),
        player(4, "Lionel Messi", "FC Barcelona", 94, nationality="Argentina", position="RF"),
        player(5, "Arrascaeta", "Flamengo", 80, position="CAM"),
    ]
    return Dataset(matches, players)


class MatchQueries(unittest.TestCase):
    def test_find_matches_between_two_teams_newest_first(self):
        """Given Flamengo and Fluminense meet twice, when searching their matches, both are returned newest first."""
        result = sample_dataset().find_matches("Flamengo", "Fluminense")
        self.assertEqual(result["total"], 2)
        self.assertEqual([m.played_on for m in result["matches"]], [date(2023, 9, 3), date(2023, 5, 28)])

    def test_find_matches_by_competition_and_season(self):
        """Given a Copa do Brasil match in 2023, when filtering by that competition and season, only it is returned."""
        result = sample_dataset().find_matches(
            "Corinthians", competition="copa do brasil", season=2023
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["matches"][0].competition, CUP)

    def test_find_matches_by_venue(self):
        """Given Palmeiras plays at home and away, when asking for home matches only, away games are excluded."""
        home = sample_dataset().find_matches("Palmeiras", venue="home", season=2023)
        self.assertTrue(all(m.home.base == "palmeiras" for m in home["matches"]))

    def test_find_matches_by_date_range(self):
        """Given matches across 2022 and 2023, a date range narrows the result."""
        ds = sample_dataset()
        result = ds.find_matches("Palmeiras", start=date(2023, 1, 1), end=date(2023, 8, 31))
        self.assertEqual(result["total"], 3)  # two Brasileirão games plus the June Libertadores tie

    def test_matches_with_team_names_in_any_form_are_found(self):
        """Given the query "Palmeiras" and records "Palmeiras-SP", the match is found."""
        self.assertGreater(sample_dataset().find_matches("Palmeiras")["total"], 0)


class TeamRecords(unittest.TestCase):
    def test_team_record_counts_wins_draws_losses_and_goals(self):
        """Given Corinthians' 2022 matches, the record has wins, draws, losses and goals."""
        record = sample_dataset().team_record("Corinthians", season=2022)
        self.assertEqual(record["played"], 3)
        self.assertEqual((record["wins"], record["draws"], record["losses"]), (1, 2, 0))
        self.assertEqual((record["goals_for"], record["goals_against"]), (5, 2))
        self.assertEqual(record["win_rate"], 33.3)

    def test_home_record_uses_only_home_games(self):
        """Given Palmeiras' 2023 home games, only those count toward the home record."""
        record = sample_dataset().team_record("Palmeiras", venue="home", season=2023)
        self.assertEqual(record["played"], 2)
        self.assertEqual(record["wins"], 2)

    def test_unknown_team_has_empty_record(self):
        """Given a team absent from the dataset, the record reports zero matches."""
        self.assertEqual(sample_dataset().team_record("Nonexistent FC")["played"], 0)


class HeadToHead(unittest.TestCase):
    def test_head_to_head_summary(self):
        """Given Palmeiras and Santos met in 2023, the head-to-head shows each side's wins."""
        result = sample_dataset().head_to_head("Palmeiras", "Santos", season=2023)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["a"]["wins"], 1)
        self.assertEqual(result["a"]["draws"], 1)
        self.assertEqual(result["b"]["wins"], 0)


class Standings(unittest.TestCase):
    def test_table_is_ordered_by_points(self):
        """Given 2023 Série A results, the table is ordered by points with positions assigned."""
        table = sample_dataset().standings(2023, competition="brasileirao")
        self.assertEqual([row["position"] for row in table], list(range(1, len(table) + 1)))
        points = [row["points"] for row in table]
        self.assertEqual(points, sorted(points, reverse=True))

    def test_standings_points_follow_three_for_win_one_for_draw(self):
        """Given Palmeiras won twice and drew once in 2023, it has seven points from those matches."""
        table = {row["team"]: row for row in sample_dataset().standings(2023, competition="brasileirao")}
        self.assertEqual(table["palmeiras"]["points"], 7)


class Statistics(unittest.TestCase):
    def test_league_stats_average_goals(self):
        """Given 2023 Série A matches, the average goals per match is calculated."""
        stats = sample_dataset().league_stats(competition="brasileirao", season=2023)
        self.assertEqual(stats["matches"], 5)
        self.assertEqual(stats["total_goals"], 1 + 3 + 3 + 2 + 3)
        self.assertEqual(stats["goals_per_match"], 2.4)

    def test_rank_teams_by_home_win_rate(self):
        """Given home results in 2022 and 2023, teams are ranked by home win rate."""
        rows = sample_dataset().rank_teams("home_win_rate", competition="brasileirao", min_matches=2)
        self.assertEqual(rows[0]["team"], "palmeiras")

    def test_rank_teams_rejects_unknown_metric(self):
        """Given an unsupported metric, a ValueError is raised."""
        with self.assertRaises(ValueError):
            sample_dataset().rank_teams("vibes")

    def test_biggest_wins_sorted_by_margin(self):
        """Given several decided matches, the largest margin comes first."""
        wins = sample_dataset().biggest_wins(limit=1)
        self.assertEqual(abs(wins[0].home_goals - wins[0].away_goals), 3)


class PlayerQueries(unittest.TestCase):
    def test_search_by_name_is_accent_and_case_insensitive(self):
        """Given "gabriel", both Gabriel players are returned."""
        result = sample_dataset().search_players(name="gabriel")
        self.assertEqual(result["total"], 2)

    def test_players_at_a_club_sorted_by_overall(self):
        """Given Flamengo players, the highest-rated comes first."""
        result = sample_dataset().search_players(club="Flamengo")
        self.assertEqual(result["players"][0].name, "Gabriel Barbosa")

    def test_filter_by_nationality_and_position(self):
        """Given a nationality and position filter, only matching players remain."""
        result = sample_dataset().search_players(nationality="Brazil", position="GK")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["players"][0].name, "Alisson")

    def test_club_summary_averages_overall(self):
        """Given Flamengo's two players rated 85 and 80, the average is 82.5."""
        rows = {r["club"]: r for r in sample_dataset().club_summary()}
        self.assertEqual(rows["Flamengo"]["avg_overall"], 82.5)


if __name__ == "__main__":
    unittest.main()
