package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

// Tool describes an MCP tool.
type Tool struct {
	Name        string      `json:"name"`
	Description string      `json:"description"`
	InputSchema interface{} `json:"inputSchema"`
}

// ToolCallParams holds the decoded parameters for a tool/call request.
type ToolCallParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

// ToolResult is what the server returns for a tool call.
type ToolResult struct {
	Content []ContentBlock `json:"content"`
	IsError bool           `json:"isError,omitempty"`
}

// ContentBlock is a single piece of content in a tool result.
type ContentBlock struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

func textResult(text string) *ToolResult {
	return &ToolResult{
		Content: []ContentBlock{{Type: "text", Text: text}},
	}
}

func errorResult(msg string) *ToolResult {
	return &ToolResult{
		Content: []ContentBlock{{Type: "text", Text: "Error: " + msg}},
		IsError: true,
	}
}

// allTools returns all tools exposed by this server.
func allTools() []Tool {
	return []Tool{
		{
			Name:        "search_matches",
			Description: "Search for soccer matches across all datasets. Filter by team, competition, season, or date range. Returns match results with scores.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"team": map[string]interface{}{
						"type":        "string",
						"description": "Team name to search for (partial match, e.g. 'Flamengo', 'Palmeiras'). Matches home or away.",
					},
					"team2": map[string]interface{}{
						"type":        "string",
						"description": "Second team name for head-to-head match search (requires team to be set).",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Competition name filter, e.g. 'Brasileirao', 'Copa do Brasil', 'Libertadores'.",
					},
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Season year, e.g. 2022.",
					},
					"date_from": map[string]interface{}{
						"type":        "string",
						"description": "Start date filter in YYYY-MM-DD format.",
					},
					"date_to": map[string]interface{}{
						"type":        "string",
						"description": "End date filter in YYYY-MM-DD format.",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum number of matches to return (default: 20, max: 100).",
					},
				},
			},
		},
		{
			Name:        "team_statistics",
			Description: "Get win/draw/loss statistics for a team. Optionally filter by competition and/or season.",
			InputSchema: map[string]interface{}{
				"type":     "object",
				"required": []string{"team"},
				"properties": map[string]interface{}{
					"team": map[string]interface{}{
						"type":        "string",
						"description": "Team name (e.g. 'Corinthians', 'Santos').",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Competition filter (e.g. 'Brasileirao', 'Libertadores').",
					},
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Season year filter.",
					},
					"home_away": map[string]interface{}{
						"type":        "string",
						"enum":        []string{"both", "home", "away"},
						"description": "Filter to home matches, away matches, or both (default: both).",
					},
				},
			},
		},
		{
			Name:        "head_to_head",
			Description: "Compare two teams' historical record against each other, showing all matches and aggregate wins/draws/losses.",
			InputSchema: map[string]interface{}{
				"type":     "object",
				"required": []string{"team1", "team2"},
				"properties": map[string]interface{}{
					"team1": map[string]interface{}{
						"type":        "string",
						"description": "First team name.",
					},
					"team2": map[string]interface{}{
						"type":        "string",
						"description": "Second team name.",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Competition filter (optional).",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum matches to show (default: 20).",
					},
				},
			},
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality, club, or position. Returns player ratings and attributes.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"name": map[string]interface{}{
						"type":        "string",
						"description": "Player name search (partial match, e.g. 'Neymar', 'Gabriel').",
					},
					"nationality": map[string]interface{}{
						"type":        "string",
						"description": "Player nationality, e.g. 'Brazil', 'Argentina'.",
					},
					"club": map[string]interface{}{
						"type":        "string",
						"description": "Club name, e.g. 'Flamengo', 'Palmeiras', 'Santos'.",
					},
					"position": map[string]interface{}{
						"type":        "string",
						"description": "Playing position, e.g. 'GK', 'ST', 'LW', 'CDM'.",
					},
					"min_overall": map[string]interface{}{
						"type":        "integer",
						"description": "Minimum FIFA overall rating (0-99).",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum number of players to return (default: 20).",
					},
				},
			},
		},
		{
			Name:        "competition_standings",
			Description: "Calculate competition standings (points table) for a given competition and season based on match results.",
			InputSchema: map[string]interface{}{
				"type":     "object",
				"required": []string{"competition", "season"},
				"properties": map[string]interface{}{
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Competition name, e.g. 'Brasileirao', 'Copa do Brasil', 'Libertadores'.",
					},
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Season year, e.g. 2019.",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum number of teams to show (default: 20).",
					},
				},
			},
		},
		{
			Name:        "match_analysis",
			Description: "Perform statistical analysis: biggest wins, average goals per match, home/away advantage, or top scoring teams.",
			InputSchema: map[string]interface{}{
				"type":     "object",
				"required": []string{"analysis_type"},
				"properties": map[string]interface{}{
					"analysis_type": map[string]interface{}{
						"type":        "string",
						"enum":        []string{"biggest_wins", "average_goals", "home_advantage", "top_scoring_teams", "best_home_record", "best_away_record"},
						"description": "Type of analysis to perform.",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Competition filter (optional).",
					},
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Season filter (optional).",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Number of results to return (default: 10).",
					},
				},
			},
		},
	}
}

