package mcp

import (
	"fmt"
	"strings"
	"time"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/query"
)

// RegisterAll wires up the soccer tools against the dataset.
func RegisterAll(s *Server, ds *data.Dataset) {
	s.Register(Tool{
		Name:        "find_matches",
		Description: "Find matches by team(s), date range, competition, or season. Returns a formatted list.",
		InputSchema: schemaObject(map[string]any{
			"team":        schemaString("Any team (home or away)"),
			"opponent":    schemaString("Opponent paired with team — find team vs opponent"),
			"home_team":   schemaString("Filter by home team only"),
			"away_team":   schemaString("Filter by away team only"),
			"competition": schemaString("Competition name (e.g., Brasileirão, Copa do Brasil, Libertadores)"),
			"season":      schemaInt("Season (year)"),
			"from":        schemaString("Start date (YYYY-MM-DD)"),
			"to":          schemaString("End date (YYYY-MM-DD)"),
			"limit":       schemaInt("Max matches to return (default 25)"),
		}, nil),
		Handler: func(args map[string]any) (string, error) {
			f := query.MatchFilter{
				Team:        argString(args, "team"),
				Opponent:    argString(args, "opponent"),
				HomeTeam:    argString(args, "home_team"),
				AwayTeam:    argString(args, "away_team"),
				Competition: argString(args, "competition"),
				Season:      argInt(args, "season"),
				Limit:       argIntDefault(args, "limit", 25),
			}
			if v := argString(args, "from"); v != "" {
				if t, _, err := parseDateArg(v); err == nil {
					f.From = t
				}
			}
			if v := argString(args, "to"); v != "" {
				if t, _, err := parseDateArg(v); err == nil {
					f.To = t.Add(24 * time.Hour)
				}
			}
			matches := query.FindMatches(ds, f)
			return formatMatches(matches), nil
		},
	})

	s.Register(Tool{
		Name:        "head_to_head",
		Description: "Aggregate head-to-head record (wins/losses/draws, goals) between two teams across all competitions.",
		InputSchema: schemaObject(map[string]any{
			"team_a": schemaString("First team"),
			"team_b": schemaString("Second team"),
			"limit":  schemaInt("Max matches to include in the listing (default 10)"),
		}, []string{"team_a", "team_b"}),
		Handler: func(args map[string]any) (string, error) {
			a := argString(args, "team_a")
			b := argString(args, "team_b")
			if a == "" || b == "" {
				return "", fmt.Errorf("team_a and team_b are required")
			}
			h := query.ComputeHeadToHead(ds, a, b)
			return formatHeadToHead(h, argIntDefault(args, "limit", 10)), nil
		},
	})

	s.Register(Tool{
		Name:        "team_stats",
		Description: "Compute win/loss/draw and goal totals for a team, optionally scoped to competition, season, or home/away venue.",
		InputSchema: schemaObject(map[string]any{
			"team":        schemaString("Team name"),
			"competition": schemaString("Competition name"),
			"season":      schemaInt("Season (year)"),
			"venue":       schemaEnum("Restrict to home or away matches", []string{"home", "away", "any"}),
		}, []string{"team"}),
		Handler: func(args map[string]any) (string, error) {
			team := argString(args, "team")
			if team == "" {
				return "", fmt.Errorf("team is required")
			}
			venue := argString(args, "venue")
			if venue == "any" {
				venue = ""
			}
			r := query.TeamStats(ds, team, argString(args, "competition"), argInt(args, "season"), venue)
			return formatRecord(r), nil
		},
	})

	s.Register(Tool{
		Name:        "top_scoring_teams",
		Description: "List top-scoring teams in a competition/season.",
		InputSchema: schemaObject(map[string]any{
			"competition": schemaString("Competition name"),
			"season":      schemaInt("Season (year)"),
			"limit":       schemaInt("Number of teams to return (default 10)"),
		}, nil),
		Handler: func(args map[string]any) (string, error) {
			records := query.TopScoringTeams(ds, argString(args, "competition"), argInt(args, "season"), argIntDefault(args, "limit", 10))
			return formatTopScorers(records), nil
		},
	})

	s.Register(Tool{
		Name:        "search_players",
		Description: "Search FIFA player data by name, nationality, club, position, and overall rating.",
		InputSchema: schemaObject(map[string]any{
			"name":        schemaString("Substring of player name"),
			"nationality": schemaString("Player nationality, e.g. Brazil"),
			"club":        schemaString("Substring of club"),
			"position":    schemaString("Position code, e.g. ST, CB"),
			"min_overall": schemaInt("Minimum overall rating"),
			"max_overall": schemaInt("Maximum overall rating"),
			"limit":       schemaInt("Max players to return (default 20)"),
		}, nil),
		Handler: func(args map[string]any) (string, error) {
			f := query.PlayerFilter{
				NameContains: argString(args, "name"),
				Nationality:  argString(args, "nationality"),
				Club:         argString(args, "club"),
				Position:     argString(args, "position"),
				MinOverall:   argInt(args, "min_overall"),
				MaxOverall:   argInt(args, "max_overall"),
				Limit:        argIntDefault(args, "limit", 20),
			}
			return formatPlayers(query.SearchPlayers(ds, f)), nil
		},
	})

	s.Register(Tool{
		Name:        "top_clubs_by_nationality",
		Description: "Aggregate FIFA roster counts by club for a nationality (e.g. Brazilian players per club).",
		InputSchema: schemaObject(map[string]any{
			"nationality": schemaString("Player nationality"),
			"limit":       schemaInt("Max clubs to return (default 15)"),
		}, []string{"nationality"}),
		Handler: func(args map[string]any) (string, error) {
			nat := argString(args, "nationality")
			if nat == "" {
				return "", fmt.Errorf("nationality is required")
			}
			out := query.TopClubsByNationality(ds, nat, argIntDefault(args, "limit", 15))
			return formatClubSummaries(out, nat), nil
		},
	})

	s.Register(Tool{
		Name:        "standings",
		Description: "Compute the league standings for a competition and season using 3-1-0 points.",
		InputSchema: schemaObject(map[string]any{
			"competition": schemaString("Competition name (defaults to Brasileirão)"),
			"season":      schemaInt("Season (year)"),
			"limit":       schemaInt("Number of positions to return (default 20)"),
		}, []string{"season"}),
		Handler: func(args map[string]any) (string, error) {
			comp := argString(args, "competition")
			if comp == "" {
				comp = "Brasileirão"
			}
			season := argInt(args, "season")
			if season == 0 {
				return "", fmt.Errorf("season is required")
			}
			limit := argIntDefault(args, "limit", 20)
			st := query.Standings(ds, comp, season)
			if limit > 0 && len(st) > limit {
				st = st[:limit]
			}
			return formatStandings(st, comp, season), nil
		},
	})

	s.Register(Tool{
		Name:        "biggest_wins",
		Description: "List the largest-margin victories in the dataset, optionally restricted to a competition.",
		InputSchema: schemaObject(map[string]any{
			"competition": schemaString("Competition name"),
			"limit":       schemaInt("Number of matches to return (default 10)"),
		}, nil),
		Handler: func(args map[string]any) (string, error) {
			matches := query.BiggestWins(ds, argString(args, "competition"), argIntDefault(args, "limit", 10))
			return "Biggest victories in dataset:\n" + formatMatches(matches), nil
		},
	})

	s.Register(Tool{
		Name:        "aggregate_stats",
		Description: "Average goals, home win rate, etc., across a competition/season.",
		InputSchema: schemaObject(map[string]any{
			"competition": schemaString("Competition name"),
			"season":      schemaInt("Season (year)"),
		}, nil),
		Handler: func(args map[string]any) (string, error) {
			s := query.AggregateStats(ds, argString(args, "competition"), argInt(args, "season"))
			return formatStats(s), nil
		},
	})

	s.Register(Tool{
		Name:        "list_seasons",
		Description: "List the seasons present in the dataset, optionally filtered to a competition.",
		InputSchema: schemaObject(map[string]any{
			"competition": schemaString("Competition name"),
		}, nil),
		Handler: func(args map[string]any) (string, error) {
			seasons := query.Seasons(ds, argString(args, "competition"))
			if len(seasons) == 0 {
				return "No seasons found.", nil
			}
			strs := make([]string, len(seasons))
			for i, s := range seasons {
				strs[i] = fmt.Sprintf("%d", s)
			}
			return "Seasons: " + strings.Join(strs, ", "), nil
		},
	})

	s.Register(Tool{
		Name:        "dataset_summary",
		Description: "Return a summary of records loaded from each dataset file.",
		InputSchema: schemaObject(map[string]any{}, nil),
		Handler: func(_ map[string]any) (string, error) {
			byComp := map[data.Competition]int{}
			for _, m := range ds.Matches {
				byComp[m.Competition]++
			}
			var b strings.Builder
			fmt.Fprintf(&b, "Total matches: %d\nTotal players: %d\n\nBy competition:\n", len(ds.Matches), len(ds.Players))
			for _, c := range []data.Competition{data.CompBrasileirao, data.CompCopaBrasil, data.CompLibertadores, data.CompExtended, data.CompHistorical} {
				fmt.Fprintf(&b, "- %s: %d\n", c, byComp[c])
			}
			return b.String(), nil
		},
	})
}

