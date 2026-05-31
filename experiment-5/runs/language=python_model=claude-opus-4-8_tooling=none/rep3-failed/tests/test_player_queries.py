"""BDD: player queries.

Feature: Player Queries
  Scenario: Search players by name
  Scenario: Filter by nationality / club / position
  Scenario: Rank players by rating
"""


def test_search_player_by_name(graph):
    res = graph.search_players(name="Neymar")
    assert res
    assert any("neymar" in p.name.lower() for p in res)
    assert res[0].overall and res[0].overall >= 85


def test_filter_brazilian_players(graph):
    res = graph.search_players(nationality="Brazil", limit=50)
    assert len(res) == 50
    assert all(p.nationality.lower() == "brazil" for p in res)


def test_top_brazilian_players_sorted(graph):
    top = graph.top_brazilian_players(limit=10)
    ratings = [p.overall for p in top]
    assert ratings == sorted(ratings, reverse=True)
    assert ratings[0] >= 88


def test_players_at_club(graph):
    res = graph.players_at_club("Flamengo")
    assert res
    assert all("flamengo" in p.club.lower() for p in res)
    ratings = [p.overall or 0 for p in res]
    assert ratings == sorted(ratings, reverse=True)


def test_filter_by_position_and_min_overall(graph):
    res = graph.search_players(position="GK", min_overall=85, limit=20)
    assert res
    assert all(p.position == "GK" for p in res)
    assert all(p.overall >= 85 for p in res)
