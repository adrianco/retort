"""BDD-style scenarios (Given the data is loaded / When ... / Then ...) for the
five capability areas of the specification."""
import datetime as dt
import time

import pytest

from brazilian_soccer_mcp.data import COPA_BR, LIBERTADORES, SERIE_A


# ---------------------------------------------------------------- data coverage
class TestDataCoverage:
    def test_all_six_files_are_loaded(self, kb):
        s = kb.summary()
        assert s["source_rows"] == {
            "Brasileirao_Matches.csv": 4180, "novo_campeonato_brasileiro.csv": 6886,
            "Brazilian_Cup_Matches.csv": 1337, "BR-Football-Dataset.csv": 10296,
            "Libertadores_Matches.csv": 1254,  # 1255 rows minus one undated placeholder
        }
        assert s["players"] == 18207

    def test_every_file_is_queryable(self, kb):
        sources = {src for m in kb.matches for src in m.sources}
        assert len(sources) == 5

    def test_fixtures_reported_by_several_files_are_merged(self, kb):
        # Then each Serie A season 2006-2022 has exactly 380 unique matches
        for season in range(2006, 2023):
            if season == 2015:
                continue  # one stray non-league row in the source
            assert len(kb.search_matches(competition="Serie A", season=season)) == 380, season
        m = kb.search_matches("Flamengo", "Corinthians", season=2019, venue="home",
                              competition="Brasileirão")[0]
        assert len(m.sources) == 3 and m.arena and m.stats and m.round


# --------------------------------------------------------------- match queries
class TestMatchQueries:
    def test_find_matches_between_two_teams(self, kb):
        # When I search for matches between "Flamengo" and "Fluminense"
        ms = kb.search_matches("Flamengo", "Fluminense")
        # Then I should receive a list of matches with date, scores and competition
        assert len(ms) > 30
        for m in ms:
            assert {m.home, m.away} == {"Flamengo", "Fluminense"}
            assert m.date and m.competition and m.played
        assert ms == sorted(ms, key=lambda m: m.date, reverse=True)

    def test_matches_by_team_and_season(self, kb):
        ms = kb.search_matches("Palmeiras", season=2023)
        assert ms and all(m.season == 2023 and "Palmeiras" in (m.home, m.away) for m in ms)

    def test_home_and_away_filters(self, kb):
        home = kb.search_matches("Santos", venue="home", season=2019, competition="Brasileirão")
        away = kb.search_matches("Santos", venue="away", season=2019, competition="Brasileirão")
        assert len(home) == len(away) == 19
        assert all(m.home == "Santos" for m in home) and all(m.away == "Santos" for m in away)

    def test_date_range_accepts_both_formats(self, kb):
        ms = kb.search_matches(date_from="01/05/2019", date_to="2019-05-31")
        assert ms and all(dt.date(2019, 5, 1) <= m.date <= dt.date(2019, 5, 31) for m in ms)

    @pytest.mark.parametrize("name, comp", [("Brasileirão", SERIE_A), ("serie a", SERIE_A),
                                            ("Copa do Brasil", COPA_BR), ("libertadores", LIBERTADORES)])
    def test_by_competition(self, kb, name, comp):
        ms = kb.search_matches(competition=name, season=2018)
        assert ms and all(m.competition == comp for m in ms)

    def test_copa_do_brasil_finals(self, kb):
        finals = kb.search_matches(competition="Copa do Brasil", stage="final")
        by_season = {m.season: {m.home, m.away} for m in finals}
        assert by_season[2019] == {"Athletico-PR", "Internacional"}
        assert by_season[2018] == {"Cruzeiro", "Corinthians"}
        assert by_season[2015] == {"Palmeiras", "Santos"}

    def test_last_meeting(self, kb):
        last = kb.search_matches("Flamengo", "Corinthians")[0]
        assert last.date == max(m.date for m in kb.search_matches("Corinthians", "Flamengo"))
        assert last.home_goals is not None and last.away_goals is not None

    def test_unknown_team_and_competition_are_reported(self, kb):
        with pytest.raises(ValueError):
            kb.search_matches("Real Madrid")
        with pytest.raises(ValueError):
            kb.search_matches(competition="Premier League")

    def test_derbies_in_a_season(self, kb):
        ds = kb.derbies(season=2023)
        names = {name for name, _ in ds}
        assert {"Fla-Flu", "Grenal", "Derby Paulista"} <= names
        assert all(m.season == 2023 for _, m in ds)


