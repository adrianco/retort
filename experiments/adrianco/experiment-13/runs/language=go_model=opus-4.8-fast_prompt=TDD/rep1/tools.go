// Package main — Brazilian Soccer MCP Server.
//
// tools.go: The MCP tool catalog and dispatch. Each tool exposes one query
// capability to the LLM with a JSON-Schema describing its arguments, and a
// handler that runs the query and renders a text answer. Argument extraction is
// lenient (missing optional fields default sensibly) but required fields are
// validated, surfacing user-facing errors via isError result content.
package main

import (
	"fmt"
	"strings"
)

// Tool is one callable MCP tool.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(ds *Dataset, args map[string]any) (string, error)
}

// args is a thin typed accessor over the decoded JSON arguments object.
type args map[string]any

func (a args) str(key string) string {
	if v, ok := a[key]; ok {
		if s, ok := v.(string); ok {
			return strings.TrimSpace(s)
		}
	}
	return ""
}

func (a args) intVal(key string) int {
	switch v := a[key].(type) {
	case float64:
		return int(v)
	case int:
		return v
	}
	return 0
}

// prop is a small helper to build a JSON-Schema property entry.
func prop(typ, desc string) map[string]any {
	return map[string]any{"type": typ, "description": desc}
}

// schema builds an object input schema with the given properties and required
// field names.
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

// venueFromArg maps a textual venue argument to a Venue.
func venueFromArg(s string) Venue {
	switch strings.ToLower(s) {
	case "home":
		return VenueHome
	case "away":
		return VenueAway
	default:
		return VenueAll
	}
}

// scopeSuffix builds a "( ... )" descriptor from season/competition/source for
// inclusion in formatted output headers.
func scopeSuffix(season int, competition, source string) string {
	var parts []string
	if competition != "" {
		parts = append(parts, competition)
	} else if source != "" {
		parts = append(parts, source)
	}
	if season != 0 {
		parts = append(parts, fmt.Sprintf("%d", season))
	}
	if len(parts) == 0 {
		return ""
	}
	return " (" + strings.Join(parts, " ") + ")"
}

