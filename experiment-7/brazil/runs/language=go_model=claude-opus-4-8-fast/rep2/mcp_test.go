// Brazilian Soccer MCP Server
//
// File: mcp_test.go
// Responsibility: Tests for the MCP/JSON-RPC layer and the tool handlers. They
// drive the server the way a real MCP client would — feeding newline-delimited
// JSON-RPC requests through Server.Serve and asserting on the responses — to
// confirm the initialize handshake, tools/list and tools/call all behave, and
// that each tool produces a sensible textual answer.
package main

import (
	"bufio"
	"encoding/json"
	"strings"
	"testing"
)

// runRequests feeds the given JSON-RPC request lines through a server backed by
// the fixture store and returns the decoded responses keyed by id.
func runRequests(t *testing.T, lines ...string) map[float64]jsonrpcResponse {
	t.Helper()
	srv := NewServer("test", "0")
	RegisterTools(srv, fixtureStore())

	in := strings.NewReader(strings.Join(lines, "\n") + "\n")
	var out strings.Builder
	if err := srv.Serve(in, &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}

	resp := map[float64]jsonrpcResponse{}
	sc := bufio.NewScanner(strings.NewReader(out.String()))
	for sc.Scan() {
		line := sc.Bytes()
		if len(line) == 0 {
			continue
		}
		var r jsonrpcResponse
		if err := json.Unmarshal(line, &r); err != nil {
			t.Fatalf("decode response %q: %v", line, err)
		}
		var id float64
		json.Unmarshal(r.ID, &id)
		resp[id] = r
	}
	return resp
}

// callText extracts the text payload of a tools/call response.
func callText(t *testing.T, r jsonrpcResponse) string {
	t.Helper()
	b, _ := json.Marshal(r.Result)
	var res struct {
		Content []struct {
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(b, &res); err != nil {
		t.Fatalf("decode call result: %v", err)
	}
	if len(res.Content) == 0 {
		t.Fatalf("empty content in result: %s", b)
	}
	return res.Content[0].Text
}

// Scenario: the initialize handshake and tool discovery.
func TestInitializeAndList(t *testing.T) {
	// Given a running server
	// When a client initializes and lists tools
	resp := runRequests(t,
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
	)
	// Then initialize reports the protocol version
	b, _ := json.Marshal(resp[1].Result)
	if !strings.Contains(string(b), protocolVersion) {
		t.Errorf("initialize missing protocol version: %s", b)
	}
	// And all seven tools are advertised
	lb, _ := json.Marshal(resp[2].Result)
	for _, name := range []string{"find_matches", "team_stats", "head_to_head",
		"search_players", "standings", "competition_stats", "list_competitions"} {
		if !strings.Contains(string(lb), `"`+name+`"`) {
			t.Errorf("tools/list missing %q", name)
		}
	}
}

// Scenario: notifications receive no response.
func TestNotificationNoResponse(t *testing.T) {
	resp := runRequests(t,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":9,"method":"ping"}`,
	)
	if _, ok := resp[9]; !ok {
		t.Error("ping should have produced a response")
	}
	if len(resp) != 1 {
		t.Errorf("expected exactly 1 response (ping), got %d", len(resp))
	}
}

// Scenario: calling find_matches via the protocol.
func TestToolCallFindMatches(t *testing.T) {
	resp := runRequests(t,
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Flamengo","opponent":"Atletico-MG"}}}`,
	)
	text := callText(t, resp[1])
	if !strings.Contains(text, "Head-to-head") {
		t.Errorf("find_matches with opponent should include head-to-head, got:\n%s", text)
	}
}

// Scenario: a tool reports a usage error as an MCP error result.
func TestToolCallMissingArgs(t *testing.T) {
	resp := runRequests(t,
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"team_stats","arguments":{}}}`,
	)
	text := callText(t, resp[1])
	if !strings.Contains(strings.ToLower(text), "required") {
		t.Errorf("expected a 'required' error, got:\n%s", text)
	}
}

// Scenario: unknown tool yields a JSON-RPC error.
func TestUnknownTool(t *testing.T) {
	resp := runRequests(t,
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"does_not_exist","arguments":{}}}`,
	)
	if resp[1].Error == nil {
		t.Error("expected an error for unknown tool")
	}
}

// Scenario: standings rendered through the protocol name the champion.
func TestToolCallStandings(t *testing.T) {
	resp := runRequests(t,
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"standings","arguments":{"season":2023}}}`,
	)
	text := callText(t, resp[1])
	if !strings.Contains(text, "Champion: Flamengo-RJ") {
		t.Errorf("standings should crown Flamengo-RJ, got:\n%s", text)
	}
}
