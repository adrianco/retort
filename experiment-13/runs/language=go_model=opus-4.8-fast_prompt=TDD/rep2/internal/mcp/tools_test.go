package mcp

import (
	"strings"
	"testing"
)

func TestCallHeadToHead(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "head_to_head", map[string]any{"team1": "Flamengo", "team2": "Gremio"})
	if isErr {
		t.Fatalf("unexpected error: %s", out)
	}
	// One win (5-0) and one draw (1-1) for Flamengo.
	if !strings.Contains(out, "Flamengo wins: 1") || !strings.Contains(out, "Draws: 1") {
		t.Errorf("h2h tally wrong:\n%s", out)
	}
}

func TestCallHeadToHeadMissingArgsIsError(t *testing.T) {
	s := testServer()
	_, isErr := callText(t, s, "head_to_head", map[string]any{"team1": "Flamengo"})
	if !isErr {
		t.Error("expected error when team2 missing")
	}
}

func TestCallTeamRecordHomeOnly(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "team_record", map[string]any{
		"team": "Flamengo", "home_only": true, "season": 2019, "competition": "Brasileirão"})
	if isErr {
		t.Fatalf("unexpected error: %s", out)
	}
	// Flamengo home in 2019: just the 5-0 win.
	if !strings.Contains(out, "Matches: 1") || !strings.Contains(out, "Wins: 1") {
		t.Errorf("home record wrong:\n%s", out)
	}
	if !strings.Contains(out, "(home)") {
		t.Errorf("missing home scope label:\n%s", out)
	}
}

func TestCallTeamRecordRequiresTeam(t *testing.T) {
	s := testServer()
	_, isErr := callText(t, s, "team_record", map[string]any{})
	if !isErr {
		t.Error("expected error when team missing")
	}
}

func TestCallCompetitionStats(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "competition_stats", map[string]any{"competition": "Brasileirão"})
	if isErr {
		t.Fatalf("unexpected error: %s", out)
	}
	if !strings.Contains(out, "Average goals per match") || !strings.Contains(out, "Biggest victories") {
		t.Errorf("stats output missing sections:\n%s", out)
	}
}

func TestCallSearchMatchesWithDateRange(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "search_matches", map[string]any{
		"team": "Flamengo", "date_from": "2018-01-01", "date_to": "2025-12-31"})
	if isErr {
		t.Fatalf("unexpected error: %s", out)
	}
	if !strings.Contains(out, "Found") {
		t.Errorf("unexpected output:\n%s", out)
	}
}

func TestCallSearchMatchesBadDateIsError(t *testing.T) {
	s := testServer()
	_, isErr := callText(t, s, "search_matches", map[string]any{"date_from": "13/13/2020-bad"})
	if !isErr {
		t.Error("expected error for invalid date_from")
	}
}

func TestCallSearchMatchesNoResults(t *testing.T) {
	s := testServer()
	out, _ := callText(t, s, "search_matches", map[string]any{"team": "Nonexistent United"})
	if !strings.Contains(out, "No matches found") {
		t.Errorf("expected no-results message, got:\n%s", out)
	}
}

func TestCallStandingsRequiresArgs(t *testing.T) {
	s := testServer()
	_, isErr := callText(t, s, "standings", map[string]any{"competition": "Brasileirão"})
	if !isErr {
		t.Error("expected error when season missing")
	}
}