// Tools returns the full ordered tool catalog.
func Tools() []Tool {
	return []Tool{
		{
			Name:        "search_matches",
			Description: "Search matches by team, opponent, competition, season or source. Returns dated results with scores. Useful for 'Show me all Flamengo vs Fluminense matches' or 'What matches did Palmeiras play in 2019?'.",
			InputSchema: schema(map[string]any{
				"team":        prop("string", "Team name (matches either home or away side). Accepts variations like 'Palmeiras' or 'Palmeiras-SP'."),
				"opponent":    prop("string", "Optional opponent to restrict to head-to-head meetings."),
				"competition": prop("string", "Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
				"season":      prop("integer", "Season year, e.g. 2019."),
				"source":      prop("string", "Exact dataset source: Brasileirao, Cup, Libertadores, Historico, BR-Football."),
				"limit":       prop("integer", "Maximum matches to display (default 25)."),
			}),
			Handler: handleSearchMatches,
		},
		{
			Name:        "team_record",
			Description: "Compute a team's win/draw/loss record, goals for/against and win rate, optionally restricted to a season, competition, or home/away venue. Answers 'What is Corinthians' home record in 2022?'.",
			InputSchema: schema(map[string]any{
				"team":        prop("string", "Team name (required)."),
				"season":      prop("integer", "Season year."),
				"competition": prop("string", "Competition filter."),
				"source":      prop("string", "Exact dataset source."),
				"venue":       prop("string", "One of 'home', 'away', or 'all' (default 'all')."),
			}, "team"),
			Handler: handleTeamRecord,
		},
		{
			Name:        "head_to_head",
			Description: "All-competition head-to-head record between two teams, with recent meetings. Answers 'Compare Palmeiras and Santos head-to-head'.",
			InputSchema: schema(map[string]any{
				"team_a": prop("string", "First team (required)."),
				"team_b": prop("string", "Second team (required)."),
			}, "team_a", "team_b"),
			Handler: handleHeadToHead,
		},
		{
			Name:        "standings",
			Description: "Compute a league table for a competition and season from match results (3 pts/win). Answers 'Who won the 2019 Brasileirão?'.",
			InputSchema: schema(map[string]any{
				"competition": prop("string", "Competition name, e.g. 'Brasileirão' (default Brasileirão)."),
				"season":      prop("integer", "Season year (required)."),
			}, "season"),
			Handler: handleStandings,
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality, club or position, sorted by overall rating. Answers 'Who are the top Brazilian players?' or 'Show me forwards from Santos'.",
			InputSchema: schema(map[string]any{
				"name":        prop("string", "Player name substring."),
				"nationality": prop("string", "Nationality, e.g. 'Brazil'."),
				"club":        prop("string", "Club name substring."),
				"position":    prop("string", "Position code, e.g. 'ST', 'GK', 'CB'."),
				"min_overall": prop("integer", "Minimum overall rating."),
				"limit":       prop("integer", "Maximum players to return (default 20)."),
			}),
			Handler: handleSearchPlayers,
		},
		{
			Name:        "competition_stats",
			Description: "Aggregate statistics (average goals per match, home/away win rates) and the biggest victories for a competition/season/source. Answers 'What's the average goals per match in the Brasileirão?'.",
			InputSchema: schema(map[string]any{
				"competition": prop("string", "Competition filter."),
				"season":      prop("integer", "Season year."),
				"source":      prop("string", "Exact dataset source."),
			}),
			Handler: handleCompetitionStats,
		},
	}
}

func handleSearchMatches(ds *Dataset, raw map[string]any) (string, error) {
	a := args(raw)
	f := MatchFilter{
		Team:        a.str("team"),
		Opponent:    a.str("opponent"),
		Competition: a.str("competition"),
		Source:      a.str("source"),
		Season:      a.intVal("season"),
	}
	limit := a.intVal("limit")
	if limit == 0 {
		limit = 25
	}
	return FormatMatches(ds.FindMatches(f), limit), nil
}

func handleTeamRecord(ds *Dataset, raw map[string]any) (string, error) {
	a := args(raw)
	team := a.str("team")
	if team == "" {
		return "", fmt.Errorf("argument 'team' is required")
	}
	venue := venueFromArg(a.str("venue"))
	f := MatchFilter{
		Season:      a.intVal("season"),
		Competition: a.str("competition"),
		Source:      a.str("source"),
	}
	rec := ds.TeamRecord(team, f, venue)
	scope := scopeSuffix(a.intVal("season"), a.str("competition"), a.str("source"))
	return FormatRecord(rec, venue, scope), nil
}

func handleHeadToHead(ds *Dataset, raw map[string]any) (string, error) {
	a := args(raw)
	ta, tb := a.str("team_a"), a.str("team_b")
	if ta == "" || tb == "" {
		return "", fmt.Errorf("arguments 'team_a' and 'team_b' are required")
	}
	return FormatH2H(ds.HeadToHead(ta, tb), 10), nil
}

func handleStandings(ds *Dataset, raw map[string]any) (string, error) {
	a := args(raw)
	season := a.intVal("season")
	if season == 0 {
		return "", fmt.Errorf("argument 'season' is required")
	}
	comp := a.str("competition")
	if comp == "" {
		comp = "Brasileirão"
	}
	return FormatStandings(comp, season, ds.Standings(comp, season)), nil
}

func handleSearchPlayers(ds *Dataset, raw map[string]any) (string, error) {
	a := args(raw)
	limit := a.intVal("limit")
	if limit == 0 {
		limit = 20
	}
	f := PlayerFilter{
		Name:        a.str("name"),
		Nationality: a.str("nationality"),
		Club:        a.str("club"),
		Position:    a.str("position"),
		MinOverall:  a.intVal("min_overall"),
		Limit:       limit,
	}
	return FormatPlayers(ds.SearchPlayers(f)), nil
}

func handleCompetitionStats(ds *Dataset, raw map[string]any) (string, error) {
	a := args(raw)
	f := MatchFilter{
		Competition: a.str("competition"),
		Source:      a.str("source"),
		Season:      a.intVal("season"),
	}
	stats := ds.Stats(f)
	biggest := ds.BiggestWins(f, 5)
	scope := scopeSuffix(a.intVal("season"), a.str("competition"), a.str("source"))
	return FormatStats(stats, biggest, scope), nil
}
