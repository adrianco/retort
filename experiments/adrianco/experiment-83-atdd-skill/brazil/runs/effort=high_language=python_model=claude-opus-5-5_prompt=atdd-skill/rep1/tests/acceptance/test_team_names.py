"""Data quality: the same club, written many ways, is still the same club."""


def test_should_recognise_a_club_however_its_name_is_written(archive, matches):
    archive.has_match("Palmeiras-SP 2-0 Santos-SP", source="brasileirao", season=2014)
    archive.has_match("Palmeiras - SP 1-1 Santos - SP", source="copa do brasil", season=2015)
    archive.has_match("Palmeiras 3-1 Santos", source="historical brasileirao", season=2010)

    matches.search_between("Sociedade Esportiva Palmeiras", "Santos FC")

    matches.confirm_match_count(3)


def test_should_match_club_names_regardless_of_accents(archive, matches):
    archive.has_match("Gremio 1-0 Sao Paulo", source="extended statistics", season=2021)
    archive.has_match("Grêmio 2-2 São Paulo", source="historical brasileirao", season=2011)

    matches.search_between("gremio", "SÃO PAULO")

    matches.confirm_match_count(2)


def test_should_tell_apart_clubs_that_share_a_name_in_different_states(archive, matches):
    archive.has_match("Atlético-MG 2-0 Bahia")
    archive.has_match("Atlético-PR 1-0 Bahia")
    archive.has_match("Atlético-GO 3-3 Bahia")

    matches.search(team="Atlético Mineiro")

    matches.confirm_found("Atlético-MG 2-0 Bahia")


def test_should_present_clubs_with_their_portuguese_spelling(archive, matches):
    archive.has_match("Sao Paulo-SP 1-0 Gremio-RS", source="brasileirao")

    matches.search(team="Sao Paulo")

    matches.confirm_found("São Paulo 1-0 Grêmio")


def test_should_understand_brazilian_date_format(archive, matches):
    archive.has_match("Vitória 2-1 Bahia", date="2005-03-29", source="historical brasileirao")

    matches.search(team="Vitória", date_from="2005-03-29", date_to="2005-03-29")

    matches.confirm_most_recent("Vitória 2-1 Bahia", date="2005-03-29")
