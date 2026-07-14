package mcp

import (
	"fmt"
	"math"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/soccer"
)

// argument coercion helpers -------------------------------------------------

func argString(args map[string]any, key string) string {
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return strings.TrimSpace(s)
		}
	}
	return ""
}

func argInt(args map[string]any, key string) int {
	switch v := args[key].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case string:
		var n int
		fmt.Sscanf(strings.TrimSpace(v), "%d", &n)
		return n
	}
	return 0
}

func argDate(args map[string]any, key string) time.Time {
	s := argString(args, key)
	if s == "" {
		return time.Time{}
	}
	for _, layout := range []string{"2006-01-02", "2006-01-02 15:04:05", "02/01/2006"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// schema builders -----------------------------------------------------------

func obj(props map[string]any, required ...string) map[string]any {
	m := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		m["required"] = required
	}
	return m
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}
func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

// registerTools defines the advertised tools and their handlers.
func (s *Server) registerTools() {
	add := func(name, desc string, schema map[string]any, h func(map[string]any) ToolResult) {
		s.tools = append(s.tools, Tool{Name: name, Description: desc, InputSchema: schema})
		s.handlers[name] = h
	}

	add("search_matches",
		"Find soccer matches by team, opponent, competition, season and/or date range. "+
			"Returns matches most-recent first. Handles team name variations (e.g. 'sao paulo' matches 'São Paulo-SP').",
		obj(map[string]any{
			"team":        strProp("Team name; matches whether the team played home or away."),
			"home_team":   strProp("Restrict to matches where this team played at home."),
			"away_team":   strProp("Restrict to matches where this team played away."),
			"opponent":    strProp("Combined with 'team', restricts to head-to-head fixtures."),
			"competition": strProp("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
			"season":      intProp("Season/year, e.g. 2019."),
			"from":        strProp("Start date (inclusive), format YYYY-MM-DD."),
			"to":          strProp("End date (inclusive), format YYYY-MM-DD."),
			"limit":       intProp("Maximum matches to return (default 20)."),
		}),
		s.handleSearchMatches)

	add("head_to_head",
		"Summarise the all-time head-to-head record between two teams (wins, draws, goals, last meeting).",
		obj(map[string]any{
			"team_a": strProp("First team."),
			"team_b": strProp("Second team."),
		}, "team_a", "team_b"),
		s.handleHeadToHead)

	add("team_record",
		"Aggregate a team's record (played, W/D/L, goals for/against, points, win rate), "+
			"optionally scoped to a competition, season and venue (home/away).",
		obj(map[string]any{
			"team":        strProp("Team name."),
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season/year filter."),
			"venue":       strProp("Optional venue: 'home', 'away', or 'all' (default)."),
		}, "team"),
		s.handleTeamRecord)

	add("standings",
		"Compute a league table for a competition and season from match results, "+
			"with the usual points and goal-difference tie-breakers.",
		obj(map[string]any{
			"competition": strProp("Competition, e.g. 'Brasileirão' (default) or 'Libertadores'."),
			"season":      intProp("Season/year, e.g. 2019."),
			"limit":       intProp("Maximum rows to return (default: full table)."),
		}, "season"),
		s.handleStandings)

	add("search_players",
		"Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. "+
			"Results are sorted by overall rating (highest first).",
		obj(map[string]any{
			"name":        strProp("Full or partial player name."),
			"nationality": strProp("Nationality, e.g. 'Brazil'."),
			"club":        strProp("Club name, e.g. 'Flamengo'."),
			"position":    strProp("Position code, e.g. 'ST', 'GK', 'CB'."),
			"min_overall": intProp("Minimum FIFA overall rating."),
			"limit":       intProp("Maximum players to return (default 20)."),
		}),
		s.handleSearchPlayers)

	add("match_statistics",
		"Compute aggregate statistics over a set of matches (average goals per game, home win rate, "+
			"home/away wins, biggest wins). Accepts the same filters as search_matches.",
		obj(map[string]any{
			"team":        strProp("Optional team filter."),
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season/year filter."),
			"from":        strProp("Optional start date, YYYY-MM-DD."),
			"to":          strProp("Optional end date, YYYY-MM-DD."),
		}),
		s.handleStatistics)

	add("data_overview",
		"Report what data is loaded: match and player counts, available competitions and season range, "+
			"plus any load warnings.",
		obj(map[string]any{}),
		s.handleOverview)
}

// handlers ------------------------------------------------------------------

func (s *Server) handleSearchMatches(args map[string]any) ToolResult {
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 20
	}
	f := soccer.MatchFilter{
		Team:        argString(args, "team"),
		HomeTeam:    argString(args, "home_team"),
		AwayTeam:    argString(args, "away_team"),
		Opponent:    argString(args, "opponent"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		From:        argDate(args, "from"),
		To:          argDate(args, "to"),
		Limit:       limit,
	}
	matches := s.store.FindMatches(f)
	if len(matches) == 0 {
		return textResult("No matches found for the given criteria.")
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es)", len(matches))
	if f.Limit > 0 && len(matches) == f.Limit {
		fmt.Fprintf(&b, " (showing first %d)", f.Limit)
	}
	b.WriteString(":\n")
	for _, m := range matches {
		b.WriteString("- " + formatMatch(m) + "\n")
	}
	return textResult(strings.TrimRight(b.String(), "\n"))
}

func (s *Server) handleHeadToHead(args map[string]any) ToolResult {
	a := argString(args, "team_a")
	bteam := argString(args, "team_b")
	if a == "" || bteam == "" {
		return errorResult("both team_a and team_b are required")
	}
	h := s.store.HeadToHead(a, bteam)
	if h.Matches == 0 {
		return textResult(fmt.Sprintf("No recorded matches between %s and %s.", h.TeamA, h.TeamB))
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head: %s vs %s\n", h.TeamA, h.TeamB)
	fmt.Fprintf(&b, "- Matches: %d\n", h.Matches)
	fmt.Fprintf(&b, "- %s wins: %d, %s wins: %d, Draws: %d\n", h.TeamA, h.WinsA, h.TeamB, h.WinsB, h.Draws)
	fmt.Fprintf(&b, "- Goals: %s %d - %d %s\n", h.TeamA, h.GoalsA, h.GoalsB, h.TeamB)
	if h.LastMeeting != nil {
		fmt.Fprintf(&b, "- Last meeting: %s", formatMatch(*h.LastMeeting))
	}
	return textResult(strings.TrimRight(b.String(), "\n"))
}

func (s *Server) handleTeamRecord(args map[string]any) ToolResult {
	team := argString(args, "team")
	if team == "" {
		return errorResult("team is required")
	}
	rec := s.store.TeamRecord(team, soccer.TeamRecordOptions{
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		Venue:       argString(args, "venue"),
	})
	if rec.Played == 0 {
		return textResult(fmt.Sprintf("No matches found for %s under the given filters.", rec.Team))
	}
	scope := describeScope(rec.Competition, rec.Season, rec.Venue)
	var b strings.Builder
	fmt.Fprintf(&b, "%s record%s:\n", rec.Team, scope)
	fmt.Fprintf(&b, "- Matches: %d\n", rec.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", rec.Wins, rec.Draws, rec.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", rec.GoalsFor, rec.GoalsAgainst)
	fmt.Fprintf(&b, "- Points: %d\n", rec.Points)
	fmt.Fprintf(&b, "- Win rate: %.1f%%", rec.WinRate()*100)
	return textResult(b.String())
}

func (s *Server) handleStandings(args map[string]any) ToolResult {
	season := argInt(args, "season")
	if season == 0 {
		return errorResult("season is required")
	}
	comp := argString(args, "competition")
	if comp == "" {
		comp = "Brasileirão"
	}
	table := s.store.Standings(comp, season)
	if len(table) == 0 {
		return textResult(fmt.Sprintf("No standings available for %s %d.", comp, season))
	}
	limit := argInt(args, "limit")
	if limit > 0 && limit < len(table) {
		table = table[:limit]
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d standings (calculated from matches):\n", comp, season)
	for _, r := range table {
		fmt.Fprintf(&b, "%2d. %-24s %3d pts (%dW %dD %dL, GF %d GA %d, GD %+d)\n",
			r.Position, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff)
	}
	return textResult(strings.TrimRight(b.String(), "\n"))
}

func (s *Server) handleSearchPlayers(args map[string]any) ToolResult {
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 20
	}
	f := soccer.PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		Limit:       limit,
	}
	players := s.store.FindPlayers(f)
	if len(players) == 0 {
		return textResult("No players found for the given criteria.")
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s):\n", len(players))
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
			i+1, p.Name, p.Overall, orDash(p.Position), orDash(p.Club), orDash(p.Nationality), p.Age)
	}
	return textResult(strings.TrimRight(b.String(), "\n"))
}

