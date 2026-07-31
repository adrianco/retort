"""
Unit tests for the analytical query API.

Context
-------
Where possible these assert against *externally verifiable* facts rather than
against whatever the code happens to produce: the 2019 Brasileirao really was
won by Flamengo on 90 points with 28 wins, Cruzeiro really did take 100 points
in 2003, and the clubs relegated in 2019 really were Cruzeiro, CSA, Chapecoense
and Avai.  If the loaders, the club registry or the de-duplication regress,
these numbers move and the tests fail.
"""

from __future__ import annotations

import datetime as dt

import pytest

from brazilian_soccer import queries as q


# ---------------------------------------------------------------------------
# Argument resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("brasileirao", "serie-a"),
        ("Brasileirão", "serie-a"),
        ("serie a", "serie-a"),
        ("Série A", "serie-a"),
        ("Campeonato Brasileiro Série A", "serie-a"),
        ("serie-a", "serie-a"),
        ("copa do brasil", "copa-do-brasil"),
        ("Brazilian Cup", "copa-do-brasil"),
        ("libertadores", "libertadores"),
        ("Copa Libertadores", "libertadores"),
        ("serie b", "serie-b"),
    ],
)
def test_resolve_competition_aliases(value, expected):
    assert q.resolve_competition(value).id == expected


def test_resolve_competition_none_is_no_filter():
    assert q.resolve_competition(None) is None
    assert q.resolve_competition("") is None


def test_unknown_competition_lists_the_known_ones():
    with pytest.raises(q.CompetitionNotFound) as error:
        q.resolve_competition("Premier League")
    assert "Copa Libertadores" in str(error.value)


def test_unknown_team_raises_with_suggestions(graph):
    with pytest.raises(q.TeamNotFound) as error:
        q.resolve_team(graph, "")
    assert error.value.suggestions


def test_resolve_team_prefers_clubs_that_actually_played(graph):
    assert q.resolve_team(graph, "Flamengo").id == "flamengo-rj"
    assert len(graph.matches_by_team[q.resolve_team(graph, "Botafogo").id]) > 100


# ---------------------------------------------------------------------------
# Standings -- checked against real results
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "season, champion, points",
    [
        (2003, "Cruzeiro", 100),
        (2015, "Corinthians", 81),
        (2016, "Palmeiras", 80),
        (2017, "Corinthians", 72),
        (2018, "Palmeiras", 80),
        (2019, "Flamengo", 90),
        (2021, "Atlético Mineiro", 84),
        (2022, "Palmeiras", 81),
    ],
)
def test_league_champions_match_the_historical_record(graph, season, champion, points):
    table = q.standings(graph, "brasileirao", season)
    assert champion in table[0].record.team_name
    assert table[0].record.points == points
    assert table[0].note == "Champion"


def test_2019_table_reproduces_the_task_example(graph):
    table = q.standings(graph, "brasileirao", 2019)
    top = table[0].record
    assert (top.wins, top.draws, top.losses) == (28, 6, 4)
    assert [row.record.points for row in table[:3]] == [90, 74, 74]
    assert "Santos" in table[1].record.team_name
    assert "Palmeiras" in table[2].record.team_name


def test_known_gap_in_2009_is_visible_rather_than_hidden(graph):
    """One Flamengo-Botafogo fixture is absent from every provided file.

    Flamengo won the real 2009 Brasileirao with 67 points; the data yields 64
    from 37 matches, so the calculated table puts Internacional first.  The
    behaviour is pinned here (and documented in the README) so the gap is a
    known property of the sources rather than a silent surprise.
    """

    table = q.standings(graph, "brasileirao", 2009)
    by_team = {row.record.team_id: row.record for row in table}
    assert by_team["flamengo-rj"].played == 37
    assert by_team["botafogo-rj"].played == 37
    assert all(record.played == 38 for team_id, record in by_team.items()
               if team_id not in {"flamengo-rj", "botafogo-rj"})


def test_relegation_places_match_the_historical_record(graph):
    relegated = {row.record.team_name for row in q.relegated_teams(graph, "brasileirao", 2019)}
    assert {"Cruzeiro (MG)", "CSA (AL)", "Chapecoense (SC)", "Avaí (SC)"} == relegated


def test_standings_are_internally_consistent(graph):
    table = q.standings(graph, "brasileirao", 2018)
    assert len(table) == 20
    for row in table:
        record = row.record
        assert record.played == record.wins + record.draws + record.losses == 38
        assert record.points == record.wins * 3 + record.draws
    assert sum(r.record.goals_for for r in table) == sum(r.record.goals_against for r in table)
    assert sum(r.record.wins for r in table) == sum(r.record.losses for r in table)


