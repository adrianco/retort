package mcp

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func exchange(t *testing.T, s *Server, lines ...string) []map[string]any {
	t.Helper()
	var out bytes.Buffer
	if err := s.Serve(strings.NewReader(strings.Join(lines, "\n")+"\n"), &out); err != nil {
		t.Fatal(err)
	}
	var resps []map[string]any
	for _, l := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if l == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(l), &m); err != nil {
			t.Fatalf("bad response %q", l)
		}
		resps = append(resps, m)
	}
	return resps
}

func testServer() *Server {
	s := NewServer("test", "1", "")
	s.AddTool(Tool{Name: "echo", InputSchema: map[string]any{"type": "object"}, Handler: func(a Args) (string, any, error) {
		n, err := a.Int("n")
		return "n is " + a.String("n"), map[string]any{"n": n}, err
	}})
	return s
}

func TestHandshakeListAndCall(t *testing.T) {
	resps := exchange(t, testServer(),
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"n":"7"}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"echo","arguments":{"n":"seven"}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"nope"}`,
	)
	if len(resps) != 5 {
		t.Fatalf("notifications get no reply; expected 5 responses, got %d", len(resps))
	}
	if v := resps[0]["result"].(map[string]any)["protocolVersion"]; v != "2025-03-26" {
		t.Errorf("should agree to the client's supported version, got %v", v)
	}
	if tools := resps[1]["result"].(map[string]any)["tools"].([]any); len(tools) != 1 {
		t.Errorf("expected one tool")
	}
	call := resps[2]["result"].(map[string]any)
	if call["structuredContent"].(map[string]any)["n"].(float64) != 7 {
		t.Errorf("numbers sent as text should be understood: %v", call)
	}
	if resps[3]["result"].(map[string]any)["isError"] != true {
		t.Errorf("a bad argument is a tool error the model can read")
	}
	if resps[4]["error"].(map[string]any)["code"].(float64) != -32601 {
		t.Errorf("unknown methods are JSON-RPC errors")
	}
}

func TestMalformedJSONIsAParseError(t *testing.T) {
	resps := exchange(t, testServer(), `{not json`)
	if resps[0]["error"].(map[string]any)["code"].(float64) != -32700 {
		t.Errorf("expected parse error, got %v", resps[0])
	}
}
