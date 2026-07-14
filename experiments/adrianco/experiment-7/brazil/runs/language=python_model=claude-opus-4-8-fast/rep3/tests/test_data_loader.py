"""
================================================================================
Context
================================================================================
Test module: test_data_loader.py
Project:     Brazilian Soccer MCP Server
Feature:     Loading and normalizing all six source CSV files.
Style:       BDD Given-When-Then.

Confirms every dataset is loadable and queryable, dates in several formats are
parsed, "NA" scores become None, and the FIFA BOM column is handled.
================================================================================
"""

from datetime import date

import data_loader
from data_loader import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
)


class TestMatchLoading:
    def test_all_match_files_load(self):
        # Given the six CSV datasets on disk
        # When matches are loaded
        # Then a large unified set of matches is returned
        matches = data_loader.load_matches()
        assert len(matches) > 20000

    def test_every_competition_is_represented(self, ):
        # Given the loaded matches
        # When the competitions are collected
        # Then the three headline competitions are present
        matches = data_loader.load_matches()
        comps = {m.competition for m in matches}
        assert {SERIE_A, COPA_DO_BRASIL, LIBERTADORES} <= comps

    def test_dates_are_parsed_across_formats(self):
        # Given matches sourced from ISO and DD/MM/YYYY files
        # When loaded
        # Then their dates are real date objects
        matches = data_loader.load_matches()
        dated = [m for m in matches if m.date is not None]
        assert len(dated) > 20000
        assert all(isinstance(m.date, date) for m in dated)

    def test_na_scores_become_none(self):
        # Given the brasileirao file contains "NA" goal values for unplayed games
        # When loaded
        # Then those scores are None rather than raising
        matches = data_loader.load_matches()
        unplayed = [m for m in matches if m.home_goal is None or m.away_goal is None]
        assert len(unplayed) > 0
        # And a played match exposes integer goals
        played = next(m for m in matches if m.home_goal is not None)
        assert isinstance(played.home_goal, int)

    def test_match_winner_and_draw_logic(self):
        # Given a constructed match
        # When the winner property is read
        # Then it reflects the score
        m = data_loader.Match(SERIE_A, 2019, "Flamengo", "Vasco", 2, 1)
        assert m.winner == "Flamengo"
        assert not m.is_draw
        assert m.total_goals == 3
        draw = data_loader.Match(SERIE_A, 2019, "Flamengo", "Vasco", 1, 1)
        assert draw.winner is None
        assert draw.is_draw


class TestPlayerLoading:
    def test_players_load_with_bom_column(self):
        # Given the FIFA file has a UTF-8 BOM on its first column
        # When players are loaded
        # Then names/ratings parse correctly
        players = data_loader.load_players()
        assert len(players) > 18000
        messi = next(p for p in players if p.name == "L. Messi")
        assert messi.overall == 94
        assert messi.nationality == "Argentina"

    def test_brazilian_players_present(self):
        # Given the player dataset
        # When filtered to Brazil nationality
        # Then a substantial set is found
        players = data_loader.load_players()
        brazilians = [p for p in players if p.nationality == "Brazil"]
        assert len(brazilians) > 500
