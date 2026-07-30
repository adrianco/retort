"""BDD-style acceptance tests for Brazilian soccer data querying."""

from pathlib import Path

from brazilian_soccer_mcp import SoccerData, canonical_team, handle_request


DATA = Path(__file__).parents[1] / "data" / "kaggle"


def test_normalizes_accents_state_suffixes_and_full_team_names():
    # Given equivalent spellings of a team
    # When they are canonicalized
    # Then they identify the same team node.
    assert canonical_team("São Paulo-SP") == canonical_team("Sao Paulo FC") == "sao paulo"
    assert canonical_team("Sport Club Corinthians Paulista") == canonical_team("Corinthians-SP")


def test_finds_head_to_head_matches_with_required_match_fields():
    # Given loaded match data
    data = SoccerData(DATA)
    # When Flamengo and Fluminense are requested
    result = data.search_matches(team="Flamengo", opponent="Fluminense", limit=10)
    # Then matches include date, score and competition.
    assert result["count"] > 0
    assert {"date", "home_goals", "away_goals", "competition"} <= result["matches"][0].keys()


def test_team_stats_and_standings_calculate_results_from_matches():
    # Given loaded 2019 Brasileirao results
    data = SoccerData(DATA)
    # When team statistics and the league table are requested
    stats = data.team_stats("Flamengo", season=2019, competition="Brasileirao")
    table = data.standings(2019)
    # Then the record has a complete W/D/L accounting and standings are ordered.
    assert stats["matches"] == stats["wins"] + stats["draws"] + stats["losses"]
    assert table["standings"]
    assert all(a["points"] >= b["points"] for a, b in zip(table["standings"], table["standings"][1:]))


def test_head_to_head_totals_do_not_depend_on_the_display_limit():
    # Given a rivalry with more than one recorded match
    data = SoccerData(DATA)
    # When its match display is limited
    compact = data.head_to_head("Flamengo", "Fluminense", limit=1)
    full = data.head_to_head("Flamengo", "Fluminense", limit=500)
    # Then the aggregate record still covers the full relationship.
    assert len(compact["matches"]) == 1
    assert (compact["team_a_wins"], compact["team_b_wins"], compact["draws"]) == (
        full["team_a_wins"], full["team_b_wins"], full["draws"]
    )


def test_players_can_be_filtered_by_name_and_nationality():
    # Given FIFA player data
    data = SoccerData(DATA)
    # When a Brazilian player name is searched
    result = data.search_players(name="Neymar", nationality="Brazil")
    # Then matching player records with ratings are returned.
    assert result["count"] > 0
    assert all("neymar" in player["name"].lower() for player in result["players"])
    assert result["players"][0]["overall"] is not None


def test_all_sources_are_loaded_and_extended_data_is_queryable():
    # Given the complete supplied data directory
    data = SoccerData(DATA)
    # When its source inventory and a source-specific competition are queried
    sources = {match.source for match in data.matches}
    result = data.search_matches(competition="Copa do Brasil", season=2023)
    # Then all five match CSVs and the player CSV have contributed usable data.
    assert len(sources) == 5
    assert len(data.players) > 18_000
    assert result["count"] > 0


def test_mcp_tools_list_and_call_return_structured_content():
    # Given a loaded server engine
    data = SoccerData(DATA)
    # When an MCP client lists and calls tools
    listed = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, data)
    called = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_players", "arguments": {"name": "Neymar", "limit": 1}}}, data)
    # Then the tool schema and structured result are returned according to MCP.
    assert any(tool["name"] == "search_matches" for tool in listed["result"]["tools"])
    assert called["result"]["content"][0]["type"] == "text"
    assert called["result"]["structuredContent"]["players"]
