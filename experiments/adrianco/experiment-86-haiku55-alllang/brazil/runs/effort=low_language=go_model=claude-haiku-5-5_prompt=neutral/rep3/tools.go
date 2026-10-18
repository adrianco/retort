// MCP tool definitions and their text formatting.
//
// Each tool maps to one of the required query categories in TASK.md:
// matches, team records, players, competitions and statistics. Output is plain
// text laid out like the example answers in the spec so an LLM can quote it.

package main

import (
	"fmt"
	"strings"
	"time"
)

const defaultLimit = 20

// Tools returns the tool catalogue advertised by tools/list.
func Tools() []Tool {
	teamProp := map[string]any{"type": "string", "description": "Team name, with or without state suffix, e.g. \"Palmeiras\", \"Palmeiras-SP\", \"Sport Club Corinthians Paulista\""}
	competitionProp := map[string]any{"type": "string", "description": "Competition filter, e.g. \"Brasileirão Série A\", \"Copa do Brasil\", \"Copa Libertadores\", \"Série B\". Substring, accent-insensitive."}
	seasonProp := map[string]any{"type": "integer", "description": "Season year, e.g. 2023"}
	venueProp := map[string]any{"type": "string", "enum": []string{"home", "away"}, "description": "Restrict to home or away matches"}
	limitProp := map[string]any{"type": "integer", "description": "Maximum rows to return (default 20)"}

	return []Tool{
		{
			Name:        "search_matches",
			Description: "Find matches across all competitions by team, opponent, competition, season, venue or date range. Most recent first.",
			InputSchema: schema(map[string]any{
				"team":        teamProp,
				"opponent":    map[string]any{"type": "string", "description": "Second team; with team gives head-to-head fixtures"},
				"venue":       venueProp,
				"competition": competitionProp,
				"season":      seasonProp,
				"from":        map[string]any{"type": "string", "description": "Start date YYYY-MM-DD (inclusive)"},
				"to":          map[string]any{"type": "string", "description": "End date YYYY-MM-DD (inclusive)"},
				"limit":       limitProp,
			}),
		},
		{
			Name:        "team_record",
			Description: "Win/draw/loss record, goals for and against and win rate for a team, optionally by venue, season or competition.",
			InputSchema: schema(map[string]any{
				"team":        teamProp,
				"venue":       venueProp,
				"competition": competitionProp,
				"season":      seasonProp,
			}, "team"),
		},
		{
			Name:        "head_to_head",
			Description: "All-time head-to-head record between two teams in the dataset.",
			InputSchema: schema(map[string]any{
				"team":     teamProp,
				"opponent": map[string]any{"type": "string", "description": "The other team"},
				"limit":    limitProp,
			}, "team", "opponent"),
		},
		{
			Name:        "standings",
			Description: "League table for a season calculated from match results (3 points for a win, 1 for a draw).",
			InputSchema: schema(map[string]any{
				"season":      seasonProp,
				"competition": map[string]any{"type": "string", "description": "Defaults to \"Brasileirão Série A\""},
			}, "season"),
		},
		{
			Name:        "league_stats",
			Description: "Aggregate statistics for a competition and/or season: matches, goals per match, home/draw/away percentages.",
			InputSchema: schema(map[string]any{
				"season":      seasonProp,
				"competition": competitionProp,
			}),
		},
		{
			Name:        "biggest_wins",
			Description: "Matches with the largest winning margin, optionally for a competition or season.",
			InputSchema: schema(map[string]any{
				"season":      seasonProp,
				"competition": competitionProp,
				"limit":       limitProp,
			}),
		},
		{
			Name:        "search_players",
			Description: "Search FIFA player ratings data by name, nationality, club, position or minimum overall. Sorted by overall rating.",
			InputSchema: schema(map[string]any{
				"name":                 map[string]any{"type": "string", "description": "Name or part of a name, e.g. \"Gabriel Barbosa\", \"Messi\""},
				"nationality":          map[string]any{"type": "string", "description": "e.g. \"Brazil\""},
				"club":                 map[string]any{"type": "string", "description": "Club name or part of it, e.g. \"Flamengo\""},
				"position":             map[string]any{"type": "string", "description": "FIFA code (ST, LW, CB, GK...) or group FORWARD, MIDFIELDER, DEFENDER, GOALKEEPER"},
				"min_overall":          map[string]any{"type": "integer", "description": "Minimum overall rating"},
				"brazilian_clubs_only": map[string]any{"type": "boolean", "description": "Only players at clubs that appear in the Brasileirão match data"},
				"limit":                limitProp,
			}),
		},
	}
}

