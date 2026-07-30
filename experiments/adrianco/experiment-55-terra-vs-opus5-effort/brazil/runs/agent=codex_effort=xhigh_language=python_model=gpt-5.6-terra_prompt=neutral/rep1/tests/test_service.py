"""Behaviour-focused tests for the Brazilian soccer query service."""

from __future__ import annotations

from pathlib import Path

import pytest

from soccer_mcp import SoccerData
from soccer_mcp.normalization import normalize_team


@pytest.fixture(scope="session")
def data() -> SoccerData:
    return SoccerData.load(Path(__file__).resolve().parents[1] / "data" / "kaggle")


def test_all_six_csv_files_are_loaded(data: SoccerData) -> None:
    summary = data.data_summary()
    assert summary["player_count"] == 18_207
    assert {source["id"] for source in summary["sources"]} == {
        "brasileirao", "brazilian_cup", "libertadores", "extended_statistics", "historical_brasileirao", "fifa_players",
    }
    assert summary["match_count"] == 23_954


def test_team_variants_are_normalized() -> None:
    assert normalize_team("Flamengo-RJ") == normalize_team("Flamengo")
    assert normalize_team("São Paulo FC") == normalize_team("Sao Paulo")
    assert normalize_team("Sport Club Corinthians Paulista") == normalize_team("Corinthians")
    assert normalize_team("Atlético-MG") != normalize_team("Athletico-PR")


def test_given_team_variant_finds_brasileirao_matches(data: SoccerData) -> None:
    result = data.search_matches(team="Flamengo", competition="Brasileirão", season=2022, source="brasileirao", limit=500)
    assert result["count"] == 38
    assert all(match["competition"] == "Brasileirão Série A" for match in result["matches"])
    assert all("Flamengo" in {match["home_team"], match["away_team"]} for match in result["matches"])


def test_date_range_and_competition_filter(data: SoccerData) -> None:
    result = data.search_matches(
        competition="Copa do Brasil", date_from="2023-09-01", date_to="2023-09-30", limit=100,
    )
    assert result["count"] > 0
    assert all("2023-09-01" <= match["date"] <= "2023-09-30" for match in result["matches"])
    assert all(match["competition"] == "Copa do Brasil" for match in result["matches"])


def test_team_home_record_calculates_consistent_totals(data: SoccerData) -> None:
    result = data.team_statistics("Corinthians", season=2022, competition="Brasileirão", venue="home")
    record = result["record"]
    assert result["matches_found"] == 19
    assert record["matches"] == record["wins"] + record["draws"] + record["losses"]
    assert record["matches"] <= result["matches_found"]
    assert record["goals_for"] - record["goals_against"] == record["goal_difference"]


def test_head_to_head_returns_only_the_requested_pair(data: SoccerData) -> None:
    result = data.head_to_head("Flamengo", "Fluminense", competition="Brasileirão", limit=100)
    assert result["matches_found"] > 0
    assert result["record"]["team_a_wins"] + result["record"]["team_b_wins"] + result["record"]["draws"] <= result["matches_found"]
    assert all({match["home_team"], match["away_team"]} == {"Flamengo", "Fluminense"} for match in result["matches"])


def test_standings_award_three_points_for_wins(data: SoccerData) -> None:
    standings = data.competition_standings("Brasileirão", season=2019)
    assert standings["matches_used"] == 380
    assert standings["champion"] == "Flamengo"
    assert all(row["points"] == row["wins"] * 3 + row["draws"] for row in standings["standings"])


def test_competition_statistics_include_goal_rates_and_biggest_wins(data: SoccerData) -> None:
    result = data.competition_statistics("Brasileirão", season=2022, biggest_wins_limit=3)
    assert result["matches_found"] == 380
    assert result["completed_matches"] > 0
    assert result["average_goals_per_match"] > 0
    assert len(result["biggest_wins"]) == 3
    assert 0 <= result["home_win_rate"] <= 100


def test_player_search_supports_brazilian_and_position_group(data: SoccerData) -> None:
    result = data.search_players(nationality="Brazilian", position="forward", min_overall=80, limit=100)
    assert result["count"] > 0
    assert all(player["nationality"] == "Brazil" for player in result["players"])
    assert all(player["position"] in {"ST", "CF", "LW", "RW", "LF", "RF"} for player in result["players"])


def test_team_overview_combines_match_and_player_datasets(data: SoccerData) -> None:
    result = data.team_overview("Gremio", season=2018, player_limit=5)
    assert result["statistics"]["matches_found"] > 0
    assert result["players"]["count"] > 0
    assert all("Gremio" in player["club"] or "Grêmio" in player["club"] for player in result["players"]["players"])


def test_extended_statistics_source_exposes_match_statistics(data: SoccerData) -> None:
    result = data.search_matches(source="extended_statistics", competition="Serie A", season=2023, limit=1)
    details = result["matches"][0]["details"]
    assert {"home_corners", "away_corners", "home_shots", "away_shots"} <= details.keys()


def test_natural_language_routes_a_last_match_question(data: SoccerData) -> None:
    result = data.answer_question("When did Flamengo last play Corinthians?")
    assert result["intent"] == "latest_match"
    assert result["answer"]["returned"] == 1
    match = result["answer"]["matches"][0]
    assert {match["home_team"], match["away_team"]} == {"Flamengo", "Corinthians"}


def test_natural_language_routes_position_and_club_player_question(data: SoccerData) -> None:
    result = data.answer_question("Show all forwards from Grêmio")
    assert result["intent"] == "player_search"
    assert result["answer"]["count"] > 0
    assert all(player["position"] in {"ST", "CF", "LW", "RW", "LF", "RF"} for player in result["answer"]["players"])


def test_invalid_date_range_is_rejected(data: SoccerData) -> None:
    with pytest.raises(ValueError, match="date_from"):
        data.search_matches(date_from="2023-02-01", date_to="2023-01-01")
