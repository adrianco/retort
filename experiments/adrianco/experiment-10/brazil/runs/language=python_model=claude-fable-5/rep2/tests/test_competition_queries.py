"""BDD scenarios: competition queries (TASK.md capability 4).

Feature: Competition Queries
  Standings calculated from match results, champions, relegation, cup finals
  and tournament brackets.
"""

from team_normalizer import team_matches


class TestStandings:
    """Scenario: Who won the 2019 Brasileirão?"""

    def test_2019_champion_is_flamengo(self, kb):
        # Given the match data is loaded
        # When I calculate the 2019 Serie A standings
        result = kb.standings(2019)
        # Then Flamengo are champions with 90 points from 38 games
        assert team_matches("Flamengo", result["champion"])
        top = result["standings"][0]
        assert top["points"] == 90
        assert top["played"] == 38
        assert (top["wins"], top["draws"], top["losses"]) == (28, 6, 4)

    def test_table_is_complete_and_ordered(self, kb):
        result = kb.standings(2019)
        rows = result["standings"]
        # Then all 20 clubs appear, ordered by points
        assert len(rows) == 20
        points = [r["points"] for r in rows]
        assert points == sorted(points, reverse=True)
        assert [r["position"] for r in rows] == list(range(1, 21))
        # And every club played 38 matches
        assert all(r["played"] == 38 for r in rows)

    def test_2008_to_2019_historical_champions(self, kb):
        # Sanity-check a few known champions against calculated tables
        assert team_matches("São Paulo", kb.standings(2008)["champion"])
        assert team_matches("Corinthians", kb.standings(2017)["champion"])
        assert team_matches("Palmeiras", kb.standings(2018)["champion"])


class TestRelegation:
    """Scenario: Which teams were relegated in 2020?"""

    def test_2020_relegated_teams(self, kb):
        result = kb.standings(2020)
        relegated = result["relegated"]
        assert len(relegated) == 4
        expected = ("Vasco", "Goias", "Coritiba", "Botafogo-RJ")
        for name in expected:
            assert any(team_matches(name, t) for t in relegated), name


class TestCupFinals:
    """Scenario: Find all Copa do Brasil finals."""

    def test_finals_for_every_covered_season(self, kb):
        result = kb.cup_finals("Copa do Brasil")
        finals = result["finals_by_season"]
        # Then each fully-covered season (2012-2020; the data stops during
        # the 2021 edition) has a one- or two-legged final
        assert set(finals) >= {str(y) for y in range(2012, 2021)}
        for season, legs in finals.items():
            assert 1 <= len(legs) <= 2, season

    def test_2013_final_won_by_flamengo(self, kb):
        legs = kb.cup_finals()["finals_by_season"]["2013"]
        # Flamengo beat Atlético-PR 2-0 in the second leg
        last = legs[-1]
        assert team_matches("Flamengo", last["home_team"])
        assert last["score"] == "2-0"


class TestLibertadoresBracket:
    """Scenario: Show the 2018 Copa Libertadores bracket."""

    def test_2018_stages(self, kb):
        result = kb.libertadores_stage_results(2018)
        stages = result["stages"]
        assert {"group stage", "round of 16", "quarterfinals",
                "semifinals", "final"} <= set(stages)

    def test_2018_final(self, kb):
        result = kb.libertadores_stage_results(2018, stage="final")
        final_legs = result["stages"]["final"]
        # River Plate beat Boca Juniors 3-1 in the deciding leg
        decider = final_legs[-1]
        assert decider["home_team"] == "River Plate"
        assert decider["away_team"] == "Boca Juniors"
        assert decider["score"] == "3-1"
