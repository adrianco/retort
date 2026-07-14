"""Feature: Competition Queries (standings, champions)."""

import pytest


class TestSeasonStandings:
    """
    Scenario: 2019 Brasileirão Final Standings
      Given matches for 2019 are loaded
      When I compute the season standings
      Then Flamengo should be the champion with 90 points
    """

    def test_2019_brasileirao_flamengo_champion(self, knowledge):
        table = knowledge.season_standings(season=2019, competition="Brasileirão Série A")
        champ = table.iloc[0]
        assert champ["team"].lower() == "flamengo"
        assert int(champ["points"]) == 90
        assert int(champ["wins"]) == 28
        assert int(champ["draws"]) == 6
        assert int(champ["losses"]) == 4

    def test_standings_are_sorted_by_points(self, knowledge):
        table = knowledge.season_standings(season=2019)
        pts = table["points"].tolist()
        assert pts == sorted(pts, reverse=True)

    def test_each_team_played_38_matches(self, knowledge):
        table = knowledge.season_standings(season=2019)
        # 20 teams in the Brasileirão; each plays 38
        assert (table["played"] == 38).all()
        assert len(table) == 20

    def test_rank_column_is_1_indexed(self, knowledge):
        table = knowledge.season_standings(season=2019)
        assert table["rank"].tolist() == list(range(1, len(table) + 1))

    def test_unknown_season_empty(self, knowledge):
        table = knowledge.season_standings(season=1900)
        assert table.empty


class TestChampion:
    def test_champion_returns_dict(self, knowledge):
        champ = knowledge.champion(2019, "Brasileirão Série A")
        assert champ is not None
        assert champ["team"].lower() == "flamengo"
        assert champ["season"] == 2019

    def test_unknown_season(self, knowledge):
        assert knowledge.champion(1900) is None
