from __future__ import annotations

import pytest


QUESTIONS = (
    "Show me all Flamengo vs Fluminense matches",
    "What matches did Palmeiras play in 2023?",
    "Find all Copa do Brasil finals",
    "What is Corinthians' home record in 2022 Brasileirão?",
    "Which team scored the most goals in Serie A 2023?",
    "Compare Palmeiras and Santos head-to-head",
    "Find all Brazilian players in the dataset",
    "Who are the highest-rated players at Grêmio?",
    "Show me all forwards from São Paulo FC",
    "Who won the 2019 Brasileirão?",
    "Show the 2018 Copa Libertadores bracket",
    "Which teams were relegated in 2020?",
    "What's the average goals per match in the Brasileirão?",
    "Which team has the best away record?",
    "Show me the biggest wins in the dataset",
    "When did Flamengo last play Corinthians?",
    "Who is Neymar Jr?",
    "Which players play for Grêmio?",
    "Show me all derbies in 2023",
    "What competitions has Palmeiras played in?",
)


@pytest.mark.parametrize("question", QUESTIONS)
def test_given_sample_question_when_asked_then_it_routes_to_a_supported_behavior(natural_query, question):
    result = natural_query.ask(question, limit=10)
    assert result["intent"] != "unsupported"
    assert result["answer"]
    assert "data" in result


def test_given_context_free_score_question_when_asked_then_server_requests_clarification(natural_query):
    result = natural_query.ask("What was the score?")
    assert result["intent"] == "clarification"


def test_given_unanswerable_top_scorer_when_asked_then_server_does_not_invent_data(natural_query):
    result = natural_query.ask("Who was the top scorer in 2019?")
    assert result["intent"] == "unavailable_statistic"
    assert result["data"]["missing_field"] == "goal scorer"
