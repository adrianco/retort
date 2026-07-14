// server_test.go - protocol-level tests for the MCP stdio transport.
//
// Context
// -------
// These tests drive the JSON-RPC loop end to end over in-memory pipes: they
// perform the initialize handshake, list tools and call a tool, asserting on the
// wire-level responses. A trivial echo tool is registered so the transport is
// tested independently of the soccer domain logic.
package mcp

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
	"testing"
)

// run feeds the given newline-delimited JSON requests through a server and
// returns the decoded responses (one per non-notification request line).
func run(t *testing.T, s *Server, requests ...string) []map[string]any {
	t.Helper()
	in := strings.NewReader(strings.Join(requests, "\n") + "\n")
	pr, pw := io.Pipe()
	go func() {
		_ = s.Serve(in, pw)
		pw.Close()
	}()
	var out []map[string]any
	scanner := bufio.NewScanner(pr)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(strings.TrimSpace(string(line))) == 0 {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal(line, &m); err != nil {
			t.Fatalf("invalid JSON response %q: %v", line, err)
		}
		out = append(out, m)
	}
	return out
}

func newEchoServer() *Server {
	s := NewServer("test", "0.0.1")
	s.Register("echo", "echo back the text argument",
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

func TestInitializeHandshake(t *testing.T) {
	// Given a server
	s := newEchoServer()
	// When the client initializes
	resp := run(t, s, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	// Then it advertises the protocol version and server info
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	result, _ := resp[0]["result"].(map[string]any)
	if result["protocolVersion"] != ProtocolVersion {
		t.Errorf("protocolVersion = %v, want %v", result["protocolVersion"], ProtocolVersion)
	}
	info, _ := result["serverInfo"].(map[string]any)
	if info["name"] != "test" {
		t.Errorf("serverInfo.name = %v, want test", info["name"])
	}
}

func TestNotificationProducesNoResponse(t *testing.T) {
	// Given a server
	s := newEchoServer()
	// When an initialized notification (no id) is sent
	resp := run(t, s, `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
	// Then no response is written
	if len(resp) != 0 {
		t.Fatalf("expected no responses for a notification, got %d", len(resp))
	}
}

func TestToolsListAndCall(t *testing.T) {
	// Given an initialized server
	s := newEchoServer()
	resp := run(t, s,
		`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"text":"hi"}}}`,
	)
	if len(resp) != 2 {
		t.Fatalf("expected 2 responses, got %d", len(resp))
	}
	// Then tools/list contains the echo tool with a schema
	listResult, _ := resp[0]["result"].(map[string]any)
	tools, _ := listResult["tools"].([]any)
	if len(tools) != 1 {
		t.Fatalf("expected 1 tool, got %d", len(tools))
	}
	tool, _ := tools[0].(map[string]any)
	if tool["name"] != "echo" {
		t.Errorf("tool name = %v, want echo", tool["name"])
	}
	if _, ok := tool["inputSchema"].(map[string]any); !ok {
		t.Error("tool should expose an inputSchema object")
	}
	// And tools/call returns the echoed content
	callResult, _ := resp[1]["result"].(map[string]any)
	if callResult["isError"] != false {
		t.Errorf("isError = %v, want false", callResult["isError"])
	}
	content, _ := callResult["content"].([]any)
	first, _ := content[0].(map[string]any)
	if first["text"] != "echo: hi" {
		t.Errorf("text = %v, want 'echo: hi'", first["text"])
	}
}

func TestUnknownToolReportsError(t *testing.T) {
	// Given a server
	s := newEchoServer()
	// When an unknown tool is called
	resp := run(t, s, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nope"}}`)
	// Then a JSON-RPC error is returned
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	if _, ok := resp[0]["error"].(map[string]any); !ok {
		t.Errorf("expected an error object, got %v", resp[0])
	}
}

func TestUnknownMethodReturnsMethodNotFound(t *testing.T) {
	// Given a server
	s := newEchoServer()
	// When an unsupported method is requested
	resp := run(t, s, `{"jsonrpc":"2.0","id":7,"method":"resources/list"}`)
	// Then a method-not-found error is returned
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	errObj, ok := resp[0]["error"].(map[string]any)
	if !ok {
		t.Fatalf("expected an error, got %v", resp[0])
	}
	if code, _ := errObj["code"].(float64); int(code) != errMethodNotFound {
		t.Errorf("code = %v, want %d", errObj["code"], errMethodNotFound)
	}
}
