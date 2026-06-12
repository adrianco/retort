"""End-to-end checks against the real datasets.

Exercises the sample questions from the specification and the performance /
coverage success criteria.
"""

import time

import pytest

from brazilian_soccer.queries import KnowledgeBase
from brazilian_soccer.tools import SoccerTools


@pytest.fixture(scope="module")
def tools():
    return SoccerTools(KnowledgeBase.load())


def test_all_six_files_loaded(tools):
    s = tools.kb.summary()
    # 20,914 = raw row sum (24,754) minus the de-duplicated Brasileirão
    # seasons 2012-2019 that overlap between the two league sources.
    assert s["total_matches"] == 20914
    assert s["total_players"] == 18207
    assert {"Brasileirão", "Copa do Brasil", "Copa Libertadores"} <= set(s["competitions"])


def test_simple_lookup_under_two_seconds(tools):
    start = time.perf_counter()
    out = tools.search_matches(team="Flamengo", opponent="Corinthians")
    elapsed = time.perf_counter() - start
    assert "Flamengo" in out
    assert elapsed < 2.0


def test_aggregate_query_under_five_seconds(tools):
    start = time.perf_counter()
    out = tools.standings(season=2019, competition="Brasileirão")
    elapsed = time.perf_counter() - start
    assert "Flamengo" in out.splitlines()[1]  # 2019 champion
    assert elapsed < 5.0


def test_2019_brasileirao_champion_is_flamengo(tools):
    table = tools.kb.standings(season=2019, competition="Brasileirão")
    assert table[0]["team_key"] == "flamengo"
    assert table[0]["points"] == 90  # historically Flamengo finished on 90 pts
    # Santos (22 wins) finished 2nd above Palmeiras (21 wins) on the wins
    # tiebreaker, despite equal points.
    assert table[1]["team_key"] == "santos"
    assert table[2]["team_key"] == "palmeiras"


def test_player_lookup_by_name(tools):
    # The provided FIFA database is the FIFA 19 export; Neymar is present.
    out = tools.search_players(name="Neymar")
    assert "Neymar Jr" in out


def test_brazilian_players_filter(tools):
    out = tools.search_players(nationality="Brazil", limit=5)
    assert out.count("Nationality: Brazil") == 5


def test_players_by_brazilian_club(tools):
    # Santos is one of the Brazilian clubs present in the FIFA 19 dataset.
    out = tools.search_players(club="Santos")
    assert "Santos" in out


def test_head_to_head_real(tools):
    out = tools.head_to_head("Palmeiras", "Santos")
    assert "head-to-head" in out.lower()
    assert "Palmeiras" in out and "Santos" in out


def test_statistics_average_goals_reasonable(tools):
    avg = tools.kb.average_goals_per_match(competition="Brasileirão")
    assert 1.5 < avg < 4.0


def test_biggest_wins_real(tools):
    out = tools.biggest_wins(limit=5)
    assert "Biggest victories" in out


def test_cross_file_competitions_for_palmeiras(tools):
    # Palmeiras should appear across multiple competitions/files.
    matches = tools.kb.find_matches(team="Palmeiras")
    comps = {m.competition for m in matches}
    assert len(comps) >= 2


def test_twenty_sample_questions_answerable(tools):
    """Twenty distinct sample queries each return a non-empty, sensible answer."""
    answers = [
        tools.search_matches(team="Flamengo", opponent="Fluminense"),
        tools.search_matches(team="Palmeiras", season=2019),
        tools.search_matches(competition="Copa do Brasil", season=2019),
        tools.search_matches(home="Corinthians", season=2019),
        tools.search_matches(team="Santos", competition="Copa Libertadores"),
        tools.head_to_head("Palmeiras", "Santos"),
        tools.head_to_head("Flamengo", "Fluminense"),
        tools.team_record("Corinthians", season=2019, venue="home"),
        tools.team_record("Gremio", season=2018),
        tools.standings(season=2019, competition="Brasileirão"),
        tools.standings(season=2018, competition="Brasileirão"),
        tools.search_players(name="Neymar"),
        tools.search_players(nationality="Brazil", limit=10),
        tools.search_players(club="Flamengo"),
        tools.search_players(position="GK", nationality="Brazil", limit=5),
        tools.search_players(min_overall=88, limit=10),
        tools.statistics(competition="Brasileirão", season=2019),
        tools.biggest_wins(competition="Brasileirão", limit=5),
        tools.best_record(venue="home", season=2019, min_matches=5),
        tools.data_summary(),
    ]
    assert len(answers) >= 20
    for a in answers:
        assert isinstance(a, str) and a.strip()
        assert "Traceback" not in a
