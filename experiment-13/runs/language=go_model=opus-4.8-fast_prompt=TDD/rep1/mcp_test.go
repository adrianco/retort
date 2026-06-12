// Package main — Brazilian Soccer MCP Server.
//
// mcp_test.go: Tests the MCP JSON-RPC layer — initialize handshake, tools/list
// discovery, tools/call dispatch for every tool, notification handling and
// error responses — plus the human-readable formatting of each tool result.
package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func newServer(t *testing.T) *Server {
	t.Helper()
	return NewServer(testDataset(t))
}

// call is a helper that sends one JSON-RPC request and returns the decoded
// response object (nil if the server produced no response, e.g. notifications).
func call(t *testing.T, s *Server, req string) map[string]any {
	t.Helper()
	out, ok := s.Dispatch([]byte(req))
	if !ok {
		return nil
	}
	var resp map[string]any
	if err := json.Unmarshal(out, &resp); err != nil {
		t.Fatalf("invalid JSON response %q: %v", out, err)
	}
	return resp
}

func TestInitialize(t *testing.T) {
	s := newServer(t)
	resp := call(t, s, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	if resp["jsonrpc"] != "2.0" {
		t.Errorf("missing jsonrpc version: %v", resp)
	}
	result, ok := resp["result"].(map[string]any)
	if !ok {
		t.Fatalf("no result object: %v", resp)
	}
	if _, ok := result["protocolVersion"]; !ok {
		t.Error("initialize result missing protocolVersion")
	}
	info, ok := result["serverInfo"].(map[string]any)
	if !ok || info["name"] == "" {
		t.Errorf("missing serverInfo.name: %v", result)
	}
}

func TestNotificationHasNoResponse(t *testing.T) {
	s := newServer(t)
	out, ok := s.Dispatch([]byte(`{"jsonrpc":"2.0","method":"notifications/initialized"}`))
	if ok {
		t.Errorf("notification should produce no response, got %s", out)
	}
}

func TestToolsList(t *testing.T) {
	s := newServer(t)
	resp := call(t, s, `{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`)
	result := resp["result"].(map[string]any)
	tools, ok := result["tools"].([]any)
	if !ok || len(tools) < 6 {
		t.Fatalf("expected >= 6 tools, got %v", result["tools"])
	}
	// Every tool must have name, description and an object inputSchema.
	names := map[string]bool{}
	for _, raw := range tools {
		tool := raw.(map[string]any)
		name, _ := tool["name"].(string)
		if name == "" {
			t.Error("tool with empty name")
		}
		names[name] = true
		if _, ok := tool["inputSchema"].(map[string]any); !ok {
			t.Errorf("tool %q missing inputSchema object", name)
		}
		if tool["description"] == "" {
			t.Errorf("tool %q missing description", name)
		}
	}
	for _, want := range []string{"search_matches", "team_record", "head_to_head", "standings", "search_players", "competition_stats"} {
		if !names[want] {
			t.Errorf("missing expected tool %q", want)
		}
	}
}

// callTool invokes a tool and returns its concatenated text content.
func callTool(t *testing.T, s *Server, name string, args map[string]any) (string, bool) {
	t.Helper()
	params := map[string]any{"name": name, "arguments": args}
	reqObj := map[string]any{"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": params}
	raw, _ := json.Marshal(reqObj)
	out, ok := s.Dispatch(raw)
	if !ok {
		t.Fatal("tools/call produced no response")
	}
	var resp map[string]any
	if err := json.Unmarshal(out, &resp); err != nil {
		t.Fatalf("bad response: %v", err)
	}
	if errObj, ok := resp["error"].(map[string]any); ok {
		t.Fatalf("unexpected JSON-RPC error: %v", errObj)
	}
	result := resp["result"].(map[string]any)
	isErr, _ := result["isError"].(bool)
	content := result["content"].([]any)
	var sb strings.Builder
	for _, c := range content {
		cm := c.(map[string]any)
		if cm["type"] == "text" {
			sb.WriteString(cm["text"].(string))
		}
	}
	return sb.String(), isErr
}

func TestCallSearchMatches(t *testing.T) {
	s := newServer(t)
	text, isErr := callTool(t, s, "search_matches", map[string]any{
		"team": "Flamengo", "opponent": "Fluminense",
	})
	if isErr {
		t.Fatalf("unexpected error result: %s", text)
	}
	if !strings.Contains(strings.ToLower(text), "flamengo") || !strings.Contains(strings.ToLower(text), "fluminense") {
		t.Errorf("match output missing teams: %s", text)
	}
}

func TestCallStandings(t *testing.T) {
	s := newServer(t)
	text, isErr := callTool(t, s, "standings", map[string]any{
		"competition": "Brasileirão", "season": float64(2019),
	})
	if isErr {
		t.Fatalf("unexpected error: %s", text)
	}
	if !strings.Contains(strings.ToLower(text), "flamengo") || !strings.Contains(text, "90") {
		t.Errorf("standings output wrong: %s", text)
	}
}

func TestCallTeamRecord(t *testing.T) {
	s := newServer(t)
	text, _ := callTool(t, s, "team_record", map[string]any{
		"team": "Flamengo", "season": float64(2019), "source": "Brasileirao",
	})
	if !strings.Contains(text, "28") {
		t.Errorf("team record missing 28 wins: %s", text)
	}
}

func TestCallSearchPlayers(t *testing.T) {
	s := newServer(t)
	text, _ := callTool(t, s, "search_players", map[string]any{
		"nationality": "Brazil", "limit": float64(3),
	})
	if !strings.Contains(text, "Neymar") {
		t.Errorf("expected Neymar among top Brazilians: %s", text)
	}
}

func TestCallCompetitionStats(t *testing.T) {
	s := newServer(t)
	text, _ := callTool(t, s, "competition_stats", map[string]any{
		"source": "Brasileirao", "season": float64(2019),
	})
	low := strings.ToLower(text)
	if !strings.Contains(low, "average") && !strings.Contains(low, "avg") {
		t.Errorf("stats output missing average goals: %s", text)
	}
}

func TestCallHeadToHead(t *testing.T) {
	s := newServer(t)
	text, _ := callTool(t, s, "head_to_head", map[string]any{
		"team_a": "Palmeiras", "team_b": "Santos",
	})
	low := strings.ToLower(text)
	if !strings.Contains(low, "palmeiras") || !strings.Contains(low, "santos") {
		t.Errorf("h2h missing teams: %s", text)
	}
}

func TestCallUnknownToolIsError(t *testing.T) {
	s := newServer(t)
	text, isErr := callTool(t, s, "no_such_tool", map[string]any{})
	if !isErr {
		t.Errorf("expected isError for unknown tool, got: %s", text)
	}
}

func TestMissingRequiredArgIsError(t *testing.T) {
	s := newServer(t)
	// team_record requires a team name.
	text, isErr := callTool(t, s, "team_record", map[string]any{})
	if !isErr {
		t.Errorf("expected error for missing team arg, got: %s", text)
	}
}

func TestUnknownMethodReturnsError(t *testing.T) {
	s := newServer(t)
	resp := call(t, s, `{"jsonrpc":"2.0","id":7,"method":"does/not/exist"}`)
	if _, ok := resp["error"].(map[string]any); !ok {
		t.Errorf("expected JSON-RPC error for unknown method: %v", resp)
	}
}
