"""
Context
=======
Executable acceptance specification for the Brazilian Soccer MCP Server.

Every requirement / acceptance criterion in TASK.md is translated here into an
automated scenario written from the perspective of an external MCP client. The
scenarios talk in the language of the problem domain — "find matches between two
teams", "get a team's record", "calculate the standings", "search players" —
and assert on WHAT the server returns, never on HOW it computes it. The only
contact with the system is through MCP tool calls.

Each test seeds its own small, controlled dataset so outcomes are deterministic
and no test shares data with another.
"""

import pytest

from tests.conftest import call, call_expecting_error

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# A small, deterministic 3-team Brasileirão season used by several scenarios.
# Flamengo finishes on 8 pts, Palmeiras 5, Fluminense 3.
# ---------------------------------------------------------------------------
def seed_mini_league(dataset):
    dataset.brasileirao([
        {"datetime": "2023-04-15 16:00:00", "home_team": "Flamengo-RJ",
         "home_state": "RJ", "away_team": "Fluminense-RJ", "away_state": "RJ",
         "home_goal": 2, "away_goal": 1, "season": 2023, "round": 1},
        {"datetime": "2023-04-22 18:30:00", "home_team": "Palmeiras-SP",
         "home_state": "SP", "away_team": "Flamengo-RJ", "away_state": "RJ",
         "home_goal": 0, "away_goal": 0, "season": 2023, "round": 2},
        {"datetime": "2023-04-29 16:00:00", "home_team": "Fluminense-RJ",
         "home_state": "RJ", "away_team": "Palmeiras-SP", "away_state": "SP",
         "home_goal": 1, "away_goal": 0, "season": 2023, "round": 3},
        {"datetime": "2023-08-12 21:00:00", "home_team": "Fluminense-RJ",
         "home_state": "RJ", "away_team": "Flamengo-RJ", "away_state": "RJ",
         "home_goal": 1, "away_goal": 3, "season": 2023, "round": 4},
        {"datetime": "2023-08-19 16:00:00", "home_team": "Flamengo-RJ",
         "home_state": "RJ", "away_team": "Palmeiras-SP", "away_state": "SP",
         "home_goal": 1, "away_goal": 1, "season": 2023, "round": 5},
        {"datetime": "2023-08-26 18:30:00", "home_team": "Palmeiras-SP",
         "home_state": "SP", "away_team": "Fluminense-RJ", "away_state": "RJ",
         "home_goal": 2, "away_goal": 0, "season": 2023, "round": 6},
    ])


# ===========================================================================
# Tool discovery
# ===========================================================================
async def test_server_advertises_its_capabilities(client):
    tools = await client.list_tools()
    names = {t.name for t in tools.tools}
    assert {
        "find_matches",
        "get_team_record",
        "head_to_head",
        "search_players",
        "get_standings",
        "get_competition_stats",
    }.issubset(names)


# ===========================================================================
# 1. Match Queries
# ===========================================================================
async def test_find_all_matches_between_two_teams(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "find_matches",
                        team="Flamengo", opponent="Fluminense")

    assert result["count"] == 2
    pairs = {(m["home_team"], m["away_team"]) for m in result["matches"]}
    assert ("Flamengo", "Fluminense") in pairs
    assert ("Fluminense", "Flamengo") in pairs


async def test_find_matches_reports_head_to_head_when_two_teams_given(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "find_matches",
                        team="Flamengo", opponent="Fluminense")

    h2h = result["head_to_head"]
    # Flamengo won both meetings (2-1 and away 3-1).
    assert h2h["team1_wins"] == 2
    assert h2h["team2_wins"] == 0
    assert h2h["draws"] == 0


async def test_find_matches_for_a_single_team_returns_all_its_games(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "find_matches", team="Flamengo")

    assert result["count"] == 4
    for m in result["matches"]:
        assert "Flamengo" in (m["home_team"], m["away_team"])


async def test_find_matches_filtered_by_season(client, dataset):
    seed_mini_league(dataset)
    dataset.libertadores([
        {"datetime": "2022-04-05 19:15:00", "home_team": "Flamengo",
         "away_team": "Nacional (URU)", "home_goal": 3, "away_goal": 1,
         "season": 2022, "stage": "group stage"},
    ])

    result = await call(client, "find_matches", team="Flamengo", season=2023)

    assert result["count"] == 4
    assert all(m["season"] == 2023 for m in result["matches"])


