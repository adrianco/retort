package soccer

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

type Server struct{ Store *Store }

func NewServer(s *Store) *Server { return &Server{Store: s} }

type rpcReq struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      any             `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

func (s *Server) Handle(req rpcReq) any {
	switch req.Method {
	case "initialize":
		return map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}}}
	case "notifications/initialized":
		return nil
	case "tools/list":
		return map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": map[string]any{"tools": tools()}}
	case "tools/call":
		return s.call(req)
	}
	return map[string]any{"jsonrpc": "2.0", "id": req.ID, "error": map[string]any{"code": -32601, "message": "method not found"}}
}
func tools() []map[string]any {
	return []map[string]any{{"name": "search_matches", "description": "Search Brazilian soccer matches by teams, dates, competition, or season", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"team": map[string]string{"type": "string"}, "opponent": map[string]string{"type": "string"}, "competition": map[string]string{"type": "string"}, "season": map[string]string{"type": "integer"}, "from": map[string]string{"type": "string"}, "to": map[string]string{"type": "string"}, "limit": map[string]string{"type": "integer"}}}}, {"name": "team_stats", "description": "Calculate a team's match record and goals", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"team": map[string]string{"type": "string"}, "competition": map[string]string{"type": "string"}, "season": map[string]string{"type": "integer"}, "home_only": map[string]string{"type": "boolean"}}, "required": []string{"team"}}}, {"name": "search_players", "description": "Search FIFA players by name, nationality, club, position, or rating", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"name": map[string]string{"type": "string"}, "nationality": map[string]string{"type": "string"}, "club": map[string]string{"type": "string"}, "position": map[string]string{"type": "string"}, "min_overall": map[string]string{"type": "integer"}, "limit": map[string]string{"type": "integer"}}}}, {"name": "standings", "description": "Calculate competition standings from match results", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"competition": map[string]string{"type": "string"}, "season": map[string]string{"type": "integer"}}}}, {"name": "average_goals", "description": "Calculate average goals per match", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"competition": map[string]string{"type": "string"}, "season": map[string]string{"type": "integer"}}}}}
}
func (s *Server) call(req rpcReq) any {
	var p map[string]any
	_ = json.Unmarshal(req.Params, &p)
	name, _ := p["name"].(string)
	args, _ := p["arguments"].(map[string]any)
	var v any
	switch name {
	case "search_matches":
		v = s.Store.SearchMatches(MatchFilter{Team: str(args, "team"), Opponent: str(args, "opponent"), Competition: str(args, "competition"), From: str(args, "from"), To: str(args, "to"), Season: num(args, "season"), Limit: num(args, "limit")})
	case "team_stats":
		v = s.Store.Stats(str(args, "team"), str(args, "competition"), num(args, "season"), boolv(args, "home_only"))
	case "search_players":
		v = s.Store.SearchPlayers(PlayerFilter{Name: str(args, "name"), Nationality: str(args, "nationality"), Club: str(args, "club"), Position: str(args, "position"), MinOverall: num(args, "min_overall"), Limit: num(args, "limit")})
	case "standings":
		v = s.Store.Standings(str(args, "competition"), num(args, "season"))
	case "average_goals":
		v = map[string]any{"average_goals": s.Store.AverageGoals(str(args, "competition"), num(args, "season"))}
	default:
		return map[string]any{"jsonrpc": "2.0", "id": req.ID, "error": map[string]any{"code": -32602, "message": "unknown tool"}}
	}
	b, _ := json.Marshal(v)
	return map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": map[string]any{"content": []map[string]string{{"type": "text", "text": string(b)}}}}
}
func str(m map[string]any, k string) string { v, _ := m[k].(string); return v }
func num(m map[string]any, k string) int {
	switch v := m[k].(type) {
	case float64:
		return int(v)
	case int:
		return v
	}
	return 0
}
func boolv(m map[string]any, k string) bool { v, _ := m[k].(bool); return v }
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	sc := bufio.NewScanner(in)
	enc := json.NewEncoder(out)
	for sc.Scan() {
		var r rpcReq
		if json.Unmarshal(sc.Bytes(), &r) != nil {
			continue
		}
		if v := s.Handle(r); v != nil {
			if e := enc.Encode(v); e != nil {
				return e
			}
		}
	}
	return sc.Err()
}
func (s *Server) String() string {
	return fmt.Sprintf("brazilian-soccer (%d matches, %d players)", len(s.Store.Matches), len(s.Store.Players))
}

var _ = strings.TrimSpace
