from __future__ import annotations

from datetime import date
from time import perf_counter

import pytest

from query_engine import QueryEngine
from soccer_graph import SoccerGraph, normalize_team, normalize_text, parse_date


@pytest.fixture(scope="session")
def graph() -> SoccerGraph:
    return SoccerGraph()


@pytest.fixture(scope="session")
def engine(graph: SoccerGraph) -> QueryEngine:
    return QueryEngine(graph)


def test_loads_every_required_dataset(graph: SoccerGraph) -> None:
    assert graph.raw_row_counts == {
        "Brasileirao_Matches.csv": 4180,
        "Brazilian_Cup_Matches.csv": 1337,
        "Libertadores_Matches.csv": 1255,
        "BR-Football-Dataset.csv": 10296,
        "novo_campeonato_brasileiro.csv": 6886,
        "fifa_data.csv": 18207,
    }
    assert len(graph.matches) > 15_000
    assert len(graph.players) == 18_207


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("São Paulo-SP", "sao paulo"),
        ("São Paulo FC", "sao paulo"),
        ("Palmeiras-SP", "palmeiras"),
        ("Sport Club Corinthians Paulista", "corinthians"),
        ("América - MG", "america mineiro"),
        ("Atletico-PR", "athletico paranaense"),
        ("Atlético-MG", "atletico mineiro"),
    ],
)
def test_team_name_normalization(raw: str, expected: str) -> None:
    assert normalize_team(raw) == expected


def test_unicode_and_date_normalization() -> None:
    assert normalize_text("Grêmio") == "gremio"
    assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)
    assert parse_date("29/03/2003") == date(2003, 3, 29)
    assert parse_date("NA") is None


def test_match_search_across_all_five_match_sources(graph: SoccerGraph) -> None:
    for source in graph.raw_row_counts:
        if source == "fifa_data.csv":
            continue
        assert graph.find_matches(source=source, limit=1), source


def test_match_search_by_team_date_competition_and_season(graph: SoccerGraph) -> None:
    matches = graph.find_matches(
        team="Palmeiras", start_date="2022-01-01", end_date="2022-12-31",
        competition="Serie A", season=2022, limit=100,
    )
    assert matches
    assert all(match.season == 2022 and match.competition == "Brasileirão" for match in matches)
    assert all("palmeiras" in {match.home_key, match.away_key} for match in matches)


def test_head_to_head_returns_results_and_consistent_totals(graph: SoccerGraph) -> None:
    result = graph.head_to_head("Flamengo-RJ", "Fluminense")
    assert result["matches"] > 10
    assert result["team1_wins"] + result["team2_wins"] + result["draws"] == result["matches"]
    assert all({normalize_team(r["home_team"]), normalize_team(r["away_team"])} >= {"flamengo", "fluminense"} for r in result["results"])


def test_team_statistics_are_internally_consistent(graph: SoccerGraph) -> None:
    result = graph.team_statistics("Corinthians", season=2022, competition="Brasileirão", venue="home")
    assert result["matches"] == result["wins"] + result["draws"] + result["losses"]
    assert result["points"] == result["wins"] * 3 + result["draws"]
    assert result["goal_difference"] == result["goals_for"] - result["goals_against"]
    assert result["matches"] == 19


def test_2019_calculated_standings_match_known_champion(graph: SoccerGraph) -> None:
    table = graph.standings(2019, "Brasileirão")
    assert table[0]["team"] == "Flamengo"
    assert table[0]["points"] == 90
    assert table[0]["played"] == 38
    assert all(row["position"] == index for index, row in enumerate(table, 1))


def test_player_search_filters_and_sorts(graph: SoccerGraph) -> None:
    players = graph.search_players(nationality="Brazil", min_overall=80, limit=25)
    assert players
    assert all(player.nationality == "Brazil" and (player.overall or 0) >= 80 for player in players)
    assert [player.overall for player in players] == sorted((p.overall for p in players), reverse=True)


