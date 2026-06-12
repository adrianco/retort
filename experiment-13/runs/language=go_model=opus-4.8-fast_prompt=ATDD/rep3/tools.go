// Context: The MCP tool surface for the Brazilian Soccer knowledge graph. This
// file defines the six tools the server advertises and the handlers that turn a
// tools/call request into a domain query against the store and a formatted text
// answer. This is the system's public interface: the acceptance tests (and any
// real LLM client) drive everything through these tool names and JSON argument
// schemas. Each handler validates/coerces its arguments, runs the relevant
// store query, and returns human-readable text in the language of the domain.
package main

import (
	"fmt"
	"strings"
	"time"
)

// ToolHandler executes a tool given decoded JSON arguments.
type ToolHandler func(store *Store, args map[string]any) (string, error)

// Tool bundles an advertised tool's metadata with its handler.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     ToolHandler
}

// buildTools returns the ordered tool registry.
func buildTools() []Tool {
	return []Tool{
		{
			Name:        "find_matches",
			Description: "Find soccer matches by team, opponent, competition, season, or date range across all Brazilian datasets (Brasileirão, Copa do Brasil, Copa Libertadores). Returns results with scores; when both a team and an opponent are given, also returns the head-to-head summary.",
			InputSchema: objectSchema(map[string]any{
				"team":        strSchema("Team name (matches home or away), e.g. 'Flamengo'"),
				"opponent":    strSchema("Opponent team name to restrict to matches between the two teams"),
				"competition": strSchema("Competition filter: Brasileirão, Copa do Brasil, or Libertadores"),
				"season":      intSchema("Season year, e.g. 2019"),
				"start_date":  strSchema("Inclusive start date (YYYY-MM-DD)"),
				"end_date":    strSchema("Inclusive end date (YYYY-MM-DD)"),
				"limit":       intSchema("Maximum number of matches to list (default 50)"),
			}, nil),
			Handler: handleFindMatches,
		},
		{
			Name:        "team_record",
			Description: "Compute a team's win/draw/loss record, goals for/against and win rate, optionally filtered by season, competition, and venue (home/away).",
			InputSchema: objectSchema(map[string]any{
				"team":        strSchema("Team name, e.g. 'Corinthians'"),
				"season":      intSchema("Season year, e.g. 2022"),
				"competition": strSchema("Competition filter (Brasileirão, Copa do Brasil, Libertadores)"),
				"venue":       strSchema("Venue filter: 'home', 'away', or 'any' (default)"),
			}, []string{"team"}),
			Handler: handleTeamRecord,
		},
		{
			Name:        "head_to_head",
			Description: "Compare two teams head-to-head: total meetings, wins for each side, draws and goals, with the list of matches.",
			InputSchema: objectSchema(map[string]any{
				"team_a":      strSchema("First team name"),
				"team_b":      strSchema("Second team name"),
				"competition": strSchema("Optional competition filter"),
				"season":      intSchema("Optional season year filter"),
			}, []string{"team_a", "team_b"}),
			Handler: handleHeadToHead,
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club, and/or position. Results are sorted by overall rating, highest first.",
			InputSchema: objectSchema(map[string]any{
				"name":        strSchema("Full or partial player name"),
				"nationality": strSchema("Nationality, e.g. 'Brazil'"),
				"club":        strSchema("Club name (substring match)"),
				"position":    strSchema("Position code, e.g. 'ST', 'GK'"),
				"limit":       intSchema("Maximum number of players to list (default 25)"),
			}, nil),
			Handler: handleSearchPlayers,
		},
		{
			Name:        "competition_standings",
			Description: "Compute the final league standings for a competition and season from match results (3 points for a win, 1 for a draw), sorted by points then goal difference.",
			InputSchema: objectSchema(map[string]any{
				"competition": strSchema("Competition, e.g. 'Brasileirão'"),
				"season":      intSchema("Season year, e.g. 2019"),
			}, []string{"competition", "season"}),
			Handler: handleStandings,
		},
		{
			Name:        "match_statistics",
			Description: "Compute aggregate statistics over a set of matches: average goals per match, home/away win and draw rates, and the biggest victories. Optionally filter by competition and season.",
			InputSchema: objectSchema(map[string]any{
				"competition": strSchema("Optional competition filter"),
				"season":      intSchema("Optional season year filter"),
				"team":        strSchema("Optional team filter (matches involving the team)"),
				"limit":       intSchema("How many biggest victories to list (default 5)"),
			}, nil),
			Handler: handleStatistics,
		},
	}
}

