package main

import (
	"encoding/json"
	"fmt"
)

func schemaProps(props map[string]any, required ...string) map[string]any {
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

func unmarshalArgs(raw json.RawMessage, v any) error {
	if len(raw) == 0 {
		return nil
	}
	return json.Unmarshal(raw, v)
}

// RegisterTools wires all Brazilian-soccer query capabilities to the MCP
// server, backed by the given Store.
func RegisterTools(s *Server, store *Store) {
	s.Register(Tool{
		Name: "search_matches",
		Description: "Search Brazilian soccer matches (Brasileirão, Copa do Brasil, Copa Libertadores, and extended-stats sources) " +
			"by team, opponent, competition, season and/or date range. Returns matching games most-recent-first, " +
			"plus a head-to-head summary when both team and opponent are given.",
		InputSchema: schemaProps(map[string]any{
			"team":        strProp("Team name, e.g. \"Flamengo\" or \"Palmeiras-SP\". Matches home or away."),
			"opponent":    strProp("Opposing team name, to find matches between team and opponent."),
			"competition": strProp("Competition name filter, e.g. \"Brasileirão\", \"Copa do Brasil\", \"Copa Libertadores\". Substring match."),
			"season":      intProp("Season/year filter, e.g. 2023."),
			"date_from":   strProp("Earliest match date, inclusive, format YYYY-MM-DD."),
			"date_to":     strProp("Latest match date, inclusive, format YYYY-MM-DD."),
			"limit":       intProp("Max matches to return (default 20, max 200)."),
		}),
		Handler: func(raw json.RawMessage) (any, error) {
			var a struct {
				Team        string `json:"team"`
				Opponent    string `json:"opponent"`
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				DateFrom    string `json:"date_from"`
				DateTo      string `json:"date_to"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshalArgs(raw, &a); err != nil {
				return nil, err
			}
			return store.SearchMatches(a.Team, a.Opponent, a.Competition, a.Season, a.DateFrom, a.DateTo, a.Limit), nil
		},
	})

	s.Register(Tool{
		Name: "head_to_head",
		Description: "Compare two teams head-to-head across all competitions: wins, draws, goals, and biggest wins for each side, " +
			"plus the most recent matches between them.",
		InputSchema: schemaProps(map[string]any{
			"team_a":      strProp("First team name."),
			"team_b":      strProp("Second team name."),
			"competition": strProp("Optional competition filter, substring match."),
			"season":      intProp("Optional season/year filter."),
			"limit":       intProp("Max recent matches to return (default 50, max 200)."),
		}, "team_a", "team_b"),
		Handler: func(raw json.RawMessage) (any, error) {
			var a struct {
				TeamA       string `json:"team_a"`
				TeamB       string `json:"team_b"`
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshalArgs(raw, &a); err != nil {
				return nil, err
			}
			if a.TeamA == "" || a.TeamB == "" {
				return nil, fmt.Errorf("both team_a and team_b are required")
			}
			result, ok := store.HeadToHead(a.TeamA, a.TeamB, a.Competition, a.Season, a.Limit)
			if !ok {
				return nil, fmt.Errorf("could not resolve team_a=%q or team_b=%q against any team in the dataset", a.TeamA, a.TeamB)
			}
			return result, nil
		},
	})

	s.Register(Tool{
		Name: "team_record",
		Description: "Get a team's win/draw/loss record, goals for/against and win rate, optionally filtered by season, competition " +
			"and home/away venue. Also lists competitions the team appears in and its top-rated squad players (from the FIFA dataset, " +
			"when that club is present there).",
		InputSchema: schemaProps(map[string]any{
			"team":        strProp("Team name, e.g. \"Corinthians\"."),
			"season":      intProp("Optional season/year filter."),
			"competition": strProp("Optional competition filter, substring match."),
			"venue":       strProp("One of \"home\", \"away\", or \"all\" (default \"all\")."),
		}, "team"),
		Handler: func(raw json.RawMessage) (any, error) {
			var a struct {
				Team        string `json:"team"`
				Season      int    `json:"season"`
				Competition string `json:"competition"`
				Venue       string `json:"venue"`
			}
			if err := unmarshalArgs(raw, &a); err != nil {
				return nil, err
			}
			if a.Team == "" {
				return nil, fmt.Errorf("team is required")
			}
			result, ok := store.TeamRecord(a.Team, a.Season, a.Competition, a.Venue)
			if !ok {
				return nil, fmt.Errorf("no team in the dataset matched %q", a.Team)
			}
			return result, nil
		},
	})

	s.Register(Tool{
		Name:        "standings",
		Description: "Calculate a league table (points, wins, draws, losses, goal difference) for a competition and season from match results.",
		InputSchema: schemaProps(map[string]any{
			"season":      intProp("Season/year, e.g. 2019. Required."),
			"competition": strProp("Competition name, defaults to \"Brasileirão\". Substring match."),
		}, "season"),
		Handler: func(raw json.RawMessage) (any, error) {
			var a struct {
				Season      int    `json:"season"`
				Competition string `json:"competition"`
			}
			if err := unmarshalArgs(raw, &a); err != nil {
				return nil, err
			}
			if a.Season == 0 {
				return nil, fmt.Errorf("season is required")
			}
			return store.Standings(a.Season, a.Competition), nil
		},
	})

	s.Register(Tool{
		Name: "stats_overview",
		Description: "Aggregate statistics across matches: average goals per match, home/away/draw rates, biggest wins, and the best " +
			"home/away win-rate teams. Optionally filtered by competition and/or season.",
		InputSchema: schemaProps(map[string]any{
			"competition": strProp("Optional competition filter, substring match. Omit for all competitions combined."),
			"season":      intProp("Optional season/year filter."),
		}),
		Handler: func(raw json.RawMessage) (any, error) {
			var a struct {
				Competition string `json:"competition"`
				Season      int    `json:"season"`
			}
			if err := unmarshalArgs(raw, &a); err != nil {
				return nil, err
			}
			return store.StatsOverview(a.Competition, a.Season), nil
		},
	})

	s.Register(Tool{
		Name: "search_players",
		Description: "Search the FIFA player database by name, nationality, club and/or position, with an optional minimum overall " +
			"rating. Results are sorted by overall rating, descending -- omit filters to get top-rated players overall.",
		InputSchema: schemaProps(map[string]any{
			"name":        strProp("Player name, substring match, e.g. \"Neymar\"."),
			"nationality": strProp("Nationality substring, e.g. \"Brazil\"."),
			"club":        strProp("Club name, e.g. \"Flamengo\"."),
			"position":    strProp("Position code or substring, e.g. \"ST\", \"GK\", \"CB\"."),
			"min_overall": intProp("Minimum FIFA overall rating."),
			"limit":       intProp("Max players to return (default 20, max 200)."),
		}),
		Handler: func(raw json.RawMessage) (any, error) {
			var a struct {
				Name        string `json:"name"`
				Nationality string `json:"nationality"`
				Club        string `json:"club"`
				Position    string `json:"position"`
				MinOverall  int    `json:"min_overall"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshalArgs(raw, &a); err != nil {
				return nil, err
			}
			return store.SearchPlayers(a.Name, a.Nationality, a.Club, a.Position, a.MinOverall, a.Limit), nil
		},
	})
}
