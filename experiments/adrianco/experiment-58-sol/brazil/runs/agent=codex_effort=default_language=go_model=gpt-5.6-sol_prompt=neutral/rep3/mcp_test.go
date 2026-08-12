package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func TestMCPInitializeListAndToolCall(t *testing.T) {
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team1":"Alpha","team2":"Beta","limit":10}}}`,
	}, "\n")
	var output bytes.Buffer
	if err := NewMCPServer(syntheticDB()).Serve(strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(&output)
	var initResp, listResp, callResp map[string]any
	for _, target := range []*map[string]any{&initResp, &listResp, &callResp} {
		if err := decoder.Decode(target); err != nil {
			t.Fatal(err)
		}
	}
	result := initResp["result"].(map[string]any)
	if result["protocolVersion"] != "2024-11-05" {
		t.Fatalf("initialize did not negotiate the requested supported version: %v", result["protocolVersion"])
	}
	tools := listResp["result"].(map[string]any)["tools"].([]any)
	if len(tools) < 9 {
		t.Fatalf("expected specialized tool set, got %d", len(tools))
	}
	first := tools[0].(map[string]any)
	if first["name"] != "ask" || first["description"] == "" || first["inputSchema"] == nil {
		t.Fatalf("tool definition is not MCP-compatible: %#v", first)
	}
	if _, leaked := first["Name"]; leaked {
		t.Fatalf("tool definition leaked Go field names: %#v", first)
	}
	call := callResp["result"].(map[string]any)
	content := call["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(content, "2 matches") {
		t.Fatalf("unexpected tool content: %s", content)
	}
}

func TestDocumentedEntrypointServesKnown2019Standings(t *testing.T) {
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"entrypoint-test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirao","season":2019}}}`,
	}, "\n")
	var output bytes.Buffer
	if err := run([]string{"--data", "data/kaggle"}, strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}

	decoder := json.NewDecoder(&output)
	var initResp, listResp, standingsResp map[string]any
	for _, target := range []*map[string]any{&initResp, &listResp, &standingsResp} {
		if err := decoder.Decode(target); err != nil {
			t.Fatal(err)
		}
	}
	tools := listResp["result"].(map[string]any)["tools"].([]any)
	foundStandings := false
	for _, raw := range tools {
		if raw.(map[string]any)["name"] == "standings" {
			foundStandings = true
			break
		}
	}
	if !foundStandings {
		t.Fatal("standings was not discoverable from the documented entrypoint")
	}
	call := standingsResp["result"].(map[string]any)
	content := call["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(content, "1. Flamengo") || !strings.Contains(content, "90 pts") {
		t.Fatalf("known 2019 standings were not served over MCP: %s", content)
	}
}

func TestMCPInvalidDateIsToolError(t *testing.T) {
	result, err := NewMCPServer(syntheticDB()).callTool("search_matches", map[string]any{"start_date": "03/04/2022"})
	if err == nil || result.Content != nil {
		t.Fatalf("expected date validation error, got result=%+v err=%v", result, err)
	}
}
