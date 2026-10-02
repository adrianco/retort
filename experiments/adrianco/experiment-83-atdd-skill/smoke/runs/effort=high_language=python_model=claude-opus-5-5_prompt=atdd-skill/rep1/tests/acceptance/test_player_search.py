"""
Executable specification: finding players and combining them with clubs.

Layer 1 of the four-layer acceptance test model. Players come from the
FIFA player database; "Brazilian clubs" are the clubs that appear in the
Brazilian match data, which makes some of these cross-dataset questions.
"""


class PlayerSearchSpec:
    def should_find_a_player_by_name(self, given, players):
        given.fifa_player(name="Gabriel Barbosa", club="Santos", overall=78, position="ST")

        players.profile(name="Gabriel Barbosa")

        players.confirm_profile(name="Gabriel Barbosa", club="Santos", overall=78, position="ST")

    def should_find_players_of_a_nationality_highest_rated_first(self, given, players):
        given.fifa_player(name="Casemiro", nationality="Brazil", overall=89)
        given.fifa_player(name="Neymar Jr", nationality="Brazil", overall=92)
        given.fifa_player(name="L. Messi", nationality="Argentina", overall=94)

        players.search(nationality="Brazil")

        players.confirm_found_in_order("Neymar Jr", "Casemiro")

    def should_find_the_highest_rated_players_at_a_club(self, given, players):
        given.fifa_player(name="Everton", club="Grêmio", overall=82)
        given.fifa_player(name="Geromel", club="Grêmio", overall=84)
        given.fifa_player(name="Bruno Henrique", club="Santos", overall=79)

        players.search(club="Gremio")

        players.confirm_found_in_order("Geromel", "Everton")

    def should_find_forwards_at_a_club(self, given, players):
        given.fifa_player(name="Gabriel Barbosa", club="Santos", position="ST")
        given.fifa_player(name="Rodrygo", club="Santos", position="LW")
        given.fifa_player(name="Vanderlei", club="Santos", position="GK")

        players.search(club="Santos", position="forward")

        players.confirm_found(count=2)

    def should_summarise_brazilian_players_at_brazilian_clubs(self, given, players):
        given.brasileirao_match(home="Santos", away="Gremio")
        given.fifa_player(name="Rodrygo", nationality="Brazil", club="Santos", overall=70)
        given.fifa_player(name="Vanderlei", nationality="Brazil", club="Santos", overall=74)
        given.fifa_player(name="Alex Sandro", nationality="Brazil", club="Juventus", overall=86)

        players.summarise_by_brazilian_club(nationality="Brazil")

        players.confirm_club_summary(club="Santos", players=2, average_overall=72)
        players.confirm_club_not_in_summary("Juventus")

    def should_combine_a_teams_results_with_its_squad(self, given, players):
        given.brasileirao_match(home="Gremio-RS", away="Santos-SP", score="2-0")
        given.fifa_player(name="Geromel", club="Grêmio", overall=84)

        players.team_profile(team="Grêmio")

        players.confirm_team_profile(wins=1, squad_includes="Geromel")
