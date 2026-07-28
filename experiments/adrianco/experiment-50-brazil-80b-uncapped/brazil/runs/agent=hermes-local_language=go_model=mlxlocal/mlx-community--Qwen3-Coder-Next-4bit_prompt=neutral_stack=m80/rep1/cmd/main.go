package main

import (
	"context"
	"fmt"
	"log"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"brazilian-soccer-mcp/internal/models"
	"brazilian-soccer-mcp/internal/server"
	"brazilian-soccer-mcp/internal/store"
)

func main() {
	// Load data from CSV files
	storePath := "./data/kaggle"
	db, err := store.LoadData(storePath)
	if err != nil {
		log.Fatalf("Failed to load data: %v", err)
	}

	fmt.Printf("Loaded %d matches, %d players\n", db.MatchCount(), db.PlayerCount())

	// Create the soccer server
	soccerServer := server.NewSoccerServer(db)

	// Create MCP server
	s := mcp.NewServer(&mcp.Implementation{
		Name:    "brazilian-soccer-mcp",
		Version: "1.0.0",
	}, nil)

	// Add tools
	addTools(s, soccerServer)

	// Run the server on stdio transport
	if err := s.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}

func addTools(s *mcp.Server, soccerServer *server.SoccerServer) {
	// Tool: Find matches by team
	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_matches_by_team",
		Description: "Find matches for a specific team",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Team   string `json:"team" jsonschema:"required,description=Team name to search for"`
		Season *int   `json:"season" jsonschema:"description=Season year (optional)"`
	}) (*mcp.CallToolResult, any, error) {
		season := 0
		if args.Season != nil {
			season = *args.Season
		}
		matches := soccerServer.FindMatchesByTeam(args.Team, season)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatMatchesText(matches),
			}},
		}, nil, nil
	})

	// Tool: Find matches between two teams
	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_matches_between_teams",
		Description: "Find matches between two teams",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Team1 string `json:"team1" jsonschema:"required,description=First team name"`
		Team2 string `json:"team2" jsonschema:"required,description=Second team name"`
	}) (*mcp.CallToolResult, any, error) {
		matches := soccerServer.FindMatchesByTeams(args.Team1, args.Team2)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatMatchesText(matches),
			}},
		}, nil, nil
	})

	// Tool: Find matches by season
	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_matches_by_season",
		Description: "Find all matches in a season",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Season int `json:"season" jsonschema:"required,description=Season year"`
	}) (*mcp.CallToolResult, any, error) {
		matches := soccerServer.FindMatchesBySeason(args.Season)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatMatchesText(matches),
			}},
		}, nil, nil
	})

	// Tool: Find matches by competition
	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_matches_by_competition",
		Description: "Find matches by competition",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Competition string `json:"competition" jsonschema:"required,description=Competition name (brasileirao, copa do brasil, libertadores)"`
	}) (*mcp.CallToolResult, any, error) {
		matches := soccerServer.FindMatchesByCompetition(args.Competition)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatMatchesText(matches),
			}},
		}, nil, nil
	})

	// Tool: Find player by name
	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_player_by_name",
		Description: "Find a player by name",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Name string `json:"name" jsonschema:"required,description=Player name to search for"`
	}) (*mcp.CallToolResult, any, error) {
		player := soccerServer.FindPlayerByName(args.Name)
		if player == nil {
			return &mcp.CallToolResult{
				Content: []mcp.Content{&mcp.TextContent{
					Text: "Player not found",
				}},
			}, nil, nil
		}
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatPlayerText(player),
			}},
		}, nil, nil
	})

	// Tool: Find players by nationality
	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_players_by_nationality",
		Description: "Find players by nationality",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Nationality string `json:"nationality" jsonschema:"required,description=Nationality to search for"`
	}) (*mcp.CallToolResult, any, error) {
		players := soccerServer.FindPlayersByNationality(args.Nationality)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatPlayersText(players),
			}},
		}, nil, nil
	})

	// Tool: Find players by club
	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_players_by_club",
		Description: "Find players by club",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Club string `json:"club" jsonschema:"required,description=Club name"`
	}) (*mcp.CallToolResult, any, error) {
		players := soccerServer.FindPlayersByClub(args.Club)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatPlayersText(players),
			}},
		}, nil, nil
	})

	// Tool: Get team statistics
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_team_stats",
		Description: "Get statistics for a team",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Team   string `json:"team" jsonschema:"required,description=Team name"`
		Season int    `json:"season" jsonschema:"required,description=Season year"`
	}) (*mcp.CallToolResult, any, error) {
		stats := soccerServer.GetTeamStats(args.Team, args.Season)
		winRate := 0.0
		if stats.Matches > 0 {
			winRate = float64(stats.Wins) / float64(stats.Matches) * 100
		}
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: fmt.Sprintf("%s (%d): %d matches, %d wins, %d draws, %d losses, GF:%d GA:%d, %.1f%% win rate",
					stats.TeamName, args.Season, stats.Matches, stats.Wins, stats.Draws, stats.Losses,
					stats.GoalsFor, stats.GoalsAgainst, winRate),
			}},
		}, nil, nil
	})

	// Tool: Get head-to-head between two teams
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_head_to_head",
		Description: "Get head-to-head record between two teams",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Team1 string `json:"team1" jsonschema:"required,description=First team"`
		Team2 string `json:"team2" jsonschema:"required,description=Second team"`
	}) (*mcp.CallToolResult, any, error) {
		h2h := soccerServer.GetHeadToHead(args.Team1, args.Team2)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: fmt.Sprintf("%s vs %s: %d matches (%d-%d-%d)",
					h2h.Team1, h2h.Team2, h2h.Matches, h2h.Team1Wins, h2h.Team2Wins, h2h.Draws),
			}},
		}, nil, nil
	})

	// Tool: Get big wins
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_big_wins",
		Description: "Get matches with large goal differences",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Threshold *int `json:"threshold" jsonschema:"description=Minimum goal difference (default: 5)"`
	}) (*mcp.CallToolResult, any, error) {
		threshold := 5
		if args.Threshold != nil {
			threshold = *args.Threshold
		}
		wins := soccerServer.GetBigWins(threshold)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatBigWinsText(wins),
			}},
		}, nil, nil
	})

	// Tool: Get league standings
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_league_standings",
		Description: "Get league standings for a competition and season",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Competition string `json:"competition" jsonschema:"required,description=Competition name"`
		Season      int    `json:"season" jsonschema:"required,description=Season year"`
	}) (*mcp.CallToolResult, any, error) {
		standings := soccerServer.CalculateLeagueStandings(args.Competition, args.Season)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatStandingsText(standings),
			}},
		}, nil, nil
	})

	// Tool: Get average goals per match
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_average_goals",
		Description: "Get average goals per match",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Competition *string `json:"competition" jsonschema:"description=Competition name (optional)"`
		Season      *int    `json:"season" jsonschema:"description=Season year (optional)"`
	}) (*mcp.CallToolResult, any, error) {
		competition := ""
		season := 0
		if args.Competition != nil {
			competition = *args.Competition
		}
		if args.Season != nil {
			season = *args.Season
		}
		avgGoals := soccerServer.GetAverageGoalsPerMatch(competition, season)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: fmt.Sprintf("Average goals per match: %.2f", avgGoals),
			}},
		}, nil, nil
	})

	// Tool: Get home win rate
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_home_win_rate",
		Description: "Get home win rate",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Competition *string `json:"competition" jsonschema:"description=Competition name (optional)"`
		Season      *int    `json:"season" jsonschema:"description=Season year (optional)"`
	}) (*mcp.CallToolResult, any, error) {
		competition := ""
		season := 0
		if args.Competition != nil {
			competition = *args.Competition
		}
		if args.Season != nil {
			season = *args.Season
		}
		homeWinRate := soccerServer.GetHomeWinRate(competition, season)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: fmt.Sprintf("Home win rate: %.1f%%", homeWinRate),
			}},
		}, nil, nil
	})

	// Tool: Get top scorers
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_top_scorers",
		Description: "Get top scoring players",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Limit *int `json:"limit" jsonschema:"description=Number of players to return (default: 10)"`
	}) (*mcp.CallToolResult, any, error) {
		limit := 10
		if args.Limit != nil {
			limit = *args.Limit
		}
		players := soccerServer.GetTopScorers(limit)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatPlayersText(players),
			}},
		}, nil, nil
	})

	// Tool: Get top Brazilian players
	mcp.AddTool(s, &mcp.Tool{
		Name:        "get_top_brazilian_players",
		Description: "Get top-rated Brazilian players",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Limit *int `json:"limit" jsonschema:"description=Number of players to return (default: 10)"`
	}) (*mcp.CallToolResult, any, error) {
		limit := 10
		if args.Limit != nil {
			limit = *args.Limit
		}
		players := soccerServer.GetTopBrazilianPlayers(limit)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatPlayersText(players),
			}},
		}, nil, nil
	})

	// Tool: Compare two teams
	mcp.AddTool(s, &mcp.Tool{
		Name:        "compare_teams",
		Description: "Compare two teams",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args struct {
		Team1 string `json:"team1" jsonschema:"required,description=First team"`
		Team2 string `json:"team2" jsonschema:"required,description=Second team"`
	}) (*mcp.CallToolResult, any, error) {
		result := soccerServer.CompareTeams(args.Team1, args.Team2)
		return &mcp.CallToolResult{
			Content: []mcp.Content{&mcp.TextContent{
				Text: formatCompareTeamsText(result),
			}},
		}, nil, nil
	})
}

