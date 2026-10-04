"""
Executable specifications: player queries.

Capability: find players by name, nationality, club and position, rank them
by rating, and summarise Brazilian players at Brazilian clubs.

Layer: test case (layer 1 of the four-layer model).
"""


def test_should_find_a_player_by_name(soccer):
    soccer.given.player("Gabriel Barbosa", club="Flamengo", overall=78, position="ST")
    soccer.given.player("Gabriel Jesus", club="Manchester City", overall=83)

    soccer.players.confirm_profile("gabriel barbosa", club="Flamengo", overall=78, position="ST")


def test_should_find_a_player_whose_name_is_accented_when_asked_without_accents(soccer):
    soccer.given.player("Fágner", club="Corinthians")

    soccer.players.confirm_profile("Fagner", club="Corinthians")


def test_should_rank_the_top_players_of_a_nationality(soccer):
    soccer.given.player("Alisson", nationality="Brazil", overall=89, club="Liverpool")
    soccer.given.player("L. Messi", nationality="Argentina", overall=94)
    soccer.given.player("Neymar Jr", nationality="Brazil", overall=92, club="Paris Saint-Germain")
    soccer.given.player("Casemiro", nationality="Brazil", overall=88, club="Real Madrid")

    soccer.players.confirm_top_players(nationality="Brazil", ranked=["Neymar Jr", "Alisson", "Casemiro"])


def test_should_list_a_clubs_highest_rated_players_first(soccer):
    soccer.given.player("Everton", club="Grêmio", overall=80)
    soccer.given.player("Luan", club="Grêmio", overall=82)
    soccer.given.player("Geromel", club="Grêmio", overall=81)
    soccer.given.player("Neymar Jr", club="Paris Saint-Germain", overall=92)

    soccer.players.confirm_top_players(club="Gremio", ranked=["Luan", "Geromel", "Everton"])


def test_should_find_the_forwards_at_a_club(soccer):
    soccer.given.player("Gabriel Barbosa", club="Santos", position="ST")
    soccer.given.player("Rodrygo", club="Santos", position="LW")
    soccer.given.player("Vanderlei", club="Santos", position="GK")

    soccer.players.confirm_top_players(club="Santos", position="forward", ranked=["Gabriel Barbosa", "Rodrygo"],
                                       in_any_order=True)


def test_should_summarise_brazilian_players_at_brazilian_clubs(soccer):
    soccer.given.match("Grêmio 1-0 Santos")
    soccer.given.player("Luan", club="Grêmio", nationality="Brazil", overall=82)
    soccer.given.player("Everton", club="Grêmio", nationality="Brazil", overall=80)
    soccer.given.player("Kannemann", club="Grêmio", nationality="Argentina", overall=78)
    soccer.given.player("Rodrygo", club="Santos", nationality="Brazil", overall=74)
    soccer.given.player("Alisson", club="Liverpool", nationality="Brazil", overall=89)

    soccer.players.confirm_brazilians_at_brazilian_clubs({"Grêmio": (2, "81.0"), "Santos": (1, "74.0")})


def test_should_suggest_similar_players_when_a_player_is_not_in_the_dataset(soccer):
    soccer.given.player("Gabriel Jesus", club="Manchester City", overall=83)
    soccer.given.player("M. Barbosa", club="Villarreal CF", overall=76)
    soccer.given.player("Casemiro", club="Real Madrid", overall=88)

    soccer.players.confirm_not_found("Gabriel Barbosa", suggesting=["Gabriel Jesus", "M. Barbosa"])
