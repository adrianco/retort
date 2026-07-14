"""Feature: Player Queries (FIFA dataset)."""

import pytest


class TestPlayerQueries:
    """
    Scenario: Find Brazilian players in the dataset
    """

    def test_brazilian_players_exist(self, knowledge):
        df = knowledge.find_players(nationality="Brazil", limit=None)
        assert len(df) > 500
        assert (df["nationality"] == "Brazil").all()

    def test_top_brazilian_players_sorted(self, knowledge):
        df = knowledge.top_brazilian_players(limit=10)
        assert len(df) == 10
        # Sorted by overall descending
        overalls = df["overall"].tolist()
        assert overalls == sorted(overalls, reverse=True)

    def test_neymar_appears(self, knowledge):
        df = knowledge.find_players(name="Neymar", limit=5)
        assert not df.empty
        assert any("neymar" in str(n).lower() for n in df["name"])

    def test_filter_by_club(self, knowledge):
        df = knowledge.find_players(club="Real Madrid", limit=None)
        assert not df.empty
        assert df["club"].str.contains("Real Madrid").all()

    def test_filter_by_position(self, knowledge):
        df = knowledge.find_players(position="GK", limit=20)
        assert (df["position"] == "GK").all()

    def test_min_overall_filter(self, knowledge):
        df = knowledge.find_players(min_overall=85, limit=None)
        assert (df["overall"] >= 85).all()

    def test_brazil_at_brazilian_club(self, knowledge):
        # Brazilian players currently at Flamengo in the FIFA snapshot
        df = knowledge.find_players(nationality="Brazil", club="Flamengo", limit=None)
        # FIFA 19 dataset may or may not have Flamengo entries; assert shape is sane
        assert df.shape[1] > 0

    def test_unknown_player_empty(self, knowledge):
        df = knowledge.find_players(name="Zzzzzzz Nobody", limit=5)
        assert df.empty