// formatMatchesText formats matches as human-readable text
func formatMatchesText(matches []models.Match) string {
	if len(matches) == 0 {
		return "No matches found"
	}
	var result string
	for i, match := range matches {
		if i >= 20 {
			result += fmt.Sprintf("\n... and %d more matches", len(matches)-20)
			break
		}
		result += fmt.Sprintf("%s: %s %d-%d %s (Season %d, Round %d, %s)\n",
			match.Datetime.Format("2006-01-02"), match.HomeTeam, match.HomeGoal, match.AwayGoal,
			match.AwayTeam, match.Season, match.Round, match.Tournament)
	}
	return result
}

// formatPlayersText formats players as human-readable text
func formatPlayersText(players []models.Player) string {
	if len(players) == 0 {
		return "No players found"
	}
	var result string
	for i, player := range players {
		if i >= 20 {
			result += fmt.Sprintf("\n... and %d more players", len(players)-20)
			break
		}
		result += fmt.Sprintf("%d. %s (%s, %s) - Overall: %d, Club: %s\n",
			i+1, player.Name, player.Nationality, player.Position, player.Overall, player.Club)
	}
	return result
}

// formatPlayerText formats a single player as human-readable text
func formatPlayerText(player *models.Player) string {
	return fmt.Sprintf("%s (%d years old, %s) - Overall: %d, Potential: %d, Club: %s, Position: %s",
		player.Name, player.Age, player.Nationality, player.Overall, player.Potential, player.Club, player.Position)
}

