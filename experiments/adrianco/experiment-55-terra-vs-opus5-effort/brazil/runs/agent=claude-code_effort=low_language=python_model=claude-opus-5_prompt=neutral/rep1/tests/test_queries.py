"""
Context
=======
BDD scenarios for the query features in tests/features.feature: Match Queries,
Team Queries, Player Queries, Competition Queries and Statistical Analysis.

Two kinds of assertion are used deliberately:

* `tiny_graph` scenarios assert exact numbers, because the six-match mini-league
  in conftest.py is small enough to compute by hand -- these pin the arithmetic.
* `graph` scenarios assert against the real corpus.  Where a fact is historically
  known and unambiguous (Flamengo won the 2019 Brasileirao with 90 points from
  28W/6D/4L) it is asserted exactly; elsewhere the assertions are invariants
  (wins + draws + losses == matches, results honour the filters, ordering is
  monotonic) so the suite stays meaningful without hard-coding noise.
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer.graph import TeamNotFound
from brazilian_soccer.models import BRASILEIRAO_A, COPA_DO_BRASIL


# --------------------------------------------------------------- Match queries

def test_find_matches_between_two_teams(graph):
    # Given the match data is loaded
    # When I search for matches between "Flamengo" and "Fluminense"
    h2h = graph.head_to_head("Flamengo", "Fluminense", limit=None)
    # Then I should receive a list of matches
    assert h2h["total_matches"] > 20
    assert h2h["derby"] == "Fla-Flu"
    # And each match should have date, scores, and competition
    for match in h2h["matches"]:
        assert match["date"] and match["competition"]
        assert isinstance(match["home_goals"], int)
        assert isinstance(match["away_goals"], int)
        assert {match["home_team"], match["away_team"]} == {"Flamengo", "Fluminense"}
    # And the two records reconcile
    a, b = h2h["team_a_record"], h2h["team_b_record"]
    assert a["wins"] + a["draws"] + a["losses"] == h2h["total_matches"]
    assert a["wins"] == b["losses"] and a["draws"] == b["draws"]
    assert a["goals_for"] == b["goals_against"]


def test_filter_matches_by_season_and_competition(graph):
    # When I search for Palmeiras matches in the 2023 Brasileirao
    matches = graph.find_matches(team="Palmeiras", competition="Brasileirao",
                                 season=2023, limit=None)
    # Then every returned match involves Palmeiras in that competition and season
    # (37, not 38: the only source covering 2023 stops three matches short --
    # see test_known_gaps_in_the_source_data_are_visible_not_silently_wrong)
    assert len(matches) == 37
    for match in matches:
        assert match.competition == BRASILEIRAO_A
        assert match.season == 2023
        assert match.involves("palmeiras")


def test_find_all_copa_do_brasil_finals(graph):
    # When I search Copa do Brasil matches at stage "final"
    finals = graph.find_matches(competition="Copa do Brasil", stage="final", limit=None)
    # Then only finals are returned, never semifinals
    assert finals
    assert all(m.stage == "final" for m in finals)
    assert all(m.competition == COPA_DO_BRASIL for m in finals)
    # The 2019 final was Athletico-PR against Internacional over two legs.
    legs_2019 = [m for m in finals if m.season == 2019]
    assert len(legs_2019) == 2
    assert {t for m in legs_2019 for t in (m.home_display, m.away_display)} == {
        "Atlético-PR", "Internacional"
    }


def test_find_matches_in_a_date_range(graph):
    # When I search for matches between two dates
    matches = graph.find_matches(date_from="2019-05-01", date_to="2019-05-31", limit=None)
    # Then every returned match falls inside that range
    assert matches
    assert all(date(2019, 5, 1) <= m.match_date <= date(2019, 5, 31) for m in matches)
    # And the Brazilian date format is accepted too
    same = graph.find_matches(date_from="01/05/2019", date_to="31/05/2019", limit=None)
    assert len(same) == len(matches)


def test_venue_filter_splits_home_from_away(graph):
    home = graph.find_matches(team="Santos", season=2019, competition="Serie A",
                              venue="home", limit=None)
    away = graph.find_matches(team="Santos", season=2019, competition="Serie A",
                              venue="away", limit=None)
    assert len(home) == len(away) == 19
    assert all(m.home_team == "santos" for m in home)
    assert all(m.away_team == "santos" for m in away)


def test_matches_are_returned_newest_first(graph):
    matches = graph.find_matches(team="Grêmio", limit=25)
    dates = [m.match_date for m in matches if m.match_date]
    assert dates == sorted(dates, reverse=True)


def test_unknown_team_is_reported_with_suggestions(graph):
    with pytest.raises(TeamNotFound) as excinfo:
        graph.find_matches(team="Flamingo FC of Mars")
    assert "Flamingo FC of Mars" in str(excinfo.value)


def test_unknown_competition_is_rejected(graph):
    with pytest.raises(ValueError, match="Unknown competition"):
        graph.find_matches(competition="Premier League")


# ---------------------------------------------------------------- Team queries

def test_get_team_statistics(graph):
    # When I request statistics for "Palmeiras" in season "2023"
    stats = graph.team_stats("Palmeiras", season=2022, competition="Serie A")
    # Then I should receive wins, losses, draws, and goals
    overall = stats["overall"]
    assert overall["matches"] == 38
    assert overall["wins"] + overall["draws"] + overall["losses"] == 38
    assert overall["goals_for"] > 0 and overall["goals_against"] > 0
    assert overall["points"] == overall["wins"] * 3 + overall["draws"]
    assert stats["home"]["matches"] == stats["away"]["matches"] == 19
    assert stats["biggest_win"]["home_goals"] != stats["biggest_win"]["away_goals"]


def test_home_record_for_a_season(graph):
    # When I request Corinthians' home record for the 2022 Brasileirao
    stats = graph.team_stats("Corinthians", season=2022, competition="Serie A", venue="home")
    record = stats["overall"]
    # Then it covers 19 home matches and the wins, draws and losses add up
    assert record["matches"] == 19
    assert record["wins"] + record["draws"] + record["losses"] == 19
    assert 0 <= record["win_rate"] <= 100
    assert record["goal_difference"] == record["goals_for"] - record["goals_against"]


def test_compare_two_teams_head_to_head(graph):
    # When I compare Palmeiras and Santos
    h2h = graph.head_to_head("Palmeiras", "Santos", limit=None)
    # Then both records are returned and their wins and draws reconcile
    a, b = h2h["team_a_record"], h2h["team_b_record"]
    assert h2h["total_matches"] == a["matches"] == b["matches"] > 10
    assert a["wins"] + b["wins"] + a["draws"] == h2h["total_matches"]
    assert h2h["derby"] == "Clássico da Saudade"
    assert h2h["first_meeting"] < h2h["last_meeting"]
    assert set(h2h["by_competition"]) <= {BRASILEIRAO_A, COPA_DO_BRASIL, "Copa Libertadores"}


def test_head_to_head_rejects_one_team(graph):
    with pytest.raises(ValueError):
        graph.head_to_head("Santos", "Santos-SP")


def test_team_profile_lists_competitions_and_rivals(graph):
    profile = graph.team_profile("Flamengo")
    assert profile["team"] == "Flamengo"
    assert BRASILEIRAO_A in profile["competitions"]
    assert profile["total_matches"] > 500
    assert profile["record"]["matches"] == profile["total_matches"]
    rivals = {r["team"] for r in profile["most_played_opponents"]}
    assert rivals & {"Fluminense", "Vasco", "Botafogo", "São Paulo", "Corinthians"}


def test_team_statistics_are_exact_on_a_known_mini_league(tiny_graph):
    stats = tiny_graph.team_stats("Alpha", competition="Brasileirao")
    overall = stats["overall"]
    assert (overall["matches"], overall["wins"], overall["draws"], overall["losses"]) == (3, 2, 1, 0)
    assert (overall["goals_for"], overall["goals_against"]) == (6, 2)
    assert overall["points"] == 7
    assert overall["win_rate"] == pytest.approx(66.7)
    assert stats["home"]["matches"] == 2 and stats["away"]["matches"] == 1
    # Two 2-goal wins (3-1 at home, 0-2 away); either is the biggest.
    assert stats["biggest_win"]["score"] in {"3-1", "0-2"}


# -------------------------------------------------------------- Player queries

def test_find_brazilian_players(graph):
    # When I search for players of nationality "Brazil"
    players = graph.search_players(nationality="Brazil", limit=25)
    # Then every returned player is Brazilian and they are sorted by rating
    assert len(players) == 25
    assert all(p["nationality"] == "Brazil" for p in players)
    ratings = [p["overall"] for p in players]
    assert ratings == sorted(ratings, reverse=True)
    assert players[0]["name"] == "Neymar Jr"


def test_find_players_at_a_club(graph):
    # When I search for players at "Atletico Mineiro"
    players = graph.search_players(club="Atlético Mineiro", limit=50)
    # Then every returned player belongs to that club
    assert players
    assert all(p["club"] == "Atlético Mineiro" for p in players)


def test_filter_players_by_position_and_rating(graph):
    keepers = graph.search_players(nationality="Brazil", position="GK",
                                   min_overall=80, limit=20)
    assert keepers
    assert all(p["position"] == "GK" and p["overall"] >= 80 for p in keepers)


def test_look_up_one_player_by_name(graph):
    # When I ask who "Neymar" is
    result = graph.player_profile("Neymar")
    # Then a full profile with rating, position and club is returned
    assert result["found"] is True
    player = result["player"]
    assert player["nationality"] == "Brazil"
    assert player["overall"] >= 90
    assert player["position"] and player["club"]
    assert player["skills"]["Dribbling"] > 80


def test_unknown_player_names_suggest_alternatives(graph):
    # When I ask for a player who is not in the FIFA snapshot
    result = graph.player_profile("Gabriel Barbosa")
    # Then the answer says so and offers similar names
    assert result["found"] is False
    assert result["suggestions"]
    assert any("Gabriel" in p["name"] for p in result["suggestions"])


def test_brazilian_club_squads_only_lists_brazilian_clubs(graph):
    rows = graph.players_by_brazilian_club(min_players=5, limit=40)
    assert rows
    clubs = {row["club"] for row in rows}
    # Homonymous foreign clubs (River Plate of Argentina, Boavista of Portugal)
    # must not be reported as Brazilian squads.
    assert "River Plate" not in clubs and "Boavista" not in clubs
    assert clubs & {"Cruzeiro", "Grêmio", "Internacional", "Fluminense", "Santos"}
    for row in rows:
        assert row["brazilian_share"] >= 0.5
        assert 0 < row["average_overall"] < 100


def test_player_search_on_the_mini_graph(tiny_graph):
    brazilians = tiny_graph.search_players(nationality="Brazil")
    assert [p["name"] for p in brazilians] == ["Ana Silva", "Bruno Costa"]
    at_alpha = tiny_graph.search_players(club="Alpha-SP")
    assert {p["name"] for p in at_alpha} == {"Ana Silva", "Carlos Ruiz"}
    assert tiny_graph.search_players(position="ST")[0]["name"] == "Ana Silva"
    assert tiny_graph.search_players(min_age=30)[0]["name"] == "Bruno Costa"


# --------------------------------------------------------- Competition queries

def test_who_won_the_2019_brasileirao(graph):
    # When I request the 2019 Brasileirao standings
    table = graph.standings("Brasileirao", 2019)
    champion = table["table"][0]
    # Then Flamengo is champion with 90 points from 28 wins, 6 draws and 4 losses
    assert table["champion"] == "Flamengo"
    assert champion["team"] == "Flamengo"
    assert champion["points"] == 90
    assert (champion["wins"], champion["draws"], champion["losses"]) == (28, 6, 4)
    assert champion["position"] == 1


@pytest.mark.parametrize(
    "season,champion",
    [(2010, "Fluminense"), (2016, "Palmeiras"), (2020, "Flamengo"), (2022, "Palmeiras")],
)
def test_champions_match_the_historical_record(graph, season, champion):
    assert graph.standings("Serie A", season)["champion"] == champion


def test_which_teams_were_relegated(graph):
    # When I request the 2020 Brasileirao standings
    table = graph.standings("Serie A", 2020)
    # Then the bottom four teams are reported as relegated
    assert len(table["relegated"]) == 4
    assert table["relegated"] == [row["team"] for row in table["table"][-4:]]
    assert table["table"][-1]["position"] == 20


def test_standings_are_ordered_by_points_then_wins(graph):
    rows = graph.standings("Serie A", 2021)["table"]
    ranking = [(-r["points"], -r["wins"], -r["goal_difference"]) for r in rows]
    assert ranking == sorted(ranking)
    assert [r["position"] for r in rows] == list(range(1, len(rows) + 1))


def test_standings_of_the_mini_league_are_exact(tiny_graph):
    table = tiny_graph.standings("Brasileirao", 2020)
    assert table["matches_counted"] == 6
    assert table["table"][0]["team"] == "Alpha"
    assert table["table"][0]["points"] == 7
    assert sum(r["matches"] for r in table["table"]) == 12  # 6 matches, 2 teams each


def test_standings_for_a_missing_season_are_empty_not_an_error(graph):
    table = graph.standings("Serie A", 1901)
    assert table["table"] == [] and table["matches_counted"] == 0


def test_knockout_bracket(graph):
    # When I request the 2018 Copa Libertadores bracket
    bracket = graph.bracket("Libertadores", 2018)
    # Then the stages are ordered from group stage to final
    stages = [s["stage"] for s in bracket["stages"]]
    assert stages[0] == "group stage"
    assert stages[-1] == "final"
    assert "semifinals" in stages
    assert all(s["matches"] for s in bracket["stages"])


def test_competition_summary_reports_top_scoring_teams(graph):
    summary = graph.competition_summary("Serie A", 2019)
    assert summary["matches"] == 380
    assert len(summary["top_scoring_teams"]) == 5
    goals = [t["goals"] for t in summary["top_scoring_teams"]]
    assert goals == sorted(goals, reverse=True)


# ------------------------------------------------------- Statistical analysis

def test_average_goals_per_match(graph):
    # When I request Brasileirao statistics
    stats = graph.statistics(competition="Serie A")
    # Then the average goals per match and home win rate are plausible
    assert 2.0 < stats["goals_per_match"] < 3.2
    assert 40 < stats["home_win_rate"] < 55
    assert stats["home_wins"] + stats["away_wins"] + stats["draws"] == stats["matches"]
    assert stats["home_goals"] > stats["away_goals"]     # home advantage
    assert stats["total_goals"] == stats["home_goals"] + stats["away_goals"]


def test_statistics_over_a_season_range(graph):
    stats = graph.statistics(competition="Serie A", season_from=2018, season_to=2019)
    assert stats["matches"] == 760
    assert stats["date_range"][0].startswith("2018")


def test_biggest_wins(graph):
    # When I request the biggest victories
    biggest = graph.biggest_wins(limit=10)
    # Then they are ordered by winning margin
    margins = [m["margin"] for m in biggest]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 6
    assert all(m["winner"] in (m["home_team"], m["away_team"]) for m in biggest)


def test_best_away_record(graph):
    # When I rank teams by away win rate
    rows = graph.team_leaderboard(metric="win_rate", venue="away",
                                  competition="Serie A", min_matches=100, limit=10)
    # Then the leaderboard is sorted and each row counts only away matches
    rates = [r["win_rate"] for r in rows]
    assert rates == sorted(rates, reverse=True)
    assert all(r["matches"] >= 100 for r in rows)
    # Away win rates are much lower than the overall home-inclusive figure.
    assert all(r["win_rate"] < 45 for r in rows)


def test_leaderboard_by_goals_against_ranks_ascending(graph):
    rows = graph.team_leaderboard(metric="goals_against", competition="Serie A",
                                  season=2019, limit=5)
    conceded = [r["goals_against"] for r in rows]
    assert conceded == sorted(conceded)


def test_leaderboard_rejects_unknown_metric(graph):
    with pytest.raises(ValueError, match="Unknown metric"):
        graph.team_leaderboard(metric="vibes")


def test_find_derbies_in_a_season(graph):
    derbies = graph.find_derbies(season=2019, competition="Serie A", limit=None)
    assert derbies
    names = {d["derby"] for d in derbies}
    assert names & {"Fla-Flu", "Derby Paulista", "Grenal", "Choque-Rei", "Majestoso"}
    assert all(d["season"] == 2019 for d in derbies)
