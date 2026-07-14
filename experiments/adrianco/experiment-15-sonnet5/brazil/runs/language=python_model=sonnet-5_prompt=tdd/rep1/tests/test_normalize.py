import datetime

from brazilian_soccer_mcp.normalize import canonical_team_key, display_team_name, parse_date


def test_canonical_team_key_strips_state_suffix():
    assert canonical_team_key("Palmeiras-SP") == canonical_team_key("Palmeiras")


def test_canonical_team_key_is_case_insensitive():
    assert canonical_team_key("flamengo") == canonical_team_key("FLAMENGO-RJ")


def test_canonical_team_key_strips_accents():
    assert canonical_team_key("São Paulo") == canonical_team_key("Sao Paulo-SP")


def test_canonical_team_key_full_legal_name_alias():
    assert canonical_team_key("Sport Club Corinthians Paulista") == canonical_team_key("Corinthians-SP")


def test_canonical_team_key_keeps_state_for_ambiguous_base():
    # Atletico is a shared nickname for clubs in MG, PR and GO - must stay distinct
    mg = canonical_team_key("Atletico-MG")
    pr = canonical_team_key("Atletico-PR")
    go = canonical_team_key("Atletico-GO")
    assert len({mg, pr, go}) == 3


def test_canonical_team_key_handles_dash_with_spaces():
    assert canonical_team_key("America - MG") == canonical_team_key("America-MG")


def test_canonical_team_key_collapses_whitespace_and_punctuation():
    assert canonical_team_key("A.b.c. - RN") == canonical_team_key("ABC - RN")


def test_display_team_name_prefers_readable_form():
    assert display_team_name("Flamengo-RJ") == "Flamengo"
    assert display_team_name("Sport Club Corinthians Paulista") == "Corinthians"


def test_parse_date_iso_format():
    assert parse_date("2023-09-24") == datetime.date(2023, 9, 24)


def test_parse_date_iso_with_time():
    assert parse_date("2012-05-19 18:30:00") == datetime.date(2012, 5, 19)


def test_parse_date_brazilian_format():
    assert parse_date("29/03/2003") == datetime.date(2003, 3, 29)


def test_parse_date_invalid_returns_none():
    assert parse_date("not-a-date") is None


def test_parse_date_handles_missing_value():
    assert parse_date(None) is None
    assert parse_date(float("nan")) is None
