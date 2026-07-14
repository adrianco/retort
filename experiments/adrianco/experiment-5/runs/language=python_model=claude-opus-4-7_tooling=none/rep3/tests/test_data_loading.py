"""BDD: data loading covers every provided CSV.

Feature: Data loading
  Scenario: All six Kaggle datasets are parsed into memory
    Given the project's `data/kaggle` directory
    When  the dataset is loaded
    Then  matches and players are present from every source
"""

from __future__ import annotations


def test_all_six_csv_files_contribute_matches(dataset):
    # Given the canonical loader has run (session fixture)
    # When  we inspect the source attribution
    sources = {m.source for m in dataset.matches}
    # Then five match CSVs contributed at least one row each
    expected = {
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    }
    assert expected <= sources


def test_fifa_players_are_loaded(dataset):
    # Given the loader ran
    # When  we count players
    # Then  the full ~18 200 FIFA roster is in memory
    assert len(dataset.players) >= 18_000


def test_match_volume_is_reasonable_after_dedup(dataset):
    # Given the loader ran
    # When  we count matches after cross-file deduplication
    # Then  the number is plausible (< raw sum, > Brasileirão alone)
    assert 12_000 < len(dataset.matches) < 25_000


def test_team_index_is_built(dataset):
    # Given the loader ran
    # When  we look up a popular club by its normalized name
    # Then  the index contains hundreds of matches for it
    assert len(dataset.matches_by_norm_team["flamengo"]) > 500
    assert len(dataset.matches_by_norm_team["palmeiras"]) > 500


def test_special_characters_are_preserved_in_raw_team_names(dataset):
    # Given the historical Brasileirão file contains accented names
    # When  we inspect raw match data
    # Then  the accents survived the UTF-8 round-trip
    accented = [
        m for m in dataset.matches if "ã" in m.home_team or "ê" in m.home_team
    ]
    assert accented, "expected at least one accented home_team in the raw data"


def test_date_formats_are_normalized(dataset):
    # Given matches come from CSVs using ISO + Brazilian + datetime formats
    # When  we look at parsed dates
    # Then  every parseable row has a real `date` object
    parsed = [m.match_date for m in dataset.matches if m.match_date]
    assert len(parsed) > 15_000
    assert all(hasattr(d, "year") for d in parsed)
