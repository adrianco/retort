package mcp

import (
	"encoding/json"
	"strings"
	"testing"
)

// newTestServer returns a server with one echo-style tool registered.
func newTestServer() *Server {
	s := NewServer("test", "0.1")
	s.AddTool("greet", "Greets a name",
		map[string]any{"type": "object", "properties": map[string]any{
			"name": map[string]any{"type": "string"},
		}},
		func(args json.RawMessage) (string, error) {
			var a struct {
				Name string `json:"name"`
			}
			_ = json.Unmarshal(args, &a)
			if a.Name == "boom" {
				panic("kaboom")
			}
			return "Hello, " + a.Name, nil
		})
	return s
}

// run feeds the given JSON-RPC lines through the server and returns the decoded
// responses (one per non-notification request).
func run(t *testing.T, lines ...string) []map[string]any {
	t.Helper()
	in := strings.NewReader(strings.Join(lines, "\n") + "\n")
	var out strings.Builder
	if err := newTestServer().Serve(in, &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resps []map[string]any
	for _, line := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if line == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			t.Fatalf("bad response line %q: %v", line, err)
		}
		resps = append(resps, m)
	}
	return resps
}

func TestInitialize(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	if len(resps) != 1 {
		t.Fatalf("want 1 response, got %d", len(resps))
	}
	res := resps[0]["result"].(map[string]any)
	if res["protocolVersion"] != ProtocolVersion {
		t.Errorf("protocolVersion = %v", res["protocolVersion"])
	}
	if _, ok := res["serverInfo"]; !ok {
		t.Errorf("missing serverInfo")
	}
}

func TestNotificationProducesNoResponse(t *testing.T) {
	resps := run(t,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"ping"}`,
	)
	// Only the ping (id 2) should produce a response.
	if len(resps) != 1 {
		t.Fatalf("want 1 response, got %d: %v", len(resps), resps)
	}
	if resps[0]["id"].(float64) != 2 {
		t.Errorf("unexpected response id: %v", resps[0]["id"])
	}
}

func TestToolsList(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":3,"method":"tools/list"}`)
	res := resps[0]["result"].(map[string]any)
	tools := res["tools"].([]any)
	if len(tools) != 1 {
		t.Fatalf("want 1 tool, got %d", len(tools))
	}
	tool := tools[0].(map[string]any)
	if tool["name"] != "greet" {
		t.Errorf("tool name = %v", tool["name"])
	}
	if _, ok := tool["inputSchema"]; !ok {
		t.Errorf("tool missing inputSchema")
	}
}

func TestToolsCall(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"greet","arguments":{"name":"Pelé"}}}`)
	res := resps[0]["result"].(map[string]any)
	if res["isError"] != false {
		t.Errorf("isError = %v", res["isError"])
	}
	content := res["content"].([]any)
	text := content[0].(map[string]any)["text"].(string)
	if text != "Hello, Pelé" {
		t.Errorf("text = %q", text)
	}
}

func TestToolsCallUnknown(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"nope","arguments":{}}}`)
	if _, ok := resps[0]["error"]; !ok {
		t.Errorf("expected error for unknown tool, got %v", resps[0])
	}
}

func TestToolPanicBecomesError(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"greet","arguments":{"name":"boom"}}}`)
	res := resps[0]["result"].(map[string]any)
	if res["isError"] != true {
		t.Errorf("panic should yield isError=true, got %v", res)
	}
}

func TestUnknownMethod(t *testing.T) {
	resps := run(t, `{"jsonrpc":"2.0","id":7,"method":"does/not/exist"}`)
	errObj := resps[0]["error"].(map[string]any)
	if int(errObj["code"].(float64)) != codeMethodNotFound {
		t.Errorf("code = %v, want %d", errObj["code"], codeMethodNotFound)
	}
}

func TestParseError(t *testing.T) {
	resps := run(t, `{not valid json`)
	errObj := resps[0]["error"].(map[string]any)
	if int(errObj["code"].(float64)) != codeParseError {
		t.Errorf("code = %v, want %d", errObj["code"], codeParseError)
	}
}
