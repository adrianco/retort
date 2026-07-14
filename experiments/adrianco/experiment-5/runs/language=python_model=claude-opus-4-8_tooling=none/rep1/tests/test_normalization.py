"""
================================================================================
 BDD tests: data normalization (Given / When / Then)
================================================================================
Context
-------
Verifies the team-name, date and number normalization that underpins every
query.  The datasets use state suffixes, accents, full names and several date
formats; these scenarios assert that all variants collapse / parse correctly,
including the tricky ambiguous base names (Atlético-MG vs Atlético-GO).
================================================================================
"""

from datetime import date

from brazilian_soccer_mcp import normalization as norm


class TestTeamNameNormalization:
    def test_state_suffix_is_stripped_from_display_name(self):
        # Given a team name with a state suffix
        raw = "Palmeiras-SP"
        # When it is cleaned
        # Then the suffix is removed
        assert norm.clean_team_name(raw) == "Palmeiras"

    def test_spaced_and_parenthesised_suffixes_are_stripped(self):
        # Given names with various suffix styles
        # When cleaned
        # Then only the club name remains
        assert norm.clean_team_name("América - MG") == "América"
        assert norm.clean_team_name("Nacional (URU)") == "Nacional"
        assert norm.clean_team_name("Barcelona-EQU") == "Barcelona"

    def test_accent_and_suffix_variants_share_one_key(self):
        # Given several spellings of São Paulo
        # When keyed
        # Then they all collapse to the same canonical key
        keys = {norm.team_key(n) for n in
                ["São Paulo", "Sao Paulo", "São Paulo-SP", "Sao Paulo FC"]}
        assert len(keys) == 1

    def test_ambiguous_base_names_stay_distinct_by_state(self):
        # Given clubs that share the base name "Atlético"
        # When keyed
        # Then the state suffix keeps them distinct
        mg = norm.team_key("Atlético-MG")
        go = norm.team_key("Atlético-GO")
        pr = norm.team_key("Athletico-PR")
        assert mg != go != pr and mg != pr

    def test_aliases_unify_full_name_and_state_suffix(self):
        # Given the same club spelled with a suffix and with its full name
        # When keyed
        # Then aliases collapse them to one canonical key
        assert norm.team_key("Atlético-MG") == norm.team_key("Atlético Mineiro")
        assert norm.team_key("EC Bahia") == norm.team_key("Bahia")


class TestDateNormalization:
    def test_parses_iso_brazilian_and_datetime_formats(self):
        # Given dates in the three dataset formats
        # When parsed
        # Then each yields the correct date object
        assert norm.parse_date("2023-09-24") == date(2023, 9, 24)
        assert norm.parse_date("29/03/2003") == date(2003, 3, 29)
        assert norm.parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_invalid_date_returns_none(self):
        assert norm.parse_date("not-a-date") is None
        assert norm.iso_date("") is None


class TestNumberNormalization:
    def test_parses_int_float_and_quoted_scores(self):
        # Given goal values in mixed representations
        # When parsed to int
        # Then they normalize correctly
        assert norm.parse_int("2") == 2
        assert norm.parse_int("1.0") == 1
        assert norm.parse_int('"3"') == 3
        assert norm.parse_int("") is None
