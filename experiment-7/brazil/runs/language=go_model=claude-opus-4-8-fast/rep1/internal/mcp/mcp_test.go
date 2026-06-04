// Package mcp tests — JSON-RPC/MCP transport behavior (BDD Given/When/Then).
package mcp

import (
	"encoding/json"
	"strings"
	"testing"
)

// newTestServer returns a server with one echo tool registered.
func newTestServer() *Server {
	s := NewServer("test", "0.0.1")
	s.AddTool("echo", "Echoes the 'text' argument.",
		map[string]any{"type": "object", "properties": map[string]any{
			"text": map[string]any{"type": "string"},
		}},
		func(args json.RawMessage) (string, error) {
			var a struct {
				Text string `json:"text"`
			}
			_ = json.Unmarshal(args, &a)
			return "echo: " + a.Text, nil
		})
	return s
}

// roundtrip runs one request line through the server and parses the response.
func roundtrip(t *testing.T, s *Server, line string) map[string]any {
	t.Helper()
	var out strings.Builder
	if err := s.Serve(strings.NewReader(line+"\n"), &out); err != nil {
		t.Fatalf("Serve error: %v", err)
	}
	resp := strings.TrimSpace(out.String())
	if resp == "" {
		return nil
	}
	var m map[string]any
	if err := json.Unmarshal([]byte(resp), &m); err != nil {
		t.Fatalf("invalid JSON response %q: %v", resp, err)
	}
	return m
}

// Scenario: initialize returns protocol version and server info.
func TestScenario_Initialize(t *testing.T) {
	// Given an MCP server
	s := newTestServer()
	// When the client sends initialize
	resp := roundtrip(t, s, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	// Then a result with protocolVersion and serverInfo is returned
	result, ok := resp["result"].(map[string]any)
	if !ok {
		t.Fatalf("Then a result object is expected; got %v", resp)
	}
	if result["protocolVersion"] != ProtocolVersion {
		t.Errorf("Then protocolVersion should be %q; got %v", ProtocolVersion, result["protocolVersion"])
	}
	info, _ := result["serverInfo"].(map[string]any)
	if info["name"] != "test" {
		t.Errorf("Then serverInfo.name should be 'test'; got %v", info["name"])
	}
}

// Scenario: notifications/initialized produces no response.
func TestScenario_NotificationNoResponse(t *testing.T) {
	// Given an MCP server
	s := newTestServer()
	// When an initialized notification (no id) is sent
	resp := roundtrip(t, s, `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
	// Then nothing is written back
	if resp != nil {
		t.Errorf("Then notifications must not produce a response; got %v", resp)
	}
}

// Scenario: tools/list returns the registered tools.
func TestScenario_ListTools(t *testing.T) {
	// Given a server with an echo tool
	s := newTestServer()
	// When tools/list is requested
	resp := roundtrip(t, s, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	// Then the echo tool is listed with a schema
	result := resp["result"].(map[string]any)
	tools := result["tools"].([]any)
	if len(tools) != 1 {
		t.Fatalf("Then one tool is expected; got %d", len(tools))
	}
	tool := tools[0].(map[string]any)
	if tool["name"] != "echo" {
		t.Errorf("Then tool name should be 'echo'; got %v", tool["name"])
	}
	if _, ok := tool["inputSchema"].(map[string]any); !ok {
		t.Error("Then the tool should expose an inputSchema")
	}
}

// Scenario: tools/call invokes the handler and returns text content.
func TestScenario_CallTool(t *testing.T) {
	// Given a server with an echo tool
	s := newTestServer()
	// When echo is called with text "hi"
	resp := roundtrip(t, s, `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"text":"hi"}}}`)
	// Then the result content carries "echo: hi" and is not an error
	result := resp["result"].(map[string]any)
	if result["isError"] != false {
		t.Errorf("Then isError should be false; got %v", result["isError"])
	}
	content := result["content"].([]any)
	first := content[0].(map[string]any)
	if first["text"] != "echo: hi" {
		t.Errorf("Then text should be 'echo: hi'; got %v", first["text"])
	}
}

// Scenario: Calling an unknown tool yields a JSON-RPC error.
func TestScenario_CallUnknownTool(t *testing.T) {
	// Given a server
	s := newTestServer()
	// When an unregistered tool is called
	resp := roundtrip(t, s, `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"nope"}}`)
	// Then an error is returned
	if _, ok := resp["error"].(map[string]any); !ok {
		t.Errorf("Then an error is expected; got %v", resp)
	}
}

// Scenario: A handler error becomes an isError tool result, not a protocol error.
func TestScenario_HandlerErrorIsToolError(t *testing.T) {
	// Given a server with a tool that always fails
	s := NewServer("test", "0.0.1")
	s.AddTool("boom", "always fails", map[string]any{"type": "object"},
		func(args json.RawMessage) (string, error) {
			return "", errFail
		})
	// When the tool is called
	resp := roundtrip(t, s, `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"boom","arguments":{}}}`)
	// Then the result is a tool result flagged isError
	result, ok := resp["result"].(map[string]any)
	if !ok {
		t.Fatalf("Then a result (not a protocol error) is expected; got %v", resp)
	}
	if result["isError"] != true {
		t.Errorf("Then isError should be true; got %v", result["isError"])
	}
}

// Scenario: Unknown methods produce a method-not-found error.
func TestScenario_UnknownMethod(t *testing.T) {
	// Given a server
	s := newTestServer()
	// When an unknown method is called
	resp := roundtrip(t, s, `{"jsonrpc":"2.0","id":6,"method":"does/not/exist"}`)
	// Then a method-not-found error is returned
	e, ok := resp["error"].(map[string]any)
	if !ok {
		t.Fatalf("Then an error is expected; got %v", resp)
	}
	if int(e["code"].(float64)) != codeMethodNotFound {
		t.Errorf("Then code should be %d; got %v", codeMethodNotFound, e["code"])
	}
}

type sentinelErr string

func (e sentinelErr) Error() string { return string(e) }

const errFail = sentinelErr("boom failed")
