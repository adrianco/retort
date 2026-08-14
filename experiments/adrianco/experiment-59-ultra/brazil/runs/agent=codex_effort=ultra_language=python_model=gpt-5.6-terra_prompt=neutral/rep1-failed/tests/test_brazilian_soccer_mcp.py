"""BDD-style tests for the Brazilian Soccer MCP server."""

from __future__ import annotations

import json
import time
from io import StringIO

import pytest

import mcp_server
from mcp_server import BrazilianSoccerMCPServer, LATEST_PROTOCOL_VERSION
from soccer_data import (
    NaturalLanguageQueryService,
    SoccerRepository,
    normalize_team_name,
    parse_match_datetime,
)


@pytest.fixture(scope="session")
def repository() -> SoccerRepository:
    return SoccerRepository.from_default_data()


class TestDatasetLoading:
    def test_given_the_bundled_files_when_loaded_then_all_six_sources_are_queryable(self, repository: SoccerRepository) -> None:
        summary = repository.source_summary()
        by_source = {item["source"]: item for item in summary["sources"]}

        assert set(by_source) == {
            "brasileirao",
            "brazilian_cup",
            "libertadores",
            "extended_statistics",
            "historical_brasileirao",
            "fifa_players",
        }
        assert by_source["brasileirao"]["records"] == 4180
        assert by_source["brazilian_cup"]["records"] == 1337
        assert by_source["libertadores"]["records"] == 1255
        assert by_source["extended_statistics"]["records"] == 10296
        assert by_source["historical_brasileirao"]["records"] == 6886
        assert by_source["fifa_players"]["records"] == 18207
        assert summary["players"] == 18207
        assert summary["raw_match_records"] == 23954

    def test_given_the_fifa_bom_column_when_loaded_then_player_fields_remain_available(self, repository: SoccerRepository) -> None:
        result = repository.search_players(name="Neymar", limit=3)

        assert result["count"] >= 1
        player = result["players"][0]
        assert player["name"] == "Neymar Jr"
        assert player["id"]
        assert player["attributes"]["Finishing"] is not None


class TestNormalizationAndDates:
    def test_given_team_name_variants_when_normalized_then_known_clubs_share_a_key(self) -> None:
        assert normalize_team_name("São Paulo-SP") == normalize_team_name("Sao Paulo")
        assert normalize_team_name("Athletico-PR") == normalize_team_name("Atlético Paranaense - PR")
        assert normalize_team_name("Sport Club Corinthians Paulista") == normalize_team_name("Corinthians-SP")

    def test_given_distinct_state_suffixes_when_normalized_then_they_do_not_merge(self) -> None:
        assert normalize_team_name("Botafogo-RJ") != normalize_team_name("Botafogo-PB")
        assert normalize_team_name("América-MG") != normalize_team_name("América-RN")

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("29/03/2003", "2003-03-29T00:00:00"),
            ("2023-09-24", "2023-09-24T20:00:00"),
            ("2013-02-12 20:15:00", "2013-02-12T20:15:00"),
        ],
    )
    def test_given_source_date_formats_when_parsed_then_dates_are_unambiguous(
        self, raw: str, expected: str
    ) -> None:
        kickoff = "20:00:00" if raw == "2023-09-24" else None
        assert parse_match_datetime(raw, kickoff).isoformat() == expected


