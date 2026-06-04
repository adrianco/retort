// Package server wires the soccer data store to MCP tools, defining each
// tool's JSON schema, argument decoding, and human-readable text formatting.
//
// Context:
//   - Exposes 8 tools covering the five capability areas in TASK.md: match,
//     team, player, competition, and statistical queries.
//   - Handlers decode the raw JSON arguments object, call store query helpers,
//     and render a concise plain-text answer (the format the spec's "Example
//     answer format" blocks illustrate).
package server

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/store"
)

// Register adds all soccer tools backed by st to the MCP server s.
func Register(s *mcp.Server, st *store.Store) {
	s.AddTool("find_matches",
		"Find soccer matches by team, opponent (head-to-head), competition, season, or date range. Returns a chronological list with scores and competition.",
		objSchema(map[string]any{
			"team":        strProp("Team name (matches home or away). E.g. 'Flamengo'."),
			"opponent":    strProp("Opponent team; when set with 'team', restricts to head-to-head matches."),
			"competition": strProp("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
			"season":      intProp("Season year, e.g. 2019."),
			"date_from":   strProp("Inclusive start date (YYYY-MM-DD)."),
			"date_to":     strProp("Inclusive end date (YYYY-MM-DD)."),
			"limit":       intProp("Max matches to return (default 25)."),
		}, nil),
		handleFindMatches(st))

	s.AddTool("head_to_head",
		"Summarize the head-to-head record between two teams (wins/draws/losses and goals) plus recent meetings.",
		objSchema(map[string]any{
			"team_a": strProp("First team."),
			"team_b": strProp("Second team."),
			"limit":  intProp("Max recent matches to list (default 10)."),
		}, []string{"team_a", "team_b"}),
		handleHeadToHead(st))

	s.AddTool("team_stats",
		"Compute a team's record: matches, wins, draws, losses, goals for/against, win rate. Optionally filter by competition, season, and venue.",
		objSchema(map[string]any{
			"team":        strProp("Team name."),
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season year."),
			"venue":       enumProp("Restrict to 'home', 'away', or 'all' matches (default all).", "home", "away", "all"),
		}, []string{"team"}),
		handleTeamStats(st))

	s.AddTool("standings",
		"Compute a league table (points, W/D/L, goals) for a competition and season, calculated from match results.",
		objSchema(map[string]any{
			"competition": strProp("Competition (default 'Brasileirão Série A')."),
			"season":      intProp("Season year (required for a meaningful table), e.g. 2019."),
			"limit":       intProp("Max teams to show (default all)."),
		}, []string{"season"}),
		handleStandings(st))

	s.AddTool("search_players",
		"Search FIFA player data by name, nationality, club, position, or minimum overall rating. Sorted by rating.",
		objSchema(map[string]any{
			"name":        strProp("Player name (substring)."),
			"nationality": strProp("Nationality, e.g. 'Brazil'."),
			"club":        strProp("Club name (substring)."),
			"position":    strProp("Position code, e.g. 'ST', 'GK', 'CB'."),
			"min_overall": intProp("Minimum FIFA overall rating."),
			"limit":       intProp("Max players to return (default 20)."),
		}, nil),
		handleSearchPlayers(st))

	s.AddTool("competition_stats",
		"Aggregate statistics for a competition/season: matches, average goals per match, home/away/draw split.",
		objSchema(map[string]any{
			"competition": strProp("Competition filter (default all competitions)."),
			"season":      intProp("Optional season year."),
		}, nil),
		handleCompetitionStats(st))

	s.AddTool("biggest_wins",
		"List matches with the largest goal margins, optionally filtered by competition and season.",
		objSchema(map[string]any{
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season year."),
			"limit":       intProp("Max matches to return (default 10)."),
		}, nil),
		handleBiggestWins(st))

	s.AddTool("list_competitions",
		"List the competitions and season range available in the loaded datasets.",
		objSchema(map[string]any{}, nil),
		handleListCompetitions(st))
}

// --- argument types ---

type findMatchesArgs struct {
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	DateFrom    string `json:"date_from"`
	DateTo      string `json:"date_to"`
	Limit       int    `json:"limit"`
}

func handleFindMatches(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		var a findMatchesArgs
		if err := decode(raw, &a); err != nil {
			return "", err
		}
		if a.Team == "" && a.Opponent == "" && a.Competition == "" && a.Season == 0 && a.DateFrom == "" && a.DateTo == "" {
			return "", fmt.Errorf("provide at least one filter (team, competition, season, or date range)")
		}
		f := store.MatchFilter{
			Team:        a.Team,
			Opponent:    a.Opponent,
			Competition: a.Competition,
			Season:      a.Season,
		}
		if a.DateFrom != "" {
			t, err := time.Parse("2006-01-02", a.DateFrom)
			if err != nil {
				return "", fmt.Errorf("invalid date_from (use YYYY-MM-DD): %w", err)
			}
			f.DateFrom = t
		}
		if a.DateTo != "" {
			t, err := time.Parse("2006-01-02", a.DateTo)
			if err != nil {
				return "", fmt.Errorf("invalid date_to (use YYYY-MM-DD): %w", err)
			}
			f.DateTo = t
		}
		limit := a.Limit
		if limit == 0 {
			limit = 25
		}
		matches := st.FindMatches(f, limit)
		if len(matches) == 0 {
			return "No matches found for the given criteria.", nil
		}
		var b strings.Builder
		fmt.Fprintf(&b, "Found %d match(es):\n", len(matches))
		for _, m := range matches {
			b.WriteString(formatMatch(m))
			b.WriteByte('\n')
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

type headToHeadArgs struct {
	TeamA string `json:"team_a"`
	TeamB string `json:"team_b"`
	Limit int    `json:"limit"`
}

func handleHeadToHead(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		var a headToHeadArgs
		if err := decode(raw, &a); err != nil {
			return "", err
		}
		if a.TeamA == "" || a.TeamB == "" {
			return "", fmt.Errorf("both team_a and team_b are required")
		}
		rec, matches := st.HeadToHead(a.TeamA, a.TeamB)
		if len(matches) == 0 {
			return fmt.Sprintf("No matches found between %s and %s.", a.TeamA, a.TeamB), nil
		}
		limit := a.Limit
		if limit == 0 {
			limit = 10
		}
		var b strings.Builder
		fmt.Fprintf(&b, "Head-to-head: %s vs %s\n", a.TeamA, a.TeamB)
		fmt.Fprintf(&b, "Total meetings with scores: %d\n", rec.Matches)
		fmt.Fprintf(&b, "%s: %d wins, %d draws, %d wins for %s\n",
			a.TeamA, rec.Wins, rec.Draws, rec.Losses, a.TeamB)
		fmt.Fprintf(&b, "Goals: %s %d - %d %s\n\n", a.TeamA, rec.GoalsFor, rec.GoalsAgainst, a.TeamB)
		b.WriteString("Recent meetings:\n")
		for i, m := range matches {
			if i >= limit {
				fmt.Fprintf(&b, "... (%d more)\n", len(matches)-limit)
				break
			}
			b.WriteString(formatMatch(m))
			b.WriteByte('\n')
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

type teamStatsArgs struct {
	Team        string `json:"team"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Venue       string `json:"venue"`
}

func handleTeamStats(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		var a teamStatsArgs
		if err := decode(raw, &a); err != nil {
			return "", err
		}
		if a.Team == "" {
			return "", fmt.Errorf("team is required")
		}
		venue := store.VenueAll
		switch strings.ToLower(a.Venue) {
		case "home":
			venue = store.VenueHome
		case "away":
			venue = store.VenueAway
		case "", "all":
			venue = store.VenueAll
		default:
			return "", fmt.Errorf("venue must be 'home', 'away', or 'all'")
		}
		rec := st.TeamStats(a.Team, a.Competition, a.Season, venue)
		if rec.Matches == 0 {
			return fmt.Sprintf("No matches found for %s with the given filters.", a.Team), nil
		}
		var scope []string
		if a.Competition != "" {
			scope = append(scope, a.Competition)
		}
		if a.Season != 0 {
			scope = append(scope, fmt.Sprintf("%d", a.Season))
		}
		if venue != store.VenueAll {
			scope = append(scope, strings.ToLower(a.Venue))
		}
		title := a.Team
		if len(scope) > 0 {
			title = fmt.Sprintf("%s (%s)", a.Team, strings.Join(scope, ", "))
		}
		var b strings.Builder
		fmt.Fprintf(&b, "%s record:\n", title)
		fmt.Fprintf(&b, "- Matches: %d\n", rec.Matches)
		fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", rec.Wins, rec.Draws, rec.Losses)
		fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n", rec.GoalsFor, rec.GoalsAgainst, rec.GoalDiff())
		fmt.Fprintf(&b, "- Win rate: %.1f%%\n", rec.WinRate()*100)
		fmt.Fprintf(&b, "- Points (3-1-0): %d", rec.Points())
		return b.String(), nil
	}
}

type standingsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Limit       int    `json:"limit"`
}

func handleStandings(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		var a standingsArgs
		if err := decode(raw, &a); err != nil {
			return "", err
		}
		if a.Season == 0 {
			return "", fmt.Errorf("season is required for standings")
		}
		comp := a.Competition
		if comp == "" {
			comp = store.CompBrasileirao
		}
		table := st.Standings(comp, a.Season)
		if len(table) == 0 {
			return fmt.Sprintf("No standings available for %s %d.", comp, a.Season), nil
		}
		limit := a.Limit
		if limit <= 0 || limit > len(table) {
			limit = len(table)
		}
		var b strings.Builder
		fmt.Fprintf(&b, "%s %d standings (calculated from matches):\n", comp, a.Season)
		for i := 0; i < limit; i++ {
			r := table[i]
			fmt.Fprintf(&b, "%2d. %-28s %3d pts (%2dW %2dD %2dL, GF %d GA %d, %+d)\n",
				i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff())
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

type searchPlayersArgs struct {
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	MinOverall  int    `json:"min_overall"`
	Limit       int    `json:"limit"`
}

func handleSearchPlayers(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		var a searchPlayersArgs
		if err := decode(raw, &a); err != nil {
			return "", err
		}
		if a.Name == "" && a.Nationality == "" && a.Club == "" && a.Position == "" && a.MinOverall == 0 {
			return "", fmt.Errorf("provide at least one filter (name, nationality, club, position, or min_overall)")
		}
		limit := a.Limit
		if limit == 0 {
			limit = 20
		}
		players := st.SearchPlayers(store.PlayerFilter{
			Name:        a.Name,
			Nationality: a.Nationality,
			Club:        a.Club,
			Position:    a.Position,
			MinOverall:  a.MinOverall,
		}, limit)
		if len(players) == 0 {
			return "No players found for the given criteria.", nil
		}
		var b strings.Builder
		fmt.Fprintf(&b, "Found %d player(s):\n", len(players))
		for i, p := range players {
			fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
				i+1, p.Name, p.Overall, dash(p.Position), dash(p.Club), p.Nationality, p.Age)
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

type competitionStatsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
}

func handleCompetitionStats(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		var a competitionStatsArgs
		if err := decode(raw, &a); err != nil {
			return "", err
		}
		cs := st.CompetitionStats(a.Competition, a.Season)
		if cs.Matches == 0 {
			return "No matches found for the given criteria.", nil
		}
		label := a.Competition
		if label == "" {
			label = "All competitions"
		}
		if a.Season != 0 {
			label = fmt.Sprintf("%s %d", label, a.Season)
		}
		var b strings.Builder
		fmt.Fprintf(&b, "%s statistics:\n", label)
		fmt.Fprintf(&b, "- Matches (with scores): %d\n", cs.Matches)
		fmt.Fprintf(&b, "- Total goals: %d\n", cs.TotalGoals)
		fmt.Fprintf(&b, "- Average goals per match: %.2f\n", cs.AvgGoals())
		fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Away wins: %d, Draws: %d",
			cs.HomeWins, cs.HomeWinRate()*100, cs.AwayWins, cs.Draws)
		return b.String(), nil
	}
}

type biggestWinsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Limit       int    `json:"limit"`
}

func handleBiggestWins(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		var a biggestWinsArgs
		if err := decode(raw, &a); err != nil {
			return "", err
		}
		limit := a.Limit
		if limit == 0 {
			limit = 10
		}
		matches := st.BiggestWins(a.Competition, a.Season, limit)
		if len(matches) == 0 {
			return "No matches found for the given criteria.", nil
		}
		var b strings.Builder
		b.WriteString("Biggest victories:\n")
		for i, m := range matches {
			fmt.Fprintf(&b, "%d. %s\n", i+1, formatMatch(m))
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

func handleListCompetitions(st *store.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		type info struct{ min, max, count int }
		comps := map[string]*info{}
		for _, m := range st.Matches {
			c := comps[m.Competition]
			if c == nil {
				c = &info{min: 1 << 30}
				comps[m.Competition] = c
			}
			c.count++
			if m.Season != 0 {
				if m.Season < c.min {
					c.min = m.Season
				}
				if m.Season > c.max {
					c.max = m.Season
				}
			}
		}
		var b strings.Builder
		fmt.Fprintf(&b, "Loaded %d matches and %d players.\n", len(st.Matches), len(st.Players))
		b.WriteString("Competitions available:\n")
		for name, c := range comps {
			if c.max > 0 {
				fmt.Fprintf(&b, "- %s: %d matches (%d-%d)\n", name, c.count, c.min, c.max)
			} else {
				fmt.Fprintf(&b, "- %s: %d matches\n", name, c.count)
			}
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

// --- formatting helpers ---

// formatMatch renders one match as a single line, e.g.
// "2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Série A, Round 30)".
func formatMatch(m store.Match) string {
	date := "????-??-??"
	if m.HasDate {
		date = m.Date.Format("2006-01-02")
	}
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	var extra []string
	extra = append(extra, m.Competition)
	if m.Stage != "" {
		extra = append(extra, m.Stage)
	} else if m.Round != "" {
		extra = append(extra, "Round "+m.Round)
	}
	if m.Season != 0 && !m.HasDate {
		extra = append(extra, fmt.Sprintf("%d", m.Season))
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", date, m.HomeTeam, score, m.AwayTeam, strings.Join(extra, ", "))
}

func dash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}

// --- JSON schema helpers ---

func objSchema(props map[string]any, required []string) map[string]any {
	schema := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}
func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}
func enumProp(desc string, vals ...string) map[string]any {
	return map[string]any{"type": "string", "description": desc, "enum": vals}
}

// decode unmarshals raw JSON args, tolerating an empty/null arguments object.
func decode(raw json.RawMessage, v any) error {
	if len(raw) == 0 || string(raw) == "null" {
		return nil
	}
	if err := json.Unmarshal(raw, v); err != nil {
		return fmt.Errorf("invalid arguments: %w", err)
	}
	return nil
}
