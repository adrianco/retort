"""
================================================================================
Context
================================================================================
Test module: test_competition_queries.py
Project:     Brazilian Soccer MCP Server
Feature:     Competition Queries (capability category 4) — standings & champions.
Style:       BDD Given-When-Then.

Standings are validated against known real-world results, e.g. Flamengo won the
2019 Brasileirão with 90 points (28W 6D 4L) — exactly the spec's example.
================================================================================
"""


class TestStandings:
    def test_serie_a_table_has_twenty_teams(self, kg):
        # Given the match data is loaded
        # When I compute the 2019 Brasileirão table
        table = kg.standings("brasileirao", 2019)
        # Then it has the expected 20 teams each playing 38 games
        assert len(table) == 20
        assert all(r.played == 38 for r in table)

    def test_2019_champion_is_flamengo_with_90_points(self, kg):
        # When I ask who won the 2019 Brasileirão
        champ = kg.champion("brasileirao", 2019)
        # Then it is Flamengo with the historically correct record
        assert champ.team == "Flamengo"
        assert champ.points == 90
        assert (champ.wins, champ.draws, champ.losses) == (28, 6, 4)

    def test_table_is_ordered_by_points(self, kg):
        # When the table is produced
        table = kg.standings("brasileirao", 2018)
        # Then points are non-increasing down the table
        points = [r.points for r in table]
        assert points == sorted(points, reverse=True)
        # And positions are 1..N
        assert [r.position for r in table] == list(range(1, len(table) + 1))

    def test_points_equal_three_wins_plus_draws(self, kg):
        table = kg.standings("brasileirao", 2017)
        for r in table:
            assert r.points == r.wins * 3 + r.draws

    def test_historic_season_only_in_novo_source(self, kg):
        # Given 2010 exists only in the historical (novo) dataset
        # When I compute its champion
        champ = kg.champion("brasileirao", 2010)
        # Then Fluminense (the real 2010 champion) tops the table
        assert champ.team == "Fluminense"


class TestSeasonsAndCompetitions:
    def test_list_seasons(self, kg):
        seasons = kg.list_seasons("brasileirao")
        assert 2003 in seasons and 2019 in seasons
        assert seasons == sorted(seasons)

    def test_list_competitions(self, kg):
        comps = kg.list_competitions()
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps
