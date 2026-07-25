"""Feature: The sample questions from the specification are answerable.

  Scenario: An LLM answers a user's question through the MCP tools
    Given the knowledge graph is loaded
    When each of the sample questions is routed to its tool
    Then a substantive answer comes back quickly

The specification asks for at least twenty answerable questions; the demo list
is the single source of truth for both this test and ``python -m
brazilian_soccer.demo``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("mcp.server.fastmcp",
                    reason="the MCP SDK is needed to route questions to tools")

from brazilian_soccer.demo import SAMPLE_QUESTIONS, answer  # noqa: E402

#: Phrases that mean "I could not answer" — none should appear in the demo run.
FAILURE_MARKERS = (
    "No team matching",
    "Unknown competition",
    "Cannot answer that",
    "no matches found",
    "No matches found",
)


def test_at_least_twenty_sample_questions_exist():
    """
    Given the specification asks for twenty answerable questions
    When the demo list is counted
    Then there are at least twenty, spread across every tool category
    """
    assert len(SAMPLE_QUESTIONS) >= 20
    tools = {entry[1] for entry in SAMPLE_QUESTIONS}
    assert len(tools) >= 12


@pytest.mark.parametrize("entry", SAMPLE_QUESTIONS,
                         ids=[entry[0] for entry in SAMPLE_QUESTIONS])
def test_sample_question_is_answered(graph, fastest, entry):
    """
    Given one of the sample questions
    When it is routed to its MCP tool
    Then a substantive answer is returned in under two seconds
    """
    response, elapsed = fastest(answer, entry)

    assert isinstance(response, str)
    assert len(response) > 60, response
    assert not any(marker in response for marker in FAILURE_MARKERS), response
    assert elapsed < 2.0, f"{entry[0]} took {elapsed:.2f}s"


def test_specification_examples_produce_the_documented_shapes(graph):
    """
    Given the answer formats printed in the specification
    When the matching questions are asked
    Then the responses carry the same landmarks
    """
    from brazilian_soccer import server

    head_to_head = server.head_to_head(team_a="Flamengo", team_b="Fluminense")
    assert "Head-to-head:" in head_to_head and "draws" in head_to_head

    record = server.team_statistics(team="Corinthians", season=2022,
                                    competition="Brasileirão", venue="home")
    assert "- Matches: 19" in record and "Win rate:" in record

    table = server.standings(competition="Brasileirão", season=2019)
    assert "1. Flamengo - 90 pts (28W, 6D, 4L)" in table

    players = server.search_players(nationality="Brazil", limit=3)
    assert "1. Neymar Jr - Overall: 92" in players

    stats = server.dataset_statistics()
    assert "Average goals per match:" in stats and "Home win rate:" in stats
