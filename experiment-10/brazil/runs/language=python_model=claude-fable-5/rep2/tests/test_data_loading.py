"""BDD scenarios: dataset loading and de-duplication.

Feature: Data coverage
  All six CSV files must be loadable and queryable, with overlapping Serie A
  sources de-duplicated.
"""

from data_loader import (
    COPA_DO_BRASIL, LIBERTADORES, SERIE_A, SERIE_B, SERIE_C, parse_date,
)


class TestAllSourcesLoad:
    def test_all_six_files_contribute(self, kb):
        # Given the knowledge base is loaded
        # Then every CSV file contributed records
        sources = {m.source for m in kb.matches}
        assert sources == {
            "Brasileirao_Matches.csv",
            "novo_campeonato_brasileiro.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
        }
        assert len(kb.players) == 18207

    def test_all_competitions_present(self, kb):
        comps = {m.competition for m in kb.matches}
        assert {SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES} <= comps

    def test_season_coverage(self, kb):
        seasons = {m.season for m in kb.matches if m.season}
        assert min(seasons) == 2003
        assert max(seasons) >= 2023


class TestDeduplication:
    def test_serie_a_seasons_have_correct_match_counts(self, kb):
        # Given Serie A 2012-2019 appears in three overlapping sources
        # When matches are loaded
        per_season = {}
        for m in kb.matches:
            if m.competition == SERIE_A and m.season:
                per_season[m.season] = per_season.get(m.season, 0) + 1
        # Then each 20-team season has (about) the real 380 fixtures,
        # not double or triple counts
        for season in range(2006, 2023):
            assert 370 <= per_season[season] <= 385, (
                f"season {season}: {per_season[season]} matches"
            )
        # And the 24-team 2003 season has 552
        assert per_season[2003] == 552

    def test_team_plays_each_season_twice_against_opponent(self, kb):
        # Given a league season, two clubs meet exactly twice
        matches = kb.find_matches(
            team="Flamengo", opponent="Fluminense",
            competition="Serie A", season=2019, limit=0,
        )
        assert len(matches) == 2


class TestDateParsing:
    def test_iso_datetime(self):
        assert str(parse_date("2012-05-19 18:30:00")) == "2012-05-19"

    def test_iso_date(self):
        assert str(parse_date("2023-09-24")) == "2023-09-24"

    def test_brazilian_format(self):
        # Given the DD/MM/YYYY format used by the historical dataset
        assert str(parse_date("29/03/2003")) == "2003-03-29"

    def test_garbage_returns_none(self):
        assert parse_date("not a date") is None
        assert parse_date("") is None


class TestEncoding:
    def test_utf8_team_names_preserved(self, kb):
        # Given Brazilian Portuguese club names with accents
        names = {m.home_team for m in kb.matches}
        # Then accented names survive loading intact
        assert any("São Paulo" in n for n in names)
        assert any("Grêmio" in n for n in names)