async def test_find_matches_filtered_by_competition(client, dataset):
    seed_mini_league(dataset)
    dataset.libertadores([
        {"datetime": "2023-04-05 19:15:00", "home_team": "Flamengo",
         "away_team": "Nacional (URU)", "home_goal": 3, "away_goal": 1,
         "season": 2023, "stage": "group stage"},
    ])

    result = await call(client, "find_matches",
                        team="Flamengo", competition="Libertadores")

    assert result["count"] == 1
    assert result["matches"][0]["away_team"] == "Nacional"
    assert "Libertadores" in result["matches"][0]["competition"]


async def test_find_matches_filtered_by_date_range(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "find_matches", team="Flamengo",
                        start_date="2023-08-01", end_date="2023-08-31")

    assert result["count"] == 2
    for m in result["matches"]:
        assert m["date"] >= "2023-08-01"
        assert m["date"] <= "2023-08-31"


async def test_team_name_variations_are_normalized(client, dataset):
    # The same team appears with a state suffix and a country suffix.
    dataset.brasileirao([
        {"datetime": "2023-05-01 16:00:00", "home_team": "São Paulo-SP",
         "home_state": "SP", "away_team": "Grêmio-RS", "away_state": "RS",
         "home_goal": 2, "away_goal": 0, "season": 2023, "round": 1},
    ])

    # Query without the suffix and without accents still finds the match.
    result = await call(client, "find_matches", team="Sao Paulo")

    assert result["count"] == 1
    assert result["matches"][0]["home_team"] == "São Paulo"


# ===========================================================================
# 2. Team Queries
# ===========================================================================
async def test_team_record_for_a_season(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "get_team_record", team="Flamengo", season=2023)

    assert result["matches"] == 4
    assert result["wins"] == 2
    assert result["draws"] == 2
    assert result["losses"] == 0
    assert result["goals_for"] == 6
    assert result["goals_against"] == 3
    assert result["win_rate"] == pytest.approx(50.0, abs=0.1)


async def test_team_home_record_only(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "get_team_record",
                        team="Flamengo", season=2023, home_away="home")

    # Home games: 2-1 vs Fluminense (W) and 1-1 vs Palmeiras (D).
    assert result["matches"] == 2
    assert result["wins"] == 1
    assert result["draws"] == 1
    assert result["losses"] == 0
    assert result["goals_for"] == 3
    assert result["goals_against"] == 2


async def test_head_to_head_between_two_teams(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "head_to_head", team1="Palmeiras", team2="Fluminense")

    # Fluminense 1-0 Palmeiras, Palmeiras 2-0 Fluminense -> one win each.
    assert result["total_matches"] == 2
    assert result["team1_wins"] == 1   # Palmeiras
    assert result["team2_wins"] == 1   # Fluminense
    assert result["draws"] == 0


# ===========================================================================
# 3. Player Queries
# ===========================================================================
def seed_players(dataset):
    dataset.fifa_players([
        {"name": "Neymar Jr", "nationality": "Brazil", "overall": 92,
         "potential": 92, "club": "Paris Saint-Germain", "position": "LW", "age": 31},
        {"name": "Gabriel Barbosa", "nationality": "Brazil", "overall": 83,
         "potential": 85, "club": "Flamengo", "position": "ST", "age": 26},
        {"name": "Bruno Henrique", "nationality": "Brazil", "overall": 80,
         "potential": 80, "club": "Flamengo", "position": "LW", "age": 32},
        {"name": "Dudu", "nationality": "Brazil", "overall": 79,
         "potential": 79, "club": "Palmeiras", "position": "RM", "age": 31},
        {"name": "L. Messi", "nationality": "Argentina", "overall": 94,
         "potential": 94, "club": "FC Barcelona", "position": "RF", "age": 31},
    ])


async def test_search_players_by_name(client, dataset):
    seed_players(dataset)

    result = await call(client, "search_players", name="Gabriel")

    assert result["count"] == 1
    assert result["players"][0]["name"] == "Gabriel Barbosa"
    assert result["players"][0]["club"] == "Flamengo"


async def test_find_brazilian_players_sorted_by_rating(client, dataset):
    seed_players(dataset)

    result = await call(client, "search_players", nationality="Brazil")

    names = [p["name"] for p in result["players"]]
    assert names == ["Neymar Jr", "Gabriel Barbosa", "Bruno Henrique", "Dudu"]
    assert all(p["nationality"] == "Brazil" for p in result["players"])


async def test_highest_rated_players_at_a_club(client, dataset):
    seed_players(dataset)

    result = await call(client, "search_players", club="Flamengo")

    assert result["count"] == 2
    assert result["players"][0]["name"] == "Gabriel Barbosa"  # higher overall