// formatBigWinsText formats big wins as human-readable text
func formatBigWinsText(wins []models.BigWin) string {
	if len(wins) == 0 {
		return "No big wins found"
	}
	var result string
	for i, win := range wins {
		if i >= 20 {
			result += fmt.Sprintf("\n... and %d more big wins", len(wins)-20)
			break
		}
		result += fmt.Sprintf("%d. %s: %s %d-%d %s (Goal Diff: %d, %s)\n",
			i+1, win.Date.Format("2006-01-02"), win.HomeTeam, win.HomeGoal, win.AwayGoal,
			win.AwayTeam, win.GoalDiff, win.Tournament)
	}
	return result
}

// formatStandingsText formats standings as human-readable text
func formatStandingsText(standings []models.CompetitionResult) string {
	if len(standings) == 0 {
		return "No standings found"
	}
	var result string
	for i, team := range standings {
		result += fmt.Sprintf("%d. %s - %d pts (%dW-%dD-%dL) GF:%d GA:%d\n",
			i+1, team.TeamName, team.Points, team.Wins, team.Draws, team.Losses,
			team.GoalsFor, team.GoalsAgainst)
	}
	return result
}

// formatCompareTeamsText formats team comparison as human-readable text
func formatCompareTeamsText(result map[string]interface{}) string {
	team1 := result["team_1"].(map[string]interface{})
	team2 := result["team_2"].(map[string]interface{})
	h2h := result["head_to_head"].(map[string]interface{})

	return fmt.Sprintf("Team 1 (%s): %d matches, %d wins, %d draws, %d losses, GF:%d GA:%d %d pts\n"+
		"Team 2 (%s): %d matches, %d wins, %d draws, %d losses, GF:%d GA:%d %d pts\n"+
		"Head-to-Head: %d-%d-%d",
		team1["name"], team1["matches"], team1["wins"], team1["draws"], team1["losses"],
		team1["goals_for"], team1["goals_against"], team1["points"],
		team2["name"], team2["matches"], team2["wins"], team2["draws"], team2["losses"],
		team2["goals_for"], team2["goals_against"], team2["points"],
		h2h["team_1_wins"], h2h["team_2_wins"], h2h["draws"])
}
