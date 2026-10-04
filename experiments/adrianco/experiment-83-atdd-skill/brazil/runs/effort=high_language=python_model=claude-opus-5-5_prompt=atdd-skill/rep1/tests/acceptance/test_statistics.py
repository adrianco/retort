"""Statistical analysis: averages, rates, records and biggest wins."""


def test_should_calculate_the_average_goals_per_match(archive, statistics):
    archive.has_matches("Flamengo 2-1 Santos", "Santos 0-0 Bahia", "Bahia 1-2 Flamengo")

    statistics.request_overview(competition="Brasileirão")

    statistics.confirm_average_goals_per_match("2.00")


def test_should_calculate_the_home_win_rate(archive, statistics):
    archive.has_matches("Flamengo 2-1 Santos", "Santos 0-0 Bahia", "Bahia 1-2 Flamengo", "Santos 1-0 Flamengo")

    statistics.request_overview()

    statistics.confirm_home_win_rate("50.0%")


def test_should_find_the_biggest_wins(archive, statistics):
    archive.has_match("Santos 8-0 Bolívar", competition="Copa Libertadores")
    archive.has_match("Palmeiras 6-0 São Paulo")
    archive.has_match("Flamengo 5-1 Grêmio")
    archive.has_match("Bahia 1-0 Vitória")

    statistics.request_biggest_wins(limit=3)

    statistics.confirm_biggest_wins("Santos 8-0 Bolívar", "Palmeiras 6-0 São Paulo", "Flamengo 5-1 Grêmio")


def test_should_find_the_team_with_the_best_away_record(archive, statistics):
    archive.has_matches("Santos 0-1 Flamengo", "Bahia 0-2 Flamengo", "Flamengo 0-3 Bahia",
                        "Flamengo 1-1 Santos", "Santos 2-2 Bahia")

    statistics.rank_teams_by("win rate", venue="away")

    statistics.confirm_leader("Flamengo")


def test_should_find_the_highest_scoring_team_in_a_season(archive, statistics):
    archive.has_matches("Santos 0-1 Flamengo", "Bahia 4-2 Santos", "Flamengo 0-3 Bahia", season=2023)
    archive.has_match("Flamengo 9-0 Santos", season=2022)

    statistics.rank_teams_by("goals scored", season=2023)

    statistics.confirm_leader("Bahia")


def test_should_compare_two_seasons(archive, statistics):
    archive.has_matches("Flamengo 2-1 Santos", "Santos 1-0 Bahia", season=2018)
    archive.has_matches("Flamengo 4-1 Santos", "Santos 3-0 Bahia", season=2019)

    statistics.compare_seasons(2018, 2019)

    statistics.confirm_season_averages({2018: "2.00", 2019: "4.00"})
