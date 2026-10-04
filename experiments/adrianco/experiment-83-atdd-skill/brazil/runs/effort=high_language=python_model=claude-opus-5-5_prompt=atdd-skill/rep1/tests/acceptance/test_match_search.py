"""Match queries: finding matches by team, date, competition and season."""


def test_should_find_every_meeting_between_two_teams(archive, matches):
    archive.has_match("Flamengo 2-1 Fluminense", date="2023-09-03")
    archive.has_match("Fluminense 1-0 Flamengo", date="2023-05-28")
    archive.has_match("Flamengo 3-0 Santos")

    matches.search_between("Flamengo", "Fluminense")

    matches.confirm_found("Flamengo 2-1 Fluminense", "Fluminense 1-0 Flamengo")


def test_should_find_the_matches_a_team_played_in_a_season(archive, matches):
    archive.has_match("Palmeiras 2-0 Santos", date="2023-06-01")
    archive.has_match("Bahia 1-1 Palmeiras", date="2023-08-12")
    archive.has_match("Palmeiras 4-0 Bahia", date="2022-07-10")

    matches.search(team="Palmeiras", season=2023)

    matches.confirm_found("Palmeiras 2-0 Santos", "Bahia 1-1 Palmeiras")


def test_should_find_only_home_matches_when_asked(archive, matches):
    archive.has_match("Corinthians 2-0 Santos")
    archive.has_match("Santos 1-1 Corinthians")

    matches.search(team="Corinthians", venue="home")

    matches.confirm_found("Corinthians 2-0 Santos")


def test_should_find_matches_within_a_date_range(archive, matches):
    archive.has_match("Grêmio 1-0 Internacional", date="2021-03-01")
    archive.has_match("Internacional 2-2 Grêmio", date="2021-06-15")
    archive.has_match("Grêmio 3-1 Internacional", date="2021-11-20")

    matches.search(team="Grêmio", date_from="2021-05-01", date_to="2021-12-01")

    matches.confirm_found("Internacional 2-2 Grêmio", "Grêmio 3-1 Internacional")


def test_should_find_matches_in_a_single_competition(archive, matches):
    archive.has_match("Cruzeiro 2-0 Bahia", competition="Brasileirão")
    archive.has_match("Cruzeiro 1-0 Bahia", competition="Copa do Brasil")

    matches.search(team="Cruzeiro", competition="Copa do Brasil")

    matches.confirm_found("Cruzeiro 1-0 Bahia")


def test_should_find_copa_do_brasil_finals(archive, matches):
    archive.has_match("Flamengo 2-0 Athletico-PR", competition="Copa do Brasil", season=2013, cup_round=8)
    archive.has_match("Athletico-PR 1-1 Flamengo", competition="Copa do Brasil", season=2013, cup_round=8)
    archive.has_match("Flamengo 3-0 Cruzeiro", competition="Copa do Brasil", season=2013, cup_round=7)

    matches.search(competition="Copa do Brasil", stage="final")

    matches.confirm_found("Flamengo 2-0 Athletico-PR", "Athletico-PR 1-1 Flamengo")


def test_should_report_the_most_recent_meeting_first(archive, matches):
    archive.has_match("Flamengo 1-0 Corinthians", date="2019-05-01")
    archive.has_match("Corinthians 2-2 Flamengo", date="2022-10-09")
    archive.has_match("Flamengo 3-1 Corinthians", date="2021-04-04")

    matches.search_between("Flamengo", "Corinthians")

    matches.confirm_most_recent("Corinthians 2-2 Flamengo", date="2022-10-09")


def test_should_find_matches_from_every_match_dataset(archive, matches):
    archive.has_match("Santos 1-0 Vasco", source="brasileirao", season=2015)
    archive.has_match("Santos 2-0 Vasco", source="copa do brasil", season=2016)
    archive.has_match("Santos 3-0 Vasco", source="libertadores", season=2017)
    archive.has_match("Santos 4-0 Vasco", source="extended statistics", season=2023)
    archive.has_match("Santos 5-0 Vasco", source="historical brasileirao", season=2008)

    matches.search(team="Santos")

    matches.confirm_match_count(5)


def test_should_not_double_count_a_match_recorded_in_several_datasets(archive, matches):
    archive.has_match("Botafogo 2-1 Vasco", date="2019-07-14", source="brasileirao")
    archive.has_match("Botafogo 2-1 Vasco", date="2019-07-14", source="historical brasileirao")
    archive.has_match("Botafogo 2-1 Vasco", date="2019-07-14", source="extended statistics")

    matches.search_between("Botafogo", "Vasco")

    matches.confirm_match_count(1)


def test_should_include_match_statistics_when_they_are_known(archive, matches):
    archive.has_match("Fortaleza 2-0 Ceará", source="extended statistics", corners="7-3", shots="15-6")

    matches.search_between("Fortaleza", "Ceará")

    matches.confirm_statistics(corners="7-3", shots="15-6")