// handleToolCall dispatches a tools/call request to the right handler.
func (s *Server) handleToolCall(params json.RawMessage) (*ToolResult, error) {
	var p ToolCallParams
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, fmt.Errorf("invalid tool call params: %w", err)
	}

	switch p.Name {
	case "search_matches":
		return s.toolSearchMatches(p.Arguments)
	case "team_statistics":
		return s.toolTeamStatistics(p.Arguments)
	case "head_to_head":
		return s.toolHeadToHead(p.Arguments)
	case "search_players":
		return s.toolSearchPlayers(p.Arguments)
	case "competition_standings":
		return s.toolCompetitionStandings(p.Arguments)
	case "match_analysis":
		return s.toolMatchAnalysis(p.Arguments)
	default:
		return errorResult(fmt.Sprintf("unknown tool: %s", p.Name)), nil
	}
}

func decodeArgs(raw json.RawMessage, out interface{}) error {
	if len(raw) == 0 || string(raw) == "null" {
		return nil
	}
	return json.Unmarshal(raw, out)
}

func (s *Server) toolSearchMatches(raw json.RawMessage) (*ToolResult, error) {
	var args struct {
		Team        string `json:"team"`
		Team2       string `json:"team2"`
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		DateFrom    string `json:"date_from"`
		DateTo      string `json:"date_to"`
		Limit       int    `json:"limit"`
	}
	if err := decodeArgs(raw, &args); err != nil {
		return errorResult("invalid arguments: " + err.Error()), nil
	}

	if args.Limit <= 0 || args.Limit > 100 {
		args.Limit = 20
	}

	f := MatchFilter{
		Team:        args.Team,
		Team2:       args.Team2,
		Competition: args.Competition,
		Season:      args.Season,
	}
	if args.DateFrom != "" {
		f.DateFrom = parseDate(args.DateFrom)
	}
	if args.DateTo != "" {
		f.DateTo = parseDate(args.DateTo)
	}

	matches := dedupMatchesFuzzy(filterMatches(s.db.Matches, f))
	sortMatchesByDate(matches)

	total := len(matches)
	if len(matches) > args.Limit {
		matches = matches[:args.Limit]
	}

	var sb strings.Builder
	if total == 0 {
		sb.WriteString("No matches found matching the criteria.\n")
	} else {
		fmt.Fprintf(&sb, "Found %d match(es)", total)
		if total > args.Limit {
			fmt.Fprintf(&sb, " (showing first %d)", args.Limit)
		}
		sb.WriteString(":\n\n")
		for _, m := range matches {
			sb.WriteString("- ")
			sb.WriteString(formatMatch(m))
			sb.WriteByte('\n')
		}
	}

	return textResult(sb.String()), nil
}

func (s *Server) toolTeamStatistics(raw json.RawMessage) (*ToolResult, error) {
	var args struct {
		Team        string `json:"team"`
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		HomeAway    string `json:"home_away"`
	}
	if err := decodeArgs(raw, &args); err != nil {
		return errorResult("invalid arguments: " + err.Error()), nil
	}
	if args.Team == "" {
		return errorResult("team parameter is required"), nil
	}

	f := MatchFilter{
		Team:        args.Team,
		Competition: args.Competition,
		Season:      args.Season,
	}
	switch args.HomeAway {
	case "home":
		f.HomeOnly = true
	case "away":
		f.AwayOnly = true
	}

	matches := dedupMatchesFuzzy(filterMatches(s.db.Matches, f))
	stats := calcTeamStats(args.Team, matches)

	var sb strings.Builder
	title := args.Team
	if args.Competition != "" {
		title += " in " + args.Competition
	}
	if args.Season > 0 {
		fmt.Fprintf(&sb, "%s Statistics (%d):\n", title, args.Season)
	} else {
		fmt.Fprintf(&sb, "%s Statistics (all seasons):\n", title)
	}

	if args.HomeAway == "home" {
		sb.WriteString("(Home matches only)\n")
	} else if args.HomeAway == "away" {
		sb.WriteString("(Away matches only)\n")
	}
	sb.WriteString("\n")

	if stats.Played == 0 {
		fmt.Fprintf(&sb, "No matches found for %s\n", args.Team)
	} else {
		fmt.Fprintf(&sb, "Matches Played: %d\n", stats.Played)
		fmt.Fprintf(&sb, "Wins:   %d\n", stats.Wins)
		fmt.Fprintf(&sb, "Draws:  %d\n", stats.Draws)
		fmt.Fprintf(&sb, "Losses: %d\n", stats.Losses)
		fmt.Fprintf(&sb, "Goals For:     %d\n", stats.GoalsFor)
		fmt.Fprintf(&sb, "Goals Against: %d\n", stats.GoalsAgainst)
		fmt.Fprintf(&sb, "Goal Diff:     %+d\n", stats.GoalDiff())
		fmt.Fprintf(&sb, "Points:        %d\n", stats.Points)
		fmt.Fprintf(&sb, "Win Rate:      %.1f%%\n", stats.WinRate())
	}

	return textResult(sb.String()), nil
}

