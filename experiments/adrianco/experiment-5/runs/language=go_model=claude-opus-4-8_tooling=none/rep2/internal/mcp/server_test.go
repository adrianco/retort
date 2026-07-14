package mcp

import (
	"encoding/json"
	"strings"
	"testing"
)

// run feeds the given newline-delimited requests through a server and returns
// the decoded responses (one per request that expects a reply).
func run(t *testing.T, srv *Server, requests ...string) []map[string]any {
	t.Helper()
	in := strings.NewReader(strings.Join(requests, "\n") + "\n")
	var out strings.Builder
	if err := srv.Serve(in, &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resps []map[string]any
	dec := json.NewDecoder(strings.NewReader(out.String()))
	for dec.More() {
		var m map[string]any
		if err := dec.Decode(&m); err != nil {
			t.Fatalf("decode response: %v", err)
		}
		resps = append(resps, m)
	}
	return resps
}

func newTestServer() *Server {
	srv := NewServer("test", "0.0.1")
	srv.AddTool(Tool{
		Name:        "echo",
		Description: "echoes the message argument",
		InputSchema: map[string]any{"type": "object"},
		Handler: func(args json.RawMessage) (string, error) {
			var a struct {
				Message string `json:"message"`
			}
			_ = json.Unmarshal(args, &a)
			return "echo: " + a.Message, nil
		},
	})
	return srv
}

func TestInitialize(t *testing.T) {
	srv := newTestServer()
	resps := run(t, srv, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	if len(resps) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resps))
	}
	result := resps[0]["result"].(map[string]any)
	if result["protocolVersion"] != ProtocolVersion {
		t.Errorf("protocolVersion = %v, want %v", result["protocolVersion"], ProtocolVersion)
	}
	info := result["serverInfo"].(map[string]any)
	if info["name"] != "test" {
		t.Errorf("serverInfo.name = %v, want test", info["name"])
	}
}

func TestNotificationGetsNoResponse(t *testing.T) {
	srv := newTestServer()
	resps := run(t, srv, `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
	if len(resps) != 0 {
		t.Fatalf("notification should produce no response, got %d", len(resps))
	}
}

func TestToolsList(t *testing.T) {
	srv := newTestServer()
	resps := run(t, srv, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	result := resps[0]["result"].(map[string]any)
	tools := result["tools"].([]any)
	if len(tools) != 1 {
		t.Fatalf("expected 1 tool, got %d", len(tools))
	}
	tool := tools[0].(map[string]any)
	if tool["name"] != "echo" {
		t.Errorf("tool name = %v, want echo", tool["name"])
	}
	if _, ok := tool["inputSchema"]; !ok {
		t.Error("tool missing inputSchema")
	}
}

func TestToolsCall(t *testing.T) {
	srv := newTestServer()
	resps := run(t, srv,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hi"}}}`)
	result := resps[0]["result"].(map[string]any)
	content := result["content"].([]any)
	text := content[0].(map[string]any)["text"].(string)
	if text != "echo: hi" {
		t.Errorf("text = %q, want %q", text, "echo: hi")
	}
	if result["isError"] != false {
		t.Errorf("isError = %v, want false", result["isError"])
	}
}

func TestUnknownToolIsError(t *testing.T) {
	srv := newTestServer()
	resps := run(t, srv,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"nope","arguments":{}}}`)
	if resps[0]["error"] == nil {
		t.Error("expected error for unknown tool")
	}
}

func TestUnknownMethod(t *testing.T) {
	srv := newTestServer()
	resps := run(t, srv, `{"jsonrpc":"2.0","id":5,"method":"does/not/exist"}`)
	errObj := resps[0]["error"].(map[string]any)
	if int(errObj["code"].(float64)) != codeMethodNotFound {
		t.Errorf("code = %v, want %d", errObj["code"], codeMethodNotFound)
	}
}
