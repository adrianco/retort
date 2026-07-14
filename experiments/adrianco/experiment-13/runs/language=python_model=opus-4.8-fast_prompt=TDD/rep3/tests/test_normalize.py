"""Tests for the normalize module: team name and date normalization."""
from brazilian_soccer import normalize as nz


class TestStripAccents:
    def test_removes_common_accents(self):
        assert nz.strip_accents("São Paulo") == "Sao Paulo"
        assert nz.strip_accents("Grêmio") == "Gremio"
        assert nz.strip_accents("Avaí") == "Avai"
        assert nz.strip_accents("Atlético") == "Atletico"

    def test_leaves_plain_text_unchanged(self):
        assert nz.strip_accents("Flamengo") == "Flamengo"


class TestNormalizeTeamName:
    def test_strips_dash_state_suffix(self):
        assert nz.normalize_team_name("Palmeiras-SP") == "Palmeiras"
        assert nz.normalize_team_name("Flamengo-RJ") == "Flamengo"

    def test_strips_spaced_state_suffix(self):
        assert nz.normalize_team_name("América - MG") == "América"

    def test_strips_country_parenthetical(self):
        assert nz.normalize_team_name("Nacional (URU)") == "Nacional"
        assert nz.normalize_team_name("Barcelona-EQU") == "Barcelona"

    def test_collapses_whitespace_and_trims(self):
        assert nz.normalize_team_name("  Santos   FC ") == "Santos FC"

    def test_keeps_full_names(self):
        assert nz.normalize_team_name("Sport Club Corinthians Paulista") == \
            "Sport Club Corinthians Paulista"


class TestTeamKey:
    def test_key_is_lowercase_accentless_tokenized(self):
        assert nz.team_key("São Paulo") == "sao paulo"
        assert nz.team_key("Sport Club Corinthians Paulista") == \
            "sport club corinthians paulista"

    def test_key_retains_state_suffix_for_disambiguation(self):
        # Atlético-MG and Atlético-PR are different clubs and must not collide.
        assert nz.team_key("Atletico-MG") == "atletico mg"
        assert nz.team_key("Atletico-MG") != nz.team_key("Atletico-PR")

    def test_accent_normalization_is_consistent(self):
        assert nz.team_key("Sao Paulo") == nz.team_key("São Paulo")


class TestNamesMatch:
    def test_suffix_insensitive_match(self):
        assert nz.names_match("Flamengo", "Flamengo-RJ")

    def test_substring_match(self):
        assert nz.names_match("Corinthians", "Sport Club Corinthians Paulista")

    def test_non_match(self):
        assert not nz.names_match("Flamengo", "Fluminense")

    def test_accent_insensitive(self):
        assert nz.names_match("Sao Paulo", "São Paulo-SP")

    def test_distinguishes_same_name_different_state(self):
        assert not nz.names_match("Atletico-MG", "Atletico-PR")


class TestKeyMatches:
    def test_query_without_suffix_matches_keyed_team(self):
        assert nz.key_matches("Flamengo", "flamengo rj")

    def test_query_with_suffix_distinguishes(self):
        assert nz.key_matches("Atletico-MG", "atletico mg")
        assert not nz.key_matches("Atletico-MG", "atletico pr")


class TestParseDate:
    def test_iso_date(self):
        assert nz.parse_date("2023-09-24") == "2023-09-24"

    def test_iso_datetime(self):
        assert nz.parse_date("2012-05-19 18:30:00") == "2012-05-19"

    def test_brazilian_format(self):
        assert nz.parse_date("29/03/2003") == "2003-03-29"

    def test_empty_or_none(self):
        assert nz.parse_date("") is None
        assert nz.parse_date(None) is None

    def test_year_extraction(self):
        assert nz.year_of("2012-05-19 18:30:00") == 2012
        assert nz.year_of("29/03/2003") == 2003
        assert nz.year_of(None) is None
