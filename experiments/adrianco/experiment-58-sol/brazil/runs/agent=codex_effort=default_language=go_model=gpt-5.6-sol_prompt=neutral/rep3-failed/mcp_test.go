package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func TestMCPInitializeListAndToolCall(t *testing.T) {
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
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
	if result["protocolVersion"] == "" {
		t.Fatal("initialize omitted protocol version")
	}
	tools := listResp["result"].(map[string]any)["tools"].([]any)
	if len(tools) < 9 {
		t.Fatalf("expected specialized tool set, got %d", len(tools))
	}
	call := callResp["result"].(map[string]any)
	content := call["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(content, "2 matches") {
		t.Fatalf("unexpected tool content: %s", content)
	}
}

func TestMCPInvalidDateIsToolError(t *testing.T) {
	result, err := NewMCPServer(syntheticDB()).callTool("search_matches", map[string]any{"start_date": "03/04/2022"})
	if err == nil || result.Content != nil {
		t.Fatalf("expected date validation error, got result=%+v err=%v", result, err)
	}
}
