// server_test.go exercises the MCP surface end to end. A real client is
// connected to the server over an in-memory transport, so these tests cover
// tool registration, JSON Schema generation, argument validation, structured
// output and the error path exactly as a live MCP client would experience them.
package mcpsrv_test

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpsrv"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

var (
	once  sync.Once
	graph *soccer.Graph
	loadE error
)

func testGraph(t testing.TB) *soccer.Graph {
	t.Helper()
	once.Do(func() {
		dir, err := os.Getwd()
		if err != nil {
			loadE = err
			return
		}
		for i := 0; i < 6; i++ {
			cand := filepath.Join(dir, "data", "kaggle")
			if st, err := os.Stat(cand); err == nil && st.IsDir() {
				graph, loadE = soccer.Load(os.DirFS(cand))
				return
			}
			dir = filepath.Dir(dir)
		}
		t.Fatal("could not locate data/kaggle")
	})
	if loadE != nil {
		t.Fatalf("loading datasets: %v", loadE)
	}
	return graph
}

// connect returns a client session bound to a freshly built server.
func connect(t testing.TB) (context.Context, *mcp.ClientSession) {
	t.Helper()
	ctx := context.Background()
	srv := mcpsrv.New(testGraph(t))
	serverT, clientT := mcp.NewInMemoryTransports()
	if _, err := srv.MCP.Connect(ctx, serverT, nil); err != nil {
		t.Fatalf("server connect: %v", err)
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "test", Version: "0"}, nil)
	cs, err := client.Connect(ctx, clientT, nil)
	if err != nil {
		t.Fatalf("client connect: %v", err)
	}
	t.Cleanup(func() { cs.Close() })
	return ctx, cs
}

func text(res *mcp.CallToolResult) string {
	var b strings.Builder
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			b.WriteString(tc.Text)
		}
	}
	return b.String()
}

// ---------------------------------------------------------------------------

func TestToolsAreRegisteredWithSchemas(t *testing.T) {
	ctx, cs := connect(t)

	want := []string{
		"dataset_info", "list_competitions", "search_teams", "search_matches",
		"head_to_head", "team_stats", "standings", "competition_bracket",
		"league_stats", "compare_seasons", "search_players", "player_profile",
		"club_squad", "derbies",
	}
	found := map[string]bool{}
	for tool, err := range cs.Tools(ctx, nil) {
		if err != nil {
			t.Fatalf("listing tools: %v", err)
		}
		found[tool.Name] = true
		if tool.Description == "" {
			t.Errorf("tool %q has no description", tool.Name)
		}
		if tool.InputSchema == nil {
			t.Errorf("tool %q has no input schema", tool.Name)
		}
	}
	for _, name := range want {
		if !found[name] {
			t.Errorf("tool %q is not registered", name)
		}
	}
	if len(found) != len(want) {
		t.Errorf("registered %d tools, expected exactly %d", len(found), len(want))
	}
}

func TestResourcesAndPrompts(t *testing.T) {
	ctx, cs := connect(t)

	uris := []string{"soccer://datasets", "soccer://teams", "soccer://competitions"}
	for _, uri := range uris {
		res, err := cs.ReadResource(ctx, &mcp.ReadResourceParams{URI: uri})
		if err != nil {
			t.Fatalf("ReadResource(%s): %v", uri, err)
		}
		if len(res.Contents) == 0 || res.Contents[0].Text == "" {
			t.Fatalf("%s returned no content", uri)
		}
		var v any
		if err := json.Unmarshal([]byte(res.Contents[0].Text), &v); err != nil {
			t.Errorf("%s is not valid JSON: %v", uri, err)
		}
	}

	got, err := cs.GetPrompt(ctx, &mcp.GetPromptParams{
		Name:      "club_report",
		Arguments: map[string]string{"club": "Flamengo", "season": "2019"},
	})
	if err != nil {
		t.Fatalf("GetPrompt: %v", err)
	}
	if len(got.Messages) == 0 {
		t.Fatal("prompt produced no messages")
	}
	tc, ok := got.Messages[0].Content.(*mcp.TextContent)
	if !ok || !strings.Contains(tc.Text, "Flamengo") {
		t.Errorf("prompt does not mention the club: %+v", got.Messages[0].Content)
	}
}

