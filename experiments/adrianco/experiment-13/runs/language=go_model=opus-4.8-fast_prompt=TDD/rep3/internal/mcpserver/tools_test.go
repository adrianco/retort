// Context: Brazilian Soccer MCP Server.
// File: tools_test.go
// Purpose: Tests for the tool-dispatch layer that maps an MCP tool name plus
// arguments onto a formatted, human-readable answer using the query engine.
package mcpserver

import (
	"strings"
	"testing"
	"time"

	"brazilian-soccer-mcp/internal/soccer"
)

func d(s string) time.Time {
	t, _ := time.Parse("2006-01-02", s)
	return t
}

func testHandler() *Handler {
	db := &soccer.DB{
		Matches: []soccer.Match{
			{Competition: soccer.CompBrasileirao, Season: 2023, Round: "1", Date: d("2023-04-01"), HasDate: true,
				HomeTeam: "Flamengo", AwayTeam: "Fluminense", HomeGoals: 2, AwayGoals: 1, HasScore: true},
			{Competition: soccer.CompBrasileirao, Season: 2023, Round: "8", Date: d("2023-05-28"), HasDate: true,
				HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeGoals: 1, AwayGoals: 0, HasScore: true},
			{Competition: soccer.CompBrasileirao, Season: 2023, Round: "5", Date: d("2023-05-01"), HasDate: true,
				HomeTeam: "Flamengo", AwayTeam: "Santos", HomeGoals: 5, AwayGoals: 0, HasScore: true},
			{Competition: soccer.CompBrasileirao, Season: 2023, Round: "6", Date: d("2023-05-10"), HasDate: true,
				HomeTeam: "Santos", AwayTeam: "Fluminense", HomeGoals: 0, AwayGoals: 0, HasScore: true},
		},
		Players: []soccer.Player{
			{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain", Position: "LW"},
			{ID: 2, Name: "Alisson", Nationality: "Brazil", Overall: 89, Club: "Liverpool", Position: "GK"},
			{ID: 3, Name: "L. Messi", Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", Position: "RF"},
		},
	}
	return NewHandler(db)
}

func TestToolsListed(t *testing.T) {
	tools := Tools()
	want := []string{"search_matches", "head_to_head", "team_record", "standings", "search_players", "match_statistics"}
	got := map[string]bool{}
	for _, tl := range tools {
		got[tl.Name] = true
		if tl.Description == "" {
			t.Errorf("tool %q missing description", tl.Name)
		}
		if tl.InputSchema == nil {
			t.Errorf("tool %q missing input schema", tl.Name)
		}
	}
	for _, w := range want {
		if !got[w] {
			t.Errorf("missing tool %q", w)
		}
	}
}

func TestCallSearchMatches(t *testing.T) {
	h := testHandler()
	out, err := h.Call("search_matches", map[string]any{"team": "Flamengo", "opponent": "Fluminense"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "Fluminense") {
		t.Errorf("output missing teams:\n%s", out)
	}
	if !strings.Contains(out, "2-1") {
		t.Errorf("output missing score:\n%s", out)
	}
}

func TestCallHeadToHead(t *testing.T) {
	h := testHandler()
	out, err := h.Call("head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "1 win") {
		t.Errorf("expected head-to-head wins in output:\n%s", out)
	}
}

func TestCallTeamRecord(t *testing.T) {
	h := testHandler()
	out, err := h.Call("team_record", map[string]any{"team": "Flamengo", "season": float64(2023), "competition": "Brasileirão"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "Wins: 2") {
		t.Errorf("expected win count:\n%s", out)
	}
}

func TestCallStandings(t *testing.T) {
	h := testHandler()
	out, err := h.Call("standings", map[string]any{"season": float64(2023), "competition": "Brasileirão"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "pts") {
		t.Errorf("expected standings table:\n%s", out)
	}
	// Flamengo (6 pts) should be listed before Santos.
	if strings.Index(out, "Flamengo") > strings.Index(out, "Santos") {
		t.Errorf("standings order wrong:\n%s", out)
	}
}

func TestCallSearchPlayers(t *testing.T) {
	h := testHandler()
	out, err := h.Call("search_players", map[string]any{"nationality": "Brazil"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "Neymar Jr") || !strings.Contains(out, "Alisson") {
		t.Errorf("expected Brazilian players:\n%s", out)
	}
	// Neymar (92) listed before Alisson (89); Messi (Argentina) excluded.
	if strings.Index(out, "Neymar") > strings.Index(out, "Alisson") {
		t.Errorf("players not sorted by rating:\n%s", out)
	}
	if strings.Contains(out, "Messi") {
		t.Errorf("non-Brazilian leaked into results:\n%s", out)
	}
}

func TestCallMatchStatistics(t *testing.T) {
	h := testHandler()
	out, err := h.Call("match_statistics", map[string]any{"competition": "Brasileirão", "season": float64(2023)})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "Average goals") {
		t.Errorf("expected average goals:\n%s", out)
	}
	if !strings.Contains(strings.ToLower(out), "biggest") {
		t.Errorf("expected biggest wins section:\n%s", out)
	}
}

func TestCallUnknownTool(t *testing.T) {
	h := testHandler()
	if _, err := h.Call("nope", nil); err == nil {
		t.Errorf("expected error for unknown tool")
	}
}

func TestCallMissingRequiredArg(t *testing.T) {
	h := testHandler()
	if _, err := h.Call("head_to_head", map[string]any{"team_a": "Flamengo"}); err == nil {
		t.Errorf("expected error when team_b missing")
	}
}
