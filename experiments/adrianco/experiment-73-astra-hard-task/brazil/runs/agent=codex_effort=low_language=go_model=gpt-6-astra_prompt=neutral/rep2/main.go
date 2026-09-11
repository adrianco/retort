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

func toolList() []map[string]any {
	descriptions := map[string]string{
		"search_matches": "Find results/schedules across all five match files; filter team, opponent (either direction), venue, inclusive date range, season, competition, round, stage, source, or traditional derbies. Latest first; sort biggest_win for largest margins. Paginate with limit/offset. Cup round codes are source values; consult data rather than assuming a numeric final round.",
		"search_players": "Search historical FIFA players by partial name, nationality, club, or position (including forwards), sorted by overall rating. Includes all original attributes. Brazilian nationality is Brazil.",
		"team_info":      "Team graph: record, home/away splits, trends by season, competition participation/performance, match history and linked FIFA players. Requires team.",
		"head_to_head":   "Compare team and opponent in either home/away direction. Wins/draws/losses are from team's perspective. Requires both teams.",
		"standings":      "Calculate Brasileirão season table from deduplicated results. Requires competition and season. Does not claim official champion or relegation from incomplete coverage; cup brackets use search_matches instead.",
		"statistics":     "Aggregate goals per match, home win rate, season comparison, and team rankings. Venue home/away selects ranking split. sort goals ranks goals scored, otherwise win rate (sample sizes included).",
		"data_info":      "Inspect source row counts, score conflicts and dataset limitations. No individual scorer data is available.",
	}
	props := map[string]any{}
	for _, k := range []string{"team", "opponent", "venue", "competition", "from", "to", "round", "stage", "source", "sort", "name", "nationality", "club", "position"} {
		props[k] = map[string]any{"type": "string"}
	}
	for _, k := range []string{"season", "limit", "offset"} {
		props[k] = map[string]any{"type": "integer", "minimum": 0}
	}
	props["derbies"] = map[string]any{"type": "boolean"}
	out := []map[string]any{}
	for _, name := range []string{"search_matches", "search_players", "team_info", "head_to_head", "standings", "statistics", "data_info"} {
		required := []string{}
		if name == "team_info" || name == "head_to_head" {
			required = append(required, "team")
		}
		if name == "head_to_head" {
			required = append(required, "opponent")
		}
		if name == "standings" {
			required = append(required, "competition", "season")
		}
		out = append(out, map[string]any{"name": name, "description": descriptions[name], "inputSchema": map[string]any{"type": "object", "properties": props, "additionalProperties": false, "required": required}, "annotations": map[string]any{"readOnlyHint": true, "destructiveHint": false, "idempotentHint": true, "openWorldHint": false}})
	}
	return out
}
func Serve(g *Graph, in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 4096), 4*1024*1024)
	enc := json.NewEncoder(out)
	initialized := false
	for scanner.Scan() {
		line := scanner.Bytes()
		var req struct {
			JSONRPC string          `json:"jsonrpc"`
			ID      json.RawMessage `json:"id"`
			Method  string          `json:"method"`
			Params  json.RawMessage `json:"params"`
		}
		err := json.Unmarshal(line, &req)
		var result any
		code := 0
		message := ""
		if err != nil {
			code = -32700
			message = "Parse error"
		} else if req.JSONRPC != "2.0" || req.Method == "" {
			code = -32600
			message = "Invalid Request"
		} else if len(req.ID) == 0 {
			continue
		} else {
			switch req.Method {
			case "initialize":
				var p struct {
					ProtocolVersion string `json:"protocolVersion"`
				}
				if json.Unmarshal(req.Params, &p) != nil {
					code = -32602
					message = "Invalid initialize params"
					break
				}
				version := p.ProtocolVersion
				if version != "2024-11-05" && version != "2025-03-26" && version != "2025-06-18" {
					version = "2025-06-18"
				}
				initialized = true
				result = map[string]any{"protocolVersion": version, "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}, "instructions": "Use structured tools to answer natural language questions; keep follow-up context in the client. Results are historical and limited to dataset coverage. " + caveat}
			case "ping":
				result = map[string]any{}
			case "tools/list":
				if !initialized {
					code = -32002
					message = "Initialize first"
				} else {
					result = map[string]any{"tools": toolList()}
				}
			case "tools/call":
				if !initialized {
					code = -32002
					message = "Initialize first"
					break
				}
				var p struct {
					Name      string          `json:"name"`
					Arguments json.RawMessage `json:"arguments"`
				}
				if json.Unmarshal(req.Params, &p) != nil || p.Name == "" {
					code = -32602
					message = "Invalid tool params"
					break
				}
				known := false
				for _, t := range toolList() {
					if t["name"] == p.Name {
						known = true
					}
				}
				if !known {
					code = -32602
					message = "Unknown tool"
					break
				}
				f := Filter{}
				if len(p.Arguments) == 0 {
					p.Arguments = json.RawMessage(`{}`)
				}
				d := json.NewDecoder(bytes.NewReader(p.Arguments))
				d.DisallowUnknownFields()
				if e := d.Decode(&f); e != nil {
					code = -32602
					message = e.Error()
					break
				}
				value, e := g.Query(p.Name, f)
				if e != nil {
					result = map[string]any{"content": []any{map[string]string{"type": "text", "text": e.Error()}}, "isError": true}
				} else {
					b, _ := json.MarshalIndent(value, "", "  ")
					result = map[string]any{"content": []any{map[string]string{"type": "text", "text": string(b)}}, "structuredContent": value, "isError": false}
				}
			default:
				code = -32601
				message = "Method not found"
			}
		}
		id := req.ID
		if len(id) == 0 {
			id = json.RawMessage("null")
		}
		response := map[string]any{"jsonrpc": "2.0", "id": id}
		if code != 0 {
			response["error"] = map[string]any{"code": code, "message": message}
		} else {
			response["result"] = result
		}
		if e := enc.Encode(response); e != nil {
			return e
		}
	}
	return scanner.Err()
}
func main() {
	dir := flag.String("data", "data/kaggle", "Directory containing the six CSV datasets")
	flag.Parse()
	g, e := Load(*dir)
	if e == nil {
		e = Serve(g, os.Stdin, os.Stdout)
	}
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