def test_standings_require_a_season(graph):
    with pytest.raises(ValueError):
        q.standings(graph, "brasileirao", None)


def test_home_and_away_tables_sum_to_the_full_table(graph):
    full = {r.record.team_id: r.record for r in q.standings(graph, "brasileirao", 2019)}
    home = {r.record.team_id: r.record for r in
            q.standings(graph, "brasileirao", 2019, scope="home")}
    away = {r.record.team_id: r.record for r in
            q.standings(graph, "brasileirao", 2019, scope="away")}
    for team_id, record in full.items():
        assert record.points == home[team_id].points + away[team_id].points
        assert record.goals_for == home[team_id].goals_for + away[team_id].goals_for


# ---------------------------------------------------------------------------
# Champions of cup competitions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "season, champion",
    [
        (2013, "Atlético Mineiro"),
        (2014, "San Lorenzo"),
        (2015, "River Plate"),
        (2016, "Atlético Nacional"),
        (2017, "Grêmio"),
        (2018, "River Plate"),
        (2019, "Flamengo"),
        (2020, "Palmeiras"),
    ],
)
def test_libertadores_champions(graph, season, champion):
    result = q.competition_champion(graph, "libertadores", season)
    if result["champion"] is None:
        # 2013 was decided on penalties after a 2-2 aggregate; the data has no
        # shoot-out column, so the tool must say so rather than guess.
        assert "penalties" in result["method"]
        assert season == 2013
    else:
        assert champion in result["champion"].name


@pytest.mark.parametrize(
    "season, champion",
    [(2012, "Palmeiras"), (2013, "Flamengo"), (2014, "Atlético Mineiro"),
     (2016, "Grêmio"), (2018, "Cruzeiro"), (2019, "Athletico Paranaense"),
     (2020, "Palmeiras")],
)
def test_copa_do_brasil_champions(graph, season, champion):
    result = q.competition_champion(graph, "copa do brasil", season)
    assert result["champion"] is not None, result["method"]
    assert champion in result["champion"].name


def test_missing_final_does_not_produce_a_champion(graph):
    result = q.competition_champion(graph, "copa do brasil", 2023)
    assert result["champion"] is None
    assert result["final"] == []


# ---------------------------------------------------------------------------
# Team records and head-to-head
# ---------------------------------------------------------------------------


def test_home_plus_away_equals_overall(graph):
    overall = q.team_record(graph, "Palmeiras", competition="brasileirao", season=2022)
    home = q.team_record(graph, "Palmeiras", competition="brasileirao", season=2022,
                         scope="home")
    away = q.team_record(graph, "Palmeiras", competition="brasileirao", season=2022,
                         scope="away")
    assert overall.played == home.played + away.played == 38
    assert overall.wins == home.wins + away.wins
    assert overall.goals_for == home.goals_for + away.goals_for


def test_head_to_head_is_symmetric(graph):
    forward = q.head_to_head(graph, "Palmeiras", "Santos")
    backward = q.head_to_head(graph, "Santos", "Palmeiras")
    assert forward.played == backward.played
    assert forward.team_a_wins == backward.team_b_wins
    assert forward.team_a_goals == backward.team_b_goals


def test_head_to_head_totals_add_up(graph):
    record = q.head_to_head(graph, "Grêmio", "Internacional", limit=None)
    assert record.played == record.team_a_wins + record.team_b_wins + record.draws
    scored = [m for m in record.matches if m.has_score]
    assert record.played == len(scored)


def test_head_to_head_can_be_scoped_to_a_competition(graph):
    everything = q.head_to_head(graph, "Flamengo", "Fluminense", limit=None)
    league_only = q.head_to_head(graph, "Flamengo", "Fluminense",
                                 competition="brasileirao", limit=None)
    assert 0 < league_only.played < everything.played
    assert all(m.competition_id == "serie-a" for m in league_only.matches)


def test_team_profile_covers_every_competition(graph):
    profile = q.team_profile(graph, "Flamengo")
    assert {"serie-a", "copa-do-brasil", "libertadores"} <= set(profile["competitions"])
    assert profile["overall"].played > 800
    assert profile["first_match"] < profile["last_match"]
    assert len(profile["recent_matches"]) == 5


def test_compare_teams_returns_both_records_and_the_meetings(graph):
    comparison = q.compare_teams(graph, "Palmeiras", "Santos")
    assert comparison["record_a"].played > 0
    assert comparison["record_b"].played > 0
    assert comparison["head_to_head"].played > 20


