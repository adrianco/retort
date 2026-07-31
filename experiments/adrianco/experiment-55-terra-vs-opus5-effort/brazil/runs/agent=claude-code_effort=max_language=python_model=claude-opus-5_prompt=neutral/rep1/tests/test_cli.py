"""The terminal client.

Context
-------
Feature: Command line access

  Scenario: Ask a question without an MCP client
    Given the package is installed
    When a tool is called from the terminal
    Then the same text an LLM would receive is printed
"""

from __future__ import annotations

import pytest

from brazilian_soccer.cli import main, parse_value


class TestArgumentParsing:
    """Scenario: key=value arguments."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("5", 5),
            ("true", True),
            ("[2018,2019]", [2018, 2019]),
            ("Serie A", "Serie A"),
            ("Grêmio", "Grêmio"),
        ],
    )
    def test_given_a_value_when_parsed_then_json_types_are_recognised(self, raw, expected):
        """
        Given a command line value
        When it is parsed
        Then numbers, booleans and lists become Python objects and text stays text
        """
        assert parse_value(raw) == expected


class TestCommands:
    """Scenario: Running the client."""

    def test_given_the_tools_command_when_run_then_every_tool_is_listed(self, capsys):
        """
        Given a user exploring the server
        When the tools command runs
        Then each tool is printed with its arguments and summary
        """
        assert main(["tools"]) == 0
        output = capsys.readouterr().out

        assert "standings(competition, season)" in output
        assert "find_matches(" in output
        assert output.count("\n") > 30

    def test_given_a_call_command_when_run_then_the_answer_is_printed(self, capsys):
        """
        Given a question expressed as a tool call
        When the call command runs
        Then the formatted answer is printed
        """
        assert main(["call", "standings", "competition=Serie A", "season=2019"]) == 0
        output = capsys.readouterr().out

        assert "1. Flamengo" in output and "Champion" in output

    def test_given_a_call_with_a_list_argument_when_run_then_it_is_passed_through(
        self, capsys
    ):
        """
        Given a tool that takes a list
        When the value is written as JSON on the command line
        Then it reaches the tool intact
        """
        assert main(["call", "compare_seasons", "competition=Serie A", "seasons=[2018,2019]"]) == 0
        output = capsys.readouterr().out

        assert "2018:" in output and "2019:" in output

    def test_given_a_malformed_argument_when_run_then_it_fails_clearly(self):
        """
        Given an argument that is not key=value
        When the call command runs
        Then the client exits with an explanation
        """
        with pytest.raises(SystemExit):
            main(["call", "standings", "oops"])

    def test_given_the_demo_command_when_run_then_a_transcript_is_printed(self, capsys):
        """
        Given the sample question set
        When the demo command runs with a limit
        Then a numbered transcript is printed
        """
        assert main(["demo", "--limit", "2"]) == 0
        output = capsys.readouterr().out

        assert "Q1." in output and "Q2." in output
