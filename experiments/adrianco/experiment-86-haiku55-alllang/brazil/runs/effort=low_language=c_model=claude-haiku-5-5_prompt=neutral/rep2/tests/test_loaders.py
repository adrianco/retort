"""Scenarios for loading the provided Kaggle CSV files."""

import unittest
from pathlib import Path

from brazil_soccer_mcp.dataset import Dataset
from brazil_soccer_mcp.loaders import (
    load_brasileirao,
    load_cup,
    load_extended,
    load_historical,
    load_libertadores,
    load_matches,
    load_players,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


@unittest.skipUnless(DATA_DIR.exists(), "Kaggle CSVs not present")
class ProvidedDatasets(unittest.TestCase):
    def test_all_six_csv_files_are_loadable(self):
        """Given the six provided CSVs, each one loads with at least one usable row."""
        loaders = [load_brasileirao, load_cup, load_libertadores, load_historical, load_extended]
        names = ["Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv",
                 "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"]
        for loader, name in zip(loaders, names):
            with self.subTest(file=name):
                self.assertGreater(len(loader(DATA_DIR / name)), 0)
        self.assertGreater(len(load_players(DATA_DIR / "fifa_data.csv")), 18000)

    def test_unplayed_fixtures_with_na_scores_are_skipped(self):
        """Given Brasileirao_Matches.csv has 4,180 rows, the unplayed ones (NA scores) are dropped."""
        self.assertEqual(len(load_brasileirao(DATA_DIR / "Brasileirao_Matches.csv")), 4098)

    def test_overlapping_files_do_not_double_count_a_season(self):
        """Given several files cover the 2019 Série A, the season is counted once (380 matches)."""
        ds = Dataset.load(DATA_DIR)
        season = [m for m in ds.matches if m.season == 2019 and m.competition == "Brasileirão Série A"]
        self.assertEqual(len(season), 380)

    def test_dataset_answers_the_spec_lookups(self):
        """Given the loaded data, the spec's sample questions return results."""
        ds = Dataset.load(DATA_DIR)
        self.assertGreater(ds.find_matches("Flamengo", "Fluminense")["total"], 0)
        self.assertGreater(ds.team_record("Palmeiras", season=2023)["played"], 0)
        self.assertGreater(ds.search_players(nationality="Brazil", club="gremio")["total"], 0)
        self.assertGreater(len(ds.standings(2019)), 10)


class SourceSelection(unittest.TestCase):
    def test_one_source_is_kept_per_competition_and_season(self):
        """Given the same season in two files with different row counts, only the larger file is used."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "a.csv").write_text(
                '"datetime","home_team","away_team","home_goal","away_goal","season","stage"\n'
                '2019-01-01 10:00:00,"Alpha","Beta",1,0,2019,"x"\n',
                encoding="utf-8",
            )
            sources = [("a.csv", load_libertadores)]
            (tmp_path / "b.csv").write_text(
                '"datetime","home_team","away_team","home_goal","away_goal","season","stage"\n'
                '2019-01-01 10:00:00,"Alpha","Beta",1,0,2019,"x"\n'
                '2019-02-01 10:00:00,"Gamma","Delta",2,2,2019,"x"\n',
                encoding="utf-8",
            )
            sources.append(("b.csv", load_libertadores))
            matches = load_matches(tmp_path, sources)
        self.assertEqual(len(matches), 2)


if __name__ == "__main__":
    unittest.main()
