package query

import (
	"testing"

	"brazilian-soccer-mcp/data"
)

// TestQueryHandler_SearchMatches tests searching matches
func TestQueryHandler_SearchMatches(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	// Test searching by home team
	results, total, err := qh.SearchMatches(&MatchQuery{
		HomeTeam: "Flamengo",
		Limit:    10,
	})
	if err != nil {
		t.Fatalf("Failed to search matches: %v", err)
	}

	if total == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches have Flamengo as home team
	for _, m := range results {
		if m.HomeTeam != "Flamengo" {
			t.Errorf("Expected home team Flamengo, got %s", m.HomeTeam)
		}
	}
}

// TestQueryHandler_SearchMatches_AwayTeam tests searching by away team
func TestQueryHandler_SearchMatches_AwayTeam(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	results, total, err := qh.SearchMatches(&MatchQuery{
		AwayTeam: "Fluminense",
		Limit:    10,
	})
	if err != nil {
		t.Fatalf("Failed to search matches: %v", err)
	}

	if total == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches have Fluminense as away team
	for _, m := range results {
		if m.AwayTeam != "Fluminense" {
			t.Errorf("Expected away team Fluminense, got %s", m.AwayTeam)
		}
	}
}

// TestQueryHandler_SearchMatches_Tournament tests searching by tournament
func TestQueryHandler_SearchMatches_Tournament(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	results, total, err := qh.SearchMatches(&MatchQuery{
		Tournament: "Brasileirão",
		Limit:      10,
	})
	if err != nil {
		t.Fatalf("Failed to search matches: %v", err)
	}

	if total == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches are Brasileirão
	for _, m := range results {
		if m.Tournament != "Brasileirão" {
			t.Errorf("Expected tournament Brasileirão, got %s", m.Tournament)
		}
	}
}

// TestQueryHandler_SearchMatches_Season tests searching by season
func TestQueryHandler_SearchMatches_Season(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	results, total, err := qh.SearchMatches(&MatchQuery{
		Season: "2023",
		Limit:  10,
	})
	if err != nil {
		t.Fatalf("Failed to search matches: %v", err)
	}

	if total == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches are from 2023
	for _, m := range results {
		if m.Season != "2023" {
			t.Errorf("Expected season 2023, got %s", m.Season)
		}
	}
}

// TestQueryHandler_SearchMatches_Combined tests searching with multiple filters
func TestQueryHandler_SearchMatches_Combined(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	results, total, err := qh.SearchMatches(&MatchQuery{
		HomeTeam: "Flamengo",
		Season:   "2023",
		Limit:    10,
	})
	if err != nil {
		t.Fatalf("Failed to search matches: %v", err)
	}

	if total == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches have Flamengo as home team and are from 2023
	for _, m := range results {
		if m.HomeTeam != "Flamengo" || m.Season != "2023" {
			t.Errorf("Expected Flamengo home match in 2023, got %s home in %s", m.HomeTeam, m.Season)
		}
	}
}

// TestQueryHandler_GetTeamStats tests getting team statistics
func TestQueryHandler_GetTeamStats(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	stats, err := qh.GetTeamStats(&TeamQuery{
		Team:   "Flamengo",
		Season: "2023",
	})
	if err != nil {
		t.Fatalf("Failed to get team stats: %v", err)
	}

	if stats.Matches == 0 {
		t.Error("Expected matches to be found")
	}

	// Verify statistics are calculated correctly
	expectedPoints := stats.Wins*3 + stats.Draws
	if stats.Points != expectedPoints {
		t.Errorf("Expected points %d (from %d wins, %d draws), got %d",
			expectedPoints, stats.Wins, stats.Draws, stats.Points)
	}
}

