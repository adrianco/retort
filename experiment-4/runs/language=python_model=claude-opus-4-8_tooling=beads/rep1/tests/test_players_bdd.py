"""BDD step definitions for tests/features/players.feature (Player Queries)."""

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("players.feature")


@when(parsers.parse('I search for players with nationality "{nat}"'))
def _players_nat(context, nat):
    context["result"] = queries.find_players(
        nationality=nat, limit=500, data=context["data"]
    )


@when(parsers.parse(
    'I search for players with nationality "{nat}" and position "{pos}"'
))
def _players_nat_pos(context, nat, pos):
    context["result"] = queries.find_players(
        nationality=nat, position=pos, limit=500, data=context["data"]
    )


@when(parsers.parse('I look up the player "{name}"'))
def _lookup_player(context, name):
    context["result"] = queries.get_player(name, data=context["data"])


@when(parsers.parse('I list the squad for "{club}"'))
def _squad(context, club):
    context["result"] = queries.club_squad(club, data=context["data"])


@then(parsers.parse("I should receive at least {n:d} players"))
def _at_least_players(context, n):
    assert context["result"]["total_players"] >= n


@then("the top result should be Brazilian")
def _top_brazil(context):
    assert context["result"]["players"][0]["nationality"] == "Brazil"


@then("the player should be found")
def _found(context):
    assert context["result"]["found"] is True


@then(parsers.parse('the player\'s nationality should be "{nat}"'))
def _player_nat(context, nat):
    assert context["result"]["nationality"] == nat


@then("I should receive at least one player")
def _at_least_one(context):
    assert context["result"]["total_players"] >= 1


@then("the players should be sorted by overall rating descending")
def _sorted_overall(context):
    overalls = [p["overall"] for p in context["result"]["players"]
                if p["overall"] is not None]
    assert overalls == sorted(overalls, reverse=True)


@then(parsers.parse('every returned player should play position "{pos}"'))
def _every_pos(context, pos):
    players = context["result"]["players"]
    assert players
    for p in players:
        assert p["position"] == pos
