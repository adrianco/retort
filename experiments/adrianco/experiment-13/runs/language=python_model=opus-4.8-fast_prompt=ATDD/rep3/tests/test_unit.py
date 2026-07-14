"""
Unit tests for the internal building blocks (team-name normalization and the
data repository). These drive the finer-grained design underneath the
acceptance suite; they are allowed to touch internals directly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from team_names import normalize_team  # noqa: E402


def test_normalize_strips_state_suffix():
    assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")
    assert normalize_team("Flamengo-RJ") == normalize_team("Flamengo")


def test_normalize_strips_accents():
    assert normalize_team("Grêmio") == normalize_team("Gremio")
    assert normalize_team("São Paulo") == normalize_team("Sao Paulo")


def test_normalize_handles_parenthetical_country_code():
    assert normalize_team("Nacional (URU)") == normalize_team("Nacional")


def test_normalize_is_case_insensitive():
    assert normalize_team("SANTOS") == normalize_team("santos")


def test_normalize_known_full_name_alias():
    assert normalize_team("Sport Club Corinthians Paulista") == normalize_team(
        "Corinthians"
    )


def test_repository_loads_all_match_sources():
    from soccer_data import SoccerRepository

    repo = SoccerRepository.default()
    competitions = set(repo.matches["competition"].unique())
    assert "Brasileirão" in competitions
    assert "Copa do Brasil" in competitions
    assert "Copa Libertadores" in competitions
    # Players loaded too.
    assert len(repo.players) > 10000


def test_repository_deduplicates_overlapping_brasileirao_2019():
    """The 2019 Serie A appears in several source files; after de-duplication a
    20-team double round-robin has 380 matches."""
    from soccer_data import SoccerRepository

    repo = SoccerRepository.default()
    season_2019 = repo.matches[
        (repo.matches["competition"] == "Brasileirão")
        & (repo.matches["season"] == 2019)
    ]
    assert len(season_2019) == 380
