// Package main - Brazilian Soccer MCP Server
// tools.go: MCP tool implementations for querying Brazilian soccer data.
// Each tool accepts parameters as map[string]interface{} and returns a formatted string.
package main

import (
	"fmt"
	"sort"
	"strings"
)

// ToolDefinition describes an MCP tool with its schema.
type ToolDefinition struct {
	Name        string
	Description string
	InputSchema map[string]interface{}
}

// GetToolDefinitions returns all tool definitions for the MCP server.
func GetToolDefinitions() []ToolDefinition {
	return []ToolDefinition{
		{
			Name:        "search_matches",
			Description: "Search for soccer matches by team, season, competition, or date range. Returns match results with dates, scores, and competition info.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"team1": map[string]interface{}{
						"type":        "string",
						"description": "First team name to search for (partial match supported)",
					},
					"team2": map[string]interface{}{
						"type":        "string",
						"description": "Second team name for head-to-head matches (optional)",
					},
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Season year (e.g. 2023)",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Competition name: 'Brasileirao', 'Copa do Brasil', 'Libertadores', or partial match",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum number of matches to return (default 20, max 100)",
					},
				},
			},
		},
		{
			Name:        "get_team_stats",
			Description: "Get statistics for a team: wins, losses, draws, goals scored/conceded, win rate.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"team": map[string]interface{}{
						"type":        "string",
						"description": "Team name (partial match supported)",
					},
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Filter by season year (optional)",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Filter by competition name (optional)",
					},
					"home_only": map[string]interface{}{
						"type":        "boolean",
						"description": "Only include home matches",
					},
					"away_only": map[string]interface{}{
						"type":        "boolean",
						"description": "Only include away matches",
					},
				},
				"required": []string{"team"},
			},
		},
		{
			Name:        "search_players",
			Description: "Search for players in the FIFA database by name, nationality, club, or position.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"name": map[string]interface{}{
						"type":        "string",
						"description": "Player name (partial match)",
					},
					"nationality": map[string]interface{}{
						"type":        "string",
						"description": "Player nationality (e.g. 'Brazil', 'Argentina')",
					},
					"club": map[string]interface{}{
						"type":        "string",
						"description": "Club name (partial match)",
					},
					"position": map[string]interface{}{
						"type":        "string",
						"description": "Playing position (e.g. 'GK', 'ST', 'LW', 'CDM')",
					},
					"min_overall": map[string]interface{}{
						"type":        "integer",
						"description": "Minimum overall rating",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum players to return (default 20, max 100)",
					},
				},
			},
		},
		{
			Name:        "get_standings",
			Description: "Calculate league standings for a given season, showing points, wins, draws, losses, and goal difference.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Season year (required)",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Competition name (default: 'Brasileirao')",
					},
				},
				"required": []string{"season"},
			},
		},
		{
			Name:        "get_head_to_head",
			Description: "Get head-to-head record between two teams, including all matches, wins, draws, and losses.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"team1": map[string]interface{}{
						"type":        "string",
						"description": "First team name",
					},
					"team2": map[string]interface{}{
						"type":        "string",
						"description": "Second team name",
					},
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Filter by competition (optional)",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum matches to show (default 20)",
					},
				},
				"required": []string{"team1", "team2"},
			},
		},
		{
			Name:        "get_biggest_wins",
			Description: "Find the biggest victories (largest goal difference) in the dataset.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"competition": map[string]interface{}{
						"type":        "string",
						"description": "Filter by competition (optional)",
					},
					"team": map[string]interface{}{
						"type":        "string",
						"description": "Filter by team (optional)",
					},
					"season": map[string]interface{}{
						"type":        "integer",
						"description": "Filter by season (optional)",
					},
					"limit": map[string]interface{}{
						"type":        "integer",
						"description": "Number of results (default 10)",
					},
				},
			},
		},
	}
}

// getIntParam extracts an integer parameter from a params map.
func getIntParam(params map[string]interface{}, key string) int {
	v, ok := params[key]
	if !ok {
		return 0
	}
	switch val := v.(type) {
	case float64:
		return int(val)
	case int:
		return val
	case int64:
		return int(val)
	}
	return 0
}

// getStringParam extracts a string parameter from a params map.
func getStringParam(params map[string]interface{}, key string) string {
	v, ok := params[key]
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}

