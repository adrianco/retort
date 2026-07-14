package server

import (
	"context"
	"fmt"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/pkg/data"
	"brazilian-soccer-mcp/pkg/loader"
	"brazilian-soccer-mcp/pkg/query"
)

// MCPServer wraps the MCP server with all the tools and resources.
type MCPServer struct {
	mcpServer      *server.MCPServer
	queryHandler   *query.QueryHandler
	dataManager    *loader.Manager
	resourcePrefix string
}

// New creates a new MCP server instance.
func New(dataManager *loader.Manager, resourcePrefix string) *MCPServer {
	qh := query.NewQueryHandler(dataManager)

	s := &MCPServer{
		queryHandler:   qh,
		dataManager:    dataManager,
		resourcePrefix: resourcePrefix,
	}

	mcpSrv := server.NewMCPServer(
		"Brazilian Soccer MCP",
		"1.0.0",
	)

	tools := s.listTools()
	for _, t := range tools {
		mcpSrv.AddTool(t, s.toolHandler(t.Name))
	}

	resources := s.listResources()
	for _, r := range resources {
		mcpSrv.AddResource(r, s.resourceHandler(r.URI))
	}

	s.mcpServer = mcpSrv
	return s
}

func (s *MCPServer) Server() *server.MCPServer {
	return s.mcpServer
}

func (s *MCPServer) listTools() []mcp.Tool {
	return []mcp.Tool{
		mcp.NewTool("search_matches",
			mcp.WithDescription("Search for soccer matches by team name, competition, season, or date range"),
			mcp.WithString("team_name", mcp.Required(), mcp.Description("Team name to search for")),
			mcp.WithString("competition", mcp.Description("Competition: brasileirao, copa do brasil, libertadores")),
			mcp.WithString("season", mcp.Description("Season year (e.g., 2023)")),
			mcp.WithString("date_start", mcp.Description("Start date YYYY-MM-DD")),
			mcp.WithString("date_end", mcp.Description("End date YYYY-MM-DD")),
		),
		mcp.NewTool("search_matches_exact",
			mcp.WithDescription("Search for exact matches between two specific teams"),
			mcp.WithString("team1", mcp.Required(), mcp.Description("First team name")),
			mcp.WithString("team2", mcp.Required(), mcp.Description("Second team name")),
		),
		mcp.NewTool("get_team_stats",
			mcp.WithDescription("Get aggregated statistics for a team: wins, losses, draws, goals, win rate"),
			mcp.WithString("team_name", mcp.Required(), mcp.Description("Team name")),
			mcp.WithString("competition", mcp.Description("Competition filter")),
			mcp.WithString("season", mcp.Description("Season year")),
		),
		mcp.NewTool("get_head_to_head",
			mcp.WithDescription("Get head-to-head statistics between two teams with match history"),
			mcp.WithString("team1", mcp.Required(), mcp.Description("First team name")),
			mcp.WithString("team2", mcp.Required(), mcp.Description("Second team name")),
		),
		mcp.NewTool("get_competition_standings",
			mcp.WithDescription("Get competition standings calculated from match results"),
			mcp.WithString("competition", mcp.Required(), mcp.Description("Competition: brasileirao, copa do brasil, libertadores")),
			mcp.WithString("season", mcp.Description("Season year")),
		),
		mcp.NewTool("search_players",
			mcp.WithDescription("Search for players by name, nationality, club, position, or rating"),
			mcp.WithString("name", mcp.Description("Player name (fuzzy match)")),
			mcp.WithString("nationality", mcp.Description("Nationality filter")),
			mcp.WithString("club", mcp.Description("Club name filter")),
			mcp.WithString("position", mcp.Description("Position filter")),
			mcp.WithString("min_overall", mcp.Description("Minimum FIFA overall rating")),
		),
		mcp.NewTool("get_biggest_wins",
			mcp.WithDescription("Get biggest goal victories in dataset"),
			mcp.WithString("competition", mcp.Description("Competition filter")),
			mcp.WithString("limit", mcp.Description("Number of results (default 10)")),
		),
		mcp.NewTool("get_statistics",
			mcp.WithDescription("Get aggregate statistics: avg goals, home/away win rates"),
			mcp.WithString("competition", mcp.Description("Competition filter")),
		),
		mcp.NewTool("get_all_teams",
			mcp.WithDescription("Get all unique teams found in datasets"),
		),
		mcp.NewTool("get_players_by_club",
			mcp.WithDescription("Get all players at a specific club, sorted by rating"),
			mcp.WithString("club_name", mcp.Required(), mcp.Description("Club name to search for")),
		),
		mcp.NewTool("get_brazilian_players",
			mcp.WithDescription("Get top-rated Brazilian players in dataset"),
			mcp.WithString("top_n", mcp.Description("Number of top players (default 10)")),
		),
		mcp.NewTool("data_sources",
			mcp.WithDescription("Get info about loaded datasets and record counts"),
		),
	}
}