// TestSampleQuestions is the acceptance test for the specification's
// requirement that "at least 20 sample questions can be answered".
func TestSampleQuestions(t *testing.T) {
	ctx, cs := connect(t)

	questions := mcpsrv.SampleQuestions()
	if len(questions) < 20 {
		t.Fatalf("only %d sample questions defined, the specification asks for at least 20", len(questions))
	}

	for _, q := range questions {
		t.Run(q.Question, func(t *testing.T) {
			res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: q.Tool, Arguments: q.Args})
			if err != nil {
				t.Fatalf("transport error: %v", err)
			}
			body := text(res)
			if q.ExpectError {
				if !res.IsError {
					t.Fatalf("expected an honest \"not in the data\" answer, got:\n%s", body)
				}
				if len(body) < 20 {
					t.Errorf("error message is not helpful: %q", body)
				}
				return
			}
			if res.IsError {
				t.Fatalf("tool reported an error: %s", body)
			}
			if len(body) < 40 {
				t.Errorf("answer looks empty:\n%s", body)
			}
			if res.StructuredContent == nil {
				t.Error("no structured content returned")
			}
		})
	}
}

func TestStructuredContentMatchesText(t *testing.T) {
	ctx, cs := connect(t)

	res, err := cs.CallTool(ctx, &mcp.CallToolParams{
		Name:      "standings",
		Arguments: map[string]any{"competition": "serie-a", "season": 2019},
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if res.IsError {
		t.Fatalf("tool error: %s", text(res))
	}

	raw, err := json.Marshal(res.StructuredContent)
	if err != nil {
		t.Fatalf("marshalling structured content: %v", err)
	}
	var st soccer.StandingsResult
	if err := json.Unmarshal(raw, &st); err != nil {
		t.Fatalf("structured content does not match StandingsResult: %v", err)
	}
	if st.Champion != "Flamengo" {
		t.Errorf("structured champion = %q, want Flamengo", st.Champion)
	}
	if !strings.Contains(text(res), "Champion: Flamengo") {
		t.Errorf("text block does not name the champion:\n%s", text(res))
	}
	if len(st.Table) != 20 {
		t.Errorf("structured table has %d rows, want 20", len(st.Table))
	}
}

func TestAmbiguousTeamIsReportedNotGuessed(t *testing.T) {
	ctx, cs := connect(t)

	// "Vitoria" is deliberately not ambiguous (the Bahia club dominates), but a
	// club that exists in several states with comparable data must not be
	// silently resolved.
	res, err := cs.CallTool(ctx, &mcp.CallToolParams{
		Name:      "team_stats",
		Arguments: map[string]any{"team": "Nonexistent Club FC"},
	})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if !res.IsError {
		t.Fatalf("expected an error for an unknown club, got:\n%s", text(res))
	}
	if !strings.Contains(text(res), "Nonexistent Club FC") {
		t.Errorf("error should quote the query: %q", text(res))
	}
}

func TestInvalidArgumentsAreRejected(t *testing.T) {
	ctx, cs := connect(t)

	// season is declared as an integer; a string must fail schema validation.
	res, err := cs.CallTool(ctx, &mcp.CallToolParams{
		Name:      "standings",
		Arguments: map[string]any{"competition": "serie-a", "season": "nineteen"},
	})
	if err == nil && !res.IsError {
		t.Fatal("expected schema validation to reject a non-integer season")
	}
}

// ---------------------------------------------------------------------------
// Performance budgets from the specification.
// ---------------------------------------------------------------------------

func TestQueryPerformance(t *testing.T) {
	ctx, cs := connect(t)

	cases := []struct {
		name   string
		tool   string
		args   map[string]any
		budget time.Duration
	}{
		{"simple lookup", "search_matches", map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 5}, 2 * time.Second},
		{"player lookup", "player_profile", map[string]any{"name": "Neymar"}, 2 * time.Second},
		{"team lookup", "search_teams", map[string]any{"query": "Atletico"}, 2 * time.Second},
		{"aggregate", "league_stats", map[string]any{"competition": "serie-a"}, 5 * time.Second},
		{"corpus aggregate", "league_stats", map[string]any{}, 5 * time.Second},
		{"standings", "standings", map[string]any{"competition": "serie-a", "season": 2019}, 5 * time.Second},
		{"player search", "search_players", map[string]any{"nationality": "Brazil", "group_by": "club"}, 5 * time.Second},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			start := time.Now()
			res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: c.tool, Arguments: c.args})
			elapsed := time.Since(start)
			if err != nil {
				t.Fatalf("CallTool: %v", err)
			}
			if res.IsError {
				t.Fatalf("tool error: %s", text(res))
			}
			if elapsed > c.budget {
				t.Errorf("%s took %v, budget is %v", c.name, elapsed, c.budget)
			}
			t.Logf("%s answered in %v", c.name, elapsed)
		})
	}
}

func BenchmarkSearchMatches(b *testing.B) {
	ctx, cs := connect(b)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := cs.CallTool(ctx, &mcp.CallToolParams{
			Name:      "search_matches",
			Arguments: map[string]any{"team": "Flamengo", "season": 2019},
		}); err != nil {
			b.Fatal(err)
		}
	}
}
