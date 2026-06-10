// mcp_test.go - BDD (Given/When/Then) tests for the MCP protocol layer of
// the Brazilian Soccer MCP server.
//
// Context: Drives the JSON-RPC 2.0 stdio server end-to-end - initialize
// handshake, tools/list, tools/call, notifications, and error handling -
// the same way an MCP client (e.g. Claude Desktop) would.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

func testServer(t *testing.T) *MCPServer {
	t.Helper()
	return &MCPServer{
		Name:    "brazilian-soccer-mcp",
		Version: serverVersion,
		Tools:   BuildTools(sharedStore(t)),
	}
}

// roundTrip sends one JSON-RPC message and decodes the response.
func roundTrip(t *testing.T, s *MCPServer, msg string) map[string]any {
	t.Helper()
	resp := s.Handle([]byte(msg))
	if resp == nil {
		t.Fatalf("expected a response for %s", msg)
	}
	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var out map[string]any
	if err := json.Unmarshal(data, &out); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	return out
}

func TestMCPInitializeHandshake(t *testing.T) {
	// Scenario: An MCP client connects and initializes.
	// Given a running server
	s := testServer(t)
	// When the client sends initialize
	out := roundTrip(t, s, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}`)
	// Then the server reports its info and tool capability
	result, _ := out["result"].(map[string]any)
	if result == nil {
		t.Fatalf("no result: %v", out)
	}
	if result["protocolVersion"] != "2024-11-05" {
		t.Errorf("protocolVersion = %v", result["protocolVersion"])
	}
	info, _ := result["serverInfo"].(map[string]any)
	if info == nil || info["name"] != "brazilian-soccer-mcp" {
		t.Errorf("serverInfo = %v", result["serverInfo"])
	}
	caps, _ := result["capabilities"].(map[string]any)
	if caps == nil || caps["tools"] == nil {
		t.Errorf("capabilities = %v", result["capabilities"])
	}
}

func TestMCPToolsList(t *testing.T) {
	// Scenario: The client discovers available tools.
	// Given an initialized server
	s := testServer(t)
	// When tools/list is requested
	out := roundTrip(t, s, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	// Then all eight tools are advertised with schemas
	result, _ := out["result"].(map[string]any)
	tools, _ := result["tools"].([]any)
	if len(tools) != 8 {
		t.Fatalf("expected 8 tools, got %d", len(tools))
	}
	names := map[string]bool{}
	for _, raw := range tools {
		tool := raw.(map[string]any)
		names[tool["name"].(string)] = true
		if tool["inputSchema"] == nil || tool["description"] == "" {
			t.Errorf("tool %v missing schema or description", tool["name"])
		}
	}
	for _, want := range []string{"search_matches", "head_to_head", "team_stats", "league_standings",
		"search_players", "player_info", "competition_stats", "data_summary"} {
		if !names[want] {
			t.Errorf("missing tool %s", want)
		}
	}
}

func TestMCPToolsCall(t *testing.T) {
	// Scenario: The client calls a tool and receives text content.
	// Given an initialized server
	s := testServer(t)
	// When tools/call invokes league_standings for 2019
	out := roundTrip(t, s, `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"league_standings","arguments":{"season":2019}}}`)
	// Then the result carries text content with the champion
	result, _ := out["result"].(map[string]any)
	if result == nil {
		t.Fatalf("no result: %v", out)
	}
	if result["isError"] != false {
		t.Errorf("isError = %v", result["isError"])
	}
	content, _ := result["content"].([]any)
	if len(content) != 1 {
		t.Fatalf("expected 1 content item, got %d", len(content))
	}
	item := content[0].(map[string]any)
	if item["type"] != "text" || !strings.Contains(item["text"].(string), "Flamengo") {
		t.Errorf("unexpected content: %v", item)
	}
}

func TestMCPToolCallErrors(t *testing.T) {
	// Scenario: Bad tool calls produce protocol-conformant errors.
	s := testServer(t)

	// When calling an unknown tool, Then an invalid-params error is returned
	out := roundTrip(t, s, `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"no_such_tool","arguments":{}}}`)
	if out["error"] == nil {
		t.Errorf("expected error for unknown tool, got %v", out)
	}

	// When calling a tool without required args, Then isError content is returned
	out = roundTrip(t, s, `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"player_info","arguments":{}}}`)
	result, _ := out["result"].(map[string]any)
	if result == nil || result["isError"] != true {
		t.Errorf("expected isError result, got %v", out)
	}
}

func TestMCPUnknownMethodAndNotifications(t *testing.T) {
	// Scenario: Unknown methods error; notifications get no response.
	s := testServer(t)

	// When an unknown method is requested, Then -32601 is returned
	out := roundTrip(t, s, `{"jsonrpc":"2.0","id":6,"method":"bogus/method"}`)
	errObj, _ := out["error"].(map[string]any)
	if errObj == nil || errObj["code"].(float64) != -32601 {
		t.Errorf("expected -32601, got %v", out)
	}

	// When a notification arrives, Then no response is sent
	if resp := s.Handle([]byte(`{"jsonrpc":"2.0","method":"notifications/initialized"}`)); resp != nil {
		t.Errorf("expected no response to notification, got %v", resp)
	}

	// When malformed JSON arrives, Then a parse error is returned
	out = roundTrip(t, s, `{not json`)
	errObj, _ = out["error"].(map[string]any)
	if errObj == nil || errObj["code"].(float64) != -32700 {
		t.Errorf("expected -32700, got %v", out)
	}
}

func TestMCPServeOverPipe(t *testing.T) {
	// Scenario: A full client session over the stdio transport.
	// Given a server reading newline-delimited JSON
	s := testServer(t)
	session := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Fluminense","limit":3}}}`,
	}, "\n") + "\n"
	var outBuf strings.Builder
	// When the session is served
	if err := s.Serve(strings.NewReader(session), &outBuf); err != nil {
		t.Fatalf("serve: %v", err)
	}
	// Then exactly the three requests (not the notification) get responses
	var lines []string
	sc := bufio.NewScanner(strings.NewReader(outBuf.String()))
	sc.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	for sc.Scan() {
		if strings.TrimSpace(sc.Text()) != "" {
			lines = append(lines, sc.Text())
		}
	}
	if len(lines) != 3 {
		t.Fatalf("expected 3 responses, got %d: %v", len(lines), lines)
	}
	// And each response is valid JSON-RPC with matching ids
	for i, line := range lines {
		var resp map[string]any
		if err := json.Unmarshal([]byte(line), &resp); err != nil {
			t.Fatalf("response %d not JSON: %v", i, err)
		}
		if resp["jsonrpc"] != "2.0" {
			t.Errorf("response %d missing jsonrpc field", i)
		}
		if fmt.Sprintf("%v", resp["id"]) != fmt.Sprintf("%d", i+1) {
			t.Errorf("response %d has id %v", i, resp["id"])
		}
	}
	// And the tool call answer mentions the derby
	if !strings.Contains(lines[2], "Fla") {
		t.Errorf("tool call response unexpected: %s", lines[2])
	}
}
