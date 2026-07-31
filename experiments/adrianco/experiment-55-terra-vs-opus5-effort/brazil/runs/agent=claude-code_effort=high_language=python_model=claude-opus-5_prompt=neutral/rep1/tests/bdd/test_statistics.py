"""BDD scenarios for tests/features/statistics.feature."""

from __future__ import annotations

import pytest

from brazilian_soccer.queries import (
    biggest_wins,
    compare_seasons,
    competition_stats,
    find_derbies,
)
from tests.gwt import Scenario

pytestmark = pytest.mark.bdd


def test_average_goals_per_match(graph):
    with Scenario("Average goals per match") as s:
        s.given("the match data is loaded", lambda: graph.matches)
        result = s.when("I request Brasileirão aggregate statistics",
                        lambda: competition_stats("brasileirao", graph=graph))
        s.then("the average goals per match should be between 2 and 3",
               2.0 < result["goals_per_match"] < 3.0)
        s.and_("the home, away and draw rates should sum to 100 percent",
               abs(result["home_win_rate"] + result["away_win_rate"]
                   + result["draw_rate"] - 100.0) < 0.2)
        s.and_("home wins should outnumber away wins",
               result["home_wins"] > result["away_wins"])
        s.and_("goals should equal home goals plus away goals",
               result["goals"] == result["home_goals"] + result["away_goals"])
        s.and_("the lack of goalscorer data should be disclosed",
               any("goalscorer" in note for note in result["notes"]))


def test_biggest_wins(graph):
    with Scenario("Biggest wins") as s:
        result = s.when("I request the biggest victories in the datasets",
                        lambda: biggest_wins(limit=20, graph=graph))
        margins = [m["margin"] for m in result["results"]]
        s.then("results should be returned", len(margins) == 20)
        s.and_("the results should be ordered by winning margin",
               margins == sorted(margins, reverse=True))
        s.and_("the largest margin should be at least 7 goals", margins[0] >= 7)
        s.and_("each result should name a winner",
               all(m["winner"] for m in result["results"]))


def test_duplicate_fixtures_are_not_double_counted(graph):
    with Scenario("Duplicate fixtures are not double counted") as s:
        fixtures = s.when("I count Série A fixtures for the 2019 season",
                          lambda: graph.matches_by_comp_season[("serie-a", 2019)])
        s.then("there should be exactly 380 matches", len(fixtures) == 380)
        s.and_("every fixture should be unique",
               len({(m.home_slug, m.away_slug) for m in fixtures}) == 380)
        s.and_("most 2019 fixtures should come from more than one source file",
               sum(1 for m in fixtures if len(m.sources) > 1) > 300)
        s.and_("merged fixtures should keep the round from one file and the "
               "stadium from another",
               any(m.round and m.venue for m in fixtures))


def test_compare_two_seasons(graph):
    with Scenario("Compare two seasons") as s:
        result = s.when("I compare the 2018 and 2019 Brasileirão seasons",
                        lambda: compare_seasons([2018, 2019], "serie-a",
                                                graph=graph))
        rows = result["comparison"]
        s.then("both seasons should be reported", len(rows) == 2)
        s.and_("each season should report its champion",
               rows[0]["champion"] == "Palmeiras" and rows[1]["champion"] == "Flamengo")
        s.and_("each season should report goals per match",
               all(2 < row["goals_per_match"] < 3 for row in rows))
        s.and_("each season should have 380 matches",
               all(row["matches"] == 380 for row in rows))


def test_find_derbies_in_a_season(graph):
    with Scenario("Find derbies in a season") as s:
        result = s.when("I look for derbies in 2023",
                        lambda: find_derbies(season=2023, limit=100, graph=graph))
        names = {row["derby"] for row in result["derbies"]}
        s.then("derbies should be found", result["total_matches"] > 20)
        s.and_("the Fla-Flu should be present", "Fla-Flu" in names)
        s.and_("the Derby Paulista should be present", "Derby Paulista" in names)
        s.and_("the Gre-Nal should be present", "Gre-Nal" in names)
        s.and_("every listed match should be tagged with its derby name",
               all(m["derby"] for m in result["matches"]))


def test_home_advantage_is_visible_by_season(graph):
    with Scenario("Home advantage by season") as s:
        result = s.when("I ask for the season-by-season Brasileirão breakdown",
                        lambda: competition_stats("serie-a", graph=graph))
        seasons = result["by_season"]
        s.then("every season from 2003 to 2023 should appear",
               [row["season"] for row in seasons] == list(range(2003, 2024)))
        s.and_("home win rates should always be above 40 percent",
               all(row["home_win_rate"] > 40 for row in seasons))
        s.and_("goals per match should always be plausible",
               all(1.5 < row["goals_per_match"] < 4.0 for row in seasons))


def test_extended_statistics_are_merged_from_the_br_football_file(graph):
    with Scenario("Shot and corner statistics are merged in") as s:
        fixtures = s.when("I look at 2019 Série A fixtures",
                          lambda: graph.matches_by_comp_season[("serie-a", 2019)])
        with_stats = [m for m in fixtures if m.stats]
        s.then("most fixtures should carry corner/shot statistics",
               len(with_stats) > 300)
        s.and_("both sides should be recorded",
               all({"home", "away"} <= set(m.stats) for m in with_stats))
        s.and_("the statistics came from the BR-Football file",
               all("BR-Football-Dataset.csv" in m.sources for m in with_stats))
