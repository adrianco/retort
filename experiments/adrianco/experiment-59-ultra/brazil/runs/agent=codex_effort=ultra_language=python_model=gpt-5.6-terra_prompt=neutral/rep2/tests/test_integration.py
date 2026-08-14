"""End-to-end behavior tests against the supplied CSV snapshots."""

from __future__ import annotations

from time import perf_counter

import pytest

from brazilian_soccer_mcp.normalization import normalize_team
from brazilian_soccer_mcp.service import QueryValidationError


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        ("Show me all Flamengo vs Fluminense matches.", "head_to_head"),
        ("What matches did Palmeiras play in 2023?", "match_search"),
        ("Find all Copa do Brasil finals.", "match_search"),
        ("When did Flamengo last play Corinthians?", "last_match"),
        ("What is Corinthians' home record in 2022?", "team_statistics"),
        ("Which team scored the most goals in Serie A 2023?", "teams_by_goals"),
        ("Which team has the best home record?", "best_team_record"),
        ("Which team has the best away record?", "best_team_record"),
        ("Find all Brazilian players in the dataset.", "search_players"),
        ("Who are the highest-rated players at Flamengo?", "search_players"),
        ("Show me all forwards from São Paulo FC.", "search_players"),
        ("Who is L. Messi?", "search_players"),
        ("Who won the 2019 Brasileirão?", "competition_winner"),
        ("Show the 2019 Brasileirão final standings.", "competition_standings"),
        ("Show the 2018 Copa Libertadores bracket.", "libertadores_by_stage"),
        ("What competitions has Palmeiras played in?", "team_competitions"),
        ("What's the average goals per match in the Brasileirão?", "competition_statistics"),
        ("Show me the biggest wins in the dataset.", "competition_statistics"),
        ("Compare the 2018 and 2019 seasons.", "compare_seasons"),
        ("Show all derbies in 2023.", "derby_matches"),
        ("Who was the top scorer in the 2019 Brasileirão?", "top_scorers_unavailable"),
    ],
)
def test_given_sample_natural_language_questions_when_routed_then_each_has_a_deterministic_answer(
    full_service, question: str, expected_intent: str
) -> None:
    result = full_service.answer_question(question)
    assert result["intent"] == expected_intent
    assert result["answer"]


def test_given_2019_brasileirao_when_calculating_standings_then_champion_is_dataset_derived(full_service) -> None:
    standings = full_service.competition_standings(2019)
    assert standings["standings"]
    assert standings["standings"][0]["points"] >= standings["standings"][1]["points"]
    assert normalize_team(standings["standings"][0]["team"]) == "flamengo"
    assert standings["calculated_from_loaded_data"] is True


def test_given_cross_file_join_when_querying_players_at_clubs_faced_then_temporal_limitation_is_explicit(full_service) -> None:
    result = full_service.players_at_clubs_faced("Palmeiras", 2023)
    assert result["players"]
    assert "not evidence" in result["note"]
    assert "FIFA dataset snapshot" in result["players"][0]["club_data_note"]


def test_given_invalid_date_range_when_searching_matches_then_a_helpful_validation_error_is_returned(full_service) -> None:
    with pytest.raises(QueryValidationError, match="start_date must be on or before end_date"):
        full_service.search_matches(team="Flamengo", start_date="2023-12-31", end_date="2023-01-01")


def test_given_warm_catalog_when_querying_then_simple_and_aggregate_targets_are_met(full_service) -> None:
    started = perf_counter()
    result = full_service.search_matches(team="Flamengo", season=2023)
    simple_elapsed = perf_counter() - started

    started = perf_counter()
    statistics = full_service.competition_statistics(competition="Brasileirão", season=2023)
    aggregate_elapsed = perf_counter() - started

    assert result["total_matches"] > 0
    assert statistics["complete_match_count"] > 0
    assert simple_elapsed < 2.0
    assert aggregate_elapsed < 5.0

