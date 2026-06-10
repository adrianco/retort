"""Feature: Competition Queries.

Standings are calculated from match results (3 points per win, 1 per draw)
and must reproduce known historical outcomes.
"""

import queries
from models import SERIE_A


class TestStandings:
    def test_2019_brasileirao_champion_is_flamengo(self, db):
        """Scenario: 'Who won the 2019 Brasileirão?' -> Flamengo, 90 points."""
        table = queries.competition_standings(db, 2019)
        assert table["competition"] == SERIE_A
        champion = table["standings"][0]
        assert champion["team"] == "Flamengo"
        assert champion["points"] == 90
        assert (champion["wins"], champion["draws"], champion["losses"]) == \
            (28, 6, 4)

    def test_full_round_robin_season(self, db):
        table = queries.competition_standings(db, 2019)
        assert table["matches_counted"] == 380          # 20 teams, double RR
        assert len(table["standings"]) == 20
        for entry in table["standings"]:
            assert entry["played"] == 38
            assert entry["points"] == 3 * entry["wins"] + entry["draws"]

    def test_positions_are_sequential_and_sorted(self, db):
        rows = queries.competition_standings(db, 2015)["standings"]
        assert [e["position"] for e in rows] == list(range(1, len(rows) + 1))
        points = [e["points"] for e in rows]
        assert points == sorted(points, reverse=True)

    def test_historical_2003_season_available(self, db):
        """The historical file extends coverage back to 2003."""
        rows = queries.competition_standings(db, 2003)["standings"]
        assert rows and rows[0]["team"] == "Cruzeiro"   # 2003 champion

    def test_unavailable_season_returns_empty(self, db):
        table = queries.competition_standings(db, 1990)
        assert table["standings"] == []

    def test_unknown_competition_raises(self, db):
        import pytest
        with pytest.raises(ValueError):
            queries.competition_standings(db, 2019, competition="Premier League")
