// tools.go - MCP tool definitions for the Brazilian Soccer server.
//
// Context: Defines the eight tools exposed over MCP (search_matches,
// head_to_head, team_stats, league_standings, search_players, player_info,
// competition_stats, data_summary), their JSON input schemas, and the
// human-readable text formatting of results, following the answer formats
// in the specification.
package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// ---------- argument helpers (JSON-decoded args arrive as map[string]any) ----------

func argString(args map[string]any, key string) string {
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return strings.TrimSpace(s)
		}
		if f, ok := v.(float64); ok {
			return fmt.Sprintf("%v", int(f))
		}
	}
	return ""
}

func argInt(args map[string]any, key string) int {
	switch v := args[key].(type) {
	case float64:
		return int(v)
	case string:
		return atoiOr(v, 0)
	}
	return 0
}

func argDate(args map[string]any, key string) time.Time {
	if s := argString(args, key); s != "" {
		if t, ok := parseDate(s); ok {
			return t
		}
	}
	return time.Time{}
}

// ---------- formatting helpers ----------

func formatMatch(m Match) string {
	date := "????-??-??"
	if !m.Date.IsZero() {
		date = m.Date.Format("2006-01-02")
	}
	ctx := m.Competition
	if m.Round != "" {
		ctx += " Round " + m.Round
	}
	if m.Stage != "" {
		ctx += " " + m.Stage
	}
	if m.Season != 0 {
		ctx += fmt.Sprintf(", season %d", m.Season)
	}
	line := fmt.Sprintf("- %s: %s %d-%d %s (%s)", date, m.Home.Name, m.HomeGoals, m.AwayGoals, m.Away.Name, ctx)
	if m.Arena != "" {
		line += " @ " + m.Arena
	}
	return line
}

