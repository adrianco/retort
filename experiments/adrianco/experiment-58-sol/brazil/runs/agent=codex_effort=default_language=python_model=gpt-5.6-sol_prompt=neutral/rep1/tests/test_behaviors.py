from __future__ import annotations

import time

import pytest


def test_find_matches_between_two_teams(service):
    result = service.search_matches("Flamengo", "Fluminense")
    assert result["count"] > 0
    assert all({"date", "home_team", "away_team", "home_goals", "away_goals", "competition"} <= set(m)
               for m in result["matches"])


def test_find_team_matches_in_season(service):
    result = service.search_matches(team="Palmeiras", season=2023)
    assert result["count"] > 0
    assert all(m["season"] == 2023 for m in result["matches"])


def test_find_cup_final_by_stage(service):
    result = service.search_matches(competition="Libertadores", stage="final", limit=100)
    assert result["count"] > 0
    assert all("final" in m["round_or_stage"].lower() for m in result["matches"])


def test_team_statistics(service):
    result = service.team_statistics("Palmeiras", season=2023, competition="Brasileirão")
    assert result["matches"] > 0
    assert result["matches"] == result["wins"] + result["draws"] + result["losses"]
    assert result["goals_for"] >= 0 and result["goals_against"] >= 0


def test_home_record(service):
    result = service.team_statistics("Corinthians", season=2022, competition="Brasileirão", venue="home")
    assert result["matches"] > 0
    assert 0 <= result["win_rate"] <= 100


def test_head_to_head_totals(service):
    result = service.head_to_head("Palmeiras", "Santos")
    assert result["matches"] > 0
    assert result["matches"] == result["team1_wins"] + result["team2_wins"] + result["draws"]


def test_standings(service):
    result = service.standings(2019, "Brasileirão")
    table = result["standings"]
    assert table
    assert [r["position"] for r in table] == list(range(1, len(table) + 1))
    assert all(r["points"] == r["wins"] * 3 + r["draws"] for r in table)
    assert max(r["played"] for r in table) <= 38  # overlapping CSVs are not double-counted


def test_top_brazilian_players(service):
    result = service.search_players(nationality="Brazil", limit=10)
    assert result["count"] > 10
    assert all(player["nationality"] == "Brazil" for player in result["players"])
    ratings = [player["overall"] for player in result["players"]]
    assert ratings == sorted(ratings, reverse=True)


def test_player_name_lookup(service):
    result = service.search_players(name="Neymar")
    assert any("Neymar" in player["name"] for player in result["players"])


def test_player_filters_compose(service):
    result = service.search_players(nationality="Brazil", position="ST", min_overall=70)
    assert all(p["nationality"] == "Brazil" and p["position"] == "ST" and p["overall"] >= 70
               for p in result["players"])


def test_club_player_lookup(service):
    result = service.search_players(club="FC Barcelona")
    assert result["count"] > 0
    assert all("fc barcelona" in player["club"].lower() for player in result["players"])


def test_team_competitions_crosses_match_files(service):
    result = service.team_competitions("Palmeiras")
    names = {item["competition"] for item in result["competitions"]}
    assert "Brasileirão Série A" in names
    assert len(names) >= 2


def test_average_goals(service):
    result = service.competition_statistics("Brasileirão", 2023)
    assert result["matches"] > 0
    assert result["goals_per_match"] > 0
    assert result["home_wins"] + result["away_wins"] + result["draws"] == result["matches"]


def test_biggest_wins_are_sorted(service):
    result = service.biggest_wins(limit=20)
    margins = [match["margin"] for match in result["matches"]]
    assert margins == sorted(margins, reverse=True)


def test_date_range(service):
    result = service.search_matches(team="Flamengo", start_date="2023-09-01", end_date="2023-09-30")
    assert result["count"] > 0
    assert all("2023-09-01" <= m["date"] <= "2023-09-30" for m in result["matches"])


def test_match_limit_reports_total(service):
    result = service.search_matches(team="Flamengo", limit=3)
    assert result["count"] > 3
    assert result["returned"] == len(result["matches"]) == 3


def test_dataset_summary(service):
    result = service.dataset_summary()
    assert len(result["datasets"]) == 6
    assert result["total_matches"] > 20_000
    assert result["total_players"] == 18_207


def test_empty_query_is_well_formed(service):
    result = service.search_players(name="definitely-not-a-real-player")
    assert result == {"count": 0, "returned": 0, "players": []}


@pytest.mark.parametrize("kwargs", [
    {"venue": "neutral"},
])
def test_invalid_team_statistics_input(service, kwargs):
    with pytest.raises(ValueError, match="venue"):
        service.team_statistics("Flamengo", **kwargs)


def test_invalid_date_range(service):
    with pytest.raises(ValueError, match="start_date"):
        service.search_matches(start_date="2023-12-31", end_date="2023-01-01")


def test_simple_queries_meet_performance_target(service):
    started = time.perf_counter()
    for _ in range(20):
        service.search_matches(team="Flamengo", limit=20)
    assert (time.perf_counter() - started) / 20 < 2.0


def test_aggregate_queries_meet_performance_target(service):
    started = time.perf_counter()
    service.standings(2019, "Brasileirão")
    assert time.perf_counter() - started < 5.0
