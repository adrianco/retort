from __future__ import annotations

import sys
from types import ModuleType

import server


class FakeMCPServer:
    def __init__(self, name: str, **kwargs: object) -> None:
        self.name = name
        self.kwargs = kwargs
        self.tools: list[str] = []
        self.resources: list[tuple[str, str]] = []
        self.prompts: list[str] = []

    def tool(self):
        def decorate(function):
            self.tools.append(function.__name__)
            return function
        return decorate

    def resource(self, uri: str):
        def decorate(function):
            self.resources.append((uri, function.__name__))
            return function
        return decorate

    def prompt(self):
        def decorate(function):
            self.prompts.append(function.__name__)
            return function
        return decorate


def test_service_functions_return_structured_results() -> None:
    summary = server.dataset_summary()
    assert summary["files"]["fifa_data.csv"] == 18_207
    matches = server.search_matches(team="Flamengo", season=2019, limit=3)
    assert matches["count"] == 3
    assert all("score" in row for row in matches["matches"])
    answer = server.ask_soccer("Who won the 2019 Brasileirão?")
    assert answer["intent"] == "standings"
    assert "Flamengo" in answer["answer"]


def test_mcp_registration_exposes_tools_resource_and_prompt(monkeypatch) -> None:
    fake_package = ModuleType("mcp")
    fake_server_module = ModuleType("mcp.server")
    fake_server_module.MCPServer = FakeMCPServer
    fake_package.server = fake_server_module
    monkeypatch.setitem(sys.modules, "mcp", fake_package)
    monkeypatch.setitem(sys.modules, "mcp.server", fake_server_module)

    mcp = server.create_mcp_server()
    assert isinstance(mcp, FakeMCPServer)
    assert {
        "search_matches", "get_team_statistics", "compare_teams", "find_players",
        "get_standings", "get_competition_statistics", "get_biggest_wins",
        "find_derbies", "rank_teams", "get_club_overview", "ask_soccer", "dataset_summary",
    } == set(mcp.tools)
    assert mcp.resources == [("soccer://dataset/summary", "soccer_dataset_summary")]
    assert mcp.prompts == ["analyze_brazilian_soccer"]

