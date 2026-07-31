"""
Unit tests for the knowledge graph and cross-source de-duplication.

Context
-------
Serie A 2014-2019 appears in three of the provided CSV files.  If those rows
were counted three times, every league table would be wrong -- so the strongest
assertion available is a structural one: Serie A has been a double round robin
since 2003, therefore each season must contain exactly ``n * (n - 1)`` matches
and each ordered pair of clubs must appear exactly once.  These tests check
that, plus the integrity of the node/edge structure and the index caches.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

import pytest

from brazilian_soccer.graph import deduplicate, load_knowledge_graph
from brazilian_soccer.models import Match

#: Seasons where the merged data reproduces a complete Serie A round robin.
#: 2009 is missing one fixture, 2015 carries one mislabelled row and 2023 is a
#: partial season in the only file that covers it -- see README "Known data gaps".
COMPLETE_SERIE_A_SEASONS = [
    2003, 2004, 2005, 2006, 2007, 2008, 2010, 2011, 2012, 2013, 2014,
    2016, 2017, 2018, 2019, 2020, 2021, 2022,
]


def test_graph_loads_every_dataset(graph):
    assert graph.report.missing_files == []
    assert set(graph.report.rows_by_dataset) == {
        "brasileirao", "copa_do_brasil", "libertadores", "br_football",
        "historical_brasileirao", "fifa_players",
    }


def test_duplicates_were_actually_merged(graph):
    assert graph.report.merged_duplicates > 5000
    multi_source = [m for m in graph.matches if len(m.sources) > 1]
    assert len(multi_source) > 3000
    assert len(graph.matches) < sum(
        count for key, count in graph.report.rows_by_dataset.items() if key != "fifa_players"
    )


@pytest.mark.parametrize("season", COMPLETE_SERIE_A_SEASONS)
def test_serie_a_seasons_are_complete_round_robins(graph, season):
    matches = graph.matches_by_competition_season[("serie-a", season)]
    teams = {m.home_team_id for m in matches} | {m.away_team_id for m in matches}
    assert len(matches) == len(teams) * (len(teams) - 1), (
        f"{season} should be a double round robin between {len(teams)} clubs"
    )


@pytest.mark.parametrize("season", COMPLETE_SERIE_A_SEASONS)
def test_each_serie_a_fixture_appears_once(graph, season):
    matches = graph.matches_by_competition_season[("serie-a", season)]
    pairs = Counter((m.home_team_id, m.away_team_id) for m in matches)
    repeated = {pair: count for pair, count in pairs.items() if count > 1}
    assert repeated == {}


def test_every_club_plays_the_same_number_of_serie_a_matches(graph):
    matches = graph.matches_by_competition_season[("serie-a", 2019)]
    appearances = Counter()
    for match in matches:
        appearances[match.home_team_id] += 1
        appearances[match.away_team_id] += 1
    assert set(appearances.values()) == {38}


def test_merged_match_keeps_every_source(graph):
    merged = next(m for m in graph.matches
                  if m.competition_id == "serie-a" and len(m.sources) == 3)
    assert set(merged.sources) == {"brasileirao", "historical_brasileirao", "br_football"}


def test_merge_prefers_the_authoritative_score_and_keeps_extra_stats():
    """A brasileirao row wins on score; br_football contributes its stats."""

    authoritative = Match(
        id="brasileirao:1", competition_id="serie-a", season=2019,
        date=dt.date(2019, 5, 1), home_team_id="a", away_team_id="b",
        home_goals=2, away_goals=1, sources=["brasileirao"], round="3",
    )
    extended = Match(
        id="br_football:1", competition_id="serie-a", season=2019,
        date=dt.date(2019, 5, 1), home_team_id="a", away_team_id="b",
        home_goals=9, away_goals=9, sources=["br_football"],
        stats={"home_corners": 5.0}, venue="Maracanã",
    )
    merged, duplicates = deduplicate([extended, authoritative])
    assert duplicates == 1
    assert len(merged) == 1
    assert (merged[0].home_goals, merged[0].away_goals) == (2, 1)
    assert merged[0].stats["home_corners"] == 5.0
    assert merged[0].venue == "Maracanã"
    assert set(merged[0].sources) == {"brasileirao", "br_football"}


def test_two_legged_cup_ties_are_not_merged():
    """Legs have opposite home/away order, so they must stay separate."""

    first = Match(id="cup:1", competition_id="copa-do-brasil", season=2019,
                  date=dt.date(2019, 9, 11), home_team_id="a", away_team_id="b",
                  home_goals=1, away_goals=0, sources=["copa_do_brasil"])
    second = Match(id="cup:2", competition_id="copa-do-brasil", season=2019,
                   date=dt.date(2019, 9, 18), home_team_id="b", away_team_id="a",
                   home_goals=1, away_goals=1, sources=["copa_do_brasil"])
    merged, duplicates = deduplicate([first, second])
    assert duplicates == 0
    assert len(merged) == 2


def test_distinct_seasons_are_not_merged():
    same_fixture = [
        Match(id=f"x:{year}", competition_id="serie-a", season=year,
              date=dt.date(year, 8, 1), home_team_id="a", away_team_id="b",
              home_goals=1, away_goals=0, sources=["brasileirao"])
        for year in (2018, 2019, 2020)
    ]
    merged, duplicates = deduplicate(same_fixture)
    assert duplicates == 0
    assert len(merged) == 3


def test_postponed_league_fixture_is_merged_across_sources():
    """Goias-Corinthians 2022: recorded on 15 Oct (no score) and 29 Oct (0-0)."""

    scheduled = Match(id="brasileirao:9", competition_id="serie-a", season=2022,
                      date=dt.date(2022, 10, 15), home_team_id="goias-go",
                      away_team_id="corinthians-sp", sources=["brasileirao"], round="32")
    played = Match(id="br_football:9", competition_id="serie-a", season=2022,
                   date=dt.date(2022, 10, 29), home_team_id="goias-go",
                   away_team_id="corinthians-sp", home_goals=0, away_goals=0,
                   sources=["br_football"])
    merged, duplicates = deduplicate([scheduled, played])
    assert duplicates == 1
    assert merged[0].has_score and merged[0].round == "32"


# ---------------------------------------------------------------------------
# Graph structure
# ---------------------------------------------------------------------------


def test_node_and_edge_types(graph):
    schema = graph.graph_schema()
    assert set(schema["nodes"]) == {"competition", "season", "team", "match",
                                    "player", "venue"}
    assert {"home_team", "away_team", "in_competition", "in_season",
            "of_competition", "competed_in", "plays_for", "played_at"} <= set(schema["edges"])


def test_every_match_edge_points_at_a_real_team(graph):
    sample = graph.matches[:500] + graph.matches[-500:]
    for match in sample:
        for relation in ("home_team", "away_team"):
            targets = graph.neighbors(f"match:{match.id}", relation)
            assert len(targets) == 1
            assert graph.node(targets[0][1]) is not None


def test_in_edges_mirror_out_edges(graph):
    match = graph.matches[0]
    node_id = f"match:{match.id}"
    home_node = f"team:{match.home_team_id}"
    assert (("home_team", home_node)) in graph.neighbors(node_id, direction="out")
    assert (("home_team", node_id)) in graph.neighbors(home_node, direction="in")


def test_team_match_index_matches_graph_traversal(graph):
    team_id = "flamengo-rj"
    from_index = {m.id for m in graph.matches_by_team[team_id]}
    from_graph = {
        node.split(":", 1)[1]
        for relation, node in graph.neighbors(f"team:{team_id}", direction="in")
        if relation in ("home_team", "away_team")
    }
    assert from_index == from_graph


def test_players_link_to_clubs_that_exist(graph):
    linked = [p for p in graph.players if p.club_team_id]
    assert len(linked) >= 300
    assert all(p.club_team_id in graph.teams for p in linked)
    assert all(graph.teams[p.club_team_id].country == "BRA" for p in linked)


def test_seasons_are_recorded_per_competition(graph):
    assert graph.seasons_for("serie-a")[0] == 2003
    assert graph.seasons_for("libertadores")[0] == 2013
    assert graph.seasons_for("copa-do-brasil")[0] == 2012


def test_graph_is_cached_between_calls():
    first = load_knowledge_graph()
    second = load_knowledge_graph()
    assert first is second
    assert load_knowledge_graph(refresh=True) is not first


def test_load_is_fast_enough_for_a_server_start(graph):
    assert graph.report.load_seconds < 10.0


def test_neighbors_rejects_an_unknown_direction(graph):
    with pytest.raises(ValueError):
        graph.neighbors("team:flamengo-rj", direction="sideways")


def test_unknown_node_has_no_neighbours(graph):
    assert graph.node("team:nope") is None
    assert graph.neighbors("team:nope") == []


def test_nodes_of_type(graph):
    competitions = list(graph.nodes_of_type("competition"))
    assert len(competitions) == 5
    assert all(node["type"] == "competition" for node in competitions)


def test_active_teams_are_a_subset_of_all_teams(graph):
    active = graph.active_teams()
    assert 0 < len(active) <= len(graph.teams)
    assert all(graph.matches_by_team[team.id] for team in active)