# ---------------------------------------------------------------- team queries
class TestTeamQueries:
    def test_team_statistics_for_a_season(self, kb):
        # When I request statistics for "Palmeiras" in season "2023"
        r = kb.team_stats("Palmeiras", season=2023)
        # Then I should receive wins, losses, draws, and goals
        assert r["matches"] == r["wins"] + r["draws"] + r["losses"] > 30
        assert r["goals_for"] > 0 and r["goals_against"] > 0

    def test_home_record(self, kb):
        r = kb.team_stats("Corinthians", season=2022, competition="Brasileirão", venue="home")
        assert (r["matches"], r["wins"], r["draws"], r["losses"]) == (19, 12, 4, 3)
        assert r["win_rate"] == 63.2

    def test_known_season_record(self, kb):
        r = kb.team_stats("Flamengo-RJ", season=2019, competition="Serie A")
        assert (r["wins"], r["draws"], r["losses"], r["points"]) == (28, 6, 4, 90)
        assert (r["goals_for"], r["goals_against"]) == (86, 37)

    def test_head_to_head(self, kb):
        h = kb.head_to_head("Palmeiras", "Santos")
        assert h["matches"] == h["team_a_wins"] + h["team_b_wins"] + h["draws"] > 30
        assert h["rivalry"] == "Clássico da Saudade"
        mirror = kb.head_to_head("Santos", "Palmeiras")
        assert mirror["team_a_wins"] == h["team_b_wins"] and mirror["draws"] == h["draws"]

    def test_most_goals_in_a_season(self, kb):
        top = kb.rank_teams("goals_for", "Serie A", 2019, limit=1)[0]
        assert (top["team"], top["goals_for"]) == ("Flamengo", 86)

    def test_competitions_a_team_played_in(self, kb):
        comps = {c["competition"] for c in kb.team_competitions("Palmeiras")}
        assert {SERIE_A, COPA_BR, LIBERTADORES} <= comps


# --------------------------------------------------------------- player queries
class TestPlayerQueries:
    def test_search_by_name(self, kb):
        assert kb.search_players(name="neymar")[0].name == "Neymar Jr"
        assert kb.get_player("Neymar Jr").overall == 92
        assert kb.get_player(190871).name == "Neymar Jr"

    def test_brazilian_players_sorted_by_rating(self, kb):
        ps = kb.search_players(nationality="Brazil", limit=None)
        assert len(ps) == 827 and all(p.nationality == "Brazil" for p in ps)
        assert ps[0].name == "Neymar Jr"
        assert [p.overall for p in ps] == sorted((p.overall for p in ps), reverse=True)

    def test_filter_by_club_uses_team_normalisation(self, kb):
        a = kb.search_players(club="Atlético-MG", limit=None)
        b = kb.search_players(club="Atletico Mineiro", limit=None)
        assert a and a == b and all(p.club == "Atlético Mineiro" for p in a)
        santos = kb.search_players(club="Santos", limit=None)
        assert santos and all(p.club == "Santos" for p in santos)  # not Santos Laguna

    def test_filter_by_position_group(self, kb):
        fw = kb.search_players(club="Grêmio", position="forwards", limit=None)
        assert fw and all(p.position in {"ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"} for p in fw)
        assert all(p.position == "GK" for p in kb.search_players(position="GK", limit=5))

    def test_club_missing_from_fifa_data_gives_empty_result(self, kb):
        assert kb.search_players(club="Flamengo") == []

    def test_brazilian_players_by_brazilian_club(self, kb):
        rows = kb.club_summary()
        clubs = {r["club"] for r in rows}
        assert {"Santos", "Grêmio", "Cruzeiro", "Atlético-MG"} <= clubs
        assert all(r["players"] > 0 and 40 < r["avg_overall"] < 95 for r in rows)

    def test_cross_file_team_profile(self, kb):
        p = kb.team_profile("Gremio")
        assert p["overall"]["matches"] > 500 and len(p["players"]) > 10
        assert all(pl.club == "Grêmio" for pl in p["players"])