// --- handlers --------------------------------------------------------------

func handleFindMatches(store *Store, args map[string]any) (string, error) {
	f := MatchFilter{}
	team := argString(args, "team")
	opponent := argString(args, "opponent")
	if team != "" {
		f.HasTeam = true
		f.Team = parseTeamQuery(team)
	}
	if opponent != "" {
		if team == "" {
			return "", fmt.Errorf("'opponent' requires 'team' to also be specified")
		}
		f.HasOpponent = true
		f.Opponent = parseTeamQuery(opponent)
	}
	f.Competition = resolveCompetition(argString(args, "competition"))
	if season, ok := argInt(args, "season"); ok {
		f.HasSeason = true
		f.Season = season
	}
	if d, ok, err := argDate(args, "start_date"); err != nil {
		return "", err
	} else if ok {
		f.HasStart = true
		f.Start = d
	}
	if d, ok, err := argDate(args, "end_date"); err != nil {
		return "", err
	} else if ok {
		f.HasEnd = true
		// Make end-of-day inclusive.
		f.End = d.Add(24*time.Hour - time.Second)
	}

	matches := store.FindMatches(f)

	label := describeMatchScope(team, opponent, argString(args, "competition"), f)
	var h2h *HeadToHead
	aName, bName := team, opponent
	if f.HasTeam && f.HasOpponent {
		hh := store.ComputeHeadToHead(f.Team, f.Opponent, MatchFilter{
			Competition: f.Competition, Season: f.Season, HasSeason: f.HasSeason,
		})
		h2h = &hh
		aName = displayName(matches, f.Team, team)
		bName = displayName(matches, f.Opponent, opponent)
		label = aName + " vs " + bName
	}

	// Apply an optional display limit to the listed matches.
	if limit, ok := argInt(args, "limit"); ok && limit >= 0 && limit < len(matches) {
		matches = matches[:limit]
	}
	return formatFindMatches(label, matches, h2h, aName, bName), nil
}

func handleTeamRecord(store *Store, args map[string]any) (string, error) {
	team := argString(args, "team")
	if team == "" {
		return "", fmt.Errorf("'team' is required")
	}
	f := MatchFilter{HasTeam: true, Team: parseTeamQuery(team)}
	f.Competition = resolveCompetition(argString(args, "competition"))
	if season, ok := argInt(args, "season"); ok {
		f.HasSeason = true
		f.Season = season
	}
	venue := strings.ToLower(argString(args, "venue"))
	if venue == "any" {
		venue = ""
	}
	if venue != "" && venue != "home" && venue != "away" {
		return "", fmt.Errorf("'venue' must be 'home', 'away', or 'any'")
	}
	f.Venue = venue

	rec := store.ComputeTeamRecord(f)
	display := displayName(store.FindMatches(f), f.Team, team)
	return formatTeamRecord(display, f.Season, f.HasSeason, f.Competition, venue, rec), nil
}

func handleHeadToHead(store *Store, args map[string]any) (string, error) {
	a := argString(args, "team_a")
	b := argString(args, "team_b")
	if a == "" || b == "" {
		return "", fmt.Errorf("both 'team_a' and 'team_b' are required")
	}
	base := MatchFilter{}
	base.Competition = resolveCompetition(argString(args, "competition"))
	if season, ok := argInt(args, "season"); ok {
		base.HasSeason = true
		base.Season = season
	}
	qa, qb := parseTeamQuery(a), parseTeamQuery(b)
	h := store.ComputeHeadToHead(qa, qb, base)
	aName := displayName(h.Matches, qa, a)
	bName := displayName(h.Matches, qb, b)
	return formatHeadToHead(aName, bName, h), nil
}

