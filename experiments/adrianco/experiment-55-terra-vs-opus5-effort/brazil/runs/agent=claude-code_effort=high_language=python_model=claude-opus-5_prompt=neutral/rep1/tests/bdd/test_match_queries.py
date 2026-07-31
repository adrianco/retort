"""BDD scenarios for tests/features/match_queries.feature.

Context
-------
One test per scenario in the feature file, written with the
:class:`tests.gwt.Scenario` harness so the Given/When/Then structure is real
rather than commentary.  All scenarios run against the full, unmocked datasets.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.queries import QueryError, find_matches, head_to_head
from tests.gwt import Scenario

pytestmark = pytest.mark.bdd


def test_find_matches_between_two_teams(graph):
    with Scenario("Find matches between two teams") as s:
        s.given("the match data is loaded", lambda: graph.matches)
        result = s.when(
            'I search for matches between "Flamengo" and "Fluminense"',
            lambda: head_to_head("Flamengo", "Fluminense", limit=100, graph=graph),
        )
        s.then("I should receive a list of matches", len(result["matches"]) > 20)
        s.and_("each match should have date, scores and competition",
               all(m["date"] and m["competition"] and m["score"]
                   for m in result["matches"]))
        s.and_("the fixture should be recognised as the Fla-Flu derby",
               result["derby_name"] == "Fla-Flu")
        s.and_("wins and draws should account for every played match",
               result["summary"]["team_a_wins"] + result["summary"]["team_b_wins"]
               + result["summary"]["draws"] == result["total_matches"])


def test_find_matches_for_one_team_in_one_season(graph):
    with Scenario("Find matches for one team in one season") as s:
        result = s.when(
            'I search for "Palmeiras" matches in season 2023',
            lambda: find_matches(team="Palmeiras", season=2023, limit=500,
                                 graph=graph),
        )
        s.then("I should receive matches", result["total_matches"] > 30)
        s.and_("every returned match should involve Palmeiras",
               all("palmeiras" in (m["home_slug"], m["away_slug"])
                   for m in result["matches"]))
        s.and_("every returned match should be from 2023",
               all(m["season"] == 2023 for m in result["matches"]))


def test_restrict_a_search_to_home_fixtures(graph):
    with Scenario("Restrict a search to home fixtures") as s:
        result = s.when(
            'I search for "Corinthians" home matches in the 2022 Brasileirão',
            lambda: find_matches(team="Corinthians", venue="home",
                                 competition="brasileirao", season=2022,
                                 limit=100, graph=graph),
        )
        s.then("there should be 19 matches", result["total_matches"] == 19)
        s.and_("Corinthians should be the home side in all of them",
               all(m["home_slug"] == "corinthians" for m in result["matches"]))


def test_find_all_copa_do_brasil_finals(graph):
    with Scenario("Find all Copa do Brasil finals") as s:
        result = s.when(
            'I search Copa do Brasil matches with stage "Final"',
            lambda: find_matches(competition="copa-do-brasil", stage="Final",
                                 limit=100, graph=graph),
        )
        s.then("finals should be found", result["total_matches"] == 18)
        s.and_("only fixtures labelled Final should be returned",
               all(m["stage"] == "Final" for m in result["matches"]))
        s.and_("no semifinal should be included",
               not any("Semi" in (m["stage"] or "") for m in result["matches"]))
        s.and_("the 2019 final should be Athletico Paranaense vs Internacional",
               {"athletico-pr", "internacional"} == {
                   m["home_slug"] for m in result["matches"] if m["season"] == 2019
               } | {m["away_slug"] for m in result["matches"] if m["season"] == 2019})


def test_find_matches_in_a_date_range(graph):
    with Scenario("Find matches in a date range") as s:
        result = s.when(
            "I search for matches between 2019-05-01 and 2019-05-31",
            lambda: find_matches(date_from="2019-05-01", date_to="2019-05-31",
                                 limit=500, graph=graph),
        )
        s.then("matches should be found", result["total_matches"] > 50)
        s.and_("every match should fall inside that range",
               all("2019-05-01" <= m["date"] <= "2019-05-31"
                   for m in result["matches"]))


def test_team_names_are_normalised_before_searching(graph):
    with Scenario("Team names are normalised before searching") as s:
        spellings = ["Atletico-PR", "Athletico Paranaense", "Atlético - PR",
                     "ATHLETICO PR"]
        totals = s.when(
            "I search for every spelling of Athletico Paranaense",
            lambda: [find_matches(team=name, season=2019, limit=1, graph=graph)
                     for name in spellings],
        )
        s.then("all searches should return the same number of matches",
               len({r["total_matches"] for r in totals}) == 1)
        s.and_("and the same canonical club name",
               len({r["query"]["team"] for r in totals}) == 1)


def test_an_unknown_club_produces_a_helpful_error(graph):
    with Scenario("An unknown club produces a helpful error") as s:
        with pytest.raises(QueryError) as excinfo:
            s.when('I search for matches for "Wolverhampton Wanderers"',
                   lambda: find_matches(team="Wolverhampton Wanderers", graph=graph))
        s.then("the query should fail rather than return an empty list",
               "No team matching" in str(excinfo.value))


def test_date_parsing_accepts_brazilian_format(graph):
    with Scenario("Brazilian date format is accepted") as s:
        iso = s.when("I search with ISO dates",
                     lambda: find_matches(competition="serie-a",
                                          date_from="2019-05-01",
                                          date_to="2019-05-31", limit=1,
                                          graph=graph))
        br = s.when("I search with DD/MM/YYYY dates",
                    lambda: find_matches(competition="serie-a",
                                         date_from="01/05/2019",
                                         date_to="31/05/2019", limit=1,
                                         graph=graph))
        s.then("both should return the same count",
               iso["total_matches"] == br["total_matches"])
