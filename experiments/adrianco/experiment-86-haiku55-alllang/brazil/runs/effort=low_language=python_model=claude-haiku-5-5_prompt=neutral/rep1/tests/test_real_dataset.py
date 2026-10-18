# Context: Acceptance scenarios on the real Kaggle files in data/kaggle/. Checks that all six files
# load, that cross-file questions work, that at least 20 sample questions get answers, and that
# simple lookups and aggregates meet the spec's response-time targets.

import time

import pytest

from brazilian_soccer_mcp.server import SoccerTools

SAMPLE_QUESTIONS = [
    ("When did Flamengo last play Fluminense?", "find_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 5}),
    ("What matches did Palmeiras play in 2023?", "find_matches", {"team": "Palmeiras", "season": 2023, "limit": 5}),
    ("Show me Copa do Brasil matches", "find_matches", {"competition": "copa do brasil", "limit": 5}),
    ("Show me Libertadores matches", "find_matches", {"competition": "Libertadores", "limit": 5}),
    ("Palmeiras matches in a date range", "find_matches", {"team": "Palmeiras", "start_date": "01/01/2019", "end_date": "31/12/2019"}),
    ("What is Corinthians' home record in 2022?", "team_record", {"team": "Corinthians", "season": 2022, "venue": "home"}),
    ("Palmeiras record in Serie A 2023", "team_record", {"team": "Palmeiras", "season": 2023, "competition": "serie a"}),
    ("Flamengo away record", "team_record", {"team": "Flamengo", "venue": "away"}),
    ("Compare Palmeiras and Santos head-to-head", "head_to_head", {"team": "Palmeiras", "opponent": "Santos"}),
    ("Flamengo vs Fluminense in Serie A", "head_to_head", {"team": "Flamengo", "opponent": "Fluminense", "competition": "serie a"}),
    ("Who won the 2019 Brasileirão?", "standings", {"season": 2019, "relegation_places": 4}),
    ("Which teams were relegated in 2020?", "standings", {"season": 2020, "relegation_places": 4}),
    ("Who scored the most in Serie A 2023?", "standings", {"season": 2023}),
    ("Average goals per match in the Brasileirão", "season_stats", {"competition": "serie a"}),
    ("Goals per match in 2023", "season_stats", {"season": 2023}),
    ("Biggest wins in the dataset", "biggest_wins", {"limit": 5}),
    ("Which team has the best home record?", "venue_ranking", {"venue": "home", "season": 2023}),
    ("Which team has the best away record?", "venue_ranking", {"venue": "away", "season": 2023}),
    ("Who is Neymar?", "search_players", {"name": "Neymar"}),
    ("Find all Brazilian players in the dataset", "list_players", {"nationality": "Brazil", "limit": 10}),
    ("Show me all forwards from Brazil", "list_players", {"nationality": "Brazil", "position": "forward", "limit": 10}),
    ("Show me the Gremio squad", "club_profile", {"team": "Gremio"}),
    ("Stats for Atletico-MG in 2023", "team_record", {"team": "Atletico-MG", "season": 2023}),
    ("Statistics for the 2018 season", "season_stats", {"season": 2018}),
]


@pytest.fixture(scope="module")
def tools(real_kb):
    return SoccerTools(real_kb)


def test_given_the_kaggle_directory_when_loaded_then_all_six_files_contribute_data(real_kb):
    # Given the six provided files in data/kaggle
    # When the knowledge base is loaded
    competitions = {m.competition for m in real_kb.matches}
    # Then every competition family is present and the player file is loaded
    assert {"Brasileirão Série A", "Brasileirão Série B", "Brasileirão Série C",
            "Copa do Brasil", "Copa Libertadores"} <= competitions
    assert len(real_kb.players) == 18207


def test_given_the_real_matches_when_loaded_then_the_seasons_span_the_historical_and_recent_files(real_kb):
    # Given the historical 2003-2019 file and the recent Brasileirão files
    seasons = {m.season for m in real_kb.matches if m.competition == "Brasileirão Série A"}
    # Then both eras are covered
    assert min(seasons) <= 2003
    assert max(seasons) >= 2023


@pytest.mark.parametrize("question, tool, arguments", SAMPLE_QUESTIONS, ids=[q[0] for q in SAMPLE_QUESTIONS])
def test_given_a_sample_question_when_routed_to_a_tool_then_a_substantive_answer_is_returned(tools, question, tool, arguments):
    # Given a natural-language question mapped to its structured tool call
    # When the tool runs against the real data
    text = tools.call(tool, arguments)
    # Then the answer is a formatted, non-error response with content
    assert text.strip()
    assert not text.startswith("Error")
    assert "No matches found" not in text
    assert "No players found" not in text


def test_given_a_cross_file_question_when_asked_about_a_club_then_match_and_squad_data_are_combined(real_kb, tools):
    # Given Grêmio appears in the match files and the player file
    # When I ask for its 2023 record and its squad profile
    record = real_kb.team_record("Gremio", season=2023)
    club, squad = real_kb.club_profile("Gremio")
    # Then both sources contribute
    assert record.played > 0
    assert len(squad) > 0
    assert "squad" in tools.call("club_profile", {"team": "Gremio"})


def test_given_a_simple_lookup_when_timed_then_it_responds_within_two_seconds(tools):
    # Given the real data is loaded
    # When I look up a head-to-head record
    started = time.perf_counter()
    tools.call("head_to_head", {"team": "Flamengo", "opponent": "Fluminense"})
    # Then it responds in under two seconds
    assert time.perf_counter() - started < 2


def test_given_an_aggregate_query_when_timed_then_it_responds_within_five_seconds(tools):
    # Given the real data is loaded
    # When I compute a full standings table and season statistics
    started = time.perf_counter()
    tools.call("standings", {"season": 2019})
    tools.call("season_stats", {})
    # Then the aggregate answers come back in under five seconds
    assert time.perf_counter() - started < 5
