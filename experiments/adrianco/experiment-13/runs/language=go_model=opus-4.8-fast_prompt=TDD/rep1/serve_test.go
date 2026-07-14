// Package main — Brazilian Soccer MCP Server.
//
// serve_test.go: Integration test for the newline-delimited JSON-RPC transport
// loop, driving the server over in-memory pipes the way a real MCP client would
// over stdio.
package main

import (
	"bufio"
	"encoding/json"
	"strings"
	"testing"
)

func TestServeProcessesMultipleMessages(t *testing.T) {
	s := newServer(t)
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}`,
	}, "\n") + "\n"

	var out strings.Builder
	if err := s.Serve(strings.NewReader(input), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}

	// Three responses expected (the notification yields none).
	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
	var ids []float64
	for scanner.Scan() {
		line := scanner.Text()
		if strings.TrimSpace(line) == "" {
			continue
		}
		var resp map[string]any
		if err := json.Unmarshal([]byte(line), &resp); err != nil {
			t.Fatalf("response line not valid JSON: %q: %v", line, err)
		}
		if id, ok := resp["id"].(float64); ok {
			ids = append(ids, id)
		}
	}
	if len(ids) != 3 {
		t.Fatalf("expected 3 id-bearing responses, got %d (%v)", len(ids), ids)
	}
	if ids[0] != 1 || ids[1] != 2 || ids[2] != 3 {
		t.Errorf("responses out of order: %v", ids)
	}
}
