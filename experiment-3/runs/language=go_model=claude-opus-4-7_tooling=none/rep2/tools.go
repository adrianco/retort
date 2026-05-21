// tools.go defines the MCP tools exposed by the server: their JSON-Schema
// input definitions and the handlers that turn arguments into human-readable
// answers. Handlers delegate all real work to the query layer in query.go.
package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// Tool is a single MCP tool: a name, description, input schema and handler.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(args map[string]any) (string, error)
}

// --- argument helpers -------------------------------------------------------

func argString(args map[string]any, key string) string {
	v, ok := args[key]
	if !ok || v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return strings.TrimSpace(s)
	}
	return strings.TrimSpace(fmt.Sprintf("%v", v))
}

func argInt(args map[string]any, key string) int {
	v, ok := args[key]
	if !ok || v == nil {
		return 0
	}
	switch x := v.(type) {
	case float64:
		return int(x)
	case int:
		return x
	case string:
		n, _ := strconv.Atoi(strings.TrimSpace(x))
		return n
	default:
		return 0
	}
}

// --- schema helpers ---------------------------------------------------------

func prop(typ, desc string) map[string]any {
	return map[string]any{"type": typ, "description": desc}
}

func schema(props map[string]any, required ...string) map[string]any {
	m := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		m["required"] = required
	}
	return m
}

// --- formatting helpers -----------------------------------------------------

// describeMatch renders one match as a single human-readable line.
func describeMatch(m Match) string {
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoal, m.AwayGoal)
	}
	ctx := m.Competition
	switch {
	case m.Stage != "":
		ctx += ", " + m.Stage
	case m.Round != "":
		ctx += ", Round " + m.Round
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", m.DateLabel(), m.HomeTeam, score, m.AwayTeam, ctx)
}

func pct(v float64) string { return fmt.Sprintf("%.1f%%", v) }

// --- tool registry ----------------------------------------------------------

// BuildTools constructs every MCP tool bound to the given data store.
func BuildTools(store *DataStore) []Tool {
	return []Tool{
		{
			Name: "search_matches",
			Description: "Search Brazilian soccer matches by team, opponent, competition, " +
				"season or date range. Covers Brasileirão, Copa do Brasil and Copa Libertadores.",
			InputSchema: schema(map[string]any{
				"team":        prop("string", "Team name; matches as home or away (e.g. 'Flamengo')."),
				"opponent":    prop("string", "Optional opponent team name to list a specific fixture."),
				"competition": prop("string", "Optional competition: Brasileirão, Copa do Brasil or Libertadores."),
				"season":      prop("integer", "Optional season year (e.g. 2019)."),
				"venue":       prop("string", "Restrict team side: 'home', 'away' or 'any'."),
				"date_from":   prop("string", "Optional start date, YYYY-MM-DD."),
				"date_to":     prop("string", "Optional end date, YYYY-MM-DD."),
				"limit":       prop("integer", "Maximum matches to list (default 25)."),
			}),
			Handler: func(args map[string]any) (string, error) {
				return handleSearchMatches(store, args)
			},
		},
		{
			Name: "team_stats",
			Description: "Win/draw/loss record, goals and win rate for a team, optionally " +
				"filtered by season, competition and home/away venue.",
			InputSchema: schema(map[string]any{
				"team":        prop("string", "Team name (required)."),
				"season":      prop("integer", "Optional season year."),
				"competition": prop("string", "Optional competition filter."),
				"venue":       prop("string", "Restrict to 'home', 'away' or 'any' matches."),
			}, "team"),
			Handler: func(args map[string]any) (string, error) {
				return handleTeamStats(store, args)
			},
		},
		{
			Name:        "head_to_head",
			Description: "All-time head-to-head record between two teams across all competitions.",
			InputSchema: schema(map[string]any{
				"team1":       prop("string", "First team (required)."),
				"team2":       prop("string", "Second team (required)."),
				"competition": prop("string", "Optional competition filter."),
			}, "team1", "team2"),
			Handler: func(args map[string]any) (string, error) {
				return handleHeadToHead(store, args)
			},
		},
		{
			Name: "search_players",
			Description: "Search the FIFA player database by name, nationality, club, " +
				"position or minimum overall rating.",
			InputSchema: schema(map[string]any{
				"name":        prop("string", "Player name substring (e.g. 'Gabriel')."),
				"nationality": prop("string", "Nationality filter (e.g. 'Brazil')."),
				"club":        prop("string", "Club name filter (e.g. 'Flamengo')."),
				"position":    prop("string", "Exact position code (e.g. 'GK', 'ST', 'LW')."),
				"min_overall": prop("integer", "Minimum FIFA overall rating."),
				"limit":       prop("integer", "Maximum players to list (default 20)."),
			}),
			Handler: func(args map[string]any) (string, error) {
				return handleSearchPlayers(store, args)
			},
		},
		{
			Name: "competition_standings",
			Description: "Calculate a league table for a competition and season from match " +
				"results (3 points per win, 1 per draw).",
			InputSchema: schema(map[string]any{
				"competition": prop("string", "Competition name (e.g. 'Brasileirão')."),
				"season":      prop("integer", "Season year (required, e.g. 2019)."),
			}, "competition", "season"),
			Handler: func(args map[string]any) (string, error) {
				return handleStandings(store, args)
			},
		},
		{
			Name: "competition_stats",
			Description: "Aggregate statistics for a competition/season: average goals per " +
				"match, home win rate and biggest victories.",
			InputSchema: schema(map[string]any{
				"competition": prop("string", "Optional competition filter."),
				"season":      prop("integer", "Optional season year."),
				"team":        prop("string", "Optional team filter."),
			}),
			Handler: func(args map[string]any) (string, error) {
				return handleCompetitionStats(store, args)
			},
		},
		{
			Name:        "list_competitions",
			Description: "List the competitions, season coverage and dataset sizes available.",
			InputSchema: schema(map[string]any{}),
			Handler: func(args map[string]any) (string, error) {
				return handleListCompetitions(store), nil
			},
		},
	}
}

