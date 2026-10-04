package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"io"
	"strings"
	"testing"
	"time"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	return NewServer(loadTestStore(t), nil)
}

// roundTrip sends newline-delimited requests through Serve and returns the
// decoded responses.
func roundTrip(t *testing.T, srv *Server, requests ...string) []map[string]any {
	t.Helper()
	var out bytes.Buffer
	if err := srv.Serve(strings.NewReader(strings.Join(requests, "\n")+"\n"), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resps []map[string]any
	sc := bufio.NewScanner(&out)
	sc.Buffer(make([]byte, 0, 1<<20), 16<<20)
	for sc.Scan() {
		var m map[string]any
		if err := json.Unmarshal(sc.Bytes(), &m); err != nil {
			t.Fatalf("invalid JSON response %q: %v", sc.Text(), err)
		}
		resps = append(resps, m)
	}
	return resps
}

func TestMCPHandshakeAndToolsList(t *testing.T) {
	srv := newTestServer(t)
	resps := roundTrip(t, srv,
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"ping"}`,
	)
	if len(resps) != 3 {
		t.Fatalf("got %d responses, want 3 (notification must not be answered): %v", len(resps), resps)
	}
	init := resps[0]["result"].(map[string]any)
	if init["protocolVersion"] != "2025-03-26" {
		t.Errorf("protocolVersion = %v", init["protocolVersion"])
	}
	if init["serverInfo"].(map[string]any)["name"] != serverName {
		t.Errorf("serverInfo = %v", init["serverInfo"])
	}
	if _, ok := init["capabilities"].(map[string]any)["tools"]; !ok {
		t.Error("tools capability missing")
	}
	tools := resps[1]["result"].(map[string]any)["tools"].([]any)
	if len(tools) != len(Tools()) || len(tools) < 10 {
		t.Fatalf("tools/list returned %d tools", len(tools))
	}
	names := map[string]bool{}
	for _, raw := range tools {
		tool := raw.(map[string]any)
		names[tool["name"].(string)] = true
		schema, ok := tool["inputSchema"].(map[string]any)
		if !ok || schema["type"] != "object" {
			t.Errorf("tool %v has invalid inputSchema", tool["name"])
		}
		if desc, _ := tool["description"].(string); len(desc) < 20 {
			t.Errorf("tool %v lacks a description", tool["name"])
		}
	}
	for _, want := range []string{"search_matches", "head_to_head", "team_record", "standings", "search_players", "get_player", "league_stats", "biggest_wins"} {
		if !names[want] {
			t.Errorf("tool %s missing", want)
		}
	}
	if resps[2]["id"].(float64) != 3 {
		t.Errorf("ping id = %v", resps[2]["id"])
	}
}

func TestMCPUnknownProtocolVersionFallsBack(t *testing.T) {
	resps := roundTrip(t, newTestServer(t), `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"1999-01-01"}}`)
	if v := resps[0]["result"].(map[string]any)["protocolVersion"]; v != protocolVersion {
		t.Errorf("protocolVersion = %v, want %s", v, protocolVersion)
	}
}

func toolText(t *testing.T, resp map[string]any) (string, bool) {
	t.Helper()
	res, ok := resp["result"].(map[string]any)
	if !ok {
		t.Fatalf("no result in %v", resp)
	}
	content := res["content"].([]any)
	first := content[0].(map[string]any)
	if first["type"] != "text" {
		t.Fatalf("content type = %v", first["type"])
	}
	return first["text"].(string), res["isError"].(bool)
}

func TestMCPToolsCall(t *testing.T) {
	srv := newTestServer(t)
	resps := roundTrip(t, srv,
		`{"jsonrpc":"2.0","id":"a","method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"top":3}}}`,
		`{"jsonrpc":"2.0","id":"b","method":"tools/call","params":{"name":"standings","arguments":{"season":"2019"}}}`,
		`{"jsonrpc":"2.0","id":"c","method":"tools/call","params":{"name":"team_record","arguments":{"team":"Time Inexistente FC"}}}`,
		`{"jsonrpc":"2.0","id":"d","method":"tools/call","params":{"name":"no_such_tool","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":"e","method":"tools/call","params":{"name":"standings","arguments":{"season":"abc"}}}`,
	)
	if len(resps) != 5 {
		t.Fatalf("got %d responses", len(resps))
	}
	text, isErr := toolText(t, resps[0])
	if isErr || !strings.Contains(text, "1. Flamengo - 90 pts (28W, 6D, 4L)") {
		t.Errorf("standings result: %s", text)
	}
	if text, isErr := toolText(t, resps[1]); isErr || !strings.Contains(text, "Flamengo") {
		t.Errorf("season as string should work: %s", text)
	}
	if text, isErr := toolText(t, resps[2]); !isErr || !strings.Contains(text, "not found") {
		t.Errorf("unknown team should be a tool error: %s", text)
	}
	if resps[3]["error"].(map[string]any)["code"].(float64) != codeInvalidParams {
		t.Errorf("unknown tool should be a protocol error: %v", resps[3])
	}
	if _, isErr := toolText(t, resps[4]); !isErr {
		t.Error("invalid integer should be a tool error")
	}
	if resps[0]["id"] != "a" || resps[4]["id"] != "e" {
		t.Error("response ids must echo request ids")
	}
}

