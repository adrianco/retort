"""Feature: names, dates and numbers from the four different CSV conventions."""

from datetime import date

import pytest

from brazsoccer_mcp.normalize import display_name, parse_date, parse_int, team_key


class TestTeamNames:
    def test_given_state_suffix_when_normalised_then_suffix_is_removed(self):
        # Given a Brasileirão-style name with a state suffix
        # When the display name is computed
        # Then the suffix is gone
        assert display_name("Palmeiras-SP") == "Palmeiras"

    def test_given_parenthesised_note_when_normalised_then_note_is_removed(self):
        # Given a Copa do Brasil name with an antigo note and state
        raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        # When the display name is computed
        # Then only the club name remains
        assert display_name(raw) == "Boavista Sport Club"

    @pytest.mark.parametrize("raw", ["Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "Palmeiras SP"])
    def test_given_variants_of_one_club_then_they_share_a_key(self, raw):
        # Given the same club written in different styles
        # When keys are computed
        # Then they are all identical
        assert team_key(raw) == "palmeiras"

    def test_given_accents_when_keyed_then_accents_are_ignored(self):
        assert team_key("São Paulo") == team_key("Sao Paulo") == "saopaulo"

    def test_given_full_legal_name_when_keyed_then_alias_applies(self):
        assert team_key("Sport Club Corinthians Paulista") == "corinthians"

    def test_given_leading_ec_prefix_then_it_is_dropped(self):
        assert team_key("EC Bahia") == team_key("Bahia")

    def test_given_same_name_clubs_with_state_then_state_decides(self):
        # Given Atlético-PR, which is called Atletico in one file and has a UF column
        # When keyed with its state
        # Then it resolves to the Athletico club, not Atlético-MG
        assert team_key("Atletico", "PR") == "athletico"
        assert team_key("Atletico", "MG") == "atletico"


class TestDates:
    @pytest.mark.parametrize("raw, expected", [
        ("2023-09-24", date(2023, 9, 24)),
        ("2012-05-19 18:30:00", date(2012, 5, 19)),
        ("29/03/2003", date(2003, 3, 29)),
    ])
    def test_given_known_formats_then_date_is_parsed(self, raw, expected):
        assert parse_date(raw) == expected

    @pytest.mark.parametrize("raw", ["NA", "", "2023/09/24"])
    def test_given_placeholder_or_unknown_format_then_value_error(self, raw):
        with pytest.raises(ValueError):
            parse_date(raw)


class TestNumbers:
    @pytest.mark.parametrize("raw, expected", [("2", 2), ("2.0", 2), (" 3 ", 3)])
    def test_given_numeric_text_then_int_is_returned(self, raw, expected):
        assert parse_int(raw) == expected

    @pytest.mark.parametrize("raw", ["NA", "-", "", None])
    def test_given_placeholder_then_none_is_returned(self, raw):
        assert parse_int(raw) is None
