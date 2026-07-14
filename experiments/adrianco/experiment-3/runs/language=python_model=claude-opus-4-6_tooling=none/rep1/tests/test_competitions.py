import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from data_loader import BrazilianSoccerData

scenarios("features/competitions.feature")


@pytest.fixture()
def context():
    return {}


@given("the match data is loaded")
def match_data_loaded(soccer_data, context):
    context["data"] = soccer_data


@when(parsers.parse('I request standings for "{competition}" in season {season:d}'))
def request_standings(context, competition, season):
    context["standings"] = context["data"].competition_standings(competition=competition, season=season)


@when(parsers.parse('I request statistics for competition "{competition}"'))
def request_comp_stats(context, competition):
    context["stats"] = context["data"].match_statistics(competition=competition)


@then("I should receive a standings table")
def check_standings(context):
    assert len(context["standings"]) > 0


@then("the standings should have points and win columns")
def check_standings_columns(context):
    df = context["standings"]
    assert "points" in df.columns
    assert "wins" in df.columns


@then("I should receive aggregate statistics")
def check_agg_stats(context):
    s = context["stats"]
    assert s["total_matches"] > 0


@then("the statistics should include average goals per match")
def check_avg_goals(context):
    s = context["stats"]
    assert "avg_goals_per_match" in s
    assert s["avg_goals_per_match"] > 0