func TestMCPErrorsAndBatch(t *testing.T) {
	srv := newTestServer(t)
	resps := roundTrip(t, srv,
		`{not json`,
		`{"jsonrpc":"2.0","id":7,"method":"does/not/exist"}`,
	)
	if len(resps) != 2 {
		t.Fatalf("got %d responses: %v", len(resps), resps)
	}
	if resps[0]["error"].(map[string]any)["code"].(float64) != codeParseError {
		t.Errorf("parse error expected: %v", resps[0])
	}
	if resps[1]["error"].(map[string]any)["code"].(float64) != codeMethodNotFound {
		t.Errorf("method not found expected: %v", resps[1])
	}
	batch := srv.HandleMessage([]byte(`[{"jsonrpc":"2.0","id":8,"method":"ping"},{"jsonrpc":"2.0","method":"notifications/cancelled"},{"jsonrpc":"2.0","id":9,"method":"tools/list"}]`))
	list, ok := batch.([]rpcResponse)
	if !ok || len(list) != 2 {
		t.Fatalf("batch response = %#v", batch)
	}
}

func TestMCPOverPipes(t *testing.T) {
	// Exercise Serve like a real stdio client: write a request, read the
	// reply before sending the next one.
	srv := newTestServer(t)
	inR, inW := io.Pipe()
	outR, outW := io.Pipe()
	done := make(chan error, 1)
	go func() { done <- srv.Serve(inR, outW); outW.Close() }()
	reader := bufio.NewReader(outR)
	send := func(req string) map[string]any {
		if _, err := io.WriteString(inW, req+"\n"); err != nil {
			t.Fatal(err)
		}
		line, err := reader.ReadBytes('\n')
		if err != nil {
			t.Fatal(err)
		}
		var m map[string]any
		if err := json.Unmarshal(line, &m); err != nil {
			t.Fatal(err)
		}
		return m
	}
	send(`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`)
	resp := send(`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Grêmio","team_b":"Internacional"}}}`)
	text, isErr := toolText(t, resp)
	if isErr || !strings.Contains(text, "Grenal") {
		t.Errorf("head_to_head over pipes: %s", text)
	}
	inW.Close()
	select {
	case err := <-done:
		if err != nil {
			t.Errorf("Serve returned %v", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("Serve did not stop at EOF")
	}
}

func TestEveryToolRunsWithMinimalArguments(t *testing.T) {
	srv := newTestServer(t)
	minimal := map[string]map[string]any{
		"search_matches":   {"team": "Bahia"},
		"head_to_head":     {"team_a": "Bahia", "team_b": "Vitória"},
		"team_record":      {"team": "Bahia"},
		"team_overview":    {"team": "Bahia"},
		"standings":        {"season": 2015},
		"team_rankings":    {"metric": "points"},
		"league_stats":     {},
		"compare_seasons":  {"seasons": "2015-2017"},
		"biggest_wins":     {},
		"knockout_matches": {"competition": "Libertadores"},
		"find_derbies":     {},
		"search_players":   {},
		"get_player":       {"name": "Messi"},
		"club_squads":      {},
		"list_teams":       {},
		"dataset_info":     {},
	}
	for _, tool := range Tools() {
		args, ok := minimal[tool.Name]
		if !ok {
			t.Errorf("no minimal arguments defined for tool %s", tool.Name)
			continue
		}
		start := time.Now()
		text, err := srv.CallTool(tool.Name, args)
		if err != nil {
			t.Errorf("%s(%v): %v", tool.Name, args, err)
			continue
		}
		if strings.TrimSpace(text) == "" {
			t.Errorf("%s returned empty text", tool.Name)
		}
		if d := time.Since(start); d > 2*time.Second {
			t.Errorf("%s took %s", tool.Name, d)
		}
	}
}

func TestToolArgumentValidation(t *testing.T) {
	srv := newTestServer(t)
	bad := []struct {
		tool string
		args map[string]any
	}{
		{"standings", map[string]any{}},
		{"standings", map[string]any{"season": 2019, "competition": "Libertadores"}},
		{"search_matches", map[string]any{"competition": "Premier League"}},
		{"search_matches", map[string]any{"date_from": "not a date"}},
		{"search_matches", map[string]any{"venue": "home"}},
		{"search_matches", map[string]any{"season": 2019.5}},
		{"team_rankings", map[string]any{"metric": "elo"}},
		{"compare_seasons", map[string]any{"seasons": "2019"}},
		{"knockout_matches", map[string]any{"competition": "Serie A"}},
		{"head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Flamengo-RJ"}},
		{"get_player", map[string]any{}},
	}
	for _, c := range bad {
		if _, err := srv.CallTool(c.tool, c.args); err == nil {
			t.Errorf("%s(%v): expected error", c.tool, c.args)
		}
	}
}
