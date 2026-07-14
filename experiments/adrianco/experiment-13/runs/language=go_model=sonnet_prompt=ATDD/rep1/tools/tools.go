package tools

import (
	"context"
	"fmt"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"brazilian-soccer-mcp/soccer"
)

// getString extracts a string argument from the tool args map.
func getString(args map[string]interface{}, key string) string {
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

// getInt extracts an integer argument (handles float64 from JSON unmarshalling).
func getInt(args map[string]interface{}, key string) int {
	if v, ok := args[key]; ok {
		switch n := v.(type) {
		case float64:
			return int(n)
		case int:
			return n
		case int64:
			return int(n)
		}
	}
	return 0
}

// textResult wraps a string as a successful MCP tool result.
func textResult(text string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		Content: []mcp.Content{mcp.TextContent{Type: "text", Text: text}},
	}
}

// -------- find_matches --------

// NewFindMatchesHandler returns an MCP handler for finding matches.
func NewFindMatchesHandler(store *soccer.Store) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		f := soccer.MatchFilter{
			Team:        getString(args, "team"),
			Team1:       getString(args, "team1"),
			Team2:       getString(args, "team2"),
			HomeTeam:    getString(args, "home_team"),
			AwayTeam:    getString(args, "away_team"),
			Season:      getInt(args, "season"),
			Competition: getString(args, "competition"),
			Limit:       getInt(args, "limit"),
		}
		matches := store.FindMatches(f)
		if len(matches) == 0 {
			return textResult("No matches found."), nil
		}
		var sb strings.Builder
		for _, m := range matches {
			sb.WriteString(formatMatch(m))
			sb.WriteString("\n")
		}
		return textResult(strings.TrimSpace(sb.String())), nil
	}
}

func formatMatch(m soccer.Match) string {
	comp := competitionLabel(m.Competition)
	season := ""
	if m.Season != 0 {
		season = fmt.Sprintf(" | %d", m.Season)
	}
	stage := ""
	if m.Stage != "" {
		stage = " | " + m.Stage
	}
	return fmt.Sprintf("%s | %s vs %s | %d-%d | %s%s%s",
		m.Date, m.HomeTeam, m.AwayTeam, m.HomeGoals, m.AwayGoals, comp, stage, season)
}

func competitionLabel(c string) string {
	switch strings.ToLower(c) {
	case "brasileirao":
		return "Brasileirao"
	case "copa_brasil":
		return "Copa do Brasil"
	case "libertadores":
		return "Libertadores"
	default:
		return c
	}
}

// -------- get_team_stats --------

// NewGetTeamStatsHandler returns an MCP handler for team statistics.
func NewGetTeamStatsHandler(store *soccer.Store) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		team := getString(args, "team")
		if team == "" {
			return textResult("Error: team parameter is required"), nil
		}
		competition := getString(args, "competition")
		season := getInt(args, "season")

		stats := store.GetTeamStats(team, competition, season)

		seasonStr := ""
		if season != 0 {
			seasonStr = fmt.Sprintf(" (%d)", season)
		}
		compStr := ""
		if competition != "" {
			compStr = fmt.Sprintf(" in %s", competitionLabel(competition))
		}

		result := fmt.Sprintf("%s%s%s\nMatches: %d | Wins: %d | Draws: %d | Losses: %d\nGoals For: %d | Goals Against: %d | Goal Diff: %d",
			stats.Team, compStr, seasonStr,
			stats.Matches, stats.Wins, stats.Draws, stats.Losses,
			stats.GoalsFor, stats.GoalsAgainst, stats.GoalsFor-stats.GoalsAgainst)
		return textResult(result), nil
	}
}

// -------- find_players --------

// NewFindPlayersHandler returns an MCP handler for finding players.
func NewFindPlayersHandler(store *soccer.Store) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		f := soccer.PlayerFilter{
			Name:        getString(args, "name"),
			Nationality: getString(args, "nationality"),
			Club:        getString(args, "club"),
			Position:    getString(args, "position"),
			MinOverall:  getInt(args, "min_overall"),
			Limit:       getInt(args, "limit"),
		}
		players := store.FindPlayers(f)
		if len(players) == 0 {
			msg := "No players found"
			if f.Club != "" {
				msg += " for club: " + f.Club
			}
			if f.Nationality != "" {
				msg += " with nationality: " + f.Nationality
			}
			if f.Position != "" {
				msg += " at position: " + f.Position
			}
			return textResult(msg + "."), nil
		}
		var sb strings.Builder
		for _, p := range players {
			sb.WriteString(formatPlayer(p))
			sb.WriteString("\n")
		}
		return textResult(strings.TrimSpace(sb.String())), nil
	}
}