class TestMatchQueries:
    def test_given_a_team_and_opponent_when_searching_then_matches_include_scores_and_provenance(
        self, repository: SoccerRepository
    ) -> None:
        result = repository.search_matches(team="Flamengo", opponent="Fluminense", limit=10)

        assert result["count"] > 0
        assert result["matches"]
        assert all(match["date"] and match["competition"] and match["source"] for match in result["matches"])
        assert all(match["home_goals"] is not None and match["away_goals"] is not None for match in result["matches"])

    def test_given_date_and_competition_filters_when_searching_then_every_match_satisfies_them(
        self, repository: SoccerRepository
    ) -> None:
        result = repository.search_matches(
            team="Palmeiras",
            competition="Brasileirao",
            season=2022,
            date_from="2022-01-01",
            date_to="2022-12-31",
            limit=500,
        )

        assert result["count"] > 0
        assert all(match["competition"] == "Brasileirão" for match in result["matches"])
        assert all(match["season"] == 2022 for match in result["matches"])
        assert all("2022-01-01" <= match["date"] <= "2022-12-31" for match in result["matches"])

    def test_given_incomplete_source_records_when_requested_then_missing_scores_are_not_treated_as_zero(
        self, repository: SoccerRepository
    ) -> None:
        raw = repository.search_matches(
            source="brasileirao", include_incomplete=True, include_duplicates=True, limit=500
        )
        default = repository.search_matches(source="brasileirao", limit=500)

        assert raw["count"] == 4180
        assert any(match["status"] == "incomplete" for match in raw["matches"])
        assert all(match["status"] == "completed" for match in default["matches"])

    def test_given_extended_statistics_when_searching_by_source_then_extra_match_stats_are_preserved(
        self, repository: SoccerRepository
    ) -> None:
        result = repository.search_matches(source="extended_statistics", season=2023, limit=5)

        assert result["count"] > 0
        assert "total_corners" in result["matches"][0]["statistics"]


class TestTeamAndCompetitionQueries:
    def test_given_a_team_season_and_venue_when_calculating_stats_then_record_fields_balance(
        self, repository: SoccerRepository
    ) -> None:
        result = repository.team_statistics("Corinthians", competition="Brasileirão", season=2022, venue="home")
        record = result["record"]

        assert record["matches"] > 0
        assert record["wins"] + record["draws"] + record["losses"] == record["matches"]
        assert record["goals_for"] >= 0 and record["goals_against"] >= 0

    def test_given_two_teams_when_compared_then_head_to_head_is_symmetric(self, repository: SoccerRepository) -> None:
        forwards = repository.head_to_head("Palmeiras", "Santos")
        backwards = repository.head_to_head("Santos", "Palmeiras")

        assert forwards["matches"] > 0
        assert forwards["matches"] == backwards["matches"]
        assert forwards["team_one_record"]["wins"] == backwards["team_two_record"]["wins"]
        assert forwards["team_one_record"]["draws"] == backwards["team_two_record"]["draws"]

    def test_given_2019_brasileirao_when_calculating_standings_then_benchmark_order_is_reproduced(
        self, repository: SoccerRepository
    ) -> None:
        result = repository.competition_standings("Brasileirão", 2019)

        assert result["matches_used"] == 380
        assert [(row["team"], row["points"]) for row in result["standings"][:3]] == [
            ("Flamengo", 90),
            ("Santos", 74),
            ("Palmeiras", 74),
        ]

    def test_given_statistical_metrics_when_analyzed_then_aggregates_are_valid(self, repository: SoccerRepository) -> None:
        average = repository.analyze_statistics("average_goals", competition="Brasileirão", season=2019)
        home_rate = repository.analyze_statistics("home_win_rate", competition="Brasileirão", season=2019)
        biggest = repository.analyze_statistics("biggest_wins", competition="Brasileirão", season=2019, limit=3)
        away = repository.analyze_statistics("best_away_record", competition="Brasileirão", season=2019, limit=3)

        assert average["average_goals_per_match"] > 0
        assert 0 <= home_rate["home_win_rate"] <= 100
        assert len(biggest["matches"]) == 3
        assert away["leaders"]