# ---------------------------------------------------------------------------
# Match search
# ---------------------------------------------------------------------------


def test_search_matches_by_season_and_competition(graph):
    matches = q.search_matches(graph, team="Palmeiras", competition="brasileirao",
                               season=2022, limit=None)
    assert len(matches) == 38
    assert all(m.season == 2022 and m.competition_id == "serie-a" for m in matches)


def test_search_matches_home_only(graph):
    matches = q.search_matches(graph, team="Corinthians", competition="brasileirao",
                               season=2022, home_away="home", limit=None)
    assert len(matches) == 19
    assert all(m.home_team_id == "corinthians-sp" for m in matches)


def test_search_matches_by_date_range(graph):
    matches = q.search_matches(graph, date_from="2019-05-01", date_to="2019-05-31",
                               competition="brasileirao", limit=None)
    assert matches
    assert all(dt.date(2019, 5, 1) <= m.date <= dt.date(2019, 5, 31) for m in matches)


def test_search_matches_accepts_brazilian_date_format(graph):
    matches = q.search_matches(graph, date_from="29/03/2003", date_to="29/03/2003",
                               competition="brasileirao", limit=None)
    assert matches
    assert all(m.date == dt.date(2003, 3, 29) for m in matches)


def test_search_matches_orders_most_recent_first(graph):
    matches = q.search_matches(graph, team="Santos", limit=10)
    dates = [m.date for m in matches]
    assert dates == sorted(dates, reverse=True)


def test_search_matches_between_two_named_clubs_only(graph):
    matches = q.search_matches(graph, team="Flamengo", opponent="Fluminense", limit=None)
    pair = {"flamengo-rj", "fluminense-rj"}
    assert matches
    assert all({m.home_team_id, m.away_team_id} == pair for m in matches)


def test_cup_finals_can_be_searched_by_stage(graph):
    finals = q.search_matches(graph, competition="copa do brasil", stage="final", limit=None)
    assert len(finals) >= 16
    assert all(m.stage == "final" for m in finals)


def test_derbies_are_recognised(graph):
    derbies = q.find_derbies(graph, season=2019)
    names = {entry["derby"] for entry in derbies}
    assert {"Grenal", "Derby Paulista", "Fla-Flu"} <= names
    for entry in derbies:
        assert entry["matches"]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def test_competition_stats_add_up(graph):
    stats = q.competition_stats(graph, competition="brasileirao", season=2019)
    assert stats["matches"] == 380
    assert stats["home_wins"] + stats["away_wins"] + stats["draws"] == 380
    assert 2.0 < stats["goals_per_match"] < 3.5
    assert abs(stats["home_goals_per_match"] + stats["away_goals_per_match"]
               - stats["goals_per_match"]) < 0.02


def test_home_advantage_exists(graph):
    stats = q.competition_stats(graph, competition="brasileirao")
    assert stats["home_win_rate"] > stats["away_win_rate"]


def test_biggest_wins_are_ordered_by_margin(graph):
    matches = q.biggest_wins(graph, competition="brasileirao", limit=10)
    margins = [abs(m.goal_difference) for m in matches]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 5


def test_best_records_respects_the_minimum_match_filter(graph):
    records = q.best_records(graph, competition="brasileirao", min_matches=200, limit=5)
    assert all(record.played >= 200 for record in records)
    assert records == sorted(records, key=lambda r: (-r.points_per_game, -r.goal_difference,
                                                     r.team_name))


def test_top_scoring_team_of_a_season(graph):
    records = q.top_scoring_teams(graph, competition="brasileirao", season=2019, limit=3)
    assert "Flamengo" in records[0].team_name
    assert records[0].goals_for == 86


def test_compare_seasons_reports_each_season(graph):
    rows = q.compare_seasons(graph, [2018, 2019], competition="brasileirao")
    assert [row["season"] for row in rows] == [2018, 2019]
    assert all(row["matches"] == 380 for row in rows)
    assert rows[1]["champion"].startswith("Flamengo")


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


def test_brazilian_players_are_found_and_ranked(graph):
    players = q.search_players(graph, nationality="Brazil", limit=5)
    assert players[0].name == "Neymar Jr"
    assert players[0].overall == 92
    assert all(p.nationality == "Brazil" for p in players)
    ratings = [p.overall for p in players]
    assert ratings == sorted(ratings, reverse=True)


def test_players_can_be_filtered_by_club(graph):
    players = q.search_players(graph, club="Grêmio", limit=0)
    assert len(players) == 20
    assert all(p.club_team_id == "gremio-rs" for p in players)


