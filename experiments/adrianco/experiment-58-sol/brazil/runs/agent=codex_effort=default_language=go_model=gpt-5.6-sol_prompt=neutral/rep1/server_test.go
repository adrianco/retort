package main

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"
)

func TestMCPInitializeListAndCall(t *testing.T) {
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"team_statistics","arguments":{"team":"Flamengo","season":2023}}}`,
	}, "\n") + "\n"
	var out bytes.Buffer
	if err := NewServer(testStore()).Serve(context.Background(), strings.NewReader(input), &out); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 3 {
		t.Fatalf("got %d responses, want 3 (notification must be silent): %s", len(lines), out.String())
	}
	var init struct {
		Result struct {
			ProtocolVersion string `json:"protocolVersion"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[0]), &init); err != nil || init.Result.ProtocolVersion != "2024-11-05" {
		t.Fatalf("bad initialize response: %s (%v)", lines[0], err)
	}
	var listed struct {
		Result struct {
			Tools []tool `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[1]), &listed); err != nil || len(listed.Result.Tools) != 9 {
		t.Fatalf("bad tools/list response: %s (%v)", lines[1], err)
	}
	var called struct {
		Result struct {
			IsError    bool           `json:"isError"`
			Structured map[string]any `json:"structuredContent"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[2]), &called); err != nil || called.Result.IsError || called.Result.Structured["result"] == nil {
		t.Fatalf("bad tools/call response: %s (%v)", lines[2], err)
	}
}

func TestMCPCurrentDiscoveryAndStatelessCall(t *testing.T) {
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":"discover","method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"test","version":"1"},"io.modelcontextprotocol/clientCapabilities":{}}}}`,
		`{"jsonrpc":"2.0","id":"call","method":"tools/call","params":{"name":"search_players","arguments":{"nationality":"Brasil","limit":1},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"test","version":"1"}}}}`,
	}, "\n") + "\n"
	var out bytes.Buffer
	if err := NewServer(testStore()).Serve(context.Background(), strings.NewReader(input), &out); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("got %d responses: %s", len(lines), out.String())
	}
	var discovery struct {
		Result struct {
			ResultType string   `json:"resultType"`
			Supported  []string `json:"supportedVersions"`
			CacheScope string   `json:"cacheScope"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[0]), &discovery); err != nil || discovery.Result.ResultType != "complete" || len(discovery.Result.Supported) == 0 || discovery.Result.Supported[0] != protocolVersion || discovery.Result.CacheScope != "public" {
		t.Fatalf("bad discovery response: %s (%v)", lines[0], err)
	}
}

func TestMCPToolValidationAndProtocolErrors(t *testing.T) {
	s := NewServer(testStore())
	result, rpcErr := s.handle(rpcRequest{Method: "tools/call", Params: json.RawMessage(`{"name":"team_statistics","arguments":{}}`)})
	if rpcErr != nil || !result.(map[string]any)["isError"].(bool) {
		t.Fatalf("expected tool-level validation error: %#v %#v", result, rpcErr)
	}
	_, rpcErr = s.handle(rpcRequest{Method: "no/such/method"})
	if rpcErr == nil || rpcErr.Code != -32601 {
		t.Fatalf("expected method-not-found error: %#v", rpcErr)
	}
	_, rpcErr = s.handle(rpcRequest{Method: "tools/call", Params: json.RawMessage(`{"name":"no_such_tool","arguments":{}}`)})
	if rpcErr == nil || rpcErr.Code != -32602 {
		t.Fatalf("expected unknown-tool protocol error: %#v", rpcErr)
	}
}
