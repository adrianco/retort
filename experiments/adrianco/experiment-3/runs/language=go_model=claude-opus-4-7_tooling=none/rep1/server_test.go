// BDD scenarios for the MCP JSON-RPC server: initialize, tools/list,
// tools/call, notifications and error handling.
package main

import (
	"encoding/json"
	"strings"
	"testing"
)

// call builds and dispatches a single JSON-RPC request, returning the response.
func call(t *testing.T, db *DB, id any, method string, params any) *rpcResponse {
	t.Helper()
	req := &rpcRequest{JSONRPC: "2.0", Method: method}
	if id != nil {
		raw, err := json.Marshal(id)
		if err != nil {
			t.Fatalf("marshal id: %v", err)
		}
		req.ID = raw
	}
	if params != nil {
		raw, err := json.Marshal(params)
		if err != nil {
			t.Fatalf("marshal params: %v", err)
		}
		req.Params = raw
	}
	return handleRequest(db, req)
}

// callTool dispatches a tools/call request and returns the rendered text plus
// the isError flag.
func callTool(t *testing.T, db *DB, name string, args map[string]any) (string, bool) {
	t.Helper()
	resp := call(t, db, 1, "tools/call", map[string]any{"name": name, "arguments": args})
	if resp == nil || resp.Result == nil {
		t.Fatalf("tools/call %s returned no result", name)
	}
	result := resp.Result.(map[string]any)
	content := result["content"].([]map[string]any)
	isErr, _ := result["isError"].(bool)
	return content[0]["text"].(string), isErr
}

// Feature: MCP protocol handshake
//
// Scenario: The server responds to initialize with its capabilities.
func TestScenario_Initialize(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When the client sends initialize
	resp := call(t, db, 1, "initialize", map[string]any{"protocolVersion": "2025-06-18"})
	// Then it receives server info and tool capabilities
	if resp == nil || resp.Error != nil {
		t.Fatalf("initialize failed: %+v", resp)
	}
	result := resp.Result.(map[string]any)
	if result["protocolVersion"] != "2025-06-18" {
		t.Errorf("protocol version not echoed: %v", result["protocolVersion"])
	}
	info := result["serverInfo"].(map[string]any)
	if info["name"] != serverName {
		t.Errorf("unexpected server name: %v", info["name"])
	}
}

// Scenario: A notification produces no response.
func TestScenario_NotificationHasNoResponse(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When the client sends the initialized notification (no id)
	resp := call(t, db, nil, "notifications/initialized", nil)
	// Then there is no response
	if resp != nil {
		t.Errorf("expected no response to a notification, got %+v", resp)
	}
}

// Feature: Tool discovery
//
// Scenario: tools/list advertises every soccer tool.
func TestScenario_ToolsList(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When the client lists the tools
	resp := call(t, db, 2, "tools/list", nil)
	// Then all seven tools are advertised with input schemas
	result := resp.Result.(map[string]any)
	tools := result["tools"].([]map[string]any)
	if len(tools) != 7 {
		t.Fatalf("expected 7 tools, got %d", len(tools))
	}
	want := map[string]bool{
		"find_matches": true, "head_to_head": true, "team_stats": true,
		"competition_standings": true, "match_statistics": true,
		"search_players": true, "list_competitions": true,
	}
	for _, tool := range tools {
		name := tool["name"].(string)
		if !want[name] {
			t.Errorf("unexpected tool advertised: %s", name)
		}
		if tool["inputSchema"] == nil {
			t.Errorf("tool %s has no input schema", name)
		}
	}
}

// Feature: Tool invocation
//
// Scenario: find_matches answers a derby question.
func TestScenario_ToolFindMatches(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When find_matches is called for the Fla-Flu derby
	text, isErr := callTool(t, db, "find_matches", map[string]any{
		"team": "Flamengo", "opponent": "Fluminense",
	})
	// Then the answer lists matches and a head-to-head summary
	if isErr {
		t.Fatalf("find_matches reported an error: %s", text)
	}
	if !strings.Contains(text, "Flamengo") || !strings.Contains(text, "Fluminense") {
		t.Errorf("answer does not mention both teams: %s", text)
	}
	if !strings.Contains(text, "Head-to-head") {
		t.Errorf("expected a head-to-head summary in: %s", text)
	}
}

// Scenario: competition_standings reports the champion.
func TestScenario_ToolStandings(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When the 2019 Brasileirão standings are requested
	text, isErr := callTool(t, db, "competition_standings", map[string]any{
		"competition": "Brasileirão", "season": 2019,
	})
	// Then Flamengo is named champion
	if isErr {
		t.Fatalf("competition_standings reported an error: %s", text)
	}
	if !strings.Contains(text, "Champion: Flamengo") {
		t.Errorf("expected Flamengo as champion in: %s", text)
	}
}

// Scenario: search_players finds Brazilian players.
func TestScenario_ToolSearchPlayers(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When Brazilian players are searched
	text, isErr := callTool(t, db, "search_players", map[string]any{
		"nationality": "Brazil", "limit": 5,
	})
	// Then a non-empty, well-formed answer is returned
	if isErr {
		t.Fatalf("search_players reported an error: %s", text)
	}
	if !strings.Contains(text, "player(s) from Brazil") {
		t.Errorf("unexpected search_players answer: %s", text)
	}
}

// Scenario: A required argument is missing.
func TestScenario_ToolMissingRequiredArgument(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When team_stats is called without the required team argument
	text, isErr := callTool(t, db, "team_stats", map[string]any{})
	// Then the tool reports an error
	if !isErr {
		t.Errorf("expected an error for missing 'team', got: %s", text)
	}
}

// Feature: Error handling
//
// Scenario: An unknown tool is rejected.
func TestScenario_UnknownTool(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When an unknown tool is called
	text, isErr := callTool(t, db, "fly_to_the_moon", map[string]any{})
	// Then the call is flagged as an error
	if !isErr || !strings.Contains(text, "unknown tool") {
		t.Errorf("expected unknown-tool error, got isErr=%v text=%q", isErr, text)
	}
}

// Scenario: An unknown method returns a JSON-RPC error.
func TestScenario_UnknownMethod(t *testing.T) {
	// Given a loaded server
	db := testDB(t)
	// When an unknown method is requested
	resp := call(t, db, 9, "does/not/exist", nil)
	// Then a JSON-RPC "method not found" error is returned
	if resp == nil || resp.Error == nil {
		t.Fatalf("expected an error response, got %+v", resp)
	}
	if resp.Error.Code != -32601 {
		t.Errorf("expected code -32601, got %d", resp.Error.Code)
	}
}

// Scenario: The server processes a full newline-delimited session.
func TestScenario_EndToEndSession(t *testing.T) {
	// Given a loaded server and a sequence of JSON-RPC messages
	db := testDB(t)
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize"}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_competitions","arguments":{}}}`,
	}, "\n") + "\n"

	// When the session is served over stdio
	var out strings.Builder
	if err := serve(db, strings.NewReader(input), &out); err != nil {
		t.Fatalf("serve failed: %v", err)
	}

	// Then exactly two responses are emitted (the notification is silent)
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("expected 2 response lines, got %d: %q", len(lines), out.String())
	}
	// And each response is valid JSON-RPC
	for _, line := range lines {
		var resp rpcResponse
		if err := json.Unmarshal([]byte(line), &resp); err != nil {
			t.Errorf("invalid JSON-RPC response: %v", err)
		}
		if resp.JSONRPC != "2.0" {
			t.Errorf("missing jsonrpc version in %q", line)
		}
	}
}
