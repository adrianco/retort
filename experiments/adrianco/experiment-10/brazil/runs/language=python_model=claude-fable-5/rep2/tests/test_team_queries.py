"""BDD scenarios: team queries (TASK.md capability 2).

Feature: Team Queries
  Match history, win/loss/draw records, goals, and per-competition splits.
"""

from team_normalizer import team_matches


class TestTeamSeasonStatistics:
    """Scenario: Get team statistics.

    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
    """

    def test_palmeiras_2023_statistics(self, kb):
        stats = kb.team_statistics("Palmeiras", season=2023)
        assert stats["matches"] > 0
        assert stats["matches"] == stats["wins"] + stats["draws"] + stats["losses"]
        assert stats["goals_for"] > 0
        assert stats["goals_against"] > 0
        assert 0 <= stats["win_rate"] <= 100


class TestHomeRecord:
    """Scenario: What is Corinthians' home record in 2022?"""

    def test_corinthians_home_2022(self, kb):
        # When I request the home record for the 2022 Brasileirão
        stats = kb.team_statistics(
            "Corinthians", season=2022, competition="Brasileirão", venue="home",
        )
        # Then the 19 home fixtures of a 38-round season are returned
        assert stats["matches"] == 19
        assert (stats["wins"], stats["draws"], stats["losses"]) == (12, 4, 3)
        assert stats["goals_for"] == 24
        assert stats["goals_against"] == 11
        assert stats["win_rate"] == 63.2

    def test_home_plus_away_equals_total(self, kb):
        home = kb.team_statistics("Santos", season=2019, competition="Serie A", venue="home")
        away = kb.team_statistics("Santos", season=2019, competition="Serie A", venue="away")
        total = kb.team_statistics("Santos", season=2019, competition="Serie A")
        assert home["matches"] + away["matches"] == total["matches"] == 38
        assert home["wins"] + away["wins"] == total["wins"]


class TestNameVariantsGiveSameAnswer:
    """Scenario: team name variations are handled correctly."""

    def test_suffix_and_accent_variants(self, kb):
        a = kb.team_statistics("Sao Paulo", season=2019, competition="Serie A")
        b = kb.team_statistics("São Paulo", season=2019, competition="Serie A")
        c = kb.team_statistics("Sao Paulo-SP", season=2019, competition="Serie A")
        assert a["matches"] == b["matches"] == c["matches"] == 38
        assert a["points"] == b["points"] == c["points"]


class TestCompetitionsPlayed:
    """Scenario: What competitions has Palmeiras played in?"""

    def test_palmeiras_competitions(self, kb):
        result = kb.list_team_competitions("Palmeiras")
        comps = set(result["competitions"])
        assert {"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"} <= comps
        # And each competition lists the seasons covered
        assert all(result["competitions"][c] for c in comps)


class TestHeadToHeadComparison:
    """Scenario: Compare Palmeiras and Santos head-to-head."""

    def test_palmeiras_santos(self, kb):
        h2h = kb.head_to_head("Palmeiras", "Santos")
        assert h2h["total_matches"] >= 30
        rec = h2h["record"]
        assert h2h["total_matches"] == rec["team1_wins"] + rec["team2_wins"] + rec["draws"]
        # And every listed match involves both clubs
        for m in h2h["matches"]:
            teams = (m["home_team"], m["away_team"])
            assert any(team_matches("Palmeiras", t) for t in teams)
            assert any(team_matches("Santos", t) for t in teams)
