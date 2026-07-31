"""
Context
=======
Covers the specification's non-functional success criteria:

* Query performance -- simple lookups under 2 seconds, aggregate queries under
  5 seconds, no timeouts.  The graph fixture is session-scoped, so these
  timings measure query cost against an already-loaded corpus, which is what the
  MCP server does after start-up; the load itself is timed separately.
* Response formatting -- the text blocks the tools return must follow the shapes
  in the specification's "Example answer format" sections.
"""

from __future__ import annotations

import time

import pytest

from brazilian_soccer import formatters as fmt
from brazilian_soccer.loader import DEFAULT_DATA_DIR
from brazilian_soccer.graph import load_default_graph

SIMPLE_BUDGET_S = 2.0
AGGREGATE_BUDGET_S = 5.0


def _timed(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return time.perf_counter() - start, result


@pytest.mark.parametrize(
    "tool,args",
    [
        ("search_matches", {"team": "Flamengo", "opponent": "Corinthians", "limit": 10}),
        ("head_to_head", {"team_a": "Grêmio", "team_b": "Internacional"}),
        ("team_stats", {"team": "Palmeiras", "season": 2023}),
        ("player_profile", {"name": "Neymar"}),
        ("search_players", {"nationality": "Brazil", "limit": 20}),
        ("standings", {"competition": "Serie A", "season": 2019}),
    ],
)
def test_simple_lookups_respond_in_under_two_seconds(server_call, tool, args):
    elapsed, result = _timed(server_call, tool, **args)
    assert result["isError"] is False
    assert elapsed < SIMPLE_BUDGET_S, f"{tool} took {elapsed:.2f}s"


@pytest.mark.parametrize(
    "tool,args",
    [
        ("statistics", {}),
        ("statistics", {"competition": "Serie A"}),
        ("biggest_wins", {"limit": 25}),
        ("team_leaderboard", {"metric": "win_rate", "venue": "away", "min_matches": 50}),
        ("find_derbies", {}),
        ("brazilian_club_squads", {}),
        ("dataset_overview", {}),
    ],
)
def test_aggregate_queries_respond_in_under_five_seconds(server_call, tool, args):
    elapsed, result = _timed(server_call, tool, **args)
    assert result["isError"] is False
    assert elapsed < AGGREGATE_BUDGET_S, f"{tool} took {elapsed:.2f}s"


def test_loading_the_whole_corpus_is_a_few_seconds():
    if not DEFAULT_DATA_DIR.exists():
        pytest.skip("dataset directory missing")
    elapsed, graph = _timed(load_default_graph)
    assert elapsed < 30.0, f"loading took {elapsed:.1f}s"
    assert len(graph.matches) > 15000
    assert len(graph.players) == 18207


# --------------------------------------------------------------- formatting

def _match(**overrides):
    base = {
        "competition": "Brasileirão Série A", "season": 2023, "date": "2023-09-03",
        "home_team": "Flamengo", "away_team": "Fluminense",
        "home_goals": 2, "away_goals": 1, "score": "2-1", "round": "22",
        "source": "test",
    }
    base.update(overrides)
    return base


def test_match_lines_follow_the_specified_shape():
    line = fmt.format_match(_match())
    assert line == "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)"
    assert fmt.format_match(_match(), with_competition=False) == (
        "2023-09-03: Flamengo 2-1 Fluminense"
    )
    staged = fmt.format_match(_match(round=None, stage="final"))
    assert staged.endswith("(Brasileirão Série A final)")


def test_match_list_reports_how_many_more_exist():
    text = fmt.format_match_list([_match()], header="Fla-Flu:", total=18)
    assert text.startswith("Fla-Flu:")
    assert "... (17 more matches in dataset)" in text
    assert fmt.format_match_list([]) == "No matches found."


def test_record_block_matches_the_specification_example(graph):
    stats = graph.team_stats("Corinthians", season=2022, competition="Serie A", venue="home")
    text = fmt.format_team_stats(stats)
    for expected in ("- Matches:", "- Wins:", "- Goals For:", "- Win rate:"):
        assert expected in text


def test_standings_block_marks_champion_and_relegated(graph):
    text = fmt.format_standings(graph.standings("Serie A", 2019))
    lines = text.splitlines()
    assert lines[0].startswith("2019 Brasileirão Série A table")
    assert lines[1].startswith("1. Flamengo - 90 pts (28W, 6D, 4L")
    assert lines[1].endswith("- Champion")
    assert sum(1 for line in lines if line.endswith("- Relegated")) == 4


def test_player_block_matches_the_specification_example(graph):
    text = fmt.format_players(graph.search_players(nationality="Brazil", limit=3))
    first = text.splitlines()[1]
    assert first.startswith("1. Neymar Jr - Overall: 92, Position: LW, Club:")


def test_statistics_block_has_the_headline_numbers(graph):
    text = fmt.format_statistics(graph.statistics(competition="Serie A"))
    assert "- Average goals per match:" in text
    assert "- Home win rate:" in text


def test_head_to_head_block_ends_with_the_summary_line(graph):
    text = fmt.format_head_to_head(graph.head_to_head("Flamengo", "Fluminense", limit=3))
    assert text.startswith("Flamengo vs Fluminense (Fla-Flu derby):")
    assert "Head-to-head in dataset:" in text.splitlines()[-1]


def test_empty_results_never_raise():
    assert fmt.format_players([]) == "No players found."
    assert fmt.format_biggest_wins([]) == "No matches found."
    assert fmt.format_leaderboard([], metric="wins") == "No teams match these filters."
    assert fmt.format_statistics({"matches": 0}) == "No matches match these filters."
