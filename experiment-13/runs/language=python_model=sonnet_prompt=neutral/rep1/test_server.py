"""Tests for the Brazilian Soccer MCP server data loader and query engine."""

import pytest

from data_loader import DataLoader, normalize_team
from query_engine import QueryEngine


# ------------------------------------------------------------------ #
# Shared fixtures                                                      #
# ------------------------------------------------------------------ #


@pytest.fixture(scope="module")
def engine() -> QueryEngine:
    loader = DataLoader()
    return QueryEngine(loader)


@pytest.fixture(scope="module")
def loader() -> DataLoader:
    return DataLoader()


# ------------------------------------------------------------------ #
# normalize_team                                                       #
# ------------------------------------------------------------------ #


def test_normalize_strips_state_suffix():
    assert normalize_team("Flamengo-RJ") == "flamengo"
    assert normalize_team("Palmeiras-SP") == "palmeiras"
    assert normalize_team("Atletico-MG") == "atletico"


def test_normalize_strips_accents():
    assert normalize_team("Grêmio") == "gremio"
    assert normalize_team("São Paulo") == "sao paulo"
    assert normalize_team("Atlético-MG") == "atletico"


def test_normalize_strips_parentheticals():
    name = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
    assert normalize_team(name) == "boavista sport club"


def test_normalize_handles_none_and_empty():
    assert normalize_team(None) == ""
    assert normalize_team("") == ""
    assert normalize_team("  ") == ""


# ------------------------------------------------------------------ #
# Data loading                                                         #
# ------------------------------------------------------------------ #


def test_all_six_sources_loaded(loader):
    assert len(loader.brasileirao) > 4000, "Brasileirão: expected >4000 rows"
    assert len(loader.copa_brasil) > 1300, "Copa do Brasil: expected >1300 rows"
    assert len(loader.libertadores) > 1200, "Libertadores: expected >1200 rows"
    assert len(loader.extended) > 10000, "Extended: expected >10000 rows"
    assert len(loader.historico) > 6000, "Histórico: expected >6000 rows"
    assert len(loader.fifa) > 18000, "FIFA: expected >18000 rows"


def test_unified_matches_non_empty(loader):
    assert len(loader.all_matches) > 20000


def test_unified_matches_has_required_columns(loader):
    required = {
        "date", "home_team", "away_team", "home_goal", "away_goal",
        "competition", "season", "home_team_norm", "away_team_norm",
        "round_info", "source",
    }
    assert required.issubset(set(loader.all_matches.columns))


def test_all_sources_present_in_unified(loader):
    sources = set(loader.all_matches["source"].unique())
    assert {"brasileirao", "copa_brasil", "libertadores", "extended", "historico"}.issubset(sources)


def test_fifa_key_columns(loader):
    assert "Name" in loader.fifa.columns
    assert "Overall" in loader.fifa.columns
    assert "Nationality" in loader.fifa.columns
    assert "Club" in loader.fifa.columns
    assert "name_norm" in loader.fifa.columns


# ------------------------------------------------------------------ #
# search_matches                                                       #
# ------------------------------------------------------------------ #


def test_search_matches_by_team(engine):
    result = engine.search_matches(team="Flamengo", limit=10)
    assert "Flamengo" in result
    assert "Found" in result


def test_search_matches_by_team_with_suffix(engine):
    # "Flamengo-RJ" and "Flamengo" should find the same records
    result_suffix = engine.search_matches(team="Flamengo-RJ", limit=5)
    result_plain = engine.search_matches(team="Flamengo", limit=5)
    assert "Flamengo" in result_suffix
    assert "Flamengo" in result_plain


def test_search_matches_by_competition_brasileirao(engine):
    result = engine.search_matches(competition="Brasileirão", season=2022, limit=5)
    assert "Brasileirão" in result


def test_search_matches_by_competition_libertadores(engine):
    result = engine.search_matches(competition="Libertadores", limit=5)
    assert "Copa Libertadores" in result


def test_search_matches_no_results(engine):
    result = engine.search_matches(team="NonExistentTeamXYZ123")
    assert "No matches found" in result


def test_search_matches_by_season(engine):
    result = engine.search_matches(season=2019, competition="Brasileirão", limit=5)
    assert "2019" in result


def test_search_matches_by_date_range(engine):
    result = engine.search_matches(date_from="2023-01-01", date_to="2023-12-31", limit=5)
    assert "2023" in result


# ------------------------------------------------------------------ #
# head_to_head                                                         #
# ------------------------------------------------------------------ #


def test_head_to_head_fla_flu(engine):
    result = engine.head_to_head("Flamengo", "Fluminense")
    assert "Head-to-Head" in result
    assert "Flamengo" in result
    assert "Fluminense" in result
    assert "Total matches:" in result
    # There should be matches between them
    assert "Total matches: 0" not in result


def test_head_to_head_no_match(engine):
    result = engine.head_to_head("TeamAlpha999", "TeamBeta888")
    assert "No matches found" in result


def test_head_to_head_shows_wins_draws(engine):
    result = engine.head_to_head("Palmeiras", "Santos")
    assert "wins:" in result
    assert "Draws:" in result


# ------------------------------------------------------------------ #
# get_team_record                                                      #
# ------------------------------------------------------------------ #