// getBoolParam extracts a bool parameter from a params map.
func getBoolParam(params map[string]interface{}, key string) bool {
	v, ok := params[key]
	if !ok {
		return false
	}
	b, _ := v.(bool)
	return b
}

// SearchMatches finds matches matching the given criteria.
func SearchMatches(db *Database, params map[string]interface{}) string {
	team1 := getStringParam(params, "team1")
	team2 := getStringParam(params, "team2")
	season := getIntParam(params, "season")
	competition := getStringParam(params, "competition")
	limit := getIntParam(params, "limit")
	if limit <= 0 || limit > 100 {
		limit = 20
	}

	var matches []Match
	for _, m := range db.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !strings.Contains(strings.ToLower(m.Competition), strings.ToLower(competition)) {
			continue
		}
		if team1 != "" {
			matchesHome := teamMatches(m.HomeTeam, team1)
			matchesAway := teamMatches(m.AwayTeam, team1)
			if !matchesHome && !matchesAway {
				continue
			}
			if team2 != "" {
				if matchesHome && !teamMatches(m.AwayTeam, team2) {
					continue
				}
				if matchesAway && !teamMatches(m.HomeTeam, team2) {
					continue
				}
			}
		}
		matches = append(matches, m)
	}

	// Sort by date descending
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date > matches[j].Date
	})

	total := len(matches)
	if len(matches) > limit {
		matches = matches[:limit]
	}

	if total == 0 {
		return "No matches found matching the criteria."
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d matches", total))
	if total > limit {
		sb.WriteString(fmt.Sprintf(" (showing first %d)", limit))
	}
	sb.WriteString(":\n\n")

	for _, m := range matches {
		roundInfo := ""
		if m.Round != "" {
			roundInfo = fmt.Sprintf(" Round %s", m.Round)
		} else if m.Stage != "" {
			roundInfo = fmt.Sprintf(" (%s)", m.Stage)
		}
		sb.WriteString(fmt.Sprintf("- %s: %s %d-%d %s [%s%s]\n",
			m.Date,
			normalizeTeamName(m.HomeTeam),
			m.HomeGoals,
			m.AwayGoals,
			normalizeTeamName(m.AwayTeam),
			m.Competition,
			roundInfo,
		))
	}
	return sb.String()
}

// teamStatsRecord holds aggregated stats for a team.
type teamStatsRecord struct {
	Played      int
	Wins        int
	Draws       int
	Losses      int
	GoalsFor    int
	GoalsAgainst int
}

func (s *teamStatsRecord) Points() int {
	return s.Wins*3 + s.Draws
}

func (s *teamStatsRecord) GoalDiff() int {
	return s.GoalsFor - s.GoalsAgainst
}

func (s *teamStatsRecord) WinRate() float64 {
	if s.Played == 0 {
		return 0
	}
	return float64(s.Wins) / float64(s.Played) * 100
}

