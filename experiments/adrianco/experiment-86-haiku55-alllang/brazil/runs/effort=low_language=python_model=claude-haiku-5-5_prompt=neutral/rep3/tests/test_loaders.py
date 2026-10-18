"""Feature: every provided CSV loads, and bad rows are skipped and counted."""

from brazsoccer_mcp.loaders import (
    BRASILEIRAO,
    COPA_DO_BRASIL,
    LIBERTADORES,
    load_all,
    load_libertadores,
)
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


def test_given_provided_data_when_loaded_then_all_six_files_contribute_rows():
    # Given the data/kaggle directory
    # When every loader runs
    matches, players, report = load_all(DATA_DIR)
    # Then each source reports rows and the player file is populated
    for source in ("brasileirao", "historical", "cup", "libertadores", "br_football"):
        assert report.rows[source] > 0, source
    assert report.rows["fifa"] == len(players) > 15000
    assert len(matches) == sum(report.rows[s] for s in report.rows if s != "fifa")


def test_given_libertadores_file_when_loaded_then_placeholder_rows_are_skipped(tmp_path):
    # Given a file with one played match and one unplayed NA fixture
    path = tmp_path / "lib.csv"
    path.write_text(
        '"datetime","home_team","away_team","home_goal","away_goal","season","stage"\n'
        '2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"\n'
        'NA,"Flamengo","Athletico","-","-",NA,"final"\n',
        encoding="utf-8",
    )
    # When it is loaded
    matches, skipped = load_libertadores(path)
    # Then only the played match is kept and the placeholder is counted as skipped
    assert skipped == 1
    assert len(matches) == 1
    assert matches[0].competition == LIBERTADORES
    assert matches[0].home == "Nacional"
    assert matches[0].stage == "group stage"


def test_given_data_when_loaded_then_competition_names_are_canonical(data):
    names = {m.competition for m in data.matches}
    assert {BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES} <= names


def test_given_fifa_file_then_bom_is_stripped_and_brazilians_are_present(data):
    # Given the FIFA export, which starts with a byte-order mark
    # When players are read
    # Then the Name column is found and Brazilian players exist
    assert any(p.nationality == "Brazil" for p in data.players)
    assert all(p.name for p in data.players)