func formatPlayer(p soccer.Player) string {
	return fmt.Sprintf("%s (%s, %s) - Overall: %d / Potential: %d, Age: %d, Nationality: %s",
		p.Name, p.Club, p.Position, p.Overall, p.Potential, p.Age, p.Nationality)
}

// -------- get_standings --------

// NewGetStandingsHandler returns an MCP handler for league standings.
func NewGetStandingsHandler(store *soccer.Store) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		season := getInt(args, "season")
		competition := getString(args, "competition")
		if competition == "" {
			competition = "brasileirao"
		}

		standings := store.GetStandings(season, competition)
		if len(standings) == 0 {
			return textResult("No standings data found."), nil
		}

		seasonStr := ""
		if season != 0 {
			seasonStr = fmt.Sprintf(" %d", season)
		}
		var sb strings.Builder
		sb.WriteString(fmt.Sprintf("%s%s Standings\n", competitionLabel(competition), seasonStr))
		sb.WriteString(fmt.Sprintf("%-4s %-25s %3s %3s %3s %3s %3s %3s %3s %3s\n",
			"Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"))
		sb.WriteString(strings.Repeat("-", 65) + "\n")
		for _, e := range standings {
			sb.WriteString(fmt.Sprintf("%-4d %-25s %3d %3d %3d %3d %3d %3d %3d %3d\n",
				e.Position, truncate(e.Team, 25),
				e.Played, e.Won, e.Drawn, e.Lost,
				e.GoalsFor, e.GoalsAgainst, e.GoalDiff, e.Points))
		}
		return textResult(strings.TrimSpace(sb.String())), nil
	}
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}

// -------- get_head_to_head --------

// NewGetHeadToHeadHandler returns an MCP handler for head-to-head stats.
func NewGetHeadToHeadHandler(store *soccer.Store) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		team1 := getString(args, "team1")
		team2 := getString(args, "team2")
		if team1 == "" || team2 == "" {
			return textResult("Error: team1 and team2 parameters are required"), nil
		}
		competition := getString(args, "competition")

		h2h := store.GetHeadToHead(team1, team2, competition)

		var sb strings.Builder
		sb.WriteString(fmt.Sprintf("Head-to-Head: %s vs %s\n", h2h.Team1, h2h.Team2))
		sb.WriteString(fmt.Sprintf("Total matches: %d\n", len(h2h.Matches)))
		sb.WriteString(fmt.Sprintf("%s wins: %d | Draws: %d | %s wins: %d\n",
			h2h.Team1, h2h.Team1Wins, h2h.Draws, h2h.Team2, h2h.Team2Wins))
		sb.WriteString(fmt.Sprintf("Goals: %s %d - %d %s\n",
			h2h.Team1, h2h.Team1Goals, h2h.Team2Goals, h2h.Team2))

		// Show last few matches
		matches := h2h.Matches
		if len(matches) > 10 {
			matches = matches[len(matches)-10:]
		}
		if len(matches) > 0 {
			sb.WriteString("\nRecent matches:\n")
			for _, m := range matches {
				sb.WriteString(formatMatch(m))
				sb.WriteString("\n")
			}
		}
		return textResult(strings.TrimSpace(sb.String())), nil
	}
}

// -------- get_statistics --------

// NewGetStatisticsHandler returns an MCP handler for general statistics.
func NewGetStatisticsHandler(store *soccer.Store) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		statType := getString(args, "stat_type")
		competition := getString(args, "competition")
		season := getInt(args, "season")
		limit := getInt(args, "limit")

		switch strings.ToLower(statType) {
		case "biggest_wins":
			return handleBiggestWins(store, competition, season, limit)
		case "goals_average":
			return handleGoalsAverage(store, competition, season)
		case "home_away_record":
			return handleHomeAwayRecord(store, competition, season)
		default:
			return handleGoalsAverage(store, competition, season)
		}
	}
}

func handleBiggestWins(store *soccer.Store, competition string, season, limit int) (*mcp.CallToolResult, error) {
	matches := store.BiggestWins(competition, season, limit)
	if len(matches) == 0 {
		return textResult("No matches found."), nil
	}
	var sb strings.Builder
	sb.WriteString("Biggest Wins (by goal difference):\n")
	for i, m := range matches {
		diff := m.HomeGoals - m.AwayGoals
		if diff < 0 {
			diff = -diff
		}
		sb.WriteString(fmt.Sprintf("%d. %s | %s %d-%d %s | Diff: %d | %s %d\n",
			i+1, m.Date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, diff,
			competitionLabel(m.Competition), m.Season))
	}
	return textResult(strings.TrimSpace(sb.String())), nil
}

