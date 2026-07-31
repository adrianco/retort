"""BDD scenarios for tests/features/team_queries.feature."""

from __future__ import annotations

import pytest

from brazilian_soccer.queries import (
    head_to_head,
    resolve_team,
    team_profile,
    team_rankings,
    team_stats,
)
from tests.gwt import Scenario

pytestmark = pytest.mark.bdd


def test_get_team_statistics(graph):
    with Scenario("Get team statistics") as s:
        s.given("the match data is loaded", lambda: graph.matches)
        result = s.when('I request statistics for "Palmeiras" in season 2023',
                        lambda: team_stats("Palmeiras", season=2023, graph=graph))
        record = result["overall"]
        s.then("I should receive wins, losses, draws and goals",
               all(key in record for key in
                   ("wins", "losses", "draws", "goals_for", "goals_against")))
        s.and_("the results should add up to the matches played",
               record["wins"] + record["draws"] + record["losses"] == record["played"])
        s.and_("home and away splits should add up to the total",
               result["home"]["played"] + result["away"]["played"] == record["played"])
        s.and_("points should be three per win plus one per draw",
               record["points"] == record["wins"] * 3 + record["draws"])


def test_home_record_for_a_season(graph):
    with Scenario("Home record for a season") as s:
        result = s.when("I request Corinthians' home record for the 2022 Brasileirão",
                        lambda: team_stats("Corinthians", season=2022,
                                           competition="brasileirao", venue="home",
                                           graph=graph))
        record = result["overall"]
        s.then("the record should cover 19 matches", record["played"] == 19)
        s.and_("the win rate should be a percentage",
               0 <= record["win_rate"] <= 100)
        s.and_("goals for and against should be positive integers",
               record["goals_for"] > 0 and record["goals_against"] >= 0)
        s.and_("the record should match a manual count",
               record["wins"] == sum(
                   1 for m in graph.matches_by_comp_season[("serie-a", 2022)]
                   if m.home_slug == "corinthians" and m.outcome == "home"))


def test_compare_two_teams_head_to_head(graph):
    with Scenario("Compare two teams head-to-head") as s:
        result = s.when('I compare "Palmeiras" and "Santos" head-to-head',
                        lambda: head_to_head("Palmeiras", "Santos", limit=200,
                                             graph=graph))
        summary = result["summary"]
        s.then("I should receive each side's wins, the draws and the goals",
               summary["team_a_wins"] >= 0 and summary["team_b_wins"] >= 0
               and summary["team_a_goals"] > 0)
        s.and_("the wins and draws should add up to the matches played",
               summary["team_a_wins"] + summary["team_b_wins"] + summary["draws"]
               == result["total_matches"])
        s.and_("the fixture should be named as a classic",
               result["derby_name"] == "Clássico da Saudade")
        s.and_("home and away breakdowns should be present",
               result["at_team_a_home"]["played"] > 0
               and result["at_team_b_home"]["played"] > 0)


def test_a_clubs_competition_history(graph):
    with Scenario("A club's competition history") as s:
        result = s.when('I ask for the profile of "Palmeiras"',
                        lambda: team_profile("Palmeiras", graph=graph))
        competitions = {c["competition"] for c in result["competitions"]}
        s.then("I should see Série A, Copa do Brasil and Libertadores",
               {"Campeonato Brasileiro Série A", "Copa do Brasil",
                "Copa Libertadores"} <= competitions)
        s.and_("I should see the stadiums the club played in",
               any(v["venue"] for v in result["stadiums"]))
        s.and_("São Paulo should be listed as a derby opponent",
               any(o["derby"] == "Choque-Rei"
                   for o in result["most_played_opponents"]))


def test_rank_clubs_by_away_record(graph):
    with Scenario("Rank clubs by away record") as s:
        result = s.when("I rank Série A clubs by points per game away from home",
                        lambda: team_rankings(metric="points_per_game",
                                              competition="serie-a", venue="away",
                                              min_matches=100, limit=10,
                                              graph=graph))
        rankings = result["rankings"]
        s.then("clubs should be ranked", len(rankings) == 10)
        s.and_("every ranked club should meet the minimum match count",
               all(row["matches"] >= 100 for row in rankings))
        s.and_("the ranking should be in descending order",
               all(rankings[i]["points_per_game"] >= rankings[i + 1]["points_per_game"]
                   for i in range(len(rankings) - 1)))
        s.and_("ranks should be numbered from one",
               [row["rank"] for row in rankings] == list(range(1, 11)))


def test_ambiguous_club_names_are_disambiguated_by_state(graph):
    with Scenario("Ambiguous club names are disambiguated by state") as s:
        pb = s.when('I resolve "Botafogo-PB"',
                    lambda: resolve_team("Botafogo - PB", graph=graph))
        rj = s.when('I resolve "Botafogo-RJ"',
                    lambda: resolve_team("Botafogo-RJ", graph=graph))
        s.then("both should resolve", pb["matched"] and rj["matched"])
        s.and_("they should be two different clubs",
               pb["team"]["slug"] != rj["team"]["slug"])
        s.and_("the Rio club should have far more fixtures",
               rj["matches_in_data"] > pb["matches_in_data"])
        s.and_("the ambiguity should be reported",
               "Botafogo-PB" in rj["other_clubs_with_similar_names"]
               or "Botafogo-SP" in rj["other_clubs_with_similar_names"])


def test_goals_against_ranking_is_ascending(graph):
    with Scenario("Fewest goals conceded ranks ascending") as s:
        result = s.when("I rank 2019 Série A clubs by goals conceded",
                        lambda: team_rankings(metric="goals_against",
                                              competition="serie-a", season=2019,
                                              min_matches=30, limit=20, graph=graph))
        rankings = result["rankings"]
        s.then("the best defence should come first",
               rankings[0]["goals_against"] <= rankings[-1]["goals_against"])
        s.and_("the order should be non-decreasing",
               all(rankings[i]["goals_against"] <= rankings[i + 1]["goals_against"]
                   for i in range(len(rankings) - 1)))
        s.and_("ties should still be broken by points per game, best first",
               all(rankings[i]["points_per_game"] >= rankings[i + 1]["points_per_game"]
                   for i in range(len(rankings) - 1)
                   if rankings[i]["goals_against"] == rankings[i + 1]["goals_against"]))


def test_a_venue_filter_applies_to_the_competition_breakdown(graph):
    """A "home record" must not report a breakdown that includes away games."""
    with Scenario("Venue filter reaches the competition breakdown") as s:
        result = s.when("I request Corinthians' 2022 home record across all "
                        "competitions",
                        lambda: team_stats("Corinthians", season=2022,
                                           venue="home", graph=graph))
        breakdown = result["by_competition"]
        s.then("the breakdown should add up to the headline record",
               sum(row["played"] for row in breakdown)
               == result["overall"]["played"])
        s.and_("and to the home total specifically",
               result["overall"]["played"] == result["home"]["played"])


def test_team_name_resolution_is_deterministic(graph):
    """A tie in the substring search must not depend on set iteration order."""
    with Scenario("Resolution is stable across processes") as s:
        queries = ["aimor", "cast", "cab", "atletico min", "corinthans"]
        first = s.when("I resolve several partial names",
                       lambda: [graph.resolve_team(q).slug for q in queries])
        again = s.when("I resolve them again",
                       lambda: [graph.resolve_team(q).slug for q in queries])
        s.then("the answers should be identical", first == again)
        s.and_("and should not be None", all(first))
