"""Feature: Match queries."""

from datetime import date

import pytest

from brazilian_soccer import QueryError


def test_find_matches_between_two_teams(db):
    # Given the match data is loaded
    # When I search for matches between "Flamengo" and "Fluminense"
    matches = db.find_matches(team="Flamengo", opponent="Fluminense")
    # Then I should receive a list of matches
    assert len(matches) > 20
    # And each match should have date, scores, and competition
    for m in matches:
        assert {m.home, m.away} == {"Flamengo", "Fluminense"}
        assert m.date and m.competition
        assert m.home_goals >= 0 and m.away_goals >= 0


def test_team_name_variations_return_the_same_matches(db):
    baseline = db.find_matches(team="São Paulo", season=2019)
    for spelling in ("Sao Paulo", "sao paulo-SP", "São Paulo FC", "SAO PAULO - SP"):
        assert db.find_matches(team=spelling, season=2019) == baseline
    assert baseline


def test_matches_are_returned_newest_first(db):
    matches = db.find_matches(team="Flamengo", opponent="Corinthians")
    dates = [m.date for m in matches]
    assert dates == sorted(dates, reverse=True)
    assert dates[0].year == 2023  # "When did Flamengo last play Corinthians?"


def test_filter_by_season_and_competition(db):
    # When I ask what matches Palmeiras played in the 2023 Brasileirão
    matches = db.find_matches(team="Palmeiras", season=2023, competition="Serie A")
    assert 30 <= len(matches) <= 38
    assert all(m.season == 2023 and m.competition == "Brasileirão" for m in matches)


def test_filter_by_venue(db):
    home = db.find_matches(team="Corinthians", season=2022, competition="Brasileirão", venue="home")
    away = db.find_matches(team="Corinthians", season=2022, competition="Brasileirão", venue="away")
    assert len(home) == len(away) == 19
    assert all(m.home == "Corinthians" for m in home)
    assert all(m.away == "Corinthians" for m in away)


def test_filter_by_date_range_accepts_both_date_formats(db):
    matches = db.find_matches(date_from="2019-11-01", date_to="30/11/2019")
    assert matches
    assert all(date(2019, 11, 1) <= m.date <= date(2019, 11, 30) for m in matches)


def test_known_result_from_each_source_file(db):
    # Historical file (DD/MM/YYYY dates): first match of 2003
    [m] = db.find_matches(team="Guarani", opponent="Vasco", date_from="29/03/2003", date_to="29/03/2003")
    assert (m.home, m.home_goals, m.away_goals, m.away) == ("Guarani", 4, 2, "Vasco da Gama")
    assert m.arena == "Brinco de Ouro"
    # Libertadores file
    [m] = db.find_matches(team="Flamengo", competition="Libertadores", stage="final", season=2019)
    assert (m.home_goals, m.away_goals, m.away) == (2, 1, "River Plate")
    # Extended statistics file (only source for 2023)
    [m] = db.find_matches(team="Sao Paulo", opponent="Flamengo", date_from="2023-09-24", date_to="2023-09-24")
    assert m.competition == "Copa do Brasil" and m.stats["total_corners"] == 6


def test_copa_do_brasil_finals_are_found(db):
    finals = db.find_matches(competition="Copa do Brasil", stage="final")
    assert {m.season for m in finals} == set(range(2012, 2024))
    assert {(m.home, m.away) for m in finals if m.season == 2012} == {
        ("Palmeiras", "Coritiba"), ("Coritiba", "Palmeiras")}


def test_head_to_head_totals_are_consistent(db):
    h = db.head_to_head("Palmeiras", "Santos")
    assert h["total"] == h["wins_a"] + h["wins_b"] + h["draws"] == len(h["matches"])
    mirrored = db.head_to_head("Santos-SP", "Palmeiras-SP")
    assert (mirrored["wins_a"], mirrored["wins_b"]) == (h["wins_b"], h["wins_a"])
    assert h["derby"] == "Clássico da Saudade"


def test_derbies_in_a_season(db):
    derbies = db.derbies(season=2023)
    assert derbies
    assert "Fla-Flu" in {name for name, _ in derbies}
    assert all(m.season == 2023 for _, m in derbies)


def test_biggest_wins_are_sorted_by_margin(db):
    wins = db.biggest_wins(limit=10)
    margins = [m.margin for m in wins]
    assert margins == sorted(margins, reverse=True) and margins[0] >= 7
    assert db.biggest_wins(competition="Brasileirão", season=2019, limit=1)[0].margin == 5


@pytest.mark.parametrize("kwargs", [
    {"team": "Nonexistent United"},
    {"competition": "Premier League"},
    {"season": "twenty"},
    {"date_from": "yesterday"},
    {"date_from": "2020-01-02", "date_to": "2020-01-01"},
    {"team": "Flamengo", "venue": "neutral"},
])
def test_invalid_criteria_raise_a_clear_error(db, kwargs):
    with pytest.raises(QueryError):
        db.find_matches(**kwargs)


def test_ambiguous_team_is_reported_for_single_team_queries(db):
    with pytest.raises(QueryError, match="ambiguous"):
        db.team_stats("Atlético")
    with pytest.raises(QueryError):
        db.head_to_head("Flamengo", "Flamengo-RJ")
