from datetime import date

import pytest

from brazilian_soccer_mcp.normalize import normalize_team, parse_date, team_matches


@pytest.mark.parametrize(("raw", "expected"), [
    ("Palmeiras-SP", "palmeiras"),
    ("Flamengo - RJ", "flamengo"),
    ("São Paulo FC", "sao paulo"),
    ("Grêmio", "gremio"),
    ("Sport Club Corinthians Paulista", "corinthians"),
    ("Atlético-MG", "atletico mineiro"),
])
def test_team_name_variations_are_normalized(raw, expected):
    assert normalize_team(raw) == expected


@pytest.mark.parametrize("raw", ["2023-09-24", "2023-09-24 20:30:00", "24/09/2023", "24-09-2023"])
def test_supported_dates(raw):
    assert parse_date(raw) == date(2023, 9, 24)


def test_accent_insensitive_matching():
    assert team_matches("São Paulo", "Sao Paulo")

