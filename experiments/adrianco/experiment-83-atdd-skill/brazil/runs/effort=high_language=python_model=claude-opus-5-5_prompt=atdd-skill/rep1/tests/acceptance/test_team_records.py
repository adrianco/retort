"""Team queries: records, goals and performance by competition."""


def test_should_report_a_teams_home_record_for_a_season(archive, teams):
    archive.has_match("Corinthians 2-0 Santos", season=2022)
    archive.has_match("Corinthians 1-1 Palmeiras", season=2022)
    archive.has_match("Corinthians 0-1 Grêmio", season=2022)
    archive.has_match("Santos 0-3 Corinthians", season=2022)
    archive.has_match("Corinthians 5-0 Bahia", season=2021)

    teams.request_record("Corinthians", season=2022, venue="home")

    teams.confirm_record(matches=3, wins=1, draws=1, losses=1, goals_for=3, goals_against=2)


def test_should_report_a_teams_away_record(archive, teams):
    archive.has_match("Santos 0-3 Corinthians")
    archive.has_match("Bahia 1-1 Corinthians")
    archive.has_match("Corinthians 2-0 Santos")

    teams.request_record("Corinthians", venue="away")

    teams.confirm_record(matches=2, wins=1, draws=1, losses=0, goals_for=4, goals_against=1)


def test_should_report_a_teams_win_rate(archive, teams):
    archive.has_match("Fluminense 1-0 Bahia")
    archive.has_match("Fluminense 2-0 Santos")
    archive.has_match("Fluminense 0-1 Vasco")

    teams.request_record("Fluminense")

    teams.confirm_win_rate("66.7%")


def test_should_report_performance_in_each_competition(archive, teams):
    archive.has_match("Internacional 2-0 Bahia", competition="Brasileirão")
    archive.has_match("Internacional 1-0 Bahia", competition="Copa do Brasil")
    archive.has_match("Bahia 1-0 Internacional", competition="Copa do Brasil")

    teams.request_record("Internacional", competition="Copa do Brasil")

    teams.confirm_record(matches=2, wins=1, draws=0, losses=1, goals_for=1, goals_against=1)


def test_should_list_the_competitions_a_team_has_played_in(archive, teams):
    archive.has_match("Palmeiras 1-0 Santos", competition="Brasileirão")
    archive.has_match("Palmeiras 2-0 Boca Juniors", competition="Copa Libertadores")
    archive.has_match("Palmeiras 3-0 Bahia", competition="Copa do Brasil")

    teams.request_overview("Palmeiras")

    teams.confirm_competitions("Brasileirão", "Copa do Brasil", "Copa Libertadores")


def test_should_combine_a_clubs_results_with_its_squad(archive, teams):
    archive.has_match("Grêmio 2-0 Bahia")
    archive.has_player("Marcelo Grohe", club="Grêmio", overall=80)
    archive.has_player("Luan", club="Grêmio", overall=82)

    teams.request_overview("Grêmio")

    teams.confirm_squad_includes("Luan", "Marcelo Grohe")
