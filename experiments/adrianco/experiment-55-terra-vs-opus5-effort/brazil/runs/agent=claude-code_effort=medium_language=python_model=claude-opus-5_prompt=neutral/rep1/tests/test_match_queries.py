"""Feature: Match Queries.

Context
-------
Implements the Gherkin scenarios in ``TASK.md``::

    Scenario: Find matches between two teams
      Given the match data is loaded
      When I search for matches between "Flamengo" and "Fluminense"
      Then I should receive a list of matches
      And each match should have date, scores, and competition

plus the by-team / by-date / by-competition / by-season filters and the
head-to-head summary.
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer.formatting import format_head_to_head, format_matches
from brazilian_soccer.models import BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES
from brazilian_soccer.queries import SoccerQueries, TeamNotFound


class TestFindMatchesBetweenTwoTeams:
    def test_flamengo_versus_fluminense(self, queries: SoccerQueries) -> None:
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = queries.search_matches(
            team="Flamengo", opponent="Fluminense", limit=None
        )
        # Then I should receive a list of matches
        assert len(matches) > 20
        # And each match should have date, scores and competition
        for match in matches:
            assert match.match_date is not None
            assert match.has_score
            assert match.competition
            assert {match.home_key, match.away_key} == {"flamengo-rj", "fluminense-rj"}

    def test_head_to_head_totals_add_up(self, queries: SoccerQueries) -> None:
        # When I ask for the Fla-Flu head-to-head
        h2h = queries.head_to_head("Flamengo", "Fluminense")
        # Then wins + draws equal the number of matches played
        assert h2h.a_wins + h2h.b_wins + h2h.draws == h2h.total
        assert h2h.a_goals > 0 and h2h.b_goals > 0
        # And the rendering states the record explicitly
        text = format_head_to_head(h2h)
        assert "Head-to-head in dataset:" in text
        assert f"{h2h.a_wins} wins" in text

    def test_head_to_head_is_symmetric(self, queries: SoccerQueries) -> None:
        forward = queries.head_to_head("Palmeiras", "Santos")
        reverse = queries.head_to_head("Santos", "Palmeiras")
        assert forward.total == reverse.total
        assert forward.a_wins == reverse.b_wins
        assert forward.draws == reverse.draws

    def test_last_meeting_is_the_newest_match(self, queries: SoccerQueries) -> None:
        # When I ask when Flamengo last played Corinthians
        last = queries.last_meeting("Flamengo", "Corinthians")
        all_meetings = queries.search_matches(
            team="Flamengo", opponent="Corinthians", limit=None
        )
        # Then it is the most recent meeting in the data, with a score
        assert last is not None
        assert last.match_date == max(m.match_date for m in all_meetings)
        assert last.has_score

    def test_teams_that_never_met(self, queries: SoccerQueries) -> None:
        h2h = queries.head_to_head("Boca Juniors", "Botafogo-PB")
        assert h2h.total == 0
        assert "No meetings" in format_head_to_head(h2h)


class TestFilterMatches:
    def test_by_team_and_season(self, queries: SoccerQueries) -> None:
        # When I ask what matches Palmeiras played in 2023
        matches = queries.search_matches(team="Palmeiras", season=2023, limit=None)
        # Then every result is a 2023 Palmeiras match
        assert matches
        assert all(m.season == 2023 for m in matches)
        assert all(m.involves("palmeiras") for m in matches)

    @pytest.mark.parametrize(
        "competition", [BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES]
    )
    def test_by_competition(self, queries: SoccerQueries, competition: str) -> None:
        matches = queries.search_matches(competition=competition, limit=None)
        assert matches
        assert {m.competition for m in matches} == {competition}

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("brasileirao", BRASILEIRAO),
            ("Brasileirão", BRASILEIRAO),
            ("serie a", BRASILEIRAO),
            ("libertadores", LIBERTADORES),
            ("Copa do Brasil", COPA_DO_BRASIL),
            ("copa", COPA_DO_BRASIL),
        ],
    )
    def test_competition_aliases_resolve(
        self, queries: SoccerQueries, alias: str, expected: str
    ) -> None:
        assert queries._competition(alias) == expected

    def test_unknown_competition_is_reported(self, queries: SoccerQueries) -> None:
        with pytest.raises(ValueError, match="Unknown competition"):
            queries.search_matches(competition="Premier League")

    def test_by_date_range(self, queries: SoccerQueries) -> None:
        # When I search a date window
        matches = queries.search_matches(
            date_from="2023-01-01", date_to="2023-06-30", limit=None
        )
        assert matches
        assert all(date(2023, 1, 1) <= m.match_date <= date(2023, 6, 30) for m in matches)

    def test_by_brazilian_format_date(self, queries: SoccerQueries) -> None:
        matches = queries.search_matches(
            team="Corinthians", date_from="01/01/2015", date_to="31/12/2015", limit=None
        )
        assert matches
        assert all(m.match_date.year == 2015 for m in matches)

    def test_by_venue(self, queries: SoccerQueries) -> None:
        # When I ask for Santos home matches only
        home = queries.search_matches(team="Santos", venue="home", limit=None)
        away = queries.search_matches(team="Santos", venue="away", limit=None)
        every = queries.search_matches(team="Santos", limit=None)
        assert all(m.home_key == "santos-sp" for m in home)
        assert all(m.away_key == "santos-sp" for m in away)
        assert len(home) + len(away) == len(every)

    def test_by_season_range(self, queries: SoccerQueries) -> None:
        matches = queries.search_matches(
            team="Cruzeiro", season_from=2010, season_to=2012, limit=None
        )
        assert matches
        assert all(2010 <= m.season <= 2012 for m in matches)

    def test_by_stage_finds_cup_finals_only(self, queries: SoccerQueries) -> None:
        # When I ask for all Copa do Brasil finals
        finals = queries.search_matches(
            competition=COPA_DO_BRASIL, stage="final", limit=None
        )
        # Then semi-finals and quarter-finals are excluded
        assert finals
        assert all("final" in (m.stage or "") for m in finals)
        assert not any("semi" in (m.stage or "") for m in finals)
        assert not any("quarter" in (m.stage or "") for m in finals)
        # And each final is a two-legged tie in a known season
        assert {m.season for m in finals} >= {2017, 2018, 2019, 2020}

    def test_results_are_newest_first(self, queries: SoccerQueries) -> None:
        matches = queries.search_matches(team="Gremio", limit=20)
        dates = [m.match_date for m in matches]
        assert dates == sorted(dates, reverse=True)

    def test_limit_is_respected(self, queries: SoccerQueries) -> None:
        assert len(queries.search_matches(team="Gremio", limit=5)) == 5

    def test_unknown_team_raises_with_suggestions(self, queries: SoccerQueries) -> None:
        with pytest.raises(TeamNotFound):
            queries.search_matches(team="Real Madrid Castilla B")


class TestDerbies:
    def test_derbies_are_tagged(self, queries: SoccerQueries) -> None:
        # When I ask for derbies in 2023
        rows = queries.derbies(season=2023)
        # Then every row names the rivalry and both clubs are the rivals
        assert rows
        names = {row["derby"] for row in rows}
        assert "Fla-Flu" in names or "Derby Paulista" in names
        assert all(row["match"].season == 2023 for row in rows)

    def test_fla_flu_is_a_known_derby(self, queries: SoccerQueries) -> None:
        rows = queries.derbies()
        fla_flu = [row for row in rows if row["derby"] == "Fla-Flu"]
        assert fla_flu
        for row in fla_flu:
            assert {row["match"].home_key, row["match"].away_key} == {
                "flamengo-rj",
                "fluminense-rj",
            }


class TestMatchFormatting:
    def test_match_lines_carry_date_score_and_competition(
        self, queries: SoccerQueries
    ) -> None:
        matches = queries.search_matches(team="Flamengo", season=2019, limit=3)
        text = format_matches(matches, "Flamengo 2019:")
        assert "Flamengo 2019:" in text
        for match in matches:
            assert match.match_date.isoformat() in text
            assert f"{match.home_goals}-{match.away_goals}" in text
            assert match.competition in text

    def test_truncation_is_disclosed(self, queries: SoccerQueries) -> None:
        matches = queries.search_matches(team="Flamengo", limit=None)
        text = format_matches(matches, "All Flamengo matches:", limit=10)
        assert f"({len(matches) - 10} more matches in dataset)" in text

    def test_empty_result_is_explicit(self) -> None:
        assert "No matches found" in format_matches([], "Nothing:")
