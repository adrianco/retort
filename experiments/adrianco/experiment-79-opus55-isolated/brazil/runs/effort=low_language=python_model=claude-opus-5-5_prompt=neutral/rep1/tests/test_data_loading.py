"""Feature: Data coverage - all six CSV files are loadable and queryable."""

from collections import Counter

from brazilian_soccer.data import MATCH_FILES


def test_every_csv_file_is_fully_read(db):
    # Given the data is loaded / Then each file contributed its documented row count
    expected = {"Brasileirao_Matches.csv": 4180, "Brazilian_Cup_Matches.csv": 1337,
                "Libertadores_Matches.csv": 1255, "BR-Football-Dataset.csv": 10296,
                "novo_campeonato_brasileiro.csv": 6886}
    assert {name: db.load_report[name]["rows"] for name in MATCH_FILES} == expected
    assert len(db.players) == 18207


def test_every_match_file_is_queryable(db):
    sources = Counter(source for m in db.matches for source in m.sources)
    assert set(sources) == set(MATCH_FILES)
    assert all(count > 1000 for count in sources.values())


def test_fixtures_present_in_several_files_are_merged_not_double_counted(db):
    # Brasileirão 2012-2019 appears in three files; each season has 380 fixtures.
    per_season = Counter(m.season for m in db.matches if m.competition == "Brasileirão")
    for season in range(2006, 2023):
        assert per_season[season] == 380, season
    merged = [m for m in db.matches if len(m.sources) == 3]
    assert merged, "expected fixtures found in three files"


def test_merged_fixture_combines_information_from_each_file(db):
    # When a fixture is in the round file, the arena file and the statistics file
    match = next(m for m in db.matches if len(m.sources) == 3)
    # Then it carries the round, the stadium and the extended statistics
    assert match.round and match.arena and "total_corners" in match.stats


def test_rows_without_a_score_are_skipped(db):
    assert db.load_report["Libertadores_Matches.csv"]["skipped"] == 2
    assert all(isinstance(m.home_goals, int) and isinstance(m.away_goals, int) for m in db.matches)


def test_utf8_names_survive_loading(db):
    assert {"São Paulo", "Grêmio", "Avaí", "Ceará", "Goiás"} <= db.registry.names
    assert any(p["name"] == "Neymar Jr" for p in db.players)


def test_team_variants_collapse_to_one_team(db):
    names = db.registry.names
    assert "Palmeiras" in names and "Palmeiras-SP" not in names
    assert not any(n.startswith("Flamengo-RJ") or n == "Flamengo RJ" for n in names)
    assert {"Botafogo", "Botafogo-PB", "Botafogo-SP"} <= names
