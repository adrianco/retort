"""
================================================================================
 BDD tests: data loading & knowledge-graph construction
================================================================================
Context
-------
Covers the "Data Coverage" success criteria: all six CSV files load, the graph
indexes teams/players/competitions, and overlapping source files are reconciled
to a single authoritative source per competition-season (so standings are not
double-counted).
================================================================================
"""

from brazilian_soccer_mcp import data_loader as dl


class TestDatasetLoading:
    def test_all_six_csv_files_are_loadable(self):
        # Given the bundled data directory
        data_dir = dl.default_data_dir()
        # When each dataset is loaded individually
        loaders = {
            "Brasileirao_Matches.csv": dl.load_brasileirao,
            "Brazilian_Cup_Matches.csv": dl.load_copa_do_brasil,
            "Libertadores_Matches.csv": dl.load_libertadores,
            "BR-Football-Dataset.csv": dl.load_br_football,
            "novo_campeonato_brasileiro.csv": dl.load_historical_brasileirao,
        }
        import os
        # Then every match file yields rows...
        for fname, loader in loaders.items():
            rows = loader(os.path.join(data_dir, fname))
            assert len(rows) > 100, f"{fname} produced too few rows"
        # ...and the player file loads too
        players = dl.load_all_players(data_dir)
        assert len(players) > 10000

    def test_matches_carry_competition_and_normalized_keys(self):
        # Given the Brasileirão dataset
        import os
        rows = dl.load_brasileirao(
            os.path.join(dl.default_data_dir(), "Brasileirao_Matches.csv"))
        # When inspecting a row
        m = rows[0]
        # Then it is tagged with a competition and has canonical team keys
        assert m.competition == "Brasileirão Série A"
        assert m.home_key and m.away_key
        assert isinstance(m.home_goal, int) and isinstance(m.away_goal, int)


class TestKnowledgeGraph:
    def test_graph_loads_matches_players_and_competitions(self, graph):
        # Given a fully-loaded graph
        summary = graph.stats_summary()
        # Then it contains a large, plausible corpus
        assert summary["matches"] > 10000
        assert summary["players"] > 10000
        assert summary["teams"] > 100
        assert summary["competitions"] >= 4

    def test_overlapping_seasons_are_not_double_counted(self, graph):
        # Given that several files cover the 2019 Brasileirão
        from brazilian_soccer_mcp.normalization import team_key
        fla = team_key("Flamengo")
        # When counting Flamengo's 2019 Série A matches in the reconciled graph
        n = sum(1 for m in graph.matches
                if m.season == 2019
                and m.competition == "Brasileirão Série A"
                and m.involves(fla))
        # Then it equals exactly one round-robin season (38 games), not 2-3x that
        assert n == 38

    def test_competition_names_are_canonical(self, graph):
        # Given the reconciled graph
        comps = graph.competitions()
        # Then "Serie A" and "Série A" spellings have been merged
        assert "Brasileirão Série A" in comps
        assert "Brasileirão Serie A" not in comps