// TestQueryHandler_GetTeamHeadToHead tests getting head-to-head between teams
func TestQueryHandler_GetTeamHeadToHead(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	h2h, err := qh.GetTeamHeadToHead("Flamengo", "Fluminense")
	if err != nil {
		t.Fatalf("Failed to get head-to-head: %v", err)
	}

	if h2h.Matches == 0 {
		t.Error("Expected matches to be found")
	}

	// Check that the counts add up
	totalWins := h2h.Team1Wins + h2h.Team2Wins + h2h.Draws
	if totalWins != h2h.Matches {
		t.Errorf("Expected matches (%d) to equal wins + draws (%d + %d + %d)",
			h2h.Matches, h2h.Team1Wins, h2h.Team2Wins, h2h.Draws)
	}
}

// TestQueryHandler_SearchPlayers tests searching players
func TestQueryHandler_SearchPlayers(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	// Test searching by name
	results, total, err := qh.SearchPlayers(&PlayerQuery{
		Name:  "Neymar",
		Limit: 10,
	})
	if err != nil {
		t.Fatalf("Failed to search players: %v", err)
	}

	if total == 0 {
		t.Error("Expected players to be found")
	}

	// Check all players contain "Neymar"
	for _, p := range results {
		if !contains(p.Name, "Neymar") {
			t.Errorf("Expected player %s to contain 'Neymar'", p.Name)
		}
	}
}

// TestQueryHandler_SearchPlayers_Nationality tests searching by nationality
func TestQueryHandler_SearchPlayers_Nationality(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	results, total, err := qh.SearchPlayers(&PlayerQuery{
		Nationality: "Brazil",
		Limit:       10,
	})
	if err != nil {
		t.Fatalf("Failed to search players: %v", err)
	}

	if total == 0 {
		t.Error("Expected players to be found")
	}

	// Check all players are Brazilian
	for _, p := range results {
		if p.Nationality != "Brazil" && p.Nationality != "Brasil" {
			t.Errorf("Expected Brazilian player, got %s from %s", p.Name, p.Nationality)
		}
	}
}

// TestQueryHandler_SearchPlayers_Club tests searching by club
func TestQueryHandler_SearchPlayers_Club(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	results, _, err := qh.SearchPlayers(&PlayerQuery{
		Club:  "Flamengo",
		Limit: 10,
	})
	if err != nil {
		t.Fatalf("Failed to search players: %v", err)
	}

	// Check all players are from Flamengo
	for _, p := range results {
		if !contains(p.Club, "Flamengo") {
			t.Errorf("Expected Flamengo player, got %s from %s", p.Name, p.Club)
		}
	}
}

// TestQueryHandler_SearchPlayers_Position tests searching by position
func TestQueryHandler_SearchPlayers_Position(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	results, _, err := qh.SearchPlayers(&PlayerQuery{
		Position: "Forward",
		Limit:    10,
	})
	if err != nil {
		t.Fatalf("Failed to search players: %v", err)
	}

	// Check all players are forwards
	for _, p := range results {
		if !contains(p.Position, "Forward") && !contains(p.Position, "Foward") && !contains(p.Position, "Fw") {
			t.Errorf("Expected forward player, got %s at %s", p.Name, p.Position)
		}
	}
}

// TestQueryHandler_GetTopScorers tests getting top scorers
func TestQueryHandler_GetTopScorers(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	scorers, err := qh.GetTopScorers("Brasileirão", 10)
	if err != nil {
		t.Fatalf("Failed to get top scorers: %v", err)
	}

	if len(scorers) == 0 {
		t.Error("Expected scorers to be found")
	}

	// Check scorers are sorted by goals (descending)
	for i := 0; i < len(scorers)-1; i++ {
		if scorers[i].GoalsFor < scorers[i+1].GoalsFor {
			t.Errorf("Scorers not sorted by goals: %s (%d) should come before %s (%d)",
				scorers[i].Team, scorers[i].GoalsFor,
				scorers[i+1].Team, scorers[i+1].GoalsFor)
		}
	}
}

