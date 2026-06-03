// Context: Behaviour-Driven tests for the MCP JSON-RPC layer. They drive the
// server through a real stdin/stdout round-trip (newline-delimited JSON-RPC) to
// confirm the lifecycle handshake and every tool respond correctly.
package mcpserver

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/soccer"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := soccer.LoadStore("../../data/kaggle")
	if err != nil {
		t.Fatalf("loading data: %v", err)
	}
	if len(store.Matches) == 0 {
		t.Fatal("no matches loaded")
	}
	return NewServer(store)
}

// roundTrip feeds the given JSON-RPC request lines through Serve and returns the
// decoded responses in order.
func roundTrip(t *testing.T, s *Server, requests ...any) []rpcResponse {
	t.Helper()
	var in bytes.Buffer
	for _, r := range requests {
		b, err := json.Marshal(r)
		if err != nil {
			t.Fatalf("marshal request: %v", err)
		}
		in.Write(b)
		in.WriteByte('\n')
	}
	var out bytes.Buffer
	if err := s.Serve(&in, &out); err != nil {
		t.Fatalf("serve: %v", err)
	}
	var resps []rpcResponse
	for _, line := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if line == "" {
			continue
		}
		var r rpcResponse
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			t.Fatalf("unmarshal response %q: %v", line, err)
		}
		resps = append(resps, r)
	}
	return resps
}

// callText extracts the text content from a tools/call response.
func callText(t *testing.T, resp rpcResponse) string {
	t.Helper()
	b, err := json.Marshal(resp.Result)
	if err != nil {
		t.Fatalf("marshal result: %v", err)
	}
	var r callToolResult
	if err := json.Unmarshal(b, &r); err != nil {
		t.Fatalf("decode call result: %v", err)
	}
	if len(r.Content) == 0 {
		t.Fatal("empty tool content")
	}
	if r.IsError {
		t.Fatalf("tool returned error: %s", r.Content[0].Text)
	}
	return r.Content[0].Text
}

// Feature: MCP lifecycle.
func TestScenario_InitializeHandshake(t *testing.T) {
	s := newTestServer(t)
	// When the client initializes
	resps := roundTrip(t, s, map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "initialize",
		"params": map[string]any{"protocolVersion": protocolVersion},
	})
	// Then a single result with server info is returned
	if len(resps) != 1 || resps[0].Error != nil {
		t.Fatalf("unexpected initialize response: %+v", resps)
	}
	b, _ := json.Marshal(resps[0].Result)
	if !strings.Contains(string(b), "brazilian-soccer-mcp") {
		t.Errorf("initialize result missing server name: %s", b)
	}
}

// Feature: tools/list advertises every tool with a schema.
func TestScenario_ToolsList(t *testing.T) {
	s := newTestServer(t)
	resps := roundTrip(t, s, map[string]any{"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
	b, _ := json.Marshal(resps[0].Result)
	var res toolsListResult
	if err := json.Unmarshal(b, &res); err != nil {
		t.Fatalf("decode tools/list: %v", err)
	}
	if len(res.Tools) < 8 {
		t.Errorf("expected >=8 tools, got %d", len(res.Tools))
	}
	for _, tl := range res.Tools {
		if tl.Name == "" || tl.Description == "" || tl.InputSchema == nil {
			t.Errorf("tool advertised incompletely: %+v", tl)
		}
	}
}

// Feature: a notification produces no response.
func TestScenario_NotificationNoResponse(t *testing.T) {
	s := newTestServer(t)
	resps := roundTrip(t, s, map[string]any{"jsonrpc": "2.0", "method": "notifications/initialized"})
	if len(resps) != 0 {
		t.Errorf("notification should produce no response, got %+v", resps)
	}
}

// Feature: tools/call — search_players returns Brazilian players.
func TestScenario_CallSearchPlayers(t *testing.T) {
	s := newTestServer(t)
	resps := roundTrip(t, s, map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{
			"name":      "search_players",
			"arguments": map[string]any{"nationality": "Brazil", "limit": 3},
		},
	})
	text := callText(t, resps[0])
	if !strings.Contains(text, "Neymar") {
		t.Errorf("expected Neymar in top Brazilian players, got:\n%s", text)
	}
}

// Feature: tools/call — standings reproduces the 2019 champion.
func TestScenario_CallStandings(t *testing.T) {
	s := newTestServer(t)
	resps := roundTrip(t, s, map[string]any{
		"jsonrpc": "2.0", "id": 7, "method": "tools/call",
		"params": map[string]any{
			"name":      "standings",
			"arguments": map[string]any{"season": 2019, "limit": 1},
		},
	})
	text := callText(t, resps[0])
	if !strings.Contains(text, "Flamengo") || !strings.Contains(text, "90 pts") {
		t.Errorf("expected Flamengo 90 pts champion, got:\n%s", text)
	}
}

// Feature: tools/call — numeric args may arrive as strings.
func TestScenario_CallWithStringNumbers(t *testing.T) {
	s := newTestServer(t)
	resps := roundTrip(t, s, map[string]any{
		"jsonrpc": "2.0", "id": 2, "method": "tools/call",
		"params": map[string]any{
			"name":      "search_matches",
			"arguments": map[string]any{"team": "Flamengo", "opponent": "Fluminense", "season": "2019"},
		},
	})
	text := callText(t, resps[0])
	if strings.Contains(text, "No matches") {
		t.Errorf("expected Fla-Flu 2019 matches, got:\n%s", text)
	}
}

// Feature: error handling — unknown tool yields a JSON-RPC method-not-found.
func TestScenario_UnknownToolErrors(t *testing.T) {
	s := newTestServer(t)
	resps := roundTrip(t, s, map[string]any{
		"jsonrpc": "2.0", "id": 9, "method": "tools/call",
		"params": map[string]any{"name": "does_not_exist", "arguments": map[string]any{}},
	})
	if resps[0].Error == nil {
		t.Error("expected an error for unknown tool")
	}
}

// Feature: error handling — a tool missing a required arg returns isError.
func TestScenario_MissingRequiredArg(t *testing.T) {
	s := newTestServer(t)
	resps := roundTrip(t, s, map[string]any{
		"jsonrpc": "2.0", "id": 10, "method": "tools/call",
		"params": map[string]any{"name": "team_record", "arguments": map[string]any{}},
	})
	b, _ := json.Marshal(resps[0].Result)
	var r callToolResult
	json.Unmarshal(b, &r)
	if !r.IsError {
		t.Errorf("expected isError for missing 'team', got %+v", r)
	}
}
