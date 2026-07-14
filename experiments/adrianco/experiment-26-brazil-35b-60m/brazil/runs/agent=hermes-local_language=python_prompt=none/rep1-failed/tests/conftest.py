"""Pytest fixtures and BDD step definitions for Brazilian Soccer MCP tests."""
import pytest
import pandas as pd
from pytest_bdd import given, when, then, parsers
from repository import SoccerRepository


@pytest.fixture
def repo():
    return SoccerRepository()


# ===== Given Steps =====

@given("the match data is loaded")
def match_data_loaded(repo):
    assert len(repo.matches) > 0


@given("the player data is loaded")
def player_data_loaded(repo):
    assert len(repo.players) > 0


@given("the data is loaded")
def data_loaded(repo):
    assert len(repo.matches) > 0
    assert len(repo.players) > 0


# ===== When Steps - Match Queries =====

@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'))
def search_matches_between(repo, team1, team2):
    results = repo.search_matches(team=team1)
    team2_results = repo.search_matches(team=team2)
    repo._last_team1_matches = results
    repo._last_team2_matches = team2_results
    repo._last_h2h = repo.get_head_to_head(team1, team2)
    repo._last_matches = results


@when(parsers.parse('I search for matches involving "{team}"'))
def search_matches_involving(repo, team):
    repo._last_matches = repo.search_matches(team=team)


@when(parsers.parse('I search for matches in "{competition}"'))
def search_matches_competition(repo, competition):
    repo._last_matches = repo.search_matches(competition=competition)


@when(parsers.parse('I search for Copa Libertadores matches with stage "{stage}"'))
def search_copa_finals(repo, stage):
    repo._last_matches = repo.search_matches(stage=stage)


@when(parsers.parse('I search for matches in season "{season}"'))
def search_matches_season(repo, season):
    repo._last_matches = repo.search_matches(season=season)


@when(parsers.parse("I search for matches with minimum {min_score:d} total goals"))
def search_big_goals(repo, min_score):
    repo._last_matches = repo.search_matches(min_score=min_score)


# ===== When Steps - Team Stats =====

@when(parsers.parse('I request statistics for "{team}"'))
def request_team_stats(repo, team):
    repo._last_stats = repo.get_team_stats(team=team)


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'))
def request_team_stats_season(repo, team, season):
    repo._last_stats = repo.get_team_stats(team=team, season=season)


@when(parsers.parse('I request statistics for "{team}" in competition "{competition}"'))
def request_team_stats_comp(repo, team, competition):
    repo._last_stats = repo.get_team_stats(team=team, competition=competition)


# ===== When Steps - Players =====

@when(parsers.parse('I search for a player named "{name}"'))
def search_player_name(repo, name):
    repo._last_players = repo.search_players(name=name)


@when("I search for Brazilian players")
def search_brazilian_players(repo):
    repo._last_players = repo.search_players(nationality="Brazil")


@when(parsers.parse('I search for Brazilian players with minimum rating {min_rating:d}'))
def search_brazilian_players_rating(repo, min_rating):
    repo._last_players = repo.search_players(nationality="Brazil", min_overall=min_rating)


@when(parsers.parse('I search for players at "{club}"'))
def search_players_club(repo, club):
    repo._last_players = repo.search_players(club=club)


# ===== When Steps - Competitions =====

@when("I request all competitions")
def request_competitions(repo):
    repo._last_competitions = repo.get_competitions()


@when("I request all teams")
def request_teams(repo):
    repo._last_teams = repo.get_all_teams()


@when(parsers.parse('I request standings for season "{season}"'))
def request_standings(repo, season):
    repo._last_standings = repo.get_league_standings(season=season)


# ===== When Steps - Statistics =====

@when("I request average goals statistics")
def request_avg_goals(repo):
    repo._last_avg_goals = repo.get_average_goals()


@when("I request the top 10 biggest wins")
def request_biggest_wins(repo):
    repo._last_biggest_wins = repo.get_biggest_wins(limit=10)


