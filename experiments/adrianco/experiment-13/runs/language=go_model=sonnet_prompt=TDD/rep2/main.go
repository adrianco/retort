package main

import (
	"fmt"
	"log"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

const dataPath = "data/kaggle"

func main() {
	log.SetOutput(os.Stderr)
	log.Println("Loading Brazilian soccer data...")

	db := &Database{}
	var err error

	db.Brasileirao, err = LoadBrasileirao(dataPath + "/Brasileirao_Matches.csv")
	if err != nil {
		log.Printf("Warning: could not load Brasileirao: %v", err)
	} else {
		log.Printf("Loaded %d Brasileirao matches", len(db.Brasileirao))
	}

	db.Copa, err = LoadCopa(dataPath + "/Brazilian_Cup_Matches.csv")
	if err != nil {
		log.Printf("Warning: could not load Copa: %v", err)
	} else {
		log.Printf("Loaded %d Copa matches", len(db.Copa))
	}

	db.Libertadores, err = LoadLibertadores(dataPath + "/Libertadores_Matches.csv")
	if err != nil {
		log.Printf("Warning: could not load Libertadores: %v", err)
	} else {
		log.Printf("Loaded %d Libertadores matches", len(db.Libertadores))
	}

	db.BRFootball, err = LoadBRFootball(dataPath + "/BR-Football-Dataset.csv")
	if err != nil {
		log.Printf("Warning: could not load BR-Football: %v", err)
	} else {
		log.Printf("Loaded %d BR-Football matches", len(db.BRFootball))
	}

	db.Historico, err = LoadHistorico(dataPath + "/novo_campeonato_brasileiro.csv")
	if err != nil {
		log.Printf("Warning: could not load Historico: %v", err)
	} else {
		log.Printf("Loaded %d Historico matches", len(db.Historico))
	}

	db.Players, err = LoadFIFA(dataPath + "/fifa_data.csv")
	if err != nil {
		log.Printf("Warning: could not load FIFA players: %v", err)
	} else {
		log.Printf("Loaded %d FIFA players", len(db.Players))
	}

	// Create MCP server
	s := server.NewMCPServer("Brazilian Soccer MCP", "1.0.0",
		server.WithToolCapabilities(true),
	)

	// Tool: search_matches
	searchMatchesTool := mcp.NewTool("search_matches",
		mcp.WithDescription("Search for soccer matches across Brazilian competitions (Brasileirao, Copa do Brasil, Libertadores). Filter by team, competition, season, date range."),
		mcp.WithString("team", mcp.Description("Team name to search (searches both home and away). Partial, case-insensitive match. E.g. 'Palmeiras', 'Flamengo'")),
		mcp.WithString("home_team", mcp.Description("Filter by home team name")),
		mcp.WithString("away_team", mcp.Description("Filter by away team name")),
		mcp.WithString("competition", mcp.Description(fmt.Sprintf("Competition filter: '%s', '%s', '%s', '%s', '%s'", CompBrasileirao, CompCopa, CompLibertadores, CompBRFootball, CompHistorico))),
		mcp.WithNumber("season", mcp.Description("Season year (e.g. 2020)")),
		mcp.WithString("date_from", mcp.Description("Start date filter (YYYY-MM-DD)")),
		mcp.WithString("date_to", mcp.Description("End date filter (YYYY-MM-DD)")),
		mcp.WithNumber("limit", mcp.Description("Maximum number of results (default 50)")),
	)
	s.AddTool(searchMatchesTool, HandleSearchMatches(db))

	// Tool: head_to_head
	h2hTool := mcp.NewTool("head_to_head",
		mcp.WithDescription("Get head-to-head statistics between two teams. Returns win/draw/loss record from team1's perspective."),
		mcp.WithString("team1", mcp.Description("First team name"), mcp.Required()),
		mcp.WithString("team2", mcp.Description("Second team name"), mcp.Required()),
		mcp.WithString("competition", mcp.Description("Filter by competition (optional)")),
		mcp.WithNumber("season", mcp.Description("Filter by season year (optional)")),
	)
	s.AddTool(h2hTool, HandleHeadToHead(db))

	// Tool: team_stats
	teamStatsTool := mcp.NewTool("team_stats",
		mcp.WithDescription("Get aggregated statistics for a team: wins, draws, losses, goals scored/conceded, points."),
		mcp.WithString("team", mcp.Description("Team name"), mcp.Required()),
		mcp.WithString("competition", mcp.Description("Filter by competition (optional)")),
		mcp.WithNumber("season", mcp.Description("Filter by season year (optional)")),
	)
	s.AddTool(teamStatsTool, HandleTeamStats(db))

	// Tool: standings
	standingsTool := mcp.NewTool("standings",
		mcp.WithDescription("Get league standings for a competition and season. Returns teams sorted by points."),
		mcp.WithNumber("season", mcp.Description("Season year (e.g. 2023)")),
		mcp.WithString("competition", mcp.Description("Competition name (e.g. 'brasileirao', 'historico')")),
	)
	s.AddTool(standingsTool, HandleStandings(db))

	// Tool: search_players
	searchPlayersTool := mcp.NewTool("search_players",
		mcp.WithDescription("Search FIFA player database for Brazilian soccer players. Filter by name, nationality, club, position, or minimum overall rating."),
		mcp.WithString("name", mcp.Description("Player name (partial match)")),
		mcp.WithString("nationality", mcp.Description("Player nationality (e.g. 'Brazil', 'Argentina')")),
		mcp.WithString("club", mcp.Description("Club name (partial match)")),
		mcp.WithString("position", mcp.Description("Position code (e.g. 'ST', 'CDM', 'GK')")),
		mcp.WithNumber("min_overall", mcp.Description("Minimum overall rating (0-99)")),
		mcp.WithNumber("limit", mcp.Description("Maximum results (default 20)")),
	)
	s.AddTool(searchPlayersTool, HandleSearchPlayers(db))

	// Tool: get_statistics
	getStatsTool := mcp.NewTool("get_statistics",
		mcp.WithDescription("Get aggregate statistics for a competition. Stat types: 'avg_goals' (average goals per match), 'biggest_wins' (largest scorelines), 'best_home_record' (teams with best home record)."),
		mcp.WithString("competition", mcp.Description("Competition name (optional, searches all if empty)")),
		mcp.WithNumber("season", mcp.Description("Season year filter (optional)")),
		mcp.WithString("stat_type", mcp.Description("Type of statistic: 'avg_goals', 'biggest_wins', 'best_home_record'")),
	)
	s.AddTool(getStatsTool, HandleGetStatistics(db))

	log.Println("Starting Brazilian Soccer MCP server on stdio...")
	if err := server.ServeStdio(s); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
