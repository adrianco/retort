"""Feature: Data loading.

Given the six Kaggle CSV files
When the database is loaded
Then every file contributes matches/players with correct types and encodings.
"""

from datetime import date

from data_loader import parse_date
from models import COPA_DO_BRASIL, LIBERTADORES, SERIE_A


class TestAllFilesLoad:
    """Scenario: all 6 CSV files are loadable and queryable."""

    def test_every_source_file_contributes_rows(self, db):
        counts = db.sources()
        assert counts["brasileirao"] == 4180
        assert counts["copa_do_brasil"] == 1337
        assert counts["libertadores"] == 1255
        assert counts["br_football"] == 10296
        assert counts["historico"] == 6886

    def test_player_file_loads_all_rows(self, db):
        assert len(db.players) == 18207

    def test_total_match_count(self, db):
        assert len(db.matches) == 4180 + 1337 + 1255 + 10296 + 6886


class TestDateFormats:
    """Scenario: multiple date formats are handled."""

    def test_iso_date(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_iso_datetime(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_brazilian_date(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_garbage_returns_none(self):
        assert parse_date("") is None
        assert parse_date("not a date") is None

    def test_nearly_all_matches_have_parsed_dates(self, db):
        # One Libertadores row (Flamengo vs Athletico) ships without a
        # datetime in the source CSV; everything else must parse.
        missing = [m for m in db.matches if m.date is None]
        assert len(missing) <= 1


class TestEncodingAndContent:
    """Scenario: UTF-8 special characters survive loading."""

    def test_accented_team_names_present(self, db):
        names = {m.home_name for m in db.matches}
        assert "São Paulo" in names
        assert "Grêmio" in names

    def test_goals_are_ints_when_present(self, db):
        for match in db.matches:
            if match.home_goals is not None:
                assert isinstance(match.home_goals, int)
                assert isinstance(match.away_goals, int)

    def test_competitions_are_canonical(self, db):
        competitions = {m.competition for m in db.matches}
        assert SERIE_A in competitions
        assert COPA_DO_BRASIL in competitions
        assert LIBERTADORES in competitions

    def test_extended_stats_loaded(self, db):
        with_corners = [m for m in db.matches if m.source == "br_football"
                        and m.extras.get("total_corners") is not None]
        assert len(with_corners) > 5000

    def test_display_names_prefer_common_spelling(self, db):
        from team_names import parse_team
        assert db.display_name(parse_team("flamengo")) == "Flamengo"
        assert db.display_name(parse_team("sao paulo")) == "São Paulo"
