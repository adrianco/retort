import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from data_loader import BrazilianSoccerData

scenarios("features/players.feature")


@pytest.fixture()
def context():
    return {}


@given("the player data is loaded")
def player_data_loaded(soccer_data, context):
    context["data"] = soccer_data
    assert len(soccer_data.players) > 0


@when(parsers.parse('I search for player "{name}"'))
def search_player_name(context, name):
    context["results"] = context["data"].search_players(name=name)


@when(parsers.parse('I search for players from "{nationality}"'))
def search_player_nationality(context, nationality):
    context["results"] = context["data"].search_players(nationality=nationality, limit=100)
    context["nationality"] = nationality


@when(parsers.parse('I search for players at club "{club}"'))
def search_player_club(context, club):
    context["results"] = context["data"].search_players(club=club)


@when(parsers.parse("I search for players with minimum overall {rating:d}"))
def search_player_rating(context, rating):
    context["results"] = context["data"].search_players(min_overall=rating, limit=100)
    context["min_rating"] = rating


@then("I should find at least one player")
def check_player_found(context):
    assert len(context["results"]) > 0


@then(parsers.parse('the player should have a name containing "{name}"'))
def check_player_name(context, name):
    df = context["results"]
    assert df["Name"].str.contains(name, case=False, na=False).any()


@then(parsers.parse('all players should be from "{nationality}"'))
def check_nationality(context, nationality):
    df = context["results"]
    assert df["Nationality"].str.lower().str.contains(nationality.lower(), na=False).all()


@then(parsers.parse("all players should have overall rating at least {rating:d}"))
def check_min_rating(context, rating):
    df = context["results"]
    assert (df["Overall"] >= rating).all()
