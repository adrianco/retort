# Context: Behaviour scenarios for player search, filtering and club squads, run against the
# small fixture player file in conftest.py.

import pytest


def test_given_player_data_when_searching_by_partial_name_then_matching_players_are_returned_best_first(sample_kb):
    # Given the FIFA player data is loaded
    # When I search for "neymar"
    players = sample_kb.search_players("neymar")
    # Then Neymar Jr is returned with his overall rating and club
    assert [p.name for p in players] == ["Neymar Jr"]
    assert (players[0].overall, players[0].club) == (92, "Paris Saint-Germain")


def test_given_a_partial_name_when_searching_then_the_player_is_found(sample_kb):
    # Given a player with a nickname-style name in the data
    # When I search for a partial name
    players = sample_kb.search_players("gabi")
    # Then the player is found
    assert [p.name for p in players] == ["Gabigol"]


def test_given_nationality_and_position_when_filtering_then_forwards_from_brazil_are_returned_by_rating(sample_kb):
    # Given Brazilian and non-Brazilian players are loaded
    # When I list Brazilian forwards
    players = sample_kb.list_players(nationality="Brazil", position="forward")
    # Then only Brazilian forwards are returned, highest overall first
    assert [p.name for p in players] == ["Neymar Jr", "Gabriel Jesus", "Gabigol", "Pedro"]


def test_given_a_club_when_filtering_then_only_that_club_is_returned(sample_kb):
    # Given Flamengo has three players in the data
    # When I list players at Flamengo
    players = sample_kb.list_players(club="Flamengo")
    # Then all three are returned, ordered by overall then name
    assert [p.name for p in players] == ["Everton Ribeiro", "Gabigol", "Pedro"]


def test_given_a_club_name_when_building_profile_then_squad_size_and_average_rating_are_calculated(sample_kb):
    # Given Flamengo's three players in the player data
    # When I build the club profile
    club, squad = sample_kb.club_profile("Flamengo")
    # Then the squad has three players and the average overall is correct
    assert club == "Flamengo"
    assert len(squad) == 3
    assert sum(p.overall for p in squad) / len(squad) == pytest.approx(79.33, abs=0.01)


def test_given_a_long_club_name_when_building_profile_then_it_matches_the_short_name(sample_kb):
    # Given the club is recorded as "Sport Club do Recife"
    # When I ask for "Sport"
    _, squad = sample_kb.club_profile("Sport")
    # Then the squad is found through the normalized name
    assert [p.name for p in squad] == ["Pedro Henrique"]


def test_given_a_goalkeeper_position_when_filtering_then_only_goalkeepers_are_returned(sample_kb):
    # Given a goalkeeper in the data
    # When I filter by the goalkeeper position group
    players = sample_kb.list_players(position="goalkeeper")
    # Then only goalkeepers are returned
    assert [p.name for p in players] == ["Alisson"]