func (s *MCPServer) listResources() []mcp.Resource {
	return []mcp.Resource{
		mcp.NewResource(s.resourcePrefix+"/data-sources", "Data Sources",
			mcp.WithResourceDescription("Information about loaded datasets"),
			mcp.WithMIMEType("text/plain"),
		),
		mcp.NewResource(s.resourcePrefix+"/teams", "All Teams",
			mcp.WithResourceDescription("List of all unique teams in datasets"),
			mcp.WithMIMEType("text/plain"),
		),
	}
}

func (s *MCPServer) toolHandler(toolName string) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.Params.Arguments
		if args == nil {
			args = make(map[string]any)
		}

		switch toolName {
		case "search_matches":
			return s.handleSearchMatches(args)
		case "search_matches_exact":
			return s.handleSearchMatchesExact(args)
		case "get_team_stats":
			return s.handleGetTeamStats(args)
		case "get_head_to_head":
			return s.handleGetHeadToHead(args)
		case "get_competition_standings":
			return s.handleGetCompetitionStandings(args)
		case "search_players":
			return s.handleSearchPlayers(args)
		case "get_biggest_wins":
			return s.handleGetBiggestWins(args)
		case "get_statistics":
			return s.handleGetStatistics(args)
		case "get_all_teams":
			return s.handleGetAllTeams()
		case "get_players_by_club":
			return s.handleGetPlayersByClub(args)
		case "get_brazilian_players":
			return s.handleGetBrazilianPlayers(args)
		case "data_sources":
			return s.handleDataSources()
		default:
			return mcp.NewToolResultError(fmt.Sprintf("Unknown tool: %s", toolName)), nil
		}
	}
}

func (s *MCPServer) resourceHandler(uri string) server.ResourceHandlerFunc {
	return func(ctx context.Context, req mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
		switch uri {
		case s.resourcePrefix + "/data-sources":
			info := s.dataManager.DataSourceInfo()
			var lines []string
			total := 0
			for name, count := range info {
				lines = append(lines, fmt.Sprintf("  %s: %d records", name, count))
				total += count
			}
			lines = append(lines, fmt.Sprintf("  TOTAL: %d records", total))
			content := strings.Join(lines, "\n")
			return []mcp.TextResourceContents{
				mcp.TextResourceContents{
					URI:      uri,
					MIMEType: "text/plain",
					Text:     &content,
				},
			}, nil
		case s.resourcePrefix + "/teams":
			teams := s.queryHandler.GetAllTeams()
			names := make([]string, 0, len(teams))
			for _, name := range teams {
				names = append(names, name)
			}
			content := strings.Join(names, "\n")
			return []mcp.TextResourceContents{
				mcp.TextResourceContents{
					URI:      uri,
					MIMEType: "text/plain",
					Text:     &content,
				},
			}, nil
		default:
			return nil, fmt.Errorf("unknown resource: %s", uri)
		}
	}
}

// Handler implementations

