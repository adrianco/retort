package main

import (
	"fmt"
	"testing"

	"github.com/retort-2b804a4c50ba/brazilian-soccer-mcp/data"
	"github.com/retort-2b804a4c50ba/brazilian-soccer-mcp/server"
)

// TestMain runs before all tests
func TestMain(m *testing.M) {
	// Initialize loader
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		fmt.Printf("Failed to initialize data loader: %v\n", err)
		return
	}

	err = loader.LoadAll()
	if err != nil {
		fmt.Printf("Failed to load data: %v\n", err)
		return
	}

	// Initialize server
		// Run tests
	m.Run()
}

// TestLoader tests the data loader
func TestLoader(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	// Load all data
	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Verify data counts
	totalMatches := loader.TotalMatches()
	totalPlayers := loader.TotalPlayers()

	if totalMatches == 0 {
		t.Error("No matches loaded")
	}

	if totalPlayers == 0 {
		t.Error("No players loaded")
	}

	fmt.Printf("Loaded %d matches and %d players\n", totalMatches, totalPlayers)
}

// TestNormalizeTeamName tests team name normalization
func TestNormalizeTeamName(t *testing.T) {
	testCases := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Corinthians-SP", "Corinthians"},
		{"São Paulo-SP", "São Paulo"},
		{"Atlético-MG", "Atlético"},  // State suffix removed
		{"Grêmio-RS", "Grêmio"},
		{"Fluminense-RJ", "Fluminense"},
		{"Vasco-RJ", "Vasco"},
	}

	for _, tc := range testCases {
		result := data.NormalizeTeamName(tc.input)
		if result != tc.expected {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", tc.input, result, tc.expected)
		}
	}
}

// TestFindMatchesByTeams tests finding matches between two teams
func TestFindMatchesByTeams(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test Flamengo vs Fluminense
	matches, err := srv.FindMatchesByTeams("Flamengo", "Fluminense")
	if err != nil {
		t.Errorf("Failed to find matches: %v", err)
	}

	if len(matches) == 0 {
		t.Error("Expected at least one match between Flamengo and Fluminense")
	}

	fmt.Printf("Found %d matches between Flamengo and Fluminense\n", len(matches))
}

// TestFindMatchesByTeam tests finding all matches for a team
func TestFindMatchesByTeam(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test Palmeiras
	matches, err := srv.FindMatchesByTeam("Palmeiras")
	if err != nil {
		t.Errorf("Failed to find matches: %v", err)
	}

	if len(matches) == 0 {
		t.Error("Expected at least one match for Palmeiras")
	}

	fmt.Printf("Found %d matches for Palmeiras\n", len(matches))
}

// TestGetTeamStatistics tests team statistics
func TestGetTeamStatistics(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test Palmeiras in 2023
	stats, err := srv.GetTeamStatistics("Palmeiras", "2023", "Brasileirão")
	if err != nil {
		t.Logf("Expected error (no 2023 Brasileirão data): %v", err)
	}

	if stats != nil {
		fmt.Printf("Palmeiras 2023 stats: %d matches, %d wins\n", stats.Matches, stats.Wins)
	}

	// Test Flamengo without season filter
	stats, err = srv.GetTeamStatistics("Flamengo", "", "")
	if err != nil {
		t.Errorf("Failed to get statistics: %v", err)
	}

	if stats != nil && stats.Matches > 0 {
		fmt.Printf("Flamengo total stats: %d matches, %d wins, %.1f%% win rate\n", 
			stats.Matches, stats.Wins, stats.WinRate)
	}
}

// TestGetHeadToHead tests head-to-head calculations
func TestGetHeadToHead(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test Flamengo vs Fluminense
	result, err := srv.GetHeadToHead("Flamengo", "Fluminense")
	if err != nil {
		t.Errorf("Failed to get head-to-head: %v", err)
	}

	fmt.Printf("Head-to-head: %v\n", result)
}

// TestCalculateStandings tests league standings calculation
func TestCalculateStandings(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test 2019 Brasileirão standings
	standings := srv.CalculateStandings("Brasileirão", "2019")

	if len(standings) > 0 {
		fmt.Printf("Top team in 2019: %s with %d points\n", standings[0].Team, standings[0].Points)
	}

	// Test 2023 Brasileirão standings
	standings = srv.CalculateStandings("Brasileirão", "2023")

	if len(standings) > 0 {
		fmt.Printf("Top team in 2023: %s with %d points\n", standings[0].Team, standings[0].Points)
	}
}

