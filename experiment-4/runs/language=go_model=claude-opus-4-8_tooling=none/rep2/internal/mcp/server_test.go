// Context:
//   - Project: Brazilian Soccer MCP Server (see TASK.md).
//   - Role of this file: BDD end-to-end tests for the MCP JSON-RPC layer. They
//     drive the server exactly as an MCP client would — feeding newline-framed
//     JSON-RPC requests on the input stream and asserting on the responses —
//     covering the initialize handshake, tools/list discovery, and tools/call
//     execution against a small synthetic dataset.
package mcp

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/query"
)

func testEngine() *query.Engine {
	const A = data.CompSerieA
	mk := func(season int, home, away string, hg, ag int) data.Match {
		return data.Match{
			Competition: A, Season: season, HasDate: true,
			HomeRaw: home, AwayRaw: away,
			HomeTeam: data.DisplayTeam(home), AwayTeam: data.DisplayTeam(away),
			HomeGoal: hg, AwayGoal: ag, Source: "synthetic",
		}
	}
	db := &data.Database{
		Matches: []data.Match{
			mk(2023, "Flamengo-RJ", "Fluminense-RJ", 2, 1),
			mk(2023, "Fluminense-RJ", "Flamengo-RJ", 0, 1),
		},
		Players: []data.Player{
			{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Position: "LW", Club: "PSG"},
		},
	}
	return query.New(db)
}

// runRequests feeds the given JSON-RPC request lines through a fresh server and
// returns the decoded responses, in order.
func runRequests(t *testing.T, lines ...string) []Response {
	t.Helper()
	in := bytes.NewBufferString(strings.Join(lines, "\n") + "\n")
	var out bytes.Buffer
	srv := NewServer(in, &out, nil)
	NewSoccerServer(testEngine(), srv)
	if err := srv.Serve(); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resps []Response
	dec := json.NewDecoder(&out)
	for dec.More() {
		var r Response
		if err := dec.Decode(&r); err != nil {
			t.Fatalf("decode response: %v", err)
		}
		resps = append(resps, r)
	}
	return resps
}

// resultMap re-decodes a response's result into a generic map.
func resultMap(t *testing.T, r Response) map[string]any {
	t.Helper()
	b, err := json.Marshal(r.Result)
	if err != nil {
		t.Fatalf("marshal result: %v", err)
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	return m
}

// toolText extracts the text from a tools/call result.
func toolText(t *testing.T, r Response) string {
	t.Helper()
	m := resultMap(t, r)
	content, ok := m["content"].([]any)
	if !ok || len(content) == 0 {
		t.Fatalf("no content in tool result: %v", m)
	}
	first := content[0].(map[string]any)
	return first["text"].(string)
}

func TestInitialize_Handshake(t *testing.T) {
	// Feature: MCP lifecycle
	// Scenario: A client initializes the server
	// Given an initialize request
	// When the server responds
	resps := runRequests(t, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	if len(resps) != 1 {
		t.Fatalf("got %d responses; want 1", len(resps))
	}
	m := resultMap(t, resps[0])
	// Then it advertises a protocol version and server info
	if m["protocolVersion"] != protocolVersion {
		t.Fatalf("protocolVersion = %v; want %s", m["protocolVersion"], protocolVersion)
	}
	info, _ := m["serverInfo"].(map[string]any)
	if info == nil || info["name"] == "" {
		t.Fatalf("missing serverInfo: %v", m)
	}
}

func TestNotification_NoResponse(t *testing.T) {
	// Scenario: A notification (no id) produces no response
	resps := runRequests(t, `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
	if len(resps) != 0 {
		t.Fatalf("notification produced %d responses; want 0", len(resps))
	}
}

func TestToolsList_ExposesAllTools(t *testing.T) {
	// Feature: Tool discovery
	// Scenario: A client lists available tools
	resps := runRequests(t, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	m := resultMap(t, resps[0])
	tools, ok := m["tools"].([]any)
	if !ok {
		t.Fatalf("tools not a list: %v", m)
	}
	// Then every required capability is represented.
	want := map[string]bool{
		"search_matches": false, "head_to_head": false, "team_stats": false,
		"standings": false, "competition_stats": false, "search_players": false,
		"list_competitions": false,
	}
	for _, tn := range tools {
		tm := tn.(map[string]any)
		name, _ := tm["name"].(string)
		if _, exists := want[name]; exists {
			want[name] = true
		}
		// And each tool publishes an input schema.
		if _, ok := tm["inputSchema"]; !ok {
			t.Fatalf("tool %q missing inputSchema", name)
		}
	}
	for name, seen := range want {
		if !seen {
			t.Fatalf("tool %q not advertised", name)
		}
	}
}

func TestToolsCall_HeadToHead(t *testing.T) {
	// Feature: Match Queries over MCP
	// Scenario: Calling head_to_head returns a formatted record
	req := `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}`
	resps := runRequests(t, req)
	text := toolText(t, resps[0])
	if !strings.Contains(text, "Flamengo") || !strings.Contains(text, "Fluminense") {
		t.Fatalf("unexpected h2h text: %q", text)
	}
	// Flamengo won both synthetic meetings.
	if !strings.Contains(text, "Flamengo 2 wins") {
		t.Fatalf("h2h text missing record: %q", text)
	}
}

func TestToolsCall_SearchPlayers(t *testing.T) {
	// Scenario: Calling search_players returns matching players
	req := `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_players","arguments":{"nationality":"Brazil"}}}`
	resps := runRequests(t, req)
	text := toolText(t, resps[0])
	if !strings.Contains(text, "Neymar Jr") {
		t.Fatalf("search_players text missing player: %q", text)
	}
}

func TestToolsCall_MissingRequiredArg(t *testing.T) {
	// Scenario: A tool reports a usage error as an error result
	req := `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo"}}}`
	resps := runRequests(t, req)
	m := resultMap(t, resps[0])
	if isErr, _ := m["isError"].(bool); !isErr {
		t.Fatalf("expected isError=true for missing arg, got %v", m)
	}
}

func TestToolsCall_UnknownTool(t *testing.T) {
	// Scenario: Calling an unknown tool yields a JSON-RPC error
	req := `{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"does_not_exist","arguments":{}}}`
	resps := runRequests(t, req)
	if resps[0].Error == nil {
		t.Fatalf("expected error for unknown tool, got %+v", resps[0])
	}
}

func TestUnknownMethod_ReturnsError(t *testing.T) {
	// Scenario: An unknown method id-request returns method-not-found
	resps := runRequests(t, `{"jsonrpc":"2.0","id":7,"method":"no/such/method"}`)
	if resps[0].Error == nil || resps[0].Error.Code != codeMethodNotFound {
		t.Fatalf("expected method-not-found error, got %+v", resps[0])
	}
}
