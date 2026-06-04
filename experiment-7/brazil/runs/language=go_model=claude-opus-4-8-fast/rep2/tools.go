// Brazilian Soccer MCP Server
//
// File: tools.go
// Responsibility: Define the MCP tools the server exposes and the logic that
// turns loosely-typed JSON arguments into Store queries and human-readable text
// answers. There are seven tools covering the five required capability areas:
// find_matches, team_stats, head_to_head, search_players, standings,
// competition_stats and list_competitions. Each handler validates/coerces its
// arguments, runs the query against the Store, and formats a concise textual
// response in the style shown in the specification.
package main

import (
	"fmt"
	"strings"
)

// RegisterTools wires every soccer tool onto the server, closing over the store.
func RegisterTools(srv *Server, store *Store) {
	srv.AddTool(Tool{
		Name: "find_matches",
		Description: "Find soccer matches by team, opponent, competition, season " +
			"or date range. When both 'team' and 'opponent' are given, also reports " +
			"the head-to-head record. Dates use YYYY-MM-DD.",
		InputSchema: objectSchema(props{
			"team":        strProp("Team name (matches home or away), e.g. 'Flamengo'"),
			"opponent":    strProp("Opponent team name to restrict to games between the two teams"),
			"competition": strProp("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"),
			"season":      intProp("Season year, e.g. 2019"),
			"start_date":  strProp("Earliest match date (YYYY-MM-DD)"),
			"end_date":    strProp("Latest match date (YYYY-MM-DD)"),
			"home_away":   strProp("Restrict 'team' to 'home' or 'away' games"),
			"limit":       intProp("Maximum matches to list (default 25)"),
		}, nil),
		Handler: func(a map[string]interface{}) (string, error) {
			return handleFindMatches(store, a)
		},
	})

	srv.AddTool(Tool{
		Name: "team_stats",
		Description: "Aggregate win/draw/loss record and goals for a team, " +
			"optionally filtered by season, competition or home/away.",
		InputSchema: objectSchema(props{
			"team":        strProp("Team name, e.g. 'Corinthians'"),
			"season":      intProp("Season year, e.g. 2022"),
			"competition": strProp("Competition filter, e.g. 'Brasileirão'"),
			"home_away":   strProp("Restrict to 'home' or 'away' games"),
		}, []string{"team"}),
		Handler: func(a map[string]interface{}) (string, error) {
			return handleTeamStats(store, a)
		},
	})

	srv.AddTool(Tool{
		Name:        "head_to_head",
		Description: "Compare two teams head-to-head across all competitions in the data.",
		InputSchema: objectSchema(props{
			"team1": strProp("First team, e.g. 'Palmeiras'"),
			"team2": strProp("Second team, e.g. 'Santos'"),
			"limit": intProp("Maximum recent meetings to list (default 15)"),
		}, []string{"team1", "team2"}),
		Handler: func(a map[string]interface{}) (string, error) {
			return handleHeadToHead(store, a)
		},
	})

	srv.AddTool(Tool{
		Name: "search_players",
		Description: "Search the FIFA player database by name, nationality, club, " +
			"position and/or minimum overall rating. Results are sorted by rating.",
		InputSchema: objectSchema(props{
			"name":        strProp("Player name substring, e.g. 'Gabriel Barbosa'"),
			"nationality": strProp("Nationality, e.g. 'Brazil'"),
			"club":        strProp("Club name, e.g. 'Flamengo'"),
			"position":    strProp("Position code, e.g. 'ST', 'GK', 'CAM'"),
			"min_overall": intProp("Minimum FIFA overall rating"),
			"limit":       intProp("Maximum players to list (default 25)"),
		}, nil),
		Handler: func(a map[string]interface{}) (string, error) {
			return handleSearchPlayers(store, a)
		},
	})

	srv.AddTool(Tool{
		Name: "standings",
		Description: "Compute the final league table for a competition and season " +
			"from match results (points, W/D/L, goals).",
		InputSchema: objectSchema(props{
			"competition": strProp("Competition, e.g. 'Brasileirão Série A'"),
			"season":      intProp("Season year, e.g. 2019"),
			"limit":       intProp("Maximum table rows to show (default all)"),
		}, []string{"season"}),
		Handler: func(a map[string]interface{}) (string, error) {
			return handleStandings(store, a)
		},
	})

	srv.AddTool(Tool{
		Name: "competition_stats",
		Description: "Aggregate statistics over a set of matches: average goals " +
			"per match, home/away/draw rates and the biggest & highest-scoring games.",
		InputSchema: objectSchema(props{
			"competition": strProp("Competition filter, e.g. 'Brasileirão'"),
			"season":      intProp("Season year, e.g. 2019"),
		}, nil),
		Handler: func(a map[string]interface{}) (string, error) {
			return handleCompetitionStats(store, a)
		},
	})

	srv.AddTool(Tool{
		Name:        "list_competitions",
		Description: "List the competitions available in the data and the seasons covered.",
		InputSchema: objectSchema(props{}, nil),
		Handler: func(a map[string]interface{}) (string, error) {
			return handleListCompetitions(store), nil
		},
	})
}

