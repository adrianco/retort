import csv
import re

import pytest

from data_loader import COPA_DO_BRASIL, DEFAULT_DATA_DIR, SERIE_A
from queries import QueryError


# ------------------------------------------------------------- team resolution
@pytest.mark.parametrize("text,team_id", [
    ("Flamengo", "flamengo"), ("flamengo", "flamengo"), ("Sao Paulo", "sao paulo"), ("São Paulo FC", "sao paulo"),
    ("Atletico Mineiro", "atletico-mg"), ("Palmeiras-SP", "palmeiras"), ("Vasco da Gama", "vasco"),
    ("Gremio", "gremio"), ("Internacional", "internacional"), ("Boca Juniors", "boca juniors"),
    ("Sport Club Corinthians Paulista", "corinthians"), ("Bragantino", "bragantino"),
])
def test_resolve_team(q, text, team_id):
    assert q.resolve_team(text) == team_id


def test_resolve_team_unknown(q):
    with pytest.raises(QueryError):
        q.resolve_team("Zzzzz Qqqq United")


# ------------------------------------------------------------- matches
def test_filter_matches_by_team_and_season(q):
    ms = q.filter_matches("Palmeiras", season=2019, competition="Brasileirão")
    assert len(ms) == 38
    assert all(m.involves("palmeiras") and m.season == 2019 for m in ms)
    assert ms == sorted(ms, key=lambda m: m.date, reverse=True)


def test_filter_matches_by_venue_and_dates(q):
    home = q.filter_matches("Flamengo", season=2019, competition="serie a", venue="home")
    assert len(home) == 19 and all(m.home_id == "flamengo" for m in home)
    window = q.filter_matches("Flamengo", date_from="2019-11-01", date_to="30/11/2019")
    assert window and all(m.date.year == 2019 and m.date.month == 11 for m in window)


def test_filter_matches_bad_inputs(q):
    with pytest.raises(QueryError):
        q.filter_matches("Flamengo", venue="neutral")
    with pytest.raises(QueryError):
        q.filter_matches("Flamengo", date_from="yesterday")
    with pytest.raises(QueryError):
        q.filter_matches("Flamengo", competition="Bundesliga")


def test_search_matches_output(q):
    out = q.search_matches("Flamengo", "Fluminense", limit=5)
    assert out.startswith("Matches — Flamengo, vs Fluminense")
    assert len(re.findall(r"^- \d{4}-\d{2}-\d{2}: ", out, re.M)) == 5
    assert "more matches in dataset" in out


def test_head_to_head_is_consistent(q):
    out = q.head_to_head("Flamengo", "Fluminense")
    assert "Fla-Flu derby" in out
    m = re.search(r"Head-to-head in dataset \((\d+) matches\): Flamengo (\d+) wins, Fluminense (\d+) wins, "
                  r"(\d+) draws", out)
    total, a, b, d = map(int, m.groups())
    assert a + b + d == total
    ms = q.filter_matches("Flamengo", "Fluminense")
    assert total == len(ms)
    assert a == sum(1 for x in ms if x.winner_id == "flamengo")


def test_head_to_head_same_team(q):
    with pytest.raises(QueryError):
        q.head_to_head("Flamengo", "Flamengo-RJ")


