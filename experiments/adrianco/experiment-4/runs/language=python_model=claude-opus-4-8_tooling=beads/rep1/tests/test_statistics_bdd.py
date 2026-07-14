"""BDD step definitions for tests/features/statistics.feature."""

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("statistics.feature")


@when(parsers.parse('I request the statistics for the "{comp}" competition'))
def _stats(context, comp):
    context["result"] = queries.competition_stats(competition=comp, data=context["data"])


@when(parsers.parse('I request the {n:d} biggest wins in the "{comp}" competition'))
def _biggest(context, n, comp):
    context["result"] = queries.biggest_wins(
        competition=comp, limit=n, data=context["data"]
    )


@when(parsers.parse('I request the best "{venue}" records for season {season:d}'))
def _best(context, venue, season):
    context["result"] = queries.best_records(
        venue=venue, season=season, competition="Brasileirão",
        data=context["data"],
    )


@when(parsers.parse(
    'I request the top scoring teams for season {season:d} in "{comp}"'
))
def _top_scorers(context, season, comp):
    context["result"] = queries.top_scoring_teams(
        competition=comp, season=season, data=context["data"]
    )


@then("the average goals per match should be between 2.0 and 3.0")
def _avg_goals(context):
    assert 2.0 <= context["result"]["avg_goals_per_match"] <= 3.0


@then("the home, away and draw rates should sum to about 100 percent")
def _rates_sum(context):
    r = context["result"]
    total = r["home_win_rate"] + r["away_win_rate"] + r["draw_rate"]
    assert abs(total - 100.0) < 0.5


@then("each result should have a margin no larger than the result above it")
def _margin_sorted(context):
    results = context["result"]["results"]
    for prev, cur in zip(results, results[1:]):
        assert prev["margin"] >= cur["margin"]


@then(parsers.parse("the top result should have a margin of at least {n:d} goals"))
def _top_margin(context, n):
    assert context["result"]["results"][0]["margin"] >= n


@then("I should receive a ranked list of teams")
def _ranked(context):
    assert len(context["result"]["results"]) > 1


@then("the first team should have the highest win rate")
def _highest_win_rate(context):
    rows = context["result"]["results"]
    assert rows[0]["win_rate"] == max(r["win_rate"] for r in rows)


@then("the first team should have scored the most goals")
def _most_goals(context):
    rows = context["result"]["results"]
    assert rows[0]["goals_for"] == max(r["goals_for"] for r in rows)
