"""Query functions: correctness of the computed answers."""

import pytest

from brsoccer import queries as q
from brsoccer.data import COPA_DO_BRASIL, LIBERTADORES, SERIE_A


# ---------------------------------------------------------------- match queries

def test_fla_flu_matches_and_head_to_head(db):
    r = q.search_matches(team="Flamengo", opponent="Fluminense", limit=5, db=db)
    assert r["text"].startswith("Flamengo vs Fluminense (Fla-Flu derby):")
    assert "Head-to-head in dataset: Flamengo" in r["text"]
    data = r["data"]
    assert data["total"] > 30
    h2h = data["head_to_head"]
    assert h2h["Flamengo"] + h2h["Fluminense"] + h2h["draws"] == data["total"]
    for m in data["matches"]:
        assert {m["home_team"], m["away_team"]} == {"Flamengo", "Fluminense"}
    dates = [m["date"] for m in data["matches"]]
    assert dates == sorted(dates, reverse=True)


def test_matches_by_team_and_season(db):
    r = q.search_matches(team="Palmeiras", season=2023, limit=100, db=db)
    assert r["data"]["total"] >= 38
    assert all(m["season"] == 2023 for m in r["data"]["matches"])
    assert all("Palmeiras" in (m["home_team"], m["away_team"]) for m in r["data"]["matches"])


def test_matches_by_venue_and_date_range(db):
    r = q.search_matches(team="Santos", venue="home", date_from="01/01/2015", date_to="2015-12-31",
                         competition="Brasileirão", limit=100, db=db)
    assert r["data"]["total"] == 19
    assert all(m["home_team"] == "Santos" for m in r["data"]["matches"])
    assert all("2015-01-01" <= m["date"] <= "2015-12-31" for m in r["data"]["matches"])


def test_copa_do_brasil_finals(db):
    r = q.search_matches(competition="Copa do Brasil", stage="Final", limit=100, db=db)
    assert r["data"]["total"] == 24  # 12 seasons x 2 legs
    finals = {f["season"]: f["winner"] for f in q.finals(db=db)["data"]["finals"]}
    assert finals[2012] == "Palmeiras"
    assert finals[2013] == "Flamengo"
    assert finals[2014] == "Atlético Mineiro"
    assert finals[2016] == "Grêmio"
    assert finals[2018] == "Cruzeiro"
    assert finals[2019] == "Athletico Paranaense"
    assert finals[2020] == "Palmeiras"
    assert finals[2021] == "Atlético Mineiro"
    assert finals[2023] == "São Paulo"
    assert finals[2015] is None  # decided on penalties, not in the data


def test_last_meeting(db):
    r = q.head_to_head("Flamengo", "Corinthians", db=db)
    assert r["data"]["last_meeting"]["date"] == "2023-10-07"
    assert "Last meeting: 2023-10-07: Corinthians 1-1 Flamengo" in r["text"]


# ---------------------------------------------------------------- team queries

def test_corinthians_home_record_2022(db):
    r = q.team_record("Corinthians", season=2022, competition="Brasileirão", venue="home", db=db)
    d = r["data"]
    assert (d["played"], d["wins"], d["draws"], d["losses"]) == (19, 12, 4, 3)
    assert (d["goals_for"], d["goals_against"]) == (24, 11)
    assert "Corinthians home record (2022 Brasileirão Série A):" in r["text"]
    assert "Win rate: 63.2%" in r["text"]


def test_team_record_splits_add_up(db):
    d = q.team_record("Grêmio", db=db)["data"]
    assert d["home"]["played"] + d["away"]["played"] == d["played"]
    assert sum(c["played"] for c in d["by_competition"].values()) == d["played"]


def test_most_goals_in_season(db):
    r = q.team_rankings("goals_for", season=2019, limit=1, db=db)
    assert r["data"]["ranking"][0]["team"] == "Flamengo"
    assert r["data"]["ranking"][0]["goals_for"] == 86


def test_head_to_head_palmeiras_santos(db):
    d = q.head_to_head("Palmeiras", "Santos", db=db)["data"]
    assert d["derby"] == "Clássico da Saudade"
    assert d["wins_a"] + d["wins_b"] + d["draws"] == d["total"]
    assert set(d["by_competition"]) >= {SERIE_A, COPA_DO_BRASIL}


def test_team_profile_cross_file(db):
    d = q.team_profile("Palmeiras", db=db)["data"]
    assert set(d["competitions"]) == {SERIE_A, COPA_DO_BRASIL, LIBERTADORES}
    assert 2013 not in d["competitions"][SERIE_A]["seasons"]  # Série B that year
    assert {2016, 2018, 2022} <= set(d["brasileirao_titles"])
    santos = q.team_profile("Santos", db=db)["data"]
    assert len(santos["fifa_players"]) == 20


# ---------------------------------------------------------------- competition queries

def test_2019_standings(db):
    r = q.standings(2019, db=db)
    d = r["data"]
    top = d["table"][0]
    assert d["champion"] == "Flamengo"
    assert (top["points"], top["wins"], top["draws"], top["losses"]) == (90, 28, 6, 4)
    assert d["table"][1]["team"] == "Santos" and d["table"][1]["points"] == 74
    assert d["table"][2]["team"] == "Palmeiras" and d["table"][2]["points"] == 74
    assert "1. Flamengo - 90 pts (28W, 6D, 4L" in r["text"] and "Champion" in r["text"]
    assert len(d["table"]) == 20


