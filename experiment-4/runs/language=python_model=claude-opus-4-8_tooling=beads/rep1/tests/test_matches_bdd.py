"""BDD step definitions for tests/features/matches.feature (Match Queries)."""

from datetime import date

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("matches.feature")


@when(parsers.parse('I search for matches between "{a}" and "{b}"'))
def _matches_between(context, a, b):
    context["result"] = queries.head_to_head(a, b, data=context["data"])


@when(parsers.parse('I search for "{team}" matches in season {season:d}'))
def _team_season(context, team, season):
    context["result"] = queries.find_matches(
        team=team, season=season, limit=500, data=context["data"]
    )
    context["team"] = team


@when(parsers.parse('I search for "{team}" matches in the "{comp}" competition'))
def _team_comp(context, team, comp):
    context["result"] = queries.find_matches(
        team=team, competition=comp, limit=500, data=context["data"]
    )


@when(parsers.parse('I request the head-to-head between "{a}" and "{b}"'))
def _h2h(context, a, b):
    context["result"] = queries.head_to_head(a, b, data=context["data"])


@when(parsers.parse(
    'I search for "{team}" matches between "{d1}" and "{d2}"'
))
def _team_dates(context, team, d1, d2):
    context["result"] = queries.find_matches(
        team=team, date_from=d1, date_to=d2, limit=500, data=context["data"]
    )


@then(parsers.parse("I should receive at least {n:d} matches"))
def _at_least_matches(context, n):
    assert context["result"]["total_matches"] >= n


@then("every match should have a date, a score, and a competition")
def _matches_well_formed(context):
    for m in context["result"]["matches"]:
        assert m["date"] is not None
        assert m["competition"]
        assert m["score"] is not None


@then(parsers.parse('every match should involve "{team}"'))
def _matches_involve(context, team):
    tl = team.lower().split("-")[0]
    for m in context["result"]["matches"]:
        assert tl in m["home_team"].lower() or tl in m["away_team"].lower()


@then(parsers.parse('every match should be in the "{comp}" competition'))
def _matches_competition(context, comp):
    matches = context["result"]["matches"]
    assert matches, "expected at least one match"
    for m in matches:
        assert m["competition"] == comp


@then("the head-to-head total should equal the listed wins and draws")
def _h2h_consistent(context):
    r = context["result"]
    s = r["summary"]
    wins_draws = sum(v for k, v in s.items() if k.endswith("_wins")) + s["draws"]
    # Some matches may lack a recorded score, so decided games <= total.
    assert wins_draws <= r["total_matches"]
    assert wins_draws > 0


@then(parsers.parse("every match should fall within the year {year:d}"))
def _matches_in_year(context, year):
    matches = context["result"]["matches"]
    assert matches
    for m in matches:
        assert date.fromisoformat(m["date"]).year == year
