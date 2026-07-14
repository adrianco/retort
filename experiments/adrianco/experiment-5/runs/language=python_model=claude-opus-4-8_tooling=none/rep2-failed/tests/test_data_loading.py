"""
Context
=======
Feature: Data loading & coverage
Maps to the "Data Coverage" success criteria in TASK.md - all six CSV files
load and are queryable, with UTF-8 handled correctly.
"""

from __future__ import annotations

from brazilian_soccer_mcp.data_loader import load_dataset


class TestDatasetLoads:
    def test_all_six_files_contribute_data(self, graph):
        # GIVEN the dataset is loaded
        # WHEN we inspect the raw (pre-deduplication) sources
        matches, players = load_dataset()
        sources = {m.source for m in matches}
        # THEN every match CSV is represented
        assert sources == {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        }
        # AND the FIFA player file loaded too
        assert len(players) > 18000

    def test_match_counts_are_reasonable(self):
        # THEN the loaded row counts match the spec's stated sizes (approx)
        matches, _ = load_dataset()
        by_source = {}
        for m in matches:
            by_source[m.source] = by_source.get(m.source, 0) + 1
        assert by_source["Brasileirao_Matches.csv"] == 4180
        assert by_source["Brazilian_Cup_Matches.csv"] == 1337
        assert by_source["Libertadores_Matches.csv"] == 1255
        assert by_source["BR-Football-Dataset.csv"] == 10296
        assert by_source["novo_campeonato_brasileiro.csv"] == 6886

    def test_utf8_accents_preserved(self, graph):
        # THEN accented team names survive loading (encoding handled)
        names = set(graph.canonical_name.values())
        assert any("ê" in n or "ã" in n or "í" in n for n in names)

    def test_deduplication_reduces_overlap(self, graph):
        # The canonical match set is smaller than the raw rows because the
        # overlapping Série A / Copa do Brasil sources are de-duplicated.
        assert graph.raw_match_count > len(graph.matches)


class TestPlayerData:
    def test_brazilian_players_present(self, graph):
        # GIVEN the FIFA data, THEN there is a substantial Brazil contingent
        assert len(graph.players_by_nationality["brazil"]) > 500
