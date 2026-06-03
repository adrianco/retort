"""
================================================================================
 BDD tests: Competition Queries (capability category 4)
================================================================================
Feature: Competition Queries
  I want standings, champions and relegated teams calculated from match results
  So that I can answer competition-outcome questions.

These scenarios assert against *known historical facts* (e.g. Flamengo won the
2019 Brasileirão with 90 points) which doubles as a correctness check on the
standings calculation and the cross-file deduplication.
================================================================================
"""


class TestStandings:
    def test_standings_are_ordered_and_complete(self, engine):
        # Given the match data is loaded
        # When I compute the 2019 Brasileirão standings
        result = engine.standings(2019, "Brasileirão Série A")
        table = result["table"]
        # Then there are 20 teams, ranked by points descending
        assert len(table) == 20
        points = [row["points"] for row in table]
        assert points == sorted(points, reverse=True)
        # And positions are 1..20
        assert [row["position"] for row in table] == list(range(1, 21))

    def test_points_equal_three_per_win_plus_draws(self, engine):
        # Given the 2019 standings
        table = engine.standings(2019, "Brasileirão Série A")["table"]
        # Then every row's points obey the 3-1-0 system
        for row in table:
            assert row["points"] == row["wins"] * 3 + row["draws"]


class TestChampion:
    def test_2019_brasileirao_champion_is_flamengo_with_90_points(self, engine):
        # Given the match data is loaded
        # When I ask who won the 2019 Brasileirão
        champ = engine.champion(2019, "Brasileirão Série A")["champion"]
        # Then it is Flamengo with the historically-correct 90 points / 38 games
        assert "Flamengo" in champ["team"]
        assert champ["points"] == 90
        assert champ["wins"] + champ["draws"] + champ["losses"] == 38

    def test_2017_champion_is_corinthians(self, engine):
        # Given the match data is loaded (multiple Atlético clubs present)
        # When I ask who won the 2017 Brasileirão
        champ = engine.champion(2017, "Brasileirão Série A")["champion"]
        # Then it is Corinthians (proving the Atlético clubs were not merged)
        assert "Corinthians" in champ["team"]
        assert champ["wins"] + champ["draws"] + champ["losses"] == 38


class TestRelegation:
    def test_2019_relegated_teams_match_history(self, engine):
        # Given the match data is loaded
        # When I ask which teams were relegated in 2019
        rel = engine.relegated_teams(2019, "Brasileirão Série A", count=4)["relegated"]
        # Then the four historically-relegated clubs are returned
        names = {r["team"] for r in rel}
        expected = {"Cruzeiro", "CSA", "Chapecoense", "Avaí"}
        assert expected.issubset(names)
