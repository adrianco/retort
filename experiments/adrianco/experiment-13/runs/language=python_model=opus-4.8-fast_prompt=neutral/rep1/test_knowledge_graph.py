"""Tests for the KnowledgeGraph query engine.

These verify the analytical correctness required by the specification, using the
documented 2019 Brasileirão example as a ground-truth anchor (Flamengo champion
with 90 pts, 28W-6D-4L; Santos and Palmeiras on 74).
"""

import time


# --------------------------------------------------------------------------- #
# Competition standings (the strongest correctness signal)
# --------------------------------------------------------------------------- #
def test_2019_brasileirao_standings_match_known_result(kg):
    table = kg.standings("Série A", 2019)
    assert len(table) == 20, "Série A is a 20-team league"
    champ = table[0]
    assert champ["team"].startswith("Flamengo")
    assert champ["points"] == 90
    assert (champ["wins"], champ["draws"], champ["losses"]) == (28, 6, 4)
    # Every team must have played the full 38-round double round-robin.
    assert all(r["played"] == 38 for r in table)


def test_standings_have_consistent_totals(kg):
    # Across the whole table, wins == losses and points == 3*W + D.
    table = kg.standings("Série A", 2019)
    total_wins = sum(r["wins"] for r in table)
    total_losses = sum(r["losses"] for r in table)
    assert total_wins == total_losses
    for r in table:
        assert r["points"] == 3 * r["wins"] + r["draws"]
        assert r["played"] == r["wins"] + r["draws"] + r["losses"]


def test_overlapping_sources_do_not_double_count(kg):
    # 2019 Série A appears in 3 source files; dedup must keep a single one.
    champ = kg.champion("Série A", 2019)
    assert champ["played"] == 38  # not 76 or 114


def test_champion_helper(kg):
    assert kg.champion("Série A", 2019)["team"].startswith("Flamengo")


def test_every_serie_a_season_is_a_clean_round_robin(kg):
    """Regression guard: the BR-Football-Dataset groups matches by calendar
    year, so the COVID-delayed 2020 season spills into 2021 (24 teams / 49
    games).  Source selection must reject that, leaving every season a sane
    single round-robin with no inflated game counts."""
    for year in kg.list_seasons("Série A"):
        table = kg.standings("Série A", year)
        n_teams = len(table)
        assert 16 <= n_teams <= 24, f"{year}: implausible team count {n_teams}"
        full_schedule = (n_teams - 1) * 2  # double round-robin
        assert max(r["played"] for r in table) <= full_schedule, (
            f"{year}: a team played more than {full_schedule} games"
        )


def test_2021_champion_is_atletico_mineiro(kg):
    # Real-world check that depends on the calendar-year fix being correct.
    champ = kg.champion("Série A", 2021)
    assert champ["played"] == 38
    assert "Atletico" in champ["team"]  # Atlético-MG / Atletico Mineiro


# --------------------------------------------------------------------------- #
# Match queries
# --------------------------------------------------------------------------- #
def test_find_matches_by_team_and_season(kg):
    matches = kg.find_matches(team="Palmeiras", season=2019, competition="Série A")
    assert len(matches) == 38
    assert all(
        "palmeiras" in (m["home_team"] + m["away_team"]).lower() for m in matches
    )
    # Sorted most-recent-first.
    dates = [m["date"] for m in matches if m["date"]]
    assert dates == sorted(dates, reverse=True)


def test_find_matches_between_two_teams(kg):
    matches = kg.find_matches(team="Flamengo", opponent="Fluminense")
    assert len(matches) > 0
    for m in matches:
        teams = (m["home_team"] + m["away_team"]).lower()
        assert "flamengo" in teams and "fluminense" in teams


def test_find_matches_date_range(kg):
    matches = kg.find_matches(
        team="Corinthians", start_date="2019-01-01", end_date="2019-12-31"
    )
    assert matches
    assert all("2019" == m["date"][:4] for m in matches if m["date"])


