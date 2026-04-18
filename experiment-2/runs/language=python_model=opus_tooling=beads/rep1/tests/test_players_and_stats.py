"""Feature: Player and statistical queries."""


def test_find_players_by_nationality(engine):
    df = engine.find_players(nationality="Brazil", min_overall=85, limit=10)
    assert not df.empty
    assert (df["Nationality"] == "Brazil").all()
    assert (df["Overall"] >= 85).all()


def test_find_players_by_name(engine):
    df = engine.find_players(name="Neymar")
    assert not df.empty
    assert df["Name"].str.contains("Neymar", case=False).any()


def test_find_players_by_club(engine):
    # FIFA 2019 dataset only includes top European clubs, so use one that exists.
    df = engine.find_players(club="Real Madrid", limit=50)
    assert not df.empty
    assert df["Club"].str.contains("Real Madrid", case=False).all()


def test_average_goals_reasonable(engine):
    stats = engine.average_goals(competition="Brasileirão")
    assert stats["matches"] > 0
    assert 1.5 < stats["avg_goals_per_match"] < 4.0
    assert 0.3 < stats["home_win_rate"] < 0.7


def test_biggest_wins_sorted_by_margin(engine):
    df = engine.biggest_wins(limit=5)
    margins = (df["home_goal"] - df["away_goal"]).abs().tolist()
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 5
