"""Feature: Data loading and knowledge-graph construction.

Context
-------
Covers the spec's "Data Coverage" criteria -- all six CSV files must be
loadable and queryable -- plus the graph's own contract: cross-file
de-duplication, alias collection and index integrity.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brazilian_soccer.graph import KnowledgeGraph
from brazilian_soccer.loader import (
    DATA_FILES,
    load_br_football,
    load_brasileirao,
    load_copa_do_brasil,
    load_historico,
    load_libertadores,
    load_players,
)
from brazilian_soccer.models import (
    BRASILEIRAO,
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_B,
    SERIE_C,
)

EXPECTED_ROWS = {
    "Brasileirao_Matches.csv": 4180,
    "Brazilian_Cup_Matches.csv": 1337,
    "Libertadores_Matches.csv": 1255,
    "BR-Football-Dataset.csv": 10296,
    "novo_campeonato_brasileiro.csv": 6886,
    "fifa_data.csv": 18207,
}


class TestEveryFileLoads:
    """Scenario: all six provided datasets load."""

    def test_all_files_are_present(self, data_dir: Path) -> None:
        for filename in DATA_FILES.values():
            assert (data_dir / filename).exists(), f"{filename} missing"

    @pytest.mark.parametrize(
        "reader,filename,competitions",
        [
            (load_brasileirao, "Brasileirao_Matches.csv", {BRASILEIRAO}),
            (load_copa_do_brasil, "Brazilian_Cup_Matches.csv", {COPA_DO_BRASIL}),
            (load_libertadores, "Libertadores_Matches.csv", {LIBERTADORES}),
            (load_historico, "novo_campeonato_brasileiro.csv", {BRASILEIRAO}),
            (
                load_br_football,
                "BR-Football-Dataset.csv",
                {BRASILEIRAO, SERIE_B, SERIE_C, COPA_DO_BRASIL},
            ),
        ],
    )
    def test_match_files_produce_normalised_records(
        self, data_dir: Path, reader, filename: str, competitions: set[str]
    ) -> None:
        # Given one of the provided match files
        # When it is read
        matches = list(reader(data_dir / filename))
        # Then every record has canonical keys, a competition and a season
        assert len(matches) > 1000
        assert {m.competition for m in matches} <= competitions
        # And corrupt rows (self-matches, undated+unseasoned) are dropped
        assert all(m.home_key and m.away_key for m in matches)
        assert all(m.home_key != m.away_key for m in matches)
        assert all(m.season is not None for m in matches)
        assert sum(1 for m in matches if m.match_date is not None) > len(matches) * 0.99

    def test_corrupt_source_rows_are_rejected(self, data_dir: Path) -> None:
        # Given the two known bad rows in the provided files
        cup = list(load_copa_do_brasil(data_dir / "Brazilian_Cup_Matches.csv"))
        libertadores = list(load_libertadores(data_dir / "Libertadores_Matches.csv"))
        # Then the "Bragantino - PA vs Bragantino - PA" rows are gone ...
        assert len(cup) == EXPECTED_ROWS["Brazilian_Cup_Matches.csv"] - 2
        # ... and so is the 2022 Libertadores final row with NA date and score
        assert len(libertadores) == EXPECTED_ROWS["Libertadores_Matches.csv"] - 1

    def test_pandemic_season_is_attributed_correctly(self, data_dir: Path) -> None:
        # Given the 2020 Brasileirão, which finished in February 2021
        matches = [
            m
            for m in load_br_football(data_dir / "BR-Football-Dataset.csv")
            if m.competition == BRASILEIRAO
            and m.match_date
            and m.match_date.year == 2021
            and m.match_date.month <= 2
        ]
        # Then those fixtures are labelled season 2020, not 2021
        assert matches
        assert all(m.season == 2020 for m in matches)

    def test_row_counts_match_the_specification(self, data_dir: Path) -> None:
        # Given the row counts documented in TASK.md
        # When the raw files are counted
        import csv

        for filename, expected in EXPECTED_ROWS.items():
            encoding = "utf-8-sig" if filename == "fifa_data.csv" else "utf-8"
            with (data_dir / filename).open(encoding=encoding, newline="") as handle:
                rows = sum(1 for _ in csv.DictReader(handle))
            assert rows == expected, filename

    def test_player_file_loads_with_utf8_names(self, data_dir: Path) -> None:
        # Given the FIFA player file
        players = list(load_players(data_dir / "fifa_data.csv"))
        # Then all 18,207 players load with ratings and nationalities
        assert len(players) == EXPECTED_ROWS["fifa_data.csv"]
        assert all(p.name for p in players)
        assert sum(1 for p in players if p.overall is not None) == len(players)
        # And accented names are preserved rather than mangled
        assert any("é" in p.name or "ã" in p.name or "í" in p.name for p in players)

    def test_extended_statistics_are_captured(self, data_dir: Path) -> None:
        # Given BR-Football-Dataset.csv, the only file with shots/corners
        matches = list(load_br_football(data_dir / "BR-Football-Dataset.csv"))
        with_stats = [m for m in matches if m.stats]
        assert len(with_stats) > 5000
        sample = with_stats[0]
        assert {"home_corners", "away_corners"} <= set(sample.stats)


class TestGraphConstruction:
    """Scenario: the graph indexes everything it loads."""

    def test_graph_summary_is_consistent(self, graph: KnowledgeGraph) -> None:
        summary = graph.summary()
        assert summary["matches"] == len(graph.matches)
        assert summary["players"] == EXPECTED_ROWS["fifa_data.csv"]
        # 3 corrupt rows are rejected before they reach the graph
        assert summary["rows_read"] == sum(EXPECTED_ROWS.values()) - 3
        assert summary["matches"] + summary["duplicate_rows_merged"] == sum(
            count for name, count in EXPECTED_ROWS.items() if name != "fifa_data.csv"
        ) - 3

    def test_every_match_is_indexed_for_both_teams(self, graph: KnowledgeGraph) -> None:
        for index, match in list(enumerate(graph.matches))[::500]:
            assert index in graph.matches_by_team[match.home_key]
            assert index in graph.matches_by_team[match.away_key]
            assert index in graph.matches_by_competition[match.competition]

    def test_matches_are_sorted_by_date(self, graph: KnowledgeGraph) -> None:
        dates = [m.match_date for m in graph.matches if m.match_date]
        assert dates == sorted(dates)

    def test_aliases_are_collected_per_team(self, graph: KnowledgeGraph) -> None:
        # Given a club spelled many ways across the files
        team = graph.teams["atletico-mg"]
        # Then the node records every spelling it absorbed
        assert len(team.match_indexes) > 500
        assert team.region == "MG"

    def test_players_link_to_team_nodes(self, graph: KnowledgeGraph) -> None:
        # Given Brazilian clubs that appear in both the FIFA and match data
        gremio = graph.teams["gremio"]
        # Then the club node carries its FIFA squad
        assert len(gremio.player_indexes) >= 15
        assert all(
            graph.players[i].club_key == "gremio" for i in gremio.player_indexes
        )


class TestDeduplication:
    """Scenario: the same fixture in two files is counted once."""

    def test_duplicate_league_fixture_is_merged(self, tiny_graph: KnowledgeGraph) -> None:
        # Given a league fixture present in two source files
        # When the graph is built
        alpha_beta = [
            m for m in tiny_graph.matches if {m.home_key, m.away_key} == {"alpha", "beta"}
        ]
        # Then only one match survives, tagged with both sources
        assert len(alpha_beta) == 1
        assert alpha_beta[0].sources == {"test", "other"}
        assert tiny_graph.duplicates_merged == 1

    def test_merging_fills_missing_fields(self) -> None:
        # Given a scheduled fixture with no score and the same fixture with one
        from tests.conftest import _match

        skeleton = _match("Alpha-SP", "Beta-RJ", None, None, day=1, source="a")
        detailed = _match("Alpha", "Beta", 3, 1, day=1, source="b", venue="Arena")
        graph = KnowledgeGraph.build([skeleton, detailed])
        # Then the surviving record gains the score and the venue
        assert len(graph.matches) == 1
        merged = graph.matches[0]
        assert (merged.home_goals, merged.away_goals) == (3, 1)
        assert merged.venue == "Arena"

    def test_cup_ties_played_twice_are_kept(self) -> None:
        # Given a two-legged cup tie in the same season
        from tests.conftest import _match

        first = _match(
            "Alpha-SP", "Beta-RJ", 1, 0, day=1, competition=COPA_DO_BRASIL
        )
        second = _match(
            "Alpha-SP", "Beta-RJ", 2, 2, day=8, competition=COPA_DO_BRASIL
        )
        graph = KnowledgeGraph.build([first, second])
        # Then both legs are preserved (cups do not de-duplicate on season)
        assert len(graph.matches) == 2

    @pytest.mark.parametrize("season", [2014, 2016, 2017, 2018, 2019, 2020, 2021, 2022])
    def test_real_dataset_overlap_is_removed(
        self, graph: KnowledgeGraph, season: int
    ) -> None:
        # Given the three overlapping Série A sources
        # When a season covered by all of them is inspected
        season_matches = [
            graph.matches[i]
            for i in graph.matches_by_competition[BRASILEIRAO]
            if graph.matches[i].season == season
        ]
        # Then it holds exactly one double round-robin: 20 teams -> 380 matches
        assert len(season_matches) == 380
        pairs = {(m.home_key, m.away_key) for m in season_matches}
        assert len(pairs) == 380
        assert len({m.home_key for m in season_matches}) == 20

    def test_no_league_fixture_is_ever_duplicated(self, graph: KnowledgeGraph) -> None:
        # Given every league season in the graph
        seen: set[tuple] = set()
        for match in graph.matches:
            if match.competition not in (BRASILEIRAO, SERIE_B, SERIE_C):
                continue
            key = (match.competition, match.season, match.home_key, match.away_key)
            # Then an ordered pair appears at most once per season
            assert key not in seen, key
            seen.add(key)


class TestTeamResolution:
    """Scenario: user-typed names resolve to graph nodes."""

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("Flamengo", "flamengo-rj"),
            ("flamengo-rj", "flamengo-rj"),
            ("Palmeiras-SP", "palmeiras"),
            ("São Paulo", "sao-paulo"),
            ("sao paulo", "sao-paulo"),
            ("Grêmio", "gremio"),
            ("Vasco da Gama", "vasco-gama"),
            ("Athletico Paranaense", "atletico-pr"),
            ("Cruzeiro", "cruzeiro"),
        ],
    )
    def test_common_spellings_resolve(
        self, graph: KnowledgeGraph, query: str, expected: str
    ) -> None:
        team = graph.resolve_team(query)
        assert team is not None and team.key == expected

    def test_ambiguous_prefix_returns_all_candidates(self, graph: KnowledgeGraph) -> None:
        # Given a query that matches several clubs
        teams = graph.resolve_teams("atletico")
        keys = {team.key for team in teams}
        # Then every regional Atlético is offered
        assert {"atletico-mg", "atletico-pr", "atletico-go"} <= keys

    def test_unknown_team_resolves_to_nothing(self, graph: KnowledgeGraph) -> None:
        assert graph.resolve_team("Manchester United Reserves XI") is None

    def test_load_time_is_reasonable(self, graph: KnowledgeGraph) -> None:
        # 42k rows across six files should load in a couple of seconds
        assert graph.load_seconds < 10
