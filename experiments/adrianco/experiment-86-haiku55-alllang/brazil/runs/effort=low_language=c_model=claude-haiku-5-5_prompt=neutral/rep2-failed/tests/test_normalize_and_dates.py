"""Scenarios for team-name normalization and date parsing."""

import unittest
from datetime import date

from brazil_soccer_mcp.dates import parse_date, parse_date_arg
from brazil_soccer_mcp.normalize import parse_team, parse_team_query, team_matches


class TeamNameNormalization(unittest.TestCase):
    def test_state_suffix_is_split_from_the_name(self):
        """Given "Palmeiras-SP", the team is Palmeiras from SP."""
        self.assertEqual(parse_team("Palmeiras-SP"), parse_team("Palmeiras", "SP"))
        self.assertEqual(parse_team("Palmeiras-SP").base, "palmeiras")
        self.assertEqual(parse_team("Palmeiras-SP").state, "SP")

    def test_suffix_with_spaces_and_parenthetical_text(self):
        """Given a cup name with an "(antigo ...)" note and " - RJ", the club is recognized."""
        team = parse_team("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
        self.assertEqual(team.base, "boavista sport club")
        self.assertEqual(team.state, "RJ")

    def test_bare_state_code_is_recognized(self):
        """Given "Vasco da Gama RJ", it normalizes to Vasco with state RJ."""
        self.assertEqual(parse_team("Vasco da Gama RJ").base, "vasco")

    def test_full_official_names_map_to_short_names(self):
        """Given "Sport Club Corinthians Paulista", the team is Corinthians."""
        self.assertEqual(parse_team("Sport Club Corinthians Paulista").base, "corinthians")

    def test_accents_and_case_are_ignored(self):
        """Given "São Paulo" and "SAO PAULO", both normalize to the same team."""
        self.assertEqual(parse_team("São Paulo").base, parse_team("SAO PAULO").base)

    def test_country_code_suffixes_are_removed(self):
        """Given a Libertadores club like "Nacional (URU)", the country code is dropped."""
        self.assertEqual(parse_team("Nacional (URU)").base, "nacional")

    def test_query_without_state_matches_any_state(self):
        """Given the query "Atletico" and a record for Atletico-MG, the record matches."""
        self.assertTrue(team_matches(parse_team("Atletico-MG"), parse_team_query("Atletico")))

    def test_query_with_state_excludes_other_states(self):
        """Given the query "Atletico-PR", an Atletico-MG record does not match."""
        self.assertFalse(team_matches(parse_team("Atletico-MG"), parse_team_query("Atletico-PR")))

    def test_athletico_paranaense_is_one_team(self):
        """Given Atletico-PR written in two different ways, both forms are the same team."""
        self.assertEqual(parse_team("Athletico-PR").base, parse_team("Atlético Paranaense").base)


class DateParsing(unittest.TestCase):
    def test_iso_datetime(self):
        """Given "2012-05-19 18:30:00", the date is 2012-05-19."""
        self.assertEqual(parse_date("2012-05-19 18:30:00"), date(2012, 5, 19))

    def test_brazilian_day_first_format(self):
        """Given "29/03/2003", the date is 29 March 2003 (not month 29)."""
        self.assertEqual(parse_date("29/03/2003"), date(2003, 3, 29))

    def test_placeholders_return_none(self):
        """Given "NA" or a blank, no date is returned rather than an error."""
        self.assertIsNone(parse_date("NA"))
        self.assertIsNone(parse_date(""))

    def test_caller_supplied_bad_date_raises(self):
        """Given an unrecognized date from a caller, a ValueError explains the accepted formats."""
        with self.assertRaises(ValueError):
            parse_date_arg("next tuesday")


if __name__ == "__main__":
    unittest.main()
