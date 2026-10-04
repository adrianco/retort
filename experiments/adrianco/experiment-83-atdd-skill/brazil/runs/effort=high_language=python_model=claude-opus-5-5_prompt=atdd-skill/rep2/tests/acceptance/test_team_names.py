"""
Executable specifications: recognising teams however the datasets name them.

Capability: the same club is written differently across datasets
("Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "Sociedade Esportiva Palmeiras",
"Sao Paulo" / "São Paulo"). Questions about a club must cover all of them,
without confusing different clubs that share a name.

Layer: test case (layer 1 of the four-layer model).
"""


def test_should_recognise_a_club_however_a_dataset_writes_its_name(soccer):
    soccer.given.match("Palmeiras-SP 1-0 Santos-SP", source="brasileirão", date="2015-05-10")
    soccer.given.match("Palmeiras - SP 2-0 Santos - SP", source="copa do brasil", date="2015-11-25")
    soccer.given.match("Sociedade Esportiva Palmeiras 0-0 Santos FC", source="extended statistics", date="2016-06-01")

    soccer.teams.confirm_record("Palmeiras", played=3)


def test_should_answer_questions_asked_without_accents(soccer):
    soccer.given.match("Grêmio 2-1 Internacional")
    soccer.given.match("São Paulo 0-0 Grêmio")

    soccer.teams.confirm_record("gremio", played=2)


def test_should_not_confuse_clubs_from_different_states_that_share_a_name(soccer):
    soccer.given.match("Botafogo - RJ 2-0 Bahia - BA", source="copa do brasil")
    soccer.given.match("Botafogo - PB 1-1 Remo - PA", source="copa do brasil")
    soccer.given.match("Botafogo-RJ 1-0 Vasco-RJ", source="brasileirão")

    soccer.teams.confirm_record("Botafogo", played=2)


def test_should_link_a_players_club_to_the_same_clubs_matches(soccer):
    soccer.given.match("Sport-PE 2-0 Náutico-PE", source="brasileirão")
    soccer.given.player("Hernane", club="Sport Club do Recife", nationality="Brazil", overall=70)

    soccer.teams.confirm_club_profile("Sport Recife", squad_size=1, matches_played=1)


def test_should_not_confuse_a_foreign_club_with_a_brazilian_club_of_the_same_name(soccer):
    soccer.given.match("River Plate 2-0 Grêmio", competition="Libertadores")
    soccer.given.match("Palmeiras 1-1 River Plate", competition="Libertadores")
    soccer.given.match("River Plate - SE 1-0 Sergipe - SE", source="copa do brasil")

    soccer.teams.confirm_record("River Plate", played=2)


def test_should_recognise_a_club_by_its_full_formal_name(soccer):
    soccer.given.match("Corinthians 2-0 Santos")

    soccer.teams.confirm_record("SC Corinthians Paulista", played=1)


def test_should_explain_when_a_team_is_not_in_the_datasets(soccer):
    soccer.given.match("Grêmio 2-1 Internacional")

    soccer.teams.confirm_unknown("Atlantis United")
