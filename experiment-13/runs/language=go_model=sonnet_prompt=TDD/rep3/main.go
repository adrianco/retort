package main

import (
	"context"
	"log"
	"os"
	"path/filepath"
	"runtime"

	"github.com/mark3labs/mcp-go/mcp"
	mcpserver "github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/store"
	"brazilian-soccer-mcp/tools"
)

func main() {
	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		_, file, _, ok := runtime.Caller(0)
		if ok {
			dataDir = filepath.Join(filepath.Dir(file), "data", "kaggle")
		} else {
			dataDir = filepath.Join("data", "kaggle")
		}
	}

	log.Printf("Loading data from %s", dataDir)
	s, err := store.New(dataDir)
	if err != nil {
		log.Fatalf("Failed to load data: %v", err)
	}
	log.Printf("Loaded %d brasileirao matches, %d players",
		len(s.Brasileirao), len(s.Players))

	h := tools.NewHandlers(s)

	srv := mcpserver.NewMCPServer(
		"Brazilian Soccer MCP",
		"1.0.0",
		mcpserver.WithToolCapabilities(true),
	)

	registerTools(srv, h)

	log.Println("Starting Brazilian Soccer MCP server on stdio...")
	if err := mcpserver.ServeStdio(srv); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}

func registerTools(srv *mcpserver.MCPServer, h *tools.Handlers) {
	srv.AddTool(
		mcp.NewTool("search_matches",
			mcp.WithDescription("Search for Brazilian soccer matches by team, season, or competition"),
			mcp.WithString("team", mcp.Description("Team name (e.g. Flamengo, Palmeiras)")),
			mcp.WithNumber("season", mcp.Description("Season year (e.g. 2022)")),
			mcp.WithString("competition",
				mcp.Description("Competition name filter: Brasileirao, Copa do Brasil, Libertadores")),
		),
		func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			args := map[string]interface{}{}
			if v := req.GetString("team", ""); v != "" {
				args["team"] = v
			}
			if v := req.GetFloat("season", 0); v != 0 {
				args["season"] = v
			}
			if v := req.GetString("competition", ""); v != "" {
				args["competition"] = v
			}
			results, err := h.SearchMatches(ctx, args)
			if err != nil {
				return nil, err
			}
			return mcp.NewToolResultText(results[0].Text), nil
		},
	)

	srv.AddTool(
		mcp.NewTool("head_to_head",
			mcp.WithDescription("Get head-to-head record between two teams"),
			mcp.WithString("team1", mcp.Description("First team name"), mcp.Required()),
			mcp.WithString("team2", mcp.Description("Second team name"), mcp.Required()),
		),
		func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			args := map[string]interface{}{
				"team1": req.GetString("team1", ""),
				"team2": req.GetString("team2", ""),
			}
			results, err := h.HeadToHead(ctx, args)
			if err != nil {
				return nil, err
			}
			return mcp.NewToolResultText(results[0].Text), nil
		},
	)

	srv.AddTool(
		mcp.NewTool("team_stats",
			mcp.WithDescription("Get win/loss/draw statistics for a team in a specific season"),
			mcp.WithString("team", mcp.Description("Team name"), mcp.Required()),
			mcp.WithNumber("season", mcp.Description("Season year (e.g. 2022)"), mcp.Required()),
		),
		func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			args := map[string]interface{}{
				"team":   req.GetString("team", ""),
				"season": req.GetFloat("season", 0),
			}
			results, err := h.TeamStats(ctx, args)
			if err != nil {
				return nil, err
			}
			return mcp.NewToolResultText(results[0].Text), nil
		},
	)

	srv.AddTool(
		mcp.NewTool("search_players",
			mcp.WithDescription("Search FIFA player database by name, nationality, or club"),
			mcp.WithString("name", mcp.Description("Player name (partial match)")),
			mcp.WithString("nationality", mcp.Description("Player nationality (e.g. Brazil)")),
			mcp.WithString("club", mcp.Description("Club name (partial match)")),
		),
		func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			args := map[string]interface{}{}
			if v := req.GetString("name", ""); v != "" {
				args["name"] = v
			}
			if v := req.GetString("nationality", ""); v != "" {
				args["nationality"] = v
			}
			if v := req.GetString("club", ""); v != "" {
				args["club"] = v
			}
			results, err := h.SearchPlayers(ctx, args)
			if err != nil {
				return nil, err
			}
			return mcp.NewToolResultText(results[0].Text), nil
		},
	)

	srv.AddTool(
		mcp.NewTool("league_standings",
			mcp.WithDescription("Get Brasileirão Serie A standings for a season"),
			mcp.WithNumber("season", mcp.Description("Season year (e.g. 2019)"), mcp.Required()),
		),
		func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			args := map[string]interface{}{
				"season": req.GetFloat("season", 0),
			}
			results, err := h.LeagueStandings(ctx, args)
			if err != nil {
				return nil, err
			}
			return mcp.NewToolResultText(results[0].Text), nil
		},
	)

	srv.AddTool(
		mcp.NewTool("biggest_wins",
			mcp.WithDescription("Get the biggest victories (by goal difference) across all competitions"),
			mcp.WithNumber("limit", mcp.Description("Number of results to return (default 10)")),
		),
		func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			args := map[string]interface{}{}
			if v := req.GetFloat("limit", 0); v > 0 {
				args["limit"] = v
			}
			results, err := h.BiggestWins(ctx, args)
			if err != nil {
				return nil, err
			}
			return mcp.NewToolResultText(results[0].Text), nil
		},
	)

	srv.AddTool(
		mcp.NewTool("statistics",
			mcp.WithDescription("Get overall statistics about the Brazilian soccer dataset"),
		),
		func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			results, err := h.Statistics(ctx, map[string]interface{}{})
			if err != nil {
				return nil, err
			}
			return mcp.NewToolResultText(results[0].Text), nil
		},
	)
}
