package main

import (
	"path/filepath"
	"testing"
)

func TestDataLoading(t *testing.T) {
	// Get the data directory path
	dataDir := "."
	
	// Create match data store
	matchStore := NewMatchDataStore(dataDir)
	
	// Load all match files
	matchFiles := []string{
		"Brasileirao_Matches.csv",
		"Brazilian_Cup_Matches.csv",
		"Libertadores_Matches.csv",
		"BR-Football-Dataset.csv",
		"novo_campeonato_brasileiro.csv",
	}
	
	for _, file := range matchFiles {
		filePath := filepath.Join(dataDir, "data", "kaggle", file)
		if err := matchStore.LoadCSV(filePath, file); err != nil {
			t.Errorf("Failed to load %s: %v", file, err)
		}
	}
	
	// Verify data was loaded
	totalMatches := matchStore.TotalMatches()
	if totalMatches == 0 {
		t.Error("No matches loaded")
	}
	t.Logf("Total matches loaded: %d", totalMatches)
}

func TestPlayerDataLoading(t *testing.T) {
	dataDir := "."
	playerStore := NewPlayerDataStore(dataDir)
	
	playerFile := filepath.Join(dataDir, "data", "kaggle", "fifa_data.csv")
	if err := playerStore.LoadCSV(playerFile); err != nil {
		t.Errorf("Failed to load player data: %v", err)
	}
	
	totalPlayers := playerStore.TotalPlayers()
	if totalPlayers == 0 {
		t.Error("No players loaded")
	}
	t.Logf("Total players loaded: %d", totalPlayers)
}

func TestMatchQueries(t *testing.T) {
	dataDir := "."
	matchStore := NewMatchDataStore(dataDir)
	
	// Load sample data
	matchFiles := []string{"Brasileirao_Matches.csv"}
	for _, file := range matchFiles {
		filePath := filepath.Join(dataDir, "data", "kaggle", file)
		if err := matchStore.LoadCSV(filePath, file); err != nil {
			t.Skipf("Skipping match queries test: %v", err)
		}
	}
	
	// Test finding matches by team
	matches := matchStore.FindMatchesByTeam("Flamengo")
	t.Logf("Found %d matches for Flamengo", len(matches))
	
	// Test finding teams
	teams := matchStore.FindTeams("Flamengo")
	if len(teams) == 0 {
		t.Error("No teams found")
	}
	t.Logf("Found teams: %v", teams)
}

func TestTeamStats(t *testing.T) {
	dataDir := "."
	matchStore := NewMatchDataStore(dataDir)
	
	// Load sample data
	matchFiles := []string{"Brasileirao_Matches.csv"}
	for _, file := range matchFiles {
		filePath := filepath.Join(dataDir, "data", "kaggle", file)
		if err := matchStore.LoadCSV(filePath, file); err != nil {
			t.Skipf("Skipping team stats test: %v", err)
		}
	}
	
	// Test getting team stats - check for available seasons
	stats := matchStore.GetTeamStats("Palmeiras", "2012")
	t.Logf("Palmeiras 2012 stats: %d matches, %d wins", stats.Matches, stats.Wins)
	
	if stats.Matches == 0 {
		t.Error("No matches found for Palmeiras 2012")
	}
}

func TestBrasileiraoStandings(t *testing.T) {
	dataDir := "."
	matchStore := NewMatchDataStore(dataDir)
	
	// Load sample data
	matchFiles := []string{"Brasileirao_Matches.csv"}
	for _, file := range matchFiles {
		filePath := filepath.Join(dataDir, "data", "kaggle", file)
		if err := matchStore.LoadCSV(filePath, file); err != nil {
			t.Skipf("Skipping standings test: %v", err)
		}
	}
	
	// Test getting standings
	standings := matchStore.GetBrasileiraoStandings("2012")
	if len(standings) == 0 {
		t.Error("No standings found for 2012")
	} else {
		t.Logf("Top team in 2012: %s (%d points)", standings[0].Team, standings[0].Points)
	}
}

func TestPlayerSearch(t *testing.T) {
	dataDir := "."
	playerStore := NewPlayerDataStore(dataDir)
	
	// Load sample data
	playerFile := filepath.Join(dataDir, "data", "kaggle", "fifa_data.csv")
	if err := playerStore.LoadCSV(playerFile); err != nil {
		t.Skipf("Skipping player search test: %v", err)
	}
	
	// Test searching players
	players := playerStore.SearchPlayers("Neymar")
	t.Logf("Found %d players matching 'Neymar'", len(players))
	
	// Test finding Brazilian players
	brazilianPlayers := playerStore.GetTopBrazilianPlayers(5)
	if len(brazilianPlayers) == 0 {
		t.Error("No Brazilian players found")
	} else {
		t.Logf("Top Brazilian players: %v", brazilianPlayers[0].Name)
	}
}

func TestTeamNameNormalization(t *testing.T) {
	testCases := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"São Paulo-SP", "São Paulo"},
		{"Grêmio-RS", "Grêmio"},
		{"Corinthians-SP", "Corinthians"},
	}
	
	for _, tc := range testCases {
		result := normalizeTeamName(tc.input)
		if result != tc.expected {
			t.Errorf("normalizeTeamName(%q) = %q, want %q", tc.input, result, tc.expected)
		}
	}
}

func TestDateParsing(t *testing.T) {
	testCases := []struct {
		input    string
		expected string
	}{
		{"2023-09-03", "2023-09-03"},
		{"03/09/2023", "2023-09-03"},
		{"2012-05-19 18:30:00", "2012-05-19"},
	}
	
	for _, tc := range testCases {
		result := parseDate(tc.input)
		if result.IsZero() {
			t.Errorf("parseDate(%q) returned zero time", tc.input)
		}
	}
}

func TestMatchCount(t *testing.T) {
	dataDir := "."
	matchStore := NewMatchDataStore(dataDir)
	
	// Load all match files
	matchFiles := []string{
		"Brasileirao_Matches.csv",
		"Brazilian_Cup_Matches.csv",
		"Libertadores_Matches.csv",
		"BR-Football-Dataset.csv",
		"novo_campeonato_brasileiro.csv",
	}
	
	for _, file := range matchFiles {
		filePath := filepath.Join(dataDir, "data", "kaggle", file)
		if err := matchStore.LoadCSV(filePath, file); err != nil {
			t.Errorf("Failed to load %s: %v", file, err)
		}
	}
	
	totalMatches := matchStore.TotalMatches()
	t.Logf("Total matches across all files: %d", totalMatches)
	
	// Verify we have a reasonable number of matches
	if totalMatches < 1000 {
		t.Errorf("Expected at least 1000 matches, got %d", totalMatches)
	}
}

func TestPlayerCount(t *testing.T) {
	dataDir := "."
	playerStore := NewPlayerDataStore(dataDir)
	
	// Load player data
	playerFile := filepath.Join(dataDir, "data", "kaggle", "fifa_data.csv")
	if err := playerStore.LoadCSV(playerFile); err != nil {
		t.Errorf("Failed to load player data: %v", err)
	}
	
	totalPlayers := playerStore.TotalPlayers()
	t.Logf("Total players loaded: %d", totalPlayers)
	
	// Verify we have a reasonable number of players
	if totalPlayers < 1000 {
		t.Errorf("Expected at least 1000 players, got %d", totalPlayers)
	}
}
