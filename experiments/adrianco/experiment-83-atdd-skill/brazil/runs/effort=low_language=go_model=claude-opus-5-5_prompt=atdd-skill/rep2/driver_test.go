package main

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
	"sync"
	"testing"
)

// mcpDriver is the protocol driver: it talks to the server only through
// the MCP JSON-RPC stdio protocol, its public interface.
type mcpDriver struct {
	mu  sync.Mutex
	in  io.Writer
	out *bufio.Reader
	id  int
}

var (
	driverOnce sync.Once
	driver     *mcpDriver
	driverErr  error
)

func sharedDriver(t *testing.T) *mcpDriver {
	t.Helper()
	driverOnce.Do(func() {
		store, err := Load("data/kaggle")
		if err != nil {
			driverErr = err
			return
		}
		cr, sw := io.Pipe()
		sr, cw := io.Pipe()
		go NewServer(store).Serve(sr, sw)
		driver = &mcpDriver{in: cw, out: bufio.NewReader(cr)}
		var res map[string]any
		driverErr = driver.rpc("initialize", map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{},
			"clientInfo": map[string]any{"name": "acceptance", "version": "1"}}, &res)
		if driverErr == nil {
			driver.notify("notifications/initialized")
		}
	})
	if driverErr != nil {
		t.Fatalf("could not start soccer server: %v", driverErr)
	}
	return driver
}

func (d *mcpDriver) notify(method string) {
	b, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "method": method})
	d.in.Write(append(b, '\n'))
}

type rpcError struct{ msg string }

func (e rpcError) Error() string { return e.msg }

func (d *mcpDriver) rpc(method string, params any, result any) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.id++
	b, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "id": d.id, "method": method, "params": params})
	if _, err := d.in.Write(append(b, '\n')); err != nil {
		return err
	}
	line, err := d.out.ReadBytes('\n')
	if err != nil {
		return err
	}
	var resp struct {
		Result json.RawMessage           `json:"result"`
		Error  *struct{ Message string } `json:"error"`
	}
	if err := json.Unmarshal(line, &resp); err != nil {
		return err
	}
	if resp.Error != nil {
		return rpcError{resp.Error.Message}
	}
	return json.Unmarshal(resp.Result, result)
}

func (d *mcpDriver) callTool(t *testing.T, tool string, args map[string]any) string {
	t.Helper()
	var res struct {
		Content []struct{ Text string } `json:"content"`
		IsError bool                    `json:"isError"`
	}
	if err := d.rpc("tools/call", map[string]any{"name": tool, "arguments": args}, &res); err != nil {
		t.Fatalf("asking %s failed: %v", tool, err)
	}
	var sb strings.Builder
	for _, c := range res.Content {
		sb.WriteString(c.Text)
	}
	if res.IsError {
		t.Fatalf("server could not answer %s: %s", tool, sb.String())
	}
	return sb.String()
}

func (d *mcpDriver) assertMentions(t *testing.T, answer string, texts ...string) {
	t.Helper()
	for _, x := range texts {
		if !strings.Contains(answer, x) {
			t.Fatalf("expected answer to mention %q, got:\n%s", x, answer)
		}
	}
}

func (d *mcpDriver) assertNotMentions(t *testing.T, answer string, texts ...string) {
	t.Helper()
	for _, x := range texts {
		if strings.Contains(answer, x) {
			t.Fatalf("expected answer not to mention %q, got:\n%s", x, answer)
		}
	}
}