// GetTeamStats calculates statistics for a team.
func GetTeamStats(db *Database, params map[string]interface{}) string {
	team := getStringParam(params, "team")
	if team == "" {
		return "Error: 'team' parameter is required."
	}
	season := getIntParam(params, "season")
	competition := getStringParam(params, "competition")
	homeOnly := getBoolParam(params, "home_only")
	awayOnly := getBoolParam(params, "away_only")

	homeStats := &teamStatsRecord{}
	awayStats := &teamStatsRecord{}
	overallStats := &teamStatsRecord{}

	for _, m := range db.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !strings.Contains(strings.ToLower(m.Competition), strings.ToLower(competition)) {
			continue
		}

		isHome := teamMatches(m.HomeTeam, team)
		isAway := teamMatches(m.AwayTeam, team)

		if !isHome && !isAway {
			continue
		}

		if isHome && !awayOnly {
			homeStats.Played++
			overallStats.Played++
			homeStats.GoalsFor += m.HomeGoals
			homeStats.GoalsAgainst += m.AwayGoals
			overallStats.GoalsFor += m.HomeGoals
			overallStats.GoalsAgainst += m.AwayGoals
			switch {
			case m.HomeGoals > m.AwayGoals:
				homeStats.Wins++
				overallStats.Wins++
			case m.HomeGoals == m.AwayGoals:
				homeStats.Draws++
				overallStats.Draws++
			default:
				homeStats.Losses++
				overallStats.Losses++
			}
		}

		if isAway && !homeOnly {
			awayStats.Played++
			overallStats.Played++
			awayStats.GoalsFor += m.AwayGoals
			awayStats.GoalsAgainst += m.HomeGoals
			overallStats.GoalsFor += m.AwayGoals
			overallStats.GoalsAgainst += m.HomeGoals
			switch {
			case m.AwayGoals > m.HomeGoals:
				awayStats.Wins++
				overallStats.Wins++
			case m.AwayGoals == m.HomeGoals:
				awayStats.Draws++
				overallStats.Draws++
			default:
				awayStats.Losses++
				overallStats.Losses++
			}
		}
	}

	if overallStats.Played == 0 {
		return fmt.Sprintf("No matches found for team %q.", team)
	}

	var sb strings.Builder
	filterDesc := team
	if season != 0 {
		filterDesc += fmt.Sprintf(" (%d)", season)
	}
	if competition != "" {
		filterDesc += fmt.Sprintf(" [%s]", competition)
	}

	sb.WriteString(fmt.Sprintf("Statistics for %s:\n\n", filterDesc))

	if !homeOnly && !awayOnly {
		sb.WriteString(fmt.Sprintf("Overall: %dP | %dW %dD %dL | GF: %d GA: %d GD: %+d | Pts: %d | Win rate: %.1f%%\n",
			overallStats.Played, overallStats.Wins, overallStats.Draws, overallStats.Losses,
			overallStats.GoalsFor, overallStats.GoalsAgainst, overallStats.GoalDiff(),
			overallStats.Points(), overallStats.WinRate()))
		sb.WriteString(fmt.Sprintf("Home:    %dP | %dW %dD %dL | GF: %d GA: %d GD: %+d | Win rate: %.1f%%\n",
			homeStats.Played, homeStats.Wins, homeStats.Draws, homeStats.Losses,
			homeStats.GoalsFor, homeStats.GoalsAgainst, homeStats.GoalDiff(),
			homeStats.WinRate()))
		sb.WriteString(fmt.Sprintf("Away:    %dP | %dW %dD %dL | GF: %d GA: %d GD: %+d | Win rate: %.1f%%\n",
			awayStats.Played, awayStats.Wins, awayStats.Draws, awayStats.Losses,
			awayStats.GoalsFor, awayStats.GoalsAgainst, awayStats.GoalDiff(),
			awayStats.WinRate()))
	} else if homeOnly {
		sb.WriteString(fmt.Sprintf("Home: %dP | %dW %dD %dL | GF: %d GA: %d GD: %+d | Win rate: %.1f%%\n",
			homeStats.Played, homeStats.Wins, homeStats.Draws, homeStats.Losses,
			homeStats.GoalsFor, homeStats.GoalsAgainst, homeStats.GoalDiff(),
			homeStats.WinRate()))
	} else {
		sb.WriteString(fmt.Sprintf("Away: %dP | %dW %dD %dL | GF: %d GA: %d GD: %+d | Win rate: %.1f%%\n",
			awayStats.Played, awayStats.Wins, awayStats.Draws, awayStats.Losses,
			awayStats.GoalsFor, awayStats.GoalsAgainst, awayStats.GoalDiff(),
			awayStats.WinRate()))
	}
	return sb.String()
}