// ---- Handlers ----------------------------------------------------------------

func handleFindMatches(store *Store, a map[string]interface{}) (string, error) {
	f := MatchFilter{
		Team:        argStr(a, "team"),
		Opponent:    argStr(a, "opponent"),
		Competition: argStr(a, "competition"),
		Season:      argInt(a, "season"),
		HomeAway:    strings.ToLower(argStr(a, "home_away")),
		Dedup:       true,
	}
	if d, ok := parseDate(argStr(a, "start_date")); ok {
		f.StartDate = d
	}
	if d, ok := parseDate(argStr(a, "end_date")); ok {
		f.EndDate = d
	}
	if f.Team == "" && f.Opponent == "" && f.Competition == "" && f.Season == 0 &&
		f.StartDate.IsZero() && f.EndDate.IsZero() {
		return "", fmt.Errorf("provide at least one of: team, opponent, competition, season, start_date, end_date")
	}

	limit := argIntDefault(a, "limit", 25)
	matches := store.FindMatches(f)

	var b strings.Builder
	if f.Opponent != "" && f.Team != "" {
		h := store.HeadToHead(f.Team, f.Opponent)
		fmt.Fprintf(&b, "%s vs %s — %d matches in dataset\n", h.Team1, h.Team2, len(h.Matches))
		fmt.Fprintf(&b, "Head-to-head: %s %d wins, %s %d wins, %d draws (goals %d-%d)\n\n",
			h.Team1, h.Team1Wins, h.Team2, h.Team2Wins, h.Draws, h.Team1Goals, h.Team2Goals)
	} else {
		fmt.Fprintf(&b, "Found %d matches", len(matches))
		if f.Team != "" {
			fmt.Fprintf(&b, " for %s", store.DisplayName(teamKey(f.Team)))
		}
		fmt.Fprintln(&b)
		fmt.Fprintln(&b)
	}
	if len(matches) == 0 {
		b.WriteString("(no matches found)\n")
		return b.String(), nil
	}
	writeMatchList(&b, matches, limit)
	return b.String(), nil
}

