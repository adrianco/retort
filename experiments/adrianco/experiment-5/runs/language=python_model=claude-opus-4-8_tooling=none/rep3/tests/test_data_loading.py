# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.test_data_loading
# Purpose : BDD scenarios covering the data layer: every CSV loads, records are
#           well-formed, and the cross-source deduplication collapses the
#           overlapping Brasileirão seasons to one canonical source.
# =============================================================================

from soccer_mcp import data_loader as dl


class TestAllFilesLoad:
    """Feature: All six datasets are loadable and queryable."""

    def test_brasileirao_loads(self):
        # Given the Brasileirão file, When loaded, Then rows are returned
        matches = dl.load_brasileirao()
        assert len(matches) == 4180
        assert all(m.competition == "Brasileirão" for m in matches)

    def test_cup_loads(self):
        assert len(dl.load_cup()) == 1337

    def test_libertadores_loads(self):
        matches = dl.load_libertadores()
        assert len(matches) == 1255
        # Then stage information is captured
        assert any(m.stage == "final" for m in matches)

    def test_extended_loads(self):
        matches = dl.load_extended()
        assert len(matches) == 10296
        # And extended stats are present
        assert any(m.stats.get("home_shots") is not None for m in matches)

    def test_historical_loads(self):
        matches = dl.load_historical()
        assert len(matches) == 6886

    def test_players_load(self):
        players = dl.load_players()
        assert len(players) == 18207
        # And a well-known player is present and correctly parsed
        messi = [p for p in players if p.name == "L. Messi"][0]
        assert messi.overall == 94
        assert messi.nationality == "Argentina"


class TestRecordQuality:
    """Feature: Loaded records are normalised and well-formed."""

    def test_team_names_are_normalised(self):
        # Given a Brasileirão match, Then both raw and normalised names exist
        m = dl.load_brasileirao()[0]
        assert m.home_team and m.home_team_norm
        assert m.home_team_norm == m.home_team_norm.lower()

    def test_dates_are_iso(self):
        # Then parsed dates are ISO formatted
        for m in dl.load_historical()[:50]:
            if m.date:
                assert len(m.date) == 10 and m.date[4] == "-"


class TestDeduplication:
    """Feature: Overlapping seasons are deduplicated for correct aggregates."""

    def test_raw_has_duplicates(self):
        # Given the raw concatenation
        raw = dl.load_all_matches(dedupe=False)
        # Then 2019 Brasileirão appears in three sources (380 * 3 rows)
        n_2019 = sum(
            1 for m in raw if m.competition == "Brasileirão" and m.season == 2019
        )
        assert n_2019 > 380

    def test_dedupe_keeps_single_source_per_season(self):
        # When deduplicated
        deduped = dl.load_all_matches(dedupe=True)
        # Then exactly one full season (380 matches) remains for 2019
        n_2019 = sum(
            1 for m in deduped if m.competition == "Brasileirão" and m.season == 2019
        )
        assert n_2019 == 380
        # And fewer matches overall than the raw set
        assert len(deduped) < len(dl.load_all_matches(dedupe=False))
