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
		return map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}, "resources": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}}}
	case "notifications/initialized":
		return nil
	case "tools/list":
		return map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": map[string]any{"tools": tools()}}
	case "resources/list":
		return map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": map[string]any{"resources": resources()}}
	case "resources/read":
		return s.readResource(req)
	case "tools/call":
		return s.call(req)
	}
	return map[string]any{"jsonrpc": "2.0", "id": req.ID, "error": map[string]any{"code": -32601, "message": "method not found"}}
}
func tools() []map[string]any {
	return []map[string]any{
		{"name": "search_matches", "description": "Search Brazilian soccer matches by teams, dates, competition, or season", "inputSchema": schema(map[string]string{"team": "string", "opponent": "string", "competition": "string", "season": "integer", "from": "string", "to": "string", "limit": "integer"})},
		{"name": "team_stats", "description": "Calculate a team's match record and goals", "inputSchema": schema(map[string]string{"team": "string", "competition": "string", "season": "integer", "home_only": "boolean"})},
		{"name": "head_to_head", "description": "Calculate wins, draws, losses, and goals between two teams", "inputSchema": schema(map[string]string{"team1": "string", "team2": "string", "competition": "string", "season": "integer"})},
		{"name": "search_players", "description": "Search FIFA players by name, nationality, club, position, or rating", "inputSchema": schema(map[string]string{"name": "string", "nationality": "string", "club": "string", "position": "string", "min_overall": "integer", "limit": "integer"})},
		{"name": "standings", "description": "Calculate competition standings from match results", "inputSchema": schema(map[string]string{"competition": "string", "season": "integer"})},
		{"name": "average_goals", "description": "Calculate average goals per match", "inputSchema": schema(map[string]string{"competition": "string", "season": "integer"})},
	}
}
func schema(props map[string]string) map[string]any {
	p := map[string]any{}
	for k, v := range props {
		p[k] = map[string]string{"type": v}
	}
	return map[string]any{"type": "object", "properties": p}
}
func resources() []map[string]any {
	return []map[string]any{{"uri": "soccer://datasets", "name": "Loaded soccer datasets", "description": "Catalog of the CSV datasets used by this server", "mimeType": "text/plain"}}
}
func (s *Server) readResource(req rpcReq) any {
	var p map[string]any
	_ = json.Unmarshal(req.Params, &p)
	if str(p, "uri") != "soccer://datasets" {
		return map[string]any{"jsonrpc": "2.0", "id": req.ID, "error": map[string]any{"code": -32002, "message": "resource not found"}}
	}
	text := fmt.Sprintf("Matches loaded: %d\nPlayers loaded: %d\nSources: Brasileirão, Copa do Brasil, Libertadores, extended Brazilian matches, historical Brasileirão, FIFA players", len(s.Store.Matches), len(s.Store.Players))
	return map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": map[string]any{"contents": []map[string]string{{"uri": "soccer://datasets", "mimeType": "text/plain", "text": text}}}}
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
	case "head_to_head":
		v = s.Store.HeadToHead(str(args, "team1"), str(args, "team2"), str(args, "competition"), num(args, "season"))
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
