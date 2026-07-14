"""Unit tests for team name normalization."""

from brazilian_soccer_mcp.team_names import loose_key, matches, normalize


class TestNormalize:
    def test_strips_accents(self):
        assert normalize("São Paulo") == "sao paulo"
        assert normalize("Grêmio") == "gremio"

    def test_lowercases(self):
        assert normalize("Flamengo") == "flamengo"

    def test_keeps_state_suffix_distinct(self):
        # Atletico-MG and Atletico-PR should NOT collapse.
        assert normalize("Atletico-MG") != normalize("Atletico-PR")

    def test_handles_none_and_empty(self):
        assert normalize(None) == ""
        assert normalize("") == ""

    def test_drops_parenthetical_country(self):
        assert "uru" not in normalize("Nacional (URU)")


class TestLooseKey:
    def test_palmeiras_variants_match(self):
        assert loose_key("Palmeiras") == loose_key("Palmeiras-SP")

    def test_athletico_collapses_to_atletico(self):
        assert loose_key("Athletico-PR") == loose_key("Atletico-PR")

    def test_drops_clube_filler(self):
        assert loose_key("Fortaleza Esporte Clube") == loose_key("Fortaleza")


class TestMatches:
    def test_short_form_matches_long(self):
        assert matches("Flamengo", "Flamengo-RJ")

    def test_distinct_atleticos(self):
        assert not matches("Atletico-MG", "Atletico-PR")
