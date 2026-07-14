"""
================================================================================
Context
================================================================================
Test module: test_team_names.py
Project:     Brazilian Soccer MCP Server
Feature:     Team-name normalization across inconsistent dataset conventions.
Style:       BDD Given-When-Then.

Verifies that spelling variants of one club collapse to a single key while
genuinely different clubs that merely share a base name stay distinct.
================================================================================
"""

from team_names import display_team, normalize_team, teams_match


class TestTeamNameNormalization:
    def test_state_suffix_is_ignored_for_unique_clubs(self):
        # Given two spellings of Palmeiras (with and without state suffix)
        # When they are normalized
        # Then they produce the same canonical key
        assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")

    def test_accents_are_folded(self):
        # Given accented and plain spellings of the same club
        # When normalized
        # Then they match
        assert normalize_team("São Paulo") == normalize_team("Sao Paulo")
        assert normalize_team("Grêmio") == normalize_team("Gremio")

    def test_spaced_state_suffix_is_handled(self):
        # Given the Copa-do-Brasil "América - MG" spaced suffix style
        # When normalized
        # Then it matches the dashed "América-MG" style
        assert normalize_team("América - MG") == normalize_team("América-MG")

    def test_parenthetical_country_code_is_stripped(self):
        # Given a Libertadores name with a country code in parentheses
        # When normalized
        # Then the code is removed
        assert normalize_team("Nacional (URU)") == normalize_team("Nacional")

    def test_ambiguous_atletico_clubs_stay_distinct(self):
        # Given the three different Atlético clubs that share a base name
        # When normalized
        # Then each remains a distinct key (state code is retained)
        mg = normalize_team("Atletico-MG")
        go = normalize_team("Atletico-GO")
        pr = normalize_team("Athletico-PR")
        assert len({mg, go, pr}) == 3

    def test_atletico_full_names_match_their_state_form(self):
        # Given the spelled-out and dashed forms of Atlético Mineiro
        # When normalized
        # Then they refer to the same club
        assert teams_match("Atletico Mineiro", "Atletico-MG")
        assert teams_match("Athletico Paranaense", "Athletico-PR")

    def test_display_name_is_human_friendly(self):
        # Given a raw dataset spelling
        # When asked for a display name
        # Then a readable canonical name is returned
        assert display_team("flamengo-rj") == "Flamengo" or "Flamengo" in display_team("flamengo-rj")

    def test_empty_input_is_safe(self):
        assert normalize_team("") == ""
        assert normalize_team(None) == ""
