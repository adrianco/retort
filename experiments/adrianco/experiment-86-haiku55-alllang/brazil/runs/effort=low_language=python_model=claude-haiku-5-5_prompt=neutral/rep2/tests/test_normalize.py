"""Scenarios: team names, competition names and dates are normalised consistently."""

from datetime import date

import pytest

from soccer_mcp.normalize import parse_date, parse_team, resolve_competition, team_matches


@pytest.mark.parametrize("raw, base, state", [
    ("Palmeiras-SP", "palmeiras", "SP"),
    ("Palmeiras", "palmeiras", None),
    ("América - MG", "america", "MG"),
    ("Nacional (URU)", "nacional", None),
    ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista", "RJ"),
    ("São Paulo", "sao paulo", None),
    ("Sao Paulo", "sao paulo", None),
    ("Sport Club Corinthians Paulista", "corinthians", None),
    ("Atlético-MG", "atletico", "MG"),
    ("Athletico Paranaense", "atletico", "PR"),
    ("EC Bahia", "bahia", None),
    ("CSA", "csa", None),
])
def test_scenario_team_names_normalise_to_one_base(raw, base, state):
    # Given a team name as written in one of the source files
    # When it is parsed
    team = parse_team(raw)
    # Then the comparable base name and state are recognised
    assert team.base == base
    assert team.state == state


def test_scenario_explicit_state_column_overrides_name_suffix():
    # Given a name with one state suffix and a state column with another value
    # When the team is parsed with the state column value
    team = parse_team("Palmeiras-SP", "RJ")
    # Then the state column is used
    assert team.state == "RJ"


def test_scenario_short_name_matches_suffixed_club():
    # Given a club stored as "Flamengo-RJ"
    club = parse_team("Flamengo-RJ")
    # When the user asks about "Flamengo"
    # Then it matches, and the state narrows only when both sides state one
    assert team_matches(club, "Flamengo")
    assert team_matches(club, "Flamengo-RJ")
    assert not team_matches(club, "Flamengo-SP")


def test_scenario_state_disambiguates_atletico_clubs():
    # Given Atlético-MG and Atlético-PR in the data
    mg, pr = parse_team("Atlético-MG"), parse_team("Athletico-PR")
    # When the user asks for "Atletico-MG"
    # Then only the Minas Gerais club matches
    assert team_matches(mg, "Atletico-MG")
    assert not team_matches(pr, "Atletico-MG")


@pytest.mark.parametrize("text, key", [
    ("Brasileirão Série A", "brasileirao_a"),
    ("brasileirao", "brasileirao_a"),
    ("Serie B", "brasileirao_b"),
    ("copa do brasil", "copa_do_brasil"),
    ("Copa Libertadores", "libertadores"),
])
def test_scenario_competition_names_resolve(text, key):
    # Given a competition name typed by a user
    # When it is resolved
    # Then it maps to the canonical key
    assert resolve_competition(text) == key


def test_scenario_unknown_competition_is_not_resolved():
    # Given a competition the dataset does not contain
    # When it is resolved
    # Then nothing is returned
    assert resolve_competition("Premier League") is None


@pytest.mark.parametrize("text, expected", [
    ("2023-09-24", date(2023, 9, 24)),
    ("2012-05-19 18:30:00", date(2012, 5, 19)),
    ("29/03/2003", date(2003, 3, 29)),
])
def test_scenario_dates_in_all_source_formats_parse(text, expected):
    # Given a date in one of the formats used by the data files
    # When it is parsed
    # Then the calendar date is returned
    assert parse_date(text) == expected


def test_scenario_unrecognised_date_is_rejected():
    # Given a date string in an unsupported format
    # When it is parsed
    # Then a ValueError is raised
    with pytest.raises(ValueError):
        parse_date("March 3rd")
