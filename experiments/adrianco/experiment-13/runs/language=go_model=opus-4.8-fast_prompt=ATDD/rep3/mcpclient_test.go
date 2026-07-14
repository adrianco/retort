// Context: Test harness — a minimal in-process MCP client used by the
// acceptance tests. It talks to the System Under Test ONLY through the public
// MCP stdio protocol (newline-delimited JSON-RPC 2.0): it performs the
// initialize handshake, lists tools, and calls tools. No acceptance test is
// allowed to reach into the server, store, or any internal type directly — the
// MCP protocol is the only door in. This keeps the suite black-box and faithful
// to how a real LLM client would drive the server.
package main

import (
	"bufio"
	"context"
	"encoding/json"
	"io"
	"testing"
	"time"
)

// testClient drives a Server over an in-memory pipe using the MCP stdio framing.
type testClient struct {
	t      *testing.T
	enc    *json.Encoder
	in     io.WriteCloser
	out    *bufio.Reader
	nextID int
	cancel context.CancelFunc
	done   chan struct{}
}

// startServer boots a Server loading the given data directory and returns a
// connected MCP client that has already completed the initialize handshake.
func startServer(t *testing.T, dataDir string) *testClient {
	t.Helper()

	store := NewStore()
	if err := store.LoadDir(dataDir); err != nil {
		t.Fatalf("loading data dir %q: %v", dataDir, err)
	}
	srv := NewServer(store)

	clientReader, clientWriter := io.Pipe() // client -> server
	serverReader, serverWriter := io.Pipe() // server -> client

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		defer close(done)
		_ = srv.Serve(ctx, clientReader, serverWriter)
	}()

	c := &testClient{
		t:      t,
		enc:    json.NewEncoder(clientWriter),
		in:     clientWriter,
		out:    bufio.NewReader(serverReader),
		nextID: 1,
		cancel: cancel,
		done:   done,
	}
	t.Cleanup(func() {
		_ = clientWriter.Close()
		cancel()
		select {
		case <-done:
		case <-time.After(2 * time.Second):
		}
	})

	c.initialize()
	return c
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  json.RawMessage `json:"result"`
	Error   *rpcError       `json:"error"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func (c *testClient) request(method string, params any) rpcResponse {
	c.t.Helper()
	id := c.nextID
	c.nextID++
	req := map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"method":  method,
	}
	if params != nil {
		req["params"] = params
	}
	if err := c.enc.Encode(req); err != nil {
		c.t.Fatalf("encoding request %s: %v", method, err)
	}
	line, err := c.out.ReadBytes('\n')
	if err != nil {
		c.t.Fatalf("reading response to %s: %v", method, err)
	}
	var resp rpcResponse
	if err := json.Unmarshal(line, &resp); err != nil {
		c.t.Fatalf("decoding response to %s: %v (raw: %s)", method, err, line)
	}
	return resp
}

// notify sends a JSON-RPC notification (no id, no response expected).
func (c *testClient) notify(method string, params any) {
	c.t.Helper()
	req := map[string]any{"jsonrpc": "2.0", "method": method}
	if params != nil {
		req["params"] = params
	}
	if err := c.enc.Encode(req); err != nil {
		c.t.Fatalf("encoding notification %s: %v", method, err)
	}
}

func (c *testClient) initialize() {
	c.t.Helper()
	resp := c.request("initialize", map[string]any{
		"protocolVersion": "2024-11-05",
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": "acceptance-test", "version": "1.0"},
	})
	if resp.Error != nil {
		c.t.Fatalf("initialize returned error: %v", resp.Error.Message)
	}
	var result struct {
		ServerInfo struct {
			Name string `json:"name"`
		} `json:"serverInfo"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		c.t.Fatalf("decoding initialize result: %v", err)
	}
	if result.ServerInfo.Name == "" {
		c.t.Fatalf("initialize result missing serverInfo.name")
	}
	c.notify("notifications/initialized", nil)
}

type toolInfo struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"inputSchema"`
}

func (c *testClient) listTools() []toolInfo {
	c.t.Helper()
	resp := c.request("tools/list", nil)
	if resp.Error != nil {
		c.t.Fatalf("tools/list error: %v", resp.Error.Message)
	}
	var result struct {
		Tools []toolInfo `json:"tools"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		c.t.Fatalf("decoding tools/list: %v", err)
	}
	return result.Tools
}

// callTool invokes an MCP tool and returns the concatenated text content plus
// whether the call was flagged as an error result.
func (c *testClient) callTool(name string, args map[string]any) (string, bool) {
	c.t.Helper()
	resp := c.request("tools/call", map[string]any{
		"name":      name,
		"arguments": args,
	})
	if resp.Error != nil {
		c.t.Fatalf("tools/call %s protocol error: %v", name, resp.Error.Message)
	}
	var result struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		c.t.Fatalf("decoding tools/call %s: %v", name, err)
	}
	text := ""
	for _, block := range result.Content {
		text += block.Text
	}
	return text, result.IsError
}

// callRaw invokes tools/call and returns the raw JSON-RPC response so tests can
// assert on protocol-level errors for unknown tools/methods.
func (c *testClient) rawRequest(method string, params any) rpcResponse {
	return c.request(method, params)
}
