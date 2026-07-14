"""
================================================================================
Module: tests.test_competition_queries
--------------------------------------------------------------------------------
Context:
    BDD scenarios for the "Competition Queries" feature (TASK.md §4) — league
    tables computed from match results, champions, and listing the available
    competitions and seasons.

Responsibility:
    Validate KnowledgeGraph.standings / champion / list_competitions /
    list_seasons, including the critical property that overlapping source files
    do NOT inflate a 20-team season beyond 38 matches per club.
================================================================================
"""


class TestStandings:
    def test_2019_brasileirao_champion_is_flamengo(self, graph):
        # WHEN I compute the 2019 Brasileirão standings
        table = graph.standings("Brasileirão", 2019)
        # THEN Flamengo tops the table
        assert table[0]["team"].startswith("Flamengo")
        assert table[0]["position"] == 1
        assert table[0]["points"] == 90

    def test_round_robin_has_38_matches_per_team(self, graph):
        # Guards against cross-source double-counting (the dedup invariant).
        table = graph.standings("Brasileirão", 2019)
        assert len(table) == 20
        assert all(row["played"] == 38 for row in table)

    def test_standings_sorted_by_points(self, graph):
        table = graph.standings("Brasileirão", 2019)
        points = [r["points"] for r in table]
        assert points == sorted(points, reverse=True)

    def test_points_equal_three_wins_plus_draws(self, graph):
        table = graph.standings("Brasileirão", 2019)
        for r in table:
            assert r["points"] == 3 * r["wins"] + r["draws"]
            assert r["played"] == r["wins"] + r["draws"] + r["losses"]

    def test_champion_helper_matches_table_top(self, graph):
        champ = graph.champion("Brasileirão", 2019)
        table = graph.standings("Brasileirão", 2019)
        assert champ["team"] == table[0]["team"]


class TestCompetitionMetadata:
    def test_all_expected_competitions_present(self, graph):
        comps = graph.list_competitions()
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_seasons_span_the_historical_range(self, graph):
        seasons = graph.list_seasons("Brasileirão")
        # Historical data starts in 2003.
        assert min(seasons) == 2003
        assert 2019 in seasons
