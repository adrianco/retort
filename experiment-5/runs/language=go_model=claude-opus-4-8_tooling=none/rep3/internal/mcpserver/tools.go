// Context: tool definitions and handlers. Each tool wraps a soccer.Store query
// and returns a formatted text answer. Argument parsing is tolerant: numbers may
// arrive as JSON numbers or strings, and missing optional args use zero values.
package mcpserver

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/soccer"
)

// schema is a tiny helper to build a JSON-Schema object for a tool's inputs.
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

// registerTools wires up every tool's schema and handler.
func (s *Server) registerTools() {
	add := func(t tool, h func(map[string]any) (string, error)) {
		s.tools = append(s.tools, t)
		s.handlers[t.Name] = h
	}

	add(tool{
		Name:        "search_matches",
		Description: "Search matches by team, opponent, competition, season and/or date range across all Brazilian soccer datasets (Brasileirão, Copa do Brasil, Libertadores, Série B/C). Returns a dated list of results.",
		InputSchema: schema(map[string]any{
			"team":        strProp("Team name (matches home or away unless 'venue' is set), e.g. 'Flamengo'."),
			"opponent":    strProp("Opponent team name; restricts to matches between team and opponent."),
			"competition": strProp("Competition filter: 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'."),
			"season":      intProp("Season year, e.g. 2019."),
			"season_to":   intProp("Upper bound for a season range (use with 'season')."),
			"date_from":   strProp("Inclusive start date YYYY-MM-DD."),
			"date_to":     strProp("Inclusive end date YYYY-MM-DD."),
			"venue":       strProp("Restrict 'team' to 'home' or 'away'."),
			"limit":       intProp("Max results to show (default 25)."),
		}),
	}, s.searchMatches)

	add(tool{
		Name:        "team_record",
		Description: "Win/draw/loss record, goals for/against, points and win rate for a team, optionally filtered by season, competition and venue (home/away).",
		InputSchema: schema(map[string]any{
			"team":        strProp("Team name, e.g. 'Corinthians'."),
			"season":      intProp("Season year."),
			"competition": strProp("Competition filter."),
			"venue":       strProp("'home' or 'away' to restrict the record."),
		}, "team"),
	}, s.teamRecord)

	add(tool{
		Name:        "head_to_head",
		Description: "Head-to-head record between two teams: wins each way, draws, goals and the list of meetings.",
		InputSchema: schema(map[string]any{
			"team_a":      strProp("First team."),
			"team_b":      strProp("Second team."),
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season filter."),
			"limit":       intProp("Max meetings to list (default 20)."),
		}, "team_a", "team_b"),
	}, s.headToHead)

	add(tool{
		Name:        "search_players",
		Description: "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club, position and/or minimum overall rating. Results are sorted by rating.",
		InputSchema: schema(map[string]any{
			"name":        strProp("Player name substring, e.g. 'Gabriel Barbosa'."),
			"nationality": strProp("Nationality, e.g. 'Brazil'."),
			"club":        strProp("Club name, e.g. 'Flamengo'."),
			"position":    strProp("Position code, e.g. 'ST', 'GK', 'CB'."),
			"min_overall": intProp("Minimum FIFA overall rating."),
			"limit":       intProp("Max players to show (default 20)."),
		}),
	}, s.searchPlayers)

	add(tool{
		Name:        "standings",
		Description: "Compute a league table (points, W/D/L, goals) for a competition and season directly from match results. Defaults to the Brasileirão.",
		InputSchema: schema(map[string]any{
			"competition": strProp("Competition (default 'Brasileirão')."),
			"season":      intProp("Season year, e.g. 2019."),
			"limit":       intProp("Max rows (default: full table)."),
		}, "season"),
	}, s.standings)

	add(tool{
		Name:        "competition_stats",
		Description: "Aggregate statistics for a competition/season (or a single team): matches, total and average goals per match, home/away win and draw rates.",
		InputSchema: schema(map[string]any{
			"competition": strProp("Competition filter."),
			"season":      intProp("Season year."),
			"team":        strProp("Optional: restrict to matches involving this team."),
		}),
	}, s.competitionStats)

	add(tool{
		Name:        "biggest_wins",
		Description: "List the most lopsided results (largest goal margin) for a competition/season or team.",
		InputSchema: schema(map[string]any{
			"competition": strProp("Competition filter."),
			"season":      intProp("Season year."),
			"team":        strProp("Optional team filter."),
			"limit":       intProp("Max results (default 10)."),
		}),
	}, s.biggestWins)

	add(tool{
		Name:        "dataset_info",
		Description: "Summary of the loaded datasets: match and player counts and the competitions available.",
		InputSchema: schema(map[string]any{}),
	}, s.datasetInfo)
}

// --- argument helpers -----------------------------------------------------

func argStr(args map[string]any, key string) string {
	v, ok := args[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	default:
		return strings.TrimSpace(fmt.Sprintf("%v", t))
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
	case string:
		n, _ := strconv.Atoi(strings.TrimSpace(t))
		return n
	default:
		return 0
	}
}

func argIntDefault(args map[string]any, key string, def int) int {
	if _, ok := args[key]; !ok {
		return def
	}
	if v := argInt(args, key); v != 0 {
		return v
	}
	return def
}

