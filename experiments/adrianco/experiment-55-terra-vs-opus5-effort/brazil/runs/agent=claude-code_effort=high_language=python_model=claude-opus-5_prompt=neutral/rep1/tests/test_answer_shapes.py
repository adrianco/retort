"""Tests that rendered answers match the shapes shown in the specification.

Context
-------
The specification includes "Example answer format" blocks for each query
category.  An LLM consumes the text block of a tool result, so the rendering
matters as much as the numbers: these tests check that the expected labels,
orderings and caveats actually appear.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.formatting import render
from brazilian_soccer.queries import (
    biggest_wins,
    club_squad,
    competition_stats,
    find_matches,
    head_to_head,
    standings,
    team_stats,
)


def test_match_list_shape(graph):
    """`- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)`"""
    text = render("head_to_head",
                  head_to_head("Flamengo", "Fluminense", limit=3, graph=graph))
    lines = [line for line in text.splitlines() if line.startswith("- 20")]
    assert lines
    for line in lines:
        assert line[2:12].count("-") == 2          # ISO date
        assert ": " in line and "(" in line and ")" in line
    assert "Head-to-head in dataset:" in text
    assert "Fla-Flu" in text


def test_team_record_shape(graph):
    """Matches / Wins, Draws, Losses / Goals For, Goals Against / Win rate."""
    text = render("team_stats",
                  team_stats("Corinthians", season=2022, competition="serie-a",
                             venue="home", graph=graph))
    for label in ("- Matches:", "- Wins:", "Draws:", "Losses:",
                  "- Goals For:", "Goals Against:", "- Win rate:"):
        assert label in text, label
    assert text.startswith("Corinthians home record (2022")


def test_standings_shape(graph):
    text = render("standings", standings(2019, "serie-a", graph=graph))
    lines = text.splitlines()
    assert "standings (calculated from 380 matches)" in lines[0]
    header = next(line for line in lines if line.strip().startswith("#"))
    assert header.split() == ["#", "Team", "P", "W", "D", "L", "GF", "GA",
                              "GD", "Pts"]
    champion_line = next(line for line in lines if "Champion" in line)
    assert champion_line.strip().startswith("1")
    assert "Flamengo" in champion_line
    assert sum("Relegated" in line for line in lines) == 4


def test_player_list_shape(graph):
    """`1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain`"""
    from brazilian_soccer.queries import search_players

    text = render("search_players",
                  search_players(nationality="Brazil", limit=3, graph=graph))
    numbered = [line for line in text.splitlines() if line[:2] in ("1.", "2.", "3.")]
    assert len(numbered) == 3
    for line in numbered:
        assert "Overall:" in line and "Position:" in line and "Club:" in line


def test_squad_summary_shape(graph):
    text = render("club_squad", club_squad("Grêmio", limit=3, graph=graph))
    assert "average rating" in text
    assert "By position:" in text
    assert "Brazilian players in squad:" in text


def test_statistics_shape(graph):
    """`Average goals per match: 2.47` / `Home win rate: 47.3%`"""
    text = render("competition_stats",
                  competition_stats("serie-a", graph=graph))
    assert "Average goals per match:" in text
    assert "Home win rate:" in text
    assert "Top scoring teams:" in text


def test_biggest_wins_shape(graph):
    text = render("biggest_wins", biggest_wins(limit=3, graph=graph))
    numbered = [line for line in text.splitlines() if line[:2] in ("1.", "2.", "3.")]
    assert len(numbered) == 3
    assert all("margin" in line for line in numbered)


def test_empty_results_are_explained_not_blank(graph):
    text = render("find_matches",
                  find_matches(team="Santos", season=1999, limit=5, graph=graph))
    assert "no matches found" in text
    assert "Notes:" in text


def test_unplayed_matches_are_labelled(graph):
    """One Libertadores row has no score; it must not render as `None-None`."""
    result = find_matches(competition="libertadores", limit=5,
                          newest_first=False, graph=graph)
    unplayed = [m for m in result["matches"] if m["home_goals"] is None]
    assert unplayed, "expected the dateless, scoreless Libertadores row"
    text = render("find_matches", result)
    assert "not played" in text
    assert "None" not in text


def test_notes_are_rendered_when_present(graph):
    text = render("club_squad", club_squad("Palmeiras", graph=graph))
    assert "Notes:" in text and "FIFA 19" in text
