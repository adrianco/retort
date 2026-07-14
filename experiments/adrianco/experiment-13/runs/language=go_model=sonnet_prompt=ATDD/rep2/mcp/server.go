package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"brazilian-soccer-mcp/internal/loader"
	"brazilian-soccer-mcp/internal/query"
)

// Server is the MCP server holding the loaded dataset.
type Server struct {
	ds *loader.Dataset
}

// NewServer loads data from dir and returns a ready server.
func NewServer(dir string) (*Server, error) {
	ds, err := loader.Load(dir)
	if err != nil {
		return nil, err
	}
	return &Server{ds: ds}, nil
}

// Call dispatches a tool call by name and returns JSON-encoded result.
func (s *Server) Call(ctx context.Context, tool string, args map[string]any) (string, error) {
	var result any
	var err error

	switch tool {
	case "find_matches":
		result, err = s.findMatches(args)
	case "get_team_stats":
		result, err = s.getTeamStats(args)
	case "find_players":
		result, err = s.findPlayers(args)
	case "get_standings":
		result, err = s.getStandings(args)
	case "get_statistics":
		result, err = s.getStatistics(args)
	default:
		return "", fmt.Errorf("unknown tool: %s", tool)
	}
	if err != nil {
		return "", err
	}

	b, err := json.Marshal(result)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func getString(args map[string]any, key string) string {
	v, _ := args[key].(string)
	return v
}

func getInt(args map[string]any, key string) int {
	switch v := args[key].(type) {
	case int:
		return v
	case float64:
		return int(v)
	case int64:
		return int(v)
	}
	return 0
}

func parseArgDate(s string) time.Time {
	formats := []string{"2006-01-02", "2006-01-02T15:04:05", "2006-01-02 15:04:05"}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

func (s *Server) findMatches(args map[string]any) (map[string]any, error) {
	f := query.MatchFilter{
		Team1:       getString(args, "team1"),
		Team2:       getString(args, "team2"),
		Team:        getString(args, "team"),
		Competition: getString(args, "competition"),
		Season:      getInt(args, "season"),
	}
	if df := getString(args, "date_from"); df != "" {
		f.DateFrom = parseArgDate(df)
	}
	if dt := getString(args, "date_to"); dt != "" {
		f.DateTo = parseArgDate(dt)
	}

	matches, h2h := query.FindMatches(s.ds, f)

	matchList := make([]map[string]any, 0, len(matches))
	for _, m := range matches {
		row := map[string]any{
			"competition": m.Competition,
			"home_team":   m.HomeTeam,
			"away_team":   m.AwayTeam,
			"home_goal":   m.HomeGoal,
			"away_goal":   m.AwayGoal,
			"season":      float64(m.Season),
			"date":        m.Date.Format("2006-01-02"),
			"round":       m.Round,
			"stage":       m.Stage,
		}
		matchList = append(matchList, row)
	}

	result := map[string]any{
		"matches": matchList,
		"total":   len(matchList),
	}

	if f.Team1 != "" && f.Team2 != "" {
		result["head_to_head"] = map[string]any{
			"team1_wins": float64(h2h.Team1Wins),
			"team2_wins": float64(h2h.Team2Wins),
			"draws":      float64(h2h.Draws),
		}
	}

	return result, nil
}

func (s *Server) getTeamStats(args map[string]any) (map[string]any, error) {
	team := getString(args, "team")
	if team == "" {
		return nil, fmt.Errorf("team is required")
	}
	f := query.TeamStatsFilter{
		Team:        team,
		Competition: getString(args, "competition"),
		Season:      getInt(args, "season"),
	}
	stats := query.GetTeamStats(s.ds, f)

	return map[string]any{
		"team":          stats.Team,
		"matches":       float64(stats.Matches),
		"wins":          float64(stats.Wins),
		"draws":         float64(stats.Draws),
		"losses":        float64(stats.Losses),
		"goals_for":     float64(stats.GoalsFor),
		"goals_against": float64(stats.GoalsAgainst),
		"points":        float64(stats.Points),
	}, nil
}

func (s *Server) findPlayers(args map[string]any) (map[string]any, error) {
	limit := getInt(args, "limit")
	if limit == 0 {
		limit = 50
	}
	f := query.PlayerFilter{
		Name:        getString(args, "name"),
		Nationality: getString(args, "nationality"),
		Club:        getString(args, "club"),
		Limit:       limit,
	}

	players := query.FindPlayers(s.ds, f)

	list := make([]map[string]any, 0, len(players))
	for _, p := range players {
		list = append(list, map[string]any{
			"id":           float64(p.ID),
			"name":         p.Name,
			"age":          float64(p.Age),
			"nationality":  p.Nationality,
			"overall":      float64(p.Overall),
			"potential":    float64(p.Potential),
			"club":         p.Club,
			"position":     p.Position,
			"jersey_number": float64(p.JerseyNumber),
		})
	}

	return map[string]any{
		"players": list,
		"total":   len(list),
	}, nil
}

func (s *Server) getStandings(args map[string]any) (map[string]any, error) {
	f := query.StandingsFilter{
		Competition: getString(args, "competition"),
		Season:      getInt(args, "season"),
	}

	rows := query.GetStandings(s.ds, f)

	list := make([]map[string]any, 0, len(rows))
	for _, r := range rows {
		list = append(list, map[string]any{
			"position":      float64(r.Position),
			"team":          r.Team,
			"points":        float64(r.Points),
			"wins":          float64(r.Wins),
			"draws":         float64(r.Draws),
			"losses":        float64(r.Losses),
			"goals_for":     float64(r.GoalsFor),
			"goals_against": float64(r.GoalsAgainst),
			"goal_diff":     float64(r.GoalDiff),
			"matches":       float64(r.Matches),
		})
	}

	return map[string]any{
		"standings": list,
		"total":     len(list),
	}, nil
}

func (s *Server) getStatistics(args map[string]any) (map[string]any, error) {
	f := query.StandingsFilter{
		Competition: getString(args, "competition"),
		Season:      getInt(args, "season"),
	}

	stats := query.GetStatistics(s.ds, f)

	return map[string]any{
		"total_matches":      float64(stats.TotalMatches),
		"total_goals":        float64(stats.TotalGoals),
		"home_wins":          float64(stats.HomeWins),
		"away_wins":          float64(stats.AwayWins),
		"draws":              float64(stats.Draws),
		"avg_goals_per_match": stats.AvgGoalsPerMatch,
		"home_win_rate":      stats.HomeWinRate,
	}, nil
}

// ServeStdio implements the MCP stdio protocol (JSON-RPC 2.0).
func (s *Server) ServeStdio() error {
	scanner := bufio.NewScanner(os.Stdin)
	encoder := json.NewEncoder(os.Stdout)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var req struct {
			JSONRPC string          `json:"jsonrpc"`
			ID      any             `json:"id"`
			Method  string          `json:"method"`
			Params  json.RawMessage `json:"params"`
		}
		if err := json.Unmarshal(line, &req); err != nil {
			continue
		}

		switch req.Method {
		case "initialize":
			encoder.Encode(map[string]any{
				"jsonrpc": "2.0",
				"id":      req.ID,
				"result": map[string]any{
					"protocolVersion": "2024-11-05",
					"capabilities":    map[string]any{"tools": map[string]any{}},
					"serverInfo":      map[string]any{"name": "brazilian-soccer-mcp", "version": "1.0"},
				},
			})

		case "tools/list":
			encoder.Encode(map[string]any{
				"jsonrpc": "2.0",
				"id":      req.ID,
				"result":  map[string]any{"tools": toolList()},
			})

		case "tools/call":
			var p struct {
				Name      string         `json:"name"`
				Arguments map[string]any `json:"arguments"`
			}
			if err := json.Unmarshal(req.Params, &p); err != nil {
				writeError(encoder, req.ID, -32600, err.Error())
				continue
			}
			raw, err := s.Call(context.Background(), p.Name, p.Arguments)
			if err != nil {
				writeError(encoder, req.ID, -32600, err.Error())
				continue
			}
			encoder.Encode(map[string]any{
				"jsonrpc": "2.0",
				"id":      req.ID,
				"result": map[string]any{
					"content": []map[string]any{{"type": "text", "text": raw}},
				},
			})

		case "notifications/initialized":
			// no response needed

		default:
			writeError(encoder, req.ID, -32601, "method not found")
		}
	}

	return scanner.Err()
}

func writeError(enc *json.Encoder, id any, code int, msg string) {
	enc.Encode(map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"error":   map[string]any{"code": code, "message": msg},
	})
}

