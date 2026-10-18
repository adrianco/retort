package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
)

type toolDef struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

func toolList() []toolDef {
	descriptions := [][2]string{
		{"search_matches", "Find historical fixtures by normalized team and opponent (either direction), venue, inclusive dates, competition, season, stage, source, or traditional derbies. Latest first; sort biggest_win for largest goal margins. Paginated; total is before pagination."},
		{"search_players", "Search FIFA historical player snapshot by name substring, nationality, club, position (or forward), minimum overall rating. Sorted by overall rating descending. Includes all source attributes."},
		{"team_profile", "Traverse team relationships to fixtures, competition appearances, aggregate record and FIFA players. Team is required. Roster is historical and may be from a different season."},
		{"head_to_head", "Compare two distinct teams using team and opponent; return wins, draws, losses, goals and recent meetings."},
		{"standings", "Calculate league table for competition and season; 3 points per win. No certified champion or relegation claims. Use competition_results for cups."},
		{"statistics", "Aggregate goals per match, home/away wins, and team records. Group by season or competition for trends; sort teams by points, goals or win_rate. Venue selects home/away team records; summary covers selected fixtures."},
		{"competition_results", "Get schedules/results and stage counts for a competition, optionally season. Stage final matches exact finals, not semifinals. Does not infer shootout winners or a complete bracket."},
		{"data_info", "Inspect dataset coverage, all six source counts, deduplication conflicts and limitations. Individual goalscorers cannot be inferred from these datasets."},
	}
	props := map[string]any{}
	for k, d := range map[string]string{"team": "Team name, accepting aliases and accents", "opponent": "Other team in a head-to-head pairing", "competition": "Brasileirão (Serie A), Copa do Brasil, Libertadores, Série B or Série C", "from": "Inclusive date YYYY-MM-DD", "to": "Inclusive date YYYY-MM-DD", "stage": "Exact stage or round, e.g. final, semifinals, group stage, or 22", "source": "Exact CSV filename from data_info", "name": "Player name substring", "nationality": "Exact nationality, e.g. Brazil", "club": "Normalized club name substring", "position": "FIFA position or forward"} {
		props[k] = map[string]any{"type": "string", "description": d}
	}
	props["venue"] = map[string]any{"type": "string", "enum": []string{"home", "away", "either"}}
	props["sort"] = map[string]any{"type": "string", "enum": []string{"latest", "biggest_win", "points", "goals", "win_rate"}}
	props["group_by"] = map[string]any{"type": "string", "enum": []string{"season", "competition"}}
	props["season"] = map[string]any{"type": "integer", "minimum": 1}
	props["min_rating"] = map[string]any{"type": "integer", "minimum": 0, "maximum": 100}
	props["limit"] = map[string]any{"type": "integer", "minimum": 0, "maximum": 500, "description": "Page size; 0 or omitted uses 50"}
	props["offset"] = map[string]any{"type": "integer", "minimum": 0}
	props["derbies"] = map[string]any{"type": "boolean", "description": "Only curated traditional rival pairs, not exhaustive"}
	out := []toolDef{}
	for _, d := range descriptions {
		schema := map[string]any{"type": "object", "properties": props, "additionalProperties": false}
		switch d[0] {
		case "team_profile":
			schema["required"] = []string{"team"}
		case "head_to_head":
			schema["required"] = []string{"team", "opponent"}
		case "standings":
			schema["required"] = []string{"competition", "season"}
		case "competition_results":
			schema["required"] = []string{"competition"}
		}
		out = append(out, toolDef{d[0], d[1], schema})
	}
	return out
}
func strictJSON(raw []byte, out any) error {
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	return d.Decode(out)
}

