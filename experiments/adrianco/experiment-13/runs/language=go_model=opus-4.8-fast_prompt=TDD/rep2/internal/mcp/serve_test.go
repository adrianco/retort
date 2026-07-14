package mcp

import (
	"bufio"
	"encoding/json"
	"strings"
	"testing"
)

func TestServeStdioRoundTrip(t *testing.T) {
	s := testServer()
	// Two requests and one notification, newline-delimited.
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
	}, "\n") + "\n"

	var out strings.Builder
	if err := s.Serve(strings.NewReader(input), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}

	// Exactly two responses (the notification yields none).
	sc := bufio.NewScanner(strings.NewReader(out.String()))
	var ids []float64
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var r struct {
			ID json.Number `json:"id"`
		}
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			t.Fatalf("bad response line %q: %v", line, err)
		}
		f, _ := r.ID.Float64()
		ids = append(ids, f)
	}
	if len(ids) != 2 {
		t.Fatalf("got %d responses, want 2: %s", len(ids), out.String())
	}
	if ids[0] != 1 || ids[1] != 2 {
		t.Errorf("response ids = %v, want [1 2]", ids)
	}
}
