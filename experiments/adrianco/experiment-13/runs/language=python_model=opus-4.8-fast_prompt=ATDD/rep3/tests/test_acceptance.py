"""
Executable acceptance tests for the Brazilian Soccer MCP Server.

Each test is an executable specification of a requirement from TASK.md. They
are written from the perspective of an external user of the system, talk to the
server only through the published MCP tools, and assert on WHAT the system
answers in the language of the problem domain (matches, records, players,
standings) rather than on HOW it is implemented.

Every test is atomic and independent: the system under test is read-only over a
fixed dataset, so no test creates state that another test can observe.
"""

import time

import pytest


# --------------------------------------------------------------------------- #
# Protocol surface                                                            #
# --------------------------------------------------------------------------- #

EXPECTED_TOOLS = {
    "find_matches",
    "get_team_record",
    "compare_teams",
    "search_players",
    "get_standings",
    "get_competition_summary",
    "list_team_competitions",
    "get_team_profile",
}


def test_server_publishes_all_expected_tools(client):
    """An external client can discover the full toolset over the protocol."""
    tools = set(client.list_tools())
    missing = EXPECTED_TOOLS - tools
    assert not missing, f"server is missing tools: {missing}"


# --------------------------------------------------------------------------- #
# 1. Match queries                                                            #
# --------------------------------------------------------------------------- #

def test_find_matches_between_two_teams(client):
    """"Show me all Flamengo vs Fluminense matches" (the Fla-Flu derby)."""
    result = client.call("find_matches", team="Flamengo", opponent="Fluminense")

    assert result["count"] > 0
    # Every returned match must actually be between the two named teams.
    for m in result["matches"]:
        teams = {m["home_team"], m["away_team"]}
        assert any("Flamengo" in t for t in teams)
        assert any("Fluminense" in t for t in teams)

    h2h = result["head_to_head"]
    assert h2h is not None
    assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] == h2h["total"]
    assert h2h["total"] == result["count"]


def test_find_matches_by_team_and_season(client):
    """"What matches did Palmeiras play in 2019?\""""
    result = client.call("find_matches", team="Palmeiras", season=2019)

    assert result["count"] > 0
    for m in result["matches"]:
        assert m["season"] == 2019
        assert "Palmeiras" in m["home_team"] or "Palmeiras" in m["away_team"]


def test_find_matches_by_competition(client):
    """"Find Copa do Brasil matches" -- competition filtering."""
    result = client.call("find_matches", competition="Copa do Brasil", limit=25)

    assert result["count"] > 0
    for m in result["matches"]:
        assert m["competition"] == "Copa do Brasil"


def test_find_matches_by_date_range(client):
    """Matches can be filtered to a date window."""
    result = client.call(
        "find_matches", start_date="2019-01-01", end_date="2019-12-31", limit=100
    )
    assert result["count"] > 0
    for m in result["matches"]:
        assert "2019" in m["date"]


def test_find_matches_reports_a_readable_score(client):
    """A match answer includes a human-readable score line."""
    result = client.call("find_matches", team="Flamengo", season=2019, limit=5)
    assert result["matches"], "expected at least one Flamengo match in 2019"
    m = result["matches"][0]
    assert m["score"] == f"{m['home_goal']}-{m['away_goal']}"


# --------------------------------------------------------------------------- #
# 2. Team queries                                                             #
# --------------------------------------------------------------------------- #

def test_team_record_totals_are_consistent(client):
    """"What is Corinthians' record?" -- W/D/L must sum to matches played."""
    rec = client.call("get_team_record", team="Corinthians", season=2019)

    assert rec["matches"] == rec["wins"] + rec["draws"] + rec["losses"]
    assert rec["matches"] > 0
    assert 0.0 <= rec["win_rate"] <= 100.0
    assert rec["goals_for"] >= 0 and rec["goals_against"] >= 0


def test_team_home_record_is_subset_of_overall(client):
    """A home-only record never has more matches than the overall record."""
    overall = client.call("get_team_record", team="Corinthians", season=2019)
    home = client.call("get_team_record", team="Corinthians", season=2019, venue="home")

    assert home["venue"] == "home"
    assert home["matches"] <= overall["matches"]
    assert home["matches"] == home["wins"] + home["draws"] + home["losses"]


def test_compare_teams_head_to_head(client):
    """"Compare Palmeiras and Santos head-to-head\""""
    cmp = client.call("compare_teams", team_a="Palmeiras", team_b="Santos")

    assert cmp["total_matches"] > 0
    assert (
        cmp["team_a_wins"] + cmp["team_b_wins"] + cmp["draws"] == cmp["total_matches"]
    )


# --------------------------------------------------------------------------- #
# 3. Player queries                                                           #
# --------------------------------------------------------------------------- #

def test_search_player_by_name(client):
    """"Who is Neymar?" -- search the FIFA player data by name."""
    result = client.call("search_players", name="Neymar")

    assert result["count"] >= 1
    neymar = result["players"][0]
    assert "Neymar" in neymar["name"]
    assert neymar["nationality"] == "Brazil"
    assert neymar["overall"] == 92


def test_search_brazilian_players_sorted_by_rating(client):
    """"Find the top Brazilian players" -- filter by nationality, sort by rating."""
    result = client.call("search_players", nationality="Brazil", limit=10)

    assert result["count"] > 500  # the dataset has hundreds of Brazilians
    assert len(result["players"]) == 10
    overalls = [p["overall"] for p in result["players"]]
    assert overalls == sorted(overalls, reverse=True)
    assert all(p["nationality"] == "Brazil" for p in result["players"])
    assert result["players"][0]["name"].startswith("Neymar")


