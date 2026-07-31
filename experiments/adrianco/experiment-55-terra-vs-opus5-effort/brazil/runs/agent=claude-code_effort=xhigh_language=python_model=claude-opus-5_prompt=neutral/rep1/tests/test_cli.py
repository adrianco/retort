"""
Tests for the command line interface.

Context
-------
The CLI is the hand-operable face of the same tool layer the MCP server
exposes, so these tests confirm the plumbing (argument parsing, JSON output,
exit codes) rather than re-testing the analytics.
"""

from __future__ import annotations

import json

import pytest

from brazilian_soccer import cli


def test_tools_subcommand_lists_every_tool(capsys, graph):
    assert cli.main(["tools"]) == 0
    output = capsys.readouterr().out
    for name in ("search_matches", "head_to_head", "competition_standings",
                 "search_players", "dataset_summary"):
        assert name in output


def test_summary_subcommand(capsys, graph):
    assert cli.main(["summary"]) == 0
    output = capsys.readouterr().out
    assert "Brazilian Soccer knowledge graph" in output
    assert "fifa_data.csv" in output


def test_call_subcommand_prints_the_rendered_answer(capsys, graph):
    assert cli.main(["call", "team_stats", "team=Palmeiras", "season=2022",
                     "competition=brasileirao"]) == 0
    output = capsys.readouterr().out
    assert "Matches: 38" in output
    assert "Win rate" in output


def test_call_subcommand_json_output(capsys, graph):
    assert cli.main(["call", "competition_standings", "season=2019",
                     "competition=brasileirao", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["standings"][0]["points"] == 90


def test_call_subcommand_parses_json_values(capsys, graph):
    assert cli.main(["call", "compare_seasons", "seasons=[2018,2019]"]) == 0
    output = capsys.readouterr().out
    assert "2018" in output and "2019" in output


def test_call_subcommand_accepts_an_args_object(capsys, graph):
    assert cli.main(["call", "head_to_head",
                     "--args", json.dumps({"team_a": "Flamengo", "team_b": "Fluminense",
                                           "limit": 2})]) == 0
    assert "Fla-Flu" in capsys.readouterr().out


def test_unknown_tool_exits_non_zero(capsys, graph):
    assert cli.main(["call", "nope"]) == 2
    assert "unknown tool" in capsys.readouterr().err


def test_malformed_pair_is_rejected(graph):
    with pytest.raises(SystemExit):
        cli.main(["call", "team_stats", "Palmeiras"])


def test_missing_command_is_rejected():
    with pytest.raises(SystemExit):
        cli.main([])


def test_serve_subcommand_delegates_to_the_mcp_server(monkeypatch):
    calls: list[str] = []
    import brazilian_soccer.server as server_module

    monkeypatch.setattr(server_module, "main", lambda transport="stdio": calls.append(transport))
    assert cli.main(["serve", "--transport", "stdio"]) == 0
    assert calls == ["stdio"]
