"""Every sample question from the specification, end to end through the tools.

Context
-------
The specification's data-coverage criterion is "at least 20 sample questions
can be answered".  This module runs each of the questions it lists -- plus the
three "Sample Questions and Expected Behaviours" tables -- through
``call_tool`` and asserts on the *content* of the answer, not merely that a
call succeeded.  ``tests/test_answer_shapes.py`` covers the formatting; this
file is about factual correctness.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.cli import DEMO_QUESTIONS
from brazilian_soccer.tools import call_tool


def answer(graph, tool, **arguments) -> tuple[str, dict]:
    result = call_tool(tool, arguments, graph=graph)
    assert not result["isError"], result["content"][0]["text"]
    return result["content"][0]["text"], result["structuredContent"]


# --- Section 1: Match Queries ---------------------------------------------

def test_q01_show_me_all_flamengo_vs_fluminense_matches(graph):
    text, data = answer(graph, "head_to_head", team_a="Flamengo",
                        team_b="Fluminense", limit=5)
    assert data["derby_name"] == "Fla-Flu"
    assert data["total_matches"] > 40
    assert "Head-to-head in dataset" in text
    assert "more matches in dataset" in text


def test_q02_what_matches_did_palmeiras_play_in_2023(graph):
    _, data = answer(graph, "find_matches", team="Palmeiras", season=2023,
                     limit=100)
    assert data["total_matches"] >= 38
    assert {m["season"] for m in data["matches"]} == {2023}


def test_q03_find_all_copa_do_brasil_finals(graph):
    _, data = answer(graph, "find_matches", competition="copa-do-brasil",
                     stage="Final", limit=50)
    assert data["total_matches"] == 18
    winners_2019 = {m["home_team"] for m in data["matches"] if m["season"] == 2019}
    assert winners_2019 == {"Athletico Paranaense", "Internacional"}


def test_q04_when_did_flamengo_last_play_corinthians(graph):
    _, data = answer(graph, "head_to_head", team_a="Flamengo",
                     team_b="Corinthians", limit=1)
    last = data["last_meeting"]
    assert last["date"] == "2023-10-08"
    assert last["score"] == "1-1"


def test_q05_what_was_the_score(graph):
    """Follow-up question: the score comes back with the match."""
    _, data = answer(graph, "find_matches", team="Flamengo",
                     opponent="Corinthians", limit=1)
    match = data["matches"][0]
    assert match["home_goals"] is not None and match["away_goals"] is not None
    assert match["score"] == f"{match['home_goals']}-{match['away_goals']}"


# --- Section 2: Team Queries ----------------------------------------------

def test_q06_corinthians_home_record_in_2022(graph):
    text, data = answer(graph, "team_stats", team="Corinthians", season=2022,
                        competition="brasileirao", venue="home")
    record = data["overall"]
    assert record["played"] == 19
    assert record["wins"] + record["draws"] + record["losses"] == 19
    assert "Win rate" in text and "Goals For" in text


def test_q07_which_team_scored_the_most_goals_in_serie_a_2023(graph):
    _, data = answer(graph, "team_rankings", metric="goals_for",
                     competition="serie-a", season=2023, limit=3)
    top = data["rankings"][0]
    assert top["goals_for"] >= data["rankings"][1]["goals_for"]
    assert top["team"] == "Grêmio"


def test_q08_compare_palmeiras_and_santos_head_to_head(graph):
    _, data = answer(graph, "head_to_head", team_a="Palmeiras", team_b="Santos",
                     limit=5)
    assert data["derby_name"] == "Clássico da Saudade"
    assert data["total_matches"] > 35


def test_q09_which_players_play_for_flamengo(graph):
    """An honest empty answer: FIFA 19 did not license Flamengo."""
    text, data = answer(graph, "club_squad", club="Flamengo")
    assert data["squad_size"] == 0
    assert "FIFA 19" in text


def test_q10_what_competitions_has_palmeiras_played_in(graph):
    _, data = answer(graph, "team_profile", team="Palmeiras")
    assert {c["competition_slug"] for c in data["competitions"]} == {
        "serie-a", "copa-do-brasil", "libertadores"}


def test_q11_which_team_has_the_best_home_record(graph):
    _, data = answer(graph, "team_rankings", metric="win_rate",
                     competition="serie-a", venue="home", min_matches=100,
                     limit=5)
    assert data["rankings"][0]["win_rate"] > 50
    assert all(row["matches"] >= 100 for row in data["rankings"])


def test_q12_which_team_has_the_best_away_record(graph):
    _, data = answer(graph, "team_rankings", metric="points_per_game",
                     competition="serie-a", venue="away", min_matches=100,
                     limit=5)
    best = data["rankings"][0]
    assert best["points_per_game"] > 1.0
    assert best["team"] in {"Palmeiras", "São Paulo", "Flamengo", "Cruzeiro",
                            "Corinthians", "Grêmio", "Internacional",
                            "Atlético Mineiro", "Santos"}


# --- Section 3: Player Queries --------------------------------------------

def test_q13_find_all_brazilian_players(graph):
    _, data = answer(graph, "search_players", nationality="Brazil", limit=500)
    assert data["total_players"] == 827
    assert data["players"][0]["name"] == "Neymar Jr"


def test_q14_who_are_the_highest_rated_players_at_a_brazilian_club(graph):
    text, data = answer(graph, "club_squad", club="Cruzeiro", limit=5)
    assert data["squad_size"] == 20
    assert data["average_overall"] > 60
    assert "Overall" in text


def test_q15_show_me_all_forwards_from_a_club(graph):
    _, data = answer(graph, "search_players", club="Santos", position="FWD",
                     limit=20)
    assert data["total_players"] > 0
    assert all(p["position_group"] == "FWD" for p in data["players"])


def test_q16_who_is_gabriel_jesus(graph):
    text, data = answer(graph, "player_profile", name="Gabriel Jesus")
    assert data["player"]["nationality"] == "Brazil"
    assert data["player"]["overall"] >= 80
    assert "Overall" in text


def test_q17_who_are_the_top_brazilian_players(graph):
    _, data = answer(graph, "brazilian_players_by_club", limit=10)
    names = [p["name"] for p in data["top_rated"]]
    assert names[0] == "Neymar Jr"
    assert len(data["at_clubs_present_in_match_data"]) >= 10


# --- Section 4: Competition Queries ---------------------------------------

def test_q18_who_won_the_2019_brasileirao(graph):
    text, data = answer(graph, "standings", season=2019)
    assert data["champion"] == "Flamengo"
    assert data["table"][0]["points"] == 90
    assert "Champion" in text


def test_q19_which_teams_were_relegated_in_2020(graph):
    _, data = answer(graph, "standings", season=2020)
    assert len(data["relegated"]) == 4
    assert "Botafogo" in data["relegated"]


def test_q20_show_the_2018_libertadores_knockout_stages(graph):
    _, data = answer(graph, "find_matches", competition="libertadores",
                     season=2018, stage="Final", limit=10)
    assert data["total_matches"] == 2
    teams = {m["home_team"] for m in data["matches"]}
    assert teams == {"River Plate", "Boca Juniors"}


# --- Section 5: Statistical Analysis --------------------------------------

def test_q21_average_goals_per_match_in_the_brasileirao(graph):
    _, data = answer(graph, "competition_stats", competition="brasileirao")
    assert 2.0 < data["goals_per_match"] < 3.0
    assert 40 < data["home_win_rate"] < 60


def test_q22_biggest_wins_in_the_dataset(graph):
    _, data = answer(graph, "biggest_wins", limit=10)
    margins = [m["margin"] for m in data["results"]]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 7


def test_q23_compare_the_2018_and_2019_seasons(graph):
    _, data = answer(graph, "compare_seasons", seasons=[2018, 2019],
                     competition="serie-a")
    champions = [row["champion"] for row in data["comparison"]]
    assert champions == ["Palmeiras", "Flamengo"]


def test_q24_show_me_all_derbies_in_2023(graph):
    _, data = answer(graph, "find_derbies", season=2023, limit=50)
    names = {row["derby"] for row in data["derbies"]}
    assert {"Fla-Flu", "Derby Paulista", "Gre-Nal"} <= names


def test_q25_biggest_wins_for_one_club(graph):
    _, data = answer(graph, "biggest_wins", team="Flamengo",
                     competition="serie-a", limit=5)
    assert all(m["winner"] == "Flamengo" for m in data["results"])


def test_q26_dataset_coverage(graph):
    text, data = answer(graph, "dataset_summary")
    assert len(data["files"]) == 6
    assert data["matches"]["merged_duplicates"] > 5000
    assert "Source files" in text


# --- The CLI demo runs every question without error -----------------------

@pytest.mark.parametrize("question,tool,arguments",
                         DEMO_QUESTIONS,
                         ids=[q[0][:48] for q in DEMO_QUESTIONS])
def test_demo_questions_all_answer(graph, question, tool, arguments):
    result = call_tool(tool, arguments, graph=graph)
    assert not result["isError"], result["content"][0]["text"]
    assert len(result["content"][0]["text"]) > 20


def test_the_demo_covers_at_least_twenty_questions():
    assert len(DEMO_QUESTIONS) >= 20
    assert len({tool for _, tool, _ in DEMO_QUESTIONS}) >= 10
