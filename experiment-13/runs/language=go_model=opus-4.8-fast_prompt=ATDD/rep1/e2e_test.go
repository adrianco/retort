package app_test

import (
	"bufio"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

// TestEndToEndOverStdio builds the real bsmcp binary and drives it over actual
// stdin/stdout pipes, exactly as an MCP client would, to prove the production
// stdio transport works end-to-end against on-disk CSV data.
func TestEndToEndOverStdio(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping binary build in -short mode")
	}

	dir := t.TempDir()
	bin := filepath.Join(dir, "bsmcp")
	build := exec.Command("go", "build", "-o", bin, "./cmd/bsmcp")
	if out, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build failed: %v\n%s", err, out)
	}

	// Seed a tiny dataset on disk.
	dataDir := filepath.Join(dir, "data")
	kaggle := filepath.Join(dataDir, "kaggle")
	if err := os.MkdirAll(kaggle, 0o755); err != nil {
		t.Fatal(err)
	}
	header := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"` + "\n"
	rows := `2023-09-03 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2023,22` + "\n"
	if err := os.WriteFile(filepath.Join(kaggle, "Brasileirao_Matches.csv"), []byte(header+rows), 0o644); err != nil {
		t.Fatal(err)
	}

	cmd := exec.Command(bin, "-data", dataDir)
	stdin, err := cmd.StdinPipe()
	if err != nil {
		t.Fatal(err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		_ = stdin.Close()
		_ = cmd.Wait()
	})

	enc := json.NewEncoder(stdin)
	dec := json.NewDecoder(bufio.NewReader(stdout))

	send := func(v any) {
		if err := enc.Encode(v); err != nil {
			t.Fatalf("send: %v", err)
		}
	}
	read := func() rpcResponse {
		var resp rpcResponse
		done := make(chan error, 1)
		go func() { done <- dec.Decode(&resp) }()
		select {
		case err := <-done:
			if err != nil {
				t.Fatalf("read: %v", err)
			}
		case <-time.After(15 * time.Second):
			t.Fatal("timed out reading from binary")
		}
		return resp
	}

	send(map[string]any{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": map[string]any{}})
	if r := read(); r.Error != nil {
		t.Fatalf("initialize error: %s", r.Error.Message)
	}
	send(map[string]any{"jsonrpc": "2.0", "method": "notifications/initialized", "params": map[string]any{}})

	send(map[string]any{
		"jsonrpc": "2.0", "id": 2, "method": "tools/call",
		"params": map[string]any{"name": "find_matches", "arguments": map[string]any{"team": "Flamengo", "opponent": "Fluminense"}},
	})
	resp := read()
	if resp.Error != nil {
		t.Fatalf("tools/call error: %s", resp.Error.Message)
	}
	var result struct {
		Content []struct {
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("bad result: %v", err)
	}
	if result.IsError || len(result.Content) == 0 {
		t.Fatalf("unexpected tool error result: %+v", result)
	}
	var payload findMatchesResult
	if err := json.Unmarshal([]byte(result.Content[0].Text), &payload); err != nil {
		t.Fatalf("payload: %v", err)
	}
	if payload.Count != 1 {
		t.Fatalf("expected 1 Fla-Flu match over stdio, got %d", payload.Count)
	}
	if payload.HeadToHead == nil || payload.HeadToHead.TeamWins != 1 {
		t.Fatalf("expected head-to-head with 1 Flamengo win, got %+v", payload.HeadToHead)
	}
}
