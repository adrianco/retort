package main

import (
	"testing"
)

func testDB() *Database {
	return &Database{
		Matches: []Match{
			{HomeTeam: "Flamengo", AwayTeam: "Corinthians", HomeGoal: 3, AwayGoal: 1, Season: 2023, Round: "10", Date: "2023-05-10", Competition: "Brasileirao"},
			{HomeTeam: "Corinthians", AwayTeam: "Flamengo", HomeGoal: 0, AwayGoal: 2, Season: 2023, Round: "20", Date: "2023-09-15", Competition: "Brasileirao"},
			{HomeTeam: "Palmeiras", AwayTeam: "Santos", HomeGoal: 2, AwayGoal: 0, Season: 2023, Round: "5", Date: "2023-04-02", Competition: "Brasileirao"},
			{HomeTeam: "Santos", AwayTeam: "Palmeiras", HomeGoal: 1, AwayGoal: 1, Season: 2022, Round: "15", Date: "2022-07-10", Competition: "Brasileirao"},
			{HomeTeam: "Flamengo", AwayTeam: "River Plate", HomeGoal: 2, AwayGoal: 1, Season: 2019, Round: "final", Date: "2019-11-23", Competition: "Libertadores", Stage: "final"},
			{HomeTeam: "São Paulo", AwayTeam: "Flamengo", HomeGoal: 2, AwayGoal: 1, Season: 2023, Round: "Final", Date: "2023-10-01", Competition: "Copa do Brasil"},
			{HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeGoal: 1, AwayGoal: 2, Season: 2023, Round: "22", Date: "2023-09-03", Competition: "Brasileirao"},
		},
		Players: []Player{
			{ID: "1", Name: "Neymar Jr", Age: 26, Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain", Position: "LW"},
			{ID: "2", Name: "Alisson", Age: 25, Nationality: "Brazil", Overall: 89, Club: "Liverpool", Position: "GK"},
			{ID: "3", Name: "Gabriel Barbosa", Age: 22, Nationality: "Brazil", Overall: 80, Club: "Flamengo", Position: "ST"},
			{ID: "4", Name: "L. Messi", Age: 31, Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", Position: "RF"},
			{ID: "5", Name: "Vinícius Jr", Age: 18, Nationality: "Brazil", Overall: 79, Club: "Real Madrid", Position: "LW"},
		},
	}
}

// --- SearchMatches ---

func TestSearchMatchesByTeam(t *testing.T) {
	db := testDB()
	results := SearchMatches(db, SearchMatchesParams{Team: "Flamengo"})
	if len(results) != 5 {
		t.Errorf("expected 5 Flamengo matches, got %d", len(results))
	}
}

func TestSearchMatchesBySeason(t *testing.T) {
	db := testDB()
	results := SearchMatches(db, SearchMatchesParams{Season: 2023})
	if len(results) != 5 {
		t.Errorf("expected 5 matches in 2023, got %d", len(results))
	}
}

func TestSearchMatchesByCompetition(t *testing.T) {
	db := testDB()
	results := SearchMatches(db, SearchMatchesParams{Competition: "libertadores"})
	if len(results) != 1 {
		t.Errorf("expected 1 Libertadores match, got %d", len(results))
	}
}

func TestSearchMatchesByHomeAndAway(t *testing.T) {
	db := testDB()
	results := SearchMatches(db, SearchMatchesParams{HomeTeam: "Flamengo", AwayTeam: "Corinthians"})
	if len(results) != 1 {
		t.Errorf("expected 1 match, got %d", len(results))
	}
}

func TestSearchMatchesByDateRange(t *testing.T) {
	db := testDB()
	results := SearchMatches(db, SearchMatchesParams{StartDate: "2023-09-01", EndDate: "2023-12-31"})
	if len(results) != 3 {
		t.Errorf("expected 3 matches in date range, got %d", len(results))
	}
}

func TestSearchMatchesLimit(t *testing.T) {
	db := testDB()
	results := SearchMatches(db, SearchMatchesParams{Team: "Flamengo", Limit: 2})
	if len(results) != 2 {
		t.Errorf("expected 2 results (limit), got %d", len(results))
	}
}

func TestSearchMatchesNoFilter(t *testing.T) {
	db := testDB()
	results := SearchMatches(db, SearchMatchesParams{})
	if len(results) != len(db.Matches) {
		t.Errorf("expected all %d matches, got %d", len(db.Matches), len(results))
	}
}

// --- GetHeadToHead ---

func TestGetHeadToHead(t *testing.T) {
	db := testDB()
	h2h := GetHeadToHead(db, "Flamengo", "Corinthians", GetHeadToHeadParams{})
	if h2h.Team1Wins != 2 {
		t.Errorf("Flamengo wins = %d, want 2", h2h.Team1Wins)
	}
	if h2h.Team2Wins != 0 {
		t.Errorf("Corinthians wins = %d, want 0", h2h.Team2Wins)
	}
	if h2h.Draws != 0 {
		t.Errorf("Draws = %d, want 0", h2h.Draws)
	}
	if h2h.TotalMatches != 2 {
		t.Errorf("TotalMatches = %d, want 2", h2h.TotalMatches)
	}
}

func TestGetHeadToHeadGoals(t *testing.T) {
	db := testDB()
	h2h := GetHeadToHead(db, "Palmeiras", "Santos", GetHeadToHeadParams{})
	// Palmeiras 2-0 Santos + Santos 1-1 Palmeiras
	if h2h.TotalMatches != 2 {
		t.Errorf("TotalMatches = %d, want 2", h2h.TotalMatches)
	}
	if h2h.Team1Wins != 1 {
		t.Errorf("Palmeiras wins = %d, want 1", h2h.Team1Wins)
	}
	if h2h.Draws != 1 {
		t.Errorf("Draws = %d, want 1", h2h.Draws)
	}
}

// --- GetTeamStats ---

func TestGetTeamStatsBasic(t *testing.T) {
	db := testDB()
	// Flamengo matches: (1) Flamengo 3-1 Corinthians W, (2) Corinthians 0-2 Flamengo W,
	// (3) Flamengo 2-1 River Plate W, (4) Sao Paulo 2-1 Flamengo L, (5) Fluminense 1-2 Flamengo W
	stats := GetTeamStats(db, "Flamengo", GetTeamStatsParams{})
	if stats.Played != 5 {
		t.Errorf("Played = %d, want 5", stats.Played)
	}
	if stats.Wins != 4 {
		t.Errorf("Wins = %d, want 4", stats.Wins)
	}
	if stats.Losses != 1 {
		t.Errorf("Losses = %d, want 1", stats.Losses)
	}
}

func TestGetTeamStatsHomeOnly(t *testing.T) {
	db := testDB()
	stats := GetTeamStats(db, "Flamengo", GetTeamStatsParams{HomeOnly: true})
	if stats.Played != 2 {
		t.Errorf("Played (home) = %d, want 2", stats.Played)
	}
	if stats.Wins != 2 {
		t.Errorf("Wins (home) = %d, want 2", stats.Wins)
	}
}

func TestGetTeamStatsBySeason(t *testing.T) {
	db := testDB()
	stats := GetTeamStats(db, "Flamengo", GetTeamStatsParams{Season: 2023})
	if stats.Played != 4 {
		t.Errorf("Played 2023 = %d, want 4", stats.Played)
	}
}

// --- GetStandings ---

func TestGetStandings(t *testing.T) {
	db := testDB()
	standings := GetStandings(db, "Brasileirao", 2023)
	if len(standings) == 0 {
		t.Fatal("expected standings, got none")
	}
	// Flamengo: 2 wins (from home 3-1 + away 0-2) = 6 pts, Fluminense: 0 pts
	// 2023 Brasileirao Flamengo: W vs Corinthians(h), W vs Corinthians(a), W vs Fluminense(a) = 3 wins
	var flamengo *TeamRecord
	for i := range standings {
		if standings[i].Team == "Flamengo" {
			flamengo = &standings[i]
			break
		}
	}
	if flamengo == nil {
		t.Fatal("Flamengo not found in standings")
	}
	if flamengo.Wins != 3 {
		t.Errorf("Flamengo wins = %d, want 3", flamengo.Wins)
	}
	if flamengo.Points != 9 {
		t.Errorf("Flamengo points = %d, want 9", flamengo.Points)
	}
}

func TestGetStandingsSorted(t *testing.T) {
	db := testDB()
	standings := GetStandings(db, "Brasileirao", 2023)
	// Standings must be sorted by points descending
	for i := 1; i < len(standings); i++ {
		if standings[i].Points > standings[i-1].Points {
			t.Errorf("standings not sorted: %s(%d) > %s(%d)",
				standings[i].Team, standings[i].Points,
				standings[i-1].Team, standings[i-1].Points)
		}
	}
}

// --- SearchPlayers ---

func TestSearchPlayersByName(t *testing.T) {
	db := testDB()
	players := SearchPlayers(db, SearchPlayersParams{Name: "Neymar"})
	if len(players) != 1 {
		t.Errorf("expected 1 player, got %d", len(players))
	}
	if players[0].Name != "Neymar Jr" {
		t.Errorf("Name = %q, want Neymar Jr", players[0].Name)
	}
}

func TestSearchPlayersByNationality(t *testing.T) {
	db := testDB()
	players := SearchPlayers(db, SearchPlayersParams{Nationality: "Brazil"})
	if len(players) != 4 {
		t.Errorf("expected 4 Brazilian players, got %d", len(players))
	}
}

func TestSearchPlayersByClub(t *testing.T) {
	db := testDB()
	players := SearchPlayers(db, SearchPlayersParams{Club: "Flamengo"})
	if len(players) != 1 {
		t.Errorf("expected 1 Flamengo player, got %d", len(players))
	}
}

func TestSearchPlayersByMinOverall(t *testing.T) {
	db := testDB()
	players := SearchPlayers(db, SearchPlayersParams{MinOverall: 90})
	if len(players) != 2 { // Neymar 92, Messi 94
		t.Errorf("expected 2 players with overall >= 90, got %d", len(players))
	}
}

func TestSearchPlayersByPosition(t *testing.T) {
	db := testDB()
	players := SearchPlayers(db, SearchPlayersParams{Position: "GK"})
	if len(players) != 1 {
		t.Errorf("expected 1 GK, got %d", len(players))
	}
}

func TestSearchPlayersSortedByOverall(t *testing.T) {
	db := testDB()
	players := SearchPlayers(db, SearchPlayersParams{Nationality: "Brazil"})
	for i := 1; i < len(players); i++ {
		if players[i].Overall > players[i-1].Overall {
			t.Errorf("players not sorted by overall desc: %d > %d", players[i].Overall, players[i-1].Overall)
		}
	}
}

func TestSearchPlayersLimit(t *testing.T) {
	db := testDB()
	players := SearchPlayers(db, SearchPlayersParams{Limit: 2})
	if len(players) != 2 {
		t.Errorf("expected 2 players (limit), got %d", len(players))
	}
}

// --- GetStatistics ---

func TestGetStatisticsGoalsPerMatch(t *testing.T) {
	db := testDB()
	stats := GetStatistics(db, "goals_per_match", GetStatisticsParams{})
	if stats.GoalsPerMatch <= 0 {
		t.Errorf("GoalsPerMatch = %f, want > 0", stats.GoalsPerMatch)
	}
}

func TestGetStatisticsBiggestWins(t *testing.T) {
	db := testDB()
	stats := GetStatistics(db, "biggest_wins", GetStatisticsParams{Limit: 3})
	if len(stats.BiggestWins) == 0 {
		t.Error("expected biggest wins, got none")
	}
	// First entry should be the biggest margin
	if len(stats.BiggestWins) > 1 {
		margin0 := stats.BiggestWins[0].HomeGoal - stats.BiggestWins[0].AwayGoal
		if margin0 < 0 {
			margin0 = -margin0
		}
		margin1 := stats.BiggestWins[1].HomeGoal - stats.BiggestWins[1].AwayGoal
		if margin1 < 0 {
			margin1 = -margin1
		}
		if margin0 < margin1 {
			t.Errorf("biggest wins not sorted: margin %d < %d", margin0, margin1)
		}
	}
}

func TestGetStatisticsHomeWinRate(t *testing.T) {
	db := testDB()
	stats := GetStatistics(db, "home_record", GetStatisticsParams{})
	if stats.HomeWinRate < 0 || stats.HomeWinRate > 1 {
		t.Errorf("HomeWinRate = %f, want [0,1]", stats.HomeWinRate)
	}
}
