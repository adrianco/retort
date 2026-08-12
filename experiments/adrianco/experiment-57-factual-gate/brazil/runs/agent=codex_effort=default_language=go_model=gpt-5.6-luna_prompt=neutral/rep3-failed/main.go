package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type rpc struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      any             `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

func tools() []map[string]any {
	return []map[string]any{{"name": "search_matches", "description": "Find matches by team, date range, competition, or season", "inputSchema": map[string]any{"type": "object"}}, {"name": "team_stats", "description": "Calculate a team's match record and goals", "inputSchema": map[string]any{"type": "object", "required": []string{"team"}}}, {"name": "search_players", "description": "Search FIFA players by name, nationality, club, position, or rating", "inputSchema": map[string]any{"type": "object"}}, {"name": "standings", "description": "Calculate competition standings from match results", "inputSchema": map[string]any{"type": "object", "required": []string{"season"}}}, {"name": "statistics", "description": "Calculate aggregate goals, averages, and biggest wins", "inputSchema": map[string]any{"type": "object"}}}
}
func response(id any, result any) map[string]any {
	return map[string]any{"jsonrpc": "2.0", "id": id, "result": result}
}
func (s *Server) handle(q rpc) map[string]any {
	switch q.Method {
	case "initialize":
		return response(q.ID, map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}})
	case "notifications/initialized":
		return nil
	case "tools/list":
		return response(q.ID, map[string]any{"tools": tools()})
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if json.Unmarshal(q.Params, &p) != nil {
			return response(q.ID, map[string]any{"isError": true, "content": []map[string]string{{"type": "text", "text": "invalid tool arguments"}}})
		}
		v, e := s.CallTool(p.Name, p.Arguments)
		if e != nil {
			return response(q.ID, map[string]any{"isError": true, "content": []map[string]string{{"type": "text", "text": e.Error()}}})
		}
		b, _ := json.MarshalIndent(v, "", "  ")
		return response(q.ID, map[string]any{"content": []map[string]string{{"type": "text", "text": string(b)}}, "structuredContent": v})
	}
	return response(q.ID, map[string]any{"error": map[string]any{"code": -32601, "message": "method not found"}})
}
func run(s *Server, in io.Reader, out io.Writer) error {
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 4096), 16<<20)
	enc := json.NewEncoder(out)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "Content-Length:") {
			continue
		}
		var q rpc
		if err := json.Unmarshal([]byte(line), &q); err != nil {
			continue
		}
		if r := s.handle(q); r != nil {
			if err := enc.Encode(r); err != nil {
				return err
			}
		}
	}
	return sc.Err()
}
func main() {
	dir := os.Getenv("SOCCER_DATA_DIR")
	if dir == "" {
		dir = filepath.Join("data", "kaggle")
	}
	s, e := LoadStore(dir)
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
	if e = run(&Server{Store: s}, os.Stdin, os.Stdout); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
