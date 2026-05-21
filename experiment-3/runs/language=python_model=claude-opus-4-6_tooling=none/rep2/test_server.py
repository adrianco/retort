import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from data_loader import BrazilianSoccerData, normalize_team_name

scenarios("features/matches.feature")


@pytest.fixture
def soccer_data():
    return BrazilianSoccerData()


@pytest.fixture
def context():
    return {}


@given("the match data is loaded")
def match_data_loaded(soccer_data):
    assert len(soccer_data.brasileirao) > 0
    assert len(soccer_data.copa_do_brasil) > 0
    assert len(soccer_data.libertadores) > 0
    assert len(soccer_data.extended_stats) > 0
    assert len(soccer_data.historical) > 0
    assert len(soccer_data.fifa_players) > 0


@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'))
def search_between_teams(soccer_data, context, team1, team2):
    context["matches"] = soccer_data.search_matches(team=team1, team2=team2, limit=100)


@when(parsers.parse('I search for "{team}" matches in season {season:d}'))
def search_team_season(soccer_data, context, team, season):
    context["matches"] = soccer_data.search_matches(team=team, season=season, limit=100)
    context["team"] = team


@when(parsers.parse('I search for matches in "{competition}"'))
def search_competition(soccer_data, context, competition):
    context["matches"] = soccer_data.search_matches(competition=competition, limit=100)
    context["competition"] = competition


@when(parsers.parse('I search for matches for "{team}"'))
def search_team(soccer_data, context, team):
    context["matches"] = soccer_data.search_matches(team=team, limit=100)
    context["team"] = team


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def request_team_stats(soccer_data, context, team, season):
    context["stats"] = soccer_data.get_team_stats(team=team, season=season)


@when(parsers.parse('I compare "{team1}" and "{team2}" head to head'))
def compare_head_to_head(soccer_data, context, team1, team2):
    context["h2h"] = soccer_data.head_to_head(team1, team2)


@when(parsers.parse("I request standings for season {season:d}"))
def request_standings(soccer_data, context, season):
    context["standings"] = soccer_data.get_standings(season)


@when(parsers.parse('I search for players with nationality "{nationality}"'))
def search_players_nationality(soccer_data, context, nationality):
    context["players"] = soccer_data.search_players(nationality=nationality, limit=50)
    context["nationality"] = nationality


@when(parsers.parse('I search for players at club "{club}"'))
def search_players_club(soccer_data, context, club):
    context["players"] = soccer_data.search_players(club=club, limit=50)


@when(parsers.parse('I request statistics for "{competition}"'))
def request_comp_stats(soccer_data, context, competition):
    context["comp_stats"] = soccer_data.get_competition_stats(competition=competition)


@then("I should receive a list of matches")
def should_receive_matches(context):
    assert len(context["matches"]) > 0


@then("each match should have date, scores, and competition")
def matches_have_fields(context):
    for m in context["matches"]:
        assert m["date"] is not None
        assert m["home_goals"] is not None
        assert m["away_goals"] is not None
        assert m["competition"] is not None


@then(parsers.parse('all matches should involve "{team}"'))
def all_matches_involve_team(context, team):
    norm = normalize_team_name(team).lower()
    for m in context["matches"]:
        h = m["home_team"].lower()
        a = m["away_team"].lower()
        assert norm in h or norm in a or h in norm or a in norm


@then(parsers.parse('all matches should be from "{competition}"'))
def all_matches_from_competition(context, competition):
    for m in context["matches"]:
        assert m["competition"].lower() == competition.lower()


@then("I should receive wins, losses, draws, and goals")
def should_receive_stats(context):
    stats = context["stats"]
    assert stats["matches"] > 0
    assert "wins" in stats
    assert "losses" in stats
    assert "draws" in stats
    assert "goals_for" in stats
    assert "goals_against" in stats


@then("I should receive head-to-head statistics")
def should_receive_h2h(context):
    h2h = context["h2h"]
    assert h2h["total_matches"] > 0


@then("the result should include wins for both teams")
def h2h_has_wins(context):
    h2h = context["h2h"]
    t1, t2 = h2h["team1"], h2h["team2"]
    assert f"{t1}_wins" in h2h
    assert f"{t2}_wins" in h2h


@then("I should receive a standings table")
def should_receive_standings(context):
    assert len(context["standings"]) > 0
    first = context["standings"][0]
    assert "points" in first
    assert "wins" in first


@then(parsers.parse('"{team}" should be the champion'))
def team_should_be_champion(context, team):
    champion = context["standings"][0]["team"]
    assert normalize_team_name(team).lower() in champion.lower()


@then("I should receive a list of players")
def should_receive_players(context):
    assert len(context["players"]) > 0


@then("all players should be Brazilian")
def all_players_brazilian(context):
    for p in context["players"]:
        assert "brazil" in p.get("Nationality", "").lower()


@then("I should receive competition statistics with goals and win rates")
def should_receive_comp_stats(context):
    stats = context["comp_stats"]
    assert stats["total_matches"] > 0
    assert stats["total_goals"] > 0
    assert "avg_goals_per_match" in stats
    assert "home_win_pct" in stats


@then(parsers.parse('the results should match searching for "{team}"'))
def results_match_normalized(soccer_data, context, team):
    other = soccer_data.search_matches(team=team, limit=100)
    assert len(context["matches"]) > 0
    assert len(other) > 0
    assert abs(len(context["matches"]) - len(other)) <= len(other) * 0.1 or len(context["matches"]) == len(other)
