// Brazilian Soccer MCP Server
// Provides tools for querying Brazilian soccer data from Kaggle datasets.
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Global store instance used by tool handlers
var store *Store

func main() {
	ctx := context.Background()

	// Initialize store
	store = NewStore()

	// Load datasets
	dataDir := filepath.Join("data", "kaggle")
	if len(os.Args) > 1 {
		dataDir = os.Args[1]
	}

	// Load match data
	loadMatches(dataDir)
	log.Printf("Loaded %d matches from all sources", len(store.Matches))

	// Load player data
	players, err := LoadFIFAPlayers(filepath.Join(dataDir, "fifa_data.csv"))
	if err != nil {
		log.Printf("Warning: loading FIFA data: %v", err)
	} else {
		store.AddPlayers(players)
		log.Printf("Loaded %d players from FIFA data", len(players))
	}

	// Build MCP server
	server := mcp.NewServer(&mcp.Implementation{
		Name:    "brazilian-soccer-mcp",
		Version: "1.0.0",
	}, nil)

	// Add tools
	tools, err := BuildTools(store)
	if err != nil {
		log.Fatalf("Error building tools: %v", err)
	}

	for _, tool := range tools {
		switch tool.Name {
		case "search_matches":
			handler := func(ctx context.Context, req *mcp.CallToolRequest, input SearchMatchesInput) (*mcp.CallToolResult, SearchMatchesOutput, error) {
				if input.Limit <= 0 {
					input.Limit = 50
				}
				matches := store.SearchMatches(input.Team, input.Competition, input.Season, input.DateStart, input.DateEnd)
				if len(matches) > input.Limit {
					matches = matches[:input.Limit]
				}
				return nil, SearchMatchesOutput{
					Matches: matches,
					Count:   len(matches),
					Team:    input.Team,
				}, nil
			}
			mcp.AddTool(server, tool, handler)
		case "team_stats":
			handler := func(ctx context.Context, req *mcp.CallToolRequest, input TeamStatsInput) (*mcp.CallToolResult, TeamStatsOutput, error) {
				stats := store.TeamStats(input.TeamName, input.Competition, input.Season)
				return nil, TeamStatsOutput{
					TeamName:     stats.TeamName,
					Matches:      stats.Matches,
					Wins:         stats.Wins,
					Draws:        stats.Draws,
					Losses:       stats.Losses,
					GoalsFor:     stats.GoalsFor,
					GoalsAgainst: stats.GoalsAgainst,
					WinRate:      stats.WinRate,
				}, nil
			}
			mcp.AddTool(server, tool, handler)
		case "player_search":
			handler := func(ctx context.Context, req *mcp.CallToolRequest, input PlayerSearchInput) (*mcp.CallToolResult, PlayerSearchOutput, error) {
				if input.Limit <= 0 {
					input.Limit = 50
				}
				players := store.SearchPlayers(input.Name, input.Nationality, input.Club, input.Position)
				if len(players) > input.Limit {
					players = players[:input.Limit]
				}
				return nil, PlayerSearchOutput{
					Players: players,
					Count:   len(players),
				}, nil
			}
			mcp.AddTool(server, tool, handler)
		case "head_to_head":
			handler := func(ctx context.Context, req *mcp.CallToolRequest, input HeadToHeadInput) (*mcp.CallToolResult, HeadToHeadOutput, error) {
				h2h := store.HeadToHead(input.Team1, input.Team2)
				return nil, HeadToHeadOutput{
					Team1:        h2h.Team1,
					Team2:        h2h.Team2,
					Team1Wins:    h2h.Team1Wins,
					Team2Wins:    h2h.Team2Wins,
					Draws:        h2h.Draws,
					TotalMatches: h2h.TotalMatches,
					Matches:      h2h.Matches,
				}, nil
			}
			mcp.AddTool(server, tool, handler)
		case "standings":
			handler := func(ctx context.Context, req *mcp.CallToolRequest, input StandingsInput) (*mcp.CallToolResult, StandingsOutput, error) {
				seasonNum := parseInt(input.Season)
				table := store.CompetitionStandings(input.Competition, input.Season)

				entries := make([]StandingsEntry, 0, len(table))
				for _, e := range table {
					e.GoalDiff = e.GoalsFor - e.GoalsAgainst
					entries = append(entries, *e)
				}

				sortStandings(entries)

				return nil, StandingsOutput{
					Competition: input.Competition,
					Season:      seasonNum,
					Standings:   entries,
				}, nil
			}
			mcp.AddTool(server, tool, handler)
		case "biggest_wins":
			handler := func(ctx context.Context, req *mcp.CallToolRequest, input BiggestWinsInput) (*mcp.CallToolResult, BiggestWinsOutput, error) {
				if input.Limit <= 0 {
					input.Limit = 20
				}
				wins := store.BiggestWins(input.Competition, input.Limit)
				return nil, BiggestWinsOutput{
					Wins:  wins,
					Count: len(wins),
				}, nil
			}
			mcp.AddTool(server, tool, handler)
		case "stats":
			handler := func(ctx context.Context, req *mcp.CallToolRequest, input StatsInput) (*mcp.CallToolResult, StatsOutput, error) {
				s := store.StatsAnalysis(input.Competition, input.Season)
				return nil, StatsOutput{
					AvgGoalsPerMatch: s.AvgGoalsPerMatch,
					HomeWinRate:      s.HomeWinRate,
					DrawRate:         s.DrawRate,
					AwayWinRate:      s.AwayWinRate,
					TotalMatches:     s.TotalMatches,
					TotalGoals:       s.TotalGoals,
				}, nil
			}
			mcp.AddTool(server, tool, handler)
		}
	}

	// Connect over stdio
	transport := &mcp.StdioTransport{}
	session, err := server.Connect(ctx, transport, nil)
	if err != nil {
		log.Fatalf("Failed to connect server: %v", err)
	}
	defer session.Close()

	fmt.Fprintf(os.Stderr, "Brazilian Soccer MCP Server started\n")
	fmt.Fprintf(os.Stderr, "Matches loaded: %d\n", len(store.Matches))
	fmt.Fprintf(os.Stderr, "Players loaded: %d\n", len(store.Players))
	fmt.Fprintf(os.Stderr, "Tools registered: %d\n", len(tools))

	// Run server
	if err := server.Run(ctx, transport); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}