func formatRecord(r Record) string {
	return fmt.Sprintf("Matches: %d | Wins: %d, Draws: %d, Losses: %d | Goals For: %d, Goals Against: %d | Win rate: %.1f%%",
		r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
}

func formatPlayerLine(i int, p Player) string {
	club := p.Club
	if club == "" {
		club = "no club"
	}
	return fmt.Sprintf("%d. %s - Overall: %d, Potential: %d, Age: %d, Position: %s, Nationality: %s, Club: %s",
		i, p.Name, p.Overall, p.Potential, p.Age, p.Position, p.Nationality, club)
}

func seasonLabel(season int) string {
	if season == 0 {
		return "all seasons"
	}
	return fmt.Sprintf("season %d", season)
}

func compLabel(comp string) string {
	if comp == "" {
		return "all competitions"
	}
	return comp
}

// ---------- tool construction ----------

func schema(props map[string]any, required ...string) map[string]any {
	s := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}
func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

// BuildTools wires the query engine into MCP tool definitions.
func BuildTools(store *Store) []Tool {
	return []Tool{
		{
			Name: "search_matches",
			Description: "Search matches across Brasileirão Série A (2003-2023), Série B/C, Copa do Brasil and " +
				"Copa Libertadores. Filter by team, opponent, competition, season and date range. Team names are " +
				"normalized ('Palmeiras', 'Palmeiras-SP' and 'Sociedade Esportiva Palmeiras' all match). " +
				"When both team and opponent are given, a head-to-head summary is included.",
			InputSchema: schema(map[string]any{
				"team":        strProp("Team name; matches home or away (e.g. 'Flamengo')"),
				"opponent":    strProp("Second team, to find direct encounters (e.g. 'Fluminense')"),
				"competition": strProp("Competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Série B', 'Série C'"),
				"season":      intProp("Season year, e.g. 2019"),
				"date_from":   strProp("Earliest date, YYYY-MM-DD"),
				"date_to":     strProp("Latest date, YYYY-MM-DD"),
				"limit":       intProp("Max matches to return (default 20, most recent first)"),
			}),
			Handler: func(args map[string]any) (string, error) { return toolSearchMatches(store, args) },
		},
		{
			Name: "head_to_head",
			Description: "Head-to-head record between two teams: wins for each side, draws, goals, and the full " +
				"list of encounters in the dataset. Optionally restricted to one competition.",
			InputSchema: schema(map[string]any{
				"team1":       strProp("First team name"),
				"team2":       strProp("Second team name"),
				"competition": strProp("Optional competition filter"),
				"limit":       intProp("Max matches to list (default 15, most recent first)"),
			}, "team1", "team2"),
			Handler: func(args map[string]any) (string, error) { return toolHeadToHead(store, args) },
		},
		{
			Name: "team_stats",
			Description: "A team's win/loss/draw record, goals for/against and win rate, with a per-competition " +
				"breakdown. Filter by season, competition and venue (home/away/all).",
			InputSchema: schema(map[string]any{
				"team":        strProp("Team name"),
				"season":      intProp("Season year, e.g. 2022; omit for all seasons"),
				"competition": strProp("Optional competition filter"),
				"venue":       map[string]any{"type": "string", "enum": []string{"home", "away", "all"}, "description": "Venue filter (default all)"},
			}, "team"),
			Handler: func(args map[string]any) (string, error) { return toolTeamStats(store, args) },
		},
		{
			Name: "league_standings",
			Description: "League table for a season computed from match results (3 points per win). Defaults to " +
				"Brasileirão Série A. Shows champion at top; bottom 4 were the relegation zone.",
			InputSchema: schema(map[string]any{
				"season":      intProp("Season year, e.g. 2019"),
				"competition": strProp("Competition (default 'Brasileirão Série A'; also 'Série B', 'Série C')"),
			}, "season"),
			Handler: func(args map[string]any) (string, error) { return toolStandings(store, args) },
		},
		{
			Name: "search_players",
			Description: "Search the FIFA player database (18k+ players). Filter by name, nationality (e.g. " +
				"'Brazil'), club, position (codes like ST/GK or groups: forward, midfielder, defender, " +
				"goalkeeper), minimum overall rating and max age. Sorted by overall rating by default.",
			InputSchema: schema(map[string]any{
				"name":        strProp("Player name substring, accent-insensitive"),
				"nationality": strProp("Nationality, e.g. 'Brazil'"),
				"club":        strProp("Club name substring, e.g. 'Santos'"),
				"position":    strProp("Position code (ST, GK, CB...) or group (forward, midfielder, defender, goalkeeper)"),
				"min_overall": intProp("Minimum FIFA overall rating, e.g. 80"),
				"max_age":     intProp("Maximum age"),
				"sort_by":     map[string]any{"type": "string", "enum": []string{"overall", "potential", "age"}, "description": "Sort order (default overall, descending)"},
				"limit":       intProp("Max players to return (default 20)"),
			}),
			Handler: func(args map[string]any) (string, error) { return toolSearchPlayers(store, args) },
		},
		{
			Name: "player_info",
			Description: "Detailed FIFA profile for one player found by name: ratings, club, position, physical " +
				"attributes, value/wage and top skill ratings.",
			InputSchema: schema(map[string]any{
				"name": strProp("Player name, e.g. 'Neymar'"),
			}, "name"),
			Handler: func(args map[string]any) (string, error) { return toolPlayerInfo(store, args) },
		},
		{
			Name: "competition_stats",
			Description: "Aggregate statistics over matches: total matches, average goals per match, home win " +
				"rate, draw rate and the biggest victories. Filter by competition and/or season.",
			InputSchema: schema(map[string]any{
				"competition": strProp("Optional competition filter, e.g. 'Brasileirão'"),
				"season":      intProp("Optional season year"),
				"top_wins":    intProp("How many biggest wins to list (default 5)"),
			}),
			Handler: func(args map[string]any) (string, error) { return toolCompetitionStats(store, args) },
		},
		{
			Name: "data_summary",
			Description: "Overview of the loaded datasets: match counts per competition, season coverage, and " +
				"player database size. Useful to discover what can be queried.",
			InputSchema: schema(map[string]any{}),
			Handler:     func(args map[string]any) (string, error) { return toolDataSummary(store, args) },
		},
	}
}

// ---------- tool handlers ----------

func toolSearchMatches(store *Store, args map[string]any) (string, error) {
	f := MatchFilter{
		Team:        argString(args, "team"),
		Opponent:    argString(args, "opponent"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		From:        argDate(args, "date_from"),
		To:          argDate(args, "date_to"),
	}
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 20
	}
	matches := store.FilterMatches(f)
	if len(matches) == 0 {
		return "No matches found for those criteria.", nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es)", len(matches))
	if len(matches) > limit {
		fmt.Fprintf(&b, ", showing the %d most recent", limit)
	}
	b.WriteString(":\n")
	shown := matches
	if len(shown) > limit {
		shown = shown[len(shown)-limit:]
	}
	for i := len(shown) - 1; i >= 0; i-- { // most recent first
		b.WriteString(formatMatch(shown[i]))
		b.WriteString("\n")
	}
	if f.Team != "" && f.Opponent != "" {
		h := store.HeadToHead(f.Team, f.Opponent, f.Competition)
		fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws (goals %d-%d)\n",
			h.Team1, h.Wins1, h.Team2, h.Wins2, h.Draws, h.Goals1, h.Goals2)
	}
	return b.String(), nil
}

