"""BDD-style behavior tests for source normalization and coercion."""

from datetime import date

import pytest

from brazilian_soccer_mcp.normalization import (
    display_competition,
    normalize_competition,
    normalize_team,
    parse_date,
    parse_int,
)


@pytest.mark.parametrize(
    ("source_name", "expected"),
    [
        ("Palmeiras-SP", "palmeiras"),
        (" Flamengo - RJ ", "flamengo"),
        ("Sport Club Corinthians Paulista", "corinthians"),
        ("São Paulo FC", "sao paulo"),
        ("Grêmio", "gremio"),
        ("Athletico-PR", "athletico"),
    ],
)
def test_given_team_name_variants_when_normalized_then_one_stable_key(source_name: str, expected: str) -> None:
    assert normalize_team(source_name) == expected


@pytest.mark.parametrize(
    ("source_value", "expected"),
    [
        ("2023-09-24", date(2023, 9, 24)),
        ("2012-05-19 18:30:00", date(2012, 5, 19)),
        ("29/03/2003", date(2003, 3, 29)),
        ("NA", None),
    ],
)
def test_given_dataset_date_formats_when_parsed_then_expected_date(source_value: str, expected: date | None) -> None:
    assert parse_date(source_value) == expected


def test_given_competition_aliases_when_normalized_then_brasileirao_is_consistent() -> None:
    assert normalize_competition("Serie A") == "brasileirao"
    assert normalize_competition("Brasileirão Série A") == "brasileirao"
    assert display_competition("Serie A") == "Brasileirão"


@pytest.mark.parametrize(("source_value", "expected"), [("1", 1), ("1.0", 1), ("NA", None), ("-", None)])
def test_given_nullable_score_cells_when_coerced_then_missing_is_not_zero(source_value: str, expected: int | None) -> None:
    assert parse_int(source_value) == expected

