package main

import (
	"bufio"
	"encoding/json"
	"io"
	"sync"
)

type tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	run         func(Args) string
}

// Server is a minimal MCP server over newline-delimited JSON-RPC (stdio transport).
type Server struct {
	tools  []tool
	byName map[string]tool
}

func schema(props ...string) map[string]any {
	p := map[string]any{}
	for i := 0; i+1 < len(props); i += 2 {
		p[props[i]] = map[string]any{"type": "string", "description": props[i+1]}
	}
	return map[string]any{"type": "object", "properties": p}
}

// NewServer registers the soccer tools against a store.
func NewServer(s *Store) *Server {
	team, season, comp := "Team name (any spelling, accents optional)", "Season year, e.g. 2019", "Brasileirão, Copa do Brasil, Libertadores, Serie B, Serie C"
	srv := &Server{tools: []tool{
		{"search_matches", "Find matches by team, opponent, competition, season, stage, venue (home/away) and date range (from/to, YYYY-MM-DD).",
			schema("team", team, "opponent", team, "competition", comp, "season", season, "stage", "Stage/round e.g. final, group stage", "venue", "home or away", "from", "Start date", "to", "End date", "limit", "Max results"), s.SearchMatches},
		{"head_to_head", "Matches between two teams with head-to-head record. Use limit=1 for the most recent match.",
			schema("team_a", team, "team_b", team, "competition", comp, "season", season, "limit", "Max matches listed"), s.HeadToHead},
		{"team_record", "Win/draw/loss record and goals for a team, optionally by season, competition and venue.",
			schema("team", team, "season", season, "competition", comp, "venue", "home or away", "from", "Start date", "to", "End date"), s.TeamRecord},
		{"standings", "League table for a season calculated from match results, with champion and relegated teams. sort=goals ranks by goals scored.",
			schema("season", season, "competition", comp, "sort", "points (default) or goals"), s.Standings},
		{"search_players", "Search FIFA player data by name, nationality, club, position (e.g. ST or 'forward'), min_overall.",
			schema("name", "Player name", "nationality", "e.g. Brazil", "club", "Club name", "position", "Position code or group", "min_overall", "Minimum rating", "limit", "Max results"), s.SearchPlayers},
		{"players_by_club", "Count players and average rating per club, optionally filtered by nationality.",
			schema("nationality", "e.g. Brazil", "club", "Club filter", "limit", "Max clubs"), s.PlayersByClub},
		{"statistics", "Aggregate statistics: goals per match, home/away win and draw rates.",
			schema("competition", comp, "season", season, "team", team, "from", "Start date", "to", "End date"), s.Statistics},
		{"biggest_wins", "Matches with the largest winning margins.",
			schema("competition", comp, "season", season, "team", team, "limit", "Max results"), s.BiggestWins},
		{"rank_teams", "Rank teams by win rate overall, at home or away.",
			schema("venue", "home or away", "competition", comp, "season", season, "min_matches", "Minimum matches", "limit", "Max results"), s.RankTeams},
		{"team_profile", "Team overview: record, competitions played, recent matches and FIFA players at the club.",
			schema("team", team), s.TeamProfile},
		{"derbies", "Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista...).",
			schema("season", season, "competition", comp, "limit", "Max results"), s.Derbies},
		{"data_summary", "Describe the loaded datasets.", schema(), s.DataSummary},
	}, byName: map[string]tool{}}
	for _, t := range srv.tools {
		srv.byName[t.Name] = t
	}
	return srv
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

// Serve processes requests from r and writes responses to w until r closes.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	var mu sync.Mutex
	enc := json.NewEncoder(w)
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 1<<20), 1<<24)
	for sc.Scan() {
		var req request
		if err := json.Unmarshal(sc.Bytes(), &req); err != nil {
			mu.Lock()
			enc.Encode(map[string]any{"jsonrpc": "2.0", "id": nil, "error": map[string]any{"code": -32700, "message": "parse error"}})
			mu.Unlock()
			continue
		}
		if len(req.ID) == 0 {
			continue // notification
		}
		result, rpcErr := s.handle(req)
		resp := map[string]any{"jsonrpc": "2.0", "id": req.ID}
		if rpcErr != nil {
			resp["error"] = rpcErr
		} else {
			resp["result"] = result
		}
		mu.Lock()
		enc.Encode(resp)
		mu.Unlock()
	}
	return sc.Err()
}

func (s *Server) handle(req request) (any, map[string]any) {
	switch req.Method {
	case "initialize":
		return map[string]any{
			"protocolVersion": "2024-11-05",
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "brazilian-soccer", "version": "1.0.0"},
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": s.tools}, nil
	case "tools/call":
		var p struct {
			Name      string `json:"name"`
			Arguments Args   `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, map[string]any{"code": -32602, "message": "invalid params"}
		}
		t, ok := s.byName[p.Name]
		if !ok {
			return map[string]any{"content": []any{map[string]any{"type": "text", "text": "unknown tool: " + p.Name}}, "isError": true}, nil
		}
		if p.Arguments == nil {
			p.Arguments = Args{}
		}
		return map[string]any{"content": []any{map[string]any{"type": "text", "text": t.run(p.Arguments)}}}, nil
	}
	return nil, map[string]any{"code": -32601, "message": "method not found: " + req.Method}
}
