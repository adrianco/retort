"""Given/When/Then regression scenarios for the supplied Brazilian soccer data."""

from __future__ import annotations

import pytest

import server
from soccer_knowledge_graph import SoccerKnowledgeGraph, team_identity


@pytest.fixture(scope="module")
def graph() -> SoccerKnowledgeGraph:
    # Given the six bundled CSV datasets
    return SoccerKnowledgeGraph()


def test_given_bundled_sources_when_loaded_then_every_file_is_accounted_for(graph: SoccerKnowledgeGraph) -> None:
    # When the graph loads
    summary = graph.list_available_data()
    sources = {source["source_key"]: source for source in summary["sources"]}

    # Then all six files have their real row counts and usable records.
    assert {key: source["rows"] for key, source in sources.items()} == {
        "brasileirao": 4180,
        "brazilian_cup": 1337,
        "libertadores": 1255,
        "extended": 10296,
        "historical": 6886,
        "fifa": 18207,
    }
    assert sources["libertadores"]["loaded"] == 1254
    assert sources["libertadores"]["skipped"] == 1  # The NA placeholder fixture.
    assert summary["players"] == 18207
    assert summary["raw_match_rows"] == 23953


def test_given_historical_data_when_read_then_brazilian_dates_are_normalized(graph: SoccerKnowledgeGraph) -> None:
    # When the first historical source record is selected
    match = next(match for match in graph.matches if match.match_id == "historical:1")

    # Then DD/MM/YYYY is a real date and the match fields are intact.
    assert match.match_date.isoformat() == "2003-03-29"
    assert match.season == 2003
    assert match.round == "1"
    assert match.home_team == "Guarani"
    assert match.away_team == "Vasco"
    assert (match.home_goal, match.away_goal) == (4, 2)


def test_given_team_spelling_variants_when_searching_then_the_same_club_is_found(graph: SoccerKnowledgeGraph) -> None:
    # When a client uses an accent-free query against a state-suffixed source
    result = graph.search_matches(team="Palmeiras", season=2012, source="Brasileirao", limit=100)

    # Then the 2012 opening-round source fixture is available under its normalized identity.
    row = next(
        match
        for match in result["matches"]
        if match["date"] == "2012-05-19" and match["home_team"] == "Palmeiras-SP"
    )
    assert row["away_team"] == "Portuguesa-SP"
    assert row["score"] == "1-1"
    assert row["round"] == "1"
    assert graph.resolve_team("São Paulo").team_key == graph.resolve_team("Sao Paulo-SP").team_key


def test_given_state_qualified_atleticos_when_normalized_then_identities_stay_distinct() -> None:
    # When similarly named clubs are normalized
    mineiro = team_identity("Atlético-MG")
    goianiense = team_identity("Atletico-GO")
    paranaense = team_identity("Athletico-PR")

    # Then no aggregation key collapses them into one generic Atlético club.
    assert len({mineiro, goianiense, paranaense}) == 3


def test_given_unscored_2022_rows_when_calculating_a_home_record_then_they_are_excluded(
    graph: SoccerKnowledgeGraph,
) -> None:
    # When Corinthians' 2022 home record is calculated from the primary Brasileirão source
    stats = graph.get_team_statistics("Corinthians", season=2022, competition="Brasileirao", venue="home")

    # Then NA score rows are preserved separately rather than counted as 0-0 draws.
    assert stats["matches"] == 19
    assert stats["completed_matches"] == 15
    assert stats["unscored_matches"] == 4
    assert (stats["wins"], stats["draws"], stats["losses"]) == (10, 4, 1)
    assert (stats["goals_for"], stats["goals_against"]) == (21, 7)

    searched = graph.search_matches(team="Corinthians", season=2022, source="Brasileirao", limit=100)
    oct_eighth = next(match for match in searched["matches"] if match["date"] == "2022-10-08")
    assert oct_eighth["score"] is None
    assert oct_eighth["completed"] is False


def test_given_overlapping_sources_when_calculating_standings_then_canonical_results_do_not_double_count(
    graph: SoccerKnowledgeGraph,
) -> None:
    # When a 2019 Brasileirão table is calculated in the default canonical mode
    standings = graph.get_standings(2019)
    by_team = {entry["team"]: entry for entry in standings["standings"]}

    # Then the known 38-match table is reproduced and Atlético identities remain separate.
    assert standings["matches_considered"] == 380
    assert standings["champion"] == "Flamengo"
    assert by_team["Flamengo"]["points"] == 90
    assert by_team["Athletico-PR"]["points"] == 64
    assert by_team["Atlético-MG"]["points"] == 48


def test_given_cup_and_libertadores_data_when_filtering_finals_then_both_round_conventions_work(
    graph: SoccerKnowledgeGraph,
) -> None:
    # When Copa do Brasil's numeric final round and Libertadores' named final stage are queried
    cup = graph.search_matches(competition="Copa do Brasil", season=2020, round="8", limit=10)
    libertadores = graph.search_matches(competition="Libertadores", season=2019, stage="final", limit=10)

    # Then both 2020 Cup legs and the 2019 Libertadores final are returned.
    assert {(match["date"], match["score"]) for match in cup["matches"]} == {
        ("2021-02-28", "0-1"),
        ("2021-03-07", "2-0"),
    }
    assert libertadores["count"] == 1
    final = libertadores["matches"][0]
    assert (final["date"], final["home_team_normalized"], final["score"], final["away_team"]) == (
        "2019-11-23",
        "Flamengo",
        "2-1",
        "River Plate",
    )


