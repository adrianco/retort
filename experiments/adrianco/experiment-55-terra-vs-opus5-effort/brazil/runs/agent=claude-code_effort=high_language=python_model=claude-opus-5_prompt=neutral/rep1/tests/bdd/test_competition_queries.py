"""BDD scenarios for tests/features/competition_queries.feature."""

from __future__ import annotations

import pytest

from brazilian_soccer.queries import QueryError, standings
from tests.gwt import Scenario

pytestmark = pytest.mark.bdd


def test_final_standings_for_a_season(graph):
    with Scenario("Final standings for a season") as s:
        s.given("the match data is loaded", lambda: graph.matches)
        result = s.when("I request the 2019 Brasileirão standings",
                        lambda: standings(2019, "brasileirao", graph=graph))
        table = result["table"]
        s.then("Flamengo should be champion", result["champion"] == "Flamengo")
        s.and_("with 90 points from 28 wins, 6 draws and 4 losses",
               table[0]["points"] == 90 and table[0]["wins"] == 28
               and table[0]["draws"] == 6 and table[0]["losses"] == 4)
        s.and_("the table should have 20 teams", len(table) == 20)
        s.and_("Santos and Palmeiras should be second and third with 74 points",
               table[1]["team"] == "Santos" and table[1]["points"] == 74
               and table[2]["team"] == "Palmeiras" and table[2]["points"] == 74)
        s.and_("Santos should rank above Palmeiras on wins",
               table[1]["wins"] > table[2]["wins"])
        s.and_("every club should have played 38 matches",
               all(row["played"] == 38 for row in table))


def test_relegation_places(graph):
    with Scenario("Relegation places") as s:
        result = s.when("I request the 2020 Brasileirão standings",
                        lambda: standings(2020, "serie-a", graph=graph))
        s.then("four clubs should be listed as relegated",
               len(result["relegated"]) == 4)
        s.and_("they should be the bottom four of the table",
               result["relegated"] == [row["team"] for row in result["table"][-4:]])
        s.and_("the champion should be the top of the table",
               result["champion"] == result["table"][0]["team"])


def test_points_are_calculated_with_three_for_a_win(graph):
    with Scenario("Points are calculated with three for a win") as s:
        result = s.when("I request the 2018 Brasileirão standings",
                        lambda: standings(2018, "serie-a", graph=graph))
        s.then("every row's points should equal wins*3 + draws",
               all(row["points"] == row["wins"] * 3 + row["draws"]
                   for row in result["table"]))
        s.and_("goal difference should equal goals for minus against",
               all(row["goal_difference"] == row["goals_for"] - row["goals_against"]
                   for row in result["table"]))
        s.and_("total goals for should equal total goals against",
               sum(r["goals_for"] for r in result["table"])
               == sum(r["goals_against"] for r in result["table"]))
        s.and_("the table should be sorted by points descending",
               all(result["table"][i]["points"] >= result["table"][i + 1]["points"]
                   for i in range(len(result["table"]) - 1)))


def test_an_unavailable_season_is_refused_with_the_available_range(graph):
    with Scenario("An unavailable season is refused") as s:
        with pytest.raises(QueryError) as excinfo:
            s.when("I request the 1994 Brasileirão standings",
                   lambda: standings(1994, "serie-a", graph=graph))
        message = str(excinfo.value)
        s.then("the query should fail", "No " in message)
        s.and_("and state which seasons exist", "2003-2023" in message)


def test_knockout_competitions_are_not_presented_as_league_tables(graph):
    with Scenario("Knockout competitions are flagged") as s:
        result = s.when("I request the 2019 Copa do Brasil standings",
                        lambda: standings(2019, "copa-do-brasil", graph=graph))
        s.then("no champion should be claimed", result["champion"] is None)
        s.and_("the result should warn that it is a knockout competition",
               any("knockout" in note for note in result["notes"]))


def test_excluded_rows_do_not_make_a_partial_season_look_complete(graph):
    """A mislabelled fixture must not pad the count past the completeness bar.

    Built as a synthetic season: 20 clubs, one genuine fixture missing and one
    junk row added, so the raw total is still 380.  The junk row is excluded
    from the table, so the season must be reported as partial.
    """
    import datetime as dt
    from types import SimpleNamespace

    from brazilian_soccer.models import Match

    teams = [f"club-{i:02d}" for i in range(20)]
    fixtures, index = [], 0
    for home in teams:
        for away in teams:
            if home == away:
                continue
            index += 1
            fixtures.append(Match(
                match_id=f"m{index:05d}", competition="serie-a", season=2050,
                date=dt.date(2050, 1, 1) + dt.timedelta(days=index % 300),
                home_slug=home, away_slug=away, home_name=home, away_name=away,
                home_goals=1 if home == "club-00" else 0, away_goals=0))
    fixtures.pop()
    fixtures.append(Match(
        match_id="junk", competition="serie-a", season=2050,
        date=dt.date(2050, 6, 1), home_slug="junk-a", away_slug="junk-b",
        home_name="Junk A", away_name="Junk B", home_goals=0, away_goals=0))
    stub = SimpleNamespace(
        matches_by_comp_season={("serie-a", 2050): fixtures},
        competition_seasons=lambda slug: [2050], team_name=lambda slug: slug)

    with Scenario("Excluded rows cannot fake a complete season") as s:
        table = s.when("I ask for the standings of the synthetic season",
                       lambda: standings(2050, "serie-a", graph=stub))
        s.then("no champion should be claimed", table["champion"] is None)
        s.and_("no relegation should be claimed", table["relegated"] == [])
        s.and_("the partial-data caveat should be given",
               any("partial" in note for note in table["notes"]))
        s.and_("the junk clubs should be reported as excluded",
               {row["team"] for row in table["excluded"]} == {"junk-a", "junk-b"})


def test_champions_match_the_historical_record(graph):
    """Spot-check the computed champions against the real Brasileirão roll."""
    expected = {
        2003: "Cruzeiro", 2004: "Santos", 2005: "Corinthians",
        2006: "São Paulo", 2007: "São Paulo", 2008: "São Paulo",
        2009: "Flamengo", 2010: "Fluminense", 2011: "Corinthians",
        2012: "Fluminense", 2013: "Cruzeiro", 2014: "Cruzeiro",
        2015: "Corinthians", 2016: "Palmeiras", 2017: "Corinthians",
        2018: "Palmeiras", 2019: "Flamengo", 2020: "Flamengo",
        2021: "Atlético Mineiro", 2022: "Palmeiras",
    }
    with Scenario("Computed champions match history") as s:
        computed = s.when("I compute the champion of each season",
                          lambda: {year: standings(year, "serie-a", graph=graph)["champion"]
                                   for year in expected})
        s.then("every champion should match the historical record",
               computed == expected)
