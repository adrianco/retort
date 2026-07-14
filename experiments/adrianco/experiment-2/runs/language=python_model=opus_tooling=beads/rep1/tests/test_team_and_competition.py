"""Feature: Team and competition queries."""


def test_team_record_points_formula(engine):
    """Scenario: Team record uses 3/1/0 points."""
    rec = engine.team_record("Palmeiras", season=2023, competition="Brasileir")
    assert rec["points"] == rec["wins"] * 3 + rec["draws"]
    assert rec["matches"] == rec["wins"] + rec["draws"] + rec["losses"]


def test_home_only_restricts(engine):
    rec = engine.team_record("Corinthians", season=2022,
                             competition="Brasileir", home_only=True)
    assert rec["matches"] > 0
    assert rec["wins"] >= 0


def test_standings_flamengo_champion_2019(engine):
    """Scenario: 2019 Brasileirão was won by Flamengo."""
    s = engine.standings("Brasileirão", 2019)
    assert not s.empty
    assert "flamengo" in s.iloc[0]["team"]


def test_standings_has_20_teams_modern_era(engine):
    s = engine.standings("Brasileirão", 2018)
    assert not s.empty
    assert len(s) >= 20
