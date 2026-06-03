package main

import (
	"fmt"
	"strings"
	"time"
)

// Tool defines a single MCP tool. Handler returns (text, isError).
type tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(args map[string]any) (string, bool)
}

// argString fetches an argument by name, returning "" if missing or wrong type.
func argString(args map[string]any, key string) string {
	if args == nil {
		return ""
	}
	v, ok := args[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case float64:
		return fmt.Sprintf("%g", t)
	case int:
		return fmt.Sprintf("%d", t)
	case bool:
		return fmt.Sprintf("%t", t)
	default:
		return fmt.Sprintf("%v", t)
	}
}

func argInt(args map[string]any, key string) int {
	v, ok := args[key]
	if !ok || v == nil {
		return 0
	}
	switch t := v.(type) {
	case float64:
		return int(t)
	case int:
		return t
	case string:
		return atoi(t)
	}
	return 0
}

func argDate(args map[string]any, key string) time.Time {
	s := argString(args, key)
	if s == "" {
		return time.Time{}
	}
	return parseDate(s)
}

// buildTools assembles the tool registry. Each tool's input schema is a
// minimal JSON Schema describing the arguments it expects.
func (s *Server) buildTools() []tool {
	return []tool{
		{
			Name:        "search_matches",
			Description: "Search soccer matches by team, competition, season, date range, or stage. Returns up to `limit` matches sorted by date (most recent first).",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"team":        map[string]any{"type": "string", "description": "Team name (matches if home or away)."},
					"opponent":    map[string]any{"type": "string", "description": "Second team for head-to-head queries."},
					"home_team":   map[string]any{"type": "string"},
					"away_team":   map[string]any{"type": "string"},
					"competition": map[string]any{"type": "string", "description": "Brasileirão, Copa do Brasil, Libertadores, etc."},
					"season":      map[string]any{"type": "integer", "description": "Season year, e.g. 2019."},
					"from":        map[string]any{"type": "string", "description": "ISO date (inclusive)."},
					"to":          map[string]any{"type": "string", "description": "ISO date (inclusive)."},
					"stage":       map[string]any{"type": "string", "description": "Tournament stage substring (e.g. 'final', 'group')."},
					"limit":       map[string]any{"type": "integer", "description": "Maximum matches to return (default 25)."},
				},
			},
			Handler: s.handleSearchMatches,
		},
		{
			Name:        "team_stats",
			Description: "Compute wins/draws/losses, goals for/against and win rate for a team. Optionally restrict to home or away, a competition, or a season.",
			InputSchema: map[string]any{
				"type": "object",
				"required": []string{"team"},
				"properties": map[string]any{
					"team":        map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
					"competition": map[string]any{"type": "string"},
					"home_only":   map[string]any{"type": "boolean"},
					"away_only":   map[string]any{"type": "boolean"},
				},
			},
			Handler: s.handleTeamStats,
		},
		{
			Name:        "head_to_head",
			Description: "Summarise the head-to-head record between two teams, optionally restricted to a competition or season.",
			InputSchema: map[string]any{
				"type": "object",
				"required": []string{"team_a", "team_b"},
				"properties": map[string]any{
					"team_a":      map[string]any{"type": "string"},
					"team_b":      map[string]any{"type": "string"},
					"competition": map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
					"limit":       map[string]any{"type": "integer", "description": "Maximum matches to list (default 20)."},
				},
			},
			Handler: s.handleHeadToHead,
		},
		{
			Name:        "standings",
			Description: "Calculate a standings table from match results for a competition + season. Defaults to Brasileirão if competition is omitted.",
			InputSchema: map[string]any{
				"type": "object",
				"required": []string{"season"},
				"properties": map[string]any{
					"season":      map[string]any{"type": "integer"},
					"competition": map[string]any{"type": "string"},
					"limit":       map[string]any{"type": "integer", "description": "Maximum rows to return (default 20)."},
				},
			},
			Handler: s.handleStandings,
		},
		{
			Name:        "search_players",
			Description: "Search FIFA players by name, nationality, club, position, and minimum overall rating. Results sorted by overall rating descending.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name":        map[string]any{"type": "string"},
					"nationality": map[string]any{"type": "string"},
					"club":        map[string]any{"type": "string"},
					"position":    map[string]any{"type": "string"},
					"min_overall": map[string]any{"type": "integer"},
					"limit":       map[string]any{"type": "integer", "description": "Default 25."},
				},
			},
			Handler: s.handleSearchPlayers,
		},
		{
			Name:        "biggest_wins",
			Description: "Return matches with the largest goal margins. Optionally restrict by competition and season.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"competition": map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
					"limit":       map[string]any{"type": "integer", "description": "Default 10."},
				},
			},
			Handler: s.handleBiggestWins,
		},
		{
			Name:        "competition_summary",
			Description: "Aggregate statistics for a competition + season: total matches, total goals, average goals per match, and home win rate.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"competition": map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
				},
			},
			Handler: s.handleCompetitionSummary,
		},
		{
			Name:        "dataset_info",
			Description: "Describe the loaded data: total matches, players, competitions covered, and season ranges.",
			InputSchema: map[string]any{
				"type":       "object",
				"properties": map[string]any{},
			},
			Handler: s.handleDatasetInfo,
		},
	}
}

