"""BDD specs for brazilian_soccer_mcp.normalize: team-name key normalization,
club-name disambiguation, and flexible date parsing.
"""

import pandas as pd
import pytest

from brazilian_soccer_mcp.normalize import (
    build_known_club_states,
    disambiguate_key,
    normalize_key,
    parse_datetime,
    parse_goal_column,
    strip_accents,
    strip_state_suffix,
)


class TestStripAccents:
    def test_given_a_name_with_portuguese_accents_when_stripped_then_ascii_equivalent_is_returned(self):
        # Given a name containing Portuguese accent marks
        # When accents are stripped
        result = strip_accents("São Paulo Grêmio Avaí")
        # Then the ascii-equivalent letters are returned
        assert result == "Sao Paulo Gremio Avai"


class TestStripStateSuffix:
    def test_given_hyphenated_state_suffix_when_stripped_then_base_name_and_state_are_split(self):
        # Given a team name with a hyphenated state suffix
        # When the suffix is stripped
        base, state = strip_state_suffix("Flamengo-RJ")
        # Then the base name and state code are separated
        assert (base, state) == ("Flamengo", "RJ")

    def test_given_space_separated_state_suffix_when_stripped_then_base_name_and_state_are_split(self):
        # Given a team name with a bare space-separated state suffix (as used by BR-Football-Dataset)
        # When the suffix is stripped
        base, state = strip_state_suffix("Botafogo RJ")
        # Then the base name and state code are separated
        assert (base, state) == ("Botafogo", "RJ")

    def test_given_name_with_no_state_suffix_when_stripped_then_name_is_unchanged(self):
        # Given a team name with no recognizable state suffix
        # When the suffix-stripping is attempted
        base, state = strip_state_suffix("Vasco da Gama")
        # Then the name is returned unchanged and no state is found
        assert (base, state) == ("Vasco da Gama", None)

    def test_given_trailing_word_that_is_not_a_state_code_when_stripped_then_name_is_unchanged(self):
        # Given a name whose last two letters happen to spell something that
        # isn't a real Brazilian state code
        # When the suffix-stripping is attempted
        base, state = strip_state_suffix("4 de Julho EC")
        # Then nothing is stripped, since "EC" isn't a state code
        assert (base, state) == ("4 de Julho EC", None)


class TestNormalizeKey:
    @pytest.mark.parametrize(
        "raw",
        ["Palmeiras-SP", "Palmeiras", "PALMEIRAS", "  palmeiras  ", "Sociedade Esportiva Palmeiras"],
    )
    def test_given_any_spelling_variant_when_normalized_then_same_key_is_produced(self, raw):
        # Given several real spelling variants of Palmeiras seen across the datasets
        # When each is normalized
        # Then they all collapse onto the same key
        assert normalize_key(raw) == "palmeiras"

    def test_given_accented_and_unaccented_spellings_when_normalized_then_same_key_is_produced(self):
        # Given accented ("Grêmio") and unaccented ("Gremio") spellings
        # When normalized
        # Then both produce the same key
        assert normalize_key("Grêmio") == normalize_key("Gremio")

    def test_given_full_club_name_when_normalized_then_short_alias_key_is_produced(self):
        # Given the FIFA-style full legal name for Corinthians
        # When normalized
        # Then it resolves to the same short key used elsewhere in the data
        assert normalize_key("Sport Club Corinthians Paulista") == normalize_key("Corinthians-SP")

    def test_given_none_when_normalized_then_empty_key_is_returned(self):
        # Given a missing team name (None)
        # When normalized
        # Then an empty key is returned rather than raising
        assert normalize_key(None) == ""

    def test_given_nan_when_normalized_then_empty_key_is_returned(self):
        # Given a missing team name (pandas NaN, as seen in real CSV columns)
        # When normalized
        # Then an empty key is returned rather than raising
        assert normalize_key(float("nan")) == ""

    def test_given_athletico_paranaense_spelling_variants_when_normalized_then_same_key_is_produced(self):
        # Given the many real spellings of this club across the provided CSVs
        # ("Athletico" with h, "Atletico" without, with/without "Paranaense",
        # with/without an explicit "-PR" suffix)
        variants = [
            "Athletico-PR",
            "Atletico-PR",
            "Athletico Paranaense",
            "Atletico Paranaense",
            "Athletico Paranaense - PR",
            "Athletico",
        ]
        # When each is normalized
        keys = {normalize_key(v) for v in variants}
        # Then they all collapse onto exactly one key
        assert len(keys) == 1


class TestKnownClubStateDisambiguation:
    def test_given_two_states_sharing_a_generic_club_name_when_disambiguated_then_dominant_state_keeps_bare_key(self):
        # Given a trusted top-flight source where "Atletico" appears mostly
        # for the Minas Gerais club, with a handful for Goiás
        pairs = [("Atletico-MG", "MG")] * 20 + [("Atletico-GO", "GO")] * 3
        known_states = build_known_club_states(pairs)
        # When resolving a new "Atletico-MG" row against those known states
        mg_key = disambiguate_key("Atletico-MG", known_states)
        go_key = disambiguate_key("Atletico-GO", known_states)
        # Then the dominant (MG) club keeps the plain key, and the minority
        # (GO) club is disambiguated into a distinct key
        assert mg_key == "atletico"
        assert go_key == "atletico (go)"
        assert mg_key != go_key

    def test_given_a_minor_club_sharing_a_famous_clubs_name_when_disambiguated_then_keys_stay_distinct(self):
        # Given Flamengo-RJ is the well-known club in trusted top-flight data
        known_states = build_known_club_states([("Flamengo-RJ", "RJ")] * 10)
        # When a same-named but different, obscure lower-league club from a
        # different state (as genuinely exists in the Cup dataset) is resolved
        famous_key = disambiguate_key("Flamengo-RJ", known_states)
        minor_key = disambiguate_key("Flamengo-PI", known_states)
        # Then they resolve to different keys instead of merging
        assert famous_key != minor_key


class TestParseDatetime:
    def test_given_iso_datetime_string_when_parsed_then_timestamp_is_correct(self):
        # Given an ISO-formatted datetime string (used by the match CSVs)
        # When parsed
        result = parse_datetime("2012-05-19 18:30:00")
        # Then the correct timestamp is produced
        assert result == pd.Timestamp("2012-05-19 18:30:00")

    def test_given_brazilian_date_format_when_parsed_then_timestamp_is_correct(self):
        # Given a DD/MM/YYYY date (used by novo_campeonato_brasileiro.csv)
        # When parsed
        result = parse_datetime("29/03/2003")
        # Then it's interpreted day-first, not month-first
        assert result == pd.Timestamp("2003-03-29")

    def test_given_unparseable_text_when_parsed_then_not_a_time_is_returned(self):
        # Given a value that isn't a recognizable date
        # When parsed
        result = parse_datetime("not a date")
        # Then NaT is returned rather than raising
        assert result is pd.NaT

    def test_given_missing_value_when_parsed_then_not_a_time_is_returned(self):
        # Given a missing (NaN) value
        # When parsed
        result = parse_datetime(float("nan"))
        # Then NaT is returned
        assert result is pd.NaT


class TestParseGoalColumn:
    def test_given_placeholder_dash_for_an_unplayed_match_when_parsed_then_value_is_missing(self):
        # Given a goals column containing the Libertadores dataset's "-"
        # placeholder for matches without a recorded score
        series = pd.Series(["2", "-", "0"])
        # When parsed into a nullable integer column
        result = parse_goal_column(series)
        # Then the placeholder becomes missing, not a crash or a zero
        assert result.tolist() == [2, pd.NA, 0]
