"""Feature: Data loading

All six provided CSV files must be loadable and queryable, with UTF-8
text, multiple date formats, and team-name variations handled.
"""

from datetime import datetime

from soccer_data import normalize_team, parse_date


class TestAllFilesLoad:
    def test_all_six_files_are_loaded(self, db):
        # Given the data directory
        # When the database is loaded
        # Then every source file yields the expected number of records
        assert len(db.matches_by_source["brasileirao"]) == 4180
        assert len(db.matches_by_source["cup"]) == 1337
        assert len(db.matches_by_source["libertadores"]) == 1255
        assert len(db.matches_by_source["hist"]) == 6886
        assert len(db.matches_by_source["ext"]) == 10296
        assert len(db.players) == 18207

    def test_duplicate_matches_across_sources_are_removed(self, db):
        # The Brasileirão file (2012-2022), historical file (2003-2019) and
        # extended file all overlap, so the de-duplicated pool must be much
        # smaller than the raw sum of sources.
        raw_total = sum(len(v) for v in db.matches_by_source.values())
        assert len(db.matches) < raw_total
        # And a known overlapping season must contain exactly one full
        # double round-robin (20 teams -> 380 matches).
        m2019 = [m for m in db.matches
                 if m.competition == "serie-a" and m.season == 2019]
        assert len(m2019) == 380

    def test_utf8_team_names_are_preserved(self, db):
        # Then accented Brazilian club names survive loading intact
        names = {m.home for m in db.matches} | {m.away for m in db.matches}
        assert any("São Paulo" in n for n in names)
        assert any("Grêmio" in n for n in names)
        assert any("Avaí" in n for n in names)


class TestDateFormats:
    def test_iso_date(self):
        assert parse_date("2023-09-24") == datetime(2023, 9, 24)

    def test_iso_datetime(self):
        assert parse_date("2012-05-19 18:30:00") == datetime(2012, 5, 19, 18, 30)

    def test_brazilian_date(self):
        assert parse_date("29/03/2003") == datetime(2003, 3, 29)

    def test_missing_or_invalid_dates(self):
        assert parse_date("") is None
        assert parse_date("NA") is None
        assert parse_date(None) is None


class TestTeamNameNormalization:
    def test_state_suffix_variants_map_to_same_team(self):
        # "Palmeiras-SP", "Palmeiras - SP" and "Palmeiras" are one club
        assert normalize_team("Palmeiras-SP")[0] == normalize_team("Palmeiras")[0]
        assert normalize_team("Corinthians - SP")[0] == normalize_team("Corinthians")[0]

    def test_accents_are_normalized(self):
        assert normalize_team("São Paulo")[0] == normalize_team("Sao Paulo")[0]
        assert normalize_team("Grêmio")[0] == normalize_team("Gremio")[0]

    def test_full_club_names_resolve_to_short_names(self):
        assert normalize_team("Sport Club Corinthians Paulista")[0] == "corinthians"

    def test_stateful_clubs_stay_distinct(self):
        # Atlético-MG, Athletico-PR and Atlético-GO are different clubs
        mg = normalize_team("Atletico-MG")[0]
        pr = normalize_team("Atletico-PR")[0]
        go = normalize_team("Atlético-GO")[0]
        assert len({mg, pr, go}) == 3
        # And dataset spelling variants converge on the right club
        assert normalize_team("Athletico Paranaense")[0] == pr
        assert normalize_team("Atletico Mineiro")[0] == mg

    def test_state_is_extracted(self):
        base, state = normalize_team("Flamengo-RJ")
        assert base == "flamengo"
        assert state == "RJ"

    def test_club_form_abbreviations_are_stripped(self):
        assert normalize_team("EC Bahia")[0] == normalize_team("Bahia")[0]
        assert normalize_team("Fortaleza EC")[0] == normalize_team("Fortaleza")[0]
