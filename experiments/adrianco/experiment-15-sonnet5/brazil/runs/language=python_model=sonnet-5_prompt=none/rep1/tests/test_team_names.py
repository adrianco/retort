from soccer_mcp.team_names import normalize_team, teams_match


def test_strips_state_suffix():
    assert normalize_team("Palmeiras-SP")[0] == normalize_team("Palmeiras")[0]
    assert normalize_team("Flamengo-RJ")[0] == normalize_team("Flamengo")[0]


def test_handles_accents():
    assert normalize_team("São Paulo")[0] == normalize_team("Sao Paulo")[0]
    assert normalize_team("Grêmio")[0] == normalize_team("Gremio")[0]


def test_rebrand_alias_athletico_paranaense():
    variants = [
        "Atletico-PR",
        "Athletico-PR",
        "Atletico - PR",
        "Athletico Paranaense - PR",
        "Atletico Paranaense",
    ]
    keys = {normalize_team(v)[0] for v in variants}
    assert keys == {"athletico paranaense"}


def test_does_not_merge_different_states():
    # Atletico-MG and Atletico-PR/Athletico-PR are different clubs.
    assert normalize_team("Atletico-MG")[0] != normalize_team("Atletico-PR")[0]
    # Botafogo-RJ (top flight) must not merge with Botafogo from other states.
    assert normalize_team("Botafogo-RJ")[0] != normalize_team("Botafogo - PB")[0]
    assert normalize_team("Botafogo-RJ")[0] != normalize_team("Botafogo - SP")[0]


def test_does_not_merge_unrelated_teams_with_similar_qualifier():
    # Guarani (Brazil, SP) vs Guarani/Guaraní (Paraguay) must stay distinct.
    assert normalize_team("Guarani")[0] != normalize_team("Guaraní (PAR)")[0]


def test_parenthetical_and_full_name_variants():
    key_short, _ = normalize_team("America-MG")
    key_full, _ = normalize_team("America FC (Minas Gerais)")
    assert key_short == key_full


def test_teams_match_helper():
    assert teams_match("Corinthians-SP", "Corinthians")
    assert not teams_match("Corinthians", "Palmeiras")


def test_display_name_is_readable():
    _, display = normalize_team("flamengo-RJ")
    assert display == "Flamengo"
