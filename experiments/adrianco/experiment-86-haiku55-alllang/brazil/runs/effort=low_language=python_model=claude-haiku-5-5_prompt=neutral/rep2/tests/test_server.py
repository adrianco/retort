"""BDD scenarios for the MCP tools, as a client would call them."""

import asyncio


def test_scenario_server_exposes_all_query_tools(server):
    # Given the MCP server is created
    # When its tools are listed
    names = {t.name for t in asyncio.run(server.list_tools())}
    # Then every required query category has a tool
    assert {"search_matches", "head_to_head", "team_record", "standings", "league_stats",
            "biggest_wins", "venue_leaderboard", "search_players",
            "brazilian_players_by_club", "list_competitions"} <= names


def test_scenario_match_question_is_answered_in_spec_format(call):
    # Given the user asks for Flamengo vs Fluminense matches
    # When the search_matches tool is called
    text = call("search_matches", team="Flamengo", opponent="Fluminense", limit=3)
    # Then the answer lists dated matches with scores and competitions
    assert text.startswith("Matches for Flamengo, Fluminense:")
    assert "Flamengo" in text and "Fluminense" in text and "Brasileirão" in text
    assert "more matches in dataset" in text


def test_scenario_standings_answer_matches_spec_example(call):
    # Given the 2019 season
    # When the standings tool is called
    text = call("standings", season=2019)
    # Then the first line names the table and the champion is on 90 points
    assert text.splitlines()[0].startswith("2019 Brasileirão Série A standings")
    assert "1. Flamengo (RJ) - 90 pts (28W, 6D, 4L)" in text


def test_scenario_team_record_answer_has_spec_fields(call):
    # Given a team, season and venue
    # When the team_record tool is called
    text = call("team_record", team="Corinthians", season=2022, venue="home")
    # Then matches, wins, draws, losses, goals and win rate are shown
    for field in ("Matches:", "Wins:", "Goals For:", "Win rate:"):
        assert field in text


def test_scenario_player_question_returns_ratings(call):
    # Given a request for Brazilian players
    # When the search_players tool is called
    text = call("search_players", nationality="Brazilian", limit=3)
    # Then each player has an overall rating, position and club
    assert "Overall:" in text and "Position:" in text and "Club:" in text


def test_scenario_query_errors_are_returned_as_text(call):
    # Given an unknown competition
    # When the standings tool is called with it
    text = call("standings", season=2019, competition="Premier League")
    # Then the tool returns an error message instead of raising
    assert text.startswith("Error: Unknown competition")


def test_scenario_competition_inventory_lists_all_sources(call):
    # Given the dataset is loaded
    # When the competitions tool is called
    text = call("list_competitions")
    # Then every competition with matches is listed
    for name in ("Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"):
        assert name in text
