"""
Context
=======
Tests for bsoccer.normalize: team-name normalization is the foundation of every
query (matching, dedup, aggregation), so these tests pin down the tricky cases
called out in the spec: state suffixes, accents, full names, country tags, and
the ambiguous "Atletico"/"America" clubs that must NOT collapse together.
"""

from bsoccer.normalize import display_name, normalize_team, strip_accents


def test_strip_accents():
    assert strip_accents("São Paulo") == "Sao Paulo"
    assert strip_accents("Grêmio") == "Gremio"
    assert strip_accents("Avaí") == "Avai"


def test_state_suffix_stripped():
    assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")
    assert normalize_team("Flamengo-RJ") == normalize_team("Flamengo")
    assert normalize_team("Flamengo - RJ") == normalize_team("Flamengo")


def test_accent_insensitive():
    assert normalize_team("São Paulo") == normalize_team("Sao Paulo")
    assert normalize_team("Grêmio") == normalize_team("Gremio")


def test_full_name_collapses_to_short():
    assert normalize_team("Sport Club Corinthians Paulista") == normalize_team("Corinthians")


def test_country_tag_stripped():
    assert normalize_team("Nacional (URU)") == normalize_team("Nacional")
    assert "barcelona" in normalize_team("Barcelona-EQU")


def test_ambiguous_atletico_stay_distinct():
    mg = normalize_team("Atletico-MG")
    go = normalize_team("Atletico-GO")
    pr = normalize_team("Athletico-PR")
    assert mg != go
    assert mg != pr
    assert go != pr
    # Accented spelling normalizes the same as the unaccented one.
    assert normalize_team("Atlético-MG") == mg
    assert normalize_team("Atlético-GO") == go


def test_atletico_aliases():
    assert normalize_team("Atletico-MG") == normalize_team("Atletico Mineiro")
    assert normalize_team("Atletico-PR") == normalize_team("Athletico Paranaense")


def test_vasco_alias():
    assert normalize_team("Vasco") == normalize_team("Vasco da Gama")


def test_empty_input():
    assert normalize_team("") == ""
    assert normalize_team(None) == ""


def test_display_name():
    assert display_name("Palmeiras-SP") == "Palmeiras"
    assert display_name("Nacional (URU)") == "Nacional"
    # Ambiguous clubs keep their suffix for visual distinction.
    assert display_name("Atletico-MG") == "Atletico-MG"
    assert display_name("Atletico-GO") == "Atletico-GO"
