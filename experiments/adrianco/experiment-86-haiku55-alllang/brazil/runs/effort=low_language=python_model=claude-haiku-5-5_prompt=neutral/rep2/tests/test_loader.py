"""Scenarios: all six CSV files load, overlapping sources are de-duplicated."""

from datetime import date

from soccer_mcp.loader import Match, _dedupe, _same_match
from soccer_mcp.normalize import parse_team


def _match(day, home, away, hg, ag, comp="brasileirao_a", source="x.csv"):
    return Match(date=day, competition=comp, season=day.year, home=parse_team(home),
                 away=parse_team(away), home_goals=hg, away_goals=ag, source=source)


def test_scenario_all_match_sources_are_loaded(dataset):
    # Given the dataset is loaded from data/kaggle
    # When the matches are grouped by competition
    competitions = {m.competition for m in dataset.matches}
    # Then the Brasileirão series, the cup, Libertadores and the historical years are present
    assert {"brasileirao_a", "brasileirao_b", "brasileirao_c",
            "copa_do_brasil", "libertadores"} <= competitions
    sources = {m.source for m in dataset.matches}
    assert {"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv", "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv"} <= sources


def test_scenario_all_player_records_are_loaded(dataset):
    # Given the FIFA file has 18,207 player rows
    # When it is loaded
    # Then nearly all rows become players (the BOM and blank rows are handled)
    assert len(dataset.players) >= 18_000
    assert dataset.players[0].name


def test_scenario_matches_are_sorted_and_have_valid_scores(dataset):
    # Given the loaded matches
    # When their order and scores are checked
    dates = [m.date for m in dataset.matches]
    # Then they are sorted by date and every score is a non-negative integer
    assert dates == sorted(dates)
    assert all(m.home_goals >= 0 and m.away_goals >= 0 for m in dataset.matches)


def test_scenario_same_game_in_two_sources_is_counted_once():
    # Given the same Brasileirão game in two files, with the club spelled differently
    first = _match(date(2019, 10, 27), "Flamengo-RJ", "Csa-AL", 1, 0, source="a.csv")
    second = _match(date(2019, 10, 27), "Flamengo", "CSA", 1, 0, source="b.csv")
    # When both are de-duplicated
    kept = _dedupe([first, second])
    # Then only the first copy remains
    assert kept == [first]


def test_scenario_game_dated_one_day_apart_in_another_file_is_a_duplicate():
    # Given one game recorded on two adjacent dates by two sources
    first = _match(date(2019, 4, 27), "Flamengo-RJ", "Cruzeiro-MG", 3, 1)
    second = _match(date(2019, 4, 28), "Flamengo", "Cruzeiro", 3, 1)
    # When they are compared
    # Then they are the same game
    assert _same_match(first, second)


def test_scenario_different_games_with_same_score_are_kept():
    # Given two different games with the same score on different weeks
    first = _match(date(2019, 4, 27), "Flamengo", "Cruzeiro", 1, 0)
    second = _match(date(2019, 5, 4), "Flamengo", "Cruzeiro", 1, 0)
    # When they are de-duplicated
    # Then both are kept
    assert len(_dedupe([first, second])) == 2


def test_scenario_real_2019_flamengo_season_has_38_games(dataset):
    # Given the Brasileirão 2019 season (20 clubs, 38 rounds)
    # When Flamengo's 2019 Série A games are counted across all files
    games = [m for m in dataset.matches
             if m.competition == "brasileirao_a" and m.season == 2019
             and "flamengo" in (m.home.base, m.away.base)]
    # Then each game appears once
    assert len(games) == 38
