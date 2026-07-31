"""
Unit tests for the answer renderers.

Context
-------
TASK.md specifies the shape of the answers, and empty results are the easiest
place for a formatter to produce something useless ("Matches:" with nothing
after it).  These tests cover the empty and partial paths that the
happy-path scenarios never reach.
"""

from __future__ import annotations

import datetime as dt

import pytest

from brazilian_soccer import formatting as fmt
from brazilian_soccer import queries as q
from brazilian_soccer.models import HeadToHead, Match, StandingRow, TeamRecord


def test_match_line_without_a_score(graph):
    match = Match(id="x", competition_id="copa-do-brasil", season=2021,
                  date=dt.date(2021, 7, 27), home_team_id="flamengo-rj",
                  away_team_id="santos-sp", home_team_raw="Flamengo",
                  away_team_raw="Santos", stage="round of 16")
    line = fmt.format_match_line(graph, match)
    assert "no score recorded" in line
    assert "Round of 16" in line


def test_match_line_without_a_date(graph):
    match = Match(id="x", competition_id="libertadores", season=None, date=None,
                  home_team_id="flamengo-rj", away_team_id="athletico-pr")
    assert "date unknown" in fmt.format_match_line(graph, match)


def test_empty_match_list_explains_itself(graph):
    assert "No matches found" in fmt.format_matches(graph, [], title="Nothing")
    custom = fmt.format_matches(graph, [], title="Nothing", empty_message="Nada.")
    assert custom == "Nada."


def test_head_to_head_with_no_meetings(graph):
    record = HeadToHead(team_a_id="a", team_a="A", team_b_id="b", team_b="B")
    text = fmt.format_head_to_head(graph, record)
    assert "No meetings" in text
    assert "Head-to-head in dataset" not in text


def test_empty_standings_explains_itself(graph):
    assert "No results available" in fmt.format_standings(graph, [], title="Nowhere")


def test_standings_can_be_truncated(graph):
    rows = q.standings(graph, "brasileirao", 2019)
    text = fmt.format_standings(graph, rows, title="2019", limit=5)
    assert "(15 more teams)" in text
    assert len(text.splitlines()) == 7  # title + 5 rows + the truncation note


def test_player_list_note_is_appended_when_empty():
    text = fmt.format_players([], title="Nobody", note="Coverage note.")
    assert "No players" in text
    assert "Coverage note." in text


def test_player_profile_lists_alternatives(graph):
    profile = q.player_profile(graph, "Gabriel")
    text = fmt.format_player_profile(profile)
    assert "Other players matching that name" in text


def test_player_profile_shows_the_linked_club(graph):
    profile = q.player_profile(graph, "Josué Chiamulera")
    text = fmt.format_player_profile(profile)
    assert "Linked club in match graph" in text


def test_competition_stats_falls_back_to_a_single_biggest_win(graph):
    stats = q.competition_stats(graph, competition="libertadores", season=2019)
    text = fmt.format_competition_stats(graph, stats)
    assert "Biggest victory:" in text


def test_compare_teams_mentions_the_scope(graph):
    comparison = q.compare_teams(graph, "Palmeiras", "Santos",
                                 competition="brasileirao", season=2019)
    text = fmt.format_compare_teams(graph, comparison)
    assert "Campeonato Brasileiro Série A" in text
    assert "2019" in text


def test_no_derbies_message(graph):
    assert fmt.format_derbies(graph, []) == "No derby matches found for that filter."


def test_team_record_renders_all_labels():
    record = TeamRecord(team_id="x", team_name="X", scope="away")
    record.add(1, 0)
    text = fmt.format_team_record(record)
    assert "X away record" in text
    assert "Points: 3 (3.00 per game)" in text
    assert "diff +1" in text


def test_standing_row_note_is_rendered(graph):
    record = TeamRecord(team_id="x", team_name="X")
    record.add(1, 0)
    text = fmt.format_standings(graph, [StandingRow(1, record, "Champion")], title="T")
    assert "1. X - 3 pts (1W, 0D, 0L)" in text
    assert "- Champion" in text
