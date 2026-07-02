package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"strings"
	"testing"
)

func testServer() *Server {
	s := NewServer(log.New(io.Discard, "", 0))
	RegisterTools(s, buildTestStore())
	return s
}

func runLines(t *testing.T, s *Server, requests ...string) []map[string]any {
	t.Helper()
	in := strings.NewReader(strings.Join(requests, "\n") + "\n")
	var out bytes.Buffer
	if err := s.Run(in, &out); err != nil {
		t.Fatalf("Run: %v", err)
	}
	var responses []map[string]any
	dec := json.NewDecoder(&out)
	for dec.More() {
		var m map[string]any
		if err := dec.Decode(&m); err != nil {
			t.Fatalf("decoding response: %v", err)
		}
		responses = append(responses, m)
	}
	return responses
}

func TestInitializeAndToolsList(t *testing.T) {
	s := testServer()
	resp := runLines(t, s,
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
	)
	if len(resp) != 2 {
		t.Fatalf("got %d responses, want 2", len(resp))
	}
	result, ok := resp[0]["result"].(map[string]any)
	if !ok || result["protocolVersion"] != protocolVersion {
		t.Fatalf("initialize result = %+v", resp[0])
	}

	toolsResult := resp[1]["result"].(map[string]any)
	tools := toolsResult["tools"].([]any)
	if len(tools) != 6 {
		t.Fatalf("got %d tools, want 6", len(tools))
	}
	names := map[string]bool{}
	for _, raw := range tools {
		tool := raw.(map[string]any)
		names[tool["name"].(string)] = true
	}
	for _, want := range []string{"search_matches", "head_to_head", "team_record", "standings", "stats_overview", "search_players"} {
		if !names[want] {
			t.Errorf("missing tool %q", want)
		}
	}
}

func TestNotificationGetsNoResponse(t *testing.T) {
	s := testServer()
	resp := runLines(t, s,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":1,"method":"ping"}`,
	)
	if len(resp) != 1 {
		t.Fatalf("got %d responses, want 1 (notification should produce none)", len(resp))
	}
}

func TestToolsCallSearchMatches(t *testing.T) {
	s := testServer()
	resp := runLines(t, s,
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","limit":5}}}`,
	)
	if len(resp) != 1 {
		t.Fatalf("got %d responses, want 1", len(resp))
	}
	result := resp[0]["result"].(map[string]any)
	content := result["content"].([]any)[0].(map[string]any)
	var payload SearchMatchesResult
	if err := json.Unmarshal([]byte(content["text"].(string)), &payload); err != nil {
		t.Fatalf("unmarshalling tool text payload: %v", err)
	}
	if payload.TotalMatches == 0 {
		t.Fatalf("expected some matches for Flamengo, got %+v", payload)
	}
}

func TestToolsCallUnknownTool(t *testing.T) {
	s := testServer()
	resp := runLines(t, s,
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"does_not_exist","arguments":{}}}`,
	)
	if resp[0]["error"] == nil {
		t.Fatalf("expected an error response, got %+v", resp[0])
	}
}

func TestToolsCallMissingRequiredArg(t *testing.T) {
	s := testServer()
	resp := runLines(t, s,
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo"}}}`,
	)
	result := resp[0]["result"].(map[string]any)
	if result["isError"] != true {
		t.Fatalf("expected isError=true for missing team_b, got %+v", result)
	}
}

func TestUnknownMethod(t *testing.T) {
	s := testServer()
	resp := runLines(t, s,
		`{"jsonrpc":"2.0","id":1,"method":"totally/bogus"}`,
	)
	if resp[0]["error"] == nil {
		t.Fatalf("expected method-not-found error, got %+v", resp[0])
	}
}
