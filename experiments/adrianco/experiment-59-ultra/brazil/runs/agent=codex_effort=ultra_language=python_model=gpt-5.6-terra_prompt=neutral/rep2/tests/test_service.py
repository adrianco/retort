"""BDD-style query scenarios using a small, independently known graph."""

from datetime import date

import pytest

from brazilian_soccer_mcp.service import SoccerQueryService

from .conftest import make_catalog, match, player


@pytest.fixture()
def service() -> SoccerQueryService:
    # `extended_match_statistics:duplicate` represents a cross-source overlap.
    # The three primary records form the coherent Brasileirão source.
    matches = [
        match("p1", "Palmeiras-SP", "Flamengo-RJ", 2, 1, day=date(2023, 1, 1)),
        match("p2", "Flamengo-RJ", "Palmeiras-SP", 3, 3, day=date(2023, 2, 1)),
        match("p3", "Flamengo-RJ", "Fluminense-RJ", 1, 0, day=date(2023, 3, 1)),
        match(
            "duplicate",
            "Palmeiras",
            "Flamengo",
            2,
            1,
            day=date(2023, 1, 1),
            source="extended_match_statistics",
        ),
        match(
            "cup-final",
            "Palmeiras-SP",
            "Flamengo-RJ",
            1,
            0,
            day=date(2023, 4, 1),
            competition="Copa do Brasil",
            source="brazilian_cup_matches",
            round_value="Final",
        ),
        match(
            "cup-semi",
            "Palmeiras-SP",
            "Flamengo-RJ",
            1,
            0,
            day=date(2023, 3, 1),
            competition="Copa do Brasil",
            source="brazilian_cup_matches",
            round_value="Semi-final",
        ),
    ]
    return SoccerQueryService(
        make_catalog(
            matches,
            [
                player("1", "Gabriel Barbosa", club="São Paulo FC", position="ST", overall=82),
                player("2", "Álisson", club="Palmeiras", position="GK", overall=86),
            ],
        )
    )


def test_given_team_alias_and_inclusive_dates_when_searching_matches_then_matching_source_rows_are_returned(service) -> None:
    result = service.search_matches(
        team="Palmeiras",
        start_date="01/01/2023",
        end_date="2023-02-01",
    )
    assert result["total_matches"] == 3
    assert all(match["date"] in {"2023-01-01", "2023-02-01"} for match in result["matches"])
    assert {match["home_team"] for match in result["matches"]} >= {"Palmeiras-SP", "Flamengo-RJ"}


def test_given_reversed_fixtures_when_comparing_teams_then_head_to_head_is_orientation_independent(service) -> None:
    result = service.compare_teams("Flamengo", "Palmeiras", competition="Brasileirão")
    assert result["total_matches"] == 2
    assert result["head_to_head"] == {"team_a_wins": 0, "team_b_wins": 1, "draws": 1}


def test_given_overlapping_sources_when_calculating_team_statistics_then_one_coherent_source_is_used(service) -> None:
    result = service.team_statistics("Palmeiras", competition="Brasileirão")
    assert result["matches"] == 2
    assert result["wins"] == 1
    assert result["draws"] == 1
    assert "competition-season aggregate" in result["source_selection_policy"]


def test_given_final_round_filter_when_searching_cup_matches_then_semi_finals_are_excluded(service) -> None:
    result = service.search_matches(competition="Copa do Brasil", round_contains="final")
    assert result["total_matches"] == 1
    assert result["matches"][0]["round"] == "Final"


def test_given_normalized_player_club_and_position_when_searching_then_accent_and_group_aliases_work(service) -> None:
    result = service.search_players(club="Sao Paulo", position="forwards")
    assert result["total_players"] == 1
    assert result["players"][0]["name"] == "Gabriel Barbosa"


def test_given_dataset_without_goal_events_when_requesting_top_scorers_then_service_refuses_to_infer_them(service) -> None:
    result = service.top_scorers_status(competition="Brasileirão", season=2023)
    assert result["available"] is False
    assert "cannot be used to infer scorers" in result["reason"]


def test_given_explicit_rivalry_mapping_when_searching_derbies_then_only_known_pairs_are_selected(service) -> None:
    result = service.derby_matches(season=2023)
    assert result["total_matches"] == 1
    assert result["matches"][0]["derby"] == "Fla-Flu"


def test_given_partial_league_coverage_when_requesting_relegation_then_a_caveat_is_returned(service) -> None:
    result = service.relegated_teams(2023)
    assert result["relegation_status"] == "not_determined"
    assert "incomplete" in result["formatted_answer"]


def test_given_unknown_team_when_searching_then_the_response_is_empty_without_inventing_a_match(service) -> None:
    result = service.search_matches(team="Atléticos")
    assert result["total_matches"] == 0
    assert result["matches"] == []


def test_given_contextual_follow_up_when_last_match_is_present_then_score_is_returned(service) -> None:
    result = service.answer_question(
        "What was the score?",
        context={"last_match": {"home_team": "Palmeiras", "away_team": "Flamengo", "home_goals": 2, "away_goals": 1}},
    )
    assert result["intent"] == "contextual_score"
    assert result["answer"] == "Palmeiras 2-1 Flamengo."


def test_given_team_entity_when_building_graph_then_match_competition_and_season_edges_are_explicit(service) -> None:
    result = service.entity_graph("team", "Palmeiras", competition="Brasileirão")
    node_types = {node["type"] for node in result["nodes"]}
    edge_types = {edge["type"] for edge in result["edges"]}
    assert {"Team", "Match", "Competition", "Season"} <= node_types
    assert {"HOME_TEAM", "AWAY_TEAM", "IN_COMPETITION", "IN_SEASON", "OPPONENT"} <= edge_types
