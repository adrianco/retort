package app

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/mcp"
)

// dataDir is the bundled dataset relative to this package during testing.
const dataDir = "../../data/kaggle"

func loadStore(t *testing.T) (*mcp.Server, func(tool string, args map[string]any) string) {
	t.Helper()
	if _, err := os.Stat(dataDir + "/Brasileirao_Matches.csv"); err != nil {
		t.Skipf("bundled data not available: %v", err)
	}
	srv, _, err := New(os.DirFS(dataDir), ".")
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	call := func(tool string, args map[string]any) string {
		argsJSON, _ := json.Marshal(args)
		req := map[string]any{
			"jsonrpc": "2.0", "id": 1, "method": "tools/call",
			"params": map[string]any{"name": tool, "arguments": json.RawMessage(argsJSON)},
		}
		reqJSON, _ := json.Marshal(req)
		var out strings.Builder
		if err := srv.Serve(strings.NewReader(string(reqJSON)+"\n"), &out); err != nil {
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
		if err := json.Unmarshal([]byte(out.String()), &resp); err != nil {
			t.Fatalf("decode: %v (%s)", err, out.String())
		}
		if len(resp.Result.Content) == 0 {
			t.Fatalf("empty content for %s", tool)
		}
		if resp.Result.IsError {
			t.Fatalf("tool %s returned error: %s", tool, resp.Result.Content[0].Text)
		}
		return resp.Result.Content[0].Text
	}
	return srv, call
}

// Feature: end-to-end tool calls over the MCP server using the real datasets.

func TestStandings2019(t *testing.T) {
	_, call := loadStore(t)
	out := call("standings", map[string]any{"competition": "Brasileirão Série A", "season": 2019})
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "Champion") {
		t.Errorf("2019 standings missing champion Flamengo:\n%s", firstLines(out, 5))
	}
}

func TestHeadToHandFlaFlu(t *testing.T) {
	_, call := loadStore(t)
	out := call("head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense"})
	if !strings.Contains(out, "head-to-head") {
		t.Errorf("unexpected head_to_head output:\n%s", firstLines(out, 4))
	}
}

func TestSearchBrazilianPlayers(t *testing.T) {
	_, call := loadStore(t)
	out := call("search_players", map[string]any{"nationality": "Brazil", "limit": 5})
	if !strings.Contains(out, "Overall") {
		t.Errorf("player search output missing ratings:\n%s", firstLines(out, 3))
	}
}

func TestSearchMatchesByTeamSeason(t *testing.T) {
	_, call := loadStore(t)
	out := call("search_matches", map[string]any{"team": "Palmeiras", "season": 2019})
	if !strings.Contains(out, "Total:") {
		t.Errorf("match search missing total:\n%s", firstLines(out, 3))
	}
}

func TestTeamStatsHomeRecord(t *testing.T) {
	_, call := loadStore(t)
	out := call("team_stats", map[string]any{
		"team": "Corinthians", "competition": "Brasileirão Série A", "season": 2019, "venue": "home",
	})
	if !strings.Contains(out, "Win rate") {
		t.Errorf("team_stats missing win rate:\n%s", out)
	}
}

func TestCompetitionStats(t *testing.T) {
	_, call := loadStore(t)
	out := call("competition_stats", map[string]any{"competition": "Brasileirão Série A"})
	if !strings.Contains(out, "Average goals per match") {
		t.Errorf("competition_stats missing averages:\n%s", out)
	}
}

func TestListCompetitions(t *testing.T) {
	_, call := loadStore(t)
	out := call("list_competitions", map[string]any{})
	for _, want := range []string{"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"} {
		if !strings.Contains(out, want) {
			t.Errorf("list_competitions missing %q:\n%s", want, out)
		}
	}
}

func TestMissingRequiredArgsIsError(t *testing.T) {
	srv, _ := loadStore(t)
	// standings requires competition and season; omit them and expect isError.
	req := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"standings","arguments":{}}}`
	var out strings.Builder
	if err := srv.Serve(strings.NewReader(req+"\n"), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	if !strings.Contains(out.String(), `"isError":true`) {
		t.Errorf("expected isError for missing args, got:\n%s", out.String())
	}
}

func firstLines(s string, n int) string {
	lines := strings.SplitN(s, "\n", n+1)
	if len(lines) > n {
		lines = lines[:n]
	}
	return strings.Join(lines, "\n")
}
