// steps_test.go binds the English sentences in ../features to tool calls and
// assertions, then runs every scenario as a Go subtest.
//
// Each Given/When/Then line maps to exactly one step definition. A sentence with
// no definition fails the run, and a definition no scenario uses is reported, so
// the feature files and this file cannot drift apart.
package bdd

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// steps returns the registry of step definitions.
func steps() *Registry {
	r := &Registry{}

	// ------------------------------------------------------------- Given
	r.Step("the Brazilian soccer knowledge graph is loaded", func(w *World, _ []string) error {
		if w.Graph == nil {
			return fmt.Errorf("no graph was loaded")
		}
		if s := w.Graph.Stats(); s.Matches == 0 || s.Players == 0 {
			return fmt.Errorf("the graph is empty: %+v", s)
		}
		return nil
	})
	r.Step("the MCP server is connected", func(w *World, _ []string) error {
		if w.Session == nil {
			return fmt.Errorf("no MCP session")
		}
		if got := w.Session.InitializeResult().ServerInfo.Name; got != "brazilian-soccer" {
			return fmt.Errorf("connected to %q", got)
		}
		return nil
	})

	// -------------------------------------------------------------- When
	r.Step("I search for matches between {string} and {string}", func(w *World, a []string) error {
		w.Call("head_to_head", map[string]any{"team_a": a[0], "team_b": a[1], "limit": 100})
		return nil
	})
	r.Step("I search for matches for {string} in season {int}", func(w *World, a []string) error {
		w.Call("search_matches", map[string]any{"team": a[0], "season": atoi(a[1]), "limit": 100})
		return nil
	})
	r.Step("I search for {string} matches at stage {string}", func(w *World, a []string) error {
		w.Call("search_matches", map[string]any{"competition": a[0], "stage": a[1], "limit": 100})
		return nil
	})
	r.Step("I search for {string} matches between {string} and {string}", func(w *World, a []string) error {
		w.Call("search_matches", map[string]any{"competition": a[0], "date_from": a[1], "date_to": a[2], "limit": 200})
		return nil
	})
	r.Step("I request statistics for {string} in season {int}", func(w *World, a []string) error {
		w.Call("team_stats", map[string]any{"team": a[0], "season": atoi(a[1])})
		return nil
	})
	r.Step("I request the {string} record for {string} in the {int} {string}", func(w *World, a []string) error {
		w.Call("team_stats", map[string]any{"venue": a[0], "team": a[1], "season": atoi(a[2]), "competition": a[3]})
		return nil
	})
	r.Step("I compare {string} and {string}", func(w *World, a []string) error {
		w.Call("head_to_head", map[string]any{"team_a": a[0], "team_b": a[1], "limit": 10})
		return nil
	})
	r.Step("I request the profile of {string}", func(w *World, a []string) error {
		w.Call("team_profile", map[string]any{"team": a[0], "squad_limit": 5})
		return nil
	})
	r.Step("I search for players from {string}", func(w *World, a []string) error {
		w.Call("search_players", map[string]any{"nationality": a[0], "limit": 100, "group_by_club": true})
		return nil
	})
	r.Step("I search for players at {string}", func(w *World, a []string) error {
		w.Call("search_players", map[string]any{"club": a[0], "limit": 100})
		return nil
	})
	r.Step("I search for {string} players at {string}", func(w *World, a []string) error {
		w.Call("search_players", map[string]any{"position": a[0], "club": a[1], "limit": 100})
		return nil
	})
	r.Step("I look up the player {string}", func(w *World, a []string) error {
		w.Call("player_profile", map[string]any{"name": a[0]})
		return nil
	})
	r.Step("I request the {int} {string} standings", func(w *World, a []string) error {
		w.Call("standings", map[string]any{"season": atoi(a[0]), "competition": a[1]})
		return nil
	})
	r.Step("I ask for the champions of {string}", func(w *World, a []string) error {
		w.Call("champions", map[string]any{"competition": a[0]})
		return nil
	})
	r.Step("I request the {int} {string} bracket", func(w *World, a []string) error {
		w.Call("competition_bracket", map[string]any{"season": atoi(a[0]), "competition": a[1]})
		return nil
	})
	r.Step("I compare seasons {int} and {int} of {string}", func(w *World, a []string) error {
		w.Call("competition_summary", map[string]any{"competition": a[2], "seasons": []any{atoi(a[0]), atoi(a[1])}})
		return nil
	})
	r.Step("I request aggregate statistics for {string}", func(w *World, a []string) error {
		w.Call("aggregate_stats", map[string]any{"competition": a[0], "top": 5})
		return nil
	})
	r.Step("I request aggregate statistics for all competitions", func(w *World, _ []string) error {
		w.Call("aggregate_stats", map[string]any{"top": 5})
		return nil
	})
	r.Step("I rank clubs by {string} for {string} matches in {string}", func(w *World, a []string) error {
		w.Call("team_rankings", map[string]any{"metric": a[0], "venue": a[1], "competition": a[2], "min_matches": 100, "limit": 10})
		return nil
	})
	r.Step("I rank clubs by {string} in the {int} {string}", func(w *World, a []string) error {
		w.Call("team_rankings", map[string]any{"metric": a[0], "season": atoi(a[1]), "competition": a[2], "limit": 10})
		return nil
	})
	r.Step("I request the derbies of season {int}", func(w *World, a []string) error {
		w.Call("list_derbies", map[string]any{"season": atoi(a[0])})
		return nil
	})
	r.Step("I request the dataset information", func(w *World, _ []string) error {
		w.Call("dataset_info", map[string]any{})
		return nil
	})
	r.Step("I list the clubs matching {string}", func(w *World, a []string) error {
		w.Call("list_teams", map[string]any{"query": a[0], "limit": 50})
		return nil
	})

	// -------------------------------------------------------------- Then
	r.Step("I should receive at least {int} matches", func(w *World, a []string) error {
		field := "matches"
		if w.Tool == "head_to_head" {
			field = "total_matches"
			n, err := w.number(field)
			if err != nil {
				return err
			}
			return atLeast("matches", int(n), atoi(a[0]))
		}
		list, err := w.list(field)
		if err != nil {
			return err
		}
		return atLeast("matches", len(list), atoi(a[0]))
	})
	r.Step("each match should have a date, a score and a competition", func(w *World, _ []string) error {
		for _, m := range mustMatches(w) {
			if str(m, "date") == "" || str(m, "competition") == "" {
				return fmt.Errorf("match %v is missing a date or competition", m["line"])
			}
			if _, ok := m["home_goals"]; !ok {
				return fmt.Errorf("match %v has no score", m["line"])
			}
		}
		return nil
	})
	r.Step("the answer should include a head-to-head record", func(w *World, _ []string) error {
		if err := w.ok(); err != nil {
			return err
		}
		summary, ok := w.Structured["summary"].(map[string]any)
		if !ok {
			summary, ok = w.Structured["head_to_head"].(map[string]any)
		}
		if !ok {
			return fmt.Errorf("the %s result carries no head-to-head summary", w.Tool)
		}
		if num(summary, "matches") == 0 {
			return fmt.Errorf("the head-to-head summary reports no matches")
		}
		total := num(summary, "team_a_wins") + num(summary, "team_b_wins") + num(summary, "draws")
		if total != num(summary, "matches") {
			return fmt.Errorf("wins and draws (%v) do not add up to matches (%v)", total, num(summary, "matches"))
		}
		return nil
	})
	r.Step("every match should involve {string}", func(w *World, a []string) error {
		want := strings.ToLower(a[0])
		for _, m := range mustMatches(w) {
			home := strings.ToLower(str(m, "home_team"))
			away := strings.ToLower(str(m, "away_team"))
			if !strings.Contains(home, want) && !strings.Contains(away, want) {
				return fmt.Errorf("match %q does not involve %s", str(m, "line"), a[0])
			}
		}
		return nil
	})
	r.Step("every match should be from season {int}", func(w *World, a []string) error {
		want := float64(atoi(a[0]))
		for _, m := range mustMatches(w) {
			if num(m, "season") != want {
				return fmt.Errorf("match %q is not from %s", str(m, "line"), a[0])
			}
		}
		return nil
	})
	r.Step("every match should be at stage {string}", func(w *World, a []string) error {
		for _, m := range mustMatches(w) {
			if !strings.Contains(strings.ToLower(str(m, "stage")), strings.ToLower(a[0])) {
				return fmt.Errorf("match %q is at stage %q", str(m, "line"), str(m, "stage"))
			}
		}
		return nil
	})
	r.Step("every match should fall between {string} and {string}", func(w *World, a []string) error {
		for _, m := range mustMatches(w) {
			d := str(m, "date")
			if d < a[0] || d > a[1] {
				return fmt.Errorf("match %q is outside %s..%s", str(m, "line"), a[0], a[1])
			}
		}
		return nil
	})
	r.Step("the answer should mention {string}", func(w *World, a []string) error {
		if err := w.ok(); err != nil {
			return err
		}
		if !strings.Contains(w.Text, a[0]) {
			return fmt.Errorf("the %s answer does not mention %q:\n%s", w.Tool, a[0], clip(w.Text))
		}
		return nil
	})
	r.Step("the call should fail with a message mentioning {string}", func(w *World, a []string) error {
		if w.CallErr == nil {
			return fmt.Errorf("the %s call unexpectedly succeeded", w.Tool)
		}
		if !strings.Contains(strings.ToLower(w.CallErr.Error()), strings.ToLower(a[0])) {
			return fmt.Errorf("error %q does not mention %q", w.CallErr, a[0])
		}
		return nil
	})
	r.Step("the answer should report wins, draws and losses", func(w *World, _ []string) error {
		overall, err := record(w)
		if err != nil {
			return err
		}
		played := num(overall, "played")
		if played == 0 {
			return fmt.Errorf("no matches in the record")
		}
		if num(overall, "wins")+num(overall, "draws")+num(overall, "losses") != played {
			return fmt.Errorf("wins, draws and losses do not add up to %v matches", played)
		}
		return nil
	})
	r.Step("the answer should report goals for and against", func(w *World, _ []string) error {
		overall, err := record(w)
		if err != nil {
			return err
		}
		if _, ok := overall["goals_for"]; !ok {
			return fmt.Errorf("the record has no goals_for")
		}
		if _, ok := overall["goals_against"]; !ok {
			return fmt.Errorf("the record has no goals_against")
		}
		if num(overall, "goal_difference") != num(overall, "goals_for")-num(overall, "goals_against") {
			return fmt.Errorf("goal difference is inconsistent")
		}
		return nil
	})
	r.Step("I should receive at least {int} players", func(w *World, a []string) error {
		// The tool caps how many players it returns, so the assertion is about
		// how many the dataset holds.
		total, err := w.number("total_matching")
		if err != nil {
			return err
		}
		if _, err := w.list("players"); err != nil {
			return err
		}
		return atLeast("players", int(total), atoi(a[0]))
	})
	r.Step("every returned player should be from {string}", func(w *World, a []string) error {
		list, err := w.list("players")
		if err != nil {
			return err
		}
		for _, p := range list {
			if str(p, "nationality") != a[0] {
				return fmt.Errorf("%s is from %s", str(p, "name"), str(p, "nationality"))
			}
		}
		return nil
	})
	r.Step("every returned player should be at {string}", func(w *World, a []string) error {
		list, err := w.list("players")
		if err != nil {
			return err
		}
		for _, p := range list {
			if !strings.Contains(strings.ToLower(str(p, "club")), strings.ToLower(a[0])) {
				return fmt.Errorf("%s plays for %s", str(p, "name"), str(p, "club"))
			}
		}
		return nil
	})
	r.Step("every returned player should play as a {string}", func(w *World, a []string) error {
		list, err := w.list("players")
		if err != nil {
			return err
		}
		for _, p := range list {
			if str(p, "position_group") != a[0] {
				return fmt.Errorf("%s plays %s, which is a %s", str(p, "name"), str(p, "position"), str(p, "position_group"))
			}
		}
		return nil
	})
	r.Step("the champion should be {string}", func(w *World, a []string) error {
		champ, err := w.text("champion")
		if err != nil {
			return err
		}
		if champ != a[0] {
			return fmt.Errorf("champion is %q, want %q", champ, a[0])
		}
		return nil
	})
	r.Step("the table should have {int} rows", func(w *World, a []string) error {
		rows, err := w.list("table")
		if err != nil {
			return err
		}
		if len(rows) != atoi(a[0]) {
			return fmt.Errorf("the table has %d rows, want %s", len(rows), a[0])
		}
		return nil
	})
	r.Step("every club should have played {int} matches", func(w *World, a []string) error {
		rows, err := w.list("table")
		if err != nil {
			return err
		}
		want := float64(atoi(a[0]))
		for _, row := range rows {
			if num(row, "played") != want {
				return fmt.Errorf("%s played %v matches, want %s", str(row, "team"), num(row, "played"), a[0])
			}
		}
		return nil
	})
	r.Step("the relegated clubs should include {string}", func(w *World, a []string) error {
		if err := w.ok(); err != nil {
			return err
		}
		raw, ok := w.Structured["relegated"].([]any)
		if !ok {
			return fmt.Errorf("the standings carry no relegation list")
		}
		for _, item := range raw {
			if s, _ := item.(string); s == a[0] {
				return nil
			}
		}
		return fmt.Errorf("%q is not among the relegated clubs %v", a[0], raw)
	})
	r.Step("the answer should report a home advantage", func(w *World, _ []string) error {
		home, err := w.number("home_win_percent")
		if err != nil {
			return err
		}
		away, err := w.number("away_win_percent")
		if err != nil {
			return err
		}
		if home <= away {
			return fmt.Errorf("home win rate %.1f%% is not above the away rate %.1f%%", home, away)
		}
		return nil
	})
	r.Step("the average goals per match should be between {int} and {int}", func(w *World, a []string) error {
		gpm, err := w.number("goals_per_match")
		if err != nil {
			return err
		}
		lo, hi := float64(atoi(a[0])), float64(atoi(a[1]))
		if gpm < lo || gpm > hi {
			return fmt.Errorf("goals per match is %.2f, outside %v..%v", gpm, lo, hi)
		}
		return nil
	})
	r.Step("I should receive at least {int} ranked clubs", func(w *World, a []string) error {
		rows, err := w.list("rankings")
		if err != nil {
			return err
		}
		return atLeast("ranked clubs", len(rows), atoi(a[0]))
	})
	r.Step("every ranked club should have played at least {int} matches", func(w *World, a []string) error {
		rows, err := w.list("rankings")
		if err != nil {
			return err
		}
		want := float64(atoi(a[0]))
		for _, row := range rows {
			rec, _ := row["record"].(map[string]any)
			if rec == nil || num(rec, "played") < want {
				return fmt.Errorf("%s has too few matches", str(row, "team"))
			}
		}
		return nil
	})
	r.Step("the top ranked club should be {string}", func(w *World, a []string) error {
		rows, err := w.list("rankings")
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			return fmt.Errorf("the ranking is empty")
		}
		if str(rows[0], "team") != a[0] {
			return fmt.Errorf("the top club is %q, want %q", str(rows[0], "team"), a[0])
		}
		return nil
	})
	r.Step("the answer should arrive in under {int} seconds", func(w *World, a []string) error {
		if err := w.ok(); err != nil {
			return err
		}
		budget := time.Duration(atoi(a[0])) * time.Second
		if w.Elapsed > budget {
			return fmt.Errorf("the %s call took %v, the budget is %v", w.Tool, w.Elapsed, budget)
		}
		return nil
	})
	return r
}