func schema(props map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

// Handler runs tools against a Dataset.
type Handler struct {
	DS *Dataset
}

// Call executes the named tool.
func (h *Handler) Call(name string, args map[string]any) (string, error) {
	switch name {
	case "search_matches":
		return h.searchMatches(args)
	case "team_record":
		return h.teamRecord(args)
	case "head_to_head":
		return h.headToHead(args)
	case "standings":
		return h.standings(args)
	case "league_stats":
		return h.leagueStats(args)
	case "biggest_wins":
		return h.biggestWins(args)
	case "search_players":
		return h.searchPlayers(args)
	default:
		return "", fmt.Errorf("unknown tool %q", name)
	}
}

// --- argument helpers -------------------------------------------------------

func argString(args map[string]any, key string) string {
	if v, ok := args[key].(string); ok {
		return strings.TrimSpace(v)
	}
	return ""
}

// argInt accepts JSON numbers (float64) and numeric strings.
func argInt(args map[string]any, key string) int {
	switch v := args[key].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case string:
		return atoi(v)
	}
	return 0
}

func argBool(args map[string]any, key string) bool {
	v, _ := args[key].(bool)
	return v
}

func argDate(args map[string]any, key string) (time.Time, error) {
	s := argString(args, key)
	if s == "" {
		return time.Time{}, nil
	}
	t, err := time.Parse("2006-01-02", s)
	if err != nil {
		return time.Time{}, fmt.Errorf("%s must be YYYY-MM-DD, got %q", key, s)
	}
	return t, nil
}

func argLimit(args map[string]any) int {
	n := argInt(args, "limit")
	if n <= 0 {
		return defaultLimit
	}
	return n
}

func argVenue(args map[string]any) (string, error) {
	v := strings.ToLower(argString(args, "venue"))
	if v != "" && v != "home" && v != "away" {
		return "", fmt.Errorf("venue must be \"home\" or \"away\", got %q", v)
	}
	return v, nil
}

// --- tools ------------------------------------------------------------------

func (h *Handler) searchMatches(args map[string]any) (string, error) {
	from, err := argDate(args, "from")
	if err != nil {
		return "", err
	}
	to, err := argDate(args, "to")
	if err != nil {
		return "", err
	}
	venue, err := argVenue(args)
	if err != nil {
		return "", err
	}
	f := MatchFilter{
		Team:        argString(args, "team"),
		Opponent:    argString(args, "opponent"),
		Venue:       venue,
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		From:        from,
	}
	if !to.IsZero() {
		f.To = to.Add(24*time.Hour - time.Nanosecond)
	}
	if f.Team == "" && f.Opponent == "" && f.Competition == "" && f.Season == 0 && from.IsZero() && to.IsZero() {
		return "", fmt.Errorf("give at least one of team, opponent, competition, season or a date range")
	}

	matches := h.DS.FindMatches(f)
	if len(matches) == 0 {
		return "No matches found for those criteria.", nil
	}
	title := describeFilter(f)
	return formatMatches(title, matches, argLimit(args)), nil
}

func (h *Handler) teamRecord(args map[string]any) (string, error) {
	team := argString(args, "team")
	if team == "" {
		return "", fmt.Errorf("team is required")
	}
	venue, err := argVenue(args)
	if err != nil {
		return "", err
	}
	f := MatchFilter{
		Team:        team,
		Venue:       venue,
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
	}
	rec, _ := h.DS.TeamRecord(f)
	if rec.Played == 0 {
		return fmt.Sprintf("No matches found for %s with these criteria.", team), nil
	}
	label := describeFilter(f)
	return fmt.Sprintf("%s record%s:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %.1f%%",
		team, suffix(label), rec.Played, rec.Wins, rec.Draws, rec.Losses, rec.GoalsFor, rec.GoalsAgainst, rec.WinRate()), nil
}

func (h *Handler) headToHead(args map[string]any) (string, error) {
	a := argString(args, "team")
	b := argString(args, "opponent")
	if a == "" || b == "" {
		return "", fmt.Errorf("team and opponent are required")
	}
	rec, matches := h.DS.HeadToHead(a, b)
	if rec.Played == 0 {
		return fmt.Sprintf("No matches between %s and %s in the dataset.", a, b), nil
	}
	var sb strings.Builder
	fmt.Fprintf(&sb, "%s vs %s head-to-head in dataset:\n", a, b)
	for _, m := range firstN(matches, argLimit(args)) {
		fmt.Fprintf(&sb, "- %s\n", formatMatchLine(m))
	}
	if rest := len(matches) - argLimit(args); rest > 0 {
		fmt.Fprintf(&sb, "- ... (%d more matches in dataset)\n", rest)
	}
	draws := rec.Draws
	fmt.Fprintf(&sb, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws",
		a, rec.Wins, b, rec.Losses, draws)
	return sb.String(), nil
}

func (h *Handler) standings(args map[string]any) (string, error) {
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	comp := argString(args, "competition")
	if comp == "" {
		comp = CompBrasileirao
	}
	table := h.DS.Standings(comp, season)
	if len(table) == 0 {
		return fmt.Sprintf("No %s matches for %d in the dataset.", comp, season), nil
	}
	var sb strings.Builder
	fmt.Fprintf(&sb, "%d %s Final Standings (calculated from matches):\n", season, comp)
	for i, r := range table {
		fmt.Fprintf(&sb, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d)", i+1, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst)
		if i == 0 {
			sb.WriteString(" - Leader")
		}
		sb.WriteString("\n")
	}
	return strings.TrimRight(sb.String(), "\n"), nil
}

