"""Tests for the command line client.

Context
-------
The CLI is the fastest way for a human to check the server's behaviour, and
``brazilian-soccer demo`` doubles as the acceptance run for the specification's
sample questions.  These tests drive ``main()`` in-process and capture stdout.
"""

from __future__ import annotations

import json

import pytest

from brazilian_soccer.cli import DEMO_QUESTIONS, main


def run(capsys, *argv) -> str:
    code = main(list(argv))
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    return captured.out


def test_tools_command_lists_every_tool(capsys, graph):
    output = run(capsys, "tools")
    assert "find_matches" in output and "dataset_summary" in output
    assert output.count("\n\n") >= 16


def test_summary_command(capsys, graph):
    output = run(capsys, "summary")
    assert "unique fixtures" in output
    assert "fifa_data.csv" in output


def test_call_command_parses_key_value_arguments(capsys, graph):
    output = run(capsys, "call", "standings", "season=2019")
    assert "Flamengo" in output and "Champion" in output


def test_call_command_parses_json_values(capsys, graph):
    output = run(capsys, "call", "compare_seasons", "seasons=[2018,2019]")
    assert "Palmeiras" in output and "Flamengo" in output


def test_json_output_is_machine_readable(capsys, graph):
    output = run(capsys, "--json", "call", "standings", "season=2019")
    payload = json.loads(output)
    assert payload["champion"] == "Flamengo"
    assert len(payload["table"]) == 20


def test_unknown_tool_exits_non_zero(capsys, graph):
    assert main(["call", "nope"]) == 2
    assert "Unknown tool" in capsys.readouterr().err


def test_failing_tool_exits_non_zero(capsys, graph):
    assert main(["call", "team_stats", "team=Real Madrid"]) == 1


def test_bad_argument_syntax_is_rejected(graph):
    with pytest.raises(SystemExit):
        main(["call", "standings", "2019"])


def test_demo_command_answers_every_question(capsys, graph):
    output = run(capsys, "demo")
    assert f"{len(DEMO_QUESTIONS)} questions answered, 0 error(s)." in output
    for question, _, _ in DEMO_QUESTIONS:
        assert question in output
