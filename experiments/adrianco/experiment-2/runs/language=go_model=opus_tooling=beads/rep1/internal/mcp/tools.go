package mcp

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"brsoccer/internal/data"
	"brsoccer/internal/query"
)

// Register installs all soccer tools on the server, backed by db.
func RegisterSoccerTools(s *Server, db *data.DB) {
	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "find_matches",
			Description: "Find soccer matches with optional filters: team, vs_team (head-to-head), competition, season, date range. Returns a formatted list of matches.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"team":        map[string]any{"type": "string", "description": "Team name (matches home or away)"},
					"vs_team":     map[string]any{"type": "string", "description": "Opponent team for head-to-head"},
					"competition": map[string]any{"type": "string", "description": "Competition name filter (e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores')"},
					"season":      map[string]any{"type": "integer", "description": "Season year"},
					"from":        map[string]any{"type": "string", "description": "Start date YYYY-MM-DD"},
					"to":          map[string]any{"type": "string", "description": "End date YYYY-MM-DD"},
					"limit":       map[string]any{"type": "integer", "description": "Max matches to return (default 20)"},
				},
			},
		},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				Team        string `json:"team"`
				VsTeam      string `json:"vs_team"`
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				From        string `json:"from"`
				To          string `json:"to"`
				Limit       int    `json:"limit"`
			}
			_ = json.Unmarshal(args, &a)
			if a.Limit == 0 {
				a.Limit = 20
			}
			f := query.MatchFilter{
				Team: a.Team, VsTeam: a.VsTeam, Competition: a.Competition,
				Season: a.Season, Limit: a.Limit,
			}
			if a.From != "" {
				if t, err := time.Parse("2006-01-02", a.From); err == nil {
					f.From = t
				}
			}
			if a.To != "" {
				if t, err := time.Parse("2006-01-02", a.To); err == nil {
					f.To = t.Add(24 * time.Hour)
				}
			}
			ms := query.FindMatches(db, f)
			return FormatMatches(ms, a.Team, a.VsTeam), nil
		},
	})

	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "team_stats",
			Description: "Return aggregate statistics for a team (wins, losses, draws, goals) optionally filtered by season and competition.",
			InputSchema: map[string]any{
				"type":     "object",
				"required": []string{"team"},
				"properties": map[string]any{
					"team":        map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
					"competition": map[string]any{"type": "string"},
				},
			},
		},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				Team        string `json:"team"`
				Season      int    `json:"season"`
				Competition string `json:"competition"`
			}
			if err := json.Unmarshal(args, &a); err != nil {
				return "", err
			}
			if a.Team == "" {
				return "", fmt.Errorf("team is required")
			}
			s := query.ComputeTeamStats(db, a.Team, a.Season, a.Competition)
			return FormatTeamStats(s), nil
		},
	})

	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "head_to_head",
			Description: "Return head-to-head record between two teams across all competitions.",
			InputSchema: map[string]any{
				"type":     "object",
				"required": []string{"team_a", "team_b"},
				"properties": map[string]any{
					"team_a": map[string]any{"type": "string"},
					"team_b": map[string]any{"type": "string"},
				},
			},
		},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				A string `json:"team_a"`
				B string `json:"team_b"`
			}
			if err := json.Unmarshal(args, &a); err != nil {
				return "", err
			}
			h := query.H2H(db, a.A, a.B)
			return FormatH2H(h), nil
		},
	})

	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "standings",
			Description: "Compute a standings table for a season and competition from match results.",
			InputSchema: map[string]any{
				"type":     "object",
				"required": []string{"season"},
				"properties": map[string]any{
					"season":      map[string]any{"type": "integer"},
					"competition": map[string]any{"type": "string", "description": "Default: Brasileirão"},
					"limit":       map[string]any{"type": "integer"},
				},
			},
		},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				Season      int    `json:"season"`
				Competition string `json:"competition"`
				Limit       int    `json:"limit"`
			}
			_ = json.Unmarshal(args, &a)
			if a.Competition == "" {
				a.Competition = "Brasileirão"
			}
			if a.Limit == 0 {
				a.Limit = 20
			}
			st := query.Standings(db, a.Season, a.Competition)
			if len(st) > a.Limit {
				st = st[:a.Limit]
			}
			return FormatStandings(st, a.Season, a.Competition), nil
		},
	})

	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "find_players",
			Description: "Search FIFA player database. Filter by name, nationality, club, position, minimum overall rating.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name":        map[string]any{"type": "string"},
					"nationality": map[string]any{"type": "string"},
					"club":        map[string]any{"type": "string"},
					"position":    map[string]any{"type": "string"},
					"min_overall": map[string]any{"type": "integer"},
					"limit":       map[string]any{"type": "integer"},
				},
			},
		},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				Name        string `json:"name"`
				Nationality string `json:"nationality"`
				Club        string `json:"club"`
				Position    string `json:"position"`
				MinOverall  int    `json:"min_overall"`
				Limit       int    `json:"limit"`
			}
			_ = json.Unmarshal(args, &a)
			if a.Limit == 0 {
				a.Limit = 20
			}
			ps := query.FindPlayers(db, query.PlayerFilter{
				Name: a.Name, Nationality: a.Nationality, Club: a.Club,
				Position: a.Position, MinOverall: a.MinOverall, Limit: a.Limit,
			})
			return FormatPlayers(ps), nil
		},
	})

	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "overall_stats",
			Description: "Return aggregate dataset statistics: total matches, average goals, home win rate, etc.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"competition": map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
				},
			},
		},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				Competition string `json:"competition"`
				Season      int    `json:"season"`
			}
			_ = json.Unmarshal(args, &a)
			g := query.Overall(db, a.Competition, a.Season)
			return FormatOverall(g, a.Competition, a.Season), nil
		},
	})

	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "biggest_wins",
			Description: "Return matches with the largest goal differences.",
			InputSchema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"competition": map[string]any{"type": "string"},
					"limit":       map[string]any{"type": "integer"},
				},
			},
		},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				Competition string `json:"competition"`
				Limit       int    `json:"limit"`
			}
			_ = json.Unmarshal(args, &a)
			if a.Limit == 0 {
				a.Limit = 10
			}
			ms := query.BiggestWins(db, a.Competition, a.Limit)
			return FormatMatches(ms, "", ""), nil
		},
	})

	s.Register(Tool{
		Schema: ToolSchema{
			Name:        "dataset_info",
			Description: "Return information about the loaded dataset (match counts per competition, total players).",
			InputSchema: map[string]any{"type": "object", "properties": map[string]any{}},
		},
		Handler: func(args json.RawMessage) (string, error) {
			byComp := map[string]int{}
			for _, m := range db.Matches {
				byComp[m.Competition]++
			}
			var sb strings.Builder
			sb.WriteString(fmt.Sprintf("Total matches: %d\n", len(db.Matches)))
			sb.WriteString(fmt.Sprintf("Total players: %d\n\nMatches by competition:\n", len(db.Players)))
			for k, v := range byComp {
				sb.WriteString(fmt.Sprintf("  %s: %d\n", k, v))
			}
			return sb.String(), nil
		},
	})
}
