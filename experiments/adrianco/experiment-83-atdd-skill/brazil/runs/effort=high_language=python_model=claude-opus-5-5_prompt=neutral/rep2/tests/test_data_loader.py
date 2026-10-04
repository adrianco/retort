from collections import Counter
from datetime import date

import pytest

from data_loader import (
    COPA_DO_BRASIL,
    FILES,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    parse_date,
    resolve_competition,
)


def test_all_six_files_loaded(data):
    assert set(data.raw_counts) == set(FILES.values())
    assert data.raw_counts["Brasileirao_Matches.csv"] == 4180
    assert data.raw_counts["Brazilian_Cup_Matches.csv"] == 1337
    assert data.raw_counts["Libertadores_Matches.csv"] == 1255
    assert data.raw_counts["BR-Football-Dataset.csv"] == 10296
    assert data.raw_counts["novo_campeonato_brasileiro.csv"] == 6886
    assert data.raw_counts["fifa_data.csv"] == 18207
    assert len(data.players) == 18207
    # Every match file contributes records to the unified match list.
    sources = Counter(s for m in data.matches for s in m.sources)
    for f in ("Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv",
              "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv"):
        assert sources[f] > 1000


@pytest.mark.parametrize("value,expected", [
    ("2023-09-24", date(2023, 9, 24)),
    ("29/03/2003", date(2003, 3, 29)),
    ("2012-05-19 18:30:00", date(2012, 5, 19)),
    ("NA", None),
    ("", None),
])
def test_parse_date_formats(value, expected):
    assert parse_date(value) == expected


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError):
        parse_date("next tuesday")


@pytest.mark.parametrize("text,expected", [
    ("Brasileirão", SERIE_A), ("serie a", SERIE_A), ("Campeonato Brasileiro", SERIE_A),
    ("Série B", SERIE_B), ("copa do brasil", COPA_DO_BRASIL), ("Libertadores", LIBERTADORES),
    ("Copa Libertadores", LIBERTADORES), (None, None), ("all", None),
])
def test_resolve_competition(text, expected):
    assert resolve_competition(text) == expected


def test_resolve_competition_unknown():
    with pytest.raises(ValueError):
        resolve_competition("Premier League")


def test_serie_a_deduplicated_to_full_seasons(data):
    per_season = Counter(m.season for m in data.matches if m.competition == SERIE_A)
    assert per_season[2003] == 552 and per_season[2004] == 552 and per_season[2005] == 462
    for season in range(2006, 2023):
        assert per_season[season] == 380, season
        teams = {t for m in data.matches if m.competition == SERIE_A and m.season == season
                 for t in (m.home_id, m.away_id)}
        assert len(teams) == 20, season
    assert 370 <= per_season[2023] <= 380  # only in BR-Football-Dataset.csv


def test_overlapping_files_are_merged(data):
    merged = [m for m in data.matches if len(m.sources) == 3]
    assert merged, "2014-2019 Série A matches appear in three files"
    m = merged[0]
    assert m.source == "Brasileirao_Matches.csv"
    assert m.arena  # from novo_campeonato_brasileiro.csv
    assert m.stats and "home_corner" in m.stats  # from BR-Football-Dataset.csv


def test_covid_season_assignment(data):
    # The 2020 season finished in February 2021.
    late = [m for m in data.matches if m.competition == SERIE_A and m.date and m.date.year == 2021
            and m.date.month <= 2]
    assert late and all(m.season == 2020 for m in late)


def test_unplayed_rows_skipped(data):
    assert data.skipped_counts["Brasileirao_Matches.csv"] == 82
    assert all(isinstance(m.home_goals, int) and isinstance(m.away_goals, int) for m in data.matches)


def test_copa_do_brasil_finals_identified(data):
    finals = Counter(m.season for m in data.matches if m.competition == COPA_DO_BRASIL and m.stage == "final")
    assert sorted(finals) == list(range(2012, 2024))
    assert all(n == 2 for n in finals.values())


def test_utf8_names_preserved(data):
    assert data.team_name("sao paulo") == "São Paulo"
    assert data.team_name("gremio") == "Grêmio"
    assert any(p.name == "L. Modrić" for p in data.players)
    assert any(p.club == "Grêmio" for p in data.players)


def test_libertadores_stages(data):
    stages = Counter(m.stage for m in data.matches if m.competition == LIBERTADORES)
    assert set(stages) == {"group stage", "round of 16", "quarterfinals", "semifinals", "final"}