// SearchPlayers finds players matching given criteria, sorted by overall rating.
func SearchPlayers(db *Database, params map[string]interface{}) string {
	name := getStringParam(params, "name")
	nationality := getStringParam(params, "nationality")
	club := getStringParam(params, "club")
	position := getStringParam(params, "position")
	minOverall := getIntParam(params, "min_overall")
	limit := getIntParam(params, "limit")
	if limit <= 0 || limit > 100 {
		limit = 20
	}

	var players []Player
	for _, p := range db.Players {
		if name != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(name)) {
			continue
		}
		if nationality != "" && !strings.Contains(strings.ToLower(p.Nationality), strings.ToLower(nationality)) {
			continue
		}
		if club != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(club)) {
			continue
		}
		if position != "" && !strings.Contains(strings.ToLower(p.Position), strings.ToLower(position)) {
			continue
		}
		if minOverall > 0 && p.Overall < minOverall {
			continue
		}
		players = append(players, p)
	}

	// Sort by overall rating descending
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	total := len(players)
	if len(players) > limit {
		players = players[:limit]
	}

	if total == 0 {
		return "No players found matching the criteria."
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d players", total))
	if total > limit {
		sb.WriteString(fmt.Sprintf(" (showing top %d by overall rating)", limit))
	}
	sb.WriteString(":\n\n")

	for i, p := range players {
		sb.WriteString(fmt.Sprintf("%d. %s - Overall: %d, Potential: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, p.Club, p.Nationality, p.Age))
	}
	return sb.String()
}

// GetStandings calculates league standings for a season.
func GetStandings(db *Database, params map[string]interface{}) string {
	season := getIntParam(params, "season")
	if season == 0 {
		return "Error: 'season' parameter is required."
	}
	competition := getStringParam(params, "competition")
	if competition == "" {
		competition = "Brasileirao"
	}

	standings := make(map[string]*teamStatsRecord)

	for _, m := range db.Matches {
		if m.Season != season {
			continue
		}
		if !strings.Contains(strings.ToLower(m.Competition), strings.ToLower(competition)) {
			continue
		}

		home := normalizeTeamName(m.HomeTeam)
		away := normalizeTeamName(m.AwayTeam)

		if _, ok := standings[home]; !ok {
			standings[home] = &teamStatsRecord{}
		}
		if _, ok := standings[away]; !ok {
			standings[away] = &teamStatsRecord{}
		}

		h := standings[home]
		a := standings[away]

		h.Played++
		a.Played++
		h.GoalsFor += m.HomeGoals
		h.GoalsAgainst += m.AwayGoals
		a.GoalsFor += m.AwayGoals
		a.GoalsAgainst += m.HomeGoals

		switch {
		case m.HomeGoals > m.AwayGoals:
			h.Wins++
			a.Losses++
		case m.HomeGoals == m.AwayGoals:
			h.Draws++
			a.Draws++
		default:
			h.Losses++
			a.Wins++
		}
	}

	if len(standings) == 0 {
		return fmt.Sprintf("No matches found for %s %d.", competition, season)
	}

	// Convert to slice for sorting
	type teamEntry struct {
		name  string
		stats *teamStatsRecord
	}
	var entries []teamEntry
	for name, stats := range standings {
		entries = append(entries, teamEntry{name, stats})
	}

	// Sort by points, then goal diff, then goals for
	sort.Slice(entries, func(i, j int) bool {
		pi := entries[i].stats.Points()
		pj := entries[j].stats.Points()
		if pi != pj {
			return pi > pj
		}
		di := entries[i].stats.GoalDiff()
		dj := entries[j].stats.GoalDiff()
		if di != dj {
			return di > dj
		}
		return entries[i].stats.GoalsFor > entries[j].stats.GoalsFor
	})

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%d %s Standings (%d teams):\n\n", season, competition, len(entries)))
	sb.WriteString(fmt.Sprintf("%-4s %-25s %3s %3s %3s %3s %4s %4s %4s %4s\n",
		"Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"))
	sb.WriteString(strings.Repeat("-", 65) + "\n")

	for i, e := range entries {
		s := e.stats
		sb.WriteString(fmt.Sprintf("%-4d %-25s %3d %3d %3d %3d %4d %4d %+4d %4d\n",
			i+1, e.name, s.Played, s.Wins, s.Draws, s.Losses,
			s.GoalsFor, s.GoalsAgainst, s.GoalDiff(), s.Points()))
	}
	return sb.String()
}

// GetHeadToHead returns the head-to-head record between two teams.
func GetHeadToHead(db *Database, params map[string]interface{}) string {
	team1 := getStringParam(params, "team1")
	team2 := getStringParam(params, "team2")
	competition := getStringParam(params, "competition")
	limit := getIntParam(params, "limit")
	if limit <= 0 || limit > 100 {
		limit = 20
	}

	if team1 == "" || team2 == "" {
		return "Error: 'team1' and 'team2' parameters are required."
	}

	var matches []Match
	t1Wins, t2Wins, draws := 0, 0, 0
	t1Goals, t2Goals := 0, 0

	for _, m := range db.Matches {
		if competition != "" && !strings.Contains(strings.ToLower(m.Competition), strings.ToLower(competition)) {
			continue
		}

		isT1Home := teamMatches(m.HomeTeam, team1) && teamMatches(m.AwayTeam, team2)
		isT2Home := teamMatches(m.HomeTeam, team2) && teamMatches(m.AwayTeam, team1)

		if !isT1Home && !isT2Home {
			continue
		}

		matches = append(matches, m)

		if isT1Home {
			t1Goals += m.HomeGoals
			t2Goals += m.AwayGoals
			switch {
			case m.HomeGoals > m.AwayGoals:
				t1Wins++
			case m.HomeGoals == m.AwayGoals:
				draws++
			default:
				t2Wins++
			}
		} else {
			t1Goals += m.AwayGoals
			t2Goals += m.HomeGoals
			switch {
			case m.AwayGoals > m.HomeGoals:
				t1Wins++
			case m.AwayGoals == m.HomeGoals:
				draws++
			default:
				t2Wins++
			}
		}
	}

	if len(matches) == 0 {
		return fmt.Sprintf("No matches found between %q and %q.", team1, team2)
	}

	// Sort by date descending
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date > matches[j].Date
	})

	total := len(matches)

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Head-to-Head: %s vs %s\n", team1, team2))
	sb.WriteString(fmt.Sprintf("Total matches: %d | %s: %d wins | %s: %d wins | Draws: %d\n",
		total, team1, t1Wins, team2, t2Wins, draws))
	sb.WriteString(fmt.Sprintf("Goals: %s %d - %d %s\n\n", team1, t1Goals, t2Goals, team2))

	displayed := clampInt(total, limit)
	sb.WriteString(fmt.Sprintf("Most recent %d matches:\n", displayed))

	for i, m := range matches {
		if i >= limit {
			break
		}
		roundInfo := ""
		if m.Round != "" {
			roundInfo = fmt.Sprintf(" Round %s", m.Round)
		} else if m.Stage != "" {
			roundInfo = fmt.Sprintf(" (%s)", m.Stage)
		}
		sb.WriteString(fmt.Sprintf("- %s: %s %d-%d %s [%s%s]\n",
			m.Date,
			normalizeTeamName(m.HomeTeam),
			m.HomeGoals,
			m.AwayGoals,
			normalizeTeamName(m.AwayTeam),
			m.Competition,
			roundInfo,
		))
	}
	return sb.String()
}

