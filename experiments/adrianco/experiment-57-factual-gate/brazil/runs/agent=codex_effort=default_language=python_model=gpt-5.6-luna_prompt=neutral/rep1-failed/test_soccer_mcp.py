import csv

from soccer_mcp import SoccerData


def write_csv(path, name, headers, rows):
    with (path / name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers); writer.writeheader(); writer.writerows(rows)


def dataset(tmp_path):
    write_csv(tmp_path, "Brasileirao_Matches.csv", ["datetime", "home_team", "home_team_state", "away_team", "away_team_state", "home_goal", "away_goal", "season", "round"], [
        {"datetime":"2023-09-03", "home_team":"Flamengo-RJ", "home_team_state":"RJ", "away_team":"Fluminense-RJ", "away_team_state":"RJ", "home_goal":"2", "away_goal":"1", "season":"2023", "round":"22"},
        {"datetime":"2023-05-28", "home_team":"Fluminense-RJ", "home_team_state":"RJ", "away_team":"Flamengo-RJ", "away_team_state":"RJ", "home_goal":"0", "away_goal":"0", "season":"2023", "round":"8"},
    ])
    write_csv(tmp_path, "fifa_data.csv", ["ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position"], [
        {"ID":"1", "Name":"Neymar Jr", "Age":"27", "Nationality":"Brazil", "Overall":"92", "Potential":"92", "Club":"Flamengo", "Position":"LW"},
        {"ID":"2", "Name":"Test Player", "Age":"20", "Nationality":"Brazil", "Overall":"70", "Potential":"80", "Club":"Santos", "Position":"ST"},
    ])
    return SoccerData(tmp_path)


def test_match_normalizes_state_suffix_and_date_filter(tmp_path):
    data = dataset(tmp_path)
    rows = data.matches(team="Flamengo", start_date="2023-06-01")
    assert len(rows) == 1 and rows[0]["away_team"] == "Fluminense-RJ"


def test_head_to_head_and_stats(tmp_path):
    data = dataset(tmp_path)
    h2h = data.head_to_head("Flamengo", "Fluminense")
    assert (h2h["team_a_wins"], h2h["draws"], h2h["team_b_wins"]) == (1, 1, 0)
    assert data.team_stats("Flamengo") == {"team":"Flamengo", "matches":2, "wins":1, "draws":1, "losses":0, "goals_for":2, "goals_against":1, "win_rate":50.0}


def test_players_are_filtered_and_sorted(tmp_path):
    data = dataset(tmp_path)
    assert data.players(nationality="Brazil", min_overall=80)[0]["Name"] == "Neymar Jr"


def test_standings_and_statistics(tmp_path):
    data = dataset(tmp_path)
    table = data.standings(2023)
    assert table[0]["team"] == "Flamengo-RJ" and table[0]["points"] == 4
    stats = data.statistics(season=2023)
    assert stats["matches"] == 2 and stats["average_goals"] == 1.5