func (s *Server) handleSearchMatches(args map[string]any) (string, bool) {
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 25
	}
	filter := MatchFilter{
		Team:        argString(args, "team"),
		Opponent:    argString(args, "opponent"),
		HomeTeam:    argString(args, "home_team"),
		AwayTeam:    argString(args, "away_team"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		Stage:       argString(args, "stage"),
		From:        argDate(args, "from"),
		To:          argDate(args, "to"),
		Limit:       limit,
	}
	matches := s.ds.FindMatches(filter)
	if len(matches) == 0 {
		return "No matches found.", false
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es) (showing %d):\n", len(matches), len(matches))
	for _, m := range matches {
		fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
	}
	if filter.Team != "" && filter.Opponent != "" {
		h := ComputeHeadToHead(filter.Team, filter.Opponent, matches)
		fmt.Fprintf(&b, "\nHead-to-head: %s %dW, %s %dW, %d draws (goals %d-%d).\n",
			filter.Team, h.AWins, filter.Opponent, h.BWins, h.Draws, h.AGoals, h.BGoals)
	}
	return b.String(), false
}

func (s *Server) handleTeamStats(args map[string]any) (string, bool) {
	team := argString(args, "team")
	if team == "" {
		return "Argument 'team' is required.", true
	}
	homeOnly, _ := args["home_only"].(bool)
	awayOnly, _ := args["away_only"].(bool)
	filter := MatchFilter{
		Team:        team,
		Season:      argInt(args, "season"),
		Competition: argString(args, "competition"),
	}
	matches := s.ds.FindMatches(filter)
	if len(matches) == 0 {
		return fmt.Sprintf("No matches found for %s with the given filters.", team), false
	}
	stats := ComputeTeamStats(team, matches, homeOnly, awayOnly)
	var b strings.Builder
	scope := []string{team}
	if filter.Season != 0 {
		scope = append(scope, fmt.Sprintf("season %d", filter.Season))
	}
	if filter.Competition != "" {
		scope = append(scope, filter.Competition)
	}
	if homeOnly {
		scope = append(scope, "home")
	}
	if awayOnly {
		scope = append(scope, "away")
	}
	fmt.Fprintf(&b, "%s record:\n", strings.Join(scope, ", "))
	fmt.Fprintf(&b, "- Matches: %d\n", stats.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", stats.Wins, stats.Draws, stats.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n",
		stats.GoalsFor, stats.GoalsAgainst, stats.GoalsFor-stats.GoalsAgainst)
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", stats.WinRate())
	fmt.Fprintf(&b, "- Points (3W/1D): %d\n", stats.Points)
	return b.String(), false
}

func (s *Server) handleHeadToHead(args map[string]any) (string, bool) {
	a := argString(args, "team_a")
	bTeam := argString(args, "team_b")
	if a == "" || bTeam == "" {
		return "Arguments 'team_a' and 'team_b' are required.", true
	}
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 20
	}
	filter := MatchFilter{
		Team:        a,
		Opponent:    bTeam,
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
	}
	matches := s.ds.FindMatches(filter)
	h := ComputeHeadToHead(a, bTeam, matches)
	if h.Matches == 0 {
		return fmt.Sprintf("No %s vs %s matches found.", a, bTeam), false
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s head-to-head:\n", a, bTeam)
	fmt.Fprintf(&b, "- Matches: %d\n", h.Matches)
	fmt.Fprintf(&b, "- %s wins: %d, %s wins: %d, Draws: %d\n", a, h.AWins, bTeam, h.BWins, h.Draws)
	fmt.Fprintf(&b, "- Goals: %s %d - %d %s\n", a, h.AGoals, h.BGoals, bTeam)
	show := h.MatchList
	if len(show) > limit {
		show = show[:limit]
	}
	if len(show) > 0 {
		fmt.Fprintf(&b, "\nRecent matches:\n")
		for _, m := range show {
			fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
		}
	}
	return b.String(), false
}