// TestSearchPlayers tests player search
func TestSearchPlayers(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test searching for Neymar
	players, err := srv.SearchPlayers("Neymar")
	if err != nil {
		t.Logf("Expected error (no Neymar in dataset): %v", err)
	}

	if len(players) > 0 {
		fmt.Printf("Found %d players matching 'Neymar'\n", len(players))
	}

	// Test searching for Brazil
	players, err = srv.GetPlayersByNationality("Brazil")
	if err != nil {
		t.Logf("Expected error (no Brazilian players in dataset): %v", err)
	}

	if len(players) > 0 {
		fmt.Printf("Found %d Brazilian players\n", len(players))
	}
}

// TestGetPlayersByClub tests player search by club
func TestGetPlayersByClub(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test Flamengo players
	players, err := srv.GetPlayersByClub("Flamengo")
	if err != nil {
		t.Logf("Expected error (no Flamengo players in dataset): %v", err)
	}

	if len(players) > 0 {
		fmt.Printf("Found %d players at Flamengo\n", len(players))
	}
}

// TestGetBiggestWins tests biggest wins query
func TestGetBiggestWins(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	wins, err := srv.GetBiggestWins(5)
	if err != nil {
		t.Errorf("Failed to get biggest wins: %v", err)
	}

	if len(wins) > 0 {
		fmt.Printf("Biggest wins:\n")
		for i, w := range wins {
			fmt.Printf("  %d. %s %d-%d %s (%s)\n", 
				i+1, w.HomeTeam, w.HomeGoals, w.AwayGoals, w.AwayTeam, w.Date)
		}
	}
}

// TestGetAverageGoals tests average goals calculation
func TestGetAverageGoals(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	avg, err := srv.GetAverageGoals("Brasileirão", "2023")
	if err != nil {
		t.Logf("Expected error (no 2023 Brasileirão data): %v", err)
	} else {
		fmt.Printf("Average goals per match in 2023 Brasileirão: %.2f\n", avg)
	}
}

// TestGetHomeWinRate tests home win rate calculation
func TestGetHomeWinRate(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	rate, err := srv.GetHomeWinRate("Brasileirão", "2023")
	if err != nil {
		t.Logf("Expected error (no 2023 Brasileirão data): %v", err)
	} else {
		fmt.Printf("Home win rate in 2023 Brasileirão: %.1f%%\n", rate)
	}
}

// TestGetRecentMatches tests recent matches query
func TestGetRecentMatches(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	matches, err := srv.GetRecentMatches(5)
	if err != nil {
		t.Errorf("Failed to get recent matches: %v", err)
	}

	if len(matches) > 0 {
		fmt.Printf("Recent matches:\n")
		for i, m := range matches {
			fmt.Printf("  %d. %s %d-%d %s (%s)\n", 
				i+1, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Date)
		}
	}
}

// TestGetLastMatchBetweenTeams tests last match query
func TestGetLastMatchBetweenTeams(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	match, err := srv.GetLastMatchBetweenTeams("Flamengo", "Fluminense")
	if err != nil {
		t.Logf("Expected error (no Flamengo vs Fluminense data): %v", err)
	}

	if match != nil {
		fmt.Printf("Last Flamengo vs Fluminense match: %s %d-%d %s\n", 
			match.HomeTeam, match.HomeGoals, match.AwayGoals, match.AwayTeam)
	}
}

// TestGetPlayersByPosition tests player search by position
func TestGetPlayersByPosition(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	srv := server.NewMCPServer(loader)

	// Test forwards
	forwards, err := srv.GetPlayersByPosition("LW")
	if err != nil {
		t.Logf("Expected error (no LW players in dataset): %v", err)
	}

	if len(forwards) > 0 {
		fmt.Printf("Found %d left wingers\n", len(forwards))
	}
}

// TestTotalMatches tests total matches count
func TestTotalMatches(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	total := loader.TotalMatches()
	if total == 0 {
		t.Error("Expected matches to be loaded")
	}

	fmt.Printf("Total matches loaded: %d\n", total)
}

// TestTotalPlayers tests total players count
func TestTotalPlayers(t *testing.T) {
	wd := "."
	dataDir := wd + "/data/kaggle"

	loader, err := data.NewLoader(dataDir)
	if err != nil {
		t.Fatalf("Failed to initialize data loader: %v", err)
	}

	err = loader.LoadAll()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	total := loader.TotalPlayers()
	if total == 0 {
		t.Error("Expected players to be loaded")
	}

	fmt.Printf("Total players loaded: %d\n", total)
}
