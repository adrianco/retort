// End-to-end test of the stdio transport: drives the server exactly as an MCP
// client would, feeding newline-delimited JSON-RPC on the input stream and
// reading newline-delimited responses back -- proving real protocol compliance
// over the wire, not just in-process dispatch.
package main

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"brazilian-soccer-mcp/mcp"
)

func TestStdioRoundTrip(t *testing.T) {
	dir := t.TempDir()
	csv := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2023-09-03 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2023,22
`
	if err := os.WriteFile(filepath.Join(dir, "Brasileirao_Matches.csv"), []byte(csv), 0o644); err != nil {
		t.Fatal(err)
	}
	srv, err := mcp.NewServer(dir)
	if err != nil {
		t.Fatal(err)
	}

	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize"}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Flamengo"}}}`,
	}, "\n") + "\n"

	var out strings.Builder
	if err := serve(srv, strings.NewReader(input), &out); err != nil {
		t.Fatalf("serve: %v", err)
	}

	// The notification produces no line; we expect exactly two responses.
	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	var lines []string
	for scanner.Scan() {
		if strings.TrimSpace(scanner.Text()) != "" {
			lines = append(lines, scanner.Text())
		}
	}
	if len(lines) != 2 {
		t.Fatalf("expected 2 responses (notification has none), got %d:\n%s", len(lines), out.String())
	}

	// Second response should carry the Flamengo match through the protocol.
	var resp struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[1]), &resp); err != nil {
		t.Fatalf("decode call response: %v", err)
	}
	if len(resp.Result.Content) == 0 || !strings.Contains(resp.Result.Content[0].Text, "Flamengo") {
		t.Errorf("expected Flamengo match in stdio response, got %q", lines[1])
	}
}
