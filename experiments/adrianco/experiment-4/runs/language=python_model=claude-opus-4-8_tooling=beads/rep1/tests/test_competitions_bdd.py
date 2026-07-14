"""BDD step definitions for tests/features/competitions.feature."""

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("competitions.feature")


@when(parsers.parse('I request the {season:d} "{comp}" standings'))
def _standings(context, season, comp):
    context["result"] = queries.standings(season, competition=comp, data=context["data"])


@when("I request the list of competitions")
def _list_comp(context):
    context["result"] = queries.list_competitions(data=context["data"])


@when(parsers.parse('I request the season results for {season:d} "{comp}"'))
def _season_results(context, season, comp):
    context["result"] = queries.season_results(
        season, competition=comp, limit=1000, data=context["data"]
    )


@then(parsers.parse('the champion should be "{name}"'))
def _champion(context, name):
    assert context["result"]["champion"] == name


@then(parsers.parse("the table should have {n:d} teams"))
def _table_teams(context, n):
    assert context["result"]["teams"] == n


@then("each row should have no more points than the row above it")
def _monotonic_points(context):
    rows = context["result"]["standings"]
    for prev, cur in zip(rows, rows[1:]):
        assert prev["points"] >= cur["points"]


@then(parsers.parse('"{comp}" should be among the competitions'))
def _comp_present(context, comp):
    assert comp in context["result"]["competitions"]


@then(parsers.parse("I should receive at least {n:d} matches"))
def _at_least(context, n):
    assert context["result"]["total_matches"] >= n
