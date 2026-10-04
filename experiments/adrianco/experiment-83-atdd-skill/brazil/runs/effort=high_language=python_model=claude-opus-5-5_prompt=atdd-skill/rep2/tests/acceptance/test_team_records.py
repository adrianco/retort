"""
Executable specifications: team records and head-to-head comparisons.

Capability: win/draw/loss records, goals scored and conceded, performance by
competition and venue, and head-to-head comparisons between two clubs.

Layer: test case (layer 1 of the four-layer model).
"""


def test_should_report_a_teams_home_record_for_a_season(soccer):
    soccer.given.match("Corinthians 2-0 Santos", season=2022)
    soccer.given.match("Corinthians 1-1 Palmeiras", season=2022)
    soccer.given.match("Corinthians 0-1 São Paulo", season=2022)
    soccer.given.match("Santos 0-3 Corinthians", season=2022)
    soccer.given.match("Corinthians 4-0 Santos", season=2021)

    soccer.teams.confirm_record(
        "Corinthians", season=2022, venue="home",
        played=3, won=1, drawn=1, lost=1, goals_for=3, goals_against=2, win_rate="33.3%",
    )


def test_should_report_a_teams_record_in_each_competition(soccer):
    soccer.given.match("Palmeiras 2-0 Santos", competition="Brasileirão")
    soccer.given.match("Palmeiras 0-1 Ceará", competition="Copa do Brasil")
    soccer.given.match("Bolívar 0-3 Palmeiras", competition="Libertadores")

    soccer.teams.confirm_record("Palmeiras", competition="Copa do Brasil", played=1, lost=1)


def test_should_compare_two_teams_head_to_head(soccer):
    soccer.given.match("Palmeiras 2-0 Santos")
    soccer.given.match("Santos 1-3 Palmeiras")
    soccer.given.match("Santos 2-1 Palmeiras")
    soccer.given.match("Palmeiras 1-1 Santos")
    soccer.given.match("Palmeiras 5-0 Bahia")

    soccer.teams.confirm_head_to_head("Palmeiras", "Santos", wins=(2, 1), draws=1)


def test_should_list_the_competitions_a_team_has_played_in(soccer):
    soccer.given.match("Palmeiras 2-0 Santos", competition="Brasileirão")
    soccer.given.match("Palmeiras 1-0 Ceará", competition="Copa do Brasil")
    soccer.given.match("Palmeiras 3-0 Bolívar", competition="Libertadores")
    soccer.given.match("Santos 1-0 Ponte Preta", competition="Série B")

    soccer.teams.confirm_competitions("Palmeiras", ["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"])