func (s *Server) toolHeadToHead(raw json.RawMessage) (*ToolResult, error) {
	var args struct {
		Team1       string `json:"team1"`
		Team2       string `json:"team2"`
		Competition string `json:"competition"`
		Limit       int    `json:"limit"`
	}
	if err := decodeArgs(raw, &args); err != nil {
		return errorResult("invalid arguments: " + err.Error()), nil
	}
	if args.Team1 == "" || args.Team2 == "" {
		return errorResult("team1 and team2 are required"), nil
	}
	if args.Limit <= 0 {
		args.Limit = 20
	}

	matches := s.db.Matches
	if args.Competition != "" {
		matches = filterMatches(matches, MatchFilter{Competition: args.Competition})
	}

	result := headToHead(matches, args.Team1, args.Team2)

	var sb strings.Builder
	fmt.Fprintf(&sb, "Head-to-Head: %s vs %s\n\n", args.Team1, args.Team2)

	if result.Total == 0 {
		fmt.Fprintf(&sb, "No matches found between these teams.\n")
		return textResult(sb.String()), nil
	}

	fmt.Fprintf(&sb, "Summary (%d matches):\n", result.Total)
	fmt.Fprintf(&sb, "  %s wins: %d\n", args.Team1, result.Team1Wins)
	fmt.Fprintf(&sb, "  %s wins: %d\n", args.Team2, result.Team2Wins)
	fmt.Fprintf(&sb, "  Draws:  %d\n\n", result.Draws)

	showMatches := result.Matches
	if len(showMatches) > args.Limit {
		showMatches = showMatches[:args.Limit]
		fmt.Fprintf(&sb, "Recent %d matches:\n", args.Limit)
	} else {
		sb.WriteString("All matches:\n")
	}

	for _, m := range showMatches {
		sb.WriteString("  - ")
		sb.WriteString(formatMatch(m))
		sb.WriteByte('\n')
	}

	return textResult(sb.String()), nil
}

func (s *Server) toolSearchPlayers(raw json.RawMessage) (*ToolResult, error) {
	var args struct {
		Name        string `json:"name"`
		Nationality string `json:"nationality"`
		Club        string `json:"club"`
		Position    string `json:"position"`
		MinOverall  int    `json:"min_overall"`
		Limit       int    `json:"limit"`
	}
	if err := decodeArgs(raw, &args); err != nil {
		return errorResult("invalid arguments: " + err.Error()), nil
	}
	if args.Limit <= 0 || args.Limit > 200 {
		args.Limit = 20
	}

	f := PlayerFilter{
		Name:        args.Name,
		Nationality: args.Nationality,
		Club:        args.Club,
		Position:    args.Position,
		MinOverall:  args.MinOverall,
	}

	players := searchPlayers(s.db.Players, f)
	sortPlayersByOverall(players)

	total := len(players)
	if len(players) > args.Limit {
		players = players[:args.Limit]
	}

	var sb strings.Builder
	if total == 0 {
		sb.WriteString("No players found matching the criteria.\n")
	} else {
		fmt.Fprintf(&sb, "Found %d player(s)", total)
		if total > args.Limit {
			fmt.Fprintf(&sb, " (showing top %d by overall rating)", args.Limit)
		}
		sb.WriteString(":\n\n")
		for i, p := range players {
			fmt.Fprintf(&sb, "%d. %s\n", i+1, formatPlayer(p))
		}
	}

	return textResult(sb.String()), nil
}