func loadMatches(dataDir string) {
	files := []struct {
		name   string
		loadFn func(string) ([]Match, error)
		errTag string
	}{
		{"Brasileirao_Matches.csv", LoadBrasileirao, "Brasileirao_Matches"},
		{"Brazilian_Cup_Matches.csv", LoadCopaBrasil, "Brazilian_Cup"},
		{"Libertadores_Matches.csv", LoadLibertadores, "Libertadores"},
		{"BR-Football-Dataset.csv", LoadBRFootball, "BR-Football"},
		{"novo_campeonato_brasileiro.csv", LoadNovoCampeonato, "Novo_Campeonato"},
	}

	for _, f := range files {
		path := filepath.Join(dataDir, f.name)
		matches, err := f.loadFn(path)
		if err != nil {
			log.Printf("Warning: loading %s (%s): %v", f.name, f.errTag, err)
			continue
		}
		store.AddMatches(matches)
		log.Printf("  Loaded %d %s matches", len(matches), f.errTag)
	}
}

func sortStandings(entries []StandingsEntry) {
	for i := 0; i < len(entries); i++ {
		for j := i + 1; j < len(entries); j++ {
			if entries[i].Points < entries[j].Points ||
				(entries[i].Points == entries[j].Points && entries[i].GoalDiff < entries[j].GoalDiff) ||
				(entries[i].Points == entries[j].Points && entries[i].GoalDiff == entries[j].GoalDiff && entries[i].GoalsFor < entries[j].GoalsFor) {
				entries[i], entries[j] = entries[j], entries[i]
			}
		}
	}
}