// GetBiggestWins finds the matches with the largest goal difference.
func GetBiggestWins(db *Database, params map[string]interface{}) string {
	competition := getStringParam(params, "competition")
	team := getStringParam(params, "team")
	season := getIntParam(params, "season")
	limit := getIntParam(params, "limit")
	if limit <= 0 || limit > 100 {
		limit = 10
	}

	type matchWithDiff struct {
		match Match
		diff  int
	}

	var candidates []matchWithDiff
	for _, m := range db.Matches {
		if competition != "" && !strings.Contains(strings.ToLower(m.Competition), strings.ToLower(competition)) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if team != "" {
			if !teamMatches(m.HomeTeam, team) && !teamMatches(m.AwayTeam, team) {
				continue
			}
		}
		diff := goalDiff(m.HomeGoals, m.AwayGoals)
		candidates = append(candidates, matchWithDiff{m, diff})
	}

	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].diff > candidates[j].diff
	})

	if len(candidates) == 0 {
		return "No matches found matching the criteria."
	}

	total := len(candidates)
	if len(candidates) > limit {
		candidates = candidates[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Biggest wins (out of %d matches):\n\n", total))

	for i, c := range candidates {
		m := c.match
		roundInfo := ""
		if m.Round != "" {
			roundInfo = fmt.Sprintf(" Round %s", m.Round)
		} else if m.Stage != "" {
			roundInfo = fmt.Sprintf(" (%s)", m.Stage)
		}
		sb.WriteString(fmt.Sprintf("%d. %s: %s %d-%d %s [%s%s] (margin: %d)\n",
			i+1,
			m.Date,
			normalizeTeamName(m.HomeTeam),
			m.HomeGoals,
			m.AwayGoals,
			normalizeTeamName(m.AwayTeam),
			m.Competition,
			roundInfo,
			c.diff,
		))
	}
	return sb.String()
}

// DispatchTool routes a tool call to the appropriate handler.
func DispatchTool(db *Database, toolName string, params map[string]interface{}) (string, error) {
	switch toolName {
	case "search_matches":
		return SearchMatches(db, params), nil
	case "get_team_stats":
		return GetTeamStats(db, params), nil
	case "search_players":
		return SearchPlayers(db, params), nil
	case "get_standings":
		return GetStandings(db, params), nil
	case "get_head_to_head":
		return GetHeadToHead(db, params), nil
	case "get_biggest_wins":
		return GetBiggestWins(db, params), nil
	default:
		return "", fmt.Errorf("unknown tool: %s", toolName)
	}
}
