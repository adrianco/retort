"""Loading, cleaning and merging of the six CSV files."""

from collections import Counter
from datetime import date

from brsoccer.data import (COPA_DO_BRASIL, FILES, LIBERTADORES, SERIE_A, SERIE_B, SERIE_C, parse_date)


def test_all_six_files_load_with_expected_row_counts(db):
    assert db.source_rows == {
        "Brasileirao_Matches.csv": 4180,
        "novo_campeonato_brasileiro.csv": 6886,
        "Brazilian_Cup_Matches.csv": 1337,
        "Libertadores_Matches.csv": 1255,
        "BR-Football-Dataset.csv": 10296,
        "fifa_data.csv": 18207,
    }
    assert len(db.players) == 18207


def test_every_match_file_contributes(db):
    contributing = Counter(src for m in db.matches for src in m.sources)
    for key in ("brasileirao", "historical", "cup", "libertadores", "extended"):
        assert contributing[FILES[key]] > 500, key


def test_date_formats():
    assert parse_date("2023-09-24") == date(2023, 9, 24)
    assert parse_date("29/03/2003") == date(2003, 3, 29)
    assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)
    assert parse_date("NA") is None
    assert parse_date("") is None


def test_serie_a_seasons_complete_without_duplicates(db):
    """Overlapping files (2012-2019 appear in three files) must be merged, not double counted."""
    for season in range(2006, 2023):
        ms = [m for m in db.matches if m.competition == SERIE_A and m.season == season]
        teams = Counter(t.id for m in ms for t in (m.home, m.away))
        assert len(ms) == 380, season
        assert len(teams) == 20, season
        assert set(teams.values()) == {38}, season
    assert sum(1 for m in db.matches if m.competition == SERIE_A and m.season == 2003) == 552


def test_overlapping_sources_merged_into_single_match(db):
    m = next(m for m in db.matches if m.competition == SERIE_A and m.season == 2019
             and m.home.id == "flamengo" and m.away.id == "cruzeiro")
    assert (m.home_goals, m.away_goals) == (3, 1)
    assert set(m.sources) == {FILES["brasileirao"], FILES["historical"], FILES["extended"]}
    assert m.arena == "Maracanã"           # from novo_campeonato_brasileiro.csv
    assert "home_shots" in m.stats          # from BR-Football-Dataset.csv


def test_competitions_and_seasons_covered(db):
    seasons = {c: {m.season for m in db.matches if m.competition == c}
               for c in (SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES)}
    assert seasons[SERIE_A] == set(range(2003, 2024))
    assert seasons[COPA_DO_BRASIL] == set(range(2012, 2024))
    assert seasons[LIBERTADORES] == set(range(2013, 2023))
    assert min(seasons[SERIE_B]) == 2014 and min(seasons[SERIE_C]) == 2014


def test_utf8_names_preserved(db):
    names = {t.name for t in db.teams.values()}
    assert {"São Paulo", "Grêmio", "Avaí", "Criciúma", "Goiás"} <= names
    assert any(p.name == "Thiago Silva" and p.nationality == "Brazil" for p in db.players)
    assert any("ã" in p.club or "é" in p.club for p in db.players)


def test_extended_file_uses_learned_aliases(db):
    """Minor clubs spelt differently in BR-Football are mapped onto the cup file spelling."""
    assert db.find_team("Brasil de Pelotas").id == "brasil-rs"


def test_find_team_variants(db):
    for q, expected in [("Fla", "flamengo"), ("sao paulo fc", "sao-paulo"), ("Atletico", "atletico-mineiro"),
                        ("Palmeiras-SP", "palmeiras"), ("galo", "atletico-mineiro"), ("Boca", "boca-juniors")]:
        assert db.find_team(q).id == expected, q
    assert db.find_team("zzzz not a team") is None


def test_player_parsing(db):
    neymar = next(p for p in db.players if p.name == "Neymar Jr")
    assert neymar.overall == 92 and neymar.club == "Paris Saint-Germain" and neymar.position == "LW"
    assert neymar.height_cm == 175 and neymar.value_eur == 118.5e6
    assert neymar.attributes["Dribbling"] == 96
    brazilian_clubs = {p.club_team.name for p in db.players if p.club_team}
    assert "Santos" in brazilian_clubs and "Grêmio" in brazilian_clubs
    assert not any(p.club in ("Inter", "Club América", "Santos Laguna") and p.club_team for p in db.players)
