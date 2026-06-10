// MCP tool definitions for the Brazilian Soccer server.
//
// Context: this file maps the query engine onto the nine MCP tools the
// LLM can call: search_matches, head_to_head, team_stats,
// league_standings, search_players, player_details, competition_stats,
// biggest_wins and list_teams. Each tool takes JSON arguments described
// by an inputSchema and returns a formatted plain-text answer following
// the example formats in TASK.md.
package mcp

import (
	"fmt"
	"math"
	"strconv"
	"strings"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/query"
)

// argument extraction helpers tolerant of JSON number/string typing.

func argString(args map[string]any, key string) string {
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return strings.TrimSpace(s)
		}
		if f, ok := v.(float64); ok {
			return strconv.FormatInt(int64(f), 10)
		}
	}
	return ""
}

func argInt(args map[string]any, key string) int {
	switch v := args[key].(type) {
	case float64:
		if v != math.Trunc(v) {
			return 0
		}
		return int(v)
	case string:
		n, _ := strconv.Atoi(strings.TrimSpace(v))
		return n
	}
	return 0
}

func schema(props map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

func prop(typ, desc string) map[string]any {
	return map[string]any{"type": typ, "description": desc}
}

// BuildTools constructs the MCP tool set over a query engine.
func BuildTools(e *query.Engine) []Tool {
	teamProp := prop("string", "Team name in any dataset spelling, e.g. 'Flamengo', 'Palmeiras-SP', 'São Paulo' or 'Sao Paulo'")
	compProp := prop("string", "Competition filter: 'Serie A' / 'Brasileirão', 'Serie B', 'Serie C', 'Copa do Brasil' or 'Libertadores'. Empty = all competitions")
	seasonProp := prop("integer", "Season year, e.g. 2019. 0 or omitted = all seasons")
	limitProp := prop("integer", "Maximum entries to list (default 20)")

	return []Tool{
		{
			Name: "search_matches",
			Description: "Search matches by team, opponent, competition, season and/or date range. " +
				"Returns matches newest first with date, score, competition and round.",
			InputSchema: schema(map[string]any{
				"team":        teamProp,
				"opponent":    prop("string", "Second team; restricts results to fixtures between team and opponent"),
				"competition": compProp,
				"season":      seasonProp,
				"date_from":   prop("string", "Earliest date, YYYY-MM-DD"),
				"date_to":     prop("string", "Latest date, YYYY-MM-DD"),
				"limit":       limitProp,
			}),
			Handler: func(args map[string]any) (string, error) {
				f := query.MatchFilter{
					Team:        argString(args, "team"),
					Opponent:    argString(args, "opponent"),
					Competition: argString(args, "competition"),
					Season:      argInt(args, "season"),
				}
				if s := argString(args, "date_from"); s != "" {
					t, err := data.ParseDate(s)
					if err != nil {
						return "", err
					}
					f.DateFrom = t
				}
				if s := argString(args, "date_to"); s != "" {
					t, err := data.ParseDate(s)
					if err != nil {
						return "", err
					}
					f.DateTo = t
				}
				return query.FormatMatches(e.FindMatches(f), argInt(args, "limit")), nil
			},
		},
		{
			Name:        "head_to_head",
			Description: "Compare two teams head-to-head: wins, draws, goals and the full list of matches between them.",
			InputSchema: schema(map[string]any{
				"team1":       teamProp,
				"team2":       teamProp,
				"competition": compProp,
				"limit":       limitProp,
			}, "team1", "team2"),
			Handler: func(args map[string]any) (string, error) {
				h, err := e.HeadToHead(argString(args, "team1"), argString(args, "team2"), argString(args, "competition"))
				if err != nil {
					return "", err
				}
				return query.FormatHeadToHead(h, argInt(args, "limit")), nil
			},
		},
		{
			Name:        "team_stats",
			Description: "Win/draw/loss record, goals for/against and win rate for a team, optionally filtered by season, competition and venue (home/away).",
			InputSchema: schema(map[string]any{
				"team":        teamProp,
				"season":      seasonProp,
				"competition": compProp,
				"venue":       prop("string", "'all' (default), 'home' or 'away'"),
			}, "team"),
			Handler: func(args map[string]any) (string, error) {
				venue := strings.ToLower(argString(args, "venue"))
				if venue == "" {
					venue = "all"
				}
				if venue != "all" && venue != "home" && venue != "away" {
					return "", fmt.Errorf("venue must be 'all', 'home' or 'away'")
				}
				season := argInt(args, "season")
				comp := argString(args, "competition")
				rec, _, err := e.TeamStats(argString(args, "team"), season, comp, venue)
				if err != nil {
					return "", err
				}
				return query.FormatRecord(rec, season, comp, venue), nil
			},
		},
		{
			Name:        "league_standings",
			Description: "League table for a season calculated from match results (3 points per win). Defaults to Brasileirão Série A. The first team is the champion; in Série A the bottom four are the relegation zone.",
			InputSchema: schema(map[string]any{
				"season":      prop("integer", "Season year, e.g. 2019 (required)"),
				"competition": compProp,
			}, "season"),
			Handler: func(args map[string]any) (string, error) {
				season := argInt(args, "season")
				if season == 0 {
					return "", fmt.Errorf("season is required, e.g. 2019")
				}
				comp := argString(args, "competition")
				if comp == "" {
					comp = data.CompSerieA
				}
				return query.FormatStandings(e.Standings(season, comp), season, comp), nil
			},
		},
		{
			Name:        "search_players",
			Description: "Search FIFA player data by name, nationality, club, position and/or minimum overall rating. Returns players sorted by overall rating, highest first.",
			InputSchema: schema(map[string]any{
				"name":        prop("string", "Player name or part of it, accents optional, e.g. 'Neymar'"),
				"nationality": prop("string", "Country, e.g. 'Brazil'"),
				"club":        prop("string", "Club name, e.g. 'Santos' or 'Grêmio'"),
				"position":    prop("string", "Exact position code, e.g. ST, GK, CDM, LW"),
				"min_overall": prop("integer", "Minimum FIFA overall rating"),
				"limit":       limitProp,
			}),
			Handler: func(args map[string]any) (string, error) {
				players := e.FindPlayers(query.PlayerFilter{
					Name:        argString(args, "name"),
					Nationality: argString(args, "nationality"),
					Club:        argString(args, "club"),
					Position:    argString(args, "position"),
					MinOverall:  argInt(args, "min_overall"),
				})
				return query.FormatPlayers(players, argInt(args, "limit")), nil
			},
		},
		{
			Name:        "player_details",
			Description: "Full FIFA attribute card for the best-matching player by name.",
			InputSchema: schema(map[string]any{
				"name": prop("string", "Player name, e.g. 'Gabriel Barbosa'"),
			}, "name"),
			Handler: func(args map[string]any) (string, error) {
				name := argString(args, "name")
				players := e.FindPlayers(query.PlayerFilter{Name: name})
				if len(players) == 0 {
					return fmt.Sprintf("No player matching %q found.", name), nil
				}
				out := query.FormatPlayerDetail(players[0])
				if len(players) > 1 {
					out += fmt.Sprintf("\n(%d other players also match %q)\n", len(players)-1, name)
				}
				return out, nil
			},
		},
		{
			Name:        "competition_stats",
			Description: "Aggregate statistics for a competition and/or season: matches, total goals, average goals per match, home/away win rates and draw rate.",
			InputSchema: schema(map[string]any{
				"competition": compProp,
				"season":      seasonProp,
			}),
			Handler: func(args map[string]any) (string, error) {
				st := e.CompetitionStats(argString(args, "competition"), argInt(args, "season"))
				return query.FormatCompetitionStats(st), nil
			},
		},
		{
			Name:        "biggest_wins",
			Description: "Largest margins of victory in the dataset, optionally filtered by competition and season.",
			InputSchema: schema(map[string]any{
				"competition": compProp,
				"season":      seasonProp,
				"limit":       limitProp,
			}),
			Handler: func(args map[string]any) (string, error) {
				limit := argInt(args, "limit")
				if limit <= 0 {
					limit = 10
				}
				wins := e.BiggestWins(argString(args, "competition"), argInt(args, "season"), limit)
				if len(wins) == 0 {
					return "No matches found.", nil
				}
				var b strings.Builder
				fmt.Fprintf(&b, "Biggest wins:\n")
				for i, m := range wins {
					fmt.Fprintf(&b, "%d. %s\n", i+1, query.FormatMatch(m))
				}
				return b.String(), nil
			},
		},
		{
			Name:        "list_teams",
			Description: "List team names known to the dataset, optionally filtered by a search string. Useful to resolve team-name spelling before other queries.",
			InputSchema: schema(map[string]any{
				"query": prop("string", "Optional substring to filter team names"),
				"limit": limitProp,
			}),
			Handler: func(args map[string]any) (string, error) {
				teams := e.ListTeams(argString(args, "query"))
				if len(teams) == 0 {
					return "No teams found.", nil
				}
				limit := argInt(args, "limit")
				if limit <= 0 {
					limit = 50
				}
				var b strings.Builder
				fmt.Fprintf(&b, "Found %d team(s):\n", len(teams))
				for i, t := range teams {
					if i == limit {
						fmt.Fprintf(&b, "... (%d more)\n", len(teams)-limit)
						break
					}
					fmt.Fprintf(&b, "- %s\n", t)
				}
				return b.String(), nil
			},
		},
	}
}
