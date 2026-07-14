"""BDD scenarios: match queries (TASK.md capability 1).

Feature: Match Queries
  Find matches by team, opponent, date range, competition and season.
"""

from team_normalizer import team_matches


class TestFindMatchesBetweenTwoTeams:
    """Scenario: Find matches between two teams (the Fla-Flu derby)."""

    def test_returns_a_list_of_matches(self, kb):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = kb.find_matches(team="Flamengo", opponent="Fluminense", limit=0)
        # Then I should receive a list of matches
        assert len(matches) >= 40
        # And each match should have date, scores, and competition
        for m in matches:
            assert m.date is not None
            assert isinstance(m.home_goal, int) and isinstance(m.away_goal, int)
            assert m.competition
            assert team_matches("Flamengo", m.home_team) or team_matches("Flamengo", m.away_team)
            assert team_matches("Fluminense", m.home_team) or team_matches("Fluminense", m.away_team)

    def test_head_to_head_summary(self, kb):
        # When I ask for the head-to-head record
        h2h = kb.head_to_head("Flamengo", "Fluminense")
        # Then wins, draws and totals are consistent
        rec = h2h["record"]
        assert h2h["total_matches"] == (
            rec["team1_wins"] + rec["team2_wins"] + rec["draws"]
        )
        assert h2h["total_matches"] == len(h2h["matches"])
        assert h2h["total_matches"] >= 40


class TestFindMatchesBySeason:
    """Scenario: What matches did Palmeiras play in 2023?"""

    def test_palmeiras_2023(self, kb):
        matches = kb.find_matches(team="Palmeiras", season=2023, limit=0)
        # Then a full league season (plus cup games) is returned
        assert len(matches) >= 38
        assert all(m.season == 2023 for m in matches)
        assert all(
            team_matches("Palmeiras", m.home_team)
            or team_matches("Palmeiras", m.away_team)
            for m in matches
        )


class TestFindMatchesByCompetition:
    def test_competition_filter(self, kb):
        # When I filter Flamengo matches to Copa do Brasil only
        matches = kb.find_matches(team="Flamengo", competition="Copa do Brasil", limit=0)
        # Then only cup matches are returned
        assert matches
        assert all(m.competition == "Copa do Brasil" for m in matches)

    def test_competition_name_variants(self, kb):
        # Given competition aliases ("Brasileirão", "Serie A", "Série A")
        a = kb.find_matches(team="Santos", competition="Brasileirão", season=2019, limit=0)
        b = kb.find_matches(team="Santos", competition="Serie A", season=2019, limit=0)
        assert len(a) == len(b) == 38


class TestFindMatchesByDateRange:
    def test_date_range_filter(self, kb):
        # When I search Flamengo matches within May 2019
        matches = kb.find_matches(
            team="Flamengo", date_from="2019-05-01", date_to="2019-05-31", limit=0,
        )
        # Then all matches fall inside the range
        assert matches
        for m in matches:
            assert "2019-05-01" <= m.date.isoformat() <= "2019-05-31"

    def test_brazilian_date_format_accepted(self, kb):
        # Given a date range supplied in DD/MM/YYYY format
        a = kb.find_matches(team="Flamengo", date_from="01/05/2019", date_to="31/05/2019", limit=0)
        b = kb.find_matches(team="Flamengo", date_from="2019-05-01", date_to="2019-05-31", limit=0)
        assert len(a) == len(b)


class TestMostRecentMatch:
    """Scenario: When did Flamengo last play Corinthians, and what was the score?"""

    def test_results_sorted_newest_first(self, kb):
        matches = kb.find_matches(team="Flamengo", opponent="Corinthians", limit=5)
        dates = [m.date for m in matches]
        assert dates == sorted(dates, reverse=True)

    def test_last_flamengo_corinthians(self, kb):
        latest = kb.find_matches(team="Flamengo", opponent="Corinthians", limit=1)[0]
        # Then the most recent meeting in the data is returned with its score
        assert latest.date.isoformat() == "2023-10-08"
        assert f"{latest.home_goal}-{latest.away_goal}" == "1-1"
