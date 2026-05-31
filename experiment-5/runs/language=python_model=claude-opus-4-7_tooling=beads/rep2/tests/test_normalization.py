"""Unit tests for the team-name normaliser.

The normaliser sits underneath every cross-dataset match — if it regresses,
half the queries break silently. Keep these checks small and explicit.
"""

from __future__ import annotations

from soccer_mcp.data import normalize_team_name


def test_strips_state_suffix() -> None:
    assert normalize_team_name("Palmeiras-SP") == "palmeiras"
    assert normalize_team_name("Flamengo-RJ") == "flamengo"


def test_strips_accents() -> None:
    assert normalize_team_name("São Paulo") == "sao paulo"
    assert normalize_team_name("Grêmio") == "gremio"
    assert normalize_team_name("Avaí") == "avai"


def test_long_form_maps_to_short() -> None:
    assert normalize_team_name("Sport Club Corinthians Paulista") == "corinthians"
    assert normalize_team_name("Clube de Regatas do Flamengo") == "flamengo"


def test_idempotent() -> None:
    once = normalize_team_name("São Paulo-SP")
    twice = normalize_team_name(once)
    assert once == twice == "sao paulo"


def test_handles_none_and_empty() -> None:
    assert normalize_team_name(None) == ""
    assert normalize_team_name("") == ""
    assert normalize_team_name("   ") == ""
