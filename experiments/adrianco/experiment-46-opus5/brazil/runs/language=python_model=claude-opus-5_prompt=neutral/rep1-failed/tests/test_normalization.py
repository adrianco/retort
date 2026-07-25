"""Feature: Normalizing the messy parts of the source data.

The datasets spell the same club, date and competition in several ways; these
scenarios pin down the rules that make them comparable.
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer.normalization import (
    BRASILEIRAO,
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_B,
    lookup_curated,
    normalize_competition,
    parse_date,
    parse_int,
    parse_team_name,
    parse_time,
    slugify,
    strip_accents,
)


class TestTeamNameParsing:
    """Feature: Team name variations are normalized."""

    @pytest.mark.parametrize(
        "raw, slug, state",
        [
            ("Palmeiras-SP", "palmeiras", "SP"),
            ("Flamengo-RJ", "flamengo", "RJ"),
            ("América - MG", "america", "MG"),
            ("Vasco da Gama-RJ", "vasco gama", "RJ"),
            ("Sport Club do Recife", "sport recife", None),
            ("Fortaleza EC", "fortaleza", None),
            ("Nacional (URU)", "nacional", "URU"),
            ("Guaraní-PAR", "guarani", "PAR"),
            ("Athletico Paranaense - PR", "athletico paranaense", "PR"),
            ("Boa", "boa", None),
            ("Sport", "sport", None),
        ],
    )
    def test_state_and_country_suffixes_are_split_off(self, raw, slug, state):
        """
        Given a raw team name from one of the CSV files
        When the name is parsed
        Then the identifying slug and the state/country code are separated
        """
        parsed = parse_team_name(raw)

        assert parsed.slug == slug
        assert parsed.state == state

    def test_accents_are_removed_for_matching_but_utf8_is_preserved(self):
        """
        Given accented Brazilian Portuguese club names
        When they are slugified
        Then accents are folded away while the original text stays intact
        """
        parsed = parse_team_name("Grêmio-RS")

        assert parsed.slug == "gremio"
        assert parsed.raw == "Grêmio-RS"
        assert strip_accents("São Paulo, Avaí, Fortaleza") == "Sao Paulo, Avai, Fortaleza"
        assert slugify("Atlético-MG") == "atletico mg"

    def test_foreign_clubs_carry_their_country(self):
        """
        Given a Libertadores club with a country code
        When the name is parsed
        Then the country is resolved from the code
        """
        assert parse_team_name("Nacional (URU)").country == "Uruguay"
        assert parse_team_name("Barcelona-EQU").country == "Ecuador"
        assert parse_team_name("Santos-SP").country == "Brazil"


class TestCuratedClubs:
    """Feature: Ambiguous club names resolve to the right club."""

    def test_atletico_resolves_by_state(self):
        """
        Given three clubs commonly written as "Atlético"
        When each is looked up with its state
        Then each resolves to a different canonical club
        """
        assert lookup_curated("atletico", "MG").team_id == "atletico-mineiro"
        assert lookup_curated("atletico", "PR").team_id == "athletico-paranaense"
        assert lookup_curated("atletico", "GO").team_id == "atletico-goianiense"

    def test_unambiguous_alias_resolves_without_a_state(self):
        """
        Given a full club name with no state code
        When it is looked up
        Then it still resolves, because only one club uses that name
        """
        assert lookup_curated("atletico paranaense", None).team_id == "athletico-paranaense"
        assert lookup_curated("athletico", None).team_id == "athletico-paranaense"

    def test_bare_name_prefers_the_best_known_club(self):
        """
        Given a bare name shared by a famous and an obscure club
        When it is looked up without a state
        Then the famous club wins
        """
        assert lookup_curated("flamengo", None).team_id == "flamengo"
        assert lookup_curated("flamengo", "PI").team_id == "flamengo-pi"
        assert lookup_curated("botafogo", None).team_id == "botafogo"
        assert lookup_curated("botafogo", "PB").team_id == "botafogo-pb"

    def test_unknown_state_is_not_forced_onto_a_curated_club(self):
        """
        Given a name that matches a curated club but with a different state
        When it is looked up
        Then no curated club is returned and generic rules take over
        """
        assert lookup_curated("atletico", "ES") is None


class TestDateParsing:
    """Feature: Several date formats are understood."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("2023-09-24", date(2023, 9, 24)),
            ("2012-05-19 18:30:00", date(2012, 5, 19)),
            ("29/03/2003", date(2003, 3, 29)),
            ("2019-11-23 17:00", date(2019, 11, 23)),
        ],
    )
    def test_supported_formats(self, raw, expected):
        """
        Given a date in any format used by the datasets
        When it is parsed
        Then the correct calendar date comes back
        """
        assert parse_date(raw) == expected

    @pytest.mark.parametrize("raw", ["", None, "nan", "-", "not a date"])
    def test_unparseable_dates_become_none(self, raw):
        """
        Given a missing or malformed date
        When it is parsed
        Then None is returned instead of an exception
        """
        assert parse_date(raw) is None

    def test_kickoff_time_is_extracted(self):
        assert parse_time("2012-05-19 18:30:00") == "18:30"
        assert parse_time("20:00:00") == "20:00"
        assert parse_time("2012-05-19") is None


class TestIntegerParsing:
    """Feature: Scores survive floats, blanks and placeholders."""

    @pytest.mark.parametrize(
        "raw, expected",
        [("3", 3), (3.0, 3), ("2.0", 2), ("-", None), ("", None), (None, None),
         ("nan", None)],
    )
    def test_parse_int(self, raw, expected):
        assert parse_int(raw) == expected


class TestCompetitionNames:
    """Feature: Competition labels are normalized."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Serie A", BRASILEIRAO),
            ("brasileirão", BRASILEIRAO),
            ("Campeonato Brasileiro", BRASILEIRAO),
            ("Série B", SERIE_B),
            ("copa do brasil", COPA_DO_BRASIL),
            ("Libertadores", LIBERTADORES),
            ("copa libertadores 2019", LIBERTADORES),
        ],
    )
    def test_known_competitions(self, raw, expected):
        """
        Given a competition named by a user or a dataset
        When it is normalized
        Then the canonical competition name is returned
        """
        assert normalize_competition(raw) == expected

    def test_unknown_competition_returns_none(self):
        assert normalize_competition("Premier League") is None
        assert normalize_competition("") is None
