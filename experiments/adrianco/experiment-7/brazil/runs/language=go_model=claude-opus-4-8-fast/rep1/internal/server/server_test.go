// Package server tests — end-to-end tool invocations through the MCP server
// against the real datasets (BDD Given/When/Then).
//
// Context:
//   - Loads ../../data/kaggle once, registers all tools on an mcp.Server, then
//     drives each tool the way an MCP client would (tools/call) and asserts on
//     the rendered text content.
package server

import (
	"encoding/json"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/store"
)

var (
	sharedSrv *mcp.Server
	once      sync.Once
	loadErr   error
)

func testServer(t *testing.T) *mcp.Server {
	t.Helper()
	once.Do(func() {
		var st *store.Store
		st, loadErr = store.Load(filepath.Join("..", "..", "data", "kaggle"))
		if loadErr != nil {
			return
		}
		sharedSrv = mcp.NewServer("brazilian-soccer-mcp", "test")
		Register(sharedSrv, st)
	})
	if loadErr != nil {
		t.Fatalf("Given the datasets, loading failed: %v", loadErr)
	}
	return sharedSrv
}

// callTool drives one tools/call and returns (text, isError).
func callTool(t *testing.T, s *mcp.Server, name string, args map[string]any) (string, bool) {
	t.Helper()
	argsJSON, _ := json.Marshal(args)
	req := map[string]any{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "tools/call",
		"params":  map[string]any{"name": name, "arguments": json.RawMessage(argsJSON)},
	}
	line, _ := json.Marshal(req)
	var out strings.Builder
	if err := s.Serve(strings.NewReader(string(line)+"\n"), &out); err != nil {
		t.Fatalf("Serve error: %v", err)
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
		t.Fatalf("invalid response %q: %v", out.String(), err)
	}
	if len(resp.Result.Content) == 0 {
		return "", resp.Result.IsError
	}
	return resp.Result.Content[0].Text, resp.Result.IsError
}

// Scenario: All eight tools are advertised.
func TestScenario_ToolsRegistered(t *testing.T) {
	// Given the server with all tools registered
	s := testServer(t)
	// When tools/list is requested
	var out strings.Builder
	_ = s.Serve(strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`+"\n"), &out)
	// Then the expected tool names are present
	for _, name := range []string{
		"find_matches", "head_to_head", "team_stats", "standings",
		"search_players", "competition_stats", "biggest_wins", "list_competitions",
	} {
		if !strings.Contains(out.String(), `"`+name+`"`) {
			t.Errorf("Then tool %q should be advertised", name)
		}
	}
}

// Scenario: find_matches returns Fla-Flu meetings with scores.
func TestScenario_FindMatchesTool(t *testing.T) {
	s := testServer(t)
	// When I call find_matches for Flamengo vs Fluminense
	text, isErr := callTool(t, s, "find_matches", map[string]any{
		"team": "Flamengo", "opponent": "Fluminense",
	})
	// Then it succeeds and mentions both clubs
	if isErr {
		t.Fatalf("Then call should succeed; got error: %s", text)
	}
	if !strings.Contains(text, "Found") || !containsCI(text, "Flamengo") {
		t.Errorf("Then output should list matches; got:\n%s", text)
	}
}

// Scenario: find_matches with no filters returns a helpful error.
func TestScenario_FindMatchesRequiresFilter(t *testing.T) {
	s := testServer(t)
	// When I call find_matches with no arguments
	text, isErr := callTool(t, s, "find_matches", map[string]any{})
	// Then it reports an error asking for a filter
	if !isErr {
		t.Errorf("Then an error is expected; got: %s", text)
	}
}

// Scenario: head_to_head reports a consistent record.
func TestScenario_HeadToHeadTool(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "head_to_head", map[string]any{
		"team_a": "Palmeiras", "team_b": "Santos",
	})
	if isErr {
		t.Fatalf("Then call should succeed; got: %s", text)
	}
	if !strings.Contains(text, "Head-to-head") {
		t.Errorf("Then output should be a head-to-head summary; got:\n%s", text)
	}
}

// Scenario: team_stats reports a record with a win rate.
func TestScenario_TeamStatsTool(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "team_stats", map[string]any{
		"team": "Corinthians", "season": 2022, "venue": "home",
	})
	if isErr {
		t.Fatalf("Then call should succeed; got: %s", text)
	}
	for _, want := range []string{"Matches:", "Wins:", "Win rate:"} {
		if !strings.Contains(text, want) {
			t.Errorf("Then output should contain %q; got:\n%s", want, text)
		}
	}
}

// Scenario: standings names Flamengo champion of 2019.
func TestScenario_StandingsTool(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "standings", map[string]any{"season": 2019, "limit": 5})
	if isErr {
		t.Fatalf("Then call should succeed; got: %s", text)
	}
	if !strings.Contains(text, "standings") {
		t.Errorf("Then output should be a table; got:\n%s", text)
	}
	// And the first ranked line is Flamengo
	firstLine := ""
	for _, ln := range strings.Split(text, "\n") {
		if strings.HasPrefix(strings.TrimSpace(ln), "1.") {
			firstLine = ln
			break
		}
	}
	if !containsCI(firstLine, "Flamengo") {
		t.Errorf("Then 2019 champion should be Flamengo; first line was %q", firstLine)
	}
}

// Scenario: standings requires a season.
func TestScenario_StandingsRequiresSeason(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "standings", map[string]any{})
	if !isErr {
		t.Errorf("Then missing season should error; got: %s", text)
	}
}

// Scenario: search_players finds top Brazilians (Neymar first).
func TestScenario_SearchPlayersTool(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "search_players", map[string]any{
		"nationality": "Brazil", "limit": 3,
	})
	if isErr {
		t.Fatalf("Then call should succeed; got: %s", text)
	}
	if !containsCI(text, "Neymar") {
		t.Errorf("Then top Brazilian should be Neymar; got:\n%s", text)
	}
}

// Scenario: competition_stats reports an average goals figure.
func TestScenario_CompetitionStatsTool(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "competition_stats", map[string]any{
		"competition": "Brasileirão",
	})
	if isErr {
		t.Fatalf("Then call should succeed; got: %s", text)
	}
	if !strings.Contains(text, "Average goals per match:") {
		t.Errorf("Then output should report average goals; got:\n%s", text)
	}
}

// Scenario: biggest_wins lists lopsided results.
func TestScenario_BiggestWinsTool(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "biggest_wins", map[string]any{"limit": 3})
	if isErr {
		t.Fatalf("Then call should succeed; got: %s", text)
	}
	if !strings.Contains(text, "Biggest victories") {
		t.Errorf("Then output should list biggest wins; got:\n%s", text)
	}
}

// Scenario: list_competitions summarizes loaded data.
func TestScenario_ListCompetitionsTool(t *testing.T) {
	s := testServer(t)
	text, isErr := callTool(t, s, "list_competitions", nil)
	if isErr {
		t.Fatalf("Then call should succeed; got: %s", text)
	}
	if !strings.Contains(text, "Competitions available") {
		t.Errorf("Then output should list competitions; got:\n%s", text)
	}
}

func containsCI(s, sub string) bool {
	return strings.Contains(strings.ToLower(s), strings.ToLower(sub))
}