// --- handlers ---------------------------------------------------------------

func handleSearchMatches(store *DataStore, args map[string]any) (string, error) {
	f := MatchFilter{
		Team:        argString(args, "team"),
		Opponent:    argString(args, "opponent"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		Venue:       strings.ToLower(argString(args, "venue")),
	}
	if df := argString(args, "date_from"); df != "" {
		if d, ok := parseDate(df); ok {
			f.DateFrom, f.HasDateFrom = d, true
		}
	}
	if dt := argString(args, "date_to"); dt != "" {
		if d, ok := parseDate(dt); ok {
			f.DateTo, f.HasDateTo = d, true
		}
	}
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 25
	}

	matches := FindMatches(store, f)
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es)", len(matches))
	if f.Team != "" {
		b.WriteString(" for " + f.Team)
	}
	if f.Opponent != "" {
		b.WriteString(" vs " + f.Opponent)
	}
	b.WriteString(":\n")

	shown := matches
	if len(shown) > limit {
		shown = shown[:limit]
	}
	for _, m := range shown {
		b.WriteString("- " + describeMatch(m) + "\n")
	}
	if len(matches) > limit {
		fmt.Fprintf(&b, "... (%d more not shown)\n", len(matches)-limit)
	}

	if f.Team != "" && f.Opponent != "" {
		h2h := HeadToHead(store, f.Team, f.Opponent, f.Competition)
		fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws\n",
			h2h.Team1, h2h.Team1Wins, h2h.Team2, h2h.Team2Wins, h2h.Draws)
	}
	return b.String(), nil
}

func handleTeamStats(store *DataStore, args map[string]any) (string, error) {
	team := argString(args, "team")
	if team == "" {
		return "", fmt.Errorf("'team' is required")
	}
	f := MatchFilter{
		Team:        team,
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		Venue:       strings.ToLower(argString(args, "venue")),
	}
	rec := ComputeTeamRecord(store, f)
	if rec.Played == 0 {
		return fmt.Sprintf("No matches found for %s with the given filters.", team), nil
	}

	var scope []string
	if f.Season != 0 {
		scope = append(scope, itoa(f.Season))
	}
	if f.Competition != "" {
		scope = append(scope, f.Competition)
	}
	switch f.Venue {
	case "home":
		scope = append(scope, "home matches")
	case "away":
		scope = append(scope, "away matches")
	}
	title := rec.Team + " record"
	if len(scope) > 0 {
		title += " (" + strings.Join(scope, ", ") + ")"
	}

	var b strings.Builder
	b.WriteString(title + ":\n")
	fmt.Fprintf(&b, "- Matches: %d\n", rec.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", rec.Wins, rec.Draws, rec.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n",
		rec.GoalsFor, rec.GoalsAgainst, rec.GoalDifference())
	fmt.Fprintf(&b, "- Points: %d\n", rec.Points())
	fmt.Fprintf(&b, "- Win rate: %s\n", pct(rec.WinRate()))
	return b.String(), nil
}