def test_player_lookup_by_name(graph: SoccerGraph) -> None:
    players = graph.search_players(name="Neymar", limit=5)
    assert players
    assert "Neymar" in players[0].name


def test_aggregate_statistics_and_biggest_wins(graph: SoccerGraph) -> None:
    stats = graph.aggregate_statistics(competition="Brasileirão", season=2019)
    assert stats["matches"] == 380
    assert 1.5 < stats["goals_per_match"] < 4
    assert stats["home_wins"] + stats["away_wins"] + stats["draws"] == 380
    biggest = graph.biggest_wins(competition="Libertadores", limit=5)
    margins = [abs((m["home_goals"] or 0) - (m["away_goals"] or 0)) for m in biggest]
    assert margins == sorted(margins, reverse=True)


def test_derbies_and_cross_file_club_overview(graph: SoccerGraph) -> None:
    derbies = graph.find_derbies(season=2019)
    assert derbies
    assert all("derby" in match for match in derbies)
    overview = graph.club_overview("FC Barcelona", player_limit=5)
    assert overview["players"]
    assert all("Barcelona" in player["club"] for player in overview["players"])
    assert "statistics" in overview and "competitions" in overview


def test_simple_queries_meet_two_second_budget(graph: SoccerGraph) -> None:
    started = perf_counter()
    for _ in range(25):
        graph.find_matches(team="Flamengo", season=2019, limit=50)
        graph.search_players(name="Neymar", limit=5)
    assert perf_counter() - started < 2.0


def test_aggregate_queries_meet_five_second_budget(graph: SoccerGraph) -> None:
    started = perf_counter()
    graph.standings(2019)
    graph.rank_teams(season=2022, metric="goals_for")
    graph.aggregate_statistics()
    assert perf_counter() - started < 5.0


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("Show me all Flamengo vs Fluminense matches", "head_to_head"),
        ("When did Flamengo last play Corinthians?", "head_to_head"),
        ("Compare Palmeiras and Santos head-to-head", "head_to_head"),
        ("What matches did Palmeiras play in 2022?", "match_search"),
        ("Find all Copa do Brasil finals", "match_search"),
        ("Show the 2018 Copa Libertadores bracket", "match_search"),
        ("What is Corinthians' home record in 2022?", "team_statistics"),
        ("What competitions has Palmeiras played in?", "team_competitions"),
        ("Which team scored the most goals in Serie A 2023?", "team_ranking"),
        ("Which team has the best away record?", "team_ranking"),
        ("Who won the 2019 Brasileirão?", "standings"),
        ("Show me the 2019 Brasileirão standings", "standings"),
        ("Which teams were relegated in 2020?", "standings"),
        ("Who are the top Brazilian players?", "player_search"),
        ("Who is Neymar?", "player_search"),
        ("Show me Brazilian forwards", "player_search"),
        ("What's the average goals per match in the Brasileirão?", "aggregate_statistics"),
        ("Show me the biggest wins in the dataset", "biggest_wins"),
        ("Show me all derbies in 2019", "derby_search"),
        ("Compare the 2018 and 2019 seasons", "season_comparison"),
        ("Who were the top scorers in 2019?", "unsupported_top_scorers"),
    ],
)
def test_natural_language_sample_questions(engine: QueryEngine, question: str, intent: str) -> None:
    result = engine.ask(question)
    assert result["intent"] == intent
    assert result["answer"]
    assert "data" in result


def test_invalid_inputs_fail_clearly(graph: SoccerGraph, engine: QueryEngine) -> None:
    with pytest.raises(ValueError, match="limit"):
        graph.find_matches(limit=0)
    with pytest.raises(ValueError, match="venue"):
        graph.team_statistics("Flamengo", venue="neutral")
    with pytest.raises(ValueError, match="empty"):
        engine.ask(" ")

