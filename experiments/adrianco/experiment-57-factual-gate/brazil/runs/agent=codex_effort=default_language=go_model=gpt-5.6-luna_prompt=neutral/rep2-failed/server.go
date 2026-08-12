package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}
type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   any             `json:"error,omitempty"`
}

func toolDefinitions() []map[string]any {
	return []map[string]any{
		{"name": "search_matches", "description": "Find Brazilian soccer matches by team, competition, date range, or season.", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"team": map[string]string{"type": "string"}, "competition": map[string]string{"type": "string"}, "from": map[string]string{"type": "string", "description": "YYYY-MM-DD"}, "to": map[string]string{"type": "string", "description": "YYYY-MM-DD"}, "season": map[string]string{"type": "integer"}, "limit": map[string]string{"type": "integer"}}}},
		{"name": "team_stats", "description": "Calculate a team's win, draw, loss, goals, and win-rate record.", "inputSchema": map[string]any{"type": "object", "required": []string{"team"}, "properties": map[string]any{"team": map[string]string{"type": "string"}, "competition": map[string]string{"type": "string"}, "season": map[string]string{"type": "integer"}, "home_only": map[string]string{"type": "boolean"}, "away_only": map[string]string{"type": "boolean"}}}},
		{"name": "player_search", "description": "Search FIFA players by name, nationality, club, position, or rating.", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"name": map[string]string{"type": "string"}, "nationality": map[string]string{"type": "string"}, "club": map[string]string{"type": "string"}, "position": map[string]string{"type": "string"}, "min_overall": map[string]string{"type": "integer"}, "limit": map[string]string{"type": "integer"}}}},
		{"name": "competition_stats", "description": "Calculate match count, total goals, and average goals for a competition and season.", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"competition": map[string]string{"type": "string"}, "season": map[string]string{"type": "integer"}}}},
		{"name": "standings", "description": "Calculate a competition table from match results, ordered by points, goal difference, and goals scored.", "inputSchema": map[string]any{"type": "object", "properties": map[string]any{"competition": map[string]string{"type": "string"}, "season": map[string]string{"type": "integer"}}}},
	}
}

func intArg(m map[string]any, k string) int {
	if n, ok := m[k].(float64); ok {
		return int(n)
	}
	return 0
}
func boolArg(m map[string]any, k string) bool  { b, _ := m[k].(bool); return b }
func strArg(m map[string]any, k string) string { s, _ := m[k].(string); return s }
func callTool(s *Store, name string, raw json.RawMessage) (any, error) {
	var a map[string]any
	if len(raw) > 0 {
		if err := json.Unmarshal(raw, &a); err != nil {
			return nil, err
		}
	}
	switch name {
	case "search_matches":
		return jsonResult(s.SearchMatches(strArg(a, "team"), strArg(a, "competition"), strArg(a, "from"), strArg(a, "to"), intArg(a, "season"), intArg(a, "limit"))), nil
	case "team_stats":
		return jsonResult(s.Stats(strArg(a, "team"), strArg(a, "competition"), intArg(a, "season"), boolArg(a, "home_only"), boolArg(a, "away_only"))), nil
	case "player_search":
		return jsonResult(s.SearchPlayers(strArg(a, "name"), strArg(a, "nationality"), strArg(a, "club"), strArg(a, "position"), intArg(a, "min_overall"), intArg(a, "limit"))), nil
	case "competition_stats":
		return jsonResult(s.Average(strArg(a, "competition"), intArg(a, "season"))), nil
	case "standings":
		return jsonResult(s.Standings(strArg(a, "competition"), intArg(a, "season"))), nil
	}
	return nil, fmt.Errorf("unknown tool %q", name)
}

func Serve(in io.Reader, out io.Writer, s *Store) error {
	scan := bufio.NewScanner(in)
	enc := json.NewEncoder(out)
	for scan.Scan() {
		var req rpcRequest
		if err := json.Unmarshal(scan.Bytes(), &req); err != nil {
			continue
		}
		resp := rpcResponse{JSONRPC: "2.0", ID: req.ID}
		switch req.Method {
		case "initialize":
			resp.Result = map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer-mcp", "version": "1.0.0"}}
		case "notifications/initialized":
			continue
		case "tools/list":
			resp.Result = map[string]any{"tools": toolDefinitions()}
		case "tools/call":
			var p struct {
				Name      string          `json:"name"`
				Arguments json.RawMessage `json:"arguments"`
			}
			if err := json.Unmarshal(req.Params, &p); err != nil {
				resp.Error = map[string]any{"code": -32602, "message": err.Error()}
			} else if r, err := callTool(s, p.Name, p.Arguments); err != nil {
				resp.Error = map[string]any{"code": -32602, "message": err.Error()}
			} else {
				resp.Result = r
			}
		default:
			resp.Error = map[string]any{"code": -32601, "message": "method not found"}
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
	return scan.Err()
}

func dataDir() string {
	if d := os.Getenv("SOCCER_DATA_DIR"); d != "" {
		return d
	}
	cwd, _ := os.Getwd()
	candidates := []string{filepath.Join(cwd, "data", "kaggle"), filepath.Join(filepath.Dir(os.Args[0]), "data", "kaggle")}
	for _, d := range candidates {
		if _, e := os.Stat(filepath.Join(d, "Brasileirao_Matches.csv")); e == nil {
			return d
		}
	}
	return candidates[0]
}
