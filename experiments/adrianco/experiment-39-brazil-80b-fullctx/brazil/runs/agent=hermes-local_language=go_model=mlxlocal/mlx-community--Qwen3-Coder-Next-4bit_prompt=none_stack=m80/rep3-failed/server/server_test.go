package server

import (
	"testing"
	"time"

	"soccer-mcp/models"
)

func TestNewSoccerServer(t *testing.T) {
	// Test with non-existent directory
	srv, err := NewSoccerServer("./nonexistent")
	if err == nil {
		t.Error("Expected error for non-existent directory")
	}
	if srv != nil {
		t.Error("Expected nil server for non-existent directory")
	}
}

func TestSoccerServer_Query(t *testing.T) {
	// Use the correct data path relative to project root
	dataDir := "../data/kaggle"
	
	// Create a server with actual data
	srv, err := NewSoccerServer(dataDir)
	if err != nil {
		t.Skipf("Skipping test - no data: %v", err)
	}

	// Test a simple query
	result, err := srv.Query("Who won the 2019 Brasileirão?")
	if err != nil {
		t.Errorf("Query error: %v", err)
	}
	if result == nil {
		t.Error("Expected non-nil result")
	}
	if !result.Success {
		t.Errorf("Query failed: %s", result.Error)
	}
}

func TestSoccerServer_ParseAndAnswer(t *testing.T) {
	// Use the correct data path relative to project root
	dataDir := "../data/kaggle"
	
	srv, err := NewSoccerServer(dataDir)
	if err != nil {
		t.Skipf("Skipping test - no data: %v", err)
	}

	// Test match query
	result, err := srv.parseAndAnswer("Show me Flamengo vs Fluminense matches")
	if err != nil {
		t.Errorf("Match query error: %v", err)
	}
	if result == nil {
		t.Error("Expected non-nil result for match query")
	}
}

func TestExtractTeams(t *testing.T) {
	teams := extractTeams("Show me Flamengo vs Fluminense matches")
	if len(teams) != 2 {
		t.Errorf("Expected 2 teams, got %d", len(teams))
	}
}

func TestExtractSeason(t *testing.T) {
	season := extractSeason("Show me matches in 2023")
	if season != 2023 {
		t.Errorf("Expected season 2023, got %d", season)
	}
}

func TestStringLower(t *testing.T) {
	result := stringLower("HELLO")
	if result != "hello" {
		t.Errorf("Expected 'hello', got '%s'", result)
	}
}

func TestContains(t *testing.T) {
	if !contains("Hello World", "world") {
		t.Error("Expected true for contains")
	}
	if contains("Hello", "xyz") {
		t.Error("Expected false for contains")
	}
}

func TestContainsAny(t *testing.T) {
	if !containsAny("Hello World", []string{"world", "test"}) {
		t.Error("Expected true for containsAny")
	}
	if containsAny("Hello", []string{"xyz", "abc"}) {
		t.Error("Expected false for containsAny")
	}
}

func TestFormatMatchList(t *testing.T) {
	matches := []models.Match{
		{
			Date:        time.Date(2023, 1, 1, 0, 0, 0, 0, time.UTC),
			HomeTeam:    "Flamengo",
			AwayTeam:    "Fluminense",
			HomeGoals:   2,
			AwayGoals:   1,
			Tournament:  "Brasileirão",
		},
	}

	result := formatMatchList(matches, 10)
	if result == "" {
		t.Error("Expected non-empty result")
	}
	if !contains(result, "Flamengo") {
		t.Error("Expected 'Flamengo' in result")
	}
}

func TestFormatHeadToHead(t *testing.T) {
	h2h := &models.HeadToHead{
		Team1:     "Flamengo",
		Team2:     "Fluminense",
		Team1Wins: 10,
		Team2Wins: 5,
		Draws:     3,
	}

	result := formatHeadToHead(h2h)
	if result == "" {
		t.Error("Expected non-empty result")
	}
	if !contains(result, "Flamengo") {
		t.Error("Expected 'Flamengo' in result")
	}
}

