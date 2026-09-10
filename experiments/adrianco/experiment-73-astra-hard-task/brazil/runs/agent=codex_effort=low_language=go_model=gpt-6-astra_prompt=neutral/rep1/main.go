package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
)

type toolSpec struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	Annotations map[string]any `json:"annotations"`
}

func specs() []toolSpec {
	desc := map[string]string{
		"search_matches":   "Find fixtures/results, latest first. Filter a team/opponent in either direction, venue, inclusive dates, season, competition, stage or source. derby uses a curated rivalry list. Numeric Copa do Brasil finals are inferred. Paginate with offset/limit.",
		"search_players":   "Search historical FIFA snapshot by name substring, nationality (Brazil/Brazilian), normalized club substring, position or forwards. Sorted by overall rating descending. Includes all original player attributes.",
		"team_stats":       "Team record, home/away splits, competition and season trends, plus match history. Requires team.",
		"head_to_head":     "Compare two teams in either fixture direction; records use all matching results, independent of pagination. Requires team and opponent.",
		"team_profile":     "Cross-file team information: match record, competitions, history and FIFA player snapshot. Requires team.",
		"standings":        "Calculate Serie A/B season table from recorded completed matches. Requires competition and season. This is not an official table or verified relegation/champion determination.",
		"statistics":       "Goal averages, home/away outcomes, season comparisons, ranked team records and biggest victories. sort=goals or win_rate ranks teams; venue selects home/away records.",
		"competition_info": "Competition schedules/results grouped by season, stage and round. Use for cup fixtures; scores do not prove bracket advancement or penalty winners.",
		"graph":            "Traverse a team's knowledge graph: match home/away relationships, competition seasons, and player club snapshot edges. Requires team. offset/limit page matches and players independently.",
		"data_info":        "Dataset coverage, source row counts, normalized team names, conflict warnings and limitations. Individual goalscorers are not available."}
	out := []toolSpec{}
	for _, n := range sortedKeys(desc) {
		props := map[string]any{}
		for _, k := range []string{"team", "opponent", "venue", "competition", "from", "to", "stage", "source", "name", "nationality", "club", "position", "sort"} {
			props[k] = map[string]any{"type": "string"}
		}
		props["venue"] = map[string]any{"type": "string", "enum": []string{"home", "away", "either"}}
		props["season"] = map[string]any{"type": "integer"}
		props["limit"] = map[string]any{"type": "integer", "minimum": 0, "maximum": 500, "default": 50}
		props["offset"] = map[string]any{"type": "integer", "minimum": 0}
		props["derby"] = map[string]any{"type": "boolean"}
		schema := map[string]any{"type": "object", "properties": props, "additionalProperties": false}
		switch n {
		case "team_stats", "team_profile", "graph":
			schema["required"] = []string{"team"}
		case "head_to_head":
			schema["required"] = []string{"team", "opponent"}
		case "standings":
			schema["required"] = []string{"competition", "season"}
		}
		out = append(out, toolSpec{n, desc[n], schema, map[string]any{"readOnlyHint": true, "destructiveHint": false, "idempotentHint": true, "openWorldHint": false}})
	}
	return out
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

func rpcError(id json.RawMessage, code int, msg string) map[string]any {
	if len(id) == 0 {
		id = json.RawMessage("null")
	}
	return map[string]any{"jsonrpc": "2.0", "id": id, "error": map[string]any{"code": code, "message": msg}}
}

type Server struct {
	DB          *Store
	initialized bool
	ready       bool
}

func (s *Server) handle(raw []byte) any {
	var r request
	if !json.Valid(raw) {
		return rpcError(nil, -32700, "Parse error")
	}
	if e := json.Unmarshal(raw, &r); e != nil || r.JSONRPC != "2.0" || r.Method == "" {
		return rpcError(nil, -32600, "Invalid Request")
	}
	if len(r.ID) == 0 {
		if r.Method == "notifications/initialized" && s.initialized {
			s.ready = true
		}
		return nil
	}
	var id any
	if json.Unmarshal(r.ID, &id) != nil {
		return rpcError(nil, -32600, "Invalid id")
	}
	switch id.(type) {
	case string, float64:
	default:
		return rpcError(nil, -32600, "id must be string or number")
	}
	result := any(map[string]any{})
	switch r.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		if json.Unmarshal(r.Params, &p) != nil || p.ProtocolVersion == "" {
			return rpcError(r.ID, -32602, "protocolVersion is required")
		}
		s.initialized = true
		s.ready = false
		result = map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}, "instructions": "Translate natural language into the read-only tools. Use data_info for coverage and names. Resolve follow-ups from conversation context. Never invent current data, goalscorers or official cup/relegation outcomes. " + caveat}
	case "ping":
	case "tools/list":
		if !s.ready {
			return rpcError(r.ID, -32002, "Server not initialized")
		}
		result = map[string]any{"tools": specs()}
	case "tools/call":
		if !s.ready {
			return rpcError(r.ID, -32002, "Server not initialized")
		}
		var p struct {
			Name      string          `json:"name"`
			Arguments json.RawMessage `json:"arguments"`
		}
		if json.Unmarshal(r.Params, &p) != nil || p.Name == "" {
			return rpcError(r.ID, -32602, "Invalid tool call")
		}
		known := false
		for _, t := range specs() {
			if t.Name == p.Name {
				known = true
			}
		}
		if !known {
			return rpcError(r.ID, -32602, "Unknown tool: "+p.Name)
		}
		f := Filter{}
		if len(p.Arguments) > 0 {
			if bytes.Equal(bytes.TrimSpace(p.Arguments), []byte("null")) {
				return rpcError(r.ID, -32602, "arguments must be an object")
			}
			d := json.NewDecoder(bytes.NewReader(p.Arguments))
			d.DisallowUnknownFields()
			if e := d.Decode(&f); e != nil {
				return rpcError(r.ID, -32602, e.Error())
			}
		}
		value, e := s.DB.Query(p.Name, f)
		if e != nil {
			result = map[string]any{"content": []map[string]string{{"type": "text", "text": e.Error()}}, "isError": true}
		} else {
			b, _ := json.MarshalIndent(value, "", "  ")
			result = map[string]any{"content": []map[string]string{{"type": "text", "text": string(b)}}, "isError": false}
		}
	default:
		return rpcError(r.ID, -32601, "Method not found")
	}
	return map[string]any{"jsonrpc": "2.0", "id": r.ID, "result": result}
}

// Serve implements the newline-delimited JSON-RPC stdio transport. Diagnostics never use stdout.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	scan := bufio.NewScanner(in)
	scan.Buffer(make([]byte, 4096), 4*1024*1024)
	enc := json.NewEncoder(out)
	for scan.Scan() {
		b := bytes.TrimSpace(scan.Bytes())
		if len(b) == 0 {
			continue
		}
		r := s.handle(b)
		if r != nil {
			if e := enc.Encode(r); e != nil {
				return e
			}
		}
	}
	return scan.Err()
}
func main() {
	dir := flag.String("data", "data/kaggle", "directory containing the six CSV datasets")
	flag.Parse()
	db, e := Load(*dir)
	if e == nil {
		e = (&Server{DB: db}).Serve(os.Stdin, os.Stdout)
	}
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
