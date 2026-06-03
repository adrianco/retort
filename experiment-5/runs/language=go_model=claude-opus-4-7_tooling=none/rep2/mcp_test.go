package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// fixtureDataset returns a small hand-built dataset for protocol-level tests
// that should not depend on the full CSVs being present.
func fixtureDataset() *Dataset {
	return &Dataset{
		Matches: []Match{
			{Source: "test", Competition: "Brasileirão Série A", Season: 2019,
				HomeTeam: "Flamengo-RJ", AwayTeam: "Fluminense-RJ", HomeGoals: 2, AwayGoals: 1},
			{Source: "test", Competition: "Brasileirão Série A", Season: 2019,
				HomeTeam: "Fluminense-RJ", AwayTeam: "Flamengo-RJ", HomeGoals: 0, AwayGoals: 3},
			{Source: "test", Competition: "Copa do Brasil", Season: 2019,
				HomeTeam: "Palmeiras-SP", AwayTeam: "Santos-SP", HomeGoals: 2, AwayGoals: 0},
		},
		Players: []Player{
			{ID: 1, Name: "Gabriel Barbosa", Nationality: "Brazil", Club: "Flamengo", Overall: 84, Position: "ST", Age: 25},
			{ID: 2, Name: "Neymar Jr", Nationality: "Brazil", Club: "Paris Saint-Germain", Overall: 92, Position: "LW", Age: 29},
		},
	}
}

// runRequest serialises a JSON-RPC request, runs it through the server, and
// returns the response.
func runRequest(t *testing.T, srv *Server, method string, params any, id int) jsonrpcResponse {
	t.Helper()
	paramsJSON, err := json.Marshal(params)
	if err != nil {
		t.Fatalf("marshal params: %v", err)
	}
	idJSON, _ := json.Marshal(id)
	req := jsonrpcRequest{
		JSONRPC: "2.0",
		ID:      idJSON,
		Method:  method,
		Params:  paramsJSON,
	}
	reqLine, _ := json.Marshal(req)
	reqLine = append(reqLine, '\n')

	var out bytes.Buffer
	if err := srv.Serve(bytes.NewReader(reqLine), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resp jsonrpcResponse
	dec := json.NewDecoder(&out)
	if err := dec.Decode(&resp); err != nil {
		t.Fatalf("decode resp (%q): %v", out.String(), err)
	}
	return resp
}

// Feature: MCP Protocol
// Scenario: Initialize handshake exposes the server.
func TestMCP_Initialize(t *testing.T) {
	srv := NewServer(fixtureDataset())
	resp := runRequest(t, srv, "initialize", map[string]any{"protocolVersion": mcpProtocolVersion}, 1)
	if resp.Error != nil {
		t.Fatalf("unexpected error: %+v", resp.Error)
	}
	m, ok := resp.Result.(map[string]any)
	if !ok {
		t.Fatalf("result not a map: %T", resp.Result)
	}
	if got, _ := m["protocolVersion"].(string); got != mcpProtocolVersion {
		t.Errorf("protocolVersion = %q", got)
	}
}

// Scenario: tools/list returns every registered tool.
func TestMCP_ListTools(t *testing.T) {
	srv := NewServer(fixtureDataset())
	resp := runRequest(t, srv, "tools/list", map[string]any{}, 2)
	if resp.Error != nil {
		t.Fatalf("unexpected error: %+v", resp.Error)
	}
	m := resp.Result.(map[string]any)
	tools, _ := m["tools"].([]any)
	if len(tools) < 6 {
		t.Errorf("expected at least 6 tools, got %d", len(tools))
	}
	names := map[string]bool{}
	for _, raw := range tools {
		tm := raw.(map[string]any)
		names[tm["name"].(string)] = true
	}
	for _, want := range []string{
		"search_matches", "team_stats", "head_to_head",
		"standings", "search_players", "biggest_wins",
		"competition_summary", "dataset_info",
	} {
		if !names[want] {
			t.Errorf("missing tool: %s", want)
		}
	}
}

// Scenario: Calling search_matches returns text content.
func TestMCP_CallSearchMatches(t *testing.T) {
	srv := NewServer(fixtureDataset())
	resp := runRequest(t, srv, "tools/call", map[string]any{
		"name": "search_matches",
		"arguments": map[string]any{
			"team":     "Flamengo",
			"opponent": "Fluminense",
		},
	}, 3)
	if resp.Error != nil {
		t.Fatalf("unexpected error: %+v", resp.Error)
	}
	m := resp.Result.(map[string]any)
	content := m["content"].([]any)
	if len(content) == 0 {
		t.Fatal("expected content")
	}
	text := content[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "Flamengo") || !strings.Contains(text, "Fluminense") {
		t.Errorf("unexpected text: %s", text)
	}
}

// Scenario: Calling search_players filters by nationality.
func TestMCP_CallSearchPlayers(t *testing.T) {
	srv := NewServer(fixtureDataset())
	resp := runRequest(t, srv, "tools/call", map[string]any{
		"name": "search_players",
		"arguments": map[string]any{
			"nationality": "Brazil",
			"limit":       float64(2),
		},
	}, 4)
	m := resp.Result.(map[string]any)
	text := m["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "Neymar") {
		t.Errorf("expected Neymar, got: %s", text)
	}
}

// Scenario: Calling an unknown tool returns an error response.
func TestMCP_UnknownTool(t *testing.T) {
	srv := NewServer(fixtureDataset())
	resp := runRequest(t, srv, "tools/call", map[string]any{
		"name":      "nonexistent_tool",
		"arguments": map[string]any{},
	}, 5)
	if resp.Error == nil {
		t.Fatalf("expected error, got result %+v", resp.Result)
	}
}

// Scenario: Head-to-head tool computes a record from fixture data.
func TestMCP_HeadToHead(t *testing.T) {
	srv := NewServer(fixtureDataset())
	resp := runRequest(t, srv, "tools/call", map[string]any{
		"name": "head_to_head",
		"arguments": map[string]any{
			"team_a": "Flamengo",
			"team_b": "Fluminense",
		},
	}, 6)
	m := resp.Result.(map[string]any)
	text := m["content"].([]any)[0].(map[string]any)["text"].(string)
	// Both fixture matches are won by Flamengo (2-1 and 0-3 as visitor).
	if !strings.Contains(text, "Flamengo wins: 2") {
		t.Errorf("expected Flamengo wins: 2, got: %s", text)
	}
}

// Scenario: Standings tool reflects fixture data.
func TestMCP_Standings(t *testing.T) {
	srv := NewServer(fixtureDataset())
	resp := runRequest(t, srv, "tools/call", map[string]any{
		"name": "standings",
		"arguments": map[string]any{
			"season":      float64(2019),
			"competition": "Brasileirão",
		},
	}, 7)
	m := resp.Result.(map[string]any)
	text := m["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "Flamengo") {
		t.Errorf("expected Flamengo in standings, got: %s", text)
	}
}