func (h *Handler) leagueStats(args map[string]any) (string, error) {
	f := MatchFilter{Competition: argString(args, "competition"), Season: argInt(args, "season")}
	if f.Competition == "" && f.Season == 0 {
		return "", fmt.Errorf("give a competition, a season, or both")
	}
	s := h.DS.Aggregate(f)
	if s.Matches == 0 {
		return "No matches found for those criteria.", nil
	}
	return fmt.Sprintf("Statistics%s:\n- Matches: %d\n- Average goals per match: %.2f\n- Home win rate: %.1f%%\n- Draw rate: %.1f%%\n- Away win rate: %.1f%%",
		suffix(describeFilter(f)), s.Matches, s.GoalsPerMatch, s.HomeWinPct, s.DrawPct, s.AwayWinPct), nil
}

func (h *Handler) biggestWins(args map[string]any) (string, error) {
	f := MatchFilter{Competition: argString(args, "competition"), Season: argInt(args, "season")}
	matches := h.DS.BiggestWins(f, argLimit(args))
	if len(matches) == 0 {
		return "No matches found for those criteria.", nil
	}
	var sb strings.Builder
	fmt.Fprintf(&sb, "Biggest victories%s:\n", suffix(describeFilter(f)))
	for i, m := range matches {
		fmt.Fprintf(&sb, "%d. %s\n", i+1, formatMatchLine(m))
	}
	return strings.TrimRight(sb.String(), "\n"), nil
}

func (h *Handler) searchPlayers(args map[string]any) (string, error) {
	f := PlayerFilter{
		Name:               argString(args, "name"),
		Nationality:        argString(args, "nationality"),
		Club:               argString(args, "club"),
		Position:           argString(args, "position"),
		MinOverall:         argInt(args, "min_overall"),
		BrazilianClubsOnly: argBool(args, "brazilian_clubs_only"),
	}
	if f.Name == "" && f.Nationality == "" && f.Club == "" && f.Position == "" && f.MinOverall == 0 && !f.BrazilianClubsOnly {
		return "", fmt.Errorf("give at least one of name, nationality, club, position, min_overall or brazilian_clubs_only")
	}
	players := h.DS.SearchPlayers(f)
	if len(players) == 0 {
		return "No players found for those criteria.", nil
	}
	limit := argLimit(args)
	var sb strings.Builder
	fmt.Fprintf(&sb, "%d player(s) found", len(players))
	if len(players) > limit {
		fmt.Fprintf(&sb, ", showing top %d", limit)
	}
	sb.WriteString(":\n")
	for i, p := range firstN(players, limit) {
		fmt.Fprintf(&sb, "%d. %s - Overall: %d, Potential: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, p.Club, p.Nationality, p.Age)
	}
	return strings.TrimRight(sb.String(), "\n"), nil
}

// --- formatting -------------------------------------------------------------

func formatMatches(title string, matches []Match, limit int) string {
	var sb strings.Builder
	if title != "" {
		fmt.Fprintf(&sb, "%s:\n", title)
	}
	for _, m := range firstN(matches, limit) {
		fmt.Fprintf(&sb, "- %s\n", formatMatchLine(m))
	}
	if rest := len(matches) - limit; rest > 0 {
		fmt.Fprintf(&sb, "- ... (%d more matches in dataset)\n", rest)
	}
	fmt.Fprintf(&sb, "\n%d match(es) total", len(matches))
	return sb.String()
}

// formatMatchLine renders "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)".
func formatMatchLine(m Match) string {
	extra := m.Competition
	if m.Round != "" {
		extra += ", " + m.Round
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)",
		m.Date.Format("2006-01-02"), displayName(m.Home), m.HomeGoals, m.AwayGoals, displayName(m.Away), extra)
}

// describeFilter gives a short human label for a filter, e.g. "Palmeiras, 2023".
func describeFilter(f MatchFilter) string {
	var parts []string
	if f.Team != "" {
		parts = append(parts, f.Team)
	}
	if f.Opponent != "" {
		parts = append(parts, "vs "+f.Opponent)
	}
	if f.Venue != "" {
		parts = append(parts, f.Venue+" matches")
	}
	if f.Competition != "" {
		parts = append(parts, f.Competition)
	}
	if f.Season != 0 {
		parts = append(parts, fmt.Sprint(f.Season))
	}
	return strings.Join(parts, ", ")
}

func suffix(label string) string {
	if label == "" {
		return ""
	}
	return " (" + label + ")"
}

func firstN[T any](xs []T, n int) []T {
	if n >= 0 && len(xs) > n {
		return xs[:n]
	}
	return xs
}
