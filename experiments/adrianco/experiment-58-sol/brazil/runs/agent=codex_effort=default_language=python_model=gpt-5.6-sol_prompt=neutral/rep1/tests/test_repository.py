from brazilian_soccer_mcp.repository import MATCH_FILES, PLAYER_FILE


def test_all_six_datasets_are_loaded(repository):
    counts = repository.dataset_counts
    assert set(counts) == {*MATCH_FILES, PLAYER_FILE}
    assert all(count > 0 for count in counts.values())


def test_every_match_source_is_queryable(repository):
    assert {m.source for m in repository.matches} == set(MATCH_FILES)


def test_player_catalog_is_loaded(repository):
    assert len(repository.players) == 18_207
    assert any(player.name == "Neymar Jr" for player in repository.players)


def test_team_index_understands_state_suffix(repository):
    plain = repository.matches_for_team("Flamengo")
    suffixed = repository.matches_for_team("Flamengo-RJ")
    assert plain
    assert plain == suffixed

