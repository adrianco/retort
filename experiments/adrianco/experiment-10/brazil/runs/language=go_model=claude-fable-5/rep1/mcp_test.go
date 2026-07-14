// mcp_test.go — BDD scenarios for the MCP protocol layer: JSON-RPC framing,
// initialize handshake, tool listing and tool calls over a stdio-style pipe.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	return NewServer(givenTheDataIsLoaded(t))
}

func roundTrip(t *testing.T, srv *Server, msg string) map[string]any {
	t.Helper()
	resp := srv.HandleMessage([]byte(msg))
	if resp == nil {
		return nil
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

func TestScenario_InitializeHandshake(t *testing.T) {
	// Given a running MCP server
	srv := newTestServer(t)

	// When the client sends an initialize request
	out := roundTrip(t, srv,
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}`)

	// Then the server replies with its protocol version and tool capability
	result, _ := out["result"].(map[string]any)
	if result == nil {
		t.Fatalf("no result in initialize response: %v", out)
	}
	if result["protocolVersion"] != "2024-11-05" {
		t.Errorf("protocolVersion = %v, want 2024-11-05", result["protocolVersion"])
	}
	caps, _ := result["capabilities"].(map[string]any)
	if _, ok := caps["tools"]; !ok {
		t.Errorf("missing tools capability: %v", result)
	}
	info, _ := result["serverInfo"].(map[string]any)
	if info["name"] != serverName {
		t.Errorf("serverInfo.name = %v, want %s", info["name"], serverName)
	}

	// And the initialized notification gets no response
	if resp := srv.HandleMessage([]byte(`{"jsonrpc":"2.0","method":"notifications/initialized"}`)); resp != nil {
		t.Errorf("notification got a response: %+v", resp)
	}
}

func TestScenario_ToolsListAdvertisesAllTools(t *testing.T) {
	// Given an initialized server
	srv := newTestServer(t)

	// When the client requests tools/list
	out := roundTrip(t, srv, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)

	// Then all tools are advertised with schemas
	result, _ := out["result"].(map[string]any)
	tools, _ := result["tools"].([]any)
	want := []string{"search_matches", "get_team_stats", "head_to_head", "search_players",
		"get_player_details", "get_standings", "get_competition_stats", "list_competitions"}
	if len(tools) != len(want) {
		t.Fatalf("got %d tools, want %d", len(tools), len(want))
	}
	names := map[string]bool{}
	for _, tl := range tools {
		m := tl.(map[string]any)
		names[m["name"].(string)] = true
		if m["description"] == "" || m["inputSchema"] == nil {
			t.Errorf("tool %v missing description or inputSchema", m["name"])
		}
	}
	for _, w := range want {
		if !names[w] {
			t.Errorf("tool %s not advertised", w)
		}
	}
}

func TestScenario_ToolCallOverProtocol(t *testing.T) {
	// Given an initialized server
	srv := newTestServer(t)

	// When the client calls search_matches for the Fla-Flu derby
	out := roundTrip(t, srv,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Fluminense","limit":5}}}`)

	// Then the result contains text content with match data
	result, _ := out["result"].(map[string]any)
	if result == nil {
		t.Fatalf("no result: %v", out)
	}
	if result["isError"] != false {
		t.Errorf("isError = %v, want false", result["isError"])
	}
	content, _ := result["content"].([]any)
	if len(content) != 1 {
		t.Fatalf("expected one content item, got %v", content)
	}
	item := content[0].(map[string]any)
	if item["type"] != "text" {
		t.Errorf("content type = %v, want text", item["type"])
	}
	text, _ := item["text"].(string)
	if !strings.Contains(text, "Head-to-head") {
		t.Errorf("tool text missing head-to-head summary:\n%s", text)
	}
}

func TestScenario_ToolErrorsAreReportedInBand(t *testing.T) {
	// Given an initialized server
	srv := newTestServer(t)

	// When a tool is called with invalid arguments
	out := roundTrip(t, srv,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_standings","arguments":{}}}`)

	// Then the failure is reported as an in-band tool error, not a protocol error
	if out["error"] != nil {
		t.Fatalf("expected in-band tool error, got protocol error: %v", out["error"])
	}
	result, _ := out["result"].(map[string]any)
	if result["isError"] != true {
		t.Errorf("isError = %v, want true", result["isError"])
	}

	// And calling an unknown tool yields an invalid-params protocol error
	out = roundTrip(t, srv,
		`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"no_such_tool"}}`)
	errObj, _ := out["error"].(map[string]any)
	if errObj == nil {
		t.Fatalf("expected protocol error for unknown tool, got %v", out)
	}

	// And an unknown method yields method-not-found
	out = roundTrip(t, srv, `{"jsonrpc":"2.0","id":6,"method":"bogus/method"}`)
	errObj, _ = out["error"].(map[string]any)
	if errObj == nil || errObj["code"].(float64) != codeMethodNotFound {
		t.Errorf("expected method-not-found, got %v", out)
	}
}

func TestScenario_FullSessionOverPipe(t *testing.T) {
	// Given a server reading newline-delimited JSON-RPC from a stream
	srv := newTestServer(t)
	requests := []string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_standings","arguments":{"season":2019}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"ping"}`,
	}
	in := strings.NewReader(strings.Join(requests, "\n") + "\n")
	var out strings.Builder

	// When the full session is served
	if err := srv.Serve(in, &out); err != nil {
		t.Fatalf("serve: %v", err)
	}

	// Then exactly the four non-notification requests get responses, in order
	var ids []float64
	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	for scanner.Scan() {
		var resp map[string]any
		if err := json.Unmarshal(scanner.Bytes(), &resp); err != nil {
			t.Fatalf("bad response line: %v\n%s", err, scanner.Text())
		}
		if resp["jsonrpc"] != "2.0" {
			t.Errorf("missing jsonrpc field: %v", resp)
		}
		if resp["error"] != nil {
			t.Errorf("unexpected error response: %v", resp)
		}
		ids = append(ids, resp["id"].(float64))
	}
	if fmt.Sprint(ids) != "[1 2 3 4]" {
		t.Errorf("response ids = %v, want [1 2 3 4]", ids)
	}
	// And the standings call returned the 2019 champion
	if !strings.Contains(out.String(), "Flamengo") {
		t.Errorf("expected Flamengo in 2019 standings output")
	}
	// And the negotiated protocol version was echoed
	if !strings.Contains(out.String(), "2025-03-26") {
		t.Errorf("expected echoed protocol version 2025-03-26")
	}
}