async def test_search_players_filtered_by_minimum_rating(client, dataset):
    seed_players(dataset)

    result = await call(client, "search_players",
                        nationality="Brazil", min_overall=80)

    names = [p["name"] for p in result["players"]]
    assert names == ["Neymar Jr", "Gabriel Barbosa", "Bruno Henrique"]


# ===========================================================================
# 4. Competition Queries
# ===========================================================================
async def test_season_standings_are_calculated_from_matches(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "get_standings", season=2023, competition="Brasileirão")

    table = result["standings"]
    assert [row["team"] for row in table] == ["Flamengo", "Palmeiras", "Fluminense"]
    assert [row["points"] for row in table] == [8, 5, 3]
    assert table[0]["position"] == 1
    assert result["champion"] == "Flamengo"

    flamengo = table[0]
    assert flamengo["played"] == 4
    assert flamengo["wins"] == 2
    assert flamengo["draws"] == 2
    assert flamengo["losses"] == 0
    assert flamengo["goal_difference"] == 3


# ===========================================================================
# 5. Statistical Analysis
# ===========================================================================
async def test_competition_statistics(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "get_competition_stats",
                        competition="Brasileirão", season=2023)

    assert result["matches"] == 6
    # 12 goals across 6 matches.
    assert result["average_goals_per_match"] == pytest.approx(2.0, abs=0.01)
    # 3 of 6 matches won by the home side.
    assert result["home_win_rate"] == pytest.approx(50.0, abs=0.1)


async def test_biggest_wins_are_reported(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "get_competition_stats",
                        competition="Brasileirão", season=2023)

    biggest = result["biggest_wins"][0]
    # Largest goal margin in the seeded league is 2.
    assert abs(biggest["home_goal"] - biggest["away_goal"]) == 2


# ===========================================================================
# Cross-file coverage: every dataset is loadable and queryable
# ===========================================================================
async def test_matches_are_found_across_all_competition_files(client, dataset):
    dataset.brasileirao([
        {"datetime": "2023-05-01 16:00:00", "home_team": "Santos-SP",
         "home_state": "SP", "away_team": "Corinthians-SP", "away_state": "SP",
         "home_goal": 1, "away_goal": 0, "season": 2023, "round": 1},
    ])
    dataset.copa_do_brasil([
        {"round": "Final", "datetime": "2023-09-24 16:00:00",
         "home_team": "São Paulo", "away_team": "Flamengo",
         "home_goal": 1, "away_goal": 1, "season": 2023},
    ])
    dataset.libertadores([
        {"datetime": "2023-06-01 19:15:00", "home_team": "Palmeiras",
         "away_team": "Boca Juniors (ARG)", "home_goal": 2, "away_goal": 1,
         "season": 2023, "stage": "knockout"},
    ])
    dataset.br_football([
        {"tournament": "Copa do Brasil", "home": "Sao Paulo", "home_goal": 1.0,
         "away_goal": 1.0, "away": "Flamengo", "date": "2023-09-24"},
    ])
    dataset.historical([
        {"data": "29/03/2003", "ano": 2003, "rodada": 1,
         "home_team": "Guarani", "away_team": "Vasco", "home_goal": 4,
         "away_goal": 2, "winner": "Mandante", "arena": "Brinco de Ouro"},
    ])

    # A match from the historical (DD/MM/YYYY) file is queryable.
    historical = await call(client, "find_matches", team="Guarani", season=2003)
    assert historical["count"] == 1
    assert historical["matches"][0]["date"] == "2003-03-29"

    # A Libertadores match with a country-suffixed opponent is queryable.
    liberta = await call(client, "find_matches",
                         team="Palmeiras", competition="Libertadores")
    assert liberta["count"] == 1
    assert liberta["matches"][0]["away_team"] == "Boca Juniors"

    # A Copa do Brasil final is queryable.
    cup = await call(client, "find_matches",
                     team="São Paulo", competition="Copa do Brasil")
    assert cup["count"] >= 1


# ===========================================================================
# Robustness
# ===========================================================================
async def test_unknown_team_returns_no_matches_not_an_error(client, dataset):
    seed_mini_league(dataset)

    result = await call(client, "find_matches", team="Nonexistent United")

    assert result["count"] == 0
    assert result["matches"] == []


async def test_team_record_requires_a_team_name(client, dataset):
    seed_mini_league(dataset)

    message = await call_expecting_error(client, "get_team_record", team="")
    assert "team" in message.lower()
