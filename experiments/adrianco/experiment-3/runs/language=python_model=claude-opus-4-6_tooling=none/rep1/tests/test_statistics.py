import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from data_loader import BrazilianSoccerData

scenarios("features/statistics.feature")


@pytest.fixture()
def context():
    return {}


@given("the match data is loaded")
def match_data_loaded(soccer_data, context):
    context["data"] = soccer_data


@when("I request overall match statistics")
def request_overall_stats(context):
    context["stats"] = context["data"].match_statistics()


@when(parsers.parse('I request match statistics for team "{team}"'))
def request_team_match_stats(context, team):
    context["stats"] = context["data"].match_statistics(team=team)


@then("I should receive total matches count")
def check_total_matches(context):
    assert context["stats"]["total_matches"] > 0


@then("I should receive average goals per match")
def check_avg_goals(context):
    assert "avg_goals_per_match" in context["stats"]
    assert context["stats"]["avg_goals_per_match"] > 0


@then("I should receive home and away win rates")
def check_win_rates(context):
    s = context["stats"]
    assert "home_win_rate" in s
    assert "away_win_rate" in s
    assert s["home_win_rate"] > 0
    assert s["away_win_rate"] > 0


@then("I should receive the biggest win")
def check_biggest_win(context):
    s = context["stats"]
    assert "biggest_win" in s
    assert "score" in s["biggest_win"]
