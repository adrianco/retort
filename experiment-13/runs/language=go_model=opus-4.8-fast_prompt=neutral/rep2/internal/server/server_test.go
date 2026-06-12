// Context: tests the MCP tool catalog wired to the soccer DB. Loads the soccer
// package's deterministic fixtures, then invokes each tool handler the way the
// MCP layer would and asserts on the formatted answer text.
package server

import (
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/soccer"
)

func testDB(t *testing.T) *soccer.DB {
	t.Helper()
	db, err := soccer.Load("../soccer/testdata/kaggle")
	if err != nil {
		t.Fatalf("load fixtures: %v", err)
	}
	return db
}

// handler looks up a tool by name from the catalog.
func handler(t *testing.T, db *soccer.DB, name string) func(map[string]interface{}) (string, error) {
	t.Helper()
	for _, tool := range Tools(db) {
		if tool.Name == name {
			return tool.Handler
		}
	}
	t.Fatalf("tool %q not registered", name)
	return nil
}

func call(t *testing.T, db *soccer.DB, name string, args map[string]interface{}) string {
	t.Helper()
	out, err := handler(t, db, name)(args)
	if err != nil {
		t.Fatalf("%s returned error: %v", name, err)
	}
	return out
}

func mustContain(t *testing.T, got string, subs ...string) {
	t.Helper()
	for _, s := range subs {
		if !strings.Contains(got, s) {
			t.Errorf("output missing %q\n--- got ---\n%s", s, got)
		}
	}
}

func TestCatalogComplete(t *testing.T) {
	db := testDB(t)
	want := []string{
		"search_matches", "head_to_head", "team_record", "search_players",
		"players_by_club", "competition_standings", "match_statistics", "list_competitions",
	}
	have := map[string]bool{}
	for _, tool := range Tools(db) {
		have[tool.Name] = true
		if tool.Handler == nil {
			t.Errorf("tool %s has nil handler", tool.Name)
		}
		if tool.InputSchema == nil {
			t.Errorf("tool %s has nil input schema", tool.Name)
		}
	}
	for _, w := range want {
		if !have[w] {
			t.Errorf("missing tool %s", w)
		}
	}
}

func TestSearchMatchesTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "search_matches", map[string]interface{}{
		"team": "Flamengo", "opponent": "Palmeiras",
	})
	mustContain(t, out, "Flamengo", "Palmeiras", "Brasileirão")
}

func TestStandingsTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "competition_standings", map[string]interface{}{
		"competition": "Brasileirão", "season": float64(2019),
	})
	// Fixture standings: Flamengo 10 pts, Palmeiras 4, Santos 2.
	mustContain(t, out, "1. Flamengo - 10 pts", "Palmeiras - 4 pts", "Santos - 2 pts")
}

func TestTeamRecordTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "team_record", map[string]interface{}{
		"team": "Flamengo", "season": float64(2019), "competition": "Brasileirão",
	})
	mustContain(t, out, "Matches: 4", "Wins: 3, Draws: 1, Losses: 0", "Points: 10")
}

func TestHeadToHeadTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "head_to_head", map[string]interface{}{
		"team_a": "Flamengo", "team_b": "Santos",
	})
	mustContain(t, out, "Flamengo", "Santos", "head-to-head", "1 wins")
}

func TestHeadToHeadMissingArg(t *testing.T) {
	db := testDB(t)
	_, err := handler(t, db, "head_to_head")(map[string]interface{}{"team_a": "Flamengo"})
	if err == nil {
		t.Error("expected error when team_b is missing")
	}
}

func TestSearchPlayersTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "search_players", map[string]interface{}{
		"nationality": "Brazil", "min_overall": float64(80),
	})
	mustContain(t, out, "Neymar Jr", "Overall: 92", "Gabriel Jesus")
	if strings.Contains(out, "Local Hero") {
		t.Error("Local Hero (75) should be excluded by min_overall 80")
	}
}

func TestPlayersByClubTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "players_by_club", map[string]interface{}{"nationality": "Brazil"})
	mustContain(t, out, "players", "avg rating")
}

func TestStatisticsTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "match_statistics", map[string]interface{}{
		"competition": "Brasileirão", "season": float64(2019),
	})
	mustContain(t, out, "Matches: 6", "avg", "Biggest-margin")
}

func TestListCompetitionsTool(t *testing.T) {
	db := testDB(t)
	out := call(t, db, "list_competitions", map[string]interface{}{})
	mustContain(t, out, "Brasileirão", "Copa do Brasil", "Libertadores", "Data coverage")
}

func TestArgCoercion(t *testing.T) {
	// season passed as a string should still be honored.
	db := testDB(t)
	out := call(t, db, "team_record", map[string]interface{}{
		"team": "Flamengo", "season": "2019", "competition": "Brasileirão",
	})
	mustContain(t, out, "Matches: 4")
}
