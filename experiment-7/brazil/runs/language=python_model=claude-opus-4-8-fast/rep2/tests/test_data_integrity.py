"""
================================================================================
Module: tests.test_data_integrity
--------------------------------------------------------------------------------
Context:
    Cross-cutting BDD scenarios that guard the data-loading contract: all six
    CSVs load, UTF-8 accents survive, every competition is represented, and the
    authoritative-source selection prevents the overlapping files from
    double-counting matches (TASK.md "Success Criteria" / "Data Coverage").

Responsibility:
    Assert dataset coverage and the de-duplication invariant at the graph level.
================================================================================
"""

from brazilian_soccer_mcp import data_loader
from brazilian_soccer_mcp.models import Match, Player


class TestDataCoverage:
    def test_all_six_csv_files_exist(self):
        data_dir = data_loader.find_data_dir()
        for fname in list(data_loader._MATCH_FILES) + [data_loader._PLAYER_FILE]:
            assert (data_dir / fname).exists(), f"missing {fname}"

    def test_matches_and_players_loaded(self, graph):
        assert len(graph.matches) > 10000
        assert len(graph.players) > 15000
        assert all(isinstance(m, Match) for m in graph.matches[:50])
        assert all(isinstance(p, Player) for p in graph.players[:50])

    def test_every_competition_has_matches(self, graph):
        for comp in graph.list_competitions():
            assert graph._by_comp_season  # index built
            count = sum(1 for m in graph.matches if m.competition == comp)
            assert count > 0

    def test_utf8_accents_preserved(self, graph):
        # São Paulo / Grêmio etc. should keep their diacritics in display names.
        names = {m.home_team for m in graph.matches}
        accented = [n for n in names if any(ch in n for ch in "ãáâéêíóôõúç")]
        assert accented, "expected accented Portuguese team names to survive"


class TestDeduplicationInvariant:
    def test_no_inflated_round_robin_seasons(self, graph):
        # A double round-robin with N teams gives each team 2*(N-1) games. If the
        # overlapping source files were double-counting, teams would exceed that.
        # (The Brasileirão had 24 teams in 2003 -> 46 games, 20 teams since 2006
        # -> 38 games; both are legitimate, so we bound by the actual team count.)
        for season in graph.list_seasons("Brasileirão"):
            table = graph.standings("Brasileirão", season)
            max_games = 2 * (len(table) - 1)
            for row in table:
                assert row["played"] <= max_games, (
                    f"{row['team']} played {row['played']} in {season} "
                    f"(max {max_games}) — sources are double-counting"
                )

    def test_single_source_per_competition_season(self, graph):
        # The authoritative-source selection must leave at most one source file
        # backing any (competition, season) bucket.
        from collections import defaultdict

        sources = defaultdict(set)
        for m in graph.matches:
            sources[(m.competition, m.season)].add(m.source)
        for key, srcs in sources.items():
            assert len(srcs) == 1, f"{key} backed by multiple sources: {srcs}"