# ---------------------------------------------------------- competition queries
class TestCompetitionQueries:
    def test_2019_champion_and_table(self, kb):
        s = kb.standings(2019)
        top = [(r["team"], r["points"], r["wins"], r["draws"], r["losses"]) for r in s["table"][:3]]
        assert top == [("Flamengo", 90, 28, 6, 4), ("Santos", 74, 22, 8, 8),
                       ("Palmeiras", 74, 21, 11, 6)]
        assert s["table"][0]["note"] == "Champion" and len(s["table"]) == 20

    @pytest.mark.parametrize("season, champion", [
        (2003, "Cruzeiro"), (2006, "São Paulo"), (2011, "Corinthians"), (2015, "Corinthians"),
        (2016, "Palmeiras"), (2018, "Palmeiras"), (2020, "Flamengo"), (2021, "Atlético-MG"),
        (2022, "Palmeiras")])
    def test_champions(self, kb, season, champion):
        assert kb.standings(season)["table"][0]["team"] == champion

    def test_relegated_teams_2020(self, kb):
        rel = {r["team"] for r in kb.standings(2020)["table"] if r["note"] == "Relegated"}
        assert rel == {"Vasco", "Goiás", "Coritiba", "Botafogo"}

    def test_incomplete_season_has_no_champion_label(self, kb):
        s = kb.standings(2023)
        assert not s["complete"] and all(r["note"] == "" for r in s["table"])

    def test_libertadores_bracket(self, kb):
        b = kb.bracket(2018)
        stages = [name for name, _ in b["stages"]]
        assert stages == ["group stage", "round of 16", "quarterfinals", "semifinals", "final"]
        final = dict(b["stages"])["final"]
        assert {final[0].home, final[0].away} == {"Boca Juniors", "River Plate"}

    def test_unknown_season(self, kb):
        with pytest.raises(ValueError):
            kb.standings(1990)


# --------------------------------------------------------- statistical analysis
class TestStatistics:
    def test_average_goals_per_match(self, kb):
        s = kb.competition_stats("Brasileirão")
        assert 2.2 < s["avg_goals"] < 2.9
        assert s["avg_goals"] == round(s["goals"] / s["matches"], 2)
        assert s["home_win_rate"] + s["draw_rate"] + s["away_win_rate"] == pytest.approx(100, abs=0.2)
        assert s["home_win_rate"] > s["away_win_rate"]

    def test_best_home_and_away_records(self, kb):
        home = kb.rank_teams("win_rate", "Serie A", venue="home", min_matches=100)
        away = kb.rank_teams("win_rate", "Serie A", venue="away", min_matches=100)
        assert [r["win_rate"] for r in home] == sorted((r["win_rate"] for r in home), reverse=True)
        assert all(r["matches"] >= 100 for r in home + away)
        assert home[0]["win_rate"] > away[0]["win_rate"]

    def test_biggest_wins(self, kb):
        ms = kb.biggest_wins(limit=10)
        margins = [abs(m.home_goals - m.away_goals) for m in ms]
        assert margins == sorted(margins, reverse=True) and margins[0] >= 7
        assert all("Santos" in (m.home, m.away) for m in kb.biggest_wins(team="Santos"))

    def test_compare_seasons(self, kb):
        a, b = kb.compare_seasons([2018, 2019])
        assert (a["season"], a["leader"]) == (2018, "Palmeiras")
        assert (b["season"], b["leader"]) == (2019, "Flamengo")
        assert a["matches"] == b["matches"] == 380 and a["goals"] != b["goals"]

    def test_extended_statistics_available(self, kb):
        m = kb.search_matches("Sao Paulo", "Flamengo", competition="Copa do Brasil",
                              date_from="2023-09-24", date_to="2023-09-24")[0]
        assert (m.home_goals, m.away_goals) == (1, 1)
        assert m.stats["home_corner"] == 2 and m.stats["away_shots"] == 13


# ------------------------------------------------------------------ performance
class TestPerformance:
    def test_simple_lookup_under_2_seconds(self, kb):
        t = time.perf_counter()
        kb.search_matches("Flamengo", "Fluminense")
        kb.search_players(name="Neymar")
        assert time.perf_counter() - t < 2

    def test_aggregate_queries_under_5_seconds(self, kb):
        t = time.perf_counter()
        kb.standings(2019)
        kb.rank_teams("win_rate", venue="away")
        kb.competition_stats()
        kb.biggest_wins()
        assert time.perf_counter() - t < 5
