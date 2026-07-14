"""
==============================================================================
File: tests/test_competition_and_stats.py
==============================================================================
CONTEXT
-------
BDD tests for the COMPETITION (spec section 4) and STATISTICAL ANALYSIS (spec
section 5) categories: computed standings, average goals, home/away records and
biggest wins. The 2019 Brasileirão standing is checked against the known real
result published in the specification (Flamengo champion, 90 pts, 28W-6D-4L).
==============================================================================
"""

from brazilian_soccer import queries as q


class TestStandings:
    def test_2019_brasileirao_champion_is_flamengo(self, graph):
        # Given the 2019 Brasileirão match data
        # When I compute the final standings
        s = q.standings(graph, "Brasileirão", 2019)
        # Then Flamengo are champions with the historically-correct record
        assert s["champion"] == "Flamengo"
        assert s["teams"] == 20
        champ = s["table"][0]
        assert champ["points"] == 90
        assert (champ["wins"], champ["draws"], champ["losses"]) == (28, 6, 4)

    def test_standings_points_consistency(self, graph):
        # Given any standings / Then every row's points == 3W + D
        s = q.standings(graph, "Brasileirão", 2018)
        for row in s["table"]:
            assert row["points"] == row["wins"] * 3 + row["draws"]
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]

    def test_standings_ordered_by_points(self, graph):
        # Given standings / Then points are non-increasing down the table
        s = q.standings(graph, "Brasileirão", 2017)
        pts = [r["points"] for r in s["table"]]
        assert pts == sorted(pts, reverse=True)

    def test_historical_season_from_novo_source(self, graph):
        # Given a season only present in the historical file (2008)
        # When I compute standings / Then a valid 20-team table is produced
        s = q.standings(graph, "Brasileirão", 2008)
        assert s["teams"] == 20
        assert s["champion"]


class TestListCompetitions:
    def test_lists_core_competitions_with_seasons(self, graph):
        # Given the data / When listing competitions
        r = q.list_competitions(graph)
        # Then Brasileirão is present with multiple seasons
        assert "Brasileirão" in r["competitions"]
        assert len(r["competitions"]["Brasileirão"]["seasons"]) > 5


class TestStatistics:
    def test_average_goals_per_match_is_reasonable(self, graph):
        # Given the Brasileirão data / When computing aggregate stats
        s = q.competition_stats(graph, competition="Brasileirão")
        # Then average goals per match is in a football-plausible range
        assert 2.0 <= s["avg_goals_per_match"] <= 3.5
        # And win/draw rates sum to ~100%
        total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
        assert abs(total - 100.0) < 0.5

    def test_biggest_wins_sorted_by_margin(self, graph):
        # Given the data / When listing biggest wins
        r = q.biggest_wins(graph, competition="Brasileirão", limit=5)
        margins = [
            abs(m["home_goal"] - m["away_goal"]) for m in r["matches"]
        ]
        # Then margins are non-increasing and the top one is a blowout
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5

    def test_best_home_record(self, graph):
        # Given a season / When ranking by home win-rate
        r = q.best_home_record(graph, competition="Brasileirão", season=2019)
        # Then teams are ordered by win rate descending
        rates = [t["win_rate"] for t in r["teams"]]
        assert rates == sorted(rates, reverse=True)
        assert r["teams"][0]["win_rate"] > 50

    def test_best_away_record(self, graph):
        # Given a season / When ranking by away win-rate / Then a ranking exists
        r = q.best_away_record(graph, competition="Brasileirão", season=2019)
        assert len(r["teams"]) > 0
        assert all(t["played"] >= 5 for t in r["teams"])