func handleSearchPlayers(store *Store, args map[string]any) (string, error) {
	f := PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
	}
	players := store.SearchPlayers(f)
	limit := 25
	if l, ok := argInt(args, "limit"); ok && l >= 0 {
		limit = l
	}
	return formatPlayers(players, limit), nil
}

func handleStandings(store *Store, args map[string]any) (string, error) {
	comp := resolveCompetition(argString(args, "competition"))
	if comp == "" {
		return "", fmt.Errorf("'competition' is required")
	}
	season, ok := argInt(args, "season")
	if !ok {
		return "", fmt.Errorf("'season' is required")
	}
	table := store.ComputeStandings(comp, season)
	return formatStandings(comp, season, table), nil
}

func handleStatistics(store *Store, args map[string]any) (string, error) {
	f := MatchFilter{}
	f.Competition = resolveCompetition(argString(args, "competition"))
	if season, ok := argInt(args, "season"); ok {
		f.HasSeason = true
		f.Season = season
	}
	if team := argString(args, "team"); team != "" {
		f.HasTeam = true
		f.Team = parseTeamQuery(team)
	}
	top := 5
	if l, ok := argInt(args, "limit"); ok && l >= 0 {
		top = l
	}
	stat := store.ComputeStatistics(f, top)
	return formatStatistics(describeStatScope(argString(args, "competition"), f), stat), nil
}

// --- helpers ---------------------------------------------------------------

// displayName resolves a friendly display name for a team query, using the form
// found in the data when available and falling back to the query string.
func displayName(matches []Match, q teamQuery, fallback string) string {
	for _, m := range matches {
		if q.matchesSide(m.HomeTeamNorm, m.HomeState) {
			return m.HomeTeam
		}
		if q.matchesSide(m.AwayTeamNorm, m.AwayState) {
			return m.AwayTeam
		}
	}
	return displayTeam(fallback)
}

func describeMatchScope(team, opponent, comp string, f MatchFilter) string {
	phrase := ""
	add := func(token string) {
		if phrase == "" {
			phrase = token
		} else {
			phrase += " in " + token
		}
	}
	if team != "" {
		add(displayTeam(team))
	}
	if comp != "" && f.Competition != "" {
		add(f.Competition)
	}
	if f.HasSeason {
		add(itoa(f.Season))
	}
	if phrase == "" {
		return "all matches"
	}
	return phrase
}

func describeStatScope(comp string, f MatchFilter) string {
	parts := []string{}
	if f.Competition != "" {
		parts = append(parts, f.Competition)
	}
	if f.HasSeason {
		parts = append(parts, itoa(f.Season))
	}
	if f.HasTeam {
		parts = append(parts, "team filter")
	}
	if len(parts) == 0 {
		return "all matches"
	}
	return strings.Join(parts, " ")
}

// --- argument coercion -----------------------------------------------------

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

func argInt(args map[string]any, key string) (int, bool) {
	v, ok := args[key]
	if !ok || v == nil {
		return 0, false
	}
	switch n := v.(type) {
	case float64:
		return int(n), true
	case int:
		return n, true
	case string:
		return parseGoal(n) // reuses lenient int parsing
	default:
		return 0, false
	}
}

func argDate(args map[string]any, key string) (time.Time, bool, error) {
	s := argString(args, key)
	if s == "" {
		return time.Time{}, false, nil
	}
	d, ok := parseDate(s)
	if !ok {
		return time.Time{}, false, fmt.Errorf("invalid date %q for %q (use YYYY-MM-DD)", s, key)
	}
	return d, true, nil
}

// --- JSON schema builders --------------------------------------------------

func objectSchema(props map[string]any, required []string) map[string]any {
	schema := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func strSchema(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}

func intSchema(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}
