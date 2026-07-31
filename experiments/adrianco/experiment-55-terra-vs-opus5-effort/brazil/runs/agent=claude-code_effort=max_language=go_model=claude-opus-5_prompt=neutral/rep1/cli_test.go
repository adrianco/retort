// cli_test.go builds the real binary and drives it the way a user and an MCP
// client would: the command line modes, then a full protocol session over the
// process's stdin and stdout.
package main

import (
	"bufio"
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
)

// buildBinary compiles the command once per test run.
func buildBinary(t *testing.T) string {
	t.Helper()
	if testing.Short() {
		t.Skip("skipping the binary build in short mode")
	}
	bin := filepath.Join(t.TempDir(), "brazilian-soccer-mcp")
	if runtime.GOOS == "windows" {
		bin += ".exe"
	}
	cmd := exec.Command("go", "build", "-o", bin, ".")
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("go build: %v\n%s", err, out)
	}
	return bin
}

func TestCLIVersionAndToolList(t *testing.T) {
	bin := buildBinary(t)

	out, err := exec.Command(bin, "-version").Output()
	if err != nil {
		t.Fatalf("-version: %v", err)
	}
	if !strings.Contains(string(out), "brazilian-soccer") {
		t.Errorf("-version printed %q", out)
	}

	out, err = exec.Command(bin, "-list-tools", "-quiet").Output()
	if err != nil {
		t.Fatalf("-list-tools: %v", err)
	}
	listing := string(out)
	for _, want := range []string{"search_matches", "head_to_head", "standings", "search_players", "graph_neighbors", "* = required"} {
		if !strings.Contains(listing, want) {
			t.Errorf("-list-tools does not mention %q", want)
		}
	}
}

func TestCLIToolMode(t *testing.T) {
	bin := buildBinary(t)

	out, err := exec.Command(bin, "-quiet", "-tool", "standings", "-args", `{"season":2019}`).Output()
	if err != nil {
		t.Fatalf("-tool standings: %v", err)
	}
	answer := string(out)
	for _, want := range []string{"Flamengo", "90 pts", "Champion"} {
		if !strings.Contains(answer, want) {
			t.Errorf("the answer is missing %q:\n%s", want, answer)
		}
	}

	// JSON mode returns the same result as structured data.
	out, err = exec.Command(bin, "-quiet", "-json", "-tool", "list_competitions").Output()
	if err != nil {
		t.Fatalf("-json: %v", err)
	}
	var result struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		StructuredContent map[string]any `json:"structuredContent"`
	}
	if err := json.Unmarshal(out, &result); err != nil {
		t.Fatalf("-json did not print JSON: %v\n%s", err, out)
	}
	if len(result.Content) == 0 || result.StructuredContent == nil {
		t.Errorf("-json result = %+v", result)
	}

	// A tool that refuses exits non-zero and explains itself.
	cmd := exec.Command(bin, "-quiet", "-tool", "team_stats", "-args", `{"team":"Nonexistent United"}`)
	out, err = cmd.CombinedOutput()
	if err == nil {
		t.Error("a failing tool should exit non-zero")
	}
	if !strings.Contains(string(out), "Nonexistent United") {
		t.Errorf("the failure should name the club:\n%s", out)
	}
}

// TestCLIStdioSession is the acceptance test for the deliverable: a client
// speaking MCP to the process over stdin and stdout.
func TestCLIStdioSession(t *testing.T) {
	bin := buildBinary(t)

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, bin, "-quiet")
	stdin, err := cmd.StdinPipe()
	if err != nil {
		t.Fatal(err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	defer cmd.Process.Kill()

	reader := bufio.NewReader(stdout)
	send := func(v any) {
		raw, _ := json.Marshal(v)
		if _, err := stdin.Write(append(raw, '\n')); err != nil {
			t.Fatalf("write: %v", err)
		}
	}
	receive := func() map[string]any {
		line, err := reader.ReadBytes('\n')
		if err != nil {
			t.Fatalf("read: %v", err)
		}
		var msg map[string]any
		if err := json.Unmarshal(line, &msg); err != nil {
			t.Fatalf("the server wrote a non-JSON line: %q", line)
		}
		if e, ok := msg["error"]; ok {
			t.Fatalf("server error: %v", e)
		}
		return msg["result"].(map[string]any)
	}

	send(map[string]any{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": map[string]any{
		"protocolVersion": "2025-06-18",
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": "cli-test", "version": "1"},
	}})
	init := receive()
	if init["protocolVersion"] != "2025-06-18" {
		t.Errorf("negotiated %v", init["protocolVersion"])
	}

	send(map[string]any{"jsonrpc": "2.0", "method": "notifications/initialized"})

	send(map[string]any{"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
	if tools := receive()["tools"].([]any); len(tools) < 15 {
		t.Errorf("only %d tools", len(tools))
	}

	send(map[string]any{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": map[string]any{
		"name":      "head_to_head",
		"arguments": map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 3},
	}})
	result := receive()
	text := result["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "Fla-Flu") {
		t.Errorf("head-to-head over stdio:\n%s", text)
	}

	stdin.Close()
	if err := cmd.Wait(); err != nil {
		t.Errorf("the server exited with %v", err)
	}
}

func TestFirstLineAndSortedKeys(t *testing.T) {
	if got := firstLine("one\ntwo"); got != "one" {
		t.Errorf("firstLine = %q", got)
	}
	if got := firstLine("single"); got != "single" {
		t.Errorf("firstLine = %q", got)
	}
	keys := sortedKeys(map[string]*mcp.Prop{"b": nil, "a": nil, "c": nil})
	if strings.Join(keys, "") != "abc" {
		t.Errorf("sortedKeys = %v", keys)
	}
}