func (s *Server) handleStatistics(args map[string]any) ToolResult {
	f := soccer.MatchFilter{
		Team:        argString(args, "team"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		From:        argDate(args, "from"),
		To:          argDate(args, "to"),
	}
	st := s.store.Stats(f, 5)
	if st.Matches == 0 {
		return textResult("No matches found for the given criteria.")
	}
	var b strings.Builder
	b.WriteString("Statistics" + describeScope(f.Competition, f.Season, "") + ":\n")
	fmt.Fprintf(&b, "- Matches: %d\n", st.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", st.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", round2(st.AvgGoalsPerGame))
	fmt.Fprintf(&b, "- Home wins: %d, Away wins: %d, Draws: %d\n", st.HomeWins, st.AwayWins, st.Draws)
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", st.HomeWinRate*100)
	if len(st.BiggestWins) > 0 {
		b.WriteString("- Biggest wins:\n")
		for _, m := range st.BiggestWins {
			b.WriteString("  * " + formatMatch(m) + "\n")
		}
	}
	return textResult(strings.TrimRight(b.String(), "\n"))
}

func (s *Server) handleOverview(args map[string]any) ToolResult {
	seasons := s.store.Seasons()
	var b strings.Builder
	b.WriteString("Brazilian Soccer MCP — data overview:\n")
	fmt.Fprintf(&b, "- Matches loaded: %d\n", len(s.store.Matches))
	fmt.Fprintf(&b, "- Players loaded: %d\n", len(s.store.Players))
	fmt.Fprintf(&b, "- Teams: %d\n", len(s.store.Teams()))
	fmt.Fprintf(&b, "- Competitions: %s\n", strings.Join(s.store.Competitions(), ", "))
	if len(seasons) > 0 {
		fmt.Fprintf(&b, "- Seasons: %d–%d\n", seasons[0], seasons[len(seasons)-1])
	}
	if len(s.store.Warnings) > 0 {
		b.WriteString("- Warnings:\n")
		for _, w := range s.store.Warnings {
			b.WriteString("  * " + w + "\n")
		}
	}
	return textResult(strings.TrimRight(b.String(), "\n"))
}

// formatting helpers --------------------------------------------------------

func formatMatch(m soccer.Match) string {
	date := "unknown date"
	if !m.Date.IsZero() {
		date = m.Date.Format("2006-01-02")
	}
	score := fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	if !m.Decided() {
		score = "?-?"
	}
	line := fmt.Sprintf("%s: %s %s %s (%s", date, m.HomeTeam, score, m.AwayTeam, m.Competition)
	if m.Season > 0 {
		line += fmt.Sprintf(" %d", m.Season)
	}
	if m.Round != "" {
		line += " Round " + m.Round
	}
	if m.Stage != "" {
		line += " " + m.Stage
	}
	line += ")"
	return line
}

func describeScope(comp string, season int, venue string) string {
	var parts []string
	if venue != "" && venue != "all" {
		parts = append(parts, "("+venue+")")
	}
	if comp != "" {
		parts = append(parts, comp)
	}
	if season != 0 {
		parts = append(parts, fmt.Sprintf("%d", season))
	}
	if len(parts) == 0 {
		return ""
	}
	return " " + strings.Join(parts, " ")
}

func orDash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}

func round2(f float64) float64 { return math.Round(f*100) / 100 }