def test_given_fifa_snapshot_when_searching_brazilian_players_then_results_are_ranked_and_honest(
    graph: SoccerKnowledgeGraph,
) -> None:
    # When Brazilian players are requested
    brazilian = graph.search_players(nationality="Brazil", limit=5)
    flamengo = graph.search_players(club="Flamengo", limit=5)

    # Then the real snapshot ranks Neymar first and does not invent a Flamengo roster.
    assert brazilian["count"] == 827
    assert (brazilian["players"][0]["name"], brazilian["players"][0]["overall"]) == ("Neymar Jr", 92)
    assert flamengo["count"] == 0
    assert "No players" in flamengo["message"]


def test_given_common_natural_language_when_asking_then_structured_evidence_is_returned(
    graph: SoccerKnowledgeGraph,
) -> None:
    # When sample questions are passed to the natural-language tool
    last_meeting = graph.ask_soccer("When did Flamengo last play Corinthians?")
    finals = graph.ask_soccer("Find all Copa do Brasil finals")
    bracket = graph.ask_soccer("Show the 2018 Copa Libertadores bracket")

    # Then each is routed to a concrete graph query and includes inspectable data.
    assert last_meeting["intent"] == "last_head_to_head"
    assert last_meeting["data"]["recent_matches"][0]["date"] == "2023-10-08"
    assert finals["intent"] == "competition_finals"
    assert finals["data"]["count"] >= 2
    assert all(match["round"] == "8" for match in finals["data"]["matches"])
    assert bracket["intent"] == "competition_bracket"
    assert bracket["data"]["stages"][0]["stage"] == "group stage"


def test_given_a_team_entity_when_explored_then_graph_relationships_include_opponents_and_competitions(
    graph: SoccerKnowledgeGraph,
) -> None:
    # When Flamengo's graph neighbourhood is requested
    relationships = graph.get_entity_relationships("Flamengo", limit=10)

    # Then the response expresses graph edges rather than only a flat match list.
    edge_types = {relationship["type"] for relationship in relationships["relationships"]}
    assert relationships["entity"] == "Flamengo"
    assert "PLAYED_IN" in edge_types
    assert "PLAYED_AGAINST" in edge_types


def test_given_twenty_representative_questions_when_queried_then_every_request_returns_data_or_an_honest_empty_result(
    graph: SoccerKnowledgeGraph,
) -> None:
    # Given twenty representative match, team, player, competition, graph, and natural-language requests
    requests = [
        lambda: graph.search_matches(team="Flamengo", opponent="Fluminense"),
        lambda: graph.search_matches(team="Palmeiras", season=2023),
        lambda: graph.search_matches(competition="Copa do Brasil", round="8"),
        lambda: graph.search_matches(competition="Libertadores", stage="final"),
        lambda: graph.get_team_statistics("Corinthians", season=2022, venue="home"),
        lambda: graph.get_team_statistics("Palmeiras", season=2023),
        lambda: graph.compare_teams("Palmeiras", "Santos"),
        lambda: graph.get_standings(2019),
        lambda: graph.get_relegated_teams(2020),
        lambda: graph.get_competition_statistics(competition="Brasileirao", season=2023),
        lambda: graph.get_biggest_wins(competition="Brasileirao", limit=3),
        lambda: graph.get_best_team_record(venue="away", competition="Brasileirao", season=2023),
        lambda: graph.get_competition_bracket(2018, competition="Libertadores"),
        lambda: graph.get_team_competitions("Palmeiras"),
        lambda: graph.search_derbies(season=2023),
        lambda: graph.search_players(nationality="Brazil", limit=3),
        lambda: graph.search_players(query="Neymar"),
        lambda: graph.get_entity_relationships("Flamengo"),
        lambda: graph.ask_soccer("Which team has the best away record in Brasileirão 2023?"),
        lambda: graph.ask_soccer("What's the average goals per match in the Brasileirão?"),
    ]

    # When each question is executed, then it returns a structured response rather than an exception or invented data.
    responses = [request() for request in requests]
    assert len(responses) == 20
    assert all(isinstance(response, dict) for response in responses)
    assert all("error" not in response for response in responses)


def test_given_an_mcp_runtime_when_constructing_the_adapter_then_all_query_tools_are_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a small FastMCP-compatible test double (the local host has an intentionally incompatible Pydantic v1)
    class FakeMCP:
        def __init__(self, name: str, instructions: str) -> None:
            self.name = name
            self.instructions = instructions
            self.tools: list[str] = []

        def tool(self):
            def register(function):
                self.tools.append(function.__name__)
                return function

            return register

    monkeypatch.setattr(server, "FastMCP", FakeMCP)

    # When the adapter is created, then every public graph capability becomes an MCP tool without loading data.
    adapter = server.create_mcp_server()
    assert adapter.name == "Brazilian Soccer Knowledge Graph"
    assert set(adapter.tools) == {function.__name__ for function in server.TOOL_FUNCTIONS}
    assert len(adapter.tools) == 15
