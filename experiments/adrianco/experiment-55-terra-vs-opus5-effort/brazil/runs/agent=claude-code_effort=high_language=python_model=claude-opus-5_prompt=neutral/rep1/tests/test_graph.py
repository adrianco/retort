"""Tests for knowledge-graph construction: deduplication, merging and indexes.

Context
-------
Deduplication is the single most consequential piece of logic in the project:
the same Série A fixture appears in up to three of the provided files, so
getting it wrong silently doubles every aggregate.  These tests pin the
invariants that prove it is right -- exact season fixture counts, no repeated
ordered pairs inside a league season, and merged records carrying columns from
each contributing file.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

import pytest


def test_graph_builds_quickly(graph):
    assert graph.report.build_seconds < 5.0
    assert graph.report.rows_read["fifa_data.csv"] == 18207


def test_duplicate_rows_are_merged(graph):
    source_rows = sum(count for name, count in graph.report.rows_read.items()
                      if name != "fifa_data.csv")
    assert source_rows == 23954
    assert len(graph.matches) < source_rows
    assert (len(graph.matches) + graph.report.merged_rows
            + graph.report.discarded_rows) == source_rows


def test_self_matches_are_discarded(graph):
    """The Copa do Brasil file lists "Bragantino - PA" against itself twice."""
    assert graph.report.discarded_rows == 2
    assert all(m.home_slug != m.away_slug for m in graph.matches)


#: Fixtures per Série A season after merging.  20 clubs playing a double round
#: robin is 380; 2003-2004 had 24 clubs and 2005 had 22.  2015 carries one
#: extra fixture -- BR-Football has a Brasília FC v CA Taguatinga row wrongly
#: labelled Série A -- which `standings` reports and excludes rather than
#: silently deleting from the source data.
SERIE_A_FIXTURES = {
    2003: 552, 2004: 552, 2005: 462, 2015: 381,
    **{year: 380 for year in range(2006, 2023) if year != 2015},
}


@pytest.mark.parametrize("season,expected", sorted(SERIE_A_FIXTURES.items()))
def test_serie_a_season_fixture_counts(graph, season, expected):
    fixtures = graph.matches_by_comp_season[("serie-a", season)]
    assert len(fixtures) == expected


def test_the_2015_outlier_is_excluded_from_the_table_not_the_data(graph):
    from brazilian_soccer.queries import standings

    table = standings(2015, "serie-a", graph=graph)
    assert len(table["table"]) == 20
    assert table["champion"] == "Corinthians"
    assert {row["team"] for row in table["excluded"]} == {"Brasília FC",
                                                          "Ca Taguatinga"}


def test_ordered_pairs_repeat_only_for_genuine_replays(graph):
    """A double round robin pairs each ordered couple exactly once.

    The single exception in the data is Botafogo hosting Flamengo twice in
    2009, which the source file records as two different rounds -- a real
    fixture, not a duplicate row, so the round numbers must differ.
    """
    for season in range(2006, 2023):
        fixtures = graph.matches_by_comp_season[("serie-a", season)]
        by_pair = Counter((m.home_slug, m.away_slug) for m in fixtures)
        repeated = [pair for pair, count in by_pair.items() if count > 1]
        for pair in repeated:
            rounds = [m.round for m in fixtures
                      if (m.home_slug, m.away_slug) == pair]
            assert len(set(rounds)) == len(rounds), (season, pair)
        assert len(repeated) <= 1, season


def test_merged_matches_combine_columns_from_several_files(graph):
    """Round from the Brasileirão file, stadium from the historical file,
    shot statistics from the BR-Football file -- all on one fixture."""
    merged = [m for m in graph.matches_by_comp_season[("serie-a", 2019)]
              if len(m.sources) == 3]
    assert merged
    sample = merged[0]
    assert sample.round is not None
    assert sample.venue is not None
    assert sample.stats


def test_replays_within_one_file_are_not_merged(graph):
    """Botafogo hosted Flamengo twice in the 2009 season (rounds 12 and 31)."""
    fixtures = [m for m in graph.matches_by_comp_season[("serie-a", 2009)]
                if m.home_slug == "botafogo-rj" and m.away_slug == "flamengo"]
    assert len(fixtures) == 2
    assert {m.round for m in fixtures} == {"12", "31"}


def test_indexes_agree_with_the_match_list(graph):
    sample = graph.matches_by_team["flamengo"]
    assert len(sample) == sum(1 for m in graph.matches if m.involves("flamengo"))
    pair = graph.matches_between("flamengo", "fluminense")
    assert all(m.involves("flamengo") and m.involves("fluminense") for m in pair)
    assert len(graph.matches_by_competition["libertadores"]) == 1255


def test_matches_are_sorted_by_date(graph):
    dates = [m.date or dt.date.min for m in graph.matches]
    assert dates == sorted(dates)


def test_team_resolution_paths(graph):
    exact = graph.resolve_team("Flamengo")
    assert exact.matched and exact.slug == "flamengo"

    alias = graph.resolve_team("Sport Club do Recife")
    assert alias.matched and alias.slug == "sport"

    fuzzy = graph.resolve_team("Corinthans")           # typo
    assert fuzzy.matched and fuzzy.slug == "corinthians"

    partial = graph.resolve_team("Atletico Min")
    assert partial.matched and partial.slug == "atletico-mg"

    missing = graph.resolve_team("Manchester United")
    assert not missing.matched
    assert "No team matching" in missing.message


def test_namesakes(graph):
    assert set(graph.namesakes("botafogo-rj")) >= {"botafogo-pb", "botafogo-sp"}
    # Even Flamengo has a namesake: Flamengo-PI plays in the Copa do Brasil.
    assert graph.namesakes("flamengo") == ("flamengo-pi",)
    assert graph.namesakes("gremio") == ()


def test_player_indexes(graph):
    assert len(graph.players_by_nationality["brazil"]) == 827
    gremio = graph.squad("gremio")
    assert len(gremio) == 20
    assert gremio == sorted(gremio, key=lambda p: (-(p.overall or 0), p.name))


def test_foreign_namesake_clubs_are_separated(graph):
    barcelona = [p for p in graph.players if p.club == "FC Barcelona"]
    assert barcelona and all(p.club_slug != "barcelona-equ" for p in barcelona)
    santos = [p for p in graph.players if p.club == "Santos"]
    assert santos and all(p.club_slug == "santos" for p in santos)


def test_summary_reports_every_file(graph):
    summary = graph.summary()
    assert len(summary["files"]) == 6
    assert summary["players"] == 18207
    assert {c["slug"] for c in summary["competitions"]} == {
        "serie-a", "serie-b", "serie-c", "copa-do-brasil", "libertadores"}


def test_cached_graph_is_shared(data_dir):
    from brazilian_soccer.graph import load_graph

    assert load_graph(data_dir) is load_graph(data_dir)