# ------------------------------------------------------------- team records
def _raw_home_record(team, season):
    """Independent calculation straight from novo_campeonato_brasileiro.csv."""
    w = d = l = gf = ga = 0
    with open(DEFAULT_DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["Ano"] == str(season) and r["Equipe_mandante"] == team:
                h, a = int(r["Gols_mandante"]), int(r["Gols_visitante"])
                gf += h
                ga += a
                w += h > a
                d += h == a
                l += h < a
    return w, d, l, gf, ga


def test_team_record_matches_raw_csv(q):
    w, d, l, gf, ga = _raw_home_record("Corinthians", 2019)
    out = q.team_record("Corinthians", season=2019, competition="Brasileirão", venue="home")
    assert out.startswith("Corinthians home record (2019, Brasileirão Série A):")
    assert f"- Matches: {w + d + l}" in out
    assert f"- Wins: {w}, Draws: {d}, Losses: {l}" in out
    assert f"- Goals For: {gf}, Goals Against: {ga}" in out
    assert f"- Win rate: {100 * w / (w + d + l):.1f}%" in out


def test_team_record_all_competitions_breakdown(q):
    out = q.team_record("Palmeiras", season=2018)
    assert "By competition:" in out
    assert "Copa Libertadores" in out and "Copa do Brasil" in out and SERIE_A in out


# ------------------------------------------------------------- standings
def test_standings_2019_matches_known_table(q):
    rows = q.standings_table("Brasileirão", 2019)
    assert len(rows) == 20
    top = [(r.team, r.record.points, r.record.wins, r.record.draws, r.record.losses) for r in rows[:3]]
    assert top == [("Flamengo", 90, 28, 6, 4), ("Santos", 74, 22, 8, 8), ("Palmeiras", 74, 21, 11, 6)]
    assert rows[0].note == "Champion"
    out = q.standings(2019, top=3)
    assert "1. Flamengo - 90 pts (28W, 6D, 4L" in out and "Champion" in out


def test_standings_relegation_2020(q):
    relegated = {r.team for r in q.standings_table("serie a", 2020) if r.note == "Relegated"}
    assert relegated == {"Vasco da Gama", "Goiás", "Coritiba", "Botafogo"}


@pytest.mark.parametrize("season,champion", [
    (2006, "São Paulo"), (2007, "São Paulo"), (2008, "São Paulo"), (2009, "Flamengo"), (2010, "Fluminense"),
    (2011, "Corinthians"), (2012, "Fluminense"), (2013, "Cruzeiro"), (2014, "Cruzeiro"), (2015, "Corinthians"),
    (2016, "Palmeiras"), (2017, "Corinthians"), (2018, "Palmeiras"), (2019, "Flamengo"), (2020, "Flamengo"),
    (2021, "Atlético Mineiro"), (2022, "Palmeiras"),
])
def test_calculated_champions_match_history(q, season, champion):
    assert q.standings_table(SERIE_A, season)[0].team == champion


def test_incomplete_season_uses_soft_labels(q):
    # 2023 is only in BR-Football-Dataset.csv, which is missing 3 matches.
    rows = q.standings_table(SERIE_A, 2023)
    assert rows[0].note == "Leader"
    assert sum(r.note == "Relegation zone" for r in rows) == 4
    assert "table is incomplete" in q.standings(2023)


def test_points_conservation(q):
    rows = q.standings_table(SERIE_A, 2015)
    played = sum(r.record.played for r in rows)
    assert played == 2 * 380
    assert sum(r.record.goals_for for r in rows) == sum(r.record.goals_against for r in rows)
    assert sum(r.record.wins for r in rows) == sum(r.record.losses for r in rows)


def test_standings_rejects_cups(q):
    with pytest.raises(QueryError):
        q.standings(2019, "Libertadores")


def test_standings_no_data(q):
    assert "No Brasileirão Série A matches for 1990" in q.standings(1990)


# ------------------------------------------------------------- rankings & stats
def test_rankings_most_goals_2019(q):
    out = q.team_rankings("goals_for", "Brasileirão", 2019, limit=3)
    assert out.splitlines()[1].startswith("1. Flamengo - 86 goals scored")


def test_rankings_best_defence_is_ascending(q):
    out = q.team_rankings("goals_against", "Brasileirão", 2018, limit=1)
    assert "lowest first" in out and "1. Palmeiras - 26 goals conceded" in out


def test_rankings_home_and_away(q):
    home = q.team_rankings("win_rate", venue="home", limit=3)
    away = q.team_rankings("win_rate", venue="away", limit=3)
    assert "home matches only" in home and "away matches only" in away
    pct = [float(x) for x in re.findall(r" - ([\d.]+)%", home)]
    assert pct == sorted(pct, reverse=True)


def test_rankings_unknown_metric(q):
    with pytest.raises(QueryError):
        q.team_rankings("style points")


def test_competition_stats(q):
    out = q.competition_stats("Brasileirão")
    avg = float(re.search(r"Average goals per match: ([\d.]+)", out).group(1))
    assert 2.0 < avg < 3.0
    assert "Home win rate:" in out and "Corners per match" in out


def test_competition_stats_all(q):
    out = q.competition_stats()
    assert "By competition:" in out and "Copa Libertadores" in out


def test_biggest_wins_sorted(q):
    out = q.biggest_wins(limit=10)
    margins = [int(x) for x in re.findall(r"margin (\d+)", out)]
    assert len(margins) == 10 and margins == sorted(margins, reverse=True)
    assert "Average goals per match:" in out and "Home win rate:" in out


def test_biggest_wins_for_team(q):
    out = q.biggest_wins(team="Flamengo", competition="Brasileirão", limit=3)
    assert out.count("Flamengo") >= 3


def test_compare_seasons(q):
    out = q.compare_seasons([2018, 2019])
    assert "2018:" in out and "2019:" in out
    assert "Champion (calculated): Palmeiras" in out and "Champion (calculated): Flamengo" in out


def test_team_trend(q):
    out = q.team_trend("Flamengo")
    assert "- 2019: 1st of 20, 90 pts" in out


# ------------------------------------------------------------- cups and derbies
def test_copa_do_brasil_finals(q):
    out = q.knockout_results("Copa do Brasil", stage="final")
    assert "2023 final:" in out and "São Paulo champion" in out
    assert "2012 final:" in out and "Palmeiras champion" in out


def test_libertadores_bracket_2018(q):
    out = q.knockout_results("Libertadores", 2018)
    for stage in ("round of 16", "quarterfinals", "semifinals", "final"):
        assert f"2018 {stage}:" in out
    assert "group stage" not in out
    assert "River Plate champion" in out


def test_libertadores_single_leg_final(q):
    out = q.knockout_results("Libertadores", 2019, "final")
    assert "Flamengo 2-1 River Plate — Flamengo champion" in out


def test_knockout_rejects_league(q):
    with pytest.raises(QueryError):
        q.knockout_results("Brasileirão")


def test_derbies(q):
    out = q.derby_matches(season=2023)
    assert "Fla-Flu" in out and "Grenal" in out and "Derby Paulista" in out
    only = q.derby_matches(derby="Grenal")
    assert "[Fla-Flu]" not in only and "[Grenal]" in only


# ------------------------------------------------------------- players
def test_brazilian_players(q):
    players = q.find_players(nationality="Brazilian")
    assert len(players) == 827
    assert players[0].name == "Neymar Jr"
    assert all(p.nationality == "Brazil" for p in players)


def test_players_by_club_and_position(q):
    fwd = q.find_players(club="Santos", position="forwards")
    assert fwd and all(p.club == "Santos" and p.position in {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"}
                       for p in fwd)
    gremio = q.find_players(club="Gremio")
    assert len(gremio) == 20 and all(p.club == "Grêmio" for p in gremio)


def test_foreign_club_substring(q):
    assert {p.club for p in q.find_players(club="Real Madrid")} == {"Real Madrid"}


def test_unlicensed_club_message(q):
    out = q.search_players(club="Flamengo")
    assert "FIFA 19 has no squad for Flamengo" in out


def test_name_search_accent_insensitive(q):
    assert q.find_players(name="Modric")[0].name == "L. Modrić"
    assert q.find_players(name="Lionel Messi")[0].name == "L. Messi"
    # A single-letter initial alone must not match ('Neymar' is not 'N. Kanté').
    assert [p.name for p in q.find_players(name="Neymar")] == ["Neymar Jr"]


def test_player_profile_cross_file(q):
    out = q.player_profile("Neymar")
    assert "Overall: 92" in out and "Paris Saint-Germain" in out
    # A player at a Brazilian club is linked to that club's match data.
    gremio_star = q.find_players(club="Grêmio")[0]
    out = q.player_profile(gremio_star.name)
    assert "Club in match data: Grêmio" in out


def test_player_profile_not_found(q):
    out = q.player_profile("Gabriel Barbosa")
    assert "No player named 'Gabriel Barbosa'" in out and "Gabriel Jesus" in out


def test_search_players_requires_filter(q):
    with pytest.raises(QueryError):
        q.search_players()


def test_sort_by_skill(q):
    out = q.search_players(nationality="Brazil", sort_by="Finishing", limit=3)
    vals = [int(x) for x in re.findall(r"Finishing: (\d+)", out)]
    assert len(vals) == 3 and vals == sorted(vals, reverse=True)


def test_player_club_summary(q):
    out = q.player_club_summary()
    assert "Brazil players in dataset: 827" in out
    assert "Brazil players at Brazilian clubs:" in out
    assert re.search(r"- Grêmio: \d+ players \(avg rating: \d+\)", out)


def test_team_overview_cross_file(q):
    out = q.team_overview("Grêmio")
    assert "Copa Libertadores" in out and COPA_DO_BRASIL in out and SERIE_A in out
    assert "FIFA 19 squad (Grêmio)" in out
    assert "Grenal" in out


def test_find_team(q):
    out = q.find_team("atletico")
    assert "atletico-mg" in out and "athletico-pr" in out and "atletico-go" in out
