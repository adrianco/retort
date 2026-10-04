"""Feature: Team queries, competition queries and statistical analysis."""

import pytest

from brazilian_soccer import QueryError


def test_team_statistics_for_a_season(db):
    # Given the match data is loaded
    # When I request statistics for "Palmeiras" in season "2023"
    stats = db.team_stats("Palmeiras", season=2023)
    # Then I should receive wins, losses, draws, and goals
    assert stats["matches"] == stats["wins"] + stats["draws"] + stats["losses"] > 0
    assert stats["goals_for"] > 0 and stats["goals_against"] > 0
    assert sum(r["matches"] for r in stats["by_competition"].values()) == stats["matches"]


def test_home_record_in_a_league_season(db):
    # "What is Corinthians' home record in 2022?"
    stats = db.team_stats("Corinthians", season=2022, competition="Brasileirão", venue="home")
    assert stats["matches"] == 19
    assert (stats["wins"], stats["draws"], stats["losses"]) == (12, 4, 3)
    assert stats["win_rate"] == 63.2


def test_2019_brasileirao_standings_match_the_real_table(db):
    # "Who won the 2019 Brasileirão?"
    rows = db.standings(2019)
    assert len(rows) == 20
    top = rows[0]
    assert (top["team"], top["points"], top["wins"], top["draws"], top["losses"]) == (
        "Flamengo", 90, 28, 6, 4)
    assert [(r["team"], r["points"]) for r in rows[1:3]] == [("Santos", 74), ("Palmeiras", 74)]
    assert all(r["matches"] == 38 for r in rows)


@pytest.mark.parametrize("season, champion", [
    (2006, "São Paulo"), (2011, "Corinthians"), (2015, "Corinthians"), (2016, "Palmeiras"),
    (2018, "Palmeiras"), (2019, "Flamengo"), (2020, "Flamengo"), (2021, "Atlético Mineiro"),
    (2022, "Palmeiras"),
])
def test_league_champions(db, season, champion):
    assert db.season_summary(season)["champion"] == champion


def test_relegated_teams(db):
    # "Which teams were relegated in 2020?"
    summary = db.season_summary(2020)
    assert set(summary["relegated"]) == {"Vasco da Gama", "Goiás", "Coritiba", "Botafogo"}
    assert summary["complete"]


def test_cup_winner_comes_from_the_final(db):
    summary = db.season_summary(2019, "Copa do Brasil")
    assert summary["champion"] == "Athletico Paranaense"
    assert len(summary["final"]["legs"]) == 2
    assert db.season_summary(2019, "Libertadores")["champion"] == "Flamengo"


def test_cup_level_on_aggregate_does_not_invent_a_winner(db):
    # 2015 final finished 2-2 on aggregate and went to penalties (not in the data)
    summary = db.season_summary(2015, "Copa do Brasil")
    assert summary["champion"] is None
    assert set(summary["final"]["aggregate"].values()) == {2}


def test_missing_final_is_reported_not_guessed(db):
    assert db.season_summary(2021, "Libertadores")["final"] is None


def test_unknown_season_lists_available_ones(db):
    with pytest.raises(QueryError, match="Available seasons"):
        db.standings(1999)


def test_average_goals_and_result_rates(db):
    stats = db.competition_stats("Brasileirão")
    assert 2.3 < stats["goals_per_match"] < 2.8
    assert stats["home_wins"] + stats["draws"] + stats["away_wins"] == stats["matches"]
    assert stats["home_win_rate"] > stats["away_win_rate"]
    assert stats["goals"] == stats["home_goals"] + stats["away_goals"]


def test_top_scoring_team_in_a_season(db):
    # "Which team scored the most goals in Serie A 2019?"
    best = db.rank_teams("goals_for", competition="Serie A", season=2019, limit=1)[0]
    assert (best["team"], best["goals_for"]) == ("Flamengo", 86)


def test_best_home_and_away_records(db):
    home = db.rank_teams("win_rate", venue="home", min_matches=100, limit=5)
    away = db.rank_teams("win_rate", venue="away", min_matches=100, limit=5)
    assert [r["win_rate"] for r in home] == sorted((r["win_rate"] for r in home), reverse=True)
    assert home[0]["win_rate"] > away[0]["win_rate"]
    assert all(r["matches"] >= 100 for r in home + away)
    with pytest.raises(QueryError):
        db.rank_teams("charisma")


def test_compare_two_seasons(db):
    result = db.compare_seasons(2018, 2019)
    assert result["seasons"][2018]["leader"] == "Palmeiras"
    assert result["seasons"][2019]["leader"] == "Flamengo"
    assert result["seasons"][2019]["goals"] > result["seasons"][2018]["goals"]


def test_competitions_a_team_has_played_in(db):
    competitions = db.team_competitions("Palmeiras")["competitions"]
    assert {"Brasileirão", "Copa do Brasil", "Copa Libertadores"} <= set(competitions)
    assert 2013 not in competitions["Brasileirão"]["seasons"]  # spent 2013 in Série B