func (s *Server) handleStandings(args map[string]any) (string, bool) {
	season := argInt(args, "season")
	if season == 0 {
		return "Argument 'season' is required.", true
	}
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 20
	}
	competition := argString(args, "competition")
	if competition == "" {
		competition = "Brasileirão"
	}
	matches := s.ds.FindMatches(MatchFilter{Competition: competition, Season: season})
	if len(matches) == 0 {
		return fmt.Sprintf("No matches found for %s %d.", competition, season), false
	}
	table := Standings(matches)
	if len(table) > limit {
		table = table[:limit]
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d standings (computed from %d matches):\n", competition, season, len(matches))
	fmt.Fprintf(&b, "%-4s %-30s %-5s %-3s %-3s %-3s %-5s %-3s\n", "Pos", "Team", "Pts", "W", "D", "L", "GF:GA", "GD")
	for i, row := range table {
		fmt.Fprintf(&b, "%-4d %-30s %-5d %-3d %-3d %-3d %d:%d   %+d\n",
			i+1, truncate(row.Team, 30), row.Points, row.Wins, row.Draws, row.Losses,
			row.GoalsFor, row.GoalsAgainst, row.GoalDifference)
	}
	return b.String(), false
}

func (s *Server) handleSearchPlayers(args map[string]any) (string, bool) {
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 25
	}
	filter := PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		Limit:       limit,
	}
	players := s.ds.FindPlayers(filter)
	if len(players) == 0 {
		return "No players found.", false
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s):\n", len(players))
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s — Overall: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
			i+1, p.Name, p.Overall, p.Position, p.Club, p.Nationality, p.Age)
	}
	return b.String(), false
}

func (s *Server) handleBiggestWins(args map[string]any) (string, bool) {
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 10
	}
	competition := argString(args, "competition")
	season := argInt(args, "season")
	matches := s.ds.BiggestWins(competition, season, limit)
	if len(matches) == 0 {
		return "No matches found with those filters.", false
	}
	var b strings.Builder
	title := "Biggest victories"
	if competition != "" {
		title += " in " + competition
	}
	if season != 0 {
		title += fmt.Sprintf(" %d", season)
	}
	fmt.Fprintf(&b, "%s:\n", title)
	for i, m := range matches {
		margin := abs(m.HomeGoals - m.AwayGoals)
		fmt.Fprintf(&b, "%d. %s (margin %d)\n", i+1, FormatMatch(m), margin)
	}
	return b.String(), false
}

func (s *Server) handleCompetitionSummary(args map[string]any) (string, bool) {
	competition := argString(args, "competition")
	season := argInt(args, "season")
	matches := s.ds.FindMatches(MatchFilter{Competition: competition, Season: season})
	if len(matches) == 0 {
		return "No matches found for that competition/season.", false
	}
	var b strings.Builder
	scope := []string{}
	if competition != "" {
		scope = append(scope, competition)
	}
	if season != 0 {
		scope = append(scope, fmt.Sprintf("%d", season))
	}
	if len(scope) == 0 {
		scope = append(scope, "All matches")
	}
	totalGoals := 0
	for _, m := range matches {
		totalGoals += m.HomeGoals + m.AwayGoals
	}
	fmt.Fprintf(&b, "%s summary:\n", strings.Join(scope, " "))
	fmt.Fprintf(&b, "- Matches: %d\n", len(matches))
	fmt.Fprintf(&b, "- Total goals: %d\n", totalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", AverageGoals(matches))
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", HomeWinRate(matches))
	return b.String(), false
}

func (s *Server) handleDatasetInfo(args map[string]any) (string, bool) {
	competitions := map[string]int{}
	seasons := map[int]bool{}
	var minSeason, maxSeason int
	for _, m := range s.ds.Matches {
		competitions[m.Competition]++
		if m.Season > 0 {
			seasons[m.Season] = true
			if minSeason == 0 || m.Season < minSeason {
				minSeason = m.Season
			}
			if m.Season > maxSeason {
				maxSeason = m.Season
			}
		}
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Brazilian Soccer dataset:\n")
	fmt.Fprintf(&b, "- Matches: %d\n", len(s.ds.Matches))
	fmt.Fprintf(&b, "- Players: %d\n", len(s.ds.Players))
	if minSeason > 0 {
		fmt.Fprintf(&b, "- Season range: %d-%d (%d seasons)\n", minSeason, maxSeason, len(seasons))
	}
	fmt.Fprintf(&b, "- Competitions:\n")
	for name, n := range competitions {
		fmt.Fprintf(&b, "  - %s: %d matches\n", name, n)
	}
	return b.String(), false
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	if n <= 1 {
		return s[:n]
	}
	return s[:n-1] + "…"
}
