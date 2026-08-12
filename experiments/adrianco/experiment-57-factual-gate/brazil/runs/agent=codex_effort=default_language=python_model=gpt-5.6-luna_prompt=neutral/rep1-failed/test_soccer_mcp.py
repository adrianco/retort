import soccer_mcp


def test_real_datasets_are_loaded():
    db = soccer_mcp.SoccerDatabase()
    assert len(db.matches) > 20_000
    assert len(db.players) > 18_000


def test_team_suffix_and_head_to_head_normalization():
    db = soccer_mcp.SoccerDatabase()
    rows = db.matches_query(team="Palmeiras", opponent="Portuguesa", season=2012)
    assert rows and all("Palmeiras" in (r["home_team"] + r["away_team"]) or "Portuguesa" in (r["home_team"] + r["away_team"]) for r in rows)


def test_team_statistics_are_consistent():
    db = soccer_mcp.SoccerDatabase()
    stats = db.team_stats("Palmeiras", season=2012, competition="Brasileirão")
    assert stats["matches"] > 0
    assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
    assert 0 <= stats["win_rate"] <= 100


def test_player_filters_and_rating_sort():
    db = soccer_mcp.SoccerDatabase()
    players = db.players_query(nationality="Brazil", min_overall=85, limit=10)
    assert players
    assert all(p["Nationality"] == "Brazil" and int(p["Overall"]) >= 85 for p in players)
    assert [int(p["Overall"]) for p in players] == sorted((int(p["Overall"]) for p in players), reverse=True)


def test_standings_and_aggregates():
    db = soccer_mcp.SoccerDatabase()
    table = db.standings(2012)
    assert table and table[0]["points"] >= table[-1]["points"]
    aggregate = db.aggregate_stats(season=2012)
    assert aggregate["matches"] > 0 and aggregate["average_goals"] >= 0


def test_mcp_tools_are_callable(monkeypatch, capsys):
    # Exercise the protocol's public dispatch without starting a subprocess.
    db = soccer_mcp.SoccerDatabase()
    result = soccer_mcp._call(db, "statistics", {"season": 2012})
    assert result["matches"] > 0
