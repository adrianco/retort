"""BDD scenarios: team name normalization.

Feature: Team name matching
  The datasets spell club names differently (state suffixes, accents, full
  official names); any spelling must resolve to the same club.
"""

from team_normalizer import parse_team, team_key, team_matches


class TestStateSuffixes:
    def test_state_suffix_is_recognised(self):
        # Given a team name with a state suffix
        # When it is parsed
        base, region = parse_team("Palmeiras-SP")
        # Then the base name and state are separated
        assert base == "palmeiras"
        assert region == "sp"

    def test_spaced_suffix_is_recognised(self):
        base, region = parse_team("América - MG")
        assert region == "mg"

    def test_suffixed_and_plain_names_match(self):
        # Given the same club written with and without a state suffix
        # Then they match
        assert team_matches("Flamengo", "Flamengo-RJ")
        assert team_matches("Palmeiras-SP", "Palmeiras")

    def test_different_clubs_do_not_match(self):
        # Given two clubs that share a base name but not a state
        # Then they do not match
        assert not team_matches("America-MG", "América - RN")
        assert not team_matches("Botafogo-SP", "Botafogo-RJ")


class TestAccents:
    def test_accents_are_ignored(self):
        # Given accented and unaccented spellings of São Paulo and Grêmio
        # Then they match
        assert team_matches("Sao Paulo", "São Paulo")
        assert team_matches("Grêmio", "Gremio")
        assert team_matches("Avaí", "Avai-SC")

    def test_cedilla_handled(self):
        assert team_key("Goiás") == team_key("Goias")


class TestAliases:
    def test_full_official_names(self):
        # Given a full official club name
        # Then it matches the short form used in match data
        assert team_matches("Sport Club Corinthians Paulista", "Corinthians-SP")
        assert team_matches("Vasco da Gama", "Vasco")
        assert team_matches("Ceará Sporting Club", "Ceara-CE")

    def test_athletico_rename(self):
        # Given the club renamed from Atlético-PR to Athletico Paranaense
        # Then old and new spellings match
        assert team_matches("Atletico-PR", "Athletico Paranaense")
        assert team_matches("Athletico-PR", "Atlético-PR")

    def test_organisational_tokens_stripped(self):
        # Given names decorated with EC/FC tokens
        # Then they match the bare club name
        assert team_matches("Fortaleza FC", "Fortaleza-CE")
        assert team_matches("EC Juventude", "Juventude-RS")
        assert team_matches("EC Bahia", "Bahia")

    def test_country_suffixes(self):
        base, region = parse_team("Nacional (URU)")
        assert base == "nacional"
        assert region == "uru"
        assert parse_team("Barcelona-EQU") == ("barcelona", "equ")
        # Clubs in different countries that share a name do not match
        assert not team_matches("Nacional (URU)", "Nacional (PAR)")
