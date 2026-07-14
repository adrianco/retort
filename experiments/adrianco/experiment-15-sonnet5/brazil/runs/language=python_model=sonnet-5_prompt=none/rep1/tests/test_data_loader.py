import pytest

from soccer_mcp.data_loader import load_all


@pytest.fixture(scope="module")
def data():
    return load_all()


def test_all_datasets_load_with_matches(data):
    # After deduping matches that appear in more than one overlapping source
    # dataset (see _dedupe_overlapping_sources), the total is well under the
    # raw sum of all five files' row counts (~23.8k) but still substantial.
    assert 15000 < len(data.matches) < 20000


def test_all_five_match_sources_present(data):
    sources = {m.source for m in data.matches}
    assert sources == {
        "brasileirao",
        "copa_do_brasil",
        "libertadores",
        "br_football_dataset",
        "historical_brasileirao",
    }


def test_players_loaded(data):
    assert len(data.players) > 18000


def test_player_fields_parsed(data):
    messi = next(p for p in data.players if p.name == "L. Messi")
    assert messi.nationality == "Argentina"
    assert messi.overall == 94
    assert messi.jersey_number == 10


def test_brazilian_players_present(data):
    brazilians = [p for p in data.players if p.nationality == "Brazil"]
    assert len(brazilians) > 500


def test_matches_have_parsed_dates(data):
    dated = [m for m in data.matches if m.match_date is not None]
    assert len(dated) == len(data.matches)


def test_goals_are_non_negative_ints(data):
    for m in data.matches[:2000]:
        assert isinstance(m.home_goal, int) and m.home_goal >= 0
        assert isinstance(m.away_goal, int) and m.away_goal >= 0


def test_utf8_names_preserved(data):
    # Gremio should appear with its accented form intact in raw data even
    # though normalization strips accents for matching.
    assert any("Grêmio" in m.home_team_raw or "Grêmio" in m.away_team_raw for m in data.matches)