def test_search_players_by_club(client):
    """"Which players play for Santos?" -- filter FIFA data by club."""
    result = client.call("search_players", club="Santos", limit=50)

    assert result["count"] > 0
    for p in result["players"]:
        assert "Santos" in p["club"]


def test_search_players_by_position(client):
    """"Show me all strikers" -- filter players by playing position."""
    result = client.call("search_players", position="ST", limit=20)

    assert result["count"] > 0
    for p in result["players"]:
        assert p["position"] == "ST"


# --------------------------------------------------------------------------- #
# 4. Competition queries                                                      #
# --------------------------------------------------------------------------- #

def test_2019_brasileirao_standings(client):
    """"Who won the 2019 Brasileirão?" -- standings calculated from matches."""
    standings = client.call("get_standings", season=2019, competition="Brasileirão")

    assert standings["champion"] == "Flamengo"
    table = standings["table"]
    # 20-team league.
    assert len(table) == 20

    champ = table[0]
    assert champ["position"] == 1
    assert champ["team"] == "Flamengo"
    assert champ["points"] == 90
    assert champ["wins"] == 28
    assert champ["draws"] == 6
    assert champ["losses"] == 4
    assert champ["played"] == 38

    # Table is ordered by points (descending).
    points = [row["points"] for row in table]
    assert points == sorted(points, reverse=True)


def test_standings_each_row_is_internally_consistent(client):
    """Every standings row's W/D/L and points add up correctly."""
    standings = client.call("get_standings", season=2018, competition="Brasileirão")
    for row in standings["table"]:
        assert row["played"] == row["wins"] + row["draws"] + row["losses"]
        assert row["points"] == row["wins"] * 3 + row["draws"]
        assert row["goal_difference"] == row["goals_for"] - row["goals_against"]


# --------------------------------------------------------------------------- #
# 5. Statistical analysis                                                     #
# --------------------------------------------------------------------------- #

def test_competition_summary_average_goals(client):
    """"What's the average goals per match in the Brasileirão?\""""
    summary = client.call("get_competition_summary", competition="Brasileirão")

    assert summary["matches"] > 0
    # A plausible football average is somewhere between 1.5 and 4 goals/match.
    assert 1.5 <= summary["avg_goals_per_match"] <= 4.0
    assert 0.0 <= summary["home_win_rate"] <= 100.0
    assert summary["home_wins"] + summary["away_wins"] + summary["draws"] == summary["matches"]


def test_biggest_wins_are_ordered_by_margin(client):
    """"Show me the biggest wins" -- ranked by goal margin, descending."""
    summary = client.call("get_competition_summary", competition="Brasileirão")
    biggest = summary["biggest_wins"]

    assert len(biggest) > 0
    margins = [b["margin"] for b in biggest]
    assert margins == sorted(margins, reverse=True)
    top = biggest[0]
    assert top["margin"] == abs(top["home_goal"] - top["away_goal"])
    assert top["margin"] >= 4  # the largest blowouts are emphatic


# --------------------------------------------------------------------------- #
# Cross-file query (player data + match data)                                 #
# --------------------------------------------------------------------------- #

def test_team_profile_combines_matches_and_players(client):
    """A team profile joins match history (matches) with a squad (FIFA data)."""
    profile = client.call("get_team_profile", team="Santos")

    # Match side.
    assert profile["record"]["matches"] > 0
    # Player side -- Santos exists as a club in the FIFA dataset.
    squad = profile["squad"]
    assert squad["player_count"] > 0
    for p in squad["players"]:
        assert "Santos" in p["club"]


def test_list_team_competitions(client):
    """"What competitions has Palmeiras played in?" -- spans multiple files."""
    result = client.call("list_team_competitions", team="Palmeiras")
    names = {c["competition"] for c in result["competitions"]}
    assert "Brasileirão" in names
    for c in result["competitions"]:
        assert c["matches"] > 0


# --------------------------------------------------------------------------- #
# Data-quality requirements                                                   #
# --------------------------------------------------------------------------- #

def test_team_name_variations_are_normalized(client):
    """"Palmeiras-SP" and "Palmeiras" must resolve to the same team record."""
    with_suffix = client.call("get_team_record", team="Palmeiras-SP", season=2019)
    without_suffix = client.call("get_team_record", team="Palmeiras", season=2019)

    assert with_suffix["matches"] == without_suffix["matches"]
    assert with_suffix["points"] == without_suffix["points"]
    assert with_suffix["matches"] > 0


def test_accented_team_name_is_handled(client):
    """Accented names (e.g. "Grêmio") are matched regardless of accents."""
    accented = client.call("get_team_record", team="Grêmio", season=2019)
    plain = client.call("get_team_record", team="Gremio", season=2019)
    assert accented["matches"] == plain["matches"]
    assert accented["matches"] > 0


def test_unknown_team_returns_empty_record_gracefully(client):
    """Querying a team that does not exist returns an empty result, not an error."""
    rec = client.call("get_team_record", team="Nonexistent United FC")
    assert rec["matches"] == 0
    assert rec["wins"] == 0


# --------------------------------------------------------------------------- #
# Performance requirements                                                    #
# --------------------------------------------------------------------------- #

def test_simple_lookup_responds_quickly(client):
    """Simple lookups respond in well under 2 seconds."""
    start = time.perf_counter()
    client.call("find_matches", team="Flamengo", opponent="Corinthians")
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"simple lookup took {elapsed:.2f}s"


def test_aggregate_query_responds_quickly(client):
    """Aggregate queries respond in well under 5 seconds."""
    start = time.perf_counter()
    client.call("get_standings", season=2019, competition="Brasileirão")
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, f"aggregate query took {elapsed:.2f}s"
