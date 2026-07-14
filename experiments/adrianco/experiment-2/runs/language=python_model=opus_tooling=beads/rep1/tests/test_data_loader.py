"""Feature: Data loading and normalization."""
from soccer_mcp.data_loader import normalize_team, team_key, team_matches


def test_normalizes_accents_and_case():
    assert normalize_team("São Paulo") == "sao paulo"
    assert normalize_team("Grêmio") == "gremio"


def test_preserves_state_suffix_for_disambiguation():
    assert normalize_team("Palmeiras-SP") == "palmeiras-sp"
    assert normalize_team("Atlético-MG") == "atletico-mg"


def test_aliases_map_consistently():
    assert normalize_team("Atlético Mineiro") == "atletico-mg"
    assert normalize_team("Athletico Paranaense") == "athletico-pr"


def test_team_key_strips_state_suffix():
    assert team_key("Flamengo-RJ") == "flamengo"
    assert team_key("Palmeiras") == "palmeiras"


def test_team_matches_ignores_suffix():
    assert team_matches("Flamengo", "flamengo-rj")
    assert not team_matches("Flamengo", "fluminense-rj")


def test_datasets_loaded(datasets):
    s = datasets.summary()
    assert s["brasileirao"] > 4000
    assert s["fifa_players"] > 18000
    assert s["unified_matches"] > 20000


def test_unified_matches_have_expected_columns(datasets):
    cols = set(datasets.matches.columns)
    for c in ["competition", "date", "home_team", "away_team",
              "home_key", "away_key", "home_goal", "away_goal", "season"]:
        assert c in cols
