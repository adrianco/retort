// Context: Brazilian Soccer MCP Server.
// File: server_test.go
// Purpose: Tests for the JSON-RPC 2.0 / MCP stdio protocol layer — initialize,
// tools/list, tools/call (success and error), notifications, and the
// line-oriented Serve loop.
package mcpserver

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func decode(t *testing.T, raw []byte) map[string]any {
	t.Helper()
	var m map[string]any
	if err := json.Unmarshal(raw, &m); err != nil {
		t.Fatalf("invalid JSON response %q: %v", raw, err)
	}
	return m
}

func TestHandleInitialize(t *testing.T) {
	s := NewServer(testHandler())
	resp, send := s.handleMessage([]byte(`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`))
	if !send {
		t.Fatal("initialize should produce a response")
	}
	m := decode(t, resp)
	if m["id"].(float64) != 1 {
		t.Errorf("id = %v, want 1", m["id"])
	}
	result, ok := m["result"].(map[string]any)
	if !ok {
		t.Fatalf("missing result: %v", m)
	}
	if _, ok := result["protocolVersion"]; !ok {
		t.Errorf("missing protocolVersion")
	}
	info, ok := result["serverInfo"].(map[string]any)
	if !ok || info["name"] == "" {
		t.Errorf("missing serverInfo: %v", result)
	}
}

func TestHandleNotificationNoResponse(t *testing.T) {
	s := NewServer(testHandler())
	_, send := s.handleMessage([]byte(`{"jsonrpc":"2.0","method":"notifications/initialized"}`))
	if send {
		t.Error("notifications must not produce a response")
	}
}

func TestHandleToolsList(t *testing.T) {
	s := NewServer(testHandler())
	resp, _ := s.handleMessage([]byte(`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`))
	m := decode(t, resp)
	result := m["result"].(map[string]any)
	tools, ok := result["tools"].([]any)
	if !ok || len(tools) != 6 {
		t.Fatalf("tools = %v, want 6", result["tools"])
	}
}

func TestHandleToolsCallSuccess(t *testing.T) {
	s := NewServer(testHandler())
	req := `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}`
	resp, _ := s.handleMessage([]byte(req))
	m := decode(t, resp)
	result, ok := m["result"].(map[string]any)
	if !ok {
		t.Fatalf("missing result: %v", m)
	}
	content := result["content"].([]any)
	first := content[0].(map[string]any)
	if first["type"] != "text" {
		t.Errorf("content type = %v", first["type"])
	}
	if !strings.Contains(first["text"].(string), "head-to-head") {
		t.Errorf("unexpected text: %v", first["text"])
	}
	if isErr, _ := result["isError"].(bool); isErr {
		t.Errorf("should not be an error")
	}
}

func TestHandleToolsCallToolError(t *testing.T) {
	s := NewServer(testHandler())
	// Missing required team_b -> tool error reported via isError, not a protocol error.
	req := `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo"}}}`
	resp, _ := s.handleMessage([]byte(req))
	m := decode(t, resp)
	result, ok := m["result"].(map[string]any)
	if !ok {
		t.Fatalf("expected result with isError, got %v", m)
	}
	if isErr, _ := result["isError"].(bool); !isErr {
		t.Errorf("expected isError true")
	}
}

func TestHandleUnknownMethod(t *testing.T) {
	s := NewServer(testHandler())
	resp, send := s.handleMessage([]byte(`{"jsonrpc":"2.0","id":5,"method":"bogus/method"}`))
	if !send {
		t.Fatal("expected an error response")
	}
	m := decode(t, resp)
	errObj, ok := m["error"].(map[string]any)
	if !ok {
		t.Fatalf("expected error object, got %v", m)
	}
	if errObj["code"].(float64) != -32601 {
		t.Errorf("code = %v, want -32601 (method not found)", errObj["code"])
	}
}

func TestHandleParseError(t *testing.T) {
	s := NewServer(testHandler())
	resp, send := s.handleMessage([]byte(`{not json`))
	if !send {
		t.Fatal("expected a parse-error response")
	}
	m := decode(t, resp)
	errObj := m["error"].(map[string]any)
	if errObj["code"].(float64) != -32700 {
		t.Errorf("code = %v, want -32700 (parse error)", errObj["code"])
	}
}

func TestServeLoop(t *testing.T) {
	s := NewServer(testHandler())
	in := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
	}, "\n") + "\n"
	var out bytes.Buffer
	if err := s.Serve(strings.NewReader(in), &out); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	// initialize + tools/list produce responses; the notification does not.
	if len(lines) != 2 {
		t.Fatalf("got %d response lines, want 2:\n%s", len(lines), out.String())
	}
	for _, l := range lines {
		decode(t, []byte(l)) // each line must be valid JSON
	}
}
