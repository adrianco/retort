"""The specification's sample questions, end to end.

Context
-------
Feature: Answering natural language questions

  Scenario: The demo question set
    Given the MCP server is running against the provided data
    When each sample question from the specification is asked
    Then a substantive answer comes back
    And at least 20 distinct questions are answerable

Every question is routed through the MCP tools, so this is the acceptance test
for the "Data Coverage" success criteria in the specification.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.demo import SAMPLE_QUESTIONS, render_demo, run_demo

#: Phrases that indicate the server could not answer.
FAILURE_MARKERS = ("Traceback", "No matches found for those filters.")


@pytest.fixture(scope="module")
def answers(graph):
    """Every sample question answered once, through the MCP server."""
    return run_demo(graph=graph)


class TestSampleQuestions:
    """Scenario: The sample question set is answerable."""

    def test_given_the_specification_when_counted_then_at_least_20_questions_exist(self):
        """
        Given the specification asks for at least 20 answerable questions
        When the demo set is counted
        Then it comfortably exceeds that
        """
        assert len(SAMPLE_QUESTIONS) >= 20
        assert len({question.question for question in SAMPLE_QUESTIONS}) == len(SAMPLE_QUESTIONS)

    def test_given_every_question_when_asked_then_a_substantive_answer_returns(self, answers):
        """
        Given the MCP server is running against the provided data
        When each sample question is asked
        Then every answer is non-empty and free of failure markers
        """
        assert len(answers) == len(SAMPLE_QUESTIONS)
        for question, answer in answers:
            assert answer.strip(), question.question
            assert len(answer) > 40, f"answer too short for: {question.question}"
            for marker in FAILURE_MARKERS:
                assert marker not in answer, f"{question.question}: {marker}"

    def test_given_the_question_set_when_grouped_then_all_capabilities_are_covered(self):
        """
        Given the five capability areas in the specification
        When the demo questions are grouped by tool
        Then match, team, player, competition and statistical tools are all used
        """
        tools = {question.tool for question in SAMPLE_QUESTIONS}

        assert {"find_matches", "head_to_head"} <= tools  # match queries
        assert {"team_stats", "team_profile", "team_rankings"} <= tools  # team queries
        assert {"search_players", "player_profile", "team_squad"} <= tools  # player queries
        assert {"standings", "knockout_bracket"} <= tools  # competition queries
        assert {"competition_stats", "biggest_wins", "derbies"} <= tools  # statistics

    @pytest.mark.parametrize(
        "question_fragment, expected",
        [
            ("Who won the 2019 Brasileirão", "Flamengo"),
            ("What is Corinthians' home record in 2022", "Matches: 19"),
            ("Show the 2018 Copa Libertadores bracket", "River Plate"),
            ("Find all Brazilian players in the dataset", "Neymar"),
            ("Show me all Flamengo vs Fluminense matches", "Fla-Flu"),
            ("Which teams were relegated in 2020", "Relegated"),
            ("What competitions has Palmeiras played in", "Copa Libertadores"),
            ("Compare the 2018 and 2019 seasons", "Champion"),
            ("What does this dataset cover", "Copa do Brasil"),
        ],
    )
    def test_given_a_known_question_when_answered_then_the_answer_is_right(
        self, answers, question_fragment, expected
    ):
        """
        Given a question with a verifiable answer
        When it is asked through the server
        Then the expected fact appears in the response
        """
        answer = next(
            text for question, text in answers if question_fragment in question.question
        )

        assert expected in answer

    def test_given_the_answers_when_rendered_then_a_transcript_is_produced(self, answers):
        """
        Given the answered questions
        When they are rendered
        Then a readable transcript with numbered questions is produced
        """
        transcript = render_demo(answers[:3])

        assert "Q1." in transcript and "Q3." in transcript
        assert "->" in transcript  # shows which tool answered
