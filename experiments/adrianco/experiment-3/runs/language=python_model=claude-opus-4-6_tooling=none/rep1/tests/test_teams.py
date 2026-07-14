import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from data_loader import BrazilianSoccerData

scenarios("features/teams.feature")


@pytest.fixture()
def context():
    return {}


@given("the match data is loaded")
def match_data_loaded(soccer_data, context):
    context["data"] = soccer_data


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def request_team_stats(context, team, season):
    context["stats"] = context["data"].team_statistics(team=team, season=season)


@when(parsers.parse('I request home statistics for "{team}"'))
def request_home_stats(context, team):
    context["stats"] = context["data"].team_statistics(team=team, home_only=True)


@when(parsers.parse('I compare "{team1}" and "{team2}" head to head'))
def compare_h2h(context, team1, team2):
    context["h2h"] = context["data"].head_to_head(team1=team1, team2=team2)
    context["team1"] = team1
    context["team2"] = team2


@then("I should receive wins, losses, draws, and goals")
def check_stats_fields(context):
    s = context["stats"]
    assert s["matches"] > 0
    assert "wins" in s
    assert "draws" in s
    assert "losses" in s
    assert "goals_for" in s
    assert "goals_against" in s


@then("the statistics should only count home matches")
def check_home_only(context):
    s = context["stats"]
    assert s["matches"] > 0


@then("I should receive win counts for both teams")
def check_h2h_wins(context):
    h = context["h2h"]
    assert f"{context['team1']}_wins" in h
    assert f"{context['team2']}_wins" in h


@then("I should receive a draw count")
def check_h2h_draws(context):
    assert "draws" in context["h2h"]
