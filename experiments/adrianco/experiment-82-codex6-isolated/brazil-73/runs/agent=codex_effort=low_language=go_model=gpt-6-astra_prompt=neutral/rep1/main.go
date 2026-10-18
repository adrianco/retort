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

type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	Annotations map[string]any `json:"annotations"`
}

func toolsList() []Tool {
	descriptions := [][2]string{
		{"dataset_info", "Dataset coverage, attribution, data quality warnings, normalization and known derby pairs. Read before making historical or current claims."},
		{"search_matches", "Find matches, scores and extended statistics across all five match files. Filter team/opponent, venue, inclusive dates, competition, season, stage, round, source or derbies. Newest first; biggest_win sorts by absolute goal margin. Page with limit/offset."},
		{"search_players", "Search historical FIFA players by partial name, nationality, normalized club and exact position or forwards. Sorted by overall rating descending; all source attributes included. No live roster claims."},
		{"team_profile", "Traverse team relationships to match history, home/away records, competitions and historical FIFA players. Requires team. All match filters apply only to matches."},
		{"head_to_head", "Compare two teams in either home/away order, including all results and win/draw/loss records. Requires team and opponent."},
		{"standings", "Calculate a league table from completed matches for a competition and season. Requires both. Dataset-derived, no official deductions; do not assert champion/relegation without checking completeness. Cup tables unsupported."},
		{"competition_results", "Schedules/results and stage counts for competition/season. Filter stage (final, semifinals, quarterfinals, round of 16, group stage) for knockout legs. Not a fabricated complete bracket."},
		{"statistics", "Aggregate goals per match, home/away wins, team records and seasonal trends. sort=goals for most goals, win_rate for best record (check played sample size), points otherwise. venue applies to team records."},
	}
	fields := map[string]any{}
	for _, s := range []string{"team", "opponent", "competition", "from", "to", "stage", "round", "source", "name", "nationality", "club", "position"} {
		fields[s] = map[string]any{"type": "string"}
	}
	fields["venue"] = map[string]any{"type": "string", "enum": []string{"home", "away", "either"}}
	fields["sort"] = map[string]any{"type": "string", "enum": []string{"date", "biggest_win", "goals", "points", "win_rate", "overall"}}
	fields["season"] = map[string]any{"type": "integer", "minimum": 0}
	fields["limit"] = map[string]any{"type": "integer", "minimum": 0, "maximum": 500, "description": "Default 50; max 500"}
	fields["offset"] = map[string]any{"type": "integer", "minimum": 0}
	fields["derbies"] = map[string]any{"type": "boolean"}
	out := []Tool{}
	for _, d := range descriptions {
		schema := map[string]any{"type": "object", "properties": fields, "additionalProperties": false}
		switch d[0] {
		case "team_profile":
			schema["required"] = []string{"team"}
		case "head_to_head":
			schema["required"] = []string{"team", "opponent"}
		case "standings":
			schema["required"] = []string{"competition", "season"}
		}
		out = append(out, Tool{d[0], d[1], schema, map[string]any{"readOnlyHint": true, "destructiveHint": false, "idempotentHint": true, "openWorldHint": false}})
	}
	return out
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}
type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}
type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

func strictDecode(raw []byte, v any) error {
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if e := d.Decode(v); e != nil {
		return e
	}
	var extra any
	if d.Decode(&extra) != io.EOF {
		return fmt.Errorf("unexpected trailing JSON")
	}
	return nil
}

// Serve implements newline-delimited MCP stdio. Logs must never use stdout.
func Serve(g *Graph, in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 4096), 4*1024*1024)
	enc := json.NewEncoder(out)
	initialized, ready := false, false
	for scanner.Scan() {
		line := scanner.Bytes()
		var req request
		var res response
		res.JSONRPC = "2.0"
		res.ID = json.RawMessage("null")
		if !json.Valid(line) {
			res.Error = &rpcError{-32700, "parse error"}
		} else if e := json.Unmarshal(line, &req); e != nil || req.JSONRPC != "2.0" || req.Method == "" {
			res.Error = &rpcError{-32600, "invalid request"}
		} else {
			if len(req.ID) == 0 {
				if initialized && req.Method == "notifications/initialized" {
					ready = true
				}
				continue
			}
			var id any
			_ = json.Unmarshal(req.ID, &id)
			switch id.(type) {
			case string, float64:
				res.ID = req.ID
			default:
				res.Error = &rpcError{-32600, "invalid request id"}
			}
			if res.Error == nil {
				switch req.Method {
				case "initialize":
					var p struct {
						ProtocolVersion string         `json:"protocolVersion"`
						Capabilities    map[string]any `json:"capabilities"`
						ClientInfo      map[string]any `json:"clientInfo"`
					}
					if e := json.Unmarshal(req.Params, &p); e != nil || p.ProtocolVersion == "" {
						res.Error = &rpcError{-32602, "initialize requires protocolVersion"}
						break
					}
					if initialized {
						res.Error = &rpcError{-32600, "already initialized"}
						break
					}
					version := p.ProtocolVersion
					switch version {
					case "2024-11-05", "2025-03-26", "2025-06-18":
					default:
						version = "2025-06-18"
					}
					initialized = true
					res.Result = map[string]any{"protocolVersion": version, "capabilities": map[string]any{"tools": map[string]any{"listChanged": false}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}, "instructions": caveat + " Use tools to translate natural-language questions; use prior conversation results for follow-up questions. All searches use normalized team identifiers and pagination."}
				case "ping":
					res.Result = map[string]any{}
				default:
					if !ready {
						res.Error = &rpcError{-32002, "initialize and send notifications/initialized first"}
						break
					}
					switch req.Method {
					case "tools/list":
						res.Result = map[string]any{"tools": toolsList()}
					case "tools/call":
						var p struct {
							Name      string          `json:"name"`
							Arguments json.RawMessage `json:"arguments"`
						}
						if e := json.Unmarshal(req.Params, &p); e != nil || p.Name == "" {
							res.Error = &rpcError{-32602, "invalid tool call"}
							break
						}
						known := false
						for _, t := range toolsList() {
							if t.Name == p.Name {
								known = true
							}
						}
						if !known {
							res.Error = &rpcError{-32602, "unknown tool: " + p.Name}
							break
						}
						if len(p.Arguments) == 0 {
							p.Arguments = json.RawMessage(`{}`)
						}
						var q Query
						var result any
						err := strictDecode(p.Arguments, &q)
						if bytes.Equal(bytes.TrimSpace(p.Arguments), []byte("null")) {
							err = fmt.Errorf("arguments must be an object")
						}
						if err == nil {
							result, err = g.Call(p.Name, q)
						}
						if err != nil {
							res.Result = map[string]any{"content": []any{map[string]string{"type": "text", "text": err.Error()}}, "isError": true}
						} else {
							b, e := json.MarshalIndent(result, "", "  ")
							if e != nil {
								return e
							}
							res.Result = map[string]any{"content": []any{map[string]string{"type": "text", "text": string(b)}}, "isError": false}
						}
					default:
						res.Error = &rpcError{-32601, "method not found"}
					}
				}
			}
		}
		if e := enc.Encode(res); e != nil {
			return e
		}
	}
	return scanner.Err()
}
func main() {
	dir := flag.String("data", "data/kaggle", "directory containing the six CSV datasets")
	flag.Parse()
	g, e := LoadGraph(*dir)
	if e == nil {
		e = Serve(g, os.Stdin, os.Stdout)
	}
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
