package tools_test

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/data"
	"brazilian-soccer-mcp/tools"
)

const testDataDir = "../data/kaggle"

func loadStore(t *testing.T) *data.Store {
	t.Helper()
	store, err := data.LoadStore(testDataDir)
	if err != nil {
		t.Fatalf("LoadStore: %v", err)
	}
	return store
}

func newServer(t *testing.T, store *data.Store) *server.MCPServer {
	t.Helper()
	s := server.NewMCPServer("test", "0.0.1", server.WithToolCapabilities(true))
	tools.RegisterMatchTools(s, store)
	tools.RegisterTeamTools(s, store)
	tools.RegisterPlayerTools(s, store)
	tools.RegisterCompetitionTools(s, store)

	// Initialize the server session
	initMsg := `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.0.1"}}}`
	s.HandleMessage(context.Background(), []byte(initMsg))
	return s
}

func callTool(t *testing.T, s *server.MCPServer, name string, args map[string]any) string {
	t.Helper()
	argsJSON, err := json.Marshal(args)
	if err != nil {
		t.Fatalf("marshal args: %v", err)
	}
	msg := fmt.Sprintf(`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":%q,"arguments":%s}}`,
		name, string(argsJSON))
	respMsg := s.HandleMessage(context.Background(), []byte(msg))
	respBytes, err := json.Marshal(respMsg)
	if err != nil {
		t.Fatalf("marshal response: %v", err)
	}

	// Parse response
	var result struct {
		Result struct {
			Content []struct {
				Type string `json:"type"`
				Text string `json:"text"`
			} `json:"content"`
			IsError bool `json:"isError"`
		} `json:"result"`
		Error *struct {
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.Unmarshal(respBytes, &result); err != nil {
		t.Fatalf("unmarshal response: %v\nresponse: %s", err, string(respBytes))
	}
	if result.Error != nil {
		t.Fatalf("tool %s returned JSON-RPC error: %s", name, result.Error.Message)
	}
	if result.Result.IsError {
		t.Fatalf("tool %s returned tool error", name)
	}

	var sb strings.Builder
	for _, c := range result.Result.Content {
		if c.Type == "text" {
			sb.WriteString(c.Text)
		}
	}
	return sb.String()
}

func TestSearchMatches_Flamengo(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "search_matches", map[string]any{
		"team":        "Flamengo",
		"competition": "brasileirao",
		"limit":       20.0,
	})

	if !strings.Contains(result, "Found") {
		t.Errorf("expected 'Found' in result, got: %s", result[:minLen(200, len(result))])
	}
	if !strings.Contains(strings.ToLower(result), "flamengo") {
		t.Errorf("expected 'Flamengo' in result")
	}
	t.Logf("Flamengo matches (first 300):\n%s", result[:minLen(300, len(result))])
}

func TestSearchMatches_BySeason(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "search_matches", map[string]any{
		"team":        "Palmeiras",
		"competition": "brasileirao",
		"season":      2023.0,
		"limit":       5.0,
	})

	if !strings.Contains(result, "Found") {
		t.Fatalf("expected 'Found' in result, got: %s", result)
	}
	t.Logf("Palmeiras 2023: %s", result[:minLen(300, len(result))])
}

func TestHeadToHead(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "head_to_head", map[string]any{
		"team1":       "Flamengo",
		"team2":       "Fluminense",
		"competition": "all",
	})

	if !strings.Contains(result, "Head-to-head") {
		t.Errorf("expected 'Head-to-head' in result")
	}
	t.Logf("Fla-Flu H2H:\n%s", result[:minLen(500, len(result))])
}

func TestBiggestWins(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "biggest_wins", map[string]any{
		"competition": "all",
		"limit":       5.0,
	})

	if !strings.Contains(result, "Biggest victories") {
		t.Errorf("expected 'Biggest victories' in result")
	}
	t.Logf("Biggest wins:\n%s", result)
}

