package main

import (
	"fmt"
)

// runTests executes all tests for the server
func runTests() error {
	fmt.Println("=== Brazilian Soccer MCP Server Tests ===")

	passed := 0
	failed := 0

	// Test 1: Load data
	fmt.Println("Test 1: Loading data...")
	server := NewServer()
	if err := server.LoadData("data/kaggle"); err != nil {
		fmt.Printf("  FAIL: %v\n", err)
		failed++
	} else {
		fmt.Printf("  PASS: Loaded %d matches and %d players\n",
			len(server.Data.BrasileiraoMatches)+len(server.Data.CopaDoBrasilMatches)+
				len(server.Data.CopaLibertadoresMatches)+len(server.Data.BRFootballMatches)+
				len(server.Data.NovoCampeonatoMatches),
			len(server.Data.Players))
		passed++
	}

	// Test 2: Match search by teams
	fmt.Println("\nTest 2: Finding matches between teams...")
	matches := server.Data.GetMatchesByTeams("Flamengo", "Fluminense")
	if len(matches) == 0 {
		fmt.Println("  FAIL: No matches found between Flamengo and Fluminense")
		failed++
	} else {
		fmt.Printf("  PASS: Found %d matches between Flamengo and Fluminense\n", len(matches))
		passed++
	}

	// Test 3: Team statistics
	fmt.Println("\nTest 3: Team statistics...")
	stats := server.Data.GetTeamStats("Palmeiras", 2023)
	if stats.Matches == 0 {
		fmt.Println("  FAIL: No stats found for Palmeiras in 2023")
		failed++
	} else {
		fmt.Printf("  PASS: Palmeiras 2023 stats - %d matches, %d wins\n", stats.Matches, stats.Wins)
		passed++
	}

	// Test 4: Player search
	fmt.Println("\nTest 4: Player search...")
	neymar := server.Data.GetPlayerByName("Neymar")
	if neymar == nil {
		fmt.Println("  FAIL: Player 'Neymar' not found")
		failed++
	} else {
		fmt.Printf("  PASS: Found Neymar, Overall rating: %d\n", neymar.Overall)
		passed++
	}

	// Test 5: Brazilian players
	fmt.Println("\nTest 5: Brazilian players...")
	brazilianPlayers := server.Data.GetBrazilianPlayers()
	if len(brazilianPlayers) == 0 {
		fmt.Println("  FAIL: No Brazilian players found")
		failed++
	} else {
		fmt.Printf("  PASS: Found %d Brazilian players\n", len(brazilianPlayers))
		passed++
	}

	// Test 6: Team standings
	fmt.Println("\nTest 6: Team standings...")
	standings := server.Data.GetTeamStandings("Brasileirão", 2019)
	if len(standings) == 0 {
		fmt.Println("  FAIL: No standings found for 2019 Brasileirão")
		failed++
	} else {
		fmt.Printf("  PASS: Found %d teams in 2019 Brasileirão standings\n", len(standings))
		fmt.Printf("    Champion: %s (%d pts)\n", standings[0].TeamName, standings[0].Points)
		passed++
	}

	// Test 7: Average goals per match
	fmt.Println("\nTest 7: Average goals per match...")
	avg := server.Data.GetAverageGoalsPerMatch()
	fmt.Printf("  PASS: Average goals per match: %.2f\n", avg)
	passed++

	// Test 8: Home win rate
	fmt.Println("\nTest 8: Home win rate...")
	rate := server.Data.GetHomeWinRate()
	fmt.Printf("  PASS: Home win rate: %.1f%%\n", rate)
	passed++

	// Test 9: Big wins
	fmt.Println("\nTest 9: Biggest wins...")
	wins := server.Data.FindBiggestWins(5)
	if len(wins) == 0 {
		fmt.Println("  FAIL: No big wins found")
		failed++
	} else {
		fmt.Printf("  PASS: Found %d big wins\n", len(wins))
		fmt.Printf("    Largest: %s %d-%d %s\n",
			wins[0].HomeTeam, wins[0].HomeGoal, wins[0].AwayGoal, wins[0].AwayTeam)
		passed++
	}

	// Test 10: Natural language query
	fmt.Println("\nTest 10: Natural language query...")
	response, err := server.Query("Who won the 2019 Brasileirão?")
	if err != nil {
		fmt.Printf("  FAIL: Query error: %v\n", err)
		failed++
	} else if !contains(response, "Flamengo") {
		fmt.Println("  FAIL: Expected Flamengo to be mentioned")
		fmt.Printf("    Response: %s\n", response[:min(100, len(response))])
		failed++
	} else {
		fmt.Println("  PASS: Natural language query worked")
		fmt.Printf("    Response preview: %s...\n", response[:min(100, len(response))])
		passed++
	}

	// Summary
	fmt.Printf("\n=== Test Summary ===\n")
	fmt.Printf("Passed: %d\n", passed)
	fmt.Printf("Failed: %d\n", failed)

	if failed > 0 {
		return fmt.Errorf("%d test(s) failed", failed)
	}

	return nil
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && findSubstring(s, substr))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
