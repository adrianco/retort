"""Integration coverage for all required CSV source mappings."""

from brazilian_soccer_mcp.normalization import normalize_team


def test_given_bundled_data_when_catalog_loads_then_all_six_csvs_are_queryable(full_service) -> None:
    summary = full_service.data_summary()
    assert summary["match_rows"] == 23_954
    assert summary["player_rows"] == 18_207
    assert summary["source_row_counts"] == {
        "brasileirao_matches": 4_180,
        "brazilian_cup_matches": 1_337,
        "libertadores_matches": 1_255,
        "extended_match_statistics": 10_296,
        "historical_brasileirao": 6_886,
        "fifa_players": 18_207,
    }


def test_given_historical_brazilian_dates_when_loaded_then_they_are_canonical_dates(full_service) -> None:
    record = next(
        match
        for match in full_service.catalog.matches
        if match.id == "historical_brasileirao:2003.01.0001"
    )
    assert record.match_date.isoformat() == "2003-03-29"
    assert (record.home_team, record.home_goals, record.away_team, record.away_goals) == (
        "Guarani",
        4,
        "Vasco",
        2,
    )


def test_given_unplayed_or_missing_score_rows_when_loaded_then_they_do_not_become_zero_scores(full_service) -> None:
    incomplete = [match for match in full_service.catalog.matches if not match.is_complete]
    assert incomplete
    assert any(match.source == "brasileirao_matches" for match in incomplete)
    assert any(match.source == "libertadores_matches" and match.stage == "final" for match in incomplete)


def test_given_utf8_sig_fifa_csv_when_loaded_then_player_ids_and_attributes_are_available(full_service) -> None:
    messi = next(player for player in full_service.catalog.players if player.id == "158023")
    assert messi.name == "L. Messi"
    assert messi.overall == 94
    assert messi.attributes["Finishing"] == 95


def test_given_extended_match_data_when_loaded_then_null_stat_fields_remain_null(full_service) -> None:
    record = next(
        match
        for match in full_service.catalog.matches
        if match.source == "extended_match_statistics"
        and match.home_team == "Nova Mutum"
        and match.away_team == "Londrina"
    )
    assert record.home_goals == 4
    assert record.statistics["total_corners"] == 9.0
    assert "home_attack" not in record.statistics
    assert normalize_team(record.home_team) == "nova mutum"

