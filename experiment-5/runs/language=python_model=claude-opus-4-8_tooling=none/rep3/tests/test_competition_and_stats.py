# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.test_competition_and_stats
# Purpose : BDD scenarios for categories 4 (Competition Queries) and 5
#           (Statistical Analysis): computed standings, champions, aggregate
#           goal/win-rate statistics and biggest victories.
# =============================================================================


class TestStandings:
    """Feature: League standings computed from match results."""

    def test_2019_brasileirao_has_twenty_teams(self, graph):
        # Given the 2019 Brasileirão, When standings are computed
        table = graph.standings("Brasileirão", 2019)
        # Then there are 20 teams each having played 38 games
        assert len(table) == 20
        assert all(r["played"] == 38 for r in table)

    def test_2019_champion_is_flamengo_with_90_points(self, graph):
        # Then Flamengo top the table with 90 points (matches the spec example)
        table = graph.standings("Brasileirão", 2019)
        champ = table[0]
        assert champ["position"] == 1
        assert champ["team"].lower().startswith("flamengo")
        assert champ["points"] == 90
        assert (champ["wins"], champ["draws"], champ["losses"]) == (28, 6, 4)

    def test_table_sorted_by_points(self, graph):
        table = graph.standings("Brasileirão", 2018)
        points = [r["points"] for r in table]
        assert points == sorted(points, reverse=True)

    def test_champion_helper(self, graph):
        champ = graph.champion("Brasileirão", 2019)
        assert champ["team"].lower().startswith("flamengo")


class TestAggregateStatistics:
    """Feature: Aggregate statistical analysis."""

    def test_average_goals_per_match_is_reasonable(self, graph):
        # When I ask for overall statistics
        s = graph.statistics()
        # Then the average goals per match is in a plausible football range
        assert 2.0 <= s["avg_goals_per_match"] <= 3.5
        assert s["matches"] > 0

    def test_outcome_rates_sum_to_100(self, graph):
        s = graph.statistics(competition="Brasileirão", season=2019)
        total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
        # Allow tiny rounding error
        assert abs(total - 100.0) < 0.5

    def test_home_advantage_exists(self, graph):
        s = graph.statistics(competition="Brasileirão")
        # Home win rate should exceed away win rate (home advantage)
        assert s["home_win_rate"] > s["away_win_rate"]


class TestBiggestWins:
    """Feature: Biggest victories in the dataset."""

    def test_sorted_by_margin(self, graph):
        wins = graph.biggest_wins(competition="Brasileirão", limit=10)
        margins = [abs(m.home_goal - m.away_goal) for m in wins]
        assert margins == sorted(margins, reverse=True)
        # The biggest Brasileirão margin in the data is a blowout
        assert margins[0] >= 5
