package tools

import (
	"context"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"brazilian-soccer-mcp/store"
)

func testStore(t *testing.T) *store.Store {
	t.Helper()
	_, file, _, _ := runtime.Caller(0)
	dir := filepath.Dir(filepath.Dir(file))
	s, err := store.New(filepath.Join(dir, "data", "kaggle"))
	if err != nil {
		t.Fatalf("store.New: %v", err)
	}
	return s
}

func TestSearchMatchesTool(t *testing.T) {
	s := testStore(t)
	h := NewHandlers(s)
	ctx := context.Background()

	result, err := h.SearchMatches(ctx, map[string]interface{}{
		"team": "Flamengo",
	})
	if err != nil {
		t.Fatalf("SearchMatches: %v", err)
	}
	if len(result) == 0 {
		t.Fatal("expected non-empty result")
	}
	text := result[0].Text
	if !strings.Contains(text, "Flamengo") {
		t.Errorf("result does not mention Flamengo: %s", text)
	}
}

func TestHeadToHeadTool(t *testing.T) {
	s := testStore(t)
	h := NewHandlers(s)
	ctx := context.Background()

	result, err := h.HeadToHead(ctx, map[string]interface{}{
		"team1": "Flamengo",
		"team2": "Fluminense",
	})
	if err != nil {
		t.Fatalf("HeadToHead: %v", err)
	}
	text := result[0].Text
	if !strings.Contains(text, "Flamengo") || !strings.Contains(text, "Fluminense") {
		t.Errorf("result missing team names: %s", text)
	}
	if !strings.Contains(text, "wins") {
		t.Errorf("result missing wins info: %s", text)
	}
}

func TestTeamStatsTool(t *testing.T) {
	s := testStore(t)
	h := NewHandlers(s)
	ctx := context.Background()

	result, err := h.TeamStats(ctx, map[string]interface{}{
		"team":   "Palmeiras",
		"season": float64(2022),
	})
	if err != nil {
		t.Fatalf("TeamStats: %v", err)
	}
	text := result[0].Text
	if !strings.Contains(text, "Palmeiras") {
		t.Errorf("result missing team: %s", text)
	}
	if !strings.Contains(text, "Played") {
		t.Errorf("result missing stats: %s", text)
	}
}

func TestSearchPlayersTool(t *testing.T) {
	s := testStore(t)
	h := NewHandlers(s)
	ctx := context.Background()

	result, err := h.SearchPlayers(ctx, map[string]interface{}{
		"name": "Neymar",
	})
	if err != nil {
		t.Fatalf("SearchPlayers: %v", err)
	}
	text := result[0].Text
	if !strings.Contains(text, "Neymar") {
		t.Errorf("result missing Neymar: %s", text)
	}
}

func TestLeagueStandingsTool(t *testing.T) {
	s := testStore(t)
	h := NewHandlers(s)
	ctx := context.Background()

	result, err := h.LeagueStandings(ctx, map[string]interface{}{
		"season": float64(2019),
	})
	if err != nil {
		t.Fatalf("LeagueStandings: %v", err)
	}
	text := result[0].Text
	if !strings.Contains(text, "2019") {
		t.Errorf("result missing season: %s", text)
	}
}

func TestBiggestWinsTool(t *testing.T) {
	s := testStore(t)
	h := NewHandlers(s)
	ctx := context.Background()

	result, err := h.BiggestWins(ctx, map[string]interface{}{
		"limit": float64(5),
	})
	if err != nil {
		t.Fatalf("BiggestWins: %v", err)
	}
	text := result[0].Text
	if !strings.Contains(text, "vs") {
		t.Errorf("result missing match info: %s", text)
	}
}

func TestStatisticsTool(t *testing.T) {
	s := testStore(t)
	h := NewHandlers(s)
	ctx := context.Background()

	result, err := h.Statistics(ctx, map[string]interface{}{})
	if err != nil {
		t.Fatalf("Statistics: %v", err)
	}
	text := result[0].Text
	if !strings.Contains(text, "goals per match") {
		t.Errorf("result missing goals info: %s", text)
	}
}