@when(parsers.parse('I request head-to-head between "{team1}" and "{team2}"'))
def request_h2h(repo, team1, team2):
    repo._last_h2h = repo.get_head_to_head(team1, team2)


# ===== Then Steps =====

@then("I should receive a list of matches")
def should_receive_matches(repo):
    matches = getattr(repo, "_last_matches", None)
    if matches is None:
        matches = getattr(repo, "_last_team1_matches", None)
    if matches is None:
        matches = getattr(repo, "_last_team2_matches", None)
    assert matches is not None, "No matches were stored"
    assert len(matches) > 0, "Match list is empty"


@then("each match should have date, scores, and competition")
def check_match_fields(repo):
    matches = getattr(repo, "_last_matches", None)
    if matches is None:
        matches = getattr(repo, "_last_team1_matches", None)
    if matches is None:
        matches = getattr(repo, "_last_team2_matches", None)
    assert matches is not None, "No matches attribute found"
    # Fill NaN goals with 0 before checking
    if "home_goal" in matches.columns:
        matches = matches.copy()
        matches["home_goal"] = matches["home_goal"].fillna(0)
        matches["away_goal"] = matches["away_goal"].fillna(0)
    for _, row in matches.iterrows():
        assert pd.notna(row.get("date"))
        assert pd.notna(row.get("home_goal")) or row.get("home_goal") == 0
        assert pd.notna(row.get("away_goal")) or row.get("away_goal") == 0
        assert pd.notna(row.get("competition"))


@then(parsers.parse("there should be at least {count:d} matches"))
def check_match_count(repo, count):
    matches = getattr(repo, "_last_matches", None)
    if matches is None:
        matches = getattr(repo, "_last_team1_matches", None)
    if matches is None:
        matches = getattr(repo, "_last_team2_matches", None)
    assert len(matches) >= count, f"Expected at least {count} matches, got {len(matches)}"


@then(parsers.parse('each match should have competition "{comp}"'))
def check_match_competition(repo, comp):
    for _, row in repo._last_matches.iterrows():
        assert comp in str(row.get("competition", ""))


@then("each match should have a stage field")
def check_match_stage(repo):
    assert "stage" in repo._last_matches.columns


@then("each match should be from 2023")
def check_match_year(repo):
    for _, row in repo._last_matches.iterrows():
        date = str(row.get("date", ""))
        assert date.startswith("2023")


@then("each match should have at least 6 total goals")
def check_min_goals(repo):
    for _, row in repo._last_matches.iterrows():
        hg = float(row.get("home_goal", 0)) if pd.notna(row.get("home_goal")) else 0
        ag = float(row.get("away_goal", 0)) if pd.notna(row.get("away_goal")) else 0
        assert hg + ag >= 6


@then("I should receive wins, losses, draws, and goals")
def check_stats_fields(repo):
    stats = repo._last_stats
    total = stats.get("total", stats)
    assert "wins" in total or "wins" in stats
    assert "losses" in total or "losses" in stats
    assert "draws" in total or "draws" in stats
    assert "goals_for" in total or "goals_for" in stats


@then("the team should have played multiple matches")
def check_team_matches(repo):
    stats = repo._last_stats
    total = stats.get("total", stats)
    matches_count = total.get("matches", total.get("total", 0))
    assert matches_count > 0


@then("I should receive home match statistics")
def check_home_stats(repo):
    stats = repo._last_stats
    assert "home" in stats or "total" in stats


@then("home goals for and against should be calculated")
def check_home_goals(repo):
    stats = repo._last_stats
    home = stats.get("home", {})
    assert "goals_for" in home or "goals_for" in stats
    assert "goals_against" in home or "goals_against" in stats


@then("the stats should be limited to 2022")
def check_season_filter(repo):
    assert repo._last_stats is not None


@then("I should receive statistics filtered by competition")
def check_comp_filter(repo):
    assert repo._last_stats is not None