func (s *Server) toolCompetitionStandings(raw json.RawMessage) (*ToolResult, error) {
	var args struct {
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		Limit       int    `json:"limit"`
	}
	if err := decodeArgs(raw, &args); err != nil {
		return errorResult("invalid arguments: " + err.Error()), nil
	}
	if args.Competition == "" {
		return errorResult("competition is required"), nil
	}
	if args.Season == 0 {
		return errorResult("season is required"), nil
	}
	if args.Limit <= 0 {
		args.Limit = 20
	}

	entries := competitionStandings(s.db.Matches, args.Competition, args.Season)

	var sb strings.Builder
	fmt.Fprintf(&sb, "%s %d Standings\n\n", args.Competition, args.Season)

	if len(entries) == 0 {
		fmt.Fprintf(&sb, "No data found for %s %d.\n", args.Competition, args.Season)
		return textResult(sb.String()), nil
	}

	fmt.Fprintf(&sb, "%-4s %-28s %3s %3s %3s %3s %3s %3s %4s %3s\n",
		"Pos", "Team", "MP", "W", "D", "L", "GF", "GA", "GD", "Pts")
	fmt.Fprintf(&sb, "%s\n", strings.Repeat("-", 70))

	show := entries
	if len(show) > args.Limit {
		show = show[:args.Limit]
	}

	for _, e := range show {
		teamDisplay := e.Team
		if len(teamDisplay) > 27 {
			teamDisplay = teamDisplay[:24] + "..."
		}
		fmt.Fprintf(&sb, "%-4d %-28s %3d %3d %3d %3d %3d %3d %+4d %3d\n",
			e.Rank, teamDisplay,
			e.Played, e.Wins, e.Draws, e.Losses,
			e.GoalsFor, e.GoalsAgainst, e.GoalDiff(), e.Points)
	}

	if len(entries) > args.Limit {
		fmt.Fprintf(&sb, "\n... and %d more teams\n", len(entries)-args.Limit)
	}

	return textResult(sb.String()), nil
}