class TestPlayerQueries:
    def test_given_player_filters_when_searching_then_returned_players_meet_every_filter(
        self, repository: SoccerRepository
    ) -> None:
        result = repository.search_players(nationality="Brazilian", min_overall=80, limit=20)

        assert result["count"] > 0
        assert all(player["nationality"] == "Brazil" for player in result["players"])
        assert all(player["overall"] >= 80 for player in result["players"])

    def test_given_an_absent_player_when_searching_then_the_server_returns_an_empty_result_not_an_invention(
        self, repository: SoccerRepository
    ) -> None:
        result = repository.search_players(name="Gabriel Barbosa", limit=5)

        assert result["count"] == 0
        assert result["players"] == []

    def test_given_a_team_profile_when_joining_sources_then_match_and_player_views_are_both_present(
        self, repository: SoccerRepository
    ) -> None:
        profile = repository.team_profile("Palmeiras", season=2023, match_limit=5, player_limit=5)

        assert profile["recent_matches"]["count"] > 0
        assert "players" in profile["players"]
        assert "source_join" in profile


class TestKnowledgeGraph:
    def test_given_a_team_neighborhood_when_explored_then_explicit_match_relationships_are_returned(
        self, repository: SoccerRepository
    ) -> None:
        graph = repository.knowledge_graph(team="Flamengo", season=2023, limit=5)

        assert graph["match_count"] > 0
        assert any(node["type"] == "team" for node in graph["nodes"])
        assert any(node["type"] == "match" for node in graph["nodes"])
        assert any(edge["relationship"] == "home_team_in" for edge in graph["edges"])
        assert any(edge["relationship"] == "part_of" for edge in graph["edges"])


class TestNaturalLanguageQueries:
    @pytest.mark.parametrize(
        "question",
        [
            "When did Flamengo last play Corinthians?",
            "Show me all Flamengo vs Fluminense matches",
            "What matches did Palmeiras play in 2023?",
            "Find all Copa do Brasil finals",
            "What is Corinthians' home record in 2022?",
            "Which team scored the most goals in Serie A 2023?",
            "Compare Palmeiras and Santos head-to-head",
            "Find all Brazilian players in the dataset",
            "Who are the highest-rated players at Flamengo?",
            "Show me all forwards from São Paulo FC",
            "Who won the 2019 Brasileirão?",
            "Show the 2018 Copa Libertadores bracket",
            "Which teams were relegated in 2020?",
            "What's the average goals per match in the Brasileirão?",
            "Which team has the best away record?",
            "Show me the biggest wins in the dataset",
            "What competitions has Palmeiras played in?",
            "Show me all derbies in 2023",
            "Who is Neymar Jr?",
            "Who is Gabriel Barbosa?",
        ],
    )
    def test_given_supported_benchmark_questions_when_asked_then_each_has_a_typed_answer(
        self, repository: SoccerRepository, question: str
    ) -> None:
        answer = NaturalLanguageQueryService(repository).ask(question)

        assert answer["intent"] != "unsupported"
        assert answer["answer"]
        assert isinstance(answer["data"], dict)

    def test_given_a_match_question_then_a_score_follow_up_uses_prior_context(self, repository: SoccerRepository) -> None:
        service = NaturalLanguageQueryService(repository)
        service.ask("When did Flamengo last play Corinthians?")
        answer = service.ask("What was the score?")

        assert answer["intent"] == "follow_up_score"
        assert "Flamengo" in answer["answer"] or "Corinthians" in answer["answer"]


