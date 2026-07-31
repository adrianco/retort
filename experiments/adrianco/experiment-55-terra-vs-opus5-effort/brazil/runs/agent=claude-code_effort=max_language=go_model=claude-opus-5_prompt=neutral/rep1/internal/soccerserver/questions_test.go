package soccerserver

import (
	"strings"
	"testing"
	"time"
)

// TestSampleQuestions is the "at least 20 sample questions can be answered"
// success criterion: every entry of the catalogue is executed against the real
// data and must come back with a substantive answer.
func TestSampleQuestions(t *testing.T) {
	srv := testServer(t)
	if len(SampleQuestions) < 20 {
		t.Fatalf("the catalogue has %d questions, the specification asks for at least 20", len(SampleQuestions))
	}
	categories := map[string]int{}
	for i, q := range SampleQuestions {
		q := q
		t.Run(strings.ReplaceAll(q.Question, " ", "_"), func(t *testing.T) {
			categories[q.Category]++
			if srv.Tool(q.Tool) == nil {
				t.Fatalf("question %d uses unknown tool %q", i+1, q.Tool)
			}
			start := time.Now()
			result, err := srv.CallTool(q.Tool, q.Args)
			if err != nil {
				t.Fatalf("%s: %v", q.Tool, err)
			}
			elapsed := time.Since(start)
			body := text(result)
			if strings.TrimSpace(body) == "" {
				t.Fatalf("%s returned nothing", q.Tool)
			}
			// A question may legitimately be answered with "the data does not
			// contain this", but the answer must then explain itself.
			if result.IsError && len(body) < 40 {
				t.Fatalf("%s failed without explaining itself: %s", q.Tool, body)
			}
			if q.Expect != "" && !strings.Contains(body, q.Expect) {
				t.Errorf("answer does not contain %q:\n%s", q.Expect, body)
			}
			if elapsed > 5*time.Second {
				t.Errorf("answering took %s", elapsed)
			}
		})
	}
	for _, want := range []string{"match", "team", "player", "competition", "stats", "graph"} {
		if categories[want] == 0 {
			t.Errorf("no sample question covers the %q category", want)
		}
	}
}

// Simple lookups must answer in under two seconds and aggregates in under
// five, per the specification's performance criteria.
func TestToolLatency(t *testing.T) {
	srv := testServer(t)
	simple := []struct {
		tool string
		args map[string]any
	}{
		{"search_matches", map[string]any{"team": "Flamengo", "opponent": "Fluminense", "limit": 20}},
		{"match_details", map[string]any{"team": "Flamengo", "opponent": "Corinthians"}},
		{"player_profile", map[string]any{"name": "Neymar"}},
		{"search_players", map[string]any{"nationality": "Brazil", "limit": 20}},
		{"head_to_head", map[string]any{"team_a": "Palmeiras", "team_b": "Santos"}},
		{"list_teams", map[string]any{"state": "SP"}},
	}
	for _, c := range simple {
		start := time.Now()
		if _, err := srv.CallTool(c.tool, c.args); err != nil {
			t.Fatalf("%s: %v", c.tool, err)
		}
		if elapsed := time.Since(start); elapsed > 2*time.Second {
			t.Errorf("%s took %s, the budget for a simple lookup is 2s", c.tool, elapsed)
		}
	}

	aggregate := []struct {
		tool string
		args map[string]any
	}{
		{"standings", map[string]any{"season": 2019}},
		{"season_summary", map[string]any{"competition": "libertadores", "season": 2018}},
		{"league_statistics", map[string]any{}},
		{"best_records", map[string]any{"metric": "win_rate", "min_matches": 100, "limit": 20}},
		{"compare_seasons", map[string]any{"season_from": 2003, "season_to": 2023}},
		{"team_profile", map[string]any{"team": "Flamengo"}},
		{"club_squads", map[string]any{}},
		{"list_datasets", map[string]any{}},
	}
	for _, c := range aggregate {
		start := time.Now()
		if _, err := srv.CallTool(c.tool, c.args); err != nil {
			t.Fatalf("%s: %v", c.tool, err)
		}
		if elapsed := time.Since(start); elapsed > 5*time.Second {
			t.Errorf("%s took %s, the budget for an aggregate is 5s", c.tool, elapsed)
		}
	}
}

// Every tool must be reachable, described, and callable with only its required
// arguments.
func TestEveryToolIsUsable(t *testing.T) {
	srv := testServer(t)
	if len(srv.Tools()) < 15 {
		t.Fatalf("only %d tools registered", len(srv.Tools()))
	}
	defaults := map[string]map[string]any{
		"team_profile":    {"team": "Flamengo"},
		"team_stats":      {"team": "Flamengo"},
		"head_to_head":    {"team_a": "Flamengo", "team_b": "Vasco"},
		"standings":       {"season": 2019},
		"season_summary":  {"season": 2019},
		"graph_neighbors": {"entity": "team:flamengo-rj"},
		"graph_path":      {"from": "team:flamengo-rj", "to": "competition:brasileirao"},
		"match_details":   {"team": "Flamengo", "opponent": "Vasco"},
		"player_profile":  {"name": "Neymar"},
		"compare_seasons": {"seasons": []any{2018, 2019}},
	}
	for _, tool := range srv.Tools() {
		if tool.Description == "" || tool.InputSchema == nil {
			t.Errorf("tool %s is not described", tool.Name)
		}
		for _, required := range tool.InputSchema.Required {
			if _, ok := tool.InputSchema.Properties[required]; !ok {
				t.Errorf("tool %s requires %q, which is not in its schema", tool.Name, required)
			}
		}
		for name, prop := range tool.InputSchema.Properties {
			if prop.Description == "" {
				t.Errorf("tool %s: argument %q has no description", tool.Name, name)
			}
		}
		args := defaults[tool.Name]
		if args == nil {
			args = map[string]any{}
		}
		result, err := srv.CallTool(tool.Name, args)
		if err != nil {
			t.Errorf("%s: %v", tool.Name, err)
			continue
		}
		if result.IsError {
			t.Errorf("%s failed on its default arguments: %s", tool.Name, text(result))
		}
		if len(result.Content) == 0 || strings.TrimSpace(result.Content[0].Text) == "" {
			t.Errorf("%s returned no prose", tool.Name)
		}
		if result.StructuredContent == nil {
			t.Errorf("%s returned no structured content", tool.Name)
		}
	}
}
