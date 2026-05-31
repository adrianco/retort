"""BDD step definitions for tests/features/teams.feature (Team Queries)."""

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("teams.feature")


@when(parsers.parse('I request the "{venue}" record for "{team}" in season {season:d}'))
def _venue_record(context, venue, team, season):
    context["result"] = queries.team_record(
        team, competition="Brasileirão", season=season, venue=venue,
        data=context["data"],
    )


@when(parsers.parse('I request the overall record for "{team}" in season {season:d}'))
def _overall_record(context, team, season):
    context["result"] = queries.team_record(
        team, competition="Brasileirão", season=season, data=context["data"]
    )


@when(parsers.parse('I compare "{a}" and "{b}"'))
def _compare(context, a, b):
    context["result"] = queries.compare_teams(a, b, data=context["data"])


@then("the record should report wins, draws, losses and goals")
def _record_fields(context):
    rec = context["result"]["record"]
    for f in ("wins", "draws", "losses", "goals_for", "goals_against"):
        assert f in rec


@then("wins plus draws plus losses should equal the matches played")
def _record_sums(context):
    rec = context["result"]["record"]
    assert rec["wins"] + rec["draws"] + rec["losses"] == rec["matches"]


@then("the win rate should match wins divided by matches played")
def _win_rate(context):
    rec = context["result"]["record"]
    expected = round(100.0 * rec["wins"] / rec["matches"], 1)
    assert rec["win_rate"] == expected


@then("I should get a record for each team and a head-to-head summary")
def _compare_shape(context):
    r = context["result"]
    assert r["team_a_record"]["matches"] > 0
    assert r["team_b_record"]["matches"] > 0
    assert isinstance(r["head_to_head"], dict)


@then(parsers.parse('the team name should be reported as "{name}"'))
def _team_name(context, name):
    assert context["result"]["team"] == name


@then("the record should report a positive number of matches played")
def _positive_matches(context):
    assert context["result"]["record"]["matches"] > 0