func handleTeamStats(store *Store, a map[string]interface{}) (string, error) {
	team := argStr(a, "team")
	if team == "" {
		return "", fmt.Errorf("'team' is required")
	}
	f := MatchFilter{
		Competition: argStr(a, "competition"),
		Season:      argInt(a, "season"),
		HomeAway:    strings.ToLower(argStr(a, "home_away")),
	}
	r := store.TeamStats(team, f)

	var b strings.Builder
	label := r.Team + " record"
	var scope []string
	if f.HomeAway == "home" || f.HomeAway == "away" {
		scope = append(scope, f.HomeAway)
	}
	if f.Season != 0 {
		scope = append(scope, fmt.Sprintf("%d", f.Season))
	}
	if f.Competition != "" {
		scope = append(scope, f.Competition)
	}
	if len(scope) > 0 {
		label += " (" + strings.Join(scope, " ") + ")"
	}
	fmt.Fprintf(&b, "%s:\n", label)
	if r.Matches == 0 {
		b.WriteString("- No matches found for this filter\n")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "- Matches: %d\n", r.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n", r.GoalsFor, r.GoalsAgainst, r.GoalDiff())
	fmt.Fprintf(&b, "- Points: %d\n", r.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", r.WinRate()*100)
	return b.String(), nil
}

func handleHeadToHead(store *Store, a map[string]interface{}) (string, error) {
	t1, t2 := argStr(a, "team1"), argStr(a, "team2")
	if t1 == "" || t2 == "" {
		return "", fmt.Errorf("both 'team1' and 'team2' are required")
	}
	limit := argIntDefault(a, "limit", 15)
	h := store.HeadToHead(t1, t2)

	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head (%d matches in dataset)\n", h.Team1, h.Team2, len(h.Matches))
	if len(h.Matches) == 0 {
		b.WriteString("(no recorded meetings)\n")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "%s: %d wins | %s: %d wins | Draws: %d\n", h.Team1, h.Team1Wins, h.Team2, h.Team2Wins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d - %d %s\n\n", h.Team1, h.Team1Goals, h.Team2Goals, h.Team2)
	b.WriteString("Recent meetings:\n")
	writeMatchList(&b, h.Matches, limit)
	return b.String(), nil
}

func handleSearchPlayers(store *Store, a map[string]interface{}) (string, error) {
	f := PlayerFilter{
		Name:        argStr(a, "name"),
		Nationality: argStr(a, "nationality"),
		Club:        argStr(a, "club"),
		Position:    argStr(a, "position"),
		MinOverall:  argInt(a, "min_overall"),
		Limit:       argIntDefault(a, "limit", 25),
	}
	if f.Name == "" && f.Nationality == "" && f.Club == "" && f.Position == "" && f.MinOverall == 0 {
		return "", fmt.Errorf("provide at least one of: name, nationality, club, position, min_overall")
	}
	players := store.SearchPlayers(f)

	var b strings.Builder
	fmt.Fprintf(&b, "Found %d players", len(players))
	if f.Limit > 0 && len(players) == f.Limit {
		b.WriteString(" (showing top results)")
	}
	fmt.Fprintln(&b)
	fmt.Fprintln(&b)
	if len(players) == 0 {
		b.WriteString("(no players found)\n")
		return b.String(), nil
	}
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s — Overall: %d, Potential: %d, Pos: %s, Club: %s, Nat: %s",
			i+1, p.Name, p.Overall, p.Potential, dash(p.Position), dash(p.Club), dash(p.Nationality))
		if p.Age > 0 {
			fmt.Fprintf(&b, ", Age: %d", p.Age)
		}
		fmt.Fprintln(&b)
	}
	return b.String(), nil
}

func handleStandings(store *Store, a map[string]interface{}) (string, error) {
	season := argInt(a, "season")
	if season == 0 {
		return "", fmt.Errorf("'season' is required")
	}
	competition := argStr(a, "competition")
	if competition == "" {
		competition = "Brasileirão Série A"
	}
	table := store.Standings(competition, season)

	var b strings.Builder
	fmt.Fprintf(&b, "%d %s — Final Standings (calculated from matches)\n", season, competition)
	if len(table) == 0 {
		b.WriteString("(no matches found for this competition/season)\n")
		return b.String(), nil
	}
	limit := argIntDefault(a, "limit", len(table))
	fmt.Fprintf(&b, "%-3s %-26s %4s %3s %3s %3s %3s %5s %5s\n", "#", "Team", "Pts", "P", "W", "D", "L", "GF", "GA")
	for i, r := range table {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "%-3d %-26s %4d %3d %3d %3d %3d %5d %5d\n",
			i+1, truncate(r.Team, 26), r.Points(), r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst)
	}
	if len(table) > 0 {
		fmt.Fprintf(&b, "\nChampion: %s (%d pts)\n", table[0].Team, table[0].Points())
	}
	return b.String(), nil
}

func handleCompetitionStats(store *Store, a map[string]interface{}) (string, error) {
	f := MatchFilter{
		Competition: argStr(a, "competition"),
		Season:      argInt(a, "season"),
	}
	c := store.Stats(f)

	var b strings.Builder
	scope := "all data"
	var parts []string
	if f.Competition != "" {
		parts = append(parts, f.Competition)
	}
	if f.Season != 0 {
		parts = append(parts, fmt.Sprintf("%d", f.Season))
	}
	if len(parts) > 0 {
		scope = strings.Join(parts, " ")
	}
	fmt.Fprintf(&b, "Statistics for %s:\n", scope)
	if c.WithScore == 0 {
		b.WriteString("(no matches with scores found)\n")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "- Matches: %d (%d with scores)\n", c.Matches, c.WithScore)
	fmt.Fprintf(&b, "- Total goals: %d\n", c.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", c.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %.1f%%, Away wins: %.1f%%, Draws: %.1f%%\n",
		pct(c.HomeWins, c.WithScore), pct(c.AwayWins, c.WithScore), pct(c.Draws, c.WithScore))

	b.WriteString("\nBiggest victories (by margin):\n")
	for i, m := range c.BiggestWins {
		fmt.Fprintf(&b, "%d. %s\n", i+1, formatMatch(m))
	}
	return b.String(), nil
}

