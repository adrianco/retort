"""Unit tests for the repository query logic (no MCP layer)."""

from brazilian_soccer_mcp.models import Match
from brazilian_soccer_mcp.normalize import team_key
from brazilian_soccer_mcp.repository import SoccerRepository


def _match(home, away, hg, ag, season=2022, competition="Brasileirão"):
    return Match(
        competition=competition,
        competition_type="league",
        home_team=home,
        away_team=away,
        home_goal=hg,
        away_goal=ag,
        season=season,
        home_key=team_key(home),
        away_key=team_key(away),
    )


def test_team_record_aggregates_results():
    repo = SoccerRepository(
        [
            _match("Santos", "Bahia", 2, 0),
            _match("Gremio", "Santos", 1, 1),
            _match("Santos", "Flamengo", 0, 2),
        ],
        [],
    )
    record = repo.team_record("Santos")
    assert record["matches"] == 3
    assert record["wins"] == 1
    assert record["draws"] == 1
    assert record["losses"] == 1
    assert record["goals_for"] == 3
    assert record["goals_against"] == 3


def test_standings_points_and_order():
    repo = SoccerRepository(
        [
            _match("A", "B", 2, 0),
            _match("A", "C", 1, 0),
            _match("B", "C", 3, 1),
        ],
        [],
    )
    table = repo.standings("Brasileirão", 2022)
    assert [r["team"] for r in table] == ["A", "B", "C"]
    assert table[0]["points"] == 6
    assert table[1]["points"] == 3
    assert table[2]["points"] == 0


def test_head_to_head_only_counts_the_two_teams():
    repo = SoccerRepository(
        [
            _match("Palmeiras", "Santos", 3, 0),
            _match("Santos", "Palmeiras", 1, 1),
            _match("Palmeiras", "Flamengo", 4, 0),
        ],
        [],
    )
    h2h = repo.head_to_head("Palmeiras", "Santos")
    assert h2h["total_matches"] == 2
    assert h2h["team_a_wins"] == 1
    assert h2h["draws"] == 1


def test_statistics_average_goals():
    repo = SoccerRepository(
        [_match("A", "B", 2, 1), _match("C", "D", 0, 0)],
        [],
    )
    stats = repo.statistics()
    assert stats["total_matches"] == 2
    assert stats["total_goals"] == 3
    assert stats["average_goals_per_match"] == 1.5