func toolHeadToHead(store *Store, args map[string]any) (string, error) {
	team1 := argString(args, "team1")
	team2 := argString(args, "team2")
	if team1 == "" || team2 == "" {
		return "", fmt.Errorf("both team1 and team2 are required")
	}
	comp := argString(args, "competition")
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 15
	}
	h := store.HeadToHead(team1, team2, comp)
	if len(h.Matches) == 0 {
		return fmt.Sprintf("No matches found between %s and %s.", team1, team2), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s (%s, %d matches):\n", h.Team1, h.Team2, compLabel(comp), len(h.Matches))
	fmt.Fprintf(&b, "- %s: %d wins\n- %s: %d wins\n- Draws: %d\n- Goals: %s %d, %s %d\n\n",
		h.Team1, h.Wins1, h.Team2, h.Wins2, h.Draws, h.Team1, h.Goals1, h.Team2, h.Goals2)
	b.WriteString("Matches (most recent first):\n")
	n := 0
	for i := len(h.Matches) - 1; i >= 0 && n < limit; i-- {
		b.WriteString(formatMatch(h.Matches[i]))
		b.WriteString("\n")
		n++
	}
	if len(h.Matches) > limit {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(h.Matches)-limit)
	}
	return b.String(), nil
}

func toolTeamStats(store *Store, args map[string]any) (string, error) {
	team := argString(args, "team")
	if team == "" {
		return "", fmt.Errorf("team is required")
	}
	season := argInt(args, "season")
	comp := argString(args, "competition")
	venue := argString(args, "venue")
	if venue == "all" {
		venue = ""
	}
	total, byComp, n := store.TeamStats(team, season, comp, venue)
	if n == 0 {
		return fmt.Sprintf("No matches found for %s with those filters.", team), nil
	}
	venueLabel := "home & away"
	if venue != "" {
		venueLabel = venue
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s record (%s, %s, %s):\n", parseTeam(team, "").Name, seasonLabel(season), compLabel(comp), venueLabel)
	fmt.Fprintf(&b, "- %s\n", formatRecord(total))
	if len(byComp) > 1 {
		b.WriteString("\nBy competition:\n")
		comps := make([]string, 0, len(byComp))
		for c := range byComp {
			comps = append(comps, c)
		}
		sort.Slice(comps, func(i, j int) bool { return byComp[comps[i]].Played > byComp[comps[j]].Played })
		for _, c := range comps {
			fmt.Fprintf(&b, "- %s: %s\n", c, formatRecord(*byComp[c]))
		}
	}
	return b.String(), nil
}

func toolStandings(store *Store, args map[string]any) (string, error) {
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("season is required, e.g. 2019")
	}
	comp := argString(args, "competition")
	if comp == "" {
		comp = CompSerieA
	}
	rows, nMatches := store.Standings(comp, season)
	if len(rows) == 0 {
		return fmt.Sprintf("No match data for %s season %d.", comp, season), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (computed from %d matches in dataset):\n", season, comp, nMatches)
	for i, r := range rows {
		tag := ""
		if i == 0 {
			tag = " - Champion"
		}
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)%s\n",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses,
			r.GoalsFor, r.GoalsAgainst, r.GoalsFor-r.GoalsAgainst, tag)
	}
	if strings.Contains(normalizeText(comp), "serie a") && len(rows) >= 20 {
		bottom := make([]string, 0, 4)
		for _, r := range rows[len(rows)-4:] {
			bottom = append(bottom, r.Team)
		}
		fmt.Fprintf(&b, "\nRelegation zone (bottom 4): %s\n", strings.Join(bottom, ", "))
	}
	return b.String(), nil
}

func toolSearchPlayers(store *Store, args map[string]any) (string, error) {
	f := PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		MaxAge:      argInt(args, "max_age"),
		SortBy:      argString(args, "sort_by"),
		Limit:       argInt(args, "limit"),
	}
	if f.Limit <= 0 {
		f.Limit = 20
	}
	limit := f.Limit
	f.Limit = 0
	players := store.SearchPlayers(f)
	if len(players) == 0 {
		return "No players found for those criteria. Note: the FIFA dataset has limited Brazilian-league club coverage.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s)", len(players))
	if len(players) > limit {
		fmt.Fprintf(&b, ", showing top %d", limit)
		players = players[:limit]
	}
	b.WriteString(":\n")
	for i, p := range players {
		b.WriteString(formatPlayerLine(i+1, p))
		b.WriteString("\n")
	}
	return b.String(), nil
}

