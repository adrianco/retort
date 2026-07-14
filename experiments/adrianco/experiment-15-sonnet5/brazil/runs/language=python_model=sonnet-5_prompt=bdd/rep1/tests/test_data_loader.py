"""BDD specs for brazilian_soccer_mcp.data_loader: loading and normalizing
the six provided Kaggle CSV files into unified matches/players tables.
"""

import pandas as pd

from brazilian_soccer_mcp.data_loader import MATCH_COLUMNS, load_all, load_matches, load_players


class TestLoadMatches:
    def test_given_all_five_match_csvs_when_loaded_then_every_source_file_is_represented(self, matches_df):
        # Given the five match CSV files bundled under data/kaggle/
        # When they are loaded and unified
        sources = set(matches_df["source"].unique())
        # Then rows from every source file are present in the unified table
        assert sources == {
            "Brasileirao_Matches",
            "Brazilian_Cup_Matches",
            "Libertadores_Matches",
            "BR-Football-Dataset",
            "novo_campeonato_brasileiro",
        }

    def test_given_the_unified_matches_table_when_inspected_then_row_count_matches_all_source_files_combined(
        self, matches_df
    ):
        # Given the raw row counts documented in TASK.md for each source file
        # (4180 + 1337 + 1255 + 10296 + 6886, header rows excluded)
        # When the files are loaded and concatenated
        # Then no rows are silently dropped or duplicated during loading
        assert len(matches_df) == 4180 + 1337 + 1255 + 10296 + 6886

    def test_given_the_unified_matches_table_when_inspected_then_it_has_the_documented_schema(self, matches_df):
        # Given the unified matches schema
        # When the loaded table's columns are inspected
        # Then they exactly match the documented MATCH_COLUMNS
        assert list(matches_df.columns) == MATCH_COLUMNS

    def test_given_state_suffixed_and_bare_spellings_of_a_team_when_loaded_then_they_share_one_key(self, matches_df):
        # Given "Palmeiras-SP" (Brasileirao_Matches) and other bare/differently
        # spelled occurrences of the same club across source files
        # When the data is loaded and keys are normalized
        keys = matches_df.loc[
            matches_df["home_team_raw"].isin(["Palmeiras-SP", "Palmeiras"]), "home_team_key"
        ].unique()
        # Then every spelling resolves to the same team key
        assert len(keys) == 1

    def test_given_a_libertadores_match_missing_its_score_when_loaded_then_goals_are_missing_not_zero(
        self, matches_df
    ):
        # Given the Libertadores dataset uses "-" for a small number of
        # matches with no recorded score
        unplayed = matches_df[
            (matches_df["source"] == "Libertadores_Matches") & matches_df["home_goal"].isna()
        ]
        # When that data is loaded
        # Then at least one such match is preserved with missing (not zero) goals
        assert len(unplayed) > 0
        assert unplayed["away_goal"].isna().all()

    def test_given_matches_with_recorded_scores_when_loaded_then_result_column_is_derived_correctly(
        self, matches_df
    ):
        # Given a match where the home team scored more goals than the away team
        played = matches_df.dropna(subset=["home_goal", "away_goal"])
        home_win = played[played["home_goal"] > played["away_goal"]].iloc[0]
        # When the result column is computed during loading
        # Then it correctly reflects a home win
        assert home_win["result"] == "Home"

    def test_given_a_data_directory_with_a_missing_file_when_loaded_then_a_clear_error_is_raised(self, tmp_path):
        # Given a data directory missing the required CSV files
        # When loading matches from that directory
        # Then a clear, actionable error is raised instead of a cryptic one
        try:
            load_matches(str(tmp_path))
            assert False, "expected FileNotFoundError"
        except FileNotFoundError as exc:
            assert "Brasileirao_Matches.csv" in str(exc)


class TestLoadPlayers:
    def test_given_the_fifa_player_csv_when_loaded_then_row_count_matches_the_documented_total(self, players_df):
        # Given the FIFA player dataset documented as 18,207 players
        # When it is loaded
        # Then no rows are silently dropped
        assert len(players_df) == 18207

    def test_given_the_players_table_when_inspected_then_club_key_is_normalized(self, players_df):
        # Given a well-known Brazilian club appearing in the FIFA data
        # When the players table is loaded
        santos = players_df[players_df["club_raw"] == "Santos"]
        # Then its normalized club_key matches what team-name normalization would produce
        assert not santos.empty
        assert (santos["club_key"] == "santos").all()

    def test_given_a_brazilian_player_when_loaded_then_nationality_is_exactly_brazil(self, players_df):
        # Given the well-known Brazilian player Neymar Jr in the dataset
        # When the players table is loaded
        neymar = players_df[players_df["name"] == "Neymar Jr"]
        # Then his nationality field is the exact string "Brazil"
        assert not neymar.empty
        assert (neymar["nationality"] == "Brazil").all()


class TestLoadAll:
    def test_given_the_full_dataset_when_loaded_then_both_matches_and_players_are_returned(self):
        # Given both match and player CSVs
        # When load_all is called
        data = load_all()
        # Then a combined result with both tables populated is returned
        assert isinstance(data.matches, pd.DataFrame) and not data.matches.empty
        assert isinstance(data.players, pd.DataFrame) and not data.players.empty