func TestTeamStats(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "team_stats", map[string]any{
		"team":        "Corinthians",
		"season":      2022.0,
		"competition": "brasileirao",
	})

	if strings.Contains(result, "No matches found") {
		t.Logf("No Corinthians 2022 data: %s", result)
		return
	}
	if !strings.Contains(strings.ToLower(result), "corinthians") {
		t.Errorf("expected 'Corinthians' in result: %s", result)
	}
	t.Logf("Corinthians 2022:\n%s", result)
}

func TestTopTeams(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "top_teams", map[string]any{
		"season":      2019.0,
		"competition": "brasileirao",
		"rank_by":     "points",
		"limit":       5.0,
	})

	if !strings.Contains(result, "Top teams") {
		t.Errorf("expected 'Top teams' in result")
	}
	t.Logf("2019 top teams:\n%s", result)
}

func TestSearchPlayers_Brazilian(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "search_players", map[string]any{
		"nationality": "Brazil",
		"min_overall": 85.0,
		"limit":       10.0,
	})

	if !strings.Contains(result, "Found") {
		t.Errorf("expected 'Found' in result: %s", result[:minLen(200, len(result))])
	}
	t.Logf("Top Brazilian players:\n%s", result)
}

func TestSearchPlayers_ByName(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "search_players", map[string]any{
		"name":  "Neymar",
		"limit": 5.0,
	})

	if !strings.Contains(strings.ToLower(result), "neymar") {
		t.Errorf("expected Neymar in result: %s", result)
	}
	t.Logf("Neymar search:\n%s", result)
}

func TestClubPlayers_Barcelona(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	// Use a club known to be in the FIFA dataset (international clubs)
	result := callTool(t, s, "club_players", map[string]any{
		"club":  "Barcelona",
		"limit": 10.0,
	})

	if !strings.Contains(strings.ToLower(result), "barcelona") {
		t.Errorf("expected 'barcelona' in result: %s", result[:minLen(200, len(result))])
	}
	t.Logf("Barcelona players:\n%s", result[:minLen(500, len(result))])
}

func TestStandings(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "standings", map[string]any{
		"season":      2019.0,
		"competition": "brasileirao",
	})

	if !strings.Contains(result, "2019") {
		t.Errorf("expected '2019' in result: %s", result[:minLen(300, len(result))])
	}
	t.Logf("2019 standings:\n%s", result[:minLen(1000, len(result))])
}

func TestListSeasons(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "list_seasons", map[string]any{
		"competition": "all",
	})

	if !strings.Contains(result, "Brasileirão") {
		t.Errorf("expected 'Brasileirão' in result: %s", result)
	}
	t.Logf("Seasons:\n%s", result)
}

func TestMatchStatsSummary(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "match_stats_summary", map[string]any{
		"competition": "brasileirao",
		"season":      0.0,
	})

	if !strings.Contains(result, "Total matches") {
		t.Errorf("expected 'Total matches' in result: %s", result)
	}
	t.Logf("Stats summary:\n%s", result)
}

func TestSearchMatches_Copa(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "search_matches", map[string]any{
		"team":        "Flamengo",
		"competition": "cup",
		"limit":       10.0,
	})

	if !strings.Contains(result, "Found") {
		t.Errorf("expected 'Found' in result")
	}
	t.Logf("Flamengo Copa:\n%s", result[:minLen(300, len(result))])
}

func TestSearchMatches_Libertadores(t *testing.T) {
	store := loadStore(t)
	s := newServer(t, store)

	result := callTool(t, s, "search_matches", map[string]any{
		"team":        "Palmeiras",
		"competition": "libertadores",
		"limit":       10.0,
	})

	if !strings.Contains(result, "Found") {
		t.Errorf("expected 'Found' in result")
	}
	t.Logf("Palmeiras Libertadores:\n%s", result[:minLen(300, len(result))])
}

func minLen(a, b int) int {
	if a < b {
		return a
	}
	return b
}