func handleListCompetitions(store *Store) string {
	var b strings.Builder
	b.WriteString("Available competitions and seasons:\n\n")
	for _, comp := range store.Competitions() {
		seasons := store.Seasons(comp)
		if len(seasons) == 0 {
			fmt.Fprintf(&b, "- %s\n", comp)
			continue
		}
		fmt.Fprintf(&b, "- %s: %d-%d\n", comp, seasons[0], seasons[len(seasons)-1])
	}
	fmt.Fprintf(&b, "\nTotal matches loaded: %d\nTotal players loaded: %d\n",
		len(store.Matches), len(store.Players))
	return b.String()
}

// ---- Formatting helpers ------------------------------------------------------

// writeMatchList writes up to limit matches as a bulleted list.
func writeMatchList(b *strings.Builder, matches []Match, limit int) {
	shown := matches
	if limit > 0 && len(matches) > limit {
		shown = matches[:limit]
	}
	for _, m := range shown {
		fmt.Fprintf(b, "- %s\n", formatMatch(m))
	}
	if len(matches) > len(shown) {
		fmt.Fprintf(b, "... (%d more matches in dataset)\n", len(matches)-len(shown))
	}
}

// formatMatch renders a single match as a one-line summary.
func formatMatch(m Match) string {
	date := "????-??-??"
	if m.HasDate {
		date = m.Date.Format("2006-01-02")
	}
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoal, m.AwayGoal)
	}
	ctx := m.Competition
	if m.Season != 0 {
		ctx = fmt.Sprintf("%s %d", m.Competition, m.Season)
	}
	if m.Round != "" {
		ctx += " Round " + m.Round
	}
	if m.Stage != "" {
		ctx += " " + m.Stage
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", date, m.HomeTeam, score, m.AwayTeam, strings.TrimSpace(ctx))
}

// ---- Argument coercion -------------------------------------------------------

// argStr returns a string argument, tolerating non-string JSON values.
func argStr(a map[string]interface{}, key string) string {
	v, ok := a[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case float64:
		return strings.TrimSuffix(fmt.Sprintf("%v", t), ".0")
	default:
		return strings.TrimSpace(fmt.Sprintf("%v", t))
	}
}

// argInt returns an integer argument, accepting JSON numbers or numeric strings;
// returns 0 when absent or unparseable.
func argInt(a map[string]interface{}, key string) int {
	v, ok := a[key]
	if !ok || v == nil {
		return 0
	}
	switch t := v.(type) {
	case float64:
		return int(t)
	case int:
		return t
	case string:
		if n, ok := atoi(t); ok {
			return n
		}
	}
	return 0
}

// argIntDefault is argInt with a fallback when the argument is absent/zero.
func argIntDefault(a map[string]interface{}, key string, def int) int {
	if n := argInt(a, key); n != 0 {
		return n
	}
	return def
}

// ---- Schema builders ---------------------------------------------------------

type props map[string]map[string]interface{}

func objectSchema(p props, required []string) map[string]interface{} {
	schema := map[string]interface{}{
		"type":       "object",
		"properties": map[string]interface{}(toIface(p)),
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func toIface(p props) map[string]interface{} {
	out := make(map[string]interface{}, len(p))
	for k, v := range p {
		out[k] = v
	}
	return out
}

func strProp(desc string) map[string]interface{} {
	return map[string]interface{}{"type": "string", "description": desc}
}

func intProp(desc string) map[string]interface{} {
	return map[string]interface{}{"type": "integer", "description": desc}
}

// ---- Small utilities ---------------------------------------------------------

func pct(n, total int) float64 {
	if total == 0 {
		return 0
	}
	return float64(n) / float64(total) * 100
}

func dash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}