func (s *Server) toolMatchAnalysis(raw json.RawMessage) (*ToolResult, error) {
	var args struct {
		AnalysisType string `json:"analysis_type"`
		Competition  string `json:"competition"`
		Season       int    `json:"season"`
		Limit        int    `json:"limit"`
	}
	if err := decodeArgs(raw, &args); err != nil {
		return errorResult("invalid arguments: " + err.Error()), nil
	}
	if args.AnalysisType == "" {
		return errorResult("analysis_type is required"), nil
	}
	if args.Limit <= 0 {
		args.Limit = 10
	}

	f := MatchFilter{
		Competition: args.Competition,
		Season:      args.Season,
	}
	matches := dedupMatchesFuzzy(filterMatches(s.db.Matches, f))

	if len(matches) == 0 {
		return textResult("No matches found for the specified filters.\n"), nil
	}

	var sb strings.Builder

	switch args.AnalysisType {
	case "biggest_wins":
		wins := biggestWins(matches, args.Limit)
		fmt.Fprintf(&sb, "Biggest Wins")
		if args.Competition != "" {
			fmt.Fprintf(&sb, " in %s", args.Competition)
		}
		if args.Season > 0 {
			fmt.Fprintf(&sb, " (%d)", args.Season)
		}
		sb.WriteString(":\n\n")
		for i, w := range wins {
			dateStr := "unknown"
			if !w.Match.Date.IsZero() {
				dateStr = w.Match.Date.Format("2006-01-02")
			}
			fmt.Fprintf(&sb, "%d. %s: %s %d-%d %s (margin: %d, %s)\n",
				i+1, dateStr, w.Match.HomeTeam, w.Match.HomeGoals, w.Match.AwayGoals,
				w.Match.AwayTeam, w.Margin, w.Match.Competition)
		}

	case "average_goals":
		stats := calcOverallStats(matches)
		fmt.Fprintf(&sb, "Goal Statistics")
		if args.Competition != "" {
			fmt.Fprintf(&sb, " - %s", args.Competition)
		}
		if args.Season > 0 {
			fmt.Fprintf(&sb, " %d", args.Season)
		}
		sb.WriteString(":\n\n")
		fmt.Fprintf(&sb, "Total matches:        %d\n", stats.TotalMatches)
		fmt.Fprintf(&sb, "Total goals:          %d\n", stats.TotalGoals)
		fmt.Fprintf(&sb, "Average goals/match:  %.2f\n", stats.AvgGoals)
		fmt.Fprintf(&sb, "Home wins:            %d (%.1f%%)\n", stats.HomeWins, stats.HomeWinRate)
		fmt.Fprintf(&sb, "Away wins:            %d (%.1f%%)\n", stats.AwayWins, stats.AwayWinRate)
		fmt.Fprintf(&sb, "Draws:                %d (%.1f%%)\n", stats.Draws, stats.DrawRate)

	case "home_advantage":
		stats := calcOverallStats(matches)
		fmt.Fprintf(&sb, "Home vs Away Performance")
		if args.Competition != "" {
			fmt.Fprintf(&sb, " - %s", args.Competition)
		}
		if args.Season > 0 {
			fmt.Fprintf(&sb, " %d", args.Season)
		}
		sb.WriteString(":\n\n")
		fmt.Fprintf(&sb, "Total matches: %d\n\n", stats.TotalMatches)
		fmt.Fprintf(&sb, "Home team wins: %d (%.1f%%)\n", stats.HomeWins, stats.HomeWinRate)
		fmt.Fprintf(&sb, "Away team wins: %d (%.1f%%)\n", stats.AwayWins, stats.AwayWinRate)
		fmt.Fprintf(&sb, "Draws:          %d (%.1f%%)\n", stats.Draws, stats.DrawRate)
		advantage := stats.HomeWinRate - stats.AwayWinRate
		fmt.Fprintf(&sb, "\nHome advantage: %+.1f%% win rate over away teams\n", advantage)

	case "top_scoring_teams":
		teams := topScoringTeams(matches, args.Limit)
		fmt.Fprintf(&sb, "Top Scoring Teams")
		if args.Competition != "" {
			fmt.Fprintf(&sb, " - %s", args.Competition)
		}
		if args.Season > 0 {
			fmt.Fprintf(&sb, " %d", args.Season)
		}
		sb.WriteString(":\n\n")
		for i, t := range teams {
			fmt.Fprintf(&sb, "%d. %-30s Goals: %d (in %d matches, avg: %.2f/match)\n",
				i+1, t.Team, t.GoalsFor, t.Played,
				float64(t.GoalsFor)/float64(t.Played))
		}

	case "best_home_record":
		homeMatches := filterMatches(matches, MatchFilter{})
		teams := bestHomeRecord(homeMatches, 5, args.Limit)
		fmt.Fprintf(&sb, "Best Home Records")
		if args.Competition != "" {
			fmt.Fprintf(&sb, " - %s", args.Competition)
		}
		if args.Season > 0 {
			fmt.Fprintf(&sb, " %d", args.Season)
		}
		sb.WriteString(" (min. 5 home matches):\n\n")
		for i, t := range teams {
			fmt.Fprintf(&sb, "%d. %-30s %d-%d-%d (W-D-L), %.1f%% win rate\n",
				i+1, t.Team, t.Wins, t.Draws, t.Losses, t.WinRate())
		}

	case "best_away_record":
		var awayMatches []Match
		for _, m := range matches {
			awayMatches = append(awayMatches, Match{
				HomeTeam:    m.AwayTeam,
				AwayTeam:    m.HomeTeam,
				HomeGoals:   m.AwayGoals,
				AwayGoals:   m.HomeGoals,
				Date:        m.Date,
				Season:      m.Season,
				Competition: m.Competition,
			})
		}
		teams := bestHomeRecord(awayMatches, 5, args.Limit)
		fmt.Fprintf(&sb, "Best Away Records")
		if args.Competition != "" {
			fmt.Fprintf(&sb, " - %s", args.Competition)
		}
		if args.Season > 0 {
			fmt.Fprintf(&sb, " %d", args.Season)
		}
		sb.WriteString(" (min. 5 away matches):\n\n")
		for i, t := range teams {
			fmt.Fprintf(&sb, "%d. %-30s %d-%d-%d (W-D-L), %.1f%% away win rate\n",
				i+1, t.Team, t.Wins, t.Draws, t.Losses, t.WinRate())
		}

	default:
		return errorResult(fmt.Sprintf("unknown analysis_type: %s", args.AnalysisType)), nil
	}

	return textResult(sb.String()), nil
}

// handleInitialize returns the server's capabilities.
func (s *Server) handleInitialize() interface{} {
	return map[string]interface{}{
		"protocolVersion": "2024-11-05",
		"capabilities": map[string]interface{}{
			"tools": map[string]interface{}{},
		},
		"serverInfo": map[string]interface{}{
			"name":    "brazilian-soccer-mcp",
			"version": "1.0.0",
		},
	}
}

// handleToolsList returns the list of available tools.
func (s *Server) handleToolsList() interface{} {
	return map[string]interface{}{
		"tools": allTools(),
	}
}

