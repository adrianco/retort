// MCP tool definitions. Each tool exposes one family of soccer queries, parses
// its JSON arguments and renders a human-readable text answer for the LLM.
package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Tool couples an MCP tool description with its handler.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(*DB, map[string]any) (string, error)
}

func strSchema(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}

func intSchema(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

func objectSchema(props map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

// allTools returns the registered MCP tools.
func allTools() []Tool {
	return []Tool{
		{
			Name: "find_matches",
			Description: "Find soccer matches by team, opponent, competition, season, venue or date range. " +
				"Returns matches newest first. When both team and opponent are given a head-to-head summary is appended.",
			InputSchema: objectSchema(map[string]any{
				"team":        strSchema("Team name (handles state suffixes and accents, e.g. 'Flamengo')."),
				"opponent":    strSchema("Optional opponent team name to restrict to matches between the two teams."),
				"competition": strSchema("Optional competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
				"season":      intSchema("Optional season year, e.g. 2019."),
				"venue":       map[string]any{"type": "string", "enum": []string{"home", "away", "any"}, "description": "Restrict the team's matches to home or away."},
				"date_from":   strSchema("Optional start date (YYYY-MM-DD)."),
				"date_to":     strSchema("Optional end date (YYYY-MM-DD)."),
				"limit":       intSchema("Maximum matches to list (default 20, max 100)."),
			}),
			Handler: toolFindMatches,
		},
		{
			Name:        "head_to_head",
			Description: "Compute the head-to-head record between two teams: matches played, wins, draws and goals.",
			InputSchema: objectSchema(map[string]any{
				"team_a":      strSchema("First team name."),
				"team_b":      strSchema("Second team name."),
				"competition": strSchema("Optional competition filter."),
				"season":      intSchema("Optional season year."),
			}, "team_a", "team_b"),
			Handler: toolHeadToHead,
		},
		{
			Name:        "team_stats",
			Description: "Summarize a team's record (matches, wins, draws, losses, goals, points, win rate), optionally filtered by competition, season and venue.",
			InputSchema: objectSchema(map[string]any{
				"team":        strSchema("Team name."),
				"competition": strSchema("Optional competition filter."),
				"season":      intSchema("Optional season year."),
				"venue":       map[string]any{"type": "string", "enum": []string{"home", "away", "any"}, "description": "Restrict to home or away matches."},
			}, "team"),
			Handler: toolTeamStats,
		},
		{
			Name:        "competition_standings",
			Description: "Calculate the full league table for a competition and season from match results, including the champion.",
			InputSchema: objectSchema(map[string]any{
				"competition": strSchema("Competition name (defaults to 'Brasileirão Série A')."),
				"season":      intSchema("Season year, e.g. 2019."),
			}, "season"),
			Handler: toolStandings,
		},
		{
			Name:        "match_statistics",
			Description: "Aggregate statistics over matches: average goals per match, home/away win rates, draw rate and the biggest victories.",
			InputSchema: objectSchema(map[string]any{
				"competition": strSchema("Optional competition filter."),
				"season":      intSchema("Optional season year."),
				"top_n":       intSchema("How many biggest wins to list (default 5)."),
			}),
			Handler: toolMatchStatistics,
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality, club, position or minimum overall rating. Useful for finding Brazilian players or players at Brazilian clubs.",
			InputSchema: objectSchema(map[string]any{
				"name":        strSchema("Player name substring."),
				"nationality": strSchema("Nationality filter, e.g. 'Brazil'."),
				"club":        strSchema("Club name substring, e.g. 'Flamengo'."),
				"position":    strSchema("Position filter, e.g. 'ST', 'GK', 'CB'."),
				"min_overall": intSchema("Minimum FIFA overall rating."),
				"sort_by":     map[string]any{"type": "string", "enum": []string{"overall", "potential", "age", "name"}, "description": "Sort order (default 'overall')."},
				"limit":       intSchema("Maximum players to list (default 20, max 100)."),
			}),
			Handler: toolSearchPlayers,
		},
		{
			Name:        "list_competitions",
			Description: "List the competitions available in the dataset with their match counts and season ranges.",
			InputSchema: objectSchema(map[string]any{}),
			Handler:     toolListCompetitions,
		},
	}
}

var toolByName = func() map[string]Tool {
	m := map[string]Tool{}
	for _, t := range allTools() {
		m[t.Name] = t
	}
	return m
}()

// toolSchemas renders the tool list for the MCP tools/list response.
func toolSchemas() []map[string]any {
	tools := allTools()
	out := make([]map[string]any, 0, len(tools))
	for _, t := range tools {
		out = append(out, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return out
}

// --- argument helpers --------------------------------------------------------

func argStr(a map[string]any, key string) string {
	if a == nil {
		return ""
	}
	switch v := a[key].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	}
	return ""
}

func argInt(a map[string]any, key string) (int, bool) {
	if a == nil {
		return 0, false
	}
	switch v := a[key].(type) {
	case float64:
		return int(v), true
	case string:
		v = strings.TrimSpace(v)
		if v == "" {
			return 0, false
		}
		if i, err := strconv.Atoi(v); err == nil {
			return i, true
		}
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			return int(f), true
		}
	}
	return 0, false
}

func argDate(a map[string]any, key string) (time.Time, bool) {
	s := argStr(a, key)
	if s == "" {
		return time.Time{}, false
	}
	return parseDate(s)
}

// --- formatting helpers ------------------------------------------------------

func matchLine(m Match) string {
	date := "????-??-??"
	if m.HasDate {
		date = m.Date.Format("2006-01-02")
	}
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoal, m.AwayGoal)
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", date, m.HomeTeam, score, m.AwayTeam, matchContext(m))
}

func matchContext(m Match) string {
	s := m.Competition
	if m.Season > 0 {
		s += " " + strconv.Itoa(m.Season)
	}
	if m.Round != "" {
		s += ", Round " + m.Round
	}
	if m.Stage != "" {
		s += ", " + m.Stage
	}
	return s
}

func trunc(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	if n <= 1 {
		return string(r[:n])
	}
	return string(r[:n-1]) + "…"
}

func scopeSuffix(competition string, season int, hasSeason bool) string {
	var parts []string
	if competition != "" {
		parts = append(parts, competition)
	}
	if hasSeason {
		parts = append(parts, "season "+strconv.Itoa(season))
	}
	if len(parts) == 0 {
		return ""
	}
	return " (" + strings.Join(parts, ", ") + ")"
}

// --- tool handlers -----------------------------------------------------------

func toolFindMatches(db *DB, a map[string]any) (string, error) {
	f := MatchFilter{
		Team:        argStr(a, "team"),
		Opponent:    argStr(a, "opponent"),
		Competition: argStr(a, "competition"),
		Venue:       argStr(a, "venue"),
	}
	if s, ok := argInt(a, "season"); ok {
		f.Season, f.HasSeason = s, true
	}
	if d, ok := argDate(a, "date_from"); ok {
		f.DateFrom = d
	}
	if d, ok := argDate(a, "date_to"); ok {
		f.DateTo = d
	}
	limit := 20
	if l, ok := argInt(a, "limit"); ok && l > 0 {
		limit = l
	}
	if limit > 100 {
		limit = 100
	}

	matches := db.FindMatches(f)
	var b strings.Builder
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}
	fmt.Fprintf(&b, "Found %d match(es)%s.\n", len(matches), describeMatchFilter(f))
	shown := matches
	if len(shown) > limit {
		shown = shown[:limit]
		fmt.Fprintf(&b, "Showing the %d most recent:\n", len(shown))
	}
	b.WriteString("\n")
	for _, m := range shown {
		fmt.Fprintf(&b, "- %s\n", matchLine(m))
	}
	if f.Team != "" && f.Opponent != "" {
		h := db.HeadToHead(f.Team, f.Opponent, f.Competition, f.Season, f.HasSeason)
		fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d win(s), %s %d win(s), %d draw(s).\n",
			h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
	}
	return b.String(), nil
}

func describeMatchFilter(f MatchFilter) string {
	var parts []string
	switch {
	case f.Team != "" && f.Opponent != "":
		parts = append(parts, "for "+f.Team+" vs "+f.Opponent)
	case f.Team != "":
		parts = append(parts, "for "+f.Team)
	}
	if f.Venue == "home" || f.Venue == "away" {
		parts = append(parts, "("+f.Venue+")")
	}
	if f.Competition != "" {
		parts = append(parts, "in "+f.Competition)
	}
	if f.HasSeason {
		parts = append(parts, "season "+strconv.Itoa(f.Season))
	}
	if len(parts) == 0 {
		return ""
	}
	return " " + strings.Join(parts, " ")
}

func toolHeadToHead(db *DB, a map[string]any) (string, error) {
	teamA := argStr(a, "team_a")
	teamB := argStr(a, "team_b")
	if teamA == "" || teamB == "" {
		return "", fmt.Errorf("team_a and team_b are required")
	}
	competition := argStr(a, "competition")
	season, hasSeason := argInt(a, "season")
	h := db.HeadToHead(teamA, teamB, competition, season, hasSeason)
	scope := scopeSuffix(competition, season, hasSeason)
	if len(h.Matches) == 0 {
		return fmt.Sprintf("No matches found between %s and %s%s.", h.TeamA, h.TeamB, scope), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head: %s vs %s%s\n\n", h.TeamA, h.TeamB, scope)
	fmt.Fprintf(&b, "Matches played: %d\n", len(h.Matches))
	fmt.Fprintf(&b, "%s wins: %d\n", h.TeamA, h.AWins)
	fmt.Fprintf(&b, "%s wins: %d\n", h.TeamB, h.BWins)
	fmt.Fprintf(&b, "Draws: %d\n", h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d - %d %s\n\n", h.TeamA, h.AGoals, h.BGoals, h.TeamB)
	b.WriteString("Meetings (newest first):\n")
	for i, m := range h.Matches {
		if i >= 20 {
			fmt.Fprintf(&b, "... and %d more.\n", len(h.Matches)-20)
			break
		}
		fmt.Fprintf(&b, "- %s\n", matchLine(m))
	}
	return b.String(), nil
}

func toolTeamStats(db *DB, a map[string]any) (string, error) {
	team := argStr(a, "team")
	if team == "" {
		return "", fmt.Errorf("team is required")
	}
	competition := argStr(a, "competition")
	season, hasSeason := argInt(a, "season")
	venue := argStr(a, "venue")
	s := db.ComputeTeamStats(team, competition, season, hasSeason, venue)

	var b strings.Builder
	title := s.Team + " record"
	if venue == "home" || venue == "away" {
		title = s.Team + " " + venue + " record"
	}
	fmt.Fprintf(&b, "%s%s\n\n", title, scopeSuffix(competition, season, hasSeason))
	if s.Played == 0 {
		b.WriteString("No matches with a recorded score found for these criteria.")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "Matches: %d\n", s.Played)
	fmt.Fprintf(&b, "Wins: %d, Draws: %d, Losses: %d\n", s.Wins, s.Draws, s.Losses)
	fmt.Fprintf(&b, "Goals For: %d, Goals Against: %d (difference %+d)\n",
		s.GoalsFor, s.GoalsAgst, s.GoalsFor-s.GoalsAgst)
	fmt.Fprintf(&b, "Points: %d\n", s.Points())
	fmt.Fprintf(&b, "Win rate: %.1f%%\n", s.WinRate())
	return b.String(), nil
}

func toolStandings(db *DB, a map[string]any) (string, error) {
	season, hasSeason := argInt(a, "season")
	if !hasSeason {
		return "", fmt.Errorf("season is required")
	}
	competition := resolveCompetition(argStr(a, "competition"))
	if competition == "" {
		competition = "Brasileirão Série A"
	}
	table := db.Standings(competition, season)
	if len(table) == 0 {
		return fmt.Sprintf("No matches found for %s in %d. "+
			"Try list_competitions to see available competitions and seasons.",
			competition, season), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d — Final Standings (calculated from match results)\n\n", competition, season)
	fmt.Fprintf(&b, "%-4s %-26s %4s %4s %4s %4s %4s %4s %5s %5s\n",
		"Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts")
	for i, r := range table {
		fmt.Fprintf(&b, "%-4d %-26s %4d %4d %4d %4d %4d %4d %+5d %5d\n",
			i+1, trunc(r.Team, 26), r.Played, r.Wins, r.Draws, r.Losses,
			r.GoalsFor, r.GoalsAgst, r.GoalDiff(), r.Points())
	}
	fmt.Fprintf(&b, "\nChampion: %s (%d pts)\n", table[0].Team, table[0].Points())
	return b.String(), nil
}

func toolMatchStatistics(db *DB, a map[string]any) (string, error) {
	competition := argStr(a, "competition")
	season, hasSeason := argInt(a, "season")
	topN, _ := argInt(a, "top_n")
	agg := db.ComputeAggStats(competition, season, hasSeason, topN)
	if agg.Matches == 0 {
		return fmt.Sprintf("No matches found%s.", scopeSuffix(competition, season, hasSeason)), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Match statistics%s\n\n", scopeSuffix(competition, season, hasSeason))
	fmt.Fprintf(&b, "Total matches: %d (%d with recorded scores)\n", agg.Matches, agg.Scored)
	fmt.Fprintf(&b, "Total goals: %d\n", agg.TotalGoals)
	fmt.Fprintf(&b, "Average goals per match: %.2f\n", agg.AvgGoals())
	fmt.Fprintf(&b, "Home win rate: %.1f%%\n", agg.HomeWinRate())
	fmt.Fprintf(&b, "Away win rate: %.1f%%\n", agg.AwayWinRate())
	fmt.Fprintf(&b, "Draw rate: %.1f%%\n", agg.DrawRate())
	if len(agg.BiggestWins) > 0 {
		b.WriteString("\nBiggest victories:\n")
		for i, m := range agg.BiggestWins {
			fmt.Fprintf(&b, "%d. %s\n", i+1, matchLine(m))
		}
	}
	return b.String(), nil
}

func toolSearchPlayers(db *DB, a map[string]any) (string, error) {
	f := PlayerFilter{
		Name:        argStr(a, "name"),
		Nationality: argStr(a, "nationality"),
		Club:        argStr(a, "club"),
		Position:    argStr(a, "position"),
		SortBy:      argStr(a, "sort_by"),
	}
	if mo, ok := argInt(a, "min_overall"); ok {
		f.MinOverall = mo
	}
	limit := 20
	if l, ok := argInt(a, "limit"); ok && l > 0 {
		limit = l
	}
	if limit > 100 {
		limit = 100
	}

	all := db.SearchPlayers(f)
	if len(all) == 0 {
		return "No players found for the given criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s)%s.\n", len(all), describePlayerFilter(f))

	total := 0
	for _, p := range all {
		total += p.Overall
	}
	fmt.Fprintf(&b, "Average overall rating: %.1f\n\n", float64(total)/float64(len(all)))

	shown := all
	if len(shown) > limit {
		shown = shown[:limit]
		fmt.Fprintf(&b, "Showing top %d:\n", len(shown))
	}
	for i, p := range shown {
		club := p.Club
		if club == "" {
			club = "(no club)"
		}
		fmt.Fprintf(&b, "%d. %s — Overall: %d, Potential: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
			i+1, p.Name, p.Overall, p.Potential, dash(p.Position), club, dash(p.Nationality), p.Age)
	}

	if f.Nationality != "" {
		appendClubBreakdown(&b, all)
	}
	return b.String(), nil
}

func dash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

func describePlayerFilter(f PlayerFilter) string {
	var parts []string
	if f.Name != "" {
		parts = append(parts, "named like '"+f.Name+"'")
	}
	if f.Nationality != "" {
		parts = append(parts, "from "+f.Nationality)
	}
	if f.Club != "" {
		parts = append(parts, "at clubs matching '"+f.Club+"'")
	}
	if f.Position != "" {
		parts = append(parts, "position "+f.Position)
	}
	if f.MinOverall > 0 {
		parts = append(parts, "overall >= "+strconv.Itoa(f.MinOverall))
	}
	if len(parts) == 0 {
		return ""
	}
	return " " + strings.Join(parts, ", ")
}

// appendClubBreakdown lists how the filtered players are distributed across
// clubs, with average rating per club.
func appendClubBreakdown(b *strings.Builder, players []Player) {
	type agg struct {
		count int
		total int
	}
	byClub := map[string]*agg{}
	for _, p := range players {
		club := p.Club
		if club == "" {
			continue
		}
		a := byClub[club]
		if a == nil {
			a = &agg{}
			byClub[club] = a
		}
		a.count++
		a.total += p.Overall
	}
	if len(byClub) == 0 {
		return
	}
	type row struct {
		club  string
		count int
		avg   float64
	}
	rows := make([]row, 0, len(byClub))
	for club, a := range byClub {
		rows = append(rows, row{club, a.count, float64(a.total) / float64(a.count)})
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].count != rows[j].count {
			return rows[i].count > rows[j].count
		}
		return rows[i].club < rows[j].club
	})
	b.WriteString("\nPlayers per club:\n")
	for i, r := range rows {
		if i >= 15 {
			fmt.Fprintf(b, "... and %d more clubs.\n", len(rows)-15)
			break
		}
		fmt.Fprintf(b, "- %s: %d player(s), avg rating %.0f\n", r.club, r.count, r.avg)
	}
}

func toolListCompetitions(db *DB, _ map[string]any) (string, error) {
	comps := db.Competitions()
	var b strings.Builder
	fmt.Fprintf(&b, "Dataset overview: %d matches (deduplicated), %d raw match rows, %d players.\n\n",
		len(db.Matches), len(db.AllMatches), len(db.Players))
	b.WriteString("Competitions:\n")
	for _, c := range comps {
		fmt.Fprintf(&b, "- %s: %d matches", c.Name, c.Matches)
		if c.MinSeason > 0 {
			if c.MinSeason == c.MaxSeason {
				fmt.Fprintf(&b, ", season %d", c.MinSeason)
			} else {
				fmt.Fprintf(&b, ", seasons %d-%d", c.MinSeason, c.MaxSeason)
			}
		}
		b.WriteString("\n")
	}
	return b.String(), nil
}
