"""Unit tests for :mod:`soccer_mcp.normalizer`.

These cover the team-name normalization edge cases the BDD scenarios rely on
implicitly: state-suffix collisions across clubs, alias maps for long forms,
and substring matching for short query strings.
"""
from __future__ import annotations

import pytest

from soccer_mcp.normalizer import matches_team, normalize_team, unique_teams


@pytest.mark.parametrize("raw, expected", [
    ("Palmeiras", "palmeiras"),
    ("Palmeiras-SP", "palmeiras-sp"),
    ("SE Palmeiras", "palmeiras"),
    ("Sport Club Corinthians Paulista", "corinthians"),
    ("Atletico-MG", "atletico-mg"),
    ("Atletico-PR", "atletico-pr"),
    ("Athlético-PR", "athletico-pr"),
    ("Nacional (URU)", "nacional"),
    ("Sao Paulo", "sao paulo"),
    ("Sao Paulo Futebol Clube", "sao paulo"),
    ("", ""),
    (None, ""),
])
def test_normalize_team(raw, expected):
    assert normalize_team(raw) == expected


def test_atletico_mg_and_pr_are_distinct():
    assert not matches_team("Atletico-MG", "Atletico-PR")


def test_state_suffix_does_not_block_bare_query():
    assert matches_team("Palmeiras-SP", "Palmeiras")
    assert matches_team("Flamengo-RJ", "Flamengo")


def test_long_form_alias_matches_short():
    assert matches_team("Sport Club Corinthians Paulista", "Corinthians")


def test_short_stub_does_not_match_arbitrarily():
    # "fla" is too short to be a confident substring match
    assert not matches_team("Flamengo", "fla")


def test_unique_teams_drops_blanks_and_dedupes():
    names = ["Flamengo", "Flamengo-RJ", "", None, "Palmeiras-SP", "Palmeiras"]
    out = unique_teams(names)
    assert "" not in out
    # both "flamengo" and "flamengo-rj" are kept as distinct canonical keys
    assert "flamengo" in out
    assert "flamengo-rj" in out