func (s *MCPServer) handleSearchMatches(args map[string]any) (*mcp.CallToolResult, error) {
	teamName := getString(args, "team_name", "")
	competition := getString(args, "competition", "")
	season := getString(args, "season", "")
	dateStart := getString(args, "date_start", "")
	dateEnd := getString(args, "date_end", "")

	if teamName == "" {
		return mcp.NewToolResultError("team_name is required"), nil
	}

	matches := s.queryHandler.SearchMatches(teamName, competition, season, dateStart, dateEnd)
	if len(matches) == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No matches found for team '%s'", teamName)), nil
	}
	return mcp.NewToolResultText(formatMatchResults(teamName, matches)), nil
}

func (s *MCPServer) handleSearchMatchesExact(args map[string]any) (*mcp.CallToolResult, error) {
	team1 := getString(args, "team1", "")
	team2 := getString(args, "team2", "")
	if team1 == "" || team2 == "" {
		return mcp.NewToolResultError("team1 and team2 are required"), nil
	}
	matches := s.queryHandler.SearchMatchesExact(team1, team2)
	if len(matches) == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No matches found between '%s' and '%s'", team1, team2)), nil
	}
	return mcp.NewToolResultText(formatMatchResults(team1, matches)), nil
}

func (s *MCPServer) handleGetTeamStats(args map[string]any) (*mcp.CallToolResult, error) {
	teamName := getString(args, "team_name", "")
	competition := getString(args, "competition", "")
	season := getString(args, "season", "")
	if teamName == "" {
		return mcp.NewToolResultError("team_name is required"), nil
	}
	stats := s.queryHandler.GetTeamStats(teamName, competition, season)
	if stats.Matches == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No matches found for team '%s'", teamName)), nil
	}
	return mcp.NewToolResultText(formatTeamStats(teamName, stats)), nil
}

func (s *MCPServer) handleGetHeadToHead(args map[string]any) (*mcp.CallToolResult, error) {
	team1 := getString(args, "team1", "")
	team2 := getString(args, "team2", "")
	if team1 == "" || team2 == "" {
		return mcp.NewToolResultError("team1 and team2 are required"), nil
	}
	h2h := s.queryHandler.GetHeadToHead(team1, team2)
	if h2h.Team1Wins == 0 && h2h.Team2Wins == 0 && h2h.Draws == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No head-to-head matches found between '%s' and '%s'", team1, team2)), nil
	}
	return mcp.NewToolResultText(formatH2H(h2h)), nil
}

func (s *MCPServer) handleGetCompetitionStandings(args map[string]any) (*mcp.CallToolResult, error) {
	competition := getString(args, "competition", "")
	season := getString(args, "season", "")
	if competition == "" {
		return mcp.NewToolResultError("competition is required"), nil
	}
	standings := s.queryHandler.GetCompetitionStandings(competition, season)
	if len(standings) == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No standings found for competition '%s'", competition)), nil
	}
	return mcp.NewToolResultText(formatStandings(competition, standings)), nil
}

func (s *MCPServer) handleSearchPlayers(args map[string]any) (*mcp.CallToolResult, error) {
	name := getString(args, "name", "")
	nationality := getString(args, "nationality", "")
	club := getString(args, "club", "")
	position := getString(args, "position", "")
	minOverall := parseInt(args, "min_overall", 0)

	players := s.queryHandler.SearchPlayers(name, nationality, club, position, minOverall)
	if len(players) == 0 {
		return mcp.NewToolResultText("No players found matching the criteria"), nil
	}
	return mcp.NewToolResultText(formatPlayers(players)), nil
}

func (s *MCPServer) handleGetBiggestWins(args map[string]any) (*mcp.CallToolResult, error) {
	competition := getString(args, "competition", "")
	limit := parseInt(args, "limit", 10)
	if limit <= 0 {
		limit = 10
	}
	wins := s.queryHandler.GetBiggestWins(competition, limit)
	if len(wins) == 0 {
		return mcp.NewToolResultText("No matches found"), nil
	}
	return mcp.NewToolResultText(formatBiggestWins(wins)), nil
}

