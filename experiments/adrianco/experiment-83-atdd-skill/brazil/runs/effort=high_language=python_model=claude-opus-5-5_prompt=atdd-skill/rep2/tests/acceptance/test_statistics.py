"""
Executable specifications: statistical analysis across matches.

Capability: goals-per-match averages, home/away results, biggest wins,
best home/away records, season comparisons and derbies.

Layer: test case (layer 1 of the four-layer model).
"""


def test_should_calculate_average_goals_per_match(soccer):
    soccer.given.match("Flamengo 3-1 Bahia")
    soccer.given.match("Santos 0-0 Grêmio")
    soccer.given.match("Vasco 2-1 Ceará")

    soccer.stats.confirm_summary(matches=3, average_goals="2.33")


def test_should_calculate_how_often_the_home_team_wins(soccer):
    soccer.given.match("Flamengo 3-1 Bahia")
    soccer.given.match("Santos 0-0 Grêmio")
    soccer.given.match("Vasco 2-1 Ceará")
    soccer.given.match("Ceará 0-2 Fortaleza")

    soccer.stats.confirm_summary(home_win_rate="50.0%", draw_rate="25.0%", away_win_rate="25.0%")


def test_should_list_the_biggest_wins_first(soccer):
    soccer.given.match("Palmeiras 6-0 São Paulo", date="2015-09-13")
    soccer.given.match("Santos 8-0 Bolívar", competition="Libertadores", date="2012-05-27")
    soccer.given.match("Flamengo 5-0 Grêmio", date="2019-10-27")
    soccer.given.match("Bahia 1-0 Vitória")

    soccer.stats.confirm_biggest_wins([
        "2012-05-27: Santos 8-0 Bolívar (Copa Libertadores)",
        "2015-09-13: Palmeiras 6-0 São Paulo (Brasileirão Série A)",
        "2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Série A)",
    ])


def test_should_find_the_team_with_the_best_away_record(soccer):
    soccer.given.match("Santos 0-1 Flamengo")
    soccer.given.match("Bahia 1-2 Flamengo")
    soccer.given.match("Flamengo 0-1 Palmeiras")
    soccer.given.match("Santos 1-1 Palmeiras")

    soccer.stats.confirm_best_record(venue="away", team="Flamengo")


def test_should_find_the_team_with_the_best_home_record(soccer):
    soccer.given.match("Santos 0-1 Flamengo")
    soccer.given.match("Palmeiras 2-0 Bahia")
    soccer.given.match("Palmeiras 1-0 Santos")
    soccer.given.match("Flamengo 1-1 Palmeiras")

    soccer.stats.confirm_best_record(venue="home", team="Palmeiras")


def test_should_compare_two_seasons(soccer):
    soccer.given.match("Flamengo 3-1 Bahia", season=2018)
    soccer.given.match("Santos 0-0 Grêmio", season=2018)
    soccer.given.match("Flamengo 5-0 Grêmio", season=2019)

    soccer.stats.confirm_season_comparison(2018, 2019, average_goals=("2.00", "5.00"))


def test_should_find_the_derbies_played_in_a_season(soccer):
    soccer.given.match("Flamengo 2-1 Fluminense", season=2023)
    soccer.given.match("Grêmio 1-1 Internacional", season=2023)
    soccer.given.match("Flamengo 1-0 Bahia", season=2023)
    soccer.given.match("Corinthians 0-0 Palmeiras", season=2022)

    soccer.stats.confirm_derbies(2023, ["Fla-Flu", "Grenal"])
