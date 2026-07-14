// Tools implements the MCP tool definitions and handlers for the Brazilian
// Soccer MCP Server. Each tool corresponds to a query category:
// matches, team_stats, player_search, head_to_head, standings, biggest_wins, stats.
package main

import (
	"encoding/json"
	"fmt"

	"github.com/google/jsonschema-go/jsonschema"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// BuildTools returns all MCP tool definitions for the store.
func BuildTools(store *Store) ([]*mcp.Tool, error) {
	tools := []*mcp.Tool{
		buildSearchMatchesTool(),
		buildTeamStatsTool(),
		buildPlayerSearchTool(),
		buildHeadToHeadTool(),
		buildStandingsTool(),
		buildBiggestWinsTool(),
		buildStatsTool(),
	}
	return tools, nil
}

func buildSearchMatchesTool() *mcp.Tool {
	inSchema, err := jsonschema.For[SearchMatchesInput](nil)
	if err != nil {
		return &mcp.Tool{
			Name:        "search_matches",
			Description: "Search for matches by team, competition, season, or date range (schema error)",
			InputSchema: json.RawMessage(`{"type":"object"}`),
		}
	}
	return &mcp.Tool{
		Name:        "search_matches",
		Description: "Search for matches by team, competition, season, or date range",
		InputSchema: inSchema,
	}
}

func buildTeamStatsTool() *mcp.Tool {
	inSchema, err := jsonschema.For[TeamStatsInput](nil)
	if err != nil {
		return &mcp.Tool{
			Name:        "team_stats",
			Description: "Get win/loss/draw statistics for a team in a competition or season",
			InputSchema: json.RawMessage(`{"type":"object"}`),
		}
	}
	return &mcp.Tool{
		Name:        "team_stats",
		Description: "Get win/loss/draw statistics for a team in a competition or season",
		InputSchema: inSchema,
	}
}

func buildPlayerSearchTool() *mcp.Tool {
	inSchema, err := jsonschema.For[PlayerSearchInput](nil)
	if err != nil {
		return &mcp.Tool{
			Name:        "player_search",
			Description: "Search for players by name, nationality, club, or position",
			InputSchema: json.RawMessage(`{"type":"object"}`),
		}
	}
	return &mcp.Tool{
		Name:        "player_search",
		Description: "Search for players by name, nationality, club, or position",
		InputSchema: inSchema,
	}
}

func buildHeadToHeadTool() *mcp.Tool {
	inSchema, err := jsonschema.For[HeadToHeadInput](nil)
	if err != nil {
		return &mcp.Tool{
			Name:        "head_to_head",
			Description: "Get head-to-head comparison between two teams",
			InputSchema: json.RawMessage(`{"type":"object"}`),
		}
	}
	return &mcp.Tool{
		Name:        "head_to_head",
		Description: "Get head-to-head comparison between two teams",
		InputSchema: inSchema,
	}
}

func buildStandingsTool() *mcp.Tool {
	inSchema, err := jsonschema.For[StandingsInput](nil)
	if err != nil {
		return &mcp.Tool{
			Name:        "standings",
			Description: "Get competition standings by season (calculated from match results)",
			InputSchema: json.RawMessage(`{"type":"object"}`),
		}
	}
	return &mcp.Tool{
		Name:        "standings",
		Description: "Get competition standings by season (calculated from match results)",
		InputSchema: inSchema,
	}
}

func buildBiggestWinsTool() *mcp.Tool {
	inSchema, err := jsonschema.For[BiggestWinsInput](nil)
	if err != nil {
		return &mcp.Tool{
			Name:        "biggest_wins",
			Description: "Find the biggest victories (goal difference >= 5) in a competition",
			InputSchema: json.RawMessage(`{"type":"object"}`),
		}
	}
	return &mcp.Tool{
		Name:        "biggest_wins",
		Description: "Find the biggest victories (goal difference >= 5) in a competition",
		InputSchema: inSchema,
	}
}

func buildStatsTool() *mcp.Tool {
	inSchema, err := jsonschema.For[StatsInput](nil)
	if err != nil {
		return &mcp.Tool{
			Name:        "stats",
			Description: "Get aggregated statistics (avg goals, win rates) for a competition",
			InputSchema: json.RawMessage(`{"type":"object"}`),
		}
	}
	return &mcp.Tool{
		Name:        "stats",
		Description: "Get aggregated statistics (avg goals, win rates) for a competition",
		InputSchema: inSchema,
	}
}

// Tool input/output types
type SearchMatchesInput struct {
	Team         string `json:"team" jsonschema:"Team name to search for"`
	Competition  string `json:"competition,omitempty" jsonschema:"Competition name (optional)"`
	Season       string `json:"season,omitempty" jsonschema:"Season year (optional)"`
	DateStart    string `json:"date_start,omitempty" jsonschema:"Start date filter (optional)"`
	DateEnd      string `json:"date_end,omitempty" jsonschema:"End date filter (optional)"`
	Limit        int    `json:"limit,omitempty" jsonschema:"Maximum number of results (optional, default 50)"`
}

type SearchMatchesOutput struct {
	Matches []Match `json:"matches"`
	Count   int     `json:"count"`
	Team    string  `json:"team"`
}

type TeamStatsInput struct {
	TeamName    string `json:"team_name" jsonschema:"Team name"`
	Competition string `json:"competition,omitempty" jsonschema:"Competition filter (optional)"`
	Season      string `json:"season,omitempty" jsonschema:"Season year filter (optional)"`
}

type TeamStatsOutput struct {
	TeamName     string  `json:"team_name"`
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	WinRate      float64 `json:"win_rate"`
}

type PlayerSearchInput struct {
	Name        string `json:"name,omitempty" jsonschema:"Player name (partial match, optional)"`
	Nationality string `json:"nationality,omitempty" jsonschema:"Nationality (exact match, optional)"`
	Club        string `json:"club,omitempty" jsonschema:"Club name (partial match, optional)"`
	Position    string `json:"position,omitempty" jsonschema:"Position (partial match, optional)"`
	Limit       int    `json:"limit,omitempty" jsonschema:"Maximum results (optional, default 50)"`
}

type PlayerSearchOutput struct {
	Players []Player `json:"players"`
	Count   int      `json:"count"`
}

type HeadToHeadInput struct {
	Team1 string `json:"team1" jsonschema:"First team name"`
	Team2 string `json:"team2" jsonschema:"Second team name"`
}

type HeadToHeadOutput struct {
	Team1        string  `json:"team1"`
	Team2        string  `json:"team2"`
	Team1Wins    int     `json:"team1_wins"`
	Team2Wins    int     `json:"team2_wins"`
	Draws        int     `json:"draws"`
	TotalMatches int     `json:"total_matches"`
	Matches      []Match `json:"matches,omitempty"`
}

type StandingsInput struct {
	Competition string `json:"competition" jsonschema:"Competition name"`
	Season      string `json:"season" jsonschema:"Season year"`
}

type StandingsOutput struct {
	Competition string           `json:"competition"`
	Season      int              `json:"season"`
	Standings   []StandingsEntry `json:"standings"`
}

type BiggestWinsInput struct {
	Competition string `json:"competition" jsonschema:"Competition name (optional, empty for all)"`
	Limit       int    `json:"limit,omitempty" jsonschema:"Max results (optional, default 20)"`
}

type BiggestWinsOutput struct {
	Wins  []BigWin `json:"wins"`
	Count int      `json:"count"`
}

type StatsInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"Competition name (optional)"`
	Season      string `json:"season,omitempty" jsonschema:"Season year (optional)"`
}

type StatsOutput struct {
	AvgGoalsPerMatch float64 `json:"avg_goals_per_match"`
	HomeWinRate      float64 `json:"home_win_rate"`
	DrawRate         float64 `json:"draw_rate"`
	AwayWinRate      float64 `json:"away_win_rate"`
	TotalMatches     int     `json:"total_matches"`
	TotalGoals       int     `json:"total_goals"`
}

// MatchFormat formats a match as a human-readable string.
func MatchFormat(m Match) string {
	roundInfo := ""
	if m.Round != "" {
		roundInfo = fmt.Sprintf(" (Round %s)", m.Round)
	}
	if m.Competition != "" {
		roundInfo += fmt.Sprintf(" (%s)", m.Competition)
	}
	if m.Stage != "" {
		roundInfo += fmt.Sprintf(" - %s", m.Stage)
	}
	return fmt.Sprintf("%s: %s %d-%d %s%s", m.DateTime, m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam, roundInfo)
}

// FormatMatches formats a slice of matches as a table string.
func FormatMatches(matches []Match) string {
	if len(matches) == 0 {
		return "No matches found."
	}

	var result string
	for i, m := range matches {
		if i > 0 {
			result += "\n"
		}
		result += MatchFormat(m)
	}
	return result
}

// FormatH2H formats a head-to-head record as a readable string.
func FormatH2H(record H2HRecord) string {
	if record.TotalMatches == 0 {
		return fmt.Sprintf("No matches found between %s and %s.", record.Team1, record.Team2)
	}

	result := fmt.Sprintf("%s vs %s Head-to-Head:\n", record.Team1, record.Team2)
	result += fmt.Sprintf("%s: %d wins, %d draws, %d losses\n", record.Team1, record.Team1Wins, record.Draws, record.Team2Wins)
	result += fmt.Sprintf("%s: %d wins, %d draws, %d losses\n", record.Team2, record.Team2Wins, record.Draws, record.Team1Wins)
	result += fmt.Sprintf("Total matches: %d\n\n", record.TotalMatches)

	for i, m := range record.Matches {
		if i >= 10 {
			result += fmt.Sprintf("... and %d more matches\n", len(record.Matches)-10)
			break
		}
		result += MatchFormat(m) + "\n"
	}
	return result
}

// FormatStandings formats standings as a table string.
func FormatStandings(entries []StandingsEntry) string {
	if len(entries) == 0 {
		return "No standings data available."
	}

	result := fmt.Sprintf("%-4s %-25s %-4s %-4s %-4s %-4s %-4s %-4s %-6s\n",
		"Pos", "Team", "P", "W", "D", "L", "GD", "GF", "Pts")
	result += fmt.Sprintf("%-4s %-25s %-4s %-4s %-4s %-4s %-4s %-4s %-6s\n",
		"---", "----", "---", "---", "---", "---", "---", "---", "---")

	for i, e := range entries {
		if i >= 50 {
			result += fmt.Sprintf("... and %d more teams\n", len(entries)-50)
			break
		}
		gd := e.GoalsFor - e.GoalsAgainst
		gdStr := fmt.Sprintf("%+d", gd)
		result += fmt.Sprintf("%-4d %-25s %-4d %-4d %-4d %-4d %-4s %-4d %-6d\n",
			i+1, e.Team, e.Played, e.Wins, e.Draws, e.Losses, gdStr, e.GoalsFor, e.Points)
	}
	return result
}

// FormatPlayer formats a player as a readable line.
func FormatPlayer(p Player) string {
	return fmt.Sprintf("%s (Overall: %d, Age: %d, Pos: %s, Club: %s)",
		p.Name, p.Overall, p.Age, p.Position, p.Club)
}

// formatPlayerList formats players as a numbered list.
func formatPlayerList(players []Player) string {
	if len(players) == 0 {
		return "No players found."
	}

	var result string
	for i, p := range players {
		result += fmt.Sprintf("%d. %s\n", i+1, FormatPlayer(p))
	}
	return result
}

// formatStats formats stats as readable text.
func formatStats(s StatsSummary) string {
	return fmt.Sprintf("Total matches: %d\nTotal goals: %d\nAvg goals per match: %.2f\nHome win rate: %.1f%%\nDraw rate: %.1f%%\nAway win rate: %.1f%%",
		s.TotalMatches, s.TotalGoals, s.AvgGoalsPerMatch, s.HomeWinRate, s.DrawRate, s.AwayWinRate)
}

// formatBigWins formats biggest wins as a numbered list.
func formatBigWins(wins []BigWin) string {
	if len(wins) == 0 {
		return "No big wins found."
	}

	var result string
	for i, w := range wins {
		result += fmt.Sprintf("%d. %s: %s %d-%d %s (%s)\n",
			i+1, w.Date, w.HomeTeam, w.HomeScore, w.AwayScore, w.AwayTeam, w.Competition)
	}
	return result
}

// FormatTextContent formats structured output for human reading.
func FormatTextContent(name string, v interface{}) mcp.Content {
	switch out := v.(type) {
	case SearchMatchesOutput:
		text := fmt.Sprintf("Found %d matches for team %q:\n\n%s\n", out.Count, out.Team, FormatMatches(out.Matches))
		return &mcp.TextContent{Text: text}
	case TeamStatsOutput:
		text := fmt.Sprintf("%s Record (Competition: %s, Season: %s):\n",
			out.TeamName, "all", "all")
		text += fmt.Sprintf("  Matches: %d\n", out.Matches)
		text += fmt.Sprintf("  Wins: %d, Draws: %d, Losses: %d\n", out.Wins, out.Draws, out.Losses)
		text += fmt.Sprintf("  Goals For: %d, Goals Against: %d\n", out.GoalsFor, out.GoalsAgainst)
		text += fmt.Sprintf("  Win Rate: %.1f%%\n", out.WinRate)
		return &mcp.TextContent{Text: text}
	case PlayerSearchOutput:
		text := fmt.Sprintf("Found %d players:\n\n%s\n", out.Count, formatPlayerList(out.Players))
		return &mcp.TextContent{Text: text}
	case HeadToHeadOutput:
		text := FormatH2H(H2HRecord{
			Team1: out.Team1, Team2: out.Team2,
			Team1Wins: out.Team1Wins, Team2Wins: out.Team2Wins,
			Draws: out.Draws, TotalMatches: out.TotalMatches,
			Matches: out.Matches,
		})
		return &mcp.TextContent{Text: text}
	case StandingsOutput:
		text := fmt.Sprintf("Standings: %s (%d)\n\n%s\n",
			out.Competition, out.Season, FormatStandings(out.Standings))
		return &mcp.TextContent{Text: text}
	case BiggestWinsOutput:
		text := fmt.Sprintf("Found %d big wins (goal diff >= 5):\n\n%s\n", out.Count, formatBigWins(out.Wins))
		return &mcp.TextContent{Text: text}
	case StatsOutput:
		text := fmt.Sprintf("Statistics:\n%s\n", formatStats(StatsSummary{
			AvgGoalsPerMatch: out.AvgGoalsPerMatch,
			HomeWinRate:      out.HomeWinRate,
			DrawRate:         out.DrawRate,
			AwayWinRate:      out.AwayWinRate,
			TotalMatches:     out.TotalMatches,
			TotalGoals:       out.TotalGoals,
		}))
		return &mcp.TextContent{Text: text}
	default:
		data, _ := json.MarshalIndent(v, "", "  ")
		return &mcp.TextContent{Text: string(data)}
	}
}
