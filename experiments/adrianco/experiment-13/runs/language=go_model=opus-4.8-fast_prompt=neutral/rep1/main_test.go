package main

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"brazilian-soccer-mcp/mcp"
	"brazilian-soccer-mcp/soccer"
)

func loadStore(t *testing.T) *soccer.Store {
	t.Helper()
	if _, err := os.Stat("data/kaggle/Brasileirao_Matches.csv"); err != nil {
		t.Skipf("datasets not available: %v", err)
	}
	store, _, err := soccer.LoadAll("data/kaggle")
	if err != nil {
		t.Fatalf("LoadAll: %v", err)
	}
	return store
}

// callTool drives the full MCP stack: register tools, send a tools/call request
// over a pipe, and return the text content of the response.
func callTool(t *testing.T, store *soccer.Store, name string, args map[string]any) string {
	t.Helper()
	srv := mcp.NewServer(serverName, serverVersion)
	registerTools(srv, store)

	req := map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{"name": name, "arguments": args},
	}
	line, _ := json.Marshal(req)
	var out strings.Builder
	if err := srv.Serve(strings.NewReader(string(line)+"\n"), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resp struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
			IsError bool `json:"isError"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(strings.TrimSpace(out.String())), &resp); err != nil {
		t.Fatalf("decode response: %v\n%s", err, out.String())
	}
	if resp.Result.IsError {
		t.Fatalf("tool %s returned error: %s", name, resp.Result.Content[0].Text)
	}
	if len(resp.Result.Content) == 0 {
		t.Fatalf("tool %s returned no content", name)
	}
	return resp.Result.Content[0].Text
}

func TestToolsRegistered(t *testing.T) {
	srv := mcp.NewServer(serverName, serverVersion)
	store := soccer.LoadEmptyForTest()
	registerTools(srv, store)

	var out strings.Builder
	if err := srv.Serve(strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`+"\n"), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resp struct {
		Result struct {
			Tools []struct {
				Name string `json:"name"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(strings.TrimSpace(out.String())), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(resp.Result.Tools) != 12 {
		t.Errorf("want 12 tools registered, got %d", len(resp.Result.Tools))
	}
	want := map[string]bool{
		"search_matches": true, "head_to_head": true, "team_record": true,
		"team_competitions": true, "standings": true, "competition_stats": true,
		"biggest_wins": true, "top_scoring_teams": true, "search_players": true,
		"player_info": true, "club_players": true, "dataset_overview": true,
	}
	for _, tl := range resp.Result.Tools {
		delete(want, tl.Name)
	}
	if len(want) != 0 {
		t.Errorf("missing tools: %v", want)
	}
}

func TestEndToEndQueries(t *testing.T) {
	store := loadStore(t)

	if got := callTool(t, store, "standings", map[string]any{"competition": "Brasileirão", "season": 2019, "limit": 1}); !strings.Contains(got, "Flamengo") {
		t.Errorf("standings: %s", got)
	}
	if got := callTool(t, store, "head_to_head", map[string]any{"team_a": "Palmeiras", "team_b": "Santos"}); !strings.Contains(got, "head-to-head") {
		t.Errorf("head_to_head: %s", got)
	}
	if got := callTool(t, store, "search_players", map[string]any{"nationality": "Brazil", "limit": 3}); !strings.Contains(got, "Neymar") {
		t.Errorf("search_players: %s", got)
	}
	if got := callTool(t, store, "dataset_overview", map[string]any{}); !strings.Contains(got, "Competitions") {
		t.Errorf("dataset_overview: %s", got)
	}
	// Ambiguous team should yield a helpful prompt rather than wrong data.
	if got := callTool(t, store, "team_record", map[string]any{"team": "Atletico"}); !strings.Contains(strings.ToLower(got), "ambiguous") {
		t.Errorf("expected ambiguity prompt, got: %s", got)
	}
}
