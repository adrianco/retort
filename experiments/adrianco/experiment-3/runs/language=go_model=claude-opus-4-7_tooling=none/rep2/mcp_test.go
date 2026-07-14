// mcp_test.go verifies the JSON-RPC / MCP transport layer: initialization,
// tool discovery, tool invocation and error handling.
package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// testResp mirrors an outgoing JSON-RPC response for decoding in tests.
type testResp struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  json.RawMessage `json:"result"`
	Error   *rpcError       `json:"error"`
}

// serve feeds the given JSON-RPC request lines through a fresh server and
// returns the decoded responses.
func serve(t *testing.T, requests ...string) []testResp {
	t.Helper()
	store := loadedStore(t)
	var out bytes.Buffer
	srv := NewServer(BuildTools(store), &out)
	if err := srv.Serve(strings.NewReader(strings.Join(requests, "\n") + "\n")); err != nil {
		t.Fatalf("Serve failed: %v", err)
	}
	var responses []testResp
	for _, line := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if line == "" {
			continue
		}
		var r testResp
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			t.Fatalf("invalid response JSON %q: %v", line, err)
		}
		if r.JSONRPC != "2.0" {
			t.Errorf("response jsonrpc = %q, want 2.0", r.JSONRPC)
		}
		responses = append(responses, r)
	}
	return responses
}

func TestMCP_Initialize(t *testing.T) {
	// When the client sends an initialize request
	resp := serve(t, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	// Then the server reports its protocol version and identity
	var result struct {
		ProtocolVersion string `json:"protocolVersion"`
		ServerInfo      struct {
			Name string `json:"name"`
		} `json:"serverInfo"`
		Capabilities map[string]any `json:"capabilities"`
	}
	if err := json.Unmarshal(resp[0].Result, &result); err != nil {
		t.Fatalf("decode result: %v", err)
	}
	if result.ProtocolVersion != protocolVersion {
		t.Errorf("protocolVersion = %q, want %q", result.ProtocolVersion, protocolVersion)
	}
	if result.ServerInfo.Name != serverName {
		t.Errorf("serverInfo.name = %q, want %q", result.ServerInfo.Name, serverName)
	}
	if _, ok := result.Capabilities["tools"]; !ok {
		t.Error("expected 'tools' capability to be advertised")
	}
}

func TestMCP_NotificationProducesNoResponse(t *testing.T) {
	// When a notification (no id) is sent
	resp := serve(t, `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
	// Then the server replies with nothing
	if len(resp) != 0 {
		t.Errorf("expected no response to a notification, got %d", len(resp))
	}
}

func TestMCP_ToolsList(t *testing.T) {
	// When the client lists tools
	resp := serve(t, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	var result struct {
		Tools []struct {
			Name        string         `json:"name"`
			Description string         `json:"description"`
			InputSchema map[string]any `json:"inputSchema"`
		} `json:"tools"`
	}
	if err := json.Unmarshal(resp[0].Result, &result); err != nil {
		t.Fatalf("decode result: %v", err)
	}
	// Then all seven tools are advertised with schemas
	if len(result.Tools) != 7 {
		t.Errorf("got %d tools, want 7", len(result.Tools))
	}
	for _, tool := range result.Tools {
		if tool.Name == "" || tool.Description == "" {
			t.Errorf("tool with empty name/description: %+v", tool)
		}
		if tool.InputSchema["type"] != "object" {
			t.Errorf("tool %q has malformed inputSchema", tool.Name)
		}
	}
}

func TestMCP_ToolCall(t *testing.T) {
	// When the client calls a tool
	req := `{"jsonrpc":"2.0","id":3,"method":"tools/call",` +
		`"params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019}}}`
	resp := serve(t, req)
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	var result struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(resp[0].Result, &result); err != nil {
		t.Fatalf("decode result: %v", err)
	}
	// Then text content with the expected answer is returned
	if result.IsError {
		t.Error("tool call unexpectedly reported isError")
	}
	if len(result.Content) == 0 || result.Content[0].Type != "text" {
		t.Fatalf("expected text content, got %+v", result.Content)
	}
	if !strings.Contains(result.Content[0].Text, "Flamengo") {
		t.Errorf("standings text missing Flamengo:\n%s", result.Content[0].Text)
	}
}

func TestMCP_ToolCallUnknownTool(t *testing.T) {
	// When an unknown tool is called
	req := `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"bogus","arguments":{}}}`
	resp := serve(t, req)
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	// Then a JSON-RPC error is returned
	if resp[0].Error == nil {
		t.Error("expected an error for an unknown tool")
	}
}

func TestMCP_ToolHandlerErrorIsReportedAsContent(t *testing.T) {
	// When a tool handler fails validation (missing required arg)
	req := `{"jsonrpc":"2.0","id":5,"method":"tools/call",` +
		`"params":{"name":"team_stats","arguments":{}}}`
	resp := serve(t, req)
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	// Then it is surfaced as MCP error content, not a transport error
	if resp[0].Error != nil {
		t.Errorf("handler error should not be a transport error: %+v", resp[0].Error)
	}
	var result struct {
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(resp[0].Result, &result); err != nil {
		t.Fatalf("decode result: %v", err)
	}
	if !result.IsError {
		t.Error("expected isError=true for a failed handler")
	}
}

func TestMCP_InvalidJSON(t *testing.T) {
	// When malformed JSON is received
	resp := serve(t, `{not valid json`)
	if len(resp) != 1 {
		t.Fatalf("expected 1 error response, got %d", len(resp))
	}
	// Then a parse error is reported
	if resp[0].Error == nil || resp[0].Error.Code != errParse {
		t.Errorf("expected parse error, got %+v", resp[0].Error)
	}
}

func TestMCP_UnknownMethod(t *testing.T) {
	resp := serve(t, `{"jsonrpc":"2.0","id":9,"method":"does/not/exist"}`)
	if len(resp) != 1 {
		t.Fatalf("expected 1 response, got %d", len(resp))
	}
	if resp[0].Error == nil || resp[0].Error.Code != errMethodNotFound {
		t.Errorf("expected method-not-found error, got %+v", resp[0].Error)
	}
}
