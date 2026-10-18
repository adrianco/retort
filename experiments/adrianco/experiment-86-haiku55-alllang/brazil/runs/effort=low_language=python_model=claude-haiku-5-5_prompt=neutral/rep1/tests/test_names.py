# Context: Scenarios for team and competition name normalization. Covers the spelling variants the
# spec calls out (state suffixes, full club names, accents, parenthetical notes).

import pytest

from brazilian_soccer_mcp.names import parse_team, resolve_competition


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Palmeiras-SP", ("palmeiras", "SP")),
        ("Palmeiras", ("palmeiras", None)),
        ("América - MG", ("america", "MG")),
        ("Sport Club Corinthians Paulista", ("corinthians", None)),
        ("São Paulo FC", ("sao paulo", None)),
        ("Grêmio", ("gremio", None)),
        ("Vasco (RJ)", ("vasco", "RJ")),
        ("Vasco Da Gama RJ", ("vasco", "RJ")),
        ("Athletico-PR", ("athletico", "PR")),
        ("Atletico-PR", ("athletico", "PR")),
        ("Nacional (URU)", ("nacional", None)),
    ],
)
def test_given_a_raw_team_name_when_parsed_then_key_and_state_are_normalised(raw, expected):
    # Given a raw team name from one of the datasets
    # When it is parsed
    result = parse_team(raw)
    # Then the key is accent-free and lowercase, and the state is separated out
    assert result == expected


def test_given_same_club_spelled_two_ways_when_parsed_then_keys_match():
    # Given the same club written with and without a state suffix
    # When both are parsed
    # Then they share a key so matching treats them as one club
    assert parse_team("Palmeiras-SP")[0] == parse_team("Palmeiras")[0]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("serie a", "Brasileirão Série A"),
        ("Brasileirao", "Brasileirão Série A"),
        ("Série B", "Brasileirão Série B"),
        ("copa do brasil", "Copa do Brasil"),
        ("Libertadores", "Copa Libertadores"),
    ],
)
def test_given_a_competition_alias_when_resolved_then_canonical_label_is_returned(query, expected):
    # Given a free-text competition name
    # When it is resolved
    # Then the canonical dataset label is returned
    assert resolve_competition(query) == expected
