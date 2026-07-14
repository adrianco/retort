"""BDD: competition queries.

Feature: Competition Queries
  Scenario: Compute final standings from match results
  Scenario: Identify the champion of a season
"""


def test_2019_brasileirao_standings(graph):
    # Given 2019 Série A matches / When standings computed / Then Flamengo top
    table = graph.standings("Brasileirão", 2019)
    assert len(table) == 20            # 20-team league
    champ = table[0]
    assert champ.team.lower().startswith("flamengo")
    assert champ.points == 90
    assert (champ.wins, champ.draws, champ.losses) == (28, 6, 4)


def test_standings_sorted_by_points(graph):
    table = graph.standings("Brasileirão", 2018)
    points = [r.points for r in table]
    assert points == sorted(points, reverse=True)


def test_champion_helper(graph):
    champ = graph.champion("Brasileirão", 2017)
    # Corinthians won the 2017 Brasileirão.
    assert champ is not None
    assert champ.team.lower().startswith("corinthians")


def test_each_team_plays_double_round_robin(graph):
    # In a 20-team league each team plays 38 games.
    table = graph.standings("Brasileirão", 2019)
    assert all(r.matches == 38 for r in table)
