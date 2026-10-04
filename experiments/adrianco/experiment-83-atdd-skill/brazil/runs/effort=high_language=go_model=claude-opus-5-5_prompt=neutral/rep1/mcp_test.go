// mcp_test.go — JSON-RPC / MCP protocol tests, in-process and against the
// compiled binary over real stdio.
package main

import (
	"bufio"
	"encoding/json"
	"io"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func rpc(t *testing.T, srv *Server, msg string) map[string]any {
	t.Helper()
	out := srv.HandleMessage([]byte(msg))
	if out == nil {
		t.Fatalf("no response to %s", msg)
	}
	var resp map[string]any
	if err := json.Unmarshal(out, &resp); err != nil {
		t.Fatalf("bad JSON response %s: %v", out, err)
	}
	if resp["jsonrpc"] != "2.0" {
		t.Errorf("jsonrpc = %v", resp["jsonrpc"])
	}
	return resp
}

func TestMCPInitialize(t *testing.T) {
	srv := NewServer(testStore(t))
	resp := rpc(t, srv, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}`)
	res := resp["result"].(map[string]any)
	if res["protocolVersion"] != "2024-11-05" {
		t.Errorf("protocolVersion = %v", res["protocolVersion"])
	}
	if _, ok := res["capabilities"].(map[string]any)["tools"]; !ok {
		t.Error("tools capability missing")
	}
	if res["serverInfo"].(map[string]any)["name"] != serverName {
		t.Error("serverInfo")
	}
	// Unknown versions get the latest supported one.
	resp = rpc(t, srv, `{"jsonrpc":"2.0","id":2,"method":"initialize","params":{"protocolVersion":"1999-01-01"}}`)
	if v := resp["result"].(map[string]any)["protocolVersion"]; v != latestProtocol {
		t.Errorf("fallback protocolVersion = %v", v)
	}
	if out := srv.HandleMessage([]byte(`{"jsonrpc":"2.0","method":"notifications/initialized"}`)); out != nil {
		t.Errorf("notification produced a response: %s", out)
	}
}

func TestMCPToolsList(t *testing.T) {
	srv := NewServer(testStore(t))
	resp := rpc(t, srv, `{"jsonrpc":"2.0","id":"a","method":"tools/list"}`)
	if resp["id"] != "a" {
		t.Errorf("id not echoed: %v", resp["id"])
	}
	tools := resp["result"].(map[string]any)["tools"].([]any)
	if len(tools) < 10 {
		t.Fatalf("%d tools", len(tools))
	}
	names := map[string]bool{}
	for _, x := range tools {
		tool := x.(map[string]any)
		name := tool["name"].(string)
		names[name] = true
		if tool["description"].(string) == "" {
			t.Errorf("%s has no description", name)
		}
		schema := tool["inputSchema"].(map[string]any)
		if schema["type"] != "object" {
			t.Errorf("%s schema type = %v", name, schema["type"])
		}
		if req, ok := schema["required"].([]any); ok {
			props := schema["properties"].(map[string]any)
			for _, r := range req {
				if _, ok := props[r.(string)]; !ok {
					t.Errorf("%s requires undeclared %v", name, r)
				}
			}
		}
	}
	for _, n := range []string{"search_matches", "head_to_head", "team_record", "standings", "search_players", "player_profile", "competition_stats", "biggest_wins", "knockout_bracket", "rank_teams"} {
		if !names[n] {
			t.Errorf("tool %s missing", n)
		}
	}
}

func TestMCPToolsCall(t *testing.T) {
	srv := NewServer(testStore(t))
	resp := rpc(t, srv, `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":3}}}`)
	res := resp["result"].(map[string]any)
	if res["isError"] != false {
		t.Errorf("isError = %v", res["isError"])
	}
	content := res["content"].([]any)[0].(map[string]any)
	if content["type"] != "text" || !strings.Contains(content["text"].(string), "1. Flamengo - 90 pts") {
		t.Errorf("content = %v", content)
	}
	// Arguments given as strings are accepted.
	resp = rpc(t, srv, `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_record","arguments":{"team":"corinthians","season":"2022","venue":"home","competition":"brasileirao"}}}`)
	text := resp["result"].(map[string]any)["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "Matches: 19") {
		t.Errorf("string args: %s", text)
	}
	// Tool-level failures are reported in the result with isError.
	resp = rpc(t, srv, `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"team_record","arguments":{"team":"Xyzzy"}}}`)
	res = resp["result"].(map[string]any)
	if res["isError"] != true || !strings.Contains(res["content"].([]any)[0].(map[string]any)["text"].(string), "no team matching") {
		t.Errorf("tool error result = %v", res)
	}
}

func TestMCPProtocolErrors(t *testing.T) {
	srv := NewServer(testStore(t))
	code := func(resp map[string]any) float64 {
		e, ok := resp["error"].(map[string]any)
		if !ok {
			t.Fatalf("expected error, got %v", resp)
		}
		return e["code"].(float64)
	}
	if c := code(rpc(t, srv, `{not json`)); c != -32700 {
		t.Errorf("parse error code %v", c)
	}
	if c := code(rpc(t, srv, `{"jsonrpc":"2.0","id":1,"method":"bogus/method"}`)); c != -32601 {
		t.Errorf("method not found code %v", c)
	}
	if c := code(rpc(t, srv, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nope"}}`)); c != -32602 {
		t.Errorf("unknown tool code %v", c)
	}
	if c := code(rpc(t, srv, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":"bad"}`)); c != -32602 {
		t.Errorf("bad params code %v", c)
	}
	resp := rpc(t, srv, `{"jsonrpc":"2.0","id":9,"method":"ping"}`)
	if _, ok := resp["result"]; !ok {
		t.Errorf("ping: %v", resp)
	}
}

func TestMCPBatch(t *testing.T) {
	srv := NewServer(testStore(t))
	out := srv.HandleMessage([]byte(`[{"jsonrpc":"2.0","id":1,"method":"ping"},{"jsonrpc":"2.0","method":"notifications/initialized"},{"jsonrpc":"2.0","id":2,"method":"tools/list"}]`))
	var resps []map[string]any
	if err := json.Unmarshal(out, &resps); err != nil {
		t.Fatalf("batch response %s: %v", out, err)
	}
	if len(resps) != 2 {
		t.Errorf("%d responses, want 2", len(resps))
	}
}

// TestServeStdioStream drives Serve through pipes the way an MCP client does.
func TestServeStdioStream(t *testing.T) {
	srv := NewServer(testStore(t))
	inR, inW := io.Pipe()
	outR, outW := io.Pipe()
	done := make(chan error, 1)
	go func() { done <- srv.Serve(inR, outW); outW.Close() }()
	reader := bufio.NewReader(outR)
	send := func(msg string) map[string]any {
		t.Helper()
		if _, err := io.WriteString(inW, msg+"\n"); err != nil {
			t.Fatal(err)
		}
		line, err := reader.ReadString('\n')
		if err != nil {
			t.Fatal(err)
		}
		var resp map[string]any
		if err := json.Unmarshal([]byte(line), &resp); err != nil {
			t.Fatalf("%q: %v", line, err)
		}
		return resp
	}
	send(`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`)
	io.WriteString(inW, `{"jsonrpc":"2.0","method":"notifications/initialized"}`+"\n")
	resp := send(`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Grêmio","team_b":"Internacional"}}}`)
	if resp["id"].(float64) != 2 {
		t.Errorf("id = %v", resp["id"])
	}
	text := resp["result"].(map[string]any)["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "Grenal") {
		t.Errorf("text = %s", text)
	}
	inW.Close()
	select {
	case err := <-done:
		if err != nil {
			t.Errorf("Serve: %v", err)
		}
	case <-time.After(5 * time.Second):
		t.Error("Serve did not return on EOF")
	}
}

// TestBinaryOverStdio builds the server and talks to it as a subprocess.
func TestBinaryOverStdio(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping binary build in -short mode")
	}
	bin := filepath.Join(t.TempDir(), "brsoccer")
	if out, err := exec.Command("go", "build", "-o", bin, ".").CombinedOutput(); err != nil {
		t.Fatalf("build: %v\n%s", err, out)
	}
	cmd := exec.Command(bin, "-quiet", "-data", "data/kaggle")
	cmd.Stdin = strings.NewReader(strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Fluminense","limit":3}}}`,
	}, "\n") + "\n")
	start := time.Now()
	out, err := cmd.Output()
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	t.Logf("startup + 3 requests: %s", time.Since(start))
	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	if len(lines) != 3 {
		t.Fatalf("got %d response lines:\n%s", len(lines), out)
	}
	if !strings.Contains(lines[2], "Fla-Flu") {
		t.Errorf("tools/call response: %s", lines[2])
	}

	// CLI mode.
	out, err = exec.Command(bin, "-quiet", "-data", "data/kaggle", "call", "standings", `{"season":2019,"limit":1}`).Output()
	if err != nil || !strings.Contains(string(out), "Flamengo - 90 pts") {
		t.Errorf("call mode: %v\n%s", err, out)
	}
}
