package mcp_test

import (
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/mcp"
)

var (
	srvOnce sync.Once
	srvVal  *mcp.Server
	srvErr  error
)

func server(t *testing.T) *mcp.Server {
	t.Helper()
	srvOnce.Do(func() {
		abs, err := filepath.Abs("../../data/kaggle")
		if err != nil {
			srvErr = err
			return
		}
		ds, err := data.LoadAll(abs)
		if err != nil {
			srvErr = err
			return
		}
		s := mcp.NewServer("test", "test")
		mcp.RegisterAll(s, ds)
		srvVal = s
	})
	if srvErr != nil {
		t.Fatalf("server init: %v", srvErr)
	}
	return srvVal
}

// Feature: MCP tool calls
// Scenario: every registered tool can be invoked
func TestToolsRegistered(t *testing.T) {
	s := server(t)
	expected := []string{
		"find_matches", "head_to_head", "team_stats", "top_scoring_teams",
		"search_players", "top_clubs_by_nationality", "standings",
		"biggest_wins", "aggregate_stats", "list_seasons", "dataset_summary",
	}
	names := s.ToolNames()
	have := make(map[string]bool, len(names))
	for _, n := range names {
		have[n] = true
	}
	for _, n := range expected {
		if !have[n] {
			t.Errorf("expected tool %q registered", n)
		}
	}
}

func TestFindMatchesTool(t *testing.T) {
	s := server(t)
	got, err := s.CallTool("find_matches", map[string]any{
		"team":     "Flamengo",
		"opponent": "Fluminense",
		"limit":    5,
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if got == "" || strings.Contains(got, "No matches") {
		t.Fatalf("expected matches, got %q", got)
	}
}

func TestHeadToHeadTool(t *testing.T) {
	s := server(t)
	got, err := s.CallTool("head_to_head", map[string]any{
		"team_a": "Palmeiras",
		"team_b": "Santos",
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if !strings.Contains(got, "head-to-head") {
		t.Fatalf("expected head-to-head summary, got %q", got)
	}
}

func TestStandingsTool(t *testing.T) {
	s := server(t)
	got, err := s.CallTool("standings", map[string]any{
		"competition": "Brasileirão",
		"season":      2018,
		"limit":       5,
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if !strings.Contains(got, "standings") {
		t.Fatalf("expected standings output, got %q", got)
	}
}

func TestSearchPlayersTool(t *testing.T) {
	s := server(t)
	got, err := s.CallTool("search_players", map[string]any{
		"nationality": "Brazil",
		"limit":       3,
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if strings.Contains(got, "No players") {
		t.Fatalf("expected players, got %q", got)
	}
}

func TestDatasetSummaryTool(t *testing.T) {
	s := server(t)
	got, err := s.CallTool("dataset_summary", map[string]any{})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if !strings.Contains(got, "Total matches:") {
		t.Fatalf("expected summary output, got %q", got)
	}
}

func TestMissingRequiredArgs(t *testing.T) {
	s := server(t)
	_, err := s.CallTool("head_to_head", map[string]any{"team_a": ""})
	if err == nil {
		t.Fatal("expected error for missing team_b")
	}
}
