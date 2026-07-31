"""BDD scenarios for tests/features/player_queries.feature."""

from __future__ import annotations

import pytest

from brazilian_soccer.queries import (
    QueryError,
    brazilian_players_by_club,
    club_squad,
    player_profile,
    search_players,
)
from tests.gwt import Scenario

pytestmark = pytest.mark.bdd


def test_find_all_brazilian_players(graph):
    with Scenario("Find all Brazilian players") as s:
        s.given("the player data is loaded", lambda: graph.players)
        result = s.when('I search for players with nationality "Brazil"',
                        lambda: search_players(nationality="Brazil", limit=500,
                                               graph=graph))
        s.then("I should receive more than 800 players",
               result["total_players"] > 800)
        s.and_("every player should be Brazilian",
               all(p["nationality"] == "Brazil" for p in result["players"]))
        s.and_("they should be sorted by overall rating, best first",
               all(result["players"][i]["overall"] >= result["players"][i + 1]["overall"]
                   for i in range(len(result["players"]) - 1)))
        s.and_("Neymar Jr should be the best rated",
               result["players"][0]["name"] == "Neymar Jr")


def test_find_a_player_by_name(graph):
    with Scenario("Find a player by name") as s:
        result = s.when('I look up "Neymar"',
                        lambda: player_profile("Neymar", graph=graph))
        player = result["player"]
        s.then("I should get Neymar Jr's FIFA profile",
               player["name"] == "Neymar Jr")
        s.and_("the profile should include position, club and overall rating",
               player["position"] == "LW" and player["club"] == "Paris Saint-Germain"
               and player["overall"] == 92)
        s.and_("skill attributes should be present",
               len(player["skills"]) > 20)
        s.and_("the FIFA 19 snapshot should be disclosed",
               any("FIFA 19" in note for note in result["notes"]))


def test_find_the_squad_of_a_brazilian_club(graph):
    with Scenario("Find the squad of a Brazilian club") as s:
        result = s.when('I ask for the squad of "Grêmio"',
                        lambda: club_squad("Grêmio", limit=50, graph=graph))
        s.then("I should receive a squad", result["squad_size"] == 20)
        s.and_("with an average rating", 60 < result["average_overall"] < 90)
        s.and_("every player should be registered to Grêmio",
               all(p["club_slug"] == "gremio" for p in result["players"]))
        s.and_("the squad should be ordered by rating",
               all(result["players"][i]["overall"] >= result["players"][i + 1]["overall"]
                   for i in range(len(result["players"]) - 1)))


def test_filter_players_by_position_group(graph):
    with Scenario("Filter players by position group") as s:
        result = s.when('I search for forwards at "Santos"',
                        lambda: search_players(club="Santos", position="FWD",
                                               limit=50, graph=graph))
        s.then("I should receive players", result["total_players"] > 0)
        s.and_("every returned player should play in a forward position",
               all(p["position_group"] == "FWD" for p in result["players"]))
        s.and_("every returned player should be at Santos",
               all(p["club_slug"] == "santos" for p in result["players"]))


def test_clubs_missing_from_fifa_19_are_reported_honestly(graph):
    with Scenario("Clubs missing from FIFA 19 are reported honestly") as s:
        result = s.when('I ask for the squad of "Flamengo"',
                        lambda: club_squad("Flamengo", graph=graph))
        s.then("the result should be empty", result["squad_size"] == 0)
        s.and_("it should explain that FIFA 19 did not license the club",
               any("FIFA 19" in note for note in result["notes"]))
        s.and_("the club should still resolve",
               result["club_slug"] == "flamengo")


def test_cross_file_query_joining_players_to_match_data(graph):
    with Scenario("Cross-file query joining players to match data") as s:
        result = s.when("I ask where Brazilian players play",
                        lambda: brazilian_players_by_club(limit=100, graph=graph))
        joined = result["at_clubs_present_in_match_data"]
        s.then("Brazilian players should be counted",
               result["total_brazilian_players"] > 800)
        s.and_("clubs that also appear in the match datasets should be flagged",
               len(joined) >= 10)
        s.and_("every flagged club should exist in the match graph",
               all(row["club_slug"] in graph.teams
                   and graph.matches_for(row["club_slug"]) for row in joined))
        s.and_("Grêmio should be one of them",
               any(row["club_slug"] == "gremio" for row in joined))


def test_foreign_namesakes_are_not_joined_to_brazilian_clubs(graph):
    with Scenario("Foreign namesakes are kept apart") as s:
        barcelona = s.when("I look at FC Barcelona's players",
                           lambda: [p for p in graph.players
                                    if p.club == "FC Barcelona"])
        s.then("FC Barcelona should not be joined to Barcelona-EQU",
               all(p.club_slug != "barcelona-equ" for p in barcelona))
        boavista = s.when("I look at Boavista FC's players",
                          lambda: [p for p in graph.players
                                   if p.club == "Boavista FC"])
        s.and_("Boavista FC should not be joined to Boavista-RJ",
               all(p.club_slug != "boavista-rj" for p in boavista))
        s.and_("but Santos really is the Brazilian Santos",
               all(p.club_slug == "santos" for p in graph.players
                   if p.club == "Santos"))


def test_a_club_name_never_matches_a_longer_word(graph):
    """"Nacional" is a substring of "Internacional" -- but not a token of it."""
    with Scenario("Club search matches whole words only") as s:
        result = s.when('I ask for the squad of "Nacional"',
                        lambda: club_squad("Nacional", limit=50, graph=graph))
        clubs = {p["club"] for p in result["players"]}
        s.then("no Internacional player should be returned",
               "Internacional" not in clubs)
        s.and_("exactly one club should be reported", len(clubs) == 1)
        s.and_("the reported club should be the one the players belong to",
               result["club"] in clubs)
        s.and_("the other candidates should be named, not blended in",
               "CD Nacional" in result["other_clubs_matching_the_name"])
        other = s.when('I ask for the squad of "River"',
                       lambda: club_squad("River", limit=5, graph=graph))
        s.and_("River finds River Plate, not River-PI",
               other["club"] == "River Plate" and other["squad_size"] > 0)


def test_clubs_only_in_the_fifa_file_still_resolve(graph):
    with Scenario("Clubs absent from the match data still return a squad") as s:
        for name, expected in [("Real Madrid", "Real Madrid"),
                               ("FC Barcelona", "FC Barcelona"),
                               ("Boavista FC", "Boavista FC")]:
            result = s.when(f'I ask for the squad of "{name}"',
                            lambda n=name: club_squad(n, limit=3, graph=graph))
            s.then(f"{expected} should be found",
                   result["club"] == expected and result["squad_size"] > 0)
            s.and_("the name-search caveat should be stated",
                   any("FIFA club column" in note for note in result["notes"]))


def test_unknown_player_gives_suggestions(graph):
    with Scenario("Unknown player gives suggestions") as s:
        with pytest.raises(QueryError) as excinfo:
            s.when("I look up a player who does not exist",
                   lambda: player_profile("Zzzz Nobody", graph=graph))
        s.then("the error should say the player is missing",
               "No player called" in str(excinfo.value))