func (s *MCPServer) handleGetStatistics(args map[string]any) (*mcp.CallToolResult, error) {
	competition := getString(args, "competition", "")
	stats := s.queryHandler.GetStatistics(competition)
	if stats.TotalMatches == 0 {
		return mcp.NewToolResultText("No matches found"), nil
	}
	return mcp.NewToolResultText(formatStatistics(stats, competition)), nil
}

func (s *MCPServer) handleGetAllTeams() (*mcp.CallToolResult, error) {
	teams := s.queryHandler.GetAllTeams()
	return mcp.NewToolResultText(formatTeamList(teams)), nil
}

func (s *MCPServer) handleGetPlayersByClub(args map[string]any) (*mcp.CallToolResult, error) {
	clubName := getString(args, "club_name", "")
	if clubName == "" {
		return mcp.NewToolResultError("club_name is required"), nil
	}
	players := s.queryHandler.GetPlayersByClub(clubName)
	if len(players) == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No players found at club '%s'", clubName)), nil
	}
	return mcp.NewToolResultText(formatPlayers(players)), nil
}

func (s *MCPServer) handleGetBrazilianPlayers(args map[string]any) (*mcp.CallToolResult, error) {
	topN := parseInt(args, "top_n", 10)
	players := s.queryHandler.GetBrazilianPlayers(topN)
	if len(players) == 0 {
		return mcp.NewToolResultText("No Brazilian players found"), nil
	}
	return mcp.NewToolResultText(formatPlayers(players)), nil
}

func (s *MCPServer) handleDataSources() (*mcp.CallToolResult, error) {
	info := s.dataManager.DataSourceInfo()
	var lines []string
	total := 0
	for name, count := range info {
		lines = append(lines, fmt.Sprintf("  %s: %d records", name, count))
		total += count
	}
	lines = append(lines, fmt.Sprintf("  TOTAL: %d records across all sources", total))
	return mcp.NewToolResultText(strings.Join(lines, "\n")), nil
}

// Helpers

func formatMatchResults(teamName string, matches []data.Match) string {
	if len(matches) == 0 {
		return fmt.Sprintf("No matches found for '%s'", teamName)
	}
	result := fmt.Sprintf("Found %d matches for '%s':\n\n", len(matches), teamName)
	sources := make(map[string][]data.Match)
	for _, m := range matches {
		sources[m.Source] = append(sources[m.Source], m)
	}
	for source, srcMatches := range sources {
		result += fmt.Sprintf("--- %s (%d matches) ---\n", source, len(srcMatches))
		for _, m := range srcMatches {
			line := fmt.Sprintf("  %s: %s %d-%d %s", m.Date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam)
			if m.Source == "brasileirao" || m.Source == "novo_campeonato" {
				if m.Round > 0 {
					line += fmt.Sprintf(" (Round %d)", m.Round)
				}
			}
			if m.Source == "libertadores" && m.Stage != "" {
				line += fmt.Sprintf(" (%s)", m.Stage)
			}
			if m.Source == "br_football" && m.Tournament != "" {
				line += fmt.Sprintf(" (%s)", m.Tournament)
			}
			result += line + "\n"
		}
		result += "\n"
	}
	return result
}

func formatTeamStats(teamName string, stats data.TeamStats) string {
	return fmt.Sprintf("Team Statistics: %s\n  Matches: %d\n  Wins: %d, Draws: %d, Losses: %d\n  Goals For: %d, Goals Against: %d\n  Goal Difference: %d\n  Win Rate: %.1f%%",
		teamName, stats.Matches, stats.Wins, stats.Draws, stats.Losses,
		stats.GoalsFor, stats.GoalsAgainst, stats.GoalDiffer, stats.WinRate)
}

