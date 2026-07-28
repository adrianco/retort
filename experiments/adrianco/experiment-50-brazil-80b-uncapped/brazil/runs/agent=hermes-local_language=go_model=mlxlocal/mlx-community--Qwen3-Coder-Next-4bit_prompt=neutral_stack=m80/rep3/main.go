package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/retort-2b804a4c50ba/brazilian-soccer-mcp/data"
	"github.com/retort-2b804a4c50ba/brazilian-soccer-mcp/server"
)

// Loader is a type alias for the loader
type Loader = data.Loader

func main() {
	// Get the data directory path
	wd, err := os.Getwd()
	if err != nil {
		log.Fatalf("Failed to get working directory: %v", err)
	}
	dataDir := filepath.Join(wd, "data", "kaggle")

	// Initialize the data loader
	loader, err := data.NewLoader(dataDir)
	if err != nil {
		log.Fatalf("Failed to initialize data loader: %v", err)
	}

	// Load all data
	err = loader.LoadAll()
	if err != nil {
		log.Fatalf("Failed to load data: %v", err)
	}

	// Initialize and start the MCP server
	srv := server.NewMCPServer(loader)
	
	fmt.Println("Brazilian Soccer MCP Server initialized successfully")
	fmt.Printf("Data loaded: %d matches, %d players\n", 
		loader.TotalMatches(), 
		loader.TotalPlayers())
	
	// Example usage
	exampleQueries(srv, loader)
}

func exampleQueries(srv *server.MCPServer, loader *data.Loader) {
	fmt.Println("=== Example Queries ===")

	// Example 1: Find matches between two teams
	fmt.Println("1. Flamengo vs Fluminense matches:")
	results, _ := srv.FindMatchesByTeams("Flamengo", "Fluminense")
	for i, m := range results {
		if i >= 3 {
			break
		}
		fmt.Printf("   %s: %s %d-%d %s (%s Round %d)\n", 
			m.Date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition, m.Round)
	}
	fmt.Printf("   ... and %d more matches\n\n", len(results)-3)

	// Example 2: Team statistics
	fmt.Println("2. Palmeiras home record in 2023:")
	stats, _ := srv.GetTeamStatistics("Palmeiras", "2023", "Brasileirão")
	fmt.Printf("   Matches: %d, Wins: %d, Draws: %d, Losses: %d\n", 
		stats.Matches, stats.Wins, stats.Draws, stats.Losses)
	fmt.Printf("   Goals For: %d, Goals Against: %d\n", stats.GoalsFor, stats.GoalsAgainst)
	fmt.Printf("   Win rate: %.1f%%\n\n", stats.WinRate)

	// Example 3: Brazilian players
	fmt.Println("3. Top Brazilian players:")
	players := loader.GetBrazilianPlayersByRating(10)
	for i, p := range players {
		fmt.Printf("   %d. %s - Overall: %d, Position: %s, Club: %s\n", 
			i+1, p.Name, p.Overall, p.Position, p.Club)
	}
	fmt.Println()

	// Example 4: Competition standings
	fmt.Println("4. 2019 Brasileirão Standings:")
	standings := srv.CalculateStandings("Brasileirão", "2019")
	for i, s := range standings[:5] {
		fmt.Printf("   %d. %s - %d pts (%dW, %dD, %dL)\n", 
			i+1, s.Team, s.Points, s.Wins, s.Draws, s.Losses)
	}
	fmt.Println()

	// Example 5: Player at club
	fmt.Println("5. Players at Flamengo:")
	flamengoPlayers := loader.GetPlayersByClub("Flamengo")
	fmt.Printf("   Found %d players at Flamengo\n", len(flamengoPlayers))
	if len(flamengoPlayers) > 0 {
		fmt.Printf("   Top player: %s (Overall: %d)\n", 
			flamengoPlayers[0].Name, flamengoPlayers[0].Overall)
	}
}
