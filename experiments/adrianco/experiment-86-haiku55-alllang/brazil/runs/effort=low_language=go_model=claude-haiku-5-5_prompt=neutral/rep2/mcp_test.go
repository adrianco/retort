package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// roundTrip sends newline-delimited requests to a server and decodes the responses.
func roundTrip(t *testing.T, srv *Server, lines ...string) []map[string]any {
	t.Helper()
	in := strings.NewReader(strings.Join(lines, "\n") + "\n")
	var out bytes.Buffer
	if err := srv.Serve(in, &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var responses []map[string]any
	for _, line := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if line == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			t.Fatalf("response is not JSON: %q", line)
		}
		responses = append(responses, m)
	}
	return responses
}

func testServer(t *testing.T) *Server {
	t.Helper()
	return NewServer("brazilian-soccer-mcp", "test", newTools(fixtureStore(t)))
}

func TestFeature_MCPProtocol(t *testing.T) {
	t.Run("Scenario: the client initializes the session", func(t *testing.T) {
		// Given a running server
		srv := testServer(t)
		// When the client sends initialize
		resp := roundTrip(t, srv, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}`)
		// Then the server reports its protocol version, tool capability and name
		if len(resp) != 1 {
			t.Fatalf("got %d responses", len(resp))
		}
		result := resp[0]["result"].(map[string]any)
		if result["protocolVersion"] != protocolVersion {
			t.Errorf("protocolVersion = %v", result["protocolVersion"])
		}
		if _, ok := result["capabilities"].(map[string]any)["tools"]; !ok {
			t.Error("tools capability not advertised")
		}
		if result["serverInfo"].(map[string]any)["name"] != "brazilian-soccer-mcp" {
			t.Error("serverInfo.name wrong")
		}
	})

	t.Run("Scenario: the client lists the tools", func(t *testing.T) {
		resp := roundTrip(t, testServer(t), `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
		tools := resp[0]["result"].(map[string]any)["tools"].([]any)
		names := map[string]bool{}
		for _, tool := range tools {
			m := tool.(map[string]any)
			names[m["name"].(string)] = true
			if m["description"] == "" || m["inputSchema"] == nil {
				t.Errorf("tool %v lacks a description or schema", m["name"])
			}
		}
		for _, want := range []string{"find_matches", "team_stats", "team_ranking", "standings",
			"competition_stats", "search_players", "brazilian_clubs_summary"} {
			if !names[want] {
				t.Errorf("tool %s not listed", want)
			}
		}
	})

	t.Run("Scenario: a notification is not answered", func(t *testing.T) {
		resp := roundTrip(t, testServer(t), `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
		if len(resp) != 0 {
			t.Errorf("notification got a response: %v", resp)
		}
	})

	t.Run("Scenario: ping returns an empty result", func(t *testing.T) {
		resp := roundTrip(t, testServer(t), `{"jsonrpc":"2.0","id":"abc","method":"ping"}`)
		if resp[0]["id"] != "abc" {
			t.Errorf("string id not echoed: %v", resp[0]["id"])
		}
		if _, ok := resp[0]["result"].(map[string]any); !ok {
			t.Errorf("ping result = %v", resp[0]["result"])
		}
	})

	t.Run("Scenario: an unknown method returns method-not-found", func(t *testing.T) {
		resp := roundTrip(t, testServer(t), `{"jsonrpc":"2.0","id":3,"method":"resources/list"}`)
		if code := resp[0]["error"].(map[string]any)["code"]; code != float64(errMethodNotFound) {
			t.Errorf("code = %v", code)
		}
	})

	t.Run("Scenario: malformed JSON returns a parse error", func(t *testing.T) {
		resp := roundTrip(t, testServer(t), `{not json`)
		if code := resp[0]["error"].(map[string]any)["code"]; code != float64(errParse) {
			t.Errorf("code = %v", code)
		}
	})

	t.Run("Scenario: an unknown tool is an invalid-params error", func(t *testing.T) {
		resp := roundTrip(t, testServer(t), `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"nope"}}`)
		if code := resp[0]["error"].(map[string]any)["code"]; code != float64(errInvalidParams) {
			t.Errorf("code = %v", code)
		}
	})

	t.Run("Scenario: a failing tool reports isError inside the result", func(t *testing.T) {
		// Given a team name that does not exist
		// When the client calls find_matches
		resp := roundTrip(t, testServer(t),
			`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Nowhere FC"}}}`)
		// Then the JSON-RPC call succeeds but the result is flagged as an error
		result := resp[0]["result"].(map[string]any)
		if result["isError"] != true {
			t.Fatalf("isError = %v", result["isError"])
		}
		text := result["content"].([]any)[0].(map[string]any)["text"].(string)
		if !strings.Contains(text, "no team matching") {
			t.Errorf("error text = %q", text)
		}
	})

	t.Run("Scenario: a successful tool call returns text content", func(t *testing.T) {
		resp := roundTrip(t, testServer(t),
			`{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}`)
		result := resp[0]["result"].(map[string]any)
		if result["isError"] != false {
			t.Fatalf("unexpected error: %v", result)
		}
		text := result["content"].([]any)[0].(map[string]any)["text"].(string)
		if !strings.Contains(text, "Champion") {
			t.Errorf("text = %q", text)
		}
	})

	t.Run("Scenario: several requests on one connection each get a response", func(t *testing.T) {
		resp := roundTrip(t, testServer(t),
			`{"jsonrpc":"2.0","id":1,"method":"ping"}`,
			`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
			`{"jsonrpc":"2.0","id":2,"method":"ping"}`,
		)
		if len(resp) != 2 {
			t.Fatalf("got %d responses, want 2", len(resp))
		}
	})
}