// --- argument helpers ---

func argString(args map[string]any, k string) string {
	if args == nil {
		return ""
	}
	v, ok := args[k]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case float64:
		return fmt.Sprintf("%g", t)
	default:
		return strings.TrimSpace(fmt.Sprint(v))
	}
}

func argInt(args map[string]any, k string) int {
	if args == nil {
		return 0
	}
	v, ok := args[k]
	if !ok || v == nil {
		return 0
	}
	switch t := v.(type) {
	case float64:
		return int(t)
	case int:
		return t
	case string:
		var i int
		_, _ = fmt.Sscanf(t, "%d", &i)
		return i
	}
	return 0
}

func argIntDefault(args map[string]any, k string, def int) int {
	if i := argInt(args, k); i > 0 {
		return i
	}
	return def
}

func parseDateArg(s string) (time.Time, bool, error) {
	formats := []string{"2006-01-02", "2006-01-02 15:04:05", "02/01/2006"}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t, f != "2006-01-02", nil
		}
	}
	return time.Time{}, false, fmt.Errorf("bad date %q", s)
}

// --- schema helpers ---

func schemaObject(props map[string]any, required []string) map[string]any {
	out := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		out["required"] = required
	}
	return out
}

func schemaString(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}

func schemaInt(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

func schemaEnum(desc string, values []string) map[string]any {
	return map[string]any{"type": "string", "description": desc, "enum": values}
}