func handleGoalsAverage(store *soccer.Store, competition string, season int) (*mcp.CallToolResult, error) {
	avg, count := store.GoalsAverage(competition, season)

	compStr := "all competitions"
	if competition != "" {
		compStr = competitionLabel(competition)
	}
	seasonStr := "all seasons"
	if season != 0 {
		seasonStr = fmt.Sprintf("%d", season)
	}
	result := fmt.Sprintf("Goals Average Statistics\nCompetition: %s | Season: %s\nTotal matches: %d\nAverage goals per match: %.2f",
		compStr, seasonStr, count, avg)
	return textResult(result), nil
}

func handleHomeAwayRecord(store *soccer.Store, competition string, season int) (*mcp.CallToolResult, error) {
	homeWins, awayWins, draws, total := store.HomeAwayRecord(competition, season)

	compStr := "all competitions"
	if competition != "" {
		compStr = competitionLabel(competition)
	}
	seasonStr := "all seasons"
	if season != 0 {
		seasonStr = fmt.Sprintf("%d", season)
	}

	homePct := 0.0
	awayPct := 0.0
	drawPct := 0.0
	if total > 0 {
		homePct = float64(homeWins) / float64(total) * 100
		awayPct = float64(awayWins) / float64(total) * 100
		drawPct = float64(draws) / float64(total) * 100
	}

	result := fmt.Sprintf("Home/Away Record\nCompetition: %s | Season: %s\nTotal matches: %d\nHome wins: %d (%.1f%%) | Away wins: %d (%.1f%%) | Draws: %d (%.1f%%)",
		compStr, seasonStr, total, homeWins, homePct, awayWins, awayPct, draws, drawPct)
	return textResult(result), nil
}

// RegisterTools registers all MCP tools on the server.
func RegisterTools(s *server.MCPServer, store *soccer.Store) {
	s.AddTool(mcp.NewTool("find_matches",
		mcp.WithDescription("Find soccer matches with optional filters"),
		mcp.WithString("team", mcp.Description("Team name to search for (home or away)")),
		mcp.WithString("team1", mcp.Description("First team for head-to-head search")),
		mcp.WithString("team2", mcp.Description("Second team for head-to-head search")),
		mcp.WithString("home_team", mcp.Description("Specific home team")),
		mcp.WithString("away_team", mcp.Description("Specific away team")),
		mcp.WithNumber("season", mcp.Description("Season year (e.g. 2019)")),
		mcp.WithString("competition", mcp.Description("Competition: brasileirao, copa_brasil, libertadores, other")),
		mcp.WithNumber("limit", mcp.Description("Maximum results (default 20)")),
	), NewFindMatchesHandler(store))

	s.AddTool(mcp.NewTool("get_team_stats",
		mcp.WithDescription("Get aggregated statistics for a team"),
		mcp.WithString("team", mcp.Required(), mcp.Description("Team name")),
		mcp.WithNumber("season", mcp.Description("Season year (0 = all seasons)")),
		mcp.WithString("competition", mcp.Description("Competition filter")),
	), NewGetTeamStatsHandler(store))

	s.AddTool(mcp.NewTool("find_players",
		mcp.WithDescription("Find players from the FIFA dataset"),
		mcp.WithString("name", mcp.Description("Player name (partial match)")),
		mcp.WithString("nationality", mcp.Description("Nationality (exact match, e.g. Brazil)")),
		mcp.WithString("club", mcp.Description("Club name (partial match)")),
		mcp.WithString("position", mcp.Description("Position (exact, e.g. ST, CAM, GK)")),
		mcp.WithNumber("min_overall", mcp.Description("Minimum overall rating")),
		mcp.WithNumber("limit", mcp.Description("Maximum results (default 20)")),
	), NewFindPlayersHandler(store))

	s.AddTool(mcp.NewTool("get_standings",
		mcp.WithDescription("Get league standings for a season"),
		mcp.WithNumber("season", mcp.Required(), mcp.Description("Season year")),
		mcp.WithString("competition", mcp.Description("Competition (default: brasileirao)")),
	), NewGetStandingsHandler(store))

	s.AddTool(mcp.NewTool("get_head_to_head",
		mcp.WithDescription("Get head-to-head statistics between two teams"),
		mcp.WithString("team1", mcp.Required(), mcp.Description("First team")),
		mcp.WithString("team2", mcp.Required(), mcp.Description("Second team")),
		mcp.WithString("competition", mcp.Description("Competition filter")),
	), NewGetHeadToHeadHandler(store))

	s.AddTool(mcp.NewTool("get_statistics",
		mcp.WithDescription("Get various statistics"),
		mcp.WithString("stat_type", mcp.Description("Type: biggest_wins, goals_average, home_away_record")),
		mcp.WithString("competition", mcp.Description("Competition filter")),
		mcp.WithNumber("season", mcp.Description("Season filter")),
		mcp.WithNumber("limit", mcp.Description("Result limit")),
	), NewGetStatisticsHandler(store))
}