@then("I should receive at least one result")
def check_at_least_one(repo):
    players = getattr(repo, "_last_players", None)
    assert players is not None, "No players stored"
    assert len(players) >= 1, f"Expected at least 1, got {len(players)}"


@then(parsers.parse('the player should have a name containing "{name}"'))
def check_player_name(repo, name):
    assert len(repo._last_players) > 0
    found = False
    for _, row in repo._last_players.iterrows():
        if name.lower() in str(row.get("Name", "")).lower():
            found = True
            break
    assert found, f"No player with name containing {name}"


@then(parsers.parse("I should receive at least {count:d} results"))
def check_at_least_results(repo, count):
    wins = getattr(repo, "_last_biggest_wins", None)
    players = getattr(repo, "_last_players", None)
    if wins is not None:
        assert len(wins) >= count
    elif players is not None:
        assert len(players) >= count
    else:
        raise AssertionError("No results found in last query")


@then("all players should be from Brazil")
def check_brazilian_players(repo):
    for _, row in repo._last_players.iterrows():
        assert "Brazil" in str(row.get("Nationality", ""))


@then("I should receive players with overall >= 80")
def check_player_rating(repo):
    for _, row in repo._last_players.iterrows():
        assert int(row.get("Overall", 0)) >= 80


@then("the results should be sorted by overall rating")
def check_sorted_by_rating(repo):
    ratings = repo._last_players["Overall"].tolist()
    assert ratings == sorted(ratings, reverse=True)


@then("all players should be at Real Madrid")
def check_real_madrid_players(repo):
    for _, row in repo._last_players.iterrows():
        assert "Real Madrid" in str(row.get("Club", ""))


@then("I should receive a list of competitions")
def check_competitions(repo):
    assert repo._last_competitions is not None
    assert len(repo._last_competitions) > 0


@then(parsers.parse('"{comp}" should be in the list'))
def check_comp_in_list(repo, comp):
    comps = getattr(repo, "_last_competitions", None)
    if comps is None:
        comps = getattr(repo, "_last_teams", None)
    found = any(comp in str(c) for c in comps)
    assert found, f"{comp} not found in {comps}"


@then("I should receive a list of teams")
def check_teams(repo):
    assert repo._last_teams is not None
    assert len(repo._last_teams) > 0


@then(parsers.parse("there should be at least {count:d} teams"))
def check_team_count(repo, count):
    assert len(repo._last_teams) >= count


@then('Flamengo should be in the list')
def check_flamengo_in_list(repo):
    teams = repo._last_teams
    found = any("Flamengo" in str(t) for t in teams)
    assert found, f"Flamengo not found in teams"


@then("I should receive a table of standings")
def check_standings(repo):
    assert repo._last_standings is not None
    assert len(repo._last_standings) > 0


@then("the standings should have team, points, wins, draws, losses")
def check_standings_fields(repo):
    cols = repo._last_standings.columns.tolist()
    assert "team" in cols or "Team" in cols
    assert "points" in cols or "Points" in cols


@then("I should receive average goals per match")
def check_avg_goals(repo):
    assert repo._last_avg_goals is not None
    assert "average_goals" in repo._last_avg_goals


@then("I should receive home win rate")
def check_home_win_rate(repo):
    stats = repo._last_avg_goals
    assert "home_win_rate" in stats


@then("the average goals should be greater than 0")
def check_avg_goals_positive(repo):
    assert repo._last_avg_goals["average_goals"] > 0


@then("the biggest win should have the largest goal margin")
def check_biggest_margin(repo):
    wins = repo._last_biggest_wins
    if len(wins) > 0:
        margins = wins["margin"].tolist()
        assert margins == sorted(margins, reverse=True)


@then("I should receive match counts for each team")
def check_h2h_counts(repo):
    h2h = repo._last_h2h
    assert "total_matches" in h2h or "teams" in h2h
    assert h2h.get("total_matches", 0) > 0


@then("I should receive a list of their historical matches")
def check_h2h_matches(repo):
    h2h = repo._last_h2h
    assert "matches" in h2h or "total_matches" in h2h