def test_head_to_head_symmetry(kg):
    h1 = kg.head_to_head("Flamengo", "Fluminense")
    h2 = kg.head_to_head("Fluminense", "Flamengo")
    assert h1["total_matches"] == h2["total_matches"]
    assert h1["team1_wins"] == h2["team2_wins"]
    assert h1["draws"] == h2["draws"]
    # Wins + draws account for every match with a result.
    assert h1["team1_wins"] + h1["team2_wins"] + h1["draws"] <= h1["total_matches"]


# --------------------------------------------------------------------------- #
# Team records
# --------------------------------------------------------------------------- #
def test_team_record_home_only(kg):
    rec = kg.team_record("Corinthians", season=2022, competition="Série A", venue="home")
    assert rec["played"] == 19  # half of a 38-game season at home
    assert rec["wins"] + rec["draws"] + rec["losses"] == rec["played"]
    assert 0 <= rec["win_rate"] <= 100


def test_team_record_home_plus_away_equals_all(kg):
    home = kg.team_record("Palmeiras", season=2019, competition="Série A", venue="home")
    away = kg.team_record("Palmeiras", season=2019, competition="Série A", venue="away")
    allv = kg.team_record("Palmeiras", season=2019, competition="Série A", venue="all")
    assert home["played"] + away["played"] == allv["played"]
    assert home["wins"] + away["wins"] == allv["wins"]
    assert home["goals_for"] + away["goals_for"] == allv["goals_for"]


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def test_average_goals_reasonable(kg):
    stats = kg.average_goals(competition="Série A")
    assert stats["matches"] > 1000
    assert 2.0 <= stats["avg_goals_per_match"] <= 3.5
    rates = stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"]
    assert abs(rates - 100) < 0.5
    assert stats["home_win_rate"] > stats["away_win_rate"]  # home advantage


def test_biggest_wins_sorted_by_margin(kg):
    wins = kg.biggest_wins(competition="Libertadores", limit=5)
    margins = [w["margin"] for w in wins]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 5


def test_top_scoring_teams(kg):
    top = kg.top_scoring_teams("Série A", 2019, limit=3)
    assert len(top) == 3
    goals = [t["goals_for"] for t in top]
    assert goals == sorted(goals, reverse=True)


# --------------------------------------------------------------------------- #
# Player queries
# --------------------------------------------------------------------------- #
def test_top_brazilian_player_is_neymar(kg):
    players = kg.search_players(nationality="Brazil", limit=5)
    assert players[0]["name"].startswith("Neymar")
    assert all(p["nationality"] == "Brazil" for p in players)
    overalls = [p["overall"] for p in players]
    assert overalls == sorted(overalls, reverse=True)


def test_search_players_by_club_and_position(kg):
    gks = kg.search_players(club="Santos", position="GK")
    assert gks  # Santos had goalkeepers in the FIFA data
    assert all(p["position"] == "GK" for p in gks)


def test_search_players_min_overall(kg):
    elite = kg.search_players(nationality="Brazil", min_overall=85)
    assert elite
    assert all(p["overall"] >= 85 for p in elite)


def test_get_player_by_name(kg):
    p = kg.get_player("Neymar")
    assert p is not None and "Neymar" in p["name"]
    assert kg.get_player("ZZZ no such player") is None


def test_brazilian_players_by_club(kg):
    rows = kg.brazilian_players_by_club(limit=10)
    assert rows
    counts = [r["players"] for r in rows]
    assert counts == sorted(counts, reverse=True)
    assert all(0 <= r["avg_overall"] <= 99 for r in rows)


# --------------------------------------------------------------------------- #
# Discovery + performance
# --------------------------------------------------------------------------- #
def test_discovery_helpers(kg):
    comps = kg.list_competitions()
    assert "Brasileirão Série A" in comps
    assert 2019 in kg.list_seasons("Série A")
    teams_2019 = kg.list_teams("Série A", 2019)
    assert len(teams_2019) == 20


def test_simple_lookup_under_2s(kg):
    start = time.time()
    kg.find_matches(team="Flamengo", opponent="Corinthians")
    assert time.time() - start < 2.0


def test_aggregate_query_under_5s(kg):
    start = time.time()
    kg.standings("Série A", 2019)
    kg.average_goals(competition="Série A")
    assert time.time() - start < 5.0
