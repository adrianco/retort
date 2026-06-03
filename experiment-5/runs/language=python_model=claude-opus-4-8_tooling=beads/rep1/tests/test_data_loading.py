"""
================================================================================
Feature: Data loading
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
BDD tests covering Success Criteria > Data Coverage: all six CSVs load, are
queryable, and cross-file de-duplication produces correct league sizes.
================================================================================
"""

from data_loader import (load_dataset, SERIE_A, SERIE_B, SERIE_C,
                          COPA_BRASIL, LIBERTADORES)


class TestAllFilesLoad:
    def test_matches_and_players_loaded(self, dataset):
        # Given the six provided CSV files
        # When the dataset is loaded
        # Then a substantial number of matches and players are present
        assert len(dataset.matches) > 15000
        assert len(dataset.players) == 18207

    def test_all_competitions_present(self, dataset):
        # Then every competition from the source files is represented
        comps = {m.competition for m in dataset.matches}
        for c in (SERIE_A, SERIE_B, SERIE_C, COPA_BRASIL, LIBERTADORES):
            assert c in comps


class TestDateNormalization:
    def test_all_dates_iso_or_blank(self, dataset):
        # Given the three different source date formats
        # When loaded
        # Then every populated date is ISO YYYY-MM-DD
        sample = [m for m in dataset.matches if m.date][:5000]
        for m in sample:
            assert len(m.date) == 10 and m.date[4] == "-" and m.date[7] == "-"


class TestDeduplication:
    def test_serie_a_seasons_have_correct_size(self, graph):
        # Given Série A seasons that appear in several source files
        # When de-duplicated by fixture identity
        # Then a 20-team double round-robin yields exactly 380 matches
        for season in (2019, 2020, 2022):
            matches = graph.find_matches(competition=SERIE_A, season=season)
            teams = {m.home_key for m in matches} | {m.away_key for m in matches}
            assert len(matches) == 380
            assert len(teams) == 20

    def test_extended_stats_are_merged_in(self, graph):
        # Given a Série A match that also has corner/shot stats in BR-Football
        # When fixtures are merged across files
        # Then at least some Série A matches carry the extended stats and
        # cite multiple source files
        enriched = [m for m in graph.comp_matches[SERIE_A]
                    if m.home_shots is not None and len(m.sources) > 1]
        assert enriched


class TestEncoding:
    def test_accented_team_names_preserved(self, graph):
        # Given UTF-8 accented club display names
        # Then teams like Grêmio/São Paulo are resolvable
        assert graph.resolve_team("Grêmio") == "gremio"
        assert graph.resolve_team("São Paulo") == "sao paulo"
