package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// Feature: MCP JSON-RPC protocol — initialize, tools/list, tools/call.

type rpcRespCheck struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  json.RawMessage `json:"result"`
	Error   *rpcError       `json:"error"`
}

func runMCP(t *testing.T, store *DataStore, input string) []rpcRespCheck {
	t.Helper()
	srv := NewMCPServer(store)
	var out bytes.Buffer
	if err := srv.Serve(strings.NewReader(input), &out); err != nil {
		t.Fatalf("serve: %v", err)
	}
	var responses []rpcRespCheck
	for _, line := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if line == "" {
			continue
		}
		var r rpcRespCheck
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			t.Fatalf("unmarshal %q: %v", line, err)
		}
		responses = append(responses, r)
	}
	return responses
}

func TestMCP_Initialize(t *testing.T) {
	ds := miniStore()
	out := runMCP(t, ds, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`+"\n")
	if len(out) != 1 {
		t.Fatalf("expected 1 response, got %d", len(out))
	}
	if out[0].Error != nil {
		t.Fatalf("init error: %v", out[0].Error)
	}
	if !strings.Contains(string(out[0].Result), "protocolVersion") {
		t.Errorf("missing protocolVersion in %s", out[0].Result)
	}
}

func TestMCP_ToolsList(t *testing.T) {
	ds := miniStore()
	out := runMCP(t, ds, `{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`+"\n")
	if out[0].Error != nil {
		t.Fatalf("error: %v", out[0].Error)
	}
	var res struct {
		Tools []toolDef `json:"tools"`
	}
	if err := json.Unmarshal(out[0].Result, &res); err != nil {
		t.Fatalf("unmarshal tools: %v", err)
	}
	want := map[string]bool{
		"find_matches": true, "team_stats": true, "head_to_head": true,
		"standings": true, "find_players": true, "aggregate_stats": true, "biggest_wins": true,
	}
	for _, tool := range res.Tools {
		delete(want, tool.Name)
	}
	if len(want) > 0 {
		t.Errorf("missing tools: %v", want)
	}
}

func TestMCP_ToolCall_FindMatches(t *testing.T) {
	ds := miniStore()
	in := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"find_matches","arguments":{"team1":"Flamengo","team2":"Fluminense"}}}` + "\n"
	out := runMCP(t, ds, in)
	if out[0].Error != nil {
		t.Fatalf("error: %v", out[0].Error)
	}
	var res toolResult
	if err := json.Unmarshal(out[0].Result, &res); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if res.IsError {
		t.Errorf("got IsError, content=%v", res.Content)
	}
	if !strings.Contains(res.Content[0].Text, "Flamengo") {
		t.Errorf("expected Flamengo in output, got: %s", res.Content[0].Text)
	}
}

func TestMCP_ToolCall_MissingRequired(t *testing.T) {
	ds := miniStore()
	in := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"team_stats","arguments":{}}}` + "\n"
	out := runMCP(t, ds, in)
	var res toolResult
	_ = json.Unmarshal(out[0].Result, &res)
	if !res.IsError {
		t.Errorf("expected IsError for missing 'team', got %v", res)
	}
}

func TestMCP_UnknownMethod(t *testing.T) {
	ds := miniStore()
	in := `{"jsonrpc":"2.0","id":1,"method":"does/not/exist"}` + "\n"
	out := runMCP(t, ds, in)
	if out[0].Error == nil {
		t.Errorf("expected error, got result %s", out[0].Result)
	}
	if out[0].Error.Code != -32601 {
		t.Errorf("code %d, want -32601", out[0].Error.Code)
	}
}
