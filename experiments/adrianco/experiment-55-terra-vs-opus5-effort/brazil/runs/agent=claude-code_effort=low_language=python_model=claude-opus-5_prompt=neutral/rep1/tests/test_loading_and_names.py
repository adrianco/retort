"""
Context
=======
BDD scenarios for the "Data loading" and "Team name handling" features in
tests/features.feature.

These cover the two things everything else depends on: that all six files parse,
and that the same club spelled six ways collapses to one node while genuinely
different clubs that share a base name (Atletico-MG / Athletico-PR /
Atletico-GO) stay apart.  The de-duplication assertions are the strongest
evidence the corpus is joined correctly -- if the merge were wrong, a 20-team
Serie A season would not come out at exactly 380 matches and 38 per club.
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer.loader import (
    DATASETS,
    _cup_stage,
    deduplicate,
    parse_date,
    parse_int,
    parse_time,
)
from brazilian_soccer.models import BRASILEIRAO_A, COPA_DO_BRASIL, LIBERTADORES
from brazilian_soccer.names import DisplayNames, derby_name, normalize_team, split_region

from conftest import make_match


# --------------------------------------------------------------- Data loading

def test_all_six_datasets_load(graph):
    # Given the data directory contains the six provided CSV files
    # When the knowledge graph is built
    counts = graph.source_counts
    # Then every file contributes rows
    assert set(counts) == set(DATASETS) | {"fifa_data.csv"}
    assert all(count > 0 for count in counts.values()), counts
    assert counts["fifa_data.csv"] == 18207
    assert counts["BR-Football-Dataset.csv"] == 10296
    assert counts["novo_campeonato_brasileiro.csv"] == 6886
    # And the graph reports the competitions and seasons it covers
    overview = graph.dataset_overview()
    assert set(overview["competitions"]) == {
        BRASILEIRAO_A, "Brasileirão Série B", "Brasileirão Série C",
        COPA_DO_BRASIL, LIBERTADORES,
    }
    assert overview["seasons"] == [2003, 2023]
    assert overview["brazilian_players"] > 500


# 2021 is the interesting case: the COVID-delayed 2020 championship ran into
# February 2021, and BR-Football-Dataset.csv dates rows without a season column.
@pytest.mark.parametrize("season", [2013, 2014, 2017, 2019, 2020, 2021, 2022])
def test_the_same_fixture_in_several_files_is_counted_once(graph, season):
    # Given a Serie A season present in three of the datasets
    # When the graph is built
    table = graph.standings("Serie A", season)
    # Then that season has exactly 380 matches
    assert table["matches_counted"] == 380
    assert len(table["table"]) == 20
    # And each club has played 38 of them
    assert {row["matches"] for row in table["table"]} == {38}


def test_known_gaps_in_the_source_data_are_visible_not_silently_wrong(graph):
    """Two seasons are imperfect in the *sources*; the graph must not hide it.

    2023: BR-Football-Dataset.csv is the only source for that season and stops
          three matches short of the full 380.
    2015: a single misfiled row (Brasilia FC vs CA Taguatinga, a state
          championship match tagged "Serie A") adds a 381st match.
    Both are reported honestly rather than being patched away.
    """
    assert graph.standings("Serie A", 2023)["matches_counted"] == 377
    assert graph.standings("Serie A", 2015)["matches_counted"] == 381
    strays = [row for row in graph.standings("Serie A", 2015)["table"] if row["matches"] == 1]
    assert {row["team"] for row in strays} == {"Brasília - DF", "CA Taguatinga"}


def test_deduplication_merges_near_dates_but_keeps_distinct_fixtures():
    # The same fixture dated a day apart in two files must merge...
    a = make_match("Alpha", "Beta", 1, 0, month=5, day=10, source="Brasileirao_Matches")
    b = make_match("Alpha", "Beta", 1, 0, month=5, day=11, source="BR-Football-Dataset",
                   stats={"home_shots": 12})
    merged = deduplicate([a, b])
    assert len(merged) == 1
    assert merged[0].source == "Brasileirao_Matches"      # higher priority wins
    assert merged[0].stats["home_shots"] == 12            # lower priority back-fills
    # ...but two meetings months apart are two different fixtures.
    c = make_match("Alpha", "Beta", 1, 0, month=11, day=10, source="BR-Football-Dataset")
    assert len(deduplicate([a, c])) == 2


def test_deduplication_does_not_merge_across_competitions():
    league = make_match("Alpha", "Beta", 1, 0, competition=BRASILEIRAO_A, month=5, day=10)
    cup = make_match("Alpha", "Beta", 1, 0, competition=COPA_DO_BRASIL, month=5, day=10)
    assert len(deduplicate([league, cup])) == 2


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2012-05-19 18:30:00", date(2012, 5, 19)),
        ("2023-09-24", date(2023, 9, 24)),
        ("29/03/2003", date(2003, 3, 29)),
        ("", None),
        (None, None),
        ("not a date", None),
    ],
)
def test_multiple_date_formats_are_handled(raw, expected):
    assert parse_date(raw) == expected


def test_time_and_int_parsing():
    assert parse_time("2012-05-19 18:30:00") == "18:30"
    assert parse_time("20:00:00") == "20:00"
    assert parse_time("") is None
    assert parse_int("3.0") == 3 and parse_int("") is None and parse_int(None) is None


def test_cup_round_numbers_become_stage_names():
    assert _cup_stage(8, 8) == "final"
    assert _cup_stage(7, 8) == "semifinals"
    assert _cup_stage(6, 8) == "quarterfinals"
    assert _cup_stage(1, 8) == "round 1"
    assert _cup_stage(6, 6) == "final"           # shorter seasons still end in a final
    assert _cup_stage(None, 8) is None


# --------------------------------------------------------- Team name handling

@pytest.mark.parametrize(
    "spelling",
    ["São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo Futebol Clube", "SAO PAULO"],
)
def test_spelling_variants_resolve_to_one_club(spelling):
    # Given the datasets spell Sao Paulo several different ways
    # When each spelling is normalised
    # Then they all produce the same canonical key
    assert normalize_team(spelling) == "sao paulo"


def test_the_state_suffix_distinguishes_different_clubs():
    # Given "Atletico-MG", "Athletico-PR" and "Atletico-GO"
    keys = {normalize_team(n) for n in ("Atlético-MG", "Athletico-PR", "Atlético-GO")}
    # Then they produce three different keys
    assert keys == {"atletico mineiro", "atletico paranaense", "atletico goianiense"}
    # and the long spellings agree with the abbreviated ones
    assert normalize_team("Atletico Mineiro") == normalize_team("Atlético-MG")
    assert normalize_team("Athletico Paranaense") == normalize_team("Atletico-PR")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Palmeiras-SP", "palmeiras"),
        ("Palmeiras", "palmeiras"),
        ("Vasco", "vasco da gama"),
        ("Vasco Da Gama RJ", "vasco da gama"),
        ("EC Bahia", "bahia"),
        ("Fortaleza FC", "fortaleza"),
        ("Ceará Sporting Club", "ceara"),
        ("Sport Club do Recife", "sport recife"),
        ("América FC (Minas Gerais)", "america mineiro"),
        ("Botafogo-RJ", "botafogo"),
        ("Botafogo-SP", "botafogo sp"),
        ("", ""),
    ],
)
def test_normalisation_of_real_dataset_spellings(raw, expected):
    assert normalize_team(raw) == expected


def test_region_suffixes_are_extracted():
    assert split_region("Palmeiras-SP") == ("palmeiras", "SP")
    assert split_region("Nacional (URU)") == ("nacional", "URU")
    assert split_region("Barcelona-EQU") == ("barcelona", "EQU")
    assert split_region("Flamengo") == ("flamengo", None)


def test_display_names_prefer_the_accented_short_spelling():
    names = DisplayNames()
    for raw in ("Sao Paulo-SP", "São Paulo", "Sao Paulo Futebol Clube"):
        names.observe(raw)
    assert names.display("sao paulo") == "São Paulo"


def test_utf8_accents_survive_into_answers(graph):
    displayed = {row["team"] for row in graph.list_teams(limit=40)}
    assert "São Paulo" in displayed
    assert "Grêmio" in displayed
    assert "Atlético-MG" in displayed


def test_derbies_are_recognised_in_either_order():
    assert derby_name("Flamengo", "Fluminense") == "Fla-Flu"
    assert derby_name("Fluminense-RJ", "Flamengo-RJ") == "Fla-Flu"
    assert derby_name("Grêmio", "Internacional") == "Grenal"
    assert derby_name("Flamengo", "Palmeiras") is None
