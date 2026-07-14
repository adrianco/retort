"""BDD steps for ``tests/features/statistics.feature``."""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from soccer_mcp import queries as q

scenarios("features/statistics.feature")


@given("the match data is loaded")
def _data_loaded(store):
    assert store.matches


@when(parsers.parse('I request average goals statistics for the "{comp}"'))
def avg_goals(store, comp, bdd_context):
    bdd_context["avg"] = q.average_goals_per_match(store, competition=comp)


@when(parsers.parse("I request the {n:d} biggest wins in the corpus"))
def biggest(store, n, bdd_context):
    bdd_context["wins"] = q.biggest_wins(store, limit=n)


@when(parsers.parse('I request the best home records for the "{comp}" in season {season:d}'))
def best_home(store, comp, season, bdd_context):
    bdd_context["home"] = q.best_home_record(
        store, competition=comp, season=season, min_matches=5,
    )


@when("I request the overall statistics")
def overall(store, bdd_context):
    bdd_context["overall"] = q.overall_statistics(store)


@then(parsers.parse("the average goals per match should be between {lo:f} and {hi:f}"))
def avg_range(bdd_context, lo, hi):
    assert lo <= bdd_context["avg"]["average_goals"] <= hi


@then("the home win rate plus away win rate plus draw rate should equal 1")
def rates_sum(bdd_context):
    a = bdd_context["avg"]
    total = a["home_win_rate"] + a["away_win_rate"] + a["draw_rate"]
    assert abs(total - 1.0) < 0.01, total


@then(parsers.parse("I should receive {n:d} matches"))
def n_matches(bdd_context, n):
    assert len(bdd_context["wins"]) == n


@then("every match should have a non-zero goal difference")
def nonzero_gd(bdd_context):
    for m in bdd_context["wins"]:
        assert m["home_goal"] != m["away_goal"], m


@then("the first match should have the largest margin")
def largest_first(bdd_context):
    margins = [abs(m["home_goal"] - m["away_goal"]) for m in bdd_context["wins"]]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse("the leader should have a win rate above {threshold:f}"))
def leader_winrate(bdd_context, threshold):
    leader = bdd_context["home"][0]
    assert leader["win_rate"] > threshold, leader


@then(parsers.parse("the corpus should contain more than {n:d} matches"))
def matches_total(bdd_context, n):
    assert bdd_context["overall"]["matches_total"] > n


@then(parsers.parse("the corpus should contain at least {n:d} competitions"))
def comp_count(bdd_context, n):
    assert len(bdd_context["overall"]["competitions"]) >= n