class TestMCPProtocol:
    def test_given_mcp_initialize_and_tool_requests_when_served_then_standard_json_rpc_responses_are_emitted(
        self, repository: SoccerRepository
    ) -> None:
        server = BrazilianSoccerMCPServer(repository)
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "competition_standings", "arguments": {"competition": "Brasileirão", "season": 2019}},
            },
        ]
        output = StringIO()
        server.run_stdio(StringIO("\n".join(json.dumps(request) for request in requests)), output)
        responses = [json.loads(line) for line in output.getvalue().splitlines()]

        assert [response["id"] for response in responses] == [1, 2, 3]
        assert responses[0]["result"]["protocolVersion"] == LATEST_PROTOCOL_VERSION
        assert any(tool["name"] == "ask_soccer" for tool in responses[1]["result"]["tools"])
        assert responses[2]["result"]["structuredContent"]["standings"][0]["team"] == "Flamengo"

    def test_given_an_unknown_tool_when_called_then_mcp_returns_a_tool_error(self, repository: SoccerRepository) -> None:
        response = BrazilianSoccerMCPServer(repository).call_tool("not_a_tool")

        assert response["isError"] is True
        assert "Unknown tool" in response["content"][0]["text"]

    def test_given_invalid_tool_arguments_when_called_then_mcp_returns_a_recoverable_tool_error(
        self, repository: SoccerRepository
    ) -> None:
        server = BrazilianSoccerMCPServer(repository)

        assert server.call_tool("search_matches", ["not", "an", "object"])["isError"] is True
        assert server.call_tool("search_matches", {"date_from": "not-a-date"})["isError"] is True

    @pytest.mark.parametrize(
        ("message", "expected_code"),
        [
            ([], -32600),
            ({"jsonrpc": "2.0", "id": 1}, -32600),
            ({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": []}, -32602),
            ({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {}}, -32602),
            ({"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}}, -32601),
        ],
    )
    def test_given_invalid_json_rpc_requests_when_handled_then_protocol_errors_are_explicit(
        self, repository: SoccerRepository, message: object, expected_code: int
    ) -> None:
        response = BrazilianSoccerMCPServer(repository).handle_message(message)

        assert response is not None
        assert response["error"]["code"] == expected_code

    def test_given_stdio_parse_errors_and_notifications_when_served_then_only_real_requests_reply(
        self, repository: SoccerRepository
    ) -> None:
        server = BrazilianSoccerMCPServer(repository)
        output = StringIO()
        server.run_stdio(
            StringIO("\nnot-json\n" + json.dumps({"jsonrpc": "2.0", "method": "notifications/cancelled"}) + "\n"),
            output,
        )
        responses = [json.loads(line) for line in output.getvalue().splitlines()]

        assert len(responses) == 1
        assert responses[0]["error"]["code"] == -32700

    def test_given_readable_tool_shapes_then_mcp_has_useful_text_for_each_result_type(self) -> None:
        assert "No matches" in BrazilianSoccerMCPServer._human_readable_result({"matches": []})
        assert "No players" in BrazilianSoccerMCPServer._human_readable_result({"players": []})
        assert "No completed matches" in BrazilianSoccerMCPServer._human_readable_result({"standings": []})
        assert "No teams" in BrazilianSoccerMCPServer._human_readable_result({"leaders": []})
        assert "example" in BrazilianSoccerMCPServer._human_readable_result({"example": True})

    def test_given_main_when_started_without_arguments_then_it_uses_the_default_repository(
        self, repository: SoccerRepository, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        used: dict[str, object] = {}

        monkeypatch.setattr(
            mcp_server.SoccerRepository,
            "from_default_data",
            classmethod(lambda cls: repository),
        )
        monkeypatch.setattr(
            mcp_server.BrazilianSoccerMCPServer,
            "run_stdio",
            lambda self: used.setdefault("repository", self.repository),
        )

        mcp_server.main([])

        assert used["repository"] is repository


class TestPerformance:
    def test_given_loaded_data_when_running_a_simple_lookup_then_it_returns_under_two_seconds(
        self, repository: SoccerRepository
    ) -> None:
        started = time.perf_counter()
        result = repository.search_matches(team="Flamengo", limit=50)

        assert result["matches"]
        assert time.perf_counter() - started < 2.0

    def test_given_loaded_data_when_running_an_aggregate_then_it_returns_under_five_seconds(
        self, repository: SoccerRepository
    ) -> None:
        started = time.perf_counter()
        result = repository.competition_standings("Brasileirão", 2019)

        assert result["standings"]
        assert time.perf_counter() - started < 5.0