// TestQueryHandler_CalculateStandings tests calculating standings
func TestQueryHandler_CalculateStandings(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	standings, err := qh.CalculateStandings("Brasileirão", "2023")
	if err != nil {
		t.Fatalf("Failed to calculate standings: %v", err)
	}

	if len(standings.Standings) == 0 {
		t.Error("Expected standings to be calculated")
	}

	// Check standings are sorted by points (descending)
	for i := 0; i < len(standings.Standings)-1; i++ {
		if standings.Standings[i].Points < standings.Standings[i+1].Points {
			t.Errorf("Standings not sorted by points: %s (%d) should come before %s (%d)",
				standings.Standings[i].Team, standings.Standings[i].Points,
				standings.Standings[i+1].Team, standings.Standings[i+1].Points)
		}
	}
}

// TestQueryHandler_GetBiggestWins tests getting biggest wins
func TestQueryHandler_GetBiggestWins(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	wins, err := qh.GetBiggestWins("Brasileirão", 10)
	if err != nil {
		t.Fatalf("Failed to get biggest wins: %v", err)
	}

	if len(wins) == 0 {
		t.Error("Expected wins to be found")
	}

	// Check wins are sorted by goal difference (descending)
	for i := 0; i < len(wins)-1; i++ {
		if wins[i].GoalDifference < wins[i+1].GoalDifference {
			t.Errorf("Wins not sorted by goal difference: %d should come before %d",
				wins[i].GoalDifference, wins[i+1].GoalDifference)
		}
	}

	// Check all wins have goal difference > 2
	for _, w := range wins {
		if w.GoalDifference <= 2 {
			t.Errorf("Expected win with goal difference > 2, got %d", w.GoalDifference)
		}
	}
}

// TestQueryHandler_GetRecentMatches tests getting recent matches
func TestQueryHandler_GetRecentMatches(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	matches, err := qh.GetRecentMatches("Flamengo", 10)
	if err != nil {
		t.Fatalf("Failed to get recent matches: %v", err)
	}

	if len(matches) == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches involve Flamengo
	for _, m := range matches {
		if m.HomeTeam != "Flamengo" && m.AwayTeam != "Flamengo" {
			t.Errorf("Expected Flamengo match, got %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

// TestQueryHandler_GetTeamMatches tests getting all matches for a team
func TestQueryHandler_GetTeamMatches(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	matches, err := qh.GetTeamMatches("Flamengo", "Brasileirão")
	if err != nil {
		t.Fatalf("Failed to get team matches: %v", err)
	}

	if len(matches) == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches involve Flamengo
	for _, m := range matches {
		if m.HomeTeam != "Flamengo" && m.AwayTeam != "Flamengo" {
			t.Errorf("Expected Flamengo match, got %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

// TestQueryHandler_GetMatchesBetweenTeams tests getting matches between two teams
func TestQueryHandler_GetMatchesBetweenTeams(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	matches, err := qh.GetMatchesBetweenTeams("Flamengo", "Fluminense")
	if err != nil {
		t.Fatalf("Failed to get matches between teams: %v", err)
	}

	if len(matches) == 0 {
		t.Error("Expected matches to be found")
	}

	// Check all matches involve both teams
	for _, m := range matches {
		team1Played := (m.HomeTeam == "Flamengo" && m.AwayTeam == "Fluminense") ||
			(m.HomeTeam == "Fluminense" && m.AwayTeam == "Flamengo")
		if !team1Played {
			t.Errorf("Expected Flamengo vs Fluminense match, got %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

// TestQueryHandler_GetTeamRecord tests getting team record
func TestQueryHandler_GetTeamRecord(t *testing.T) {
	dl := data.NewDataLoader("data/kaggle")
	if err := dl.LoadAll(); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qh := NewQueryHandler(dl)

	wins, draws, losses, err := qh.GetTeamRecord("Flamengo")
	if err != nil {
		t.Fatalf("Failed to get team record: %v", err)
	}

	// Verify counts add up
	total := wins + draws + losses
	if total == 0 {
		t.Error("Expected matches to be found")
	}

	// Check points calculation
	expectedPoints := wins*3 + draws
	if total > 0 {
		t.Logf("Flamengo record: %dW-%dD-%dL (%d points)", wins, draws, losses, expectedPoints)
	}
}

// Helper function to check if string contains substring
func contains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