def test_players_can_be_filtered_by_position_group(graph):
    forwards = q.search_players(graph, club="Santos", position="forward", limit=0)
    assert forwards
    from brazilian_soccer.loaders import position_group

    assert all(position_group(p.position) == "forward" for p in forwards)


def test_players_can_be_filtered_by_rating_and_age(graph):
    players = q.search_players(graph, nationality="Brazil", min_overall=85, max_age=30,
                               limit=0)
    assert players
    assert all(p.overall >= 85 and p.age <= 30 for p in players)


def test_player_profile_finds_a_player_by_partial_name(graph):
    profile = q.player_profile(graph, "Neymar")
    assert profile["player"].name == "Neymar Jr"


def test_missing_player_returns_suggestions_not_an_error(graph):
    profile = q.player_profile(graph, "Gabriel Barbosa")
    assert profile["player"] is None
    assert profile["suggestions"]


def test_club_squad_joins_players_to_match_history(graph):
    squad = q.club_squad(graph, "Cruzeiro")
    assert squad["squad_size"] == 20
    assert squad["average_overall"] > 60
    assert squad["record"].played > 500
    assert "serie-a" in squad["competitions"]


def test_club_squad_for_an_unlicensed_club_is_empty_but_valid(graph):
    squad = q.club_squad(graph, "Flamengo")
    assert squad["players"] == []
    assert squad["record"].played > 500


def test_dataset_summary_lists_every_source(graph):
    summary = q.dataset_summary(graph)
    assert len(summary["datasets"]) == 6
    assert all(entry["rows"] > 0 for entry in summary["datasets"])
    assert {entry["license"] for entry in summary["datasets"]} >= {
        "CC BY 4.0", "CC0 Public Domain", "Apache 2.0"
    }


def test_nationality_and_club_filters_combine(graph):
    """Both filters must apply -- picking one index must not drop the other."""

    everyone = q.search_players(graph, club="Real Madrid", limit=0)
    brazilians = q.search_players(graph, nationality="Brazil", club="Real Madrid", limit=0)
    assert 0 < len(brazilians) < len(everyone)
    assert all(p.nationality == "Brazil" for p in brazilians)
    assert any(p.nationality != "Brazil" for p in everyone)

    # ... and the same when the club index is the one that gets picked.
    gremio = q.search_players(graph, nationality="Brazil", club="Grêmio", limit=0)
    assert gremio and all(p.club_team_id == "gremio-rs" for p in gremio)
    assert q.search_players(graph, nationality="Argentina", club="Grêmio", limit=0) == []


def test_club_filter_falls_back_to_the_raw_fifa_club_string(graph):
    """European clubs are not in the match graph, but are still searchable."""

    players = q.search_players(graph, club="Real Madrid", limit=0)
    assert players
    assert all("Real Madrid" in (p.club_raw or "") for p in players)


@pytest.mark.parametrize("scope", ["home", "HOME", "Home", " home "])
def test_scope_arguments_are_case_insensitive(graph, scope):
    record = q.team_record(graph, "Corinthians", competition="brasileirao",
                           season=2022, scope=scope)
    assert record.played == 19


def test_an_unrecognised_scope_falls_back_to_all(graph):
    record = q.team_record(graph, "Corinthians", competition="brasileirao",
                           season=2022, scope="sideways")
    assert record.played == 38


def test_fifa_clubs_only_link_to_top_flight_brazilian_teams(graph):
    """FIFA 19 ships 20-player top-division squads and nothing else.

    Two homonyms would otherwise sneak in: "Inter" (Milan) shares a nickname
    with Internacional, and "Boavista FC" of Porto normalises to the same key
    as Boavista of Rio.  Every linked squad must be exactly 20 Brazilians.
    """

    assert len(graph.players_by_club_team) == 15
    for team_id, squad in graph.players_by_club_team.items():
        assert len(squad) == 20, f"{team_id} has {len(squad)} players"
        assert {p.nationality for p in squad} == {"Brazil"}, team_id
        assert "serie-a" in graph.team_competitions[team_id]
    assert "boavista-rj" not in graph.players_by_club_team
    assert {p.club_raw for p in graph.players_by_club_team["internacional-rs"]} == {
        "Internacional"
    }


def test_nicknames_never_resolve_dataset_names(graph):
    """Nicknames are for user search only, not for binding raw club strings."""

    assert graph.registry.lookup("Inter", brazilian_only=True) is None
    assert graph.registry.lookup("Galo", brazilian_only=True) is None
    assert graph.registry.search("Inter")[0].id == "internacional-rs"
    assert graph.registry.search("Galo")[0].id == "atletico-mg"