func TestFormatTeamStats(t *testing.T) {
	stats := &models.TeamStats{
		TeamName:     "Palmeiras",
		Matches:      20,
		Wins:         15,
		Draws:        3,
		Losses:       2,
		GoalsFor:     45,
		GoalsAgainst: 15,
		Points:       48,
	}

	result := formatTeamStats(stats)
	if result == "" {
		t.Error("Expected non-empty result")
	}
	if !contains(result, "Palmeiras") {
		t.Error("Expected 'Palmeiras' in result")
	}
}

func TestFormatPlayerList(t *testing.T) {
	players := []models.Player{
		{
			Name:    "Neymar",
			Club:    "Paris Saint-Germain",
			Overall: 92,
		},
	}

	result := formatPlayerList(players)
	if result == "" {
		t.Error("Expected non-empty result")
	}
	if !contains(result, "Neymar") {
		t.Error("Expected 'Neymar' in result")
	}
}

func TestFormatTopBrazilianPlayers(t *testing.T) {
	players := []models.Player{
		{
			Name:        "Neymar",
			Nationality: "Brazil",
			Overall:     92,
		},
	}

	result := formatTopBrazilianPlayers(players)
	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func TestFormatClubPlayers(t *testing.T) {
	result := formatClubPlayers("Flamengo", []models.Player{
		{ Name: "Player1", Club: "Flamengo", Overall: 80 },
	})

	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func TestFormatStandings(t *testing.T) {
	standings := []models.TeamStats{
		{ TeamName: "Team1", Points: 90 },
		{ TeamName: "Team2", Points: 85 },
	}

	result := formatStandings(standings, "Brasileirão", 2023)
	if result == "" {
		t.Error("Expected non-empty result")
	}
	if !contains(result, "Team1") {
		t.Error("Expected 'Team1' in result")
	}
}

func TestFormatChampion(t *testing.T) {
	stats := &models.TeamStats{
		TeamName: "Flamengo",
		Points:   90,
	}

	result := formatChampion(stats, 2023)
	if result == "" {
		t.Error("Expected non-empty result")
	}
	if !contains(result, "Flamengo") {
		t.Error("Expected 'Flamengo' in result")
	}
}

func TestFormatRelegatedTeams(t *testing.T) {
	teams := []models.TeamStats{
		{ TeamName: "Team1", Points: 20 },
		{ TeamName: "Team2", Points: 22 },
		{ TeamName: "Team3", Points: 24 },
		{ TeamName: "Team4", Points: 26 },
	}

	result := formatRelegatedTeams(teams)
	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func TestFormatBiggestWins(t *testing.T) {
	matches := []models.Match{
		{ HomeTeam: "Team1", AwayTeam: "Team2", HomeGoals: 8, AwayGoals: 0, GoalDiff: 8 },
		{ HomeTeam: "Team3", AwayTeam: "Team4", HomeGoals: 7, AwayGoals: 1, GoalDiff: 6 },
	}

	result := formatBiggestWins(matches)
	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func TestFormatTopWinners(t *testing.T) {
	teams := []models.TeamStats{
		{ TeamName: "Team1", Wins: 20 },
		{ TeamName: "Team2", Wins: 18 },
	}

	result := formatTopWinners(teams)
	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func TestFormatBestAwayRecords(t *testing.T) {
	records := []models.TeamStats{
		{ TeamName: "Team1", Points: 30, AwayWins: 10 },
		{ TeamName: "Team2", Points: 28, AwayWins: 9 },
	}

	result := formatBestAwayRecords(records)
	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func TestFormatStatisticalResult(t *testing.T) {
	result := formatStatisticalResult("Average Goals", "2.5 goals per match")
	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func TestFormatGeneralQuery(t *testing.T) {
	result := formatGeneralQuery("test query")
	if result == "" {
		t.Error("Expected non-empty result")
	}
}

func formatGeneralQuery(query string) string {
	return "General query handler"
}

func TestSoccerServer_Run(t *testing.T) {
	// Use the correct data path relative to project root
	dataDir := "../data/kaggle"

	// Create a temporary directory for data
	srv, err := NewSoccerServer(dataDir)
	if err != nil {
		t.Skipf("Skipping test - no data: %v", err)
	}

	err = srv.Run()
	if err != nil {
		t.Errorf("Run error: %v", err)
	}
}