func toolPlayerInfo(store *Store, args map[string]any) (string, error) {
	name := argString(args, "name")
	if name == "" {
		return "", fmt.Errorf("name is required")
	}
	players := store.SearchPlayers(PlayerFilter{Name: name})
	if len(players) == 0 {
		return fmt.Sprintf("No player named %q found in the FIFA dataset.", name), nil
	}
	p := players[0]
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", p.Name)
	fmt.Fprintf(&b, "- Overall: %d (potential %d)\n", p.Overall, p.Potential)
	fmt.Fprintf(&b, "- Position: %s, Jersey: %d, Preferred foot: %s\n", p.Position, p.Jersey, p.PreferredFoot)
	club := p.Club
	if club == "" {
		club = "no club"
	}
	fmt.Fprintf(&b, "- Club: %s\n", club)
	fmt.Fprintf(&b, "- Nationality: %s, Age: %d, Height: %s, Weight: %s\n", p.Nationality, p.Age, p.Height, p.Weight)
	if p.Value != "" || p.Wage != "" {
		fmt.Fprintf(&b, "- Value: %s, Wage: %s\n", p.Value, p.Wage)
	}
	if len(p.Skills) > 0 {
		skills := make([]Skill, len(p.Skills))
		copy(skills, p.Skills)
		sort.SliceStable(skills, func(i, j int) bool { return skills[i].Value > skills[j].Value })
		top := skills[:min(8, len(skills))]
		parts := make([]string, len(top))
		for i, sk := range top {
			parts[i] = fmt.Sprintf("%s %d", sk.Name, sk.Value)
		}
		fmt.Fprintf(&b, "- Top skills: %s\n", strings.Join(parts, ", "))
	}
	if len(players) > 1 {
		fmt.Fprintf(&b, "\nOther name matches: ")
		others := make([]string, 0, min(5, len(players)-1))
		for _, q := range players[1:min(6, len(players))] {
			others = append(others, fmt.Sprintf("%s (overall %d)", q.Name, q.Overall))
		}
		b.WriteString(strings.Join(others, ", "))
		b.WriteString("\n")
	}
	return b.String(), nil
}

func toolCompetitionStats(store *Store, args map[string]any) (string, error) {
	comp := argString(args, "competition")
	season := argInt(args, "season")
	topWins := argInt(args, "top_wins")
	if topWins <= 0 {
		topWins = 5
	}
	st := store.CompetitionStats(comp, season, topWins)
	if st.Matches == 0 {
		return "No matches found for those criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics for %s, %s:\n", compLabel(comp), seasonLabel(season))
	fmt.Fprintf(&b, "- Matches: %d\n", st.Matches)
	fmt.Fprintf(&b, "- Total goals: %d (average %.2f per match)\n", st.TotalGoals, st.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Away wins: %d (%.1f%%), Draws: %d (%.1f%%)\n",
		st.HomeWins, st.HomeWinRate(),
		st.AwayWins, float64(st.AwayWins)/float64(st.Matches)*100,
		st.Draws, float64(st.Draws)/float64(st.Matches)*100)
	if len(st.BiggestWins) > 0 {
		b.WriteString("\nBiggest victories:\n")
		for _, m := range st.BiggestWins {
			b.WriteString(formatMatch(m))
			b.WriteString("\n")
		}
	}
	return b.String(), nil
}

func toolDataSummary(store *Store, args map[string]any) (string, error) {
	type span struct {
		count    int
		min, max int
	}
	comps := map[string]*span{}
	for _, m := range store.Matches {
		sp, ok := comps[m.Competition]
		if !ok {
			sp = &span{min: m.Season, max: m.Season}
			comps[m.Competition] = sp
		}
		sp.count++
		if m.Season != 0 {
			if sp.min == 0 || m.Season < sp.min {
				sp.min = m.Season
			}
			if m.Season > sp.max {
				sp.max = m.Season
			}
		}
	}
	names := make([]string, 0, len(comps))
	for c := range comps {
		names = append(names, c)
	}
	sort.Slice(names, func(i, j int) bool { return comps[names[i]].count > comps[names[j]].count })

	brazilians := 0
	for _, p := range store.Players {
		if p.Nationality == "Brazil" {
			brazilians++
		}
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Loaded data summary:\n")
	fmt.Fprintf(&b, "- Matches: %d (deduplicated across 5 datasets)\n", len(store.Matches))
	for _, c := range names {
		sp := comps[c]
		fmt.Fprintf(&b, "  - %s: %d matches, seasons %d-%d\n", c, sp.count, sp.min, sp.max)
	}
	fmt.Fprintf(&b, "- FIFA players: %d (%d Brazilian)\n", len(store.Players), brazilians)
	b.WriteString("\nAvailable tools: search_matches, head_to_head, team_stats, league_standings, " +
		"search_players, player_info, competition_stats, data_summary\n")
	return b.String(), nil
}
