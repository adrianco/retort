import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from data_loader import BrazilianSoccerData

scenarios("features/matches.feature")


@pytest.fixture()
def context():
    return {}


@given("the match data is loaded")
def match_data_loaded(soccer_data, context):
    context["data"] = soccer_data
    assert len(soccer_data.all_matches) > 0


@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'))
def search_between_teams(context, team1, team2):
    context["results"] = context["data"].search_matches(team=team1, opponent=team2, limit=1000)


@when(parsers.parse('I search for matches by team "{team}"'))
def search_by_team(context, team):
    context["results"] = context["data"].search_matches(team=team, limit=100)
    context["team"] = team


@when(parsers.parse("I search for matches in season {season:d}"))
def search_by_season(context, season):
    context["results"] = context["data"].search_matches(season=season, limit=100)
    context["season"] = season


@when(parsers.parse('I search for matches in competition "{competition}"'))
def search_by_competition(context, competition):
    context["results"] = context["data"].search_matches(competition=competition, limit=100)
    context["competition"] = competition


@when(parsers.parse('I search for matches from "{date_from}" to "{date_to}"'))
def search_by_date_range(context, date_from, date_to):
    context["results"] = context["data"].search_matches(date_from=date_from, date_to=date_to, limit=100)


@then("I should receive a list of matches")
def check_matches_returned(context):
    assert len(context["results"]) > 0


@then("each match should have date, scores, and competition")
def check_match_fields(context):
    df = context["results"]
    for col in ["date", "home_goal", "away_goal", "competition"]:
        assert col in df.columns


@then(parsers.parse('at least one match should involve "{team}"'))
def check_team_in_results(context, team):
    df = context["results"]
    t = team.lower()
    mask = df["home"].str.lower().str.contains(t, na=False) | df["away"].str.lower().str.contains(t, na=False)
    assert mask.any()


@then(parsers.parse("all matches should be from season {season:d}"))
def check_season(context, season):
    df = context["results"]
    assert (df["season"] == season).all()


@then(parsers.parse('all matches should be from competition "{competition}"'))
def check_competition(context, competition):
    df = context["results"]
    assert df["competition"].str.lower().str.contains(competition.lower(), na=False).all()