// mustMatches pulls the match list out of whichever tool produced it.
func mustMatches(w *World) []map[string]any {
	list, err := w.list("matches")
	if err != nil {
		return nil
	}
	return list
}

// record pulls the headline record out of a team_stats result.
func record(w *World) (map[string]any, error) {
	if err := w.ok(); err != nil {
		return nil, err
	}
	overall, ok := w.Structured["overall"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("the %s result carries no overall record", w.Tool)
	}
	return overall, nil
}

func atLeast(what string, got, want int) error {
	if got < want {
		return fmt.Errorf("received %d %s, expected at least %d", got, what, want)
	}
	return nil
}

func atoi(s string) int {
	n, _ := strconv.Atoi(s)
	return n
}

func clip(s string) string {
	if len(s) <= 600 {
		return s
	}
	return s[:600] + "..."
}

// TestFeatures parses every feature file and runs every scenario.
func TestFeatures(t *testing.T) {
	features, err := ParseDir("../features")
	if err != nil {
		t.Fatalf("reading the feature files: %v", err)
	}
	graph, err := soccer.Load("")
	if err != nil {
		t.Fatalf("loading the datasets: %v", err)
	}
	world, err := NewWorld(context.Background(), graph)
	if err != nil {
		t.Fatalf("starting the MCP session: %v", err)
	}
	defer world.Close()

	registry := steps()
	scenarios := 0
	for _, f := range features {
		t.Run(f.Name, func(t *testing.T) {
			for _, sc := range f.Scenarios {
				scenarios++
				t.Run(sc.Name, func(t *testing.T) {
					// Each scenario starts from a clean result slate but reuses
					// the session; the server holds no per-client state.
					world.Text, world.Structured, world.CallErr, world.Tool = "", nil, nil, ""
					for _, step := range f.AllSteps(sc) {
						if err := registry.Execute(world, step); err != nil {
							t.Fatalf("%s %s\n    %v", step.Keyword, step.Text, err)
						}
					}
				})
			}
		})
	}
	if scenarios < 20 {
		t.Errorf("only %d scenarios were run", scenarios)
	}
	if unused := registry.UnusedPatterns(); len(unused) > 0 {
		t.Errorf("these step definitions are never exercised by a feature file: %v", unused)
	}
}

// TestGherkinParser covers the parser itself, including background steps and the
// And/But keyword inheriting the previous one.
func TestGherkinParser(t *testing.T) {
	features, err := ParseDir("../features")
	if err != nil {
		t.Fatal(err)
	}
	if len(features) < 5 {
		t.Errorf("expected at least five feature files, found %d", len(features))
	}
	for _, f := range features {
		if len(f.Background) == 0 {
			t.Errorf("%s has no Background", f.Path)
		}
		for _, sc := range f.Scenarios {
			if len(sc.Steps) == 0 {
				t.Errorf("%s: scenario %q has no steps", f.Path, sc.Name)
			}
			for _, step := range sc.Steps {
				switch step.Keyword {
				case "Given", "When", "Then":
				default:
					t.Errorf("%s: step %q has unresolved keyword %q", f.Path, step.Text, step.Keyword)
				}
			}
			if all := f.AllSteps(sc); len(all) != len(f.Background)+len(sc.Steps) {
				t.Errorf("%s: background steps are not prepended to %q", f.Path, sc.Name)
			}
		}
	}
}