func formatH2H(h2h data.H2HRecord) string {
	result := fmt.Sprintf("Head-to-Head: %s vs %s\n  %s wins: %d, Draws: %d, %s wins: %d\n  Total matches in dataset: %d\n\n",
		h2h.Team1Name, h2h.Team2Name, h2h.Team1Name, h2h.Team1Wins, h2h.Draws, h2h.Team2Name, h2h.Team2Wins, len(h2h.Matches))
	if len(h2h.Matches) <= 20 {
		result += "Match history:\n"
		for _, m := range h2h.Matches {
			line := fmt.Sprintf("  %s: %s %d-%d %s", m.Date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam)
			if m.Round > 0 {
				line += fmt.Sprintf(" (R%d)", m.Round)
			}
			result += line + "\n"
		}
	} else {
		result += fmt.Sprintf("Showing first 10 of %d matches:\n", len(h2h.Matches))
		for i := 0; i < 10 && i < len(h2h.Matches); i++ {
			m := h2h.Matches[i]
			result += fmt.Sprintf("  %s: %s %d-%d %s\n", m.Date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam)
		}
		result += fmt.Sprintf("  ... and %d more\n", len(h2h.Matches)-10)
	}
	return result
}

func formatStandings(competition string, standings []data.CompetitionStanding) string {
	result := fmt.Sprintf("%s Standings:\n", capitalize(competition))
	if len(standings) > 20 {
		standings = standings[:20]
	}
	for _, s := range standings {
		champ := ""
		if s.Position == 1 {
			champ = " [CHAMPION]"
		}
		result += fmt.Sprintf("%2d. %-30s %3d pts (%dW-%dD-%dL, GD=%+d)%s\n",
			s.Position, s.TeamName, s.Points, s.Wins, s.Draws, s.Losses, s.GoalDiff, champ)
	}
	return result
}

func formatPlayers(players []data.Player) string {
	result := fmt.Sprintf("Found %d players:\n\n", len(players))
	for i, p := range players {
		result += fmt.Sprintf("  %d. %s - Overall: %d, Potential: %d, Position: %s, Club: %s, Age: %d, Nationality: %s\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, p.Club, p.Age, p.Nationality)
	}
	return result
}

func formatBiggestWins(matches []data.Match) string {
	result := "Biggest Goalscoring Victories:\n"
	for i, m := range matches {
		diff := m.HomeGoals - m.AwayGoals
		if diff < 0 {
			diff = -diff
		}
		line := fmt.Sprintf("  %d. %s: %s %d-%d %s (%s)",
			i+1, m.Date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Source)
		if m.Tournament != "" {
			line += " [" + m.Tournament + "]"
		}
		line += fmt.Sprintf(" (margin: %d)", diff)
		result += line + "\n"
	}
	return result
}

func formatStatistics(stats data.StatResult, competition string) string {
	result := fmt.Sprintf("%s Statistics:\n", capitalize(competition))
	result += fmt.Sprintf("  Total Matches: %d\n", stats.TotalMatches)
	result += fmt.Sprintf("  Average Goals Per Match: %.2f\n", stats.AvgGoalsPerMatch)
	result += fmt.Sprintf("  Home Win Rate: %.1f%%\n", stats.HomeWinRate)
	result += fmt.Sprintf("  Away Win Rate: %.1f%%\n", stats.AwayWinRate)
	result += fmt.Sprintf("  Draw Rate: %.1f%%\n", stats.DrawRate)
	return result
}

func formatTeamList(teams map[string]string) string {
	result := fmt.Sprintf("Found %d unique teams:\n\n", len(teams))
	for norm, display := range teams {
		result += fmt.Sprintf("  %s (display: %s)\n", norm, display)
	}
	return result
}

func getString(m map[string]any, key, defaultVal string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok && s != "" {
			return s
		}
	}
	return defaultVal
}

func parseInt(m map[string]any, key string, defaultVal int) int {
	if v, ok := m[key]; ok {
		switch val := v.(type) {
		case int:
			return val
		case float64:
			return int(val)
		case string:
			n := 0
			for _, c := range val {
				if c >= '0' && c <= '9' {
					n = n*10 + int(c-'0')
				}
			}
			if n > 0 {
				return n
			}
		}
	}
	return defaultVal
}

func capitalize(s string) string {
	if s == "" {
		return ""
	}
	return strings.ToUpper(s[:1]) + s[1:]
}

func strPtr(s string) *string {
	return &s
}
