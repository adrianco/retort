"""BDD: data loading across all six datasets.

Feature: Load Brazilian soccer datasets
  Scenario: All provided CSV files are loadable and queryable
"""


def test_matches_and_players_loaded(graph):
    # Given the datasets / When loaded / Then both matches and players exist
    assert len(graph.matches) > 20000
    assert len(graph.players) > 18000


def test_all_competitions_present(graph):
    comps = graph.competitions()
    assert "Brasileirão Série A" in comps
    assert "Copa do Brasil" in comps
    assert "Copa Libertadores" in comps


def test_every_match_has_normalized_teams(graph):
    for m in graph.matches[:500]:
        assert m.home_key and m.away_key
        assert m.home and m.away


def test_player_fields_populated(graph):
    messi = graph.search_players(name="Messi", limit=1)
    assert messi
    p = messi[0]
    assert p.name
    assert p.overall is not None
    assert p.nationality
