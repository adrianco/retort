"""Feature: The offline CLI driver.

Context
-------
``python -m brazilian_soccer.cli demo`` is the no-MCP-client way to see the
server's answers, and doubles as an end-to-end smoke test: every demo question
must produce non-trivial output without raising.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.cli import DEMO_QUESTIONS, main
from brazilian_soccer.queries import SoccerQueries


@pytest.mark.parametrize(
    "question,answer",
    DEMO_QUESTIONS,
    ids=[question for question, _ in DEMO_QUESTIONS],
)
def test_every_demo_question_answers(
    queries: SoccerQueries, question: str, answer
) -> None:
    # Given the loaded graph
    # When the demo question is answered
    text = answer(queries)
    # Then it produces real content
    assert isinstance(text, str)
    assert len(text.strip()) > 20, question


def test_demo_covers_at_least_twenty_questions() -> None:
    assert len(DEMO_QUESTIONS) >= 20


@pytest.mark.parametrize(
    "argv",
    [
        ["overview"],
        ["matches", "--team", "Flamengo", "--season", "2019", "--limit", "3"],
        ["h2h", "Palmeiras", "Santos"],
        ["team", "Gremio"],
        ["standings", "2019"],
        ["players", "--nationality", "Brazil", "--limit", "3"],
        ["stats", "--competition", "Brasileirao", "--season", "2019"],
    ],
)
def test_cli_subcommands_run(argv: list[str], capsys) -> None:
    assert main(argv) == 0
    captured = capsys.readouterr().out
    assert captured.strip()