def test_get_team_record_palmeiras(engine):
    result = engine.get_team_record("Palmeiras")
    assert "Record for" in result
    assert "Palmeiras" in result
    assert "Wins:" in result
    assert "Goals For:" in result


def test_get_team_record_home_filter(engine):
    result = engine.get_team_record("Corinthians", competition="Brasileirão", season=2022, home_away="home")
    assert "home games only" in result


def test_get_team_record_unknown_team(engine):
    result = engine.get_team_record("NonExistentTeam999")
    assert "No matches found" in result


def test_get_team_record_with_season(engine):
    result = engine.get_team_record("Flamengo", season=2019)
    assert "Flamengo" in result
    assert "Season: 2019" in result


# ------------------------------------------------------------------ #
# get_standings                                                        #
# ------------------------------------------------------------------ #


def test_standings_2019_flamengo_first(engine):
    result = engine.get_standings(season=2019, competition="Brasileirão")
    lines = result.split("\n")
    # First team entry should be Flamengo (won 2019 with 90 pts)
    data_lines = [l for l in lines if "|" in l and "Pos" not in l and "---" not in l]
    assert len(data_lines) > 0
    first_team_line = data_lines[0]
    assert "Flamengo" in first_team_line


def test_standings_has_header(engine):
    result = engine.get_standings(season=2022, competition="Brasileirão")
    assert "Standings" in result
    assert "Pts" in result


def test_standings_historico_2003(engine):
    result = engine.get_standings(season=2003, competition="Brasileirão")
    assert "2003" in result
    assert "Standings" in result
    # There should be multiple teams
    lines = [l for l in result.split("\n") if "|" in l and "Pos" not in l and "---" not in l]
    assert len(lines) >= 10


def test_standings_no_data(engine):
    result = engine.get_standings(season=1800, competition="Brasileirão")
    assert "No match data found" in result


# ------------------------------------------------------------------ #
# search_players                                                       #
# ------------------------------------------------------------------ #


def test_search_players_by_name(engine):
    result = engine.search_players(name="Neymar")
    assert "Neymar" in result
    assert "Overall:" in result


def test_search_players_by_nationality_brazil(engine):
    result = engine.search_players(nationality="Brazil", min_overall=85, limit=10)
    assert "Brazil" in result
    assert "Found" in result


def test_search_players_by_club_fluminense(engine):
    # Flamengo is not in the FIFA 19 dataset; Fluminense is
    result = engine.search_players(club="Fluminense", limit=10)
    assert "Fluminense" in result


def test_search_players_sorted_by_overall(engine):
    result = engine.search_players(nationality="Brazil", limit=5)
    lines = [l for l in result.split("\n") if "Overall:" in l]
    if len(lines) >= 2:
        # Extract overall ratings
        ratings = []
        for line in lines:
            parts = line.split("Overall:")
            if len(parts) > 1:
                rating_str = parts[1].split("|")[0].strip()
                try:
                    ratings.append(int(rating_str))
                except ValueError:
                    pass
        # Should be descending
        assert ratings == sorted(ratings, reverse=True)


def test_search_players_by_position(engine):
    result = engine.search_players(position="GK", limit=5)
    assert "GK" in result


def test_search_players_no_results(engine):
    result = engine.search_players(name="zzznobodyyy999")
    assert "No players found" in result


# ------------------------------------------------------------------ #
# get_statistics                                                       #
# ------------------------------------------------------------------ #


def test_statistics_goals_per_match(engine):
    result = engine.get_statistics("goals_per_match")
    assert "Average Goals per Match" in result
    assert "Home Win Rate" in result
    assert "Total Matches" in result


def test_statistics_goals_per_match_with_filter(engine):
    result = engine.get_statistics("goals_per_match", competition="Brasileirão", season=2022)
    assert "Average Goals per Match" in result


def test_statistics_biggest_wins(engine):
    result = engine.get_statistics("biggest_wins", limit=5)
    assert "Biggest wins" in result
    assert "diff:" in result


def test_statistics_best_home_record(engine):
    result = engine.get_statistics("best_home_record", competition="Brasileirão", limit=5)
    assert "Best Home Records" in result
    assert "Win%" in result


def test_statistics_best_away_record(engine):
    result = engine.get_statistics("best_away_record", limit=5)
    assert "Best Away Records" in result


def test_statistics_top_teams_goals(engine):
    result = engine.get_statistics("top_teams_goals", limit=5)
    assert "Top Goal-Scoring Teams" in result
    assert "Total" in result


def test_statistics_unknown_type(engine):
    result = engine.get_statistics("unknown_stat")
    assert "Unknown stat_type" in result


# ------------------------------------------------------------------ #
# Cross-file / integration queries                                     #
# ------------------------------------------------------------------ #


def test_cross_file_player_and_match(engine):
    # Fluminense appears in both FIFA data and match data
    player_result = engine.search_players(club="Fluminense", limit=3)
    match_result = engine.search_matches(team="Fluminense", limit=3)
    assert "Fluminense" in player_result
    assert "Fluminense" in match_result


def test_libertadores_and_brasileirao_separate(engine):
    lib = engine.search_matches(competition="Libertadores", team="Flamengo", limit=5)
    bra = engine.search_matches(competition="Brasileirão", team="Flamengo", season=2019, limit=5)
    assert "Copa Libertadores" in lib
    assert "Brasileirão" in bra