func parseDateArg(s string) time.Time {
	if s == "" {
		return time.Time{}
	}
	for _, layout := range []string{"2006-01-02", "02/01/2006", "2006-01-02 15:04:05"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// --- handlers -------------------------------------------------------------

func (s *Server) searchMatches(args map[string]any) (string, error) {
	limit := argIntDefault(args, "limit", 25)
	f := soccer.MatchFilter{
		Team:        argStr(args, "team"),
		Opponent:    argStr(args, "opponent"),
		Competition: argStr(args, "competition"),
		Season:      argInt(args, "season"),
		SeasonTo:    argInt(args, "season_to"),
		DateFrom:    parseDateArg(argStr(args, "date_from")),
		DateTo:      parseDateArg(argStr(args, "date_to")),
		Venue:       strings.ToLower(argStr(args, "venue")),
	}
	matches := s.store.SearchMatches(f)
	title := describeMatchQuery(f, len(matches))
	return soccer.FormatMatchList(title, matches, limit), nil
}

func describeMatchQuery(f soccer.MatchFilter, n int) string {
	var parts []string
	if f.Team != "" {
		parts = append(parts, f.Team)
	}
	if f.Opponent != "" {
		parts = append(parts, "vs "+f.Opponent)
	}
	if f.Competition != "" {
		parts = append(parts, "in "+f.Competition)
	}
	if f.Season != 0 {
		if f.SeasonTo != 0 {
			parts = append(parts, fmt.Sprintf("%d-%d", f.Season, f.SeasonTo))
		} else {
			parts = append(parts, fmt.Sprintf("%d", f.Season))
		}
	}
	head := "Matches"
	if len(parts) > 0 {
		head += " " + strings.Join(parts, " ")
	}
	return fmt.Sprintf("%s (%d found):", head, n)
}

func (s *Server) teamRecord(args map[string]any) (string, error) {
	team := argStr(args, "team")
	if team == "" {
		return "", fmt.Errorf("'team' is required")
	}
	f := soccer.MatchFilter{
		Season:      argInt(args, "season"),
		Competition: argStr(args, "competition"),
		Venue:       strings.ToLower(argStr(args, "venue")),
	}
	rec := s.store.TeamStats(team, f)
	if rec.Matches == 0 {
		return fmt.Sprintf("No matches found for %q with the given filters.", team), nil
	}
	return soccer.FormatTeamRecord(rec), nil
}

func (s *Server) headToHead(args map[string]any) (string, error) {
	a := argStr(args, "team_a")
	b := argStr(args, "team_b")
	if a == "" || b == "" {
		return "", fmt.Errorf("'team_a' and 'team_b' are required")
	}
	limit := argIntDefault(args, "limit", 20)
	f := soccer.MatchFilter{
		Competition: argStr(args, "competition"),
		Season:      argInt(args, "season"),
	}
	h := s.store.HeadToHead(a, b, f)
	if len(h.Matches) == 0 {
		return fmt.Sprintf("No head-to-head matches found between %q and %q.", a, b), nil
	}
	return soccer.FormatHeadToHead(h, limit), nil
}

func (s *Server) searchPlayers(args map[string]any) (string, error) {
	limit := argIntDefault(args, "limit", 20)
	f := soccer.PlayerFilter{
		Name:        argStr(args, "name"),
		Nationality: argStr(args, "nationality"),
		Club:        argStr(args, "club"),
		Position:    argStr(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
	}
	players := s.store.SearchPlayers(f)
	title := fmt.Sprintf("Players (%d found):", len(players))
	return soccer.FormatPlayerList(title, players, limit), nil
}

func (s *Server) standings(args map[string]any) (string, error) {
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("'season' is required")
	}
	comp := argStr(args, "competition")
	if comp == "" {
		comp = soccer.CompBrasileirao
	}
	limit := argInt(args, "limit")
	f := soccer.MatchFilter{Competition: comp, Season: season}
	table := s.store.Standings(f)
	title := fmt.Sprintf("%d %s Standings (calculated from matches):", season, comp)
	return soccer.FormatStandings(title, table, limit), nil
}

func (s *Server) competitionStats(args map[string]any) (string, error) {
	f := soccer.MatchFilter{
		Competition: argStr(args, "competition"),
		Season:      argInt(args, "season"),
		Team:        argStr(args, "team"),
	}
	c := s.store.CompetitionStats(f)
	if c.Matches == 0 {
		return "No matches found with the given filters.", nil
	}
	return soccer.FormatCompetitionStats(c), nil
}

func (s *Server) biggestWins(args map[string]any) (string, error) {
	limit := argIntDefault(args, "limit", 10)
	f := soccer.MatchFilter{
		Competition: argStr(args, "competition"),
		Season:      argInt(args, "season"),
		Team:        argStr(args, "team"),
	}
	matches := s.store.BiggestWins(f, limit)
	return soccer.FormatMatchList("Biggest victories:", matches, limit), nil
}

func (s *Server) datasetInfo(args map[string]any) (string, error) {
	comps := map[string]int{}
	for _, m := range s.store.Matches {
		comps[m.Competition]++
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Loaded datasets:\n")
	fmt.Fprintf(&b, "- Matches: %d\n", len(s.store.Matches))
	fmt.Fprintf(&b, "- Players: %d\n", len(s.store.Players))
	b.WriteString("Competitions:\n")
	for comp, n := range comps {
		fmt.Fprintf(&b, "- %s: %d matches\n", comp, n)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}
