"""
Context
=======
Fine-grained unit tests for the internal building blocks that the acceptance
suite drives: team-name normalization, date/goal parsing, and the in-memory
query engine. These test the units directly (white-box) and complement the
black-box acceptance specification in ``test_acceptance.py``.
"""

import pytest

from brazilian_soccer_mcp.knowledge_base import KnowledgeBase
from brazilian_soccer_mcp.loader import _parse_date, _to_int
from brazilian_soccer_mcp.models import Match, Player
from brazilian_soccer_mcp.normalize import key, normalize_team, strip_accents


# -- normalization ----------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("Palmeiras-SP", "Palmeiras"),
    ("Flamengo-RJ", "Flamengo"),
    ("Grêmio - RS", "Grêmio"),
    ("Nacional (URU)", "Nacional"),
    ("Boca Juniors (ARG)", "Boca Juniors"),
    ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ",
     "Boavista Sport Club"),
    ("Sport Club Corinthians Paulista", "Corinthians"),
])
def test_normalize_team_strips_suffixes_and_aliases(raw, expected):
    assert normalize_team(raw) == expected


def test_key_is_accent_and_case_insensitive():
    assert key("São Paulo") == key("sao paulo")
    assert strip_accents("Grêmio") == "Gremio"


# -- parsing ----------------------------------------------------------------
@pytest.mark.parametrize("raw,iso,year", [
    ("2012-05-19 18:30:00", "2012-05-19", 2012),
    ("2023-09-24", "2023-09-24", 2023),
    ("29/03/2003", "2003-03-29", 2003),
    ("", None, None),
])
def test_parse_date_handles_multiple_formats(raw, iso, year):
    assert _parse_date(raw) == (iso, year)


@pytest.mark.parametrize("raw,expected", [
    ("3", 3), ("1.0", 1), ("", None), ("nan", None), (None, None),
])
def test_to_int_is_tolerant(raw, expected):
    assert _to_int(raw) == expected


# -- query engine -----------------------------------------------------------
def _match(home, away, hg, ag, season=2023, comp="Brasileirão", date="2023-01-01"):
    return Match(competition=comp, season=season, date=date,
                 home_team=home, away_team=away, home_goal=hg, away_goal=ag)


def test_team_record_counts_results_and_goals():
    kb = KnowledgeBase([
        _match("Santos", "Vasco", 2, 0),
        _match("Vasco", "Santos", 1, 1),
        _match("Santos", "Flamengo", 0, 3),
    ], [])
    rec = kb.team_record("Santos", season=2023)
    assert (rec["wins"], rec["draws"], rec["losses"]) == (1, 1, 1)
    assert rec["goals_for"] == 3 and rec["goals_against"] == 4
    assert rec["win_rate"] == pytest.approx(33.3, abs=0.1)


def test_standings_rank_by_points_then_goal_difference():
    kb = KnowledgeBase([
        _match("A", "B", 3, 0),   # A wins big
        _match("B", "C", 1, 0),   # B beats C
        _match("C", "A", 0, 0),   # draw
    ], [])
    table = kb.standings(2023)["standings"]
    assert table[0]["team"] == "A"      # 4 pts, +3 GD
    assert [r["points"] for r in table] == [4, 3, 1]


def test_search_players_sorts_by_overall_desc():
    kb = KnowledgeBase([], [
        Player("Lower", 20, "Brazil", 70, 75, "Santos", "ST"),
        Player("Higher", 25, "Brazil", 88, 88, "Santos", "ST"),
    ])
    names = [p.name for p in kb.search_players(nationality="Brazil")]
    assert names == ["Higher", "Lower"]
