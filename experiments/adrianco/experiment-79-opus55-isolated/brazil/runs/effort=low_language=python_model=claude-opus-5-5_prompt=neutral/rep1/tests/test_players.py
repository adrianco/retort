"""Feature: Player queries over the FIFA database."""

import pytest

from brazilian_soccer import QueryError


def test_search_player_by_name_ignores_accents_and_case(db):
    found = db.search_players(name="neymar")
    assert found["players"][0]["name"] == "Neymar Jr"
    assert found["players"][0]["club"] == "Paris Saint-Germain"
    assert db.search_players(name="COUTINHO")["total"] >= 1


def test_all_brazilian_players(db):
    # "Find all Brazilian players in the dataset" / "Who are the top Brazilian players?"
    found = db.search_players(nationality="Brazil", limit=5)
    assert found["total"] == 827
    assert found["players"][0]["name"] == "Neymar Jr"
    overalls = [p["overall"] for p in found["players"]]
    assert overalls == sorted(overalls, reverse=True)
    assert db.search_players(nationality="brasil")["total"] == 827


def test_players_at_a_brazilian_club(db):
    found = db.search_players(club="Grêmio", limit=50)
    assert found["total"] == len(found["players"]) > 10
    assert {p["club"] for p in found["players"]} == {"Grêmio"}
    # a different spelling of the same club gives the same squad
    assert db.search_players(club="Gremio-RS", limit=50) == found


def test_club_filter_does_not_leak_to_similarly_named_clubs(db):
    clubs = {p["club"] for p in db.search_players(club="Santos", limit=200)["players"]}
    assert clubs == {"Santos"}  # not "Santos Laguna"


def test_filter_by_position_group_and_code(db):
    forwards = db.search_players(club="Santos", position="forwards", limit=50)["players"]
    assert forwards and all(p["position"] in {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"}
                            for p in forwards)
    keepers = db.search_players(nationality="Brazil", position="GK", limit=5)["players"]
    assert keepers and all(p["position"] == "GK" for p in keepers)


def test_filter_by_rating_and_age(db):
    found = db.search_players(nationality="Brazil", min_overall=85, max_age=27, limit=50)
    assert found["players"]
    assert all(p["overall"] >= 85 and p["age"] <= 27 for p in found["players"])


def test_brazilian_players_grouped_by_brazilian_club(db):
    rows = db.players_by_club(nationality="Brazil")
    assert rows and rows[0]["players"] >= rows[-1]["players"]
    assert {"Grêmio", "Santos", "Cruzeiro"} <= {r["club"] for r in rows}
    assert all(50 < r["average_overall"] < 90 for r in rows)


def test_cross_file_team_profile_links_matches_and_players(db):
    # Cross-file query: match history (match CSVs) + squad (FIFA CSV)
    profile = db.team_profile("Gremio", season=2018)
    assert profile["team"] == "Grêmio" and profile["state"] == "RS"
    assert profile["stats"]["matches"] > 38
    assert profile["squad"]["total"] > 10
    # A club that FIFA does not license has matches but no squad
    assert db.team_profile("Flamengo")["squad"]["total"] == 0


def test_no_match_and_bad_sort(db):
    assert db.search_players(name="zzzz no such player")["total"] == 0
    with pytest.raises(QueryError):
        db.search_players(sort_by="salary")
