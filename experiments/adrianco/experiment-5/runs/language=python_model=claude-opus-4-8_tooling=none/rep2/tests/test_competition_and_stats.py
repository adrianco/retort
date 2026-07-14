"""
BDD scenarios -- Competition Queries and Statistical Analysis (G/W/T).

Feature: Competition standings and aggregate statistics
    As an analyst
    I want league tables and aggregate statistics computed from match results
    So that I can answer "who won", "biggest wins" and "average goals" questions.
"""

import time


class TestLeagueStandings:
    """Scenario: Compute standings from match results."""

    def test_2019_brasileirao_champion_is_flamengo(self, kg):
        # Given the match data is loaded
        # When I compute the 2019 Brasileirao standings
        table = kg.standings("Brasileirao", 2019)

        # Then a full 20-team table is produced, ordered by points
        assert len(table) == 20
        points = [r["points"] for r in table]
        assert points == sorted(points, reverse=True)
        # And the champion (well-documented historically) is Flamengo
        assert "flamengo" in table[0]["team"].lower()
        assert table[0]["position"] == 1

    def test_each_team_plays_38_games(self, kg):
        table = kg.standings("Brasileirao", 2019)
        assert all(r["played"] == 38 for r in table)

    def test_known_champions_match_history(self, kg):
        # Spot-check well-documented champions computed purely from match data.
        cases = {
            2003: "cruzeiro", 2008: "sao paulo", 2015: "corinthians",
            2018: "palmeiras", 2019: "flamengo", 2021: "atletico",
        }
        from team_names import strip_accents
        for season, expected in cases.items():
            champ = kg.champion("Brasileirao", season)
            assert expected in strip_accents(champ["team"]).lower(), (season, champ["team"])

    def test_team_counts_per_season(self, kg):
        # 2003-04 had 24 clubs, 2005 had 22, and 20 from 2006 onward.
        assert len(kg.standings("Brasileirao", 2004)) == 24
        assert len(kg.standings("Brasileirao", 2005)) == 22
        assert len(kg.standings("Brasileirao", 2020)) == 20


class TestStandingsOnMiniData:
    """Scenario: Standings ordering is correct on deterministic data."""

    def test_team_a_tops_table(self, mini_kg):
        table = mini_kg.standings("Brasileirao", 2020)
        assert table[0]["team"] == "Team A"
        assert table[0]["points"] == 6  # two wins
        assert table[-1]["team"] == "Team C"  # lost everything


class TestListSeasons:
    """Scenario: List the seasons available for a competition."""

    def test_brasileirao_seasons_present(self, kg):
        seasons = kg.list_seasons("Brasileirao")
        assert 2019 in seasons
        assert seasons == sorted(seasons)


class TestAverageGoals:
    """Scenario: Average goals per match and outcome rates."""

    def test_plausible_averages(self, kg):
        stats = kg.average_goals(competition="Brasileirao")
        # Then the average is in a plausible football range
        assert 1.5 <= stats["avg_goals_per_match"] <= 4.0
        # And outcome rates sum to ~100%
        total = stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"]
        assert abs(total - 100.0) < 0.5
        # And home advantage holds across the dataset
        assert stats["home_win_rate"] > stats["away_win_rate"]

    def test_mini_average(self, mini_kg):
        stats = mini_kg.average_goals()
        # 4 matches, goals: (2+0)+(3+1)+(1+1)+(0+4) = 12 -> avg 3.0
        assert stats["matches"] == 4
        assert stats["avg_goals_per_match"] == 3.0


class TestBiggestWins:
    """Scenario: Find the biggest victory margins."""

    def test_sorted_by_margin(self, kg):
        matches = kg.biggest_wins(competition="Brasileirao", limit=10)
        assert len(matches) == 10
        margins = [abs(m.home_goal - m.away_goal) for m in matches]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5  # a big rout exists in the data


class TestBestRecords:
    """Scenario: Rank teams by home win-rate."""

    def test_best_home_records(self, kg):
        rows = kg.best_team_record(
            venue="home", competition="Brasileirao", season=2019, min_matches=5
        )
        assert len(rows) > 0
        rates = [r["win_rate"] for r in rows]
        assert rates == sorted(rates, reverse=True)
        assert all(r["played"] >= 5 for r in rows)


class TestPerformance:
    """Scenario: Queries meet the spec's latency targets."""

    def test_simple_lookup_under_2s(self, kg):
        start = time.perf_counter()
        kg.find_matches(team="Flamengo", opponent="Corinthians")
        assert time.perf_counter() - start < 2.0

    def test_aggregate_under_5s(self, kg):
        start = time.perf_counter()
        kg.standings("Brasileirao", 2019)
        kg.average_goals(competition="Brasileirao")
        assert time.perf_counter() - start < 5.0
