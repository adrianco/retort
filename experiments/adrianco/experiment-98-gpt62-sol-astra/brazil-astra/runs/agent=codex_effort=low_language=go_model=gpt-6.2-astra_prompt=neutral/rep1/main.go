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

type obj = map[string]any

func catalog() []obj {
	common := "team opponent venue competition season start end stage source derbies"
	defs := []struct{ name, desc, fields string }{
		{"matches", "Find fixtures, newest first, with source rows and nullable scores. Use opponent for head-to-head, stage for finals or bracket rounds, sort=margin for biggest victories.", common + " sort limit offset"},
		{"records", "Calculated standings or team records from played fixtures. Use venue for home/away rankings. Sort by points (default), goals or win_rate. Standings reflect dataset coverage and exclude disciplinary adjustments.", common + " sort limit offset"},
		{"summary", "Totals, scoring averages, home win percentage and competitions played. Compare trends by calling once per season or competition. Individual goal scorers are unavailable.", common},
		{"players", "Search FIFA snapshot by name or club substring, nationality and position (code or forward). Highest overall first. Use club as team in match tools to link the datasets.", "name nationality club position limit offset"}}
	out := []obj{}
	for _, d := range defs {
		p := obj{}
		for _, k := range strings.Fields(d.fields) {
			typ := "string"
			switch k {
			case "limit", "offset":
				typ = "integer"
			case "derbies":
				typ = "boolean"
			}
			field := obj{"type": typ}
			switch k {
			case "competition":
				field["enum"] = []string{"Serie A", "Serie B", "Serie C", "Copa do Brasil", "Copa Libertadores", "Brasileirão"}
			case "venue":
				field["enum"] = []string{"home", "away", "either"}
			case "start", "end":
				field["description"] = "Inclusive date in YYYY-MM-DD format"
			case "limit":
				field["minimum"] = 1
				field["maximum"] = 100
				field["default"] = 20
			case "offset":
				field["minimum"] = 0
			case "source":
				field["enum"] = files[:5]
			case "stage":
				field["description"] = "Tournament stage (e.g. final, semifinals, quarterfinals, group stage) or round number"
			case "sort":
				if d.name == "matches" {
					field["enum"] = []string{"date", "margin"}
				} else {
					field["enum"] = []string{"points", "goals", "win_rate"}
				}
			}
			p[k] = field
		}
		out = append(out, obj{"name": d.name, "description": d.desc, "inputSchema": obj{"type": "object", "properties": p, "additionalProperties": false}})
	}
	return out
}

type request struct {
	JSONRPC, Method string
	ID              json.RawMessage
	Params          json.RawMessage
}

func (g *Graph) reply(line []byte) any {
	var r request
	failure := func(code int, msg string) any {
		return obj{"jsonrpc": "2.0", "id": r.ID, "error": obj{"code": code, "message": msg}}
	}
	if !json.Valid(line) {
		return failure(-32700, "Parse error")
	}
	if json.Unmarshal(line, &r) != nil || r.JSONRPC != "2.0" || r.Method == "" {
		return failure(-32600, "Invalid Request")
	}
	if r.ID == nil {
		return nil
	}
	var result any
	switch r.Method {
	case "initialize":
		var p struct{ ProtocolVersion string }
		_ = json.Unmarshal(r.Params, &p)
		v := p.ProtocolVersion
		switch v {
		case "2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25":
		default:
			v = "2025-06-18"
		}
		result = obj{"protocolVersion": v, "capabilities": obj{"tools": obj{}}, "serverInfo": obj{"name": "brazilian-soccer", "version": "1.0.0"}}
	case "ping":
		result = obj{}
	case "tools/list":
		result = obj{"tools": catalog()}
	case "tools/call":
		var p struct {
			Name      string
			Arguments Args
		}
		d := json.NewDecoder(bytes.NewReader(r.Params))
		d.DisallowUnknownFields()
		if e := d.Decode(&p); e != nil {
			return failure(-32602, e.Error())
		}
		data, e := g.query(p.Name, p.Arguments)
		if e != nil {
			return failure(-32602, e.Error())
		}
		b, e := json.Marshal(data)
		if e != nil {
			return failure(-32603, e.Error())
		}
		result = obj{"content": []obj{{"type": "text", "text": string(b)}}}
	default:
		return failure(-32601, "Method not found")
	}
	return obj{"jsonrpc": "2.0", "id": r.ID, "result": result}
}
func (g *Graph) serve(in io.Reader, out io.Writer) error {
	s := bufio.NewScanner(in)
	s.Buffer(make([]byte, 65536), 4<<20)
	enc := json.NewEncoder(out)
	for s.Scan() {
		if v := g.reply(s.Bytes()); v != nil {
			if e := enc.Encode(v); e != nil {
				return e
			}
		}
	}
	return s.Err()
}
func main() {
	dir := flag.String("data", "data/kaggle", "directory containing six CSV files")
	flag.Parse()
	g, e := Load(*dir)
	if e == nil {
		e = g.serve(os.Stdin, os.Stdout)
	}
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
