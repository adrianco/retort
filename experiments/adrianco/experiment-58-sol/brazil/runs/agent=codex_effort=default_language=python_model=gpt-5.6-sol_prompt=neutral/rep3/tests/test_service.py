from __future__ import annotations

from time import perf_counter


def test_given_two_teams_when_searching_then_every_match_has_score_and_competition(service):
    result = service.search_matches(team="Flamengo", opponent="Fluminense", limit=200)
    assert result["total"] > 0
    assert all(match["score"] and match["competition"] and match["date"] for match in result["matches"])
    assert all({match["home_team"].split("-")[0], match["away_team"].split("-")[0]} for match in result["matches"])


def test_given_filters_when_searching_then_season_competition_side_and_dates_apply(service):
    result = service.search_matches(team="Palmeiras", season=2023, competition="Serie A", side="home", start_date="2023-05-01", end_date="2023-12-31", limit=200)
    assert result["total"] > 0
    assert all(match["season"] == 2023 and "Palmeiras" in match["home_team"] for match in result["matches"])


def test_given_source_filter_when_searching_then_raw_file_is_directly_queryable(service):
    result = service.search_matches(source="novo_campeonato_brasileiro.csv", deduplicate=False, limit=5)
    assert result["total"] == 6_886
    assert all(match["source"] == "novo_campeonato_brasileiro.csv" for match in result["matches"])


def test_given_corinthians_2022_when_home_stats_requested_then_complete_source_is_used(service):
    stats = service.team_statistics("Corinthians", 2022, "Brasileirão", side="home")
    assert stats["matches"] == 19
    assert stats["wins"] + stats["draws"] + stats["losses"] == 19
    assert stats["goals_for"] - stats["goals_against"] == stats["goal_difference"]


def test_given_flamengo_and_fluminense_when_compared_then_record_balances(service):
    result = service.head_to_head("Flamengo-RJ", "Fluminense")
    assert result["meetings"] > 20
    assert result["team1_wins"] + result["team2_wins"] + result["draws"] == result["meetings"]


def test_given_2019_brasileirao_when_standings_calculated_then_flamengo_is_champion(service):
    table = service.standings(2019)
    assert table["matches_used"] == 380
    assert table["standings"][0]["team_key"] == "flamengo"
    assert table["standings"][0]["points"] == 90
    assert all(row["played"] == 38 for row in table["standings"])


def test_given_brazilian_players_when_sorted_then_neymar_is_top(service):
    result = service.search_players(nationality="Brazil", limit=5)
    assert result["total"] > 800
    assert result["players"][0]["name"] == "Neymar Jr"
    assert all(player["nationality"] == "Brazil" for player in result["players"])


def test_given_club_and_position_when_player_search_runs_then_filters_apply(service):
    result = service.search_players(club="Grêmio", position="forward", limit=100)
    assert result["total"] > 0
    assert all(player["club"] == "Grêmio" for player in result["players"])
    assert all(player["position"] in {"ST", "CF", "LF", "RF", "LW", "RW"} for player in result["players"])


def test_given_competition_when_aggregated_then_outcomes_and_goals_balance(service):
    stats = service.competition_statistics("Brasileirão", 2023)
    assert stats["matches"] > 300
    assert stats["home_wins"] + stats["away_wins"] + stats["draws"] == stats["matches"]
    assert stats["goals_per_match"] == round(stats["total_goals"] / stats["matches"], 3)


def test_given_matches_when_biggest_victories_requested_then_margin_is_descending(service):
    result = service.biggest_victories(limit=20)
    margins = [abs(match["home_goals"] - match["away_goals"]) for match in result["matches"]]
    assert margins == sorted(margins, reverse=True)


def test_given_2019_cup_when_finals_requested_then_two_legs_are_inferred(service):
    result = service.competition_finals("Copa do Brasil", 2019)
    assert result["inferred_from_highest_round"] is True
    assert result["total"] == 2
    assert {match["round"] for match in result["matches"]} == {"8"}


def test_given_2023_when_derbies_requested_then_only_known_rivalries_return(service):
    result = service.derby_matches(2023)
    assert result["total"] >= 10
    assert all(match["derby"] for match in result["matches"])


def test_given_two_seasons_when_compared_then_both_aggregates_return(service):
    result = service.compare_seasons(2018, 2019)
    assert [row["season"] for row in result["seasons"]] == [2018, 2019]


def test_given_a_club_when_profile_requested_then_player_and_match_domains_are_joined(service):
    result = service.club_profile("Grêmio", 2019, "Brasileirão", player_limit=5)
    assert result["match_statistics"]["matches"] == 38
    assert result["players"]["total"] > 0
    assert "Brasileirão Série A" in result["competitions"] or "Serie A" in result["competitions"]


def test_given_loaded_data_when_queries_run_then_performance_targets_are_met(service):
    started = perf_counter()
    service.search_matches(team="Flamengo", season=2023)
    simple_elapsed = perf_counter() - started
    started = perf_counter()
    service.standings(2019)
    aggregate_elapsed = perf_counter() - started
    assert simple_elapsed < 2.0
    assert aggregate_elapsed < 5.0