func toolList() []map[string]any {
	return []map[string]any{
		{
			"name":        "find_matches",
			"description": "Find matches by team, competition, season, or date range",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"team":        map[string]any{"type": "string", "description": "Single team name (home or away)"},
					"team1":       map[string]any{"type": "string", "description": "First team for head-to-head search"},
					"team2":       map[string]any{"type": "string", "description": "Second team for head-to-head search"},
					"competition": map[string]any{"type": "string", "description": "Competition name: Brasileirao, Copa do Brasil, Libertadores"},
					"season":      map[string]any{"type": "integer", "description": "Year of the season"},
					"date_from":   map[string]any{"type": "string", "description": "Start date YYYY-MM-DD"},
					"date_to":     map[string]any{"type": "string", "description": "End date YYYY-MM-DD"},
				},
			},
		},
		{
			"name":        "get_team_stats",
			"description": "Get win/loss/draw statistics for a team",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"team":        map[string]any{"type": "string"},
					"competition": map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
				},
				"required": []string{"team"},
			},
		},
		{
			"name":        "find_players",
			"description": "Search players by name, nationality, or club",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name":        map[string]any{"type": "string"},
					"nationality": map[string]any{"type": "string"},
					"club":        map[string]any{"type": "string"},
					"limit":       map[string]any{"type": "integer", "description": "Max results (default 50)"},
				},
			},
		},
		{
			"name":        "get_standings",
			"description": "Get league standings for a competition and season",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"competition": map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
				},
			},
		},
		{
			"name":        "get_statistics",
			"description": "Get aggregate statistics for a competition/season",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"competition": map[string]any{"type": "string"},
					"season":      map[string]any{"type": "integer"},
				},
			},
		},
	}
}
