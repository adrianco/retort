// server_test.go exercises the JSON-RPC/MCP layer with a stub tool, so the
// protocol behaviour is verified independently of the soccer data.
package mcp

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func testServer() *Server {
	s := NewServer("test", "0.0.1", "instructions")
	s.Register(Tool{
		Name:        "echo",
		Description: "echo back the message",
		InputSchema: Schema{Type: "object", Properties: map[string]*Prop{"message": {Type: "string"}}, Required: []string{"message"}},
	}, func(a Args) (*CallToolResult, error) {
		msg, err := a.RequireString("message")
		if err != nil {
			return nil, err
		}
		return &CallToolResult{Content: []Content{TextContent(msg)}}, nil
	})
	return s
}

// call sends one request and decodes the raw JSON response.
func call(t *testing.T, s *Server, req map[string]any) map[string]any {
	t.Helper()
	raw, _ := json.Marshal(req)
	var in bytes.Buffer
	in.Write(raw)
	in.WriteString("\n")
	var out bytes.Buffer
	if err := s.Serve(&in, &out); err != nil {
		t.Fatalf("serve: %v", err)
	}
	if out.Len() == 0 {
		return nil
	}
	var resp map[string]any
	if err := json.Unmarshal(out.Bytes(), &resp); err != nil {
		t.Fatalf("decode %q: %v", out.String(), err)
	}
	return resp
}

func TestInitializeHandshake(t *testing.T) {
	resp := call(t, testServer(), map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "initialize",
		"params": map[string]any{"protocolVersion": ProtocolVersion},
	})
	if resp["jsonrpc"] != "2.0" {
		t.Errorf("missing jsonrpc version: %v", resp)
	}
	result, ok := resp["result"].(map[string]any)
	if !ok {
		t.Fatalf("no result: %v", resp)
	}
	if result["protocolVersion"] != ProtocolVersion {
		t.Errorf("protocol version = %v", result["protocolVersion"])
	}
	info := result["serverInfo"].(map[string]any)
	if info["name"] != "test" {
		t.Errorf("server name = %v", info["name"])
	}
	if _, ok := result["capabilities"].(map[string]any)["tools"]; !ok {
		t.Error("tools capability not advertised")
	}
}

func TestNotificationsGetNoResponse(t *testing.T) {
	if resp := call(t, testServer(), map[string]any{
		"jsonrpc": "2.0", "method": "notifications/initialized",
	}); resp != nil {
		t.Errorf("notification produced a response: %v", resp)
	}
}

func TestToolsListDescribesSchemas(t *testing.T) {
	resp := call(t, testServer(), map[string]any{"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
	tools := resp["result"].(map[string]any)["tools"].([]any)
	if len(tools) != 1 {
		t.Fatalf("expected one tool, got %d", len(tools))
	}
	tool := tools[0].(map[string]any)
	if tool["name"] != "echo" || tool["description"] == "" {
		t.Errorf("bad tool entry: %v", tool)
	}
	schema := tool["inputSchema"].(map[string]any)
	if schema["type"] != "object" {
		t.Errorf("schema type = %v", schema["type"])
	}
}

func TestToolsCall(t *testing.T) {
	resp := call(t, testServer(), map[string]any{
		"jsonrpc": "2.0", "id": 3, "method": "tools/call",
		"params": map[string]any{"name": "echo", "arguments": map[string]any{"message": "olá"}},
	})
	content := resp["result"].(map[string]any)["content"].([]any)
	first := content[0].(map[string]any)
	if first["type"] != "text" || first["text"] != "olá" {
		t.Errorf("unexpected content: %v", content)
	}
}

func TestToolErrorsAreReportedInBand(t *testing.T) {
	resp := call(t, testServer(), map[string]any{
		"jsonrpc": "2.0", "id": 4, "method": "tools/call",
		"params": map[string]any{"name": "echo", "arguments": map[string]any{}},
	})
	if resp["error"] != nil {
		t.Fatalf("recoverable tool failures must not be protocol errors: %v", resp["error"])
	}
	result := resp["result"].(map[string]any)
	if result["isError"] != true {
		t.Errorf("expected isError: %v", result)
	}
	text := result["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "message") {
		t.Errorf("error text should name the missing argument: %q", text)
	}
}

func TestProtocolErrors(t *testing.T) {
	s := testServer()

	resp := call(t, s, map[string]any{"jsonrpc": "2.0", "id": 5, "method": "does/not/exist"})
	if e := resp["error"].(map[string]any); int(e["code"].(float64)) != CodeMethodNotFound {
		t.Errorf("expected method-not-found, got %v", e)
	}

	resp = call(t, s, map[string]any{
		"jsonrpc": "2.0", "id": 6, "method": "tools/call",
		"params": map[string]any{"name": "nope"},
	})
	if e := resp["error"].(map[string]any); int(e["code"].(float64)) != CodeInvalidParams {
		t.Errorf("expected invalid-params for an unknown tool, got %v", e)
	}

	var out bytes.Buffer
	if err := s.Serve(strings.NewReader("{not json}\n"), &out); err != nil {
		t.Fatal(err)
	}
	var parseResp map[string]any
	if err := json.Unmarshal(out.Bytes(), &parseResp); err != nil {
		t.Fatal(err)
	}
	if e := parseResp["error"].(map[string]any); int(e["code"].(float64)) != CodeParseError {
		t.Errorf("expected parse error, got %v", e)
	}
}

func TestServeHandlesMultipleMessages(t *testing.T) {
	in := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"ping"}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		``,
	}, "\n")
	var out bytes.Buffer
	if err := testServer().Serve(strings.NewReader(in), &out); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("expected two responses (the notification gets none), got %d:\n%s", len(lines), out.String())
	}
}

func TestArgsCoercion(t *testing.T) {
	a := Args{"season": "2019", "limit": 5.0, "flag": "true", "name": " Flamengo "}
	if a.Int("season", 0) != 2019 {
		t.Error("string season should coerce to int")
	}
	if a.Int("limit", 0) != 5 {
		t.Error("float limit should coerce to int")
	}
	if !a.Bool("flag", false) {
		t.Error("string flag should coerce to bool")
	}
	if a.String("name") != "Flamengo" {
		t.Errorf("string should be trimmed, got %q", a.String("name"))
	}
	if a.Int("missing", 7) != 7 {
		t.Error("missing values should fall back to the default")
	}
	if _, err := a.RequireString("missing"); err == nil {
		t.Error("RequireString should fail on a missing key")
	}
}
