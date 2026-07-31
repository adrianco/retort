"""Feature: Competition Queries.

Context
-------
Standings, champions, relegation and knockout brackets are all *derived* from
match results -- the datasets contain no table or trophy columns.  These
scenarios check the derivation against publicly known outcomes (Flamengo's
90-point 2019 title, Cruzeiro's 2018 Copa do Brasil, Flamengo's 2019
Libertadores) so a regression in de-duplication or points arithmetic fails
loudly.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.formatting import format_standings
from brazilian_soccer.models import BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES
from brazilian_soccer.queries import SoccerQueries


class TestStandings:
    def test_2019_brasileirao_matches_reality(self, queries: SoccerQueries) -> None:
        # Given the 2019 Brasileirão match results
        # When the table is calculated
        table = queries.standings(BRASILEIRAO, 2019)
        # Then it reproduces the real final table
        assert len(table) == 20
        champion = table[0]
        assert champion.team_name == "Flamengo-RJ"
        assert champion.points == 90
        assert (champion.wins, champion.draws, champion.losses) == (28, 6, 4)
        assert {table[1].team_name, table[2].team_name} == {"Santos-SP", "Palmeiras"}
        assert table[1].points == 74 and table[2].points == 74

    @pytest.mark.parametrize(
        "season,expected_champion,expected_points",
        [
            (2015, "Corinthians", 81),
            (2017, "Corinthians", 72),
            (2018, "Palmeiras", 80),
            (2019, "Flamengo-RJ", 90),
            (2022, "Palmeiras", 81),
        ],
    )
    def test_known_champions(
        self,
        queries: SoccerQueries,
        season: int,
        expected_champion: str,
        expected_points: int,
    ) -> None:
        table = queries.standings(BRASILEIRAO, season)
        assert table[0].team_name == expected_champion
        assert table[0].points == expected_points

    def test_table_is_internally_consistent(self, queries: SoccerQueries) -> None:
        table = queries.standings(BRASILEIRAO, 2021)
        # Every club plays 38 matches
        assert all(record.played == 38 for record in table)
        # Goals for and goals against balance across the league
        assert sum(r.goals_for for r in table) == sum(r.goals_against for r in table)
        # Wins balance losses
        assert sum(r.wins for r in table) == sum(r.losses for r in table)
        # Draws are counted twice, once per club
        assert sum(r.draws for r in table) % 2 == 0
        # And the table is sorted by points then goal difference
        keys = [(-r.points, -r.goal_difference, -r.goals_for) for r in table]
        assert keys == sorted(keys)

    def test_standings_on_a_known_tiny_league(self, tiny_queries: SoccerQueries) -> None:
        table = tiny_queries.standings(BRASILEIRAO, 2020)
        assert [r.team_name for r in table] == ["Gamma", "Alpha", "Beta"]
        assert [r.points for r in table] == [4, 3, 1]

    def test_standings_render_with_champion_and_relegation_tags(
        self, queries: SoccerQueries
    ) -> None:
        text = format_standings(queries.standings(BRASILEIRAO, 2019), BRASILEIRAO, 2019)
        assert "calculated from match results" in text
        assert " 1. Flamengo-RJ - 90 pts" in text
        assert "Champion" in text
        assert "Relegation zone" in text

    def test_empty_season_is_reported(self, queries: SoccerQueries) -> None:
        assert queries.standings(BRASILEIRAO, 1899) == []
        assert "No " in format_standings([], BRASILEIRAO, 1899)


class TestChampions:
    def test_league_champion_is_the_table_leader(self, queries: SoccerQueries) -> None:
        result = queries.champion(BRASILEIRAO, 2019)
        assert result["champion"] == "Flamengo-RJ"
        assert "league table" in result["basis"]
        assert result["runner_up"] in {"Santos-SP", "Palmeiras"}

    @pytest.mark.parametrize(
        "season,expected",
        [(2018, "Cruzeiro"), (2019, "Atletico-PR"), (2020, "Palmeiras")],
    )
    def test_copa_do_brasil_finals(
        self, queries: SoccerQueries, season: int, expected: str
    ) -> None:
        # Given a season whose final is labelled in the cup file
        result = queries.champion(COPA_DO_BRASIL, season)
        # Then the winner on aggregate is reported
        assert result["champion"] == expected

    def test_penalty_shootout_is_not_guessed(self, queries: SoccerQueries) -> None:
        # Given the 2017 Copa do Brasil final finished 1-1 on aggregate
        result = queries.champion(COPA_DO_BRASIL, 2017)
        # Then no winner is invented; the finalists and the reason are reported
        assert result["champion"] is None
        assert "penalties" in result["basis"]
        assert set(result["finalists"]) == {"Cruzeiro", "Flamengo-RJ"}

    def test_libertadores_2019_was_flamengo(self, queries: SoccerQueries) -> None:
        result = queries.champion(LIBERTADORES, 2019)
        assert result["champion"] == "Flamengo-RJ"
        assert result["matches"]

    def test_missing_final_is_admitted(self, queries: SoccerQueries) -> None:
        # Given the 2021 Libertadores final is absent from the dataset
        result = queries.champion(LIBERTADORES, 2021)
        # Then the answer either says so or flags the weaker inference
        assert result["champion"] is None or "inferred" in result["basis"]


class TestRelegation:
    def test_2020_relegation_zone(self, queries: SoccerQueries) -> None:
        # When I ask which teams were relegated in 2020
        result = queries.relegated(2020)
        # Then the bottom four of the calculated table come back
        assert len(result["relegated"]) == 4
        names = [row["team"] for row in result["relegated"]]
        assert names == ["Vasco Gama", "Goias", "Coritiba", "Botafogo-RJ"]
        assert "calculated from match results" in result["note"]

    def test_relegated_teams_are_the_table_bottom(self, queries: SoccerQueries) -> None:
        table = queries.standings(BRASILEIRAO, 2018)
        result = queries.relegated(2018)
        assert [row["team"] for row in result["relegated"]] == [
            record.team_name for record in table[-4:]
        ]


class TestBrackets:
    def test_libertadores_bracket_is_ordered_by_stage(
        self, queries: SoccerQueries
    ) -> None:
        bracket = queries.season_bracket(LIBERTADORES, 2019)
        stages = list(bracket["stages"])
        # Then stages run group stage -> round of 16 -> quarters -> semis -> final
        assert stages[0] == "group stage"
        assert stages[-1] == "final"
        assert len(bracket["stages"]["round of 16"]) == 16
        assert len(bracket["stages"]["semifinals"]) == 4

    def test_cup_bracket_covers_every_round(self, queries: SoccerQueries) -> None:
        bracket = queries.season_bracket(COPA_DO_BRASIL, 2018)
        assert bracket["stages"]
        total = sum(len(matches) for matches in bracket["stages"].values())
        assert total == len(
            queries.search_matches(competition=COPA_DO_BRASIL, season=2018, limit=None)
        )


class TestCoverage:
    def test_all_five_competitions_are_queryable(self, queries: SoccerQueries) -> None:
        competitions = queries.graph.competitions
        assert len(competitions) == 5
        for competition in competitions:
            seasons = queries.graph.seasons_for(competition)
            assert seasons
            assert queries.search_matches(
                competition=competition, season=seasons[-1], limit=5
            )

    def test_season_coverage_spans_2003_to_2023(self, queries: SoccerQueries) -> None:
        overview = queries.dataset_overview()
        assert overview["season_range"] == [2003, 2023]