def test_relegated_2020(db):
    d = q.standings(2020, db=db)["data"]
    assert set(d["relegated"]) == {"Vasco da Gama", "Goiás", "Coritiba", "Botafogo"}


def test_historical_standings_24_teams(db):
    d = q.standings(2003, db=db)["data"]
    assert len(d["table"]) == 24 and d["champion"] == "Cruzeiro"


def test_libertadores_2018_bracket(db):
    r = q.knockout_bracket(2018, "Libertadores", db=db)
    d = r["data"]
    assert d["champion"] == "River Plate"
    assert len(d["stages"]["Round of 16"]) == 8
    assert len(d["stages"]["Quarter-finals"]) == 4
    assert len(d["stages"]["Semi-finals"]) == 2
    assert d["stages"]["Final"][0]["aggregate"] in ("2-5", "5-3", "3-5", "5-2")
    # ties level on aggregate use the next round to show who advanced
    colo = next(t for t in d["stages"]["Round of 16"] if "Colo-Colo" in (t["team_a"], t["team_b"]))
    assert colo["winner"] == "Colo-Colo"


def test_standings_rejects_cup(db):
    with pytest.raises(q.QueryError):
        q.standings(2019, "Copa do Brasil", db=db)


# ---------------------------------------------------------------- statistics

def test_competition_stats(db):
    d = q.competition_stats("Brasileirão", db=db)["data"]
    assert 2.3 < d["avg_goals"] < 2.8
    assert abs(d["home_win_rate"] + d["draw_rate"] + d["away_win_rate"] - 100) < 0.2
    assert d["home_win_rate"] > d["away_win_rate"]


def test_best_away_record(db):
    d = q.team_rankings("win_rate", venue="away", db=db)["data"]
    rates = [r["win_rate"] for r in d["ranking"]]
    assert rates == sorted(rates, reverse=True)
    assert all(r["played"] >= 38 for r in d["ranking"])


def test_biggest_wins_sorted(db):
    d = q.biggest_wins(competition="Brasileirão", db=db)["data"]["matches"]
    margins = [abs(m["home_goals"] - m["away_goals"]) for m in d]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 6


def test_derbies_2023(db):
    d = q.derbies(season=2023, db=db)["data"]
    assert d["total"] > 20
    assert "Fla-Flu" in d["by_rivalry"] and "Grenal" in d["by_rivalry"]
    grenal = q.derbies(rivalry="grenal", db=db)["data"]
    assert set(grenal["by_rivalry"]) == {"Grenal"}


def test_compare_seasons(db):
    d = q.compare_seasons(2018, 2019, db=db)["data"]["seasons"]
    assert d[0]["champion"] == "Palmeiras" and d[1]["champion"] == "Flamengo"
    assert d[0]["matches"] == d[1]["matches"] == 380


# ---------------------------------------------------------------- players

def test_top_brazilian_players(db):
    r = q.brazilian_players_overview(db=db)
    assert r["data"]["top"][0]["name"] == "Neymar Jr"
    assert "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain" in r["text"]
    clubs = {c["club"]: c for c in r["data"]["brazilian_clubs"]}
    assert clubs["Grêmio"]["players"] == 20
    assert "Inter" not in clubs  # Inter (Milan) is not Internacional


def test_search_players_filters(db):
    d = q.search_players(nationality="Brazilian", min_overall=85, db=db)["data"]
    assert d["total"] >= 10
    assert all(p["nationality"] == "Brazil" and p["overall"] >= 85 for p in d["players"])
    fw = q.search_players(club="Santos", position="forwards", db=db)["data"]
    assert fw["total"] >= 1 and all(p["position"] in {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"}
                                    for p in fw["players"])
    assert all(p["club"] == "Santos" for p in fw["players"])  # not Santos Laguna


def test_player_profile_and_missing_player(db):
    r = q.player_profile("Neymar", db=db)
    assert r["data"]["found"] and r["data"]["player"]["overall"] == 92
    missing = q.player_profile("Gabriel Barbosa", db=db)
    assert not missing["data"]["found"]
    assert "Gabriel Jesus" in missing["text"]


def test_club_players_for_unlicensed_club(db):
    r = q.club_players("Flamengo", db=db)
    assert r["data"]["total"] == 0
    assert "not licensed" in r["text"]
    r = q.club_players("Gremio", db=db)
    assert r["data"]["total"] == 20 and "match_record" in r["data"]


# ---------------------------------------------------------------- input handling

def test_invalid_inputs_raise_query_errors(db):
    with pytest.raises(q.QueryError, match="No team matching"):
        q.team_record("Not A Real Club FC", db=db)
    with pytest.raises(q.QueryError, match="Unknown competition"):
        q.search_matches(team="Santos", competition="Premier League", db=db)
    with pytest.raises(q.QueryError, match="Season must be a year"):
        q.standings("last year", db=db)
    with pytest.raises(q.QueryError, match="Could not parse"):
        q.search_matches(team="Santos", date_from="yesterday", db=db)


def test_competition_parsing():
    assert q.parse_competition("Brasileirão") == SERIE_A
    assert q.parse_competition("serie a") == SERIE_A
    assert q.parse_competition("Copa Libertadores da América") == LIBERTADORES
    assert q.parse_competition("copa do brasil") == COPA_DO_BRASIL
    assert q.parse_competition("all") is None