func handleHeadToHead(store *DataStore, args map[string]any) (string, error) {
	team1 := argString(args, "team1")
	team2 := argString(args, "team2")
	if team1 == "" || team2 == "" {
		return "", fmt.Errorf("'team1' and 'team2' are required")
	}
	h2h := HeadToHead(store, team1, team2, argString(args, "competition"))
	if len(h2h.Matches) == 0 {
		return fmt.Sprintf("No matches found between %s and %s.", team1, team2), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s head-to-head (%d matches):\n", h2h.Team1, h2h.Team2, len(h2h.Matches))
	fmt.Fprintf(&b, "- %s wins: %d\n", h2h.Team1, h2h.Team1Wins)
	fmt.Fprintf(&b, "- %s wins: %d\n", h2h.Team2, h2h.Team2Wins)
	fmt.Fprintf(&b, "- Draws: %d\n", h2h.Draws)
	fmt.Fprintf(&b, "- Goals: %s %d, %s %d\n", h2h.Team1, h2h.Team1Goals, h2h.Team2, h2h.Team2Goals)

	b.WriteString("\nMost recent meetings:\n")
	for i, m := range h2h.Matches {
		if i >= 5 {
			break
		}
		b.WriteString("- " + describeMatch(m) + "\n")
	}
	return b.String(), nil
}

func handleSearchPlayers(store *DataStore, args map[string]any) (string, error) {
	f := PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
	}
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 20
	}

	players := SearchPlayers(store, f)
	if len(players) == 0 {
		return "No players found for the given criteria.", nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s)", len(players))
	var crit []string
	if f.Name != "" {
		crit = append(crit, "name~"+f.Name)
	}
	if f.Nationality != "" {
		crit = append(crit, "nationality="+f.Nationality)
	}
	if f.Club != "" {
		crit = append(crit, "club~"+f.Club)
	}
	if f.Position != "" {
		crit = append(crit, "position="+f.Position)
	}
	if f.MinOverall != 0 {
		crit = append(crit, "overall>="+itoa(f.MinOverall))
	}
	if len(crit) > 0 {
		b.WriteString(" (" + strings.Join(crit, ", ") + ")")
	}
	b.WriteString(":\n")

	shown := players
	if len(shown) > limit {
		shown = shown[:limit]
	}
	for i, p := range shown {
		club := p.Club
		if club == "" {
			club = "no club"
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Potential: %d, Position: %s, Age: %d, Club: %s\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, p.Age, club)
	}
	if len(players) > limit {
		fmt.Fprintf(&b, "... (%d more not shown)\n", len(players)-limit)
	}
	return b.String(), nil
}

func handleStandings(store *DataStore, args map[string]any) (string, error) {
	competition := argString(args, "competition")
	if competition == "" {
		competition = "Brasileirão"
	}
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("'season' is required")
	}

	rows := Standings(store, competition, season)
	if len(rows) == 0 {
		return fmt.Sprintf("No standings could be calculated for %s %d.", competition, season), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from match results):\n", season, competition)
	for _, r := range rows {
		marker := ""
		if r.Rank == 1 {
			marker = "  <- Champion"
		}
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW %dD %dL, GF %d GA %d, diff %+d)%s\n",
			r.Rank, r.Team, r.Points(), r.Wins, r.Draws, r.Losses,
			r.GoalsFor, r.GoalsAgainst, r.GoalDifference(), marker)
	}
	if len(rows) >= 16 && strings.Contains(normalizeText(competition), "serie a") ||
		(len(rows) >= 16 && strings.Contains(normalizeText(competition), "brasil")) {
		var releg []string
		for _, r := range rows[len(rows)-4:] {
			releg = append(releg, r.Team)
		}
		fmt.Fprintf(&b, "\nRelegation zone (bottom 4): %s\n", strings.Join(releg, ", "))
	}
	return b.String(), nil
}

func handleCompetitionStats(store *DataStore, args map[string]any) (string, error) {
	f := MatchFilter{
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		Team:        argString(args, "team"),
	}
	stats := ComputeCompetitionStats(store, f)
	if stats.Matches == 0 {
		return "No matches found for the given criteria.", nil
	}

	scope := "All competitions"
	if f.Competition != "" {
		scope = f.Competition
	}
	if f.Season != 0 {
		scope += " " + itoa(f.Season)
	} else if stats.SeasonLow > 0 {
		scope += fmt.Sprintf(" (%d-%d)", stats.SeasonLow, stats.SeasonHigh)
	}
	if f.Team != "" {
		scope += " - " + f.Team
	}

	var b strings.Builder
	b.WriteString(scope + " statistics:\n")
	fmt.Fprintf(&b, "- Matches with results: %d\n", stats.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", stats.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", stats.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %d (%s), Away wins: %d, Draws: %d\n",
		stats.HomeWins, pct(stats.HomeWinRate()), stats.AwayWins, stats.Draws)
	if len(stats.BiggestWins) > 0 {
		b.WriteString("- Biggest victories:\n")
		for _, m := range stats.BiggestWins {
			b.WriteString("    " + describeMatch(m) + "\n")
		}
	}
	return b.String(), nil
}

func handleListCompetitions(store *DataStore) string {
	type info struct {
		count, low, high int
	}
	comps := map[string]*info{}
	for _, m := range store.Matches {
		c := comps[m.Competition]
		if c == nil {
			c = &info{}
			comps[m.Competition] = c
		}
		c.count++
		if m.Season > 0 {
			if c.low == 0 || m.Season < c.low {
				c.low = m.Season
			}
			if m.Season > c.high {
				c.high = m.Season
			}
		}
	}
	names := make([]string, 0, len(comps))
	for n := range comps {
		names = append(names, n)
	}
	sort.Strings(names)

	var b strings.Builder
	fmt.Fprintf(&b, "Brazilian Soccer knowledge base: %d matches, %d players.\n\n",
		len(store.Matches), len(store.Players))
	b.WriteString("Competitions available:\n")
	for _, n := range names {
		c := comps[n]
		if c.low > 0 {
			fmt.Fprintf(&b, "- %s: %d matches, seasons %d-%d\n", n, c.count, c.low, c.high)
		} else {
			fmt.Fprintf(&b, "- %s: %d matches\n", n, c.count)
		}
	}
	return b.String()
}
