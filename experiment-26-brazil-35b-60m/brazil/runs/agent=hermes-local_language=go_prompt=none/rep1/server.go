package main

import (
	"context"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

// BuildMCPTools creates the list of MCP tools
func BuildMCPTools(analyzer *QueryAnalyzer, store *DataStore) []mcp.Tool {
	tools := []mcp.Tool{
		mcp.NewTool("search_matches_by_team",
			mcp.WithDescription("Search for matches involving a specific team across all competitions"),
			mcp.WithString("team", mcp.Required(), mcp.Description("Team name to search for")),
			mcp.WithString("competition", mcp.Description("Filter by competition name (optional)")),
		),
		mcp.NewTool("search_matches_between_teams",
			mcp.WithDescription("Search for matches between two specific teams"),
			mcp.WithString("team1", mcp.Required(), mcp.Description("First team name")),
			mcp.WithString("team2", mcp.Required(), mcp.Description("Second team name")),
		),
		mcp.NewTool("get_team_stats",
			mcp.WithDescription("Get aggregated statistics for a team across all competitions"),
			mcp.WithString("team", mcp.Required(), mcp.Description("Team name")),
			mcp.WithString("competition", mcp.Description("Filter by competition (optional)")),
			mcp.WithString("season", mcp.Description("Filter by season/year (optional)")),
		),
		mcp.NewTool("get_head_to_head",
			mcp.WithDescription("Get head-to-head statistics between two teams"),
			mcp.WithString("team1", mcp.Required(), mcp.Description("First team name")),
			mcp.WithString("team2", mcp.Required(), mcp.Description("Second team name")),
		),
		mcp.NewTool("search_players_by_name",
			mcp.WithDescription("Search for players by name substring (FIFA dataset)"),
			mcp.WithString("name", mcp.Required(), mcp.Description("Player name to search for")),
			mcp.WithInteger("limit", mcp.Description("Maximum number of results")),
		),
		mcp.NewTool("get_players_by_club",
			mcp.WithDescription("Get all players at a specific club (FIFA dataset)"),
			mcp.WithString("club", mcp.Required(), mcp.Description("Club name")),
			mcp.WithInteger("limit", mcp.Description("Maximum number of results")),
		),
		mcp.NewTool("get_players_by_nationality",
			mcp.WithDescription("Get players of a given nationality (FIFA dataset)"),
			mcp.WithString("nationality", mcp.Required(), mcp.Description("Nationality to search for")),
		),
		mcp.NewTool("get_brazilian_players",
			mcp.WithDescription("Get all Brazilian players from the FIFA dataset"),
			mcp.WithInteger("limit", mcp.Description("Maximum number of results")),
		),
		mcp.NewTool("get_top_players_by_position",
			mcp.WithDescription("Get top-rated players at a given position"),
			mcp.WithString("position", mcp.Required(), mcp.Description("Position code (e.g., FW, MF, DF, GK)")),
			mcp.WithInteger("limit", mcp.Description("Maximum number of results")),
		),
		mcp.NewTool("get_competition_standings",
			mcp.WithDescription("Get competition standings calculated from match data"),
			mcp.WithString("competition", mcp.Required(), mcp.Description("Competition name")),
			mcp.WithString("season", mcp.Description("Filter by season/year")),
		),
		mcp.NewTool("get_biggest_wins",
			mcp.WithDescription("Get the biggest margin victories across all competitions"),
			mcp.WithInteger("limit", mcp.Description("Maximum number of results")),
		),
		mcp.NewTool("get_average_goals",
			mcp.WithDescription("Get average goals per match statistics"),
			mcp.WithString("competition", mcp.Description("Filter by competition (optional)")),
		),
		mcp.NewTool("get_stats_by_competition",
			mcp.WithDescription("Get statistical breakdown per competition"),
		),
		mcp.NewTool("get_club_players_summary",
			mcp.WithDescription("Get Brazilian player counts per Brazilian club"),
		),
		mcp.NewTool("get_data_summary",
			mcp.WithDescription("Get summary of all loaded datasets and record counts"),
		),
	}
	return tools
}

func toJSONResult(data any) (*mcp.CallToolResult, error) {
	result, err := mcp.NewToolResultJSON(data)
	if err != nil {
		return mcp.NewToolResultErrorf("failed to serialize: %v", err), nil
	}
	return result, nil
}

// BuildMCPToolHandlers creates handler functions for each tool
func BuildMCPToolHandlers(analyzer *QueryAnalyzer, store *DataStore) map[string]server.ToolHandlerFunc {
	handlers := make(map[string]server.ToolHandlerFunc)

	handlers["search_matches_by_team"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		team := mcp.ParseString(request, "team", "")
		competition := mcp.ParseString(request, "competition", "")

		if team == "" {
			return mcp.NewToolResultError("team parameter is required"), nil
		}

		results := analyzer.SearchMatchesByTeam(team)
		if competition != "" {
			var filtered []MatchResult
			for _, r := range results {
				if r.Competition == competition {
					filtered = append(filtered, r)
				}
			}
			results = filtered
		}
		if results == nil {
			results = []MatchResult{}
		}

		return toJSONResult(map[string]interface{}{
			"matches":      results,
			"total_matches": len(results),
			"team":         team,
		})
	}

	handlers["search_matches_between_teams"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		team1 := mcp.ParseString(request, "team1", "")
		team2 := mcp.ParseString(request, "team2", "")

		if team1 == "" || team2 == "" {
			return mcp.NewToolResultError("team1 and team2 parameters are required"), nil
		}

		results := analyzer.SearchMatchesByTeams(team1, team2)
		if results == nil {
			results = []MatchResult{}
		}

		return toJSONResult(map[string]interface{}{
			"matches":      results,
			"total_matches": len(results),
			"team1":         team1,
			"team2":         team2,
		})
	}

	handlers["get_team_stats"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		team := mcp.ParseString(request, "team", "")
		competition := mcp.ParseString(request, "competition", "")
		season := mcp.ParseString(request, "season", "")

		if team == "" {
			return mcp.NewToolResultError("team parameter is required"), nil
		}

		stats := analyzer.GetTeamStats(team, competition, season)
		if stats == nil {
			stats = &TeamStats{}
		}

		return toJSONResult(stats)
	}

	handlers["get_head_to_head"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		team1 := mcp.ParseString(request, "team1", "")
		team2 := mcp.ParseString(request, "team2", "")

		if team1 == "" || team2 == "" {
			return mcp.NewToolResultError("team1 and team2 parameters are required"), nil
		}

		h2h := analyzer.GetHeadToHead(team1, team2)
		if h2h == nil {
			h2h = &HeadToHead{}
		}

		return toJSONResult(h2h)
	}

	handlers["search_players_by_name"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		name := mcp.ParseString(request, "name", "")
		limit := mcp.ParseInt(request, "limit", 50)

		if name == "" {
			return mcp.NewToolResultError("name parameter is required"), nil
		}

		results := analyzer.SearchPlayersByName(name)
		if len(results) > limit {
			results = results[:limit]
		}
		if results == nil {
			results = []PlayerResult{}
		}

		return toJSONResult(map[string]interface{}{
			"players": results,
			"count":   len(results),
			"name":    name,
		})
	}

	handlers["get_players_by_club"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		club := mcp.ParseString(request, "club", "")
		limit := mcp.ParseInt(request, "limit", 100)

		if club == "" {
			return mcp.NewToolResultError("club parameter is required"), nil
		}

		results := analyzer.GetPlayersByClub(club)
		if len(results) > limit {
			results = results[:limit]
		}
		if results == nil {
			results = []PlayerResult{}
		}

		return toJSONResult(map[string]interface{}{
			"players": results,
			"count":   len(results),
			"club":    club,
		})
	}

	handlers["get_players_by_nationality"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		nationality := mcp.ParseString(request, "nationality", "")

		if nationality == "" {
			return mcp.NewToolResultError("nationality parameter is required"), nil
		}

		results := analyzer.GetPlayersByNationality(nationality)
		if results == nil {
			results = []PlayerResult{}
		}

		return toJSONResult(map[string]interface{}{
			"players":     results,
			"count":       len(results),
			"nationality": nationality,
		})
	}

	handlers["get_brazilian_players"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		limit := mcp.ParseInt(request, "limit", 100)

		results := analyzer.GetBrazilianPlayers(limit)
		if results == nil {
			results = []PlayerResult{}
		}

		return toJSONResult(map[string]interface{}{
			"players": results,
			"count":   len(results),
		})
	}

	handlers["get_top_players_by_position"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		position := mcp.ParseString(request, "position", "")
		limit := mcp.ParseInt(request, "limit", 20)

		if position == "" {
			return mcp.NewToolResultError("position parameter is required"), nil
		}

		results := analyzer.GetTopPlayersByPosition(position, limit)
		if results == nil {
			results = []PlayerResult{}
		}

		return toJSONResult(map[string]interface{}{
			"players":  results,
			"count":    len(results),
			"position": position,
		})
	}

	handlers["get_competition_standings"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		competition := mcp.ParseString(request, "competition", "")
		season := mcp.ParseString(request, "season", "")

		if competition == "" {
			return mcp.NewToolResultError("competition parameter is required"), nil
		}

		standings := analyzer.GetCompetitionStandings(competition, season)
		if standings == nil {
			standings = []CompetitionStanding{}
		}

		return toJSONResult(map[string]interface{}{
			"standings":   standings,
			"competition": competition,
			"season":      season,
		})
	}

	handlers["get_biggest_wins"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		limit := mcp.ParseInt(request, "limit", 20)

		wins := analyzer.GetBiggestWins(limit)
		if wins == nil {
			wins = []BigWin{}
		}

		return toJSONResult(map[string]interface{}{
			"wins":  wins,
			"count": len(wins),
		})
	}

	handlers["get_average_goals"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		competition := mcp.ParseString(request, "competition", "")

		stats := analyzer.GetAverageGoals(competition)
		if stats == nil {
			stats = &AverageGoalsStats{}
		}

		return toJSONResult(stats)
	}

	handlers["get_stats_by_competition"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		stats := analyzer.GetStatsByCompetitionKeys()
		if stats == nil {
			stats = make(map[string]*AverageGoalsStats)
		}

		return toJSONResult(stats)
	}

	handlers["get_club_players_summary"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		summaries := analyzer.GetClubPlayersSummary()
		if summaries == nil {
			summaries = []ClubPlayersSummary{}
		}

		return toJSONResult(map[string]interface{}{
			"summaries": summaries,
			"count":     len(summaries),
		})
	}

	handlers["get_data_summary"] = func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		summary := map[string]interface{}{
			"datasets": map[string]interface{}{
				"brasileirao_matches":      len(store.GetBrasilieiraoMatches()),
				"copa_do_brasil_matches":   len(store.GetCopaDoBrasilMatches()),
				"libertadores_matches":     len(store.GetLibertadoresMatches()),
				"br_football_matches":      len(store.GetBRFootballMatches()),
				"novo_campeonato_matches":  len(store.GetNovoCampeonatoMatches()),
				"fifa_players":             len(store.GetFIFAPlayers()),
			},
		}

		return toJSONResult(summary)
	}

	return handlers
}

// BuildMCPServer creates a configured MCP server with all tools registered
func BuildMCPServer(analyzer *QueryAnalyzer, store *DataStore) *server.MCPServer {
	mcpServer := server.NewMCPServer(
		"brazilian-soccer-mcp",
		"1.0.0",
		server.WithToolCapabilities(true),
	)

	tools := BuildMCPTools(analyzer, store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	for _, tool := range tools {
		handler := handlers[tool.Name]
		mcpServer.AddTool(tool, handler)
	}

	return mcpServer
}
