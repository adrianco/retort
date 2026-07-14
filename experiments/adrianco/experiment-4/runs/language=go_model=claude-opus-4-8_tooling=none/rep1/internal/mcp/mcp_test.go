// Context
// -------
// Behaviour-Driven tests for the MCP JSON-RPC layer. They drive the server
// through an in-memory request stream (newline-delimited JSON-RPC) exactly as a
// real MCP client over stdio would, and assert the handshake, tool listing and
// tool invocation behaviour. The server is backed by the real datasets loaded
// once in TestMain.
package mcp

import (
	"bufio"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/soccer"
)

var testGraph *soccer.Graph

func TestMain(m *testing.M) {
	dir, ok := soccer.FindDataDir("")
	if !ok {
		panic("could not locate data/kaggle for tests")
	}
	g, err := soccer.LoadGraph(dir)
	if err != nil {
		panic(err)
	}
	testGraph = g
	os.Exit(m.Run())
}

// run feeds the given JSON-RPC request lines through a fresh server and returns
// the decoded responses, keyed by request id.
func run(t *testing.T, requests ...string) map[float64]Response {
	t.Helper()
	in := strings.NewReader(strings.Join(requests, "\n") + "\n")
	var out strings.Builder
	srv := NewServer(testGraph)
	if err := srv.Serve(in, &out); err != nil {
		t.Fatalf("Serve error: %v", err)
	}

	responses := map[float64]Response{}
	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var r Response
		if err := json.Unmarshal(line, &r); err != nil {
			t.Fatalf("bad response line %q: %v", line, err)
		}
		var id float64
		if len(r.ID) > 0 {
			_ = json.Unmarshal(r.ID, &id)
		}
		responses[id] = r
	}
	return responses
}

// callText extracts the text content of a tools/call response.
func callText(t *testing.T, r Response) string {
	t.Helper()
	if r.Error != nil {
		t.Fatalf("unexpected RPC error: %+v", r.Error)
	}
	b, _ := json.Marshal(r.Result)
	var res CallToolResult
	if err := json.Unmarshal(b, &res); err != nil {
		t.Fatalf("decode CallToolResult: %v", err)
	}
	if len(res.Content) == 0 {
		t.Fatal("empty tool content")
	}
	return res.Content[0].Text
}

func TestInitializeHandshake(t *testing.T) {
	// Given a client, When it sends initialize, Then the server returns its
	// protocol version, tool capability and identity.
	resps := run(t, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	r := resps[1]
	if r.Error != nil {
		t.Fatalf("initialize errored: %+v", r.Error)
	}
	b, _ := json.Marshal(r.Result)
	var init InitializeResult
	if err := json.Unmarshal(b, &init); err != nil {
		t.Fatal(err)
	}
	if init.ProtocolVersion != ProtocolVersion {
		t.Errorf("protocol version = %q, want %q", init.ProtocolVersion, ProtocolVersion)
	}
	if init.Capabilities.Tools == nil {
		t.Error("expected tools capability")
	}
	if init.ServerInfo.Name == "" {
		t.Error("expected server name")
	}
}

func TestNotificationProducesNoResponse(t *testing.T) {
	// Given an initialized notification (no id), When sent, Then no response is
	// emitted for it.
	resps := run(t,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":7,"method":"ping"}`,
	)
	if _, ok := resps[0]; ok {
		t.Error("notification should not produce a response")
	}
	if _, ok := resps[7]; !ok {
		t.Error("expected response to ping")
	}
}

func TestToolsList(t *testing.T) {
	// Given the server, When tools/list is called, Then the expected tools are
	// advertised, each with a name, description and input schema.
	resps := run(t, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	b, _ := json.Marshal(resps[2].Result)
	var list ToolsListResult
	if err := json.Unmarshal(b, &list); err != nil {
		t.Fatal(err)
	}
	want := map[string]bool{
		"search_matches": true, "head_to_head": true, "team_stats": true,
		"standings": true, "search_players": true, "competition_stats": true,
		"list_metadata": true,
	}
	got := map[string]bool{}
	for _, tool := range list.Tools {
		got[tool.Name] = true
		if tool.Description == "" {
			t.Errorf("tool %s missing description", tool.Name)
		}
		if len(tool.InputSchema) == 0 {
			t.Errorf("tool %s missing input schema", tool.Name)
		}
	}
	for name := range want {
		if !got[name] {
			t.Errorf("missing expected tool %q", name)
		}
	}
}

func TestToolCallStandings(t *testing.T) {
	// Given the server, When standings for 2019 is requested via tools/call,
	// Then the formatted table names Flamengo as champion.
	resps := run(t, `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":3}}}`)
	text := callText(t, resps[3])
	if !strings.Contains(text, "Flamengo") || !strings.Contains(text, "Champion") {
		t.Errorf("standings text missing champion:\n%s", text)
	}
}

func TestToolCallHeadToHead(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}`)
	text := callText(t, resps[4])
	if !strings.Contains(text, "Head-to-head") {
		t.Errorf("unexpected h2h text:\n%s", text)
	}
}

func TestToolCallSearchPlayers(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"search_players","arguments":{"name":"Neymar"}}}`)
	text := callText(t, resps[5])
	if !strings.Contains(text, "Neymar") {
		t.Errorf("expected Neymar in results:\n%s", text)
	}
}

func TestUnknownMethodReturnsError(t *testing.T) {
	// Given an unknown method, When called, Then a method-not-found error is
	// returned rather than crashing the server.
	resps := run(t, `{"jsonrpc":"2.0","id":9,"method":"does/not/exist"}`)
	if resps[9].Error == nil || resps[9].Error.Code != codeMethodNotFound {
		t.Errorf("expected method-not-found error, got %+v", resps[9])
	}
}

func TestUnknownToolReportsError(t *testing.T) {
	// Given an unknown tool name, When tools/call is invoked, Then the result
	// is flagged isError (an MCP-level, not protocol-level, failure).
	resps := run(t, `{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"nope","arguments":{}}}`)
	b, _ := json.Marshal(resps[10].Result)
	var res CallToolResult
	_ = json.Unmarshal(b, &res)
	if !res.IsError {
		t.Errorf("expected isError for unknown tool, got %+v", res)
	}
}
