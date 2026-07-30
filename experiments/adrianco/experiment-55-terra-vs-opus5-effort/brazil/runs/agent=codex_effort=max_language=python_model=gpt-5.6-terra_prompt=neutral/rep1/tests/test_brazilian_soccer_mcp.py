"""BDD-style acceptance tests for the Brazilian soccer MCP server."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from server import BrazilianSoccerMCPServer
from soccer_data import (
    BRASILEIRAO,
    DATA_FILENAMES,
    SoccerRepository,
    normalize_team_name,
    parse_match_date,
)


@pytest.fixture(scope="session")
def repository() -> SoccerRepository:
    # Given the bundled datasets are available, load them once for the suite.
    repo = SoccerRepository(Path(__file__).parents[1] / "data" / "kaggle")
    repo.ensure_loaded()
    return repo


@pytest.fixture(scope="session")
def mcp_server(repository: SoccerRepository) -> BrazilianSoccerMCPServer:
    return BrazilianSoccerMCPServer(repository)


def test_given_bundled_csvs_when_loaded_then_every_source_is_queryable(repository: SoccerRepository) -> None:
    summary = repository.dataset_summary()

    assert summary["match_count"] == 23_954
    assert summary["player_count"] == 18_207
    assert set(summary["sources"]) == set(DATA_FILENAMES.values())
    assert summary["sources"][DATA_FILENAMES["brasileirao"]] == 4_180
    assert summary["sources"][DATA_FILENAMES["players"]] == 18_207


def test_given_team_variations_when_normalized_then_they_share_a_club_key() -> None:
    assert normalize_team_name("Flamengo-RJ") == "flamengo"
    assert normalize_team_name("Flamengo - RJ") == "flamengo"
    assert normalize_team_name("São Paulo FC") == "sao paulo"
    assert normalize_team_name("Atlético-GO") == "atletico goianiense"
    assert parse_match_date("29/03/2003").isoformat() == "2003-03-29"
    assert parse_match_date("2012-05-19 18:30:00").isoformat() == "2012-05-19"


def test_given_match_data_when_searching_fla_flu_then_results_include_core_match_fields(
    repository: SoccerRepository,
) -> None:
    result = repository.search_matches(
        team="Flamengo-RJ", opponent="Fluminense", competition="Brasileirão", limit=10
    )

    assert result["total"] > 0
    assert result["count"] > 0
    match = result["matches"][0]
    assert {match["home_team"], match["away_team"]} == {"Flamengo", "Fluminense"}
    assert match["date"]
    assert match["score"] is not None
    assert match["competition"] == BRASILEIRAO


def test_given_completed_2022_results_when_requesting_home_record_then_incomplete_source_rows_do_not_undercount(
    repository: SoccerRepository,
) -> None:
    record = repository.team_statistics(
        "Corinthians", season=2022, competition="Brasileirão", venue="home"
    )

    assert record["matches"] == 19
    assert record["wins"] + record["draws"] + record["losses"] == 19
    assert record["goals_for"] >= record["wins"]


def test_given_brasileirao_2019_when_calculating_standings_then_flamengo_is_champion(
    repository: SoccerRepository,
) -> None:
    table = repository.standings(2019)

    assert table["champion"] == "Flamengo"
    assert table["standings"][0]["points"] == 90
    assert table["standings"][0]["position"] == 1
    assert len(table["standings"]) == 20


def test_given_a_season_when_ranking_scoring_teams_then_the_largest_goal_total_is_first(
    repository: SoccerRepository,
) -> None:
    ranking = repository.top_scoring_teams(2019, limit=3)

    assert ranking["teams"][0]["team"] == "Flamengo"
    assert ranking["teams"][0]["goals_for"] >= ranking["teams"][1]["goals_for"]


def test_given_two_teams_when_compared_then_head_to_head_has_balanced_accounting(
    repository: SoccerRepository,
) -> None:
    result = repository.compare_teams("Palmeiras", "Santos", season=2019)

    assert result["matches"] > 0
    assert (
        result["team_a_record"]["wins"]
        + result["team_b_record"]["wins"]
        + result["draws"]
        == result["matches"]
    )
    assert result["recent_matches"]


def test_given_cup_data_when_finding_finals_then_only_final_round_fixtures_are_returned(
    repository: SoccerRepository,
) -> None:
    finals = repository.finals(competition="Copa do Brasil", season=2019)

    assert finals["count"] == 2
    assert finals["inferred_from_round"] is True
    assert {match["round"] for match in finals["matches"]} == {"8"}


def test_given_fifa_players_when_filtering_brazilians_then_the_highest_rating_is_first(
    repository: SoccerRepository,
) -> None:
    players = repository.search_players(
        nationality="Brazilian", position="forwards", limit=10, include_attributes=False
    )

    assert players["total"] > 0
    assert players["players"][0]["name"] == "Neymar Jr"
    assert players["players"][0]["overall"] == 92
    assert all(player["position"] in {"ST", "CF", "LF", "RF", "LW", "RW"} for player in players["players"])


def test_given_stdio_mcp_when_initialized_and_called_then_it_returns_standard_tool_results(
    mcp_server: BrazilianSoccerMCPServer,
) -> None:
    incoming = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2025-03-26"},
                    }
                ),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "standings", "arguments": {"season": 2019, "limit": 1}},
                    }
                ),
            ]
        )
        + "\n"
    )
    outgoing = io.StringIO()

    mcp_server.run(incoming, outgoing)
    responses = [json.loads(line) for line in outgoing.getvalue().splitlines()]

    assert [response["id"] for response in responses] == [1, 2, 3]
    assert "tools" in responses[1]["result"]
    assert any(tool["name"] == "search_matches" for tool in responses[1]["result"]["tools"])
    structured = responses[2]["result"]["structuredContent"]
    assert structured["champion"] == "Flamengo"
    assert responses[2]["result"]["isError"] is False


def test_given_a_supported_natural_question_when_asked_then_the_server_routes_to_a_tool(
    mcp_server: BrazilianSoccerMCPServer,
) -> None:
    answer = mcp_server.ask_brazilian_soccer("Which teams were relegated in 2020?")
    comparison = mcp_server.ask_brazilian_soccer("Compare the 2018 and 2019 seasons")

    assert answer["route"] == "relegated_teams"
    assert len(answer["data"]["relegated_teams"]) == 4
    assert "Botafogo" in answer["answer"]
    assert comparison["route"] == "compare_seasons"
    assert comparison["data"]["seasons"]["2019"]["champion"] == "Flamengo"
