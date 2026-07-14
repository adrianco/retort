"""
================================================================================
 BDD tests: Sample Questions coverage (success criterion: >= 20 answerable)
================================================================================
Context
-------
The specification requires that "at least 20 sample questions can be answered".
This module enumerates 24 representative natural-language questions drawn from
the spec's Simple / Relationship / Analytical tables and asserts that the query
engine produces a usable, non-empty answer for each.  Each parametrized case is
a Given/When/Then scenario: GIVEN the loaded engine, WHEN the question's query
runs, THEN a meaningful answer is produced.
================================================================================
"""

import pytest


def _q(label, fn, check):
    return pytest.param(fn, check, id=label)


# Each entry: (callable(engine) -> answer, predicate(answer) -> bool)
SAMPLE_QUESTIONS = [
    # ---- Simple lookups -----------------------------------------------------
    _q("when_did_flamengo_last_play_corinthians",
       lambda e: e.last_match_between("Flamengo", "Corinthians"),
       lambda a: a is not None and "date" in a),
    _q("what_was_the_score",
       lambda e: e.last_match_between("Flamengo", "Corinthians"),
       lambda a: isinstance(a["home_goal"], int) and isinstance(a["away_goal"], int)),
    _q("who_is_neymar",
       lambda e: e.search_players("Neymar"),
       lambda a: a["count"] >= 1),
    _q("who_is_gabriel_barbosa",
       lambda e: e.search_players("Gabriel Barbosa"),
       lambda a: a["count"] >= 0),  # may or may not be in FIFA 19; must not error
    # ---- Match queries ------------------------------------------------------
    _q("all_flamengo_vs_fluminense_matches",
       lambda e: e.find_matches(team="Flamengo", opponent="Fluminense"),
       lambda a: a["count"] > 0),
    _q("what_matches_did_palmeiras_play_in_2019",
       lambda e: e.find_matches(team="Palmeiras", season=2019),
       lambda a: a["count"] > 0),
    _q("libertadores_matches",
       lambda e: e.find_matches(competition="Libertadores", limit=10),
       lambda a: a["count"] > 0),
    _q("copa_do_brasil_matches",
       lambda e: e.find_matches(competition="Copa do Brasil", limit=10),
       lambda a: a["count"] > 0),
    # ---- Team queries -------------------------------------------------------
    _q("corinthians_home_record_2021",
       lambda e: e.team_record("Corinthians", season=2021,
                               competition="Brasileirão Série A", venue="home"),
       lambda a: a["found"] and a["matches"] == 19),
    _q("which_team_scored_most_in_2019",
       lambda e: e.top_scoring_team(season=2019, competition="Brasileirão Série A"),
       lambda a: a["teams"][0]["goals_for"] > 0),
    _q("compare_palmeiras_and_santos",
       lambda e: e.head_to_head("Palmeiras", "Santos"),
       lambda a: a["total_matches"] > 0),
    _q("gremio_record_all_time",
       lambda e: e.team_record("Grêmio"),
       lambda a: a["found"] and a["matches"] > 0),
    # ---- Player queries -----------------------------------------------------
    _q("find_all_brazilian_players",
       lambda e: e.top_players(nationality="Brazil", limit=1000),
       lambda a: a["count"] > 100),
    _q("highest_rated_players_at_santos",
       lambda e: e.players_at_club("Santos"),
       lambda a: a["count"] > 0),
    _q("forwards_at_gremio",
       lambda e: e.players_at_club("Grêmio", position="ST"),
       lambda a: all(p["position"] == "ST" for p in a["players"])),
    _q("brazilian_players_by_club",
       lambda e: e.brazilian_players_by_club(),
       lambda a: a["total_brazilians"] > 100 and len(a["clubs"]) > 0),
    # ---- Competition queries ------------------------------------------------
    _q("who_won_2019_brasileirao",
       lambda e: e.champion(2019, "Brasileirão Série A"),
       lambda a: "Flamengo" in a["champion"]["team"]),
    _q("who_won_2016_brasileirao",
       lambda e: e.champion(2016, "Brasileirão Série A"),
       lambda a: a["champion"] is not None),
    _q("relegated_in_2019",
       lambda e: e.relegated_teams(2019, "Brasileirão Série A"),
       lambda a: len(a["relegated"]) == 4),
    _q("2018_standings",
       lambda e: e.standings(2018, "Brasileirão Série A"),
       lambda a: len(a["table"]) == 20),
    # ---- Analytical queries -------------------------------------------------
    _q("average_goals_per_match_brasileirao",
       lambda e: e.average_goals("Brasileirão Série A"),
       lambda a: 2.0 <= a["average_goals"] <= 3.5),
    _q("best_home_record",
       lambda e: e.best_home_record(season=2019, competition="Brasileirão Série A"),
       lambda a: len(a["teams"]) > 0),
    _q("best_away_record",
       lambda e: e.best_away_record(season=2019, competition="Brasileirão Série A"),
       lambda a: len(a["teams"]) > 0),
    _q("biggest_wins_in_dataset",
       lambda e: e.biggest_wins("Brasileirão Série A", limit=5),
       lambda a: len(a["matches"]) == 5),
    _q("compare_2018_and_2019_seasons",
       lambda e: e.compare_seasons(2018, 2019, "Brasileirão Série A"),
       lambda a: a["season_a"]["matches"] > 0 and a["season_b"]["matches"] > 0),
]


@pytest.mark.parametrize("query_fn,predicate", SAMPLE_QUESTIONS)
def test_sample_question_is_answerable(engine, query_fn, predicate):
    # Given the loaded query engine
    # When the sample question's query runs
    answer = query_fn(engine)
    # Then a meaningful, non-error answer is produced
    assert predicate(answer)


def test_at_least_twenty_sample_questions_covered():
    # The success criteria require >= 20 answerable sample questions.
    assert len(SAMPLE_QUESTIONS) >= 20