// Serve implements newline-delimited JSON-RPC on stdio, MCP 2024-11-05 through 2025-11-25.
// It holds no conversation state: the connected LLM resolves natural language and follow-ups.
func Serve(in io.Reader, out io.Writer, s *Store) error {
	scan := bufio.NewScanner(in)
	scan.Buffer(make([]byte, 4096), 4*1024*1024)
	enc := json.NewEncoder(out)
	initialized, ready := false, false
	for scan.Scan() {
		raw := scan.Bytes()
		var req struct {
			JSONRPC string          `json:"jsonrpc"`
			ID      json.RawMessage `json:"id"`
			Method  string          `json:"method"`
			Params  json.RawMessage `json:"params"`
		}
		var result any
		code, msg := 0, ""
		if !json.Valid(raw) {
			code, msg = -32700, "Parse error"
		} else if e := json.Unmarshal(raw, &req); e != nil || req.JSONRPC != "2.0" || req.Method == "" {
			code, msg = -32600, "Invalid Request"
		}
		if code == 0 && len(req.ID) > 0 {
			var id any
			_ = json.Unmarshal(req.ID, &id)
			switch id.(type) {
			case string, float64, nil:
			default:
				code, msg = -32600, "Invalid request id"
			}
		}
		if code == 0 && len(req.ID) == 0 {
			if req.Method == "notifications/initialized" && initialized {
				ready = true
			}
			continue
		}
		if code == 0 {
			switch req.Method {
			case "initialize":
				var p struct {
					ProtocolVersion string         `json:"protocolVersion"`
					Capabilities    map[string]any `json:"capabilities"`
					ClientInfo      map[string]any `json:"clientInfo"`
				}
				if e := json.Unmarshal(req.Params, &p); e != nil || p.ProtocolVersion == "" {
					code, msg = -32602, "Invalid initialize params"
					break
				}
				version := p.ProtocolVersion
				if !contains([]string{"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}, version) {
					version = "2025-11-25"
				}
				initialized = true
				ready = false
				result = map[string]any{"protocolVersion": version, "capabilities": map[string]any{"tools": map[string]any{"listChanged": false}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}, "instructions": "Use tools to answer natural-language soccer questions. Call data_info for coverage. Results are historical; never invent missing players, scorer events, shootout results, titles or relegations. Resolve follow-ups from conversation context and paginate as needed."}
			case "ping":
				result = map[string]any{}
			case "tools/list":
				if !ready {
					code, msg = -32002, "Server not initialized"
					break
				}
				result = map[string]any{"tools": toolList()}
			case "tools/call":
				if !ready {
					code, msg = -32002, "Server not initialized"
					break
				}
				var p struct {
					Name      string          `json:"name"`
					Arguments json.RawMessage `json:"arguments"`
					Meta      map[string]any  `json:"_meta,omitempty"`
				}
				if e := strictJSON(req.Params, &p); e != nil || p.Name == "" {
					code, msg = -32602, "Invalid tool call params"
					break
				}
				known := false
				for _, t := range toolList() {
					if t.Name == p.Name {
						known = true
					}
				}
				if !known {
					code, msg = -32602, "Unknown tool"
					break
				}
				var q Query
				var e error
				if len(p.Arguments) > 0 {
					if bytes.Equal(bytes.TrimSpace(p.Arguments), []byte("null")) {
						e = fmt.Errorf("arguments must be an object")
					} else {
						e = strictJSON(p.Arguments, &q)
					}
				}
				var v any
				if e == nil {
					v, e = s.Call(p.Name, q)
				}
				isError := e != nil
				var txt string
				if e != nil {
					txt = e.Error()
				} else {
					b, err := json.MarshalIndent(v, "", "  ")
					if err != nil {
						return err
					}
					txt = string(b)
				}
				result = map[string]any{"content": []any{map[string]string{"type": "text", "text": txt}}, "isError": isError}
			default:
				code, msg = -32601, "Method not found"
			}
		}
		id := req.ID
		if len(id) == 0 || code == -32700 || code == -32600 {
			id = json.RawMessage("null")
		}
		response := map[string]any{"jsonrpc": "2.0", "id": id}
		if code != 0 {
			response["error"] = map[string]any{"code": code, "message": msg}
		} else {
			response["result"] = result
		}
		if e := enc.Encode(response); e != nil {
			return e
		}
	}
	return scan.Err()
}
