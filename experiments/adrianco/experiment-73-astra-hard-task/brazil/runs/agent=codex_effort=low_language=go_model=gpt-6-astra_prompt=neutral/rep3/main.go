package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
)

type Tool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema map[string]any  `json:"inputSchema"`
	Annotations map[string]bool `json:"annotations"`
}

func schema(properties map[string]any, required ...string) map[string]any {
	m := map[string]any{"type": "object", "properties": properties, "additionalProperties": false}
	if len(required) > 0 {
		m["required"] = required
	}
	return m
}
func prop(t, description string) map[string]any {
	return map[string]any{"type": t, "description": description}
}
func filterProps() map[string]any {
	return map[string]any{
		"team": prop("string", "Team name; accent/state/full-name aliases accepted."), "opponent": prop("string", "Opponent; requires team. Searches both fixture directions."), "venue": map[string]any{"type": "string", "enum": []string{"home", "away", "either"}}, "competition": prop("string", "Brasileirão (or Serie A), Copa do Brasil, Libertadores, Serie B, Serie C."), "season": map[string]any{"type": "integer", "minimum": 1}, "date_from": prop("string", "Inclusive date, YYYY-MM-DD or DD/MM/YYYY."), "date_to": prop("string", "Inclusive date."), "round": prop("string", "Exact source round number."), "stage": prop("string", "Exact stage: final, semifinals, quarterfinals, round of 16, group stage."), "source": prop("string", "Filter by CSV filename, including merged provenance."), "derbies": prop("boolean", "Only curated traditional rivalries; list is not exhaustive."), "limit": map[string]any{"type": "integer", "minimum": 0, "maximum": 500, "default": 50}, "offset": map[string]any{"type": "integer", "minimum": 0}, "sort": map[string]any{"type": "string", "enum": []string{"date_desc", "date_asc", "biggest_wins"}}}
}
func toolList() []Tool {
	specs := []struct {
		name, desc string
		required   []string
	}{
		{"search_matches", "Search fixtures/results across all five match CSVs. Use team+opponent for derbies/head-to-head, date_desc + limit 1 for latest match, stage final for finals, biggest_wins for margins.", nil},
		{"team_stats", "Win/draw/loss, goals and win rate, home/away split, competitions played and season trends. Includes unplayed fixture count; aggregates ignore pagination.", []string{"team"}},
		{"head_to_head", "Compare two teams across both home/away directions with full-dataset records and paginated matches.", []string{"team", "opponent"}},
		{"standings", "Calculated league standings by season; not official disciplinary/tiebreak standings. Cup tables are rejected. Do not infer relegation/champion from incomplete coverage.", []string{"competition", "season"}},
		{"statistics", "Goal averages, home/away win rates and ranked team records. Compare seasons by making one call per season. Aggregates ignore pagination.", nil},
		{"competition_results", "Schedule/results and stage-grouped match IDs (bracket evidence). No penalty/aggregate advancing-team inference. Pagination applies to match details only.", []string{"competition", "season"}},
	}
	out := []Tool{}
	for _, x := range specs {
		out = append(out, Tool{x.name, x.desc, schema(filterProps(), x.required...), map[string]bool{"readOnlyHint": true, "destructiveHint": false, "idempotentHint": true, "openWorldHint": false}})
	}
	out = append(out, Tool{Name: "search_players", Description: "FIFA snapshot search by partial name, nationality, normalized club, position (or forward), minimum rating. Sorted by overall descending; retains every attribute and club aggregates.", InputSchema: schema(map[string]any{"name": prop("string", "Partial player name as recorded in FIFA."), "nationality": prop("string", "Country, e.g. Brazil."), "club": prop("string", "Club name, normalized."), "position": prop("string", "FIFA position or forward."), "min_overall": map[string]any{"type": "integer", "minimum": 0, "maximum": 100}, "limit": map[string]any{"type": "integer", "minimum": 0, "maximum": 500}, "offset": map[string]any{"type": "integer", "minimum": 0}})})
	out = append(out, Tool{Name: "team_graph", Description: "Traverse typed team, match, competition and FIFA player relationships; use offset to retrieve all edges. Player membership is historical snapshot data.", InputSchema: schema(map[string]any{"team": prop("string", "Team name."), "limit": map[string]any{"type": "integer", "minimum": 0, "maximum": 500}, "offset": map[string]any{"type": "integer", "minimum": 0}}, "team")})
	out = append(out, Tool{Name: "dataset_info", Description: "Sources, attribution, row counts, date/season coverage and data-quality warnings. Scorers and official knockout advancement cannot be inferred from these data.", InputSchema: schema(map[string]any{})})
	return out
}
func decodeArgs(raw json.RawMessage, v any) error {
	if len(raw) == 0 {
		raw = json.RawMessage(`{}`)
	}
	if !strings.HasPrefix(strings.TrimSpace(string(raw)), "{") {
		return fmt.Errorf("arguments must be an object")
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if e := d.Decode(v); e != nil {
		return e
	}
	return nil
}
func (s *Store) Call(name string, args json.RawMessage) (any, error) {
	switch name {
	case "dataset_info":
		var a struct{}
		if e := decodeArgs(args, &a); e != nil {
			return nil, e
		}
		coverage := map[string]map[int]int{}
		for _, m := range s.Matches {
			if coverage[m.Competition] == nil {
				coverage[m.Competition] = map[int]int{}
			}
			coverage[m.Competition][m.Season]++
		}
		return map[string]any{"sources": s.Sources, "unique_matches": len(s.Matches), "players": len(s.Players), "coverage": coverage, "warnings": s.Warnings, "limitations": []string{"Historical datasets only, not live data or current rosters.", "No goal-scorer events, shootout results, disciplinary deductions or complete official tiebreakers.", "Deduplication merges cross-source fixtures with the same competition, season, home and away within one day (league fixtures also merge postponed dates); first source has precedence on conflict. Raw alternatives retained.", "Copa do Brasil stages inferred only when the largest numeric round contains a two-legged final; incomplete seasons remain unlabeled. Extended calendar years are corrected from matching dated primary fixtures.", "Curated rivalry and club aliases are not exhaustive; use source names for other teams."}}, nil
	case "search_players":
		var f PlayerFilter
		if e := decodeArgs(args, &f); e != nil {
			return nil, e
		}
		return s.FindPlayers(f)
	case "team_graph":
		var a struct {
			Team   string `json:"team"`
			Limit  int    `json:"limit"`
			Offset int    `json:"offset"`
		}
		if e := decodeArgs(args, &a); e != nil {
			return nil, e
		}
		return s.Graph(a.Team, a.Limit, a.Offset)
	case "search_matches", "team_stats", "head_to_head", "standings", "statistics", "competition_results":
		var f Filter
		if e := decodeArgs(args, &f); e != nil {
			return nil, e
		}
		switch name {
		case "team_stats":
			return s.TeamStats(f)
		case "standings":
			return s.Standings(f)
		case "statistics":
			return s.Statistics(f)
		}
		if name == "head_to_head" && (f.Team == "" || f.Opponent == "") {
			return nil, fmt.Errorf("team and opponent are required")
		}
		if name == "competition_results" && (f.Competition == "" || f.Season == 0) {
			return nil, fmt.Errorf("competition and season are required")
		}
		ms, e := s.FindMatches(f)
		if e != nil {
			return nil, e
		}
		if name == "head_to_head" {
			return map[string]any{"team": teamRecord(ms, NormalizeTeam(f.Team)), "opponent": teamRecord(ms, NormalizeTeam(f.Opponent)), "results": matchPage(ms, f)}, nil
		}
		if name == "competition_results" {
			stages := map[string][]string{}
			for _, m := range ms {
				stage := m.Stage
				if stage == "" {
					stage = "round " + m.Round
				}
				stages[stage] = append(stages[stage], m.ID)
			}
			return map[string]any{"stages": stages, "results": matchPage(ms, f), "note": "Stage-grouped fixtures, not a reconstructed advancement tree; penalties and official advancement are unavailable."}, nil
		}
		return matchPage(ms, f), nil
	}
	return nil, fmt.Errorf("unknown tool %q", name)
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

func rpcError(id json.RawMessage, code int, message string) map[string]any {
	if len(id) == 0 {
		id = json.RawMessage("null")
	}
	return map[string]any{"jsonrpc": "2.0", "id": id, "error": map[string]any{"code": code, "message": message}}
}

// Serve implements newline-delimited MCP stdio. Stdout is exclusively JSON-RPC.
func Serve(in io.Reader, out io.Writer, s *Store) error {
	scan := bufio.NewScanner(in)
	scan.Buffer(make([]byte, 4096), 4*1024*1024)
	enc := json.NewEncoder(out)
	initialized := false
	ready := false
	for scan.Scan() {
		line := bytes.TrimSpace(scan.Bytes())
		var req request
		if !json.Valid(line) {
			if e := enc.Encode(rpcError(nil, -32700, "Parse error")); e != nil {
				return e
			}
			continue
		}
		if len(line) == 0 || line[0] != '{' || json.Unmarshal(line, &req) != nil || req.JSONRPC != "2.0" || req.Method == "" {
			if e := enc.Encode(rpcError(req.ID, -32600, "Invalid Request")); e != nil {
				return e
			}
			continue
		}
		if len(req.ID) > 0 {
			var id any
			_ = json.Unmarshal(req.ID, &id)
			switch id.(type) {
			case string, float64, nil:
			default:
				if e := enc.Encode(rpcError(nil, -32600, "Invalid request id")); e != nil {
					return e
				}
				continue
			}
		}
		if len(req.ID) == 0 {
			if req.Method == "notifications/initialized" && initialized {
				ready = true
			}
			continue
		}
		var result any
		var fault any
		switch req.Method {
		case "initialize":
			var p struct {
				ProtocolVersion string         `json:"protocolVersion"`
				Capabilities    map[string]any `json:"capabilities"`
				ClientInfo      map[string]any `json:"clientInfo"`
			}
			if json.Unmarshal(req.Params, &p) != nil || p.ProtocolVersion == "" {
				fault = rpcError(req.ID, -32602, "Invalid initialize parameters")
				break
			}
			version := p.ProtocolVersion
			switch version {
			case "2024-11-05", "2025-03-26", "2025-06-18":
			default:
				version = "2025-06-18"
			}
			initialized = true
			ready = false
			result = map[string]any{"protocolVersion": version, "capabilities": map[string]any{"tools": map[string]any{"listChanged": false}}, "serverInfo": map[string]any{"name": "brazilian-soccer", "version": "1.0.0"}, "instructions": "Use structured tools to answer natural-language soccer questions. Consult dataset_info for coverage. Only claim facts in these historical datasets; follow-up questions are resolved by the host LLM. Top scorers and shootout winners are unavailable. Page results using next_offset."}
		case "ping":
			result = map[string]any{}
		default:
			if !ready {
				fault = rpcError(req.ID, -32002, "Initialize and send notifications/initialized first")
				break
			}
			switch req.Method {
			case "tools/list":
				var p struct {
					Cursor string `json:"cursor"`
				}
				if len(req.Params) > 0 && json.Unmarshal(req.Params, &p) != nil || p.Cursor != "" {
					fault = rpcError(req.ID, -32602, "Invalid tools/list parameters")
					break
				}
				result = map[string]any{"tools": toolList()}
			case "tools/call":
				var p struct {
					Name      string          `json:"name"`
					Arguments json.RawMessage `json:"arguments"`
					Meta      map[string]any  `json:"_meta"`
				}
				if json.Unmarshal(req.Params, &p) != nil || p.Name == "" {
					fault = rpcError(req.ID, -32602, "Invalid tools/call parameters")
					break
				}
				known := false
				for _, t := range toolList() {
					if t.Name == p.Name {
						known = true
					}
				}
				if !known {
					fault = rpcError(req.ID, -32602, "Unknown tool: "+p.Name)
					break
				}
				v, e := s.Call(p.Name, p.Arguments)
				if e != nil {
					result = map[string]any{"isError": true, "content": []any{map[string]any{"type": "text", "text": e.Error()}}}
				} else {
					b, e := json.Marshal(v)
					if e != nil {
						return e
					}
					result = map[string]any{"content": []any{map[string]any{"type": "text", "text": string(b)}}, "isError": false}
				}
			default:
				fault = rpcError(req.ID, -32601, "Method not found")
			}
		}
		if fault != nil {
			if e := enc.Encode(fault); e != nil {
				return e
			}
		} else {
			if e := enc.Encode(map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": result}); e != nil {
				return e
			}
		}
	}
	return scan.Err()
}
func main() {
	dir := flag.String("data", "data/kaggle", "Directory containing the six CSV datasets")
	flag.Parse()
	s, e := LoadStore(*dir)
	if e == nil {
		fmt.Fprintf(os.Stderr, "Loaded %d unique matches and %d players (%d data warnings)\n", len(s.Matches), len(s.Players), len(s.Warnings))
		e = Serve(os.Stdin, os.Stdout, s)
	}
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
