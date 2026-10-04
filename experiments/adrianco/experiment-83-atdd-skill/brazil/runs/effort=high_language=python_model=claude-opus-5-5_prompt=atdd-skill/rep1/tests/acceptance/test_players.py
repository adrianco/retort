"""Player queries: names, nationalities, clubs, positions and ratings."""


def test_should_find_a_player_by_name(archive, players):
    archive.has_player("Gabriel Jesus", nationality="Brazil", club="Manchester City", position="ST", overall=83)

    players.look_up("Gabriel Jesus")

    players.confirm_profile(club="Manchester City", position="ST", overall=83, nationality="Brazil")


def test_should_find_a_player_whatever_the_accents(archive, players):
    archive.has_player("Éverton Ribeiro", club="Flamengo")

    players.look_up("everton ribeiro")

    players.confirm_profile(name="Éverton Ribeiro", club="Flamengo")


def test_should_rank_brazilian_players_by_rating(archive, players):
    archive.has_player("Neymar Jr", nationality="Brazil", overall=92)
    archive.has_player("L. Messi", nationality="Argentina", overall=94)
    archive.has_player("Casemiro", nationality="Brazil", overall=89)
    archive.has_player("Alisson", nationality="Brazil", overall=89)

    players.search(nationality="Brazilian")

    players.confirm_found_in_order("Neymar Jr", "Alisson", "Casemiro")


def test_should_rank_the_players_at_a_club(archive, players):
    archive.has_player("Luan", club="Grêmio", overall=82)
    archive.has_player("Kannemann", club="Grêmio", overall=78)
    archive.has_player("Geromel", club="Grêmio", overall=84)
    archive.has_player("D. Alves", club="Paris Saint-Germain", overall=86)

    players.search(club="Gremio")

    players.confirm_found_in_order("Geromel", "Luan", "Kannemann")


def test_should_find_the_forwards_at_a_club(archive, players):
    archive.has_player("Pato", club="São Paulo", position="ST")
    archive.has_player("Nenê", club="São Paulo", position="LW")
    archive.has_player("Volpi", club="São Paulo", position="GK")

    players.search(club="São Paulo FC", position="forward")

    players.confirm_found("Pato", "Nenê")


def test_should_summarise_brazilian_players_at_brazilian_clubs(archive, players):
    archive.has_match("Cruzeiro 1-0 Santos")
    archive.has_player("Fábio", nationality="Brazil", club="Cruzeiro", overall=80)
    archive.has_player("Thiago Neves", nationality="Brazil", club="Cruzeiro", overall=76)
    archive.has_player("Arrascaeta", nationality="Uruguay", club="Cruzeiro", overall=78)
    archive.has_player("Rodrygo", nationality="Brazil", club="Santos", overall=73)
    archive.has_player("Fernandinho", nationality="Brazil", club="Manchester City", overall=87)

    players.summarise_brazilians_at_brazilian_clubs()

    players.confirm_club_summary(Cruzeiro=(2, 78), Santos=(1, 73))


def test_should_recognise_a_clubs_formal_name_in_the_player_data(archive, players):
    archive.has_player("Magrão", club="Sport Club do Recife")

    players.search(club="Sport")

    players.confirm_found("Magrão")


def test_should_suggest_similar_names_when_a_player_is_not_found(archive, players):
    archive.has_player("Hélder Barbosa")
    archive.has_player("Neymar Jr")

    players.look_up("Gabriel Barbosa")

    players.confirm_not_found_but_suggested("Hélder Barbosa")
