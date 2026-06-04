"""
================================================================================
Module: tests.test_team_queries
--------------------------------------------------------------------------------
Context:
    BDD scenarios for the "Team Queries" feature (TASK.md §2) — win/draw/loss
    records, goals for/against, win-rate, venue splits and competition history.

Responsibility:
    Validate KnowledgeGraph.team_record / team_competitions arithmetic and the
    suffix-tolerant team resolution that underpins them.
================================================================================
"""


class TestTeamRecord:
    def test_record_fields_are_internally_consistent(self, graph):
        # WHEN I request Corinthians' 2022 home record in the Brasileirão
        r = graph.team_record("Corinthians", season=2022,
                              competition="Brasileirão", venue="home")
        # THEN matches == wins + draws + losses
        assert r["matches"] == r["wins"] + r["draws"] + r["losses"]
        assert r["matches"] > 0
        # AND points == 3*wins + draws
        assert r["points"] == 3 * r["wins"] + r["draws"]
        # AND win rate is consistent
        expected = round(r["wins"] / r["matches"] * 100, 1)
        assert r["win_rate"] == expected
        # AND goal difference matches
        assert r["goal_difference"] == r["goals_for"] - r["goals_against"]

    def test_home_and_away_split_sums_to_all(self, graph):
        # The home + away records should add up to the full-season record.
        all_r = graph.team_record("Flamengo", season=2019, competition="Brasileirão")
        home = graph.team_record("Flamengo", season=2019,
                                competition="Brasileirão", venue="home")
        away = graph.team_record("Flamengo", season=2019,
                                competition="Brasileirão", venue="away")
        assert home["matches"] + away["matches"] == all_r["matches"]
        assert home["wins"] + away["wins"] == all_r["wins"]
        assert home["goals_for"] + away["goals_for"] == all_r["goals_for"]

    def test_champion_record_matches_known_history(self, graph):
        # 2019 Brasileirão: Flamengo, 38 games, 28W 6D 4L, 90 pts (historical fact).
        r = graph.team_record("Flamengo", season=2019, competition="Brasileirão")
        assert r["matches"] == 38
        assert (r["wins"], r["draws"], r["losses"]) == (28, 6, 4)
        assert r["points"] == 90

    def test_empty_record_for_unknown_team(self, graph):
        r = graph.team_record("Nonexistent United FC")
        assert r["matches"] == 0
        assert r["win_rate"] == 0.0


class TestTeamCompetitions:
    def test_palmeiras_plays_in_all_three_majors(self, graph):
        comps = graph.team_competitions("Palmeiras")
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps
