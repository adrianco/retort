package mcpserver

import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// These tests drive the server through a real MCP client over an in-memory
// transport, so they exercise the protocol handshake, the generated JSON
// schemas and the argument marshalling — not just the query layer underneath.

const testDataDir = "../../data/kaggle"

var (
	graphOnce sync.Once
	sharedG   *soccer.Graph
	graphErr  error
)

func testGraph(t *testing.T) *soccer.Graph {
	t.Helper()
	graphOnce.Do(func() {
		if _, err := os.Stat(testDataDir); err != nil {
			graphErr = err
			return
		}
		sharedG, graphErr = soccer.Load(testDataDir)
	})
	if graphErr != nil {
		t.Fatalf("loading %s: %v", testDataDir, graphErr)
	}
	return sharedG
}

// connect starts the server on an in-memory transport and returns a connected
// client session.
func connect(t *testing.T) (*mcp.ClientSession, context.Context) {
	t.Helper()
	ctx := context.Background()
	server := New(testGraph(t))
	clientT, serverT := mcp.NewInMemoryTransports()

	serverDone := make(chan struct{})
	go func() {
		defer close(serverDone)
		if err := server.Run(ctx, serverT); err != nil {
			t.Errorf("server.Run: %v", err)
		}
	}()

	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "1"}, nil)
	session, err := client.Connect(ctx, clientT, nil)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	t.Cleanup(func() {
		session.Close()
		<-serverDone
	})
	return session, ctx
}

// call invokes a tool and returns its text block, failing the test on a tool
// error.
func call(t *testing.T, s *mcp.ClientSession, ctx context.Context, name string, args map[string]any) string {
	t.Helper()
	res, err := s.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		t.Fatalf("%s(%v): transport error: %v", name, args, err)
	}
	text := toolText(res)
	if res.IsError {
		t.Fatalf("%s(%v): tool error: %s", name, args, text)
	}
	return text
}

// callExpectingError invokes a tool that should report a tool-level error.
func callExpectingError(t *testing.T, s *mcp.ClientSession, ctx context.Context, name string, args map[string]any) string {
	t.Helper()
	res, err := s.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		t.Fatalf("%s: transport error: %v", name, err)
	}
	if !res.IsError {
		t.Fatalf("%s(%v) should have failed, got: %s", name, args, toolText(res))
	}
	return toolText(res)
}

func toolText(res *mcp.CallToolResult) string {
	var b strings.Builder
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			b.WriteString(tc.Text)
		}
	}
	return b.String()
}

func TestServerHandshakeAndToolList(t *testing.T) {
	session, ctx := connect(t)

	if got := session.InitializeResult().ServerInfo.Name; got != "brazilian-soccer" {
		t.Errorf("server name = %q", got)
	}
	if instr := session.InitializeResult().Instructions; !strings.Contains(instr, "Brasileirão") {
		t.Errorf("instructions should describe coverage, got %q", instr)
	}

	res, err := session.ListTools(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	byName := map[string]*mcp.Tool{}
	for _, tool := range res.Tools {
		byName[tool.Name] = tool
	}
	want := []string{
		"find_matches", "team_statistics", "head_to_head", "compare_teams",
		"search_teams", "find_players", "club_squad", "brazilian_club_ratings",
		"league_standings", "competition_stats", "team_leaderboard",
		"compare_seasons", "find_derbies", "dataset_info",
	}
	for _, name := range want {
		tool, ok := byName[name]
		if !ok {
			t.Errorf("tool %q missing; have %v", name, keys(byName))
			continue
		}
		if tool.Description == "" {
			t.Errorf("tool %q has no description", name)
		}
		if tool.InputSchema == nil {
			t.Errorf("tool %q has no input schema", name)
		}
	}
	if len(res.Tools) != len(want) {
		t.Errorf("got %d tools, want %d: %v", len(res.Tools), len(want), keys(byName))
	}
}

func keys[V any](m map[string]V) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

// TestSampleQuestions walks the sample questions from the specification end to
// end through the MCP protocol, asserting on the prose an LLM would receive.
func TestSampleQuestions(t *testing.T) {
	session, ctx := connect(t)

	cases := []struct {
		question string
		tool     string
		args     map[string]any
		want     []string // substrings that must appear in the answer
	}{
		{
			question: "Show me all Flamengo vs Fluminense matches",
			tool:     "find_matches",
			args:     map[string]any{"team": "Flamengo", "opponent": "Fluminense", "limit": 5},
			want:     []string{"Flamengo", "Fluminense", "Head-to-head in dataset", "more matches in dataset"},
		},
		{
			question: "What matches did Palmeiras play in 2023?",
			tool:     "find_matches",
			args:     map[string]any{"team": "Palmeiras", "season": 2023, "limit": 10},
			want:     []string{"Palmeiras", "2023-"},
		},
		{
			question: "Find all Copa do Brasil finals",
			tool:     "find_matches",
			args:     map[string]any{"competition": "copa do brasil", "round": "Final", "limit": 50},
			want:     []string{"Copa do Brasil Final"},
		},
		{
			question: "When did Flamengo last play Corinthians?",
			tool:     "find_matches",
			args:     map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
			want:     []string{"Flamengo", "Corinthians"},
		},
		{
			question: "Show me all derbies in 2023",
			tool:     "find_derbies",
			args:     map[string]any{"season": 2023},
			want:     []string{"Fla-Flu", "2023-"},
		},
		{
			question: "What is Corinthians' home record in 2022?",
			tool:     "team_statistics",
			args:     map[string]any{"team": "Corinthians", "season": 2022, "venue": "home", "competition": "serie a"},
			want:     []string{"Corinthians record", "19 matches", "win rate"},
		},
		{
			question: "Compare Palmeiras and Santos head-to-head",
			tool:     "compare_teams",
			args:     map[string]any{"team_a": "Palmeiras", "team_b": "Santos"},
			want:     []string{"Palmeiras record", "Santos record", "Head-to-head in dataset"},
		},
		{
			question: "Which team scored the most goals in Serie A 2023?",
			tool:     "team_leaderboard",
			args:     map[string]any{"metric": "goals_for", "competition": "serie a", "season": 2023, "limit": 5},
			want:     []string{"ranked by goals_for", " 1. "},
		},
		{
			question: "Which team has the best home record?",
			tool:     "team_leaderboard",
			args: map[string]any{"metric": "win_rate", "competition": "brasileirao",
				"venue": "home", "min_matches": 100, "limit": 5},
			want: []string{"ranked by win_rate", " 1. "},
		},
		{
			question: "Which team has the best away record?",
			tool:     "team_leaderboard",
			args: map[string]any{"metric": "win_rate", "competition": "brasileirao",
				"venue": "away", "min_matches": 100, "limit": 5},
			want: []string{"ranked by win_rate"},
		},
		{
			question: "Find all Brazilian players in the dataset",
			tool:     "find_players",
			args:     map[string]any{"nationality": "Brazil", "limit": 5},
			want:     []string{"Neymar", "Overall:", "Brazil", "more players match"},
		},
		{
			question: "Who are the highest-rated players at Gremio?",
			tool:     "find_players",
			args:     map[string]any{"club": "Gremio", "limit": 5},
			want:     []string{"Overall:", "Grêmio"},
		},
		{
			// São Paulo, Flamengo, Corinthians and Palmeiras are absent from the
			// FIFA 19 snapshot for licensing reasons, so this uses a club the
			// dataset does carry.
			question: "Show me all forwards from Santos",
			tool:     "find_players",
			args:     map[string]any{"club": "Santos", "position": "ST"},
			want:     []string{"Position: ST", "Club: Santos"},
		},
		{
			question: "Which players play for Internacional?",
			tool:     "club_squad",
			args:     map[string]any{"club": "Internacional", "include_players": true},
			want:     []string{"average rating", "fixture data", "Overall:"},
		},
		{
			question: "Brazilian players at Brazilian clubs",
			tool:     "brazilian_club_ratings",
			args:     map[string]any{"nationality": "Brazil", "limit": 10},
			want:     []string{"avg rating", "matches in fixture data"},
		},
		{
			question: "Who won the 2019 Brasileirao?",
			tool:     "league_standings",
			args:     map[string]any{"competition": "brasileirao", "season": 2019},
			want: []string{"2019 Brasileirão Série A Final Standings",
				" 1. Flamengo", "90 pts", "Champion", "calculated from match results"},
		},
		{
			question: "Which teams were relegated in 2020?",
			tool:     "league_standings",
			args:     map[string]any{"season": 2020},
			want:     []string{"Relegated", "17.", "20."},
		},
		{
			question: "What's the average goals per match in the Brasileirao?",
			tool:     "competition_stats",
			args:     map[string]any{"competition": "brasileirao"},
			want:     []string{"Average goals per match:", "Home win rate:"},
		},
		{
			question: "Show me the biggest wins in the dataset",
			tool:     "competition_stats",
			args:     map[string]any{"top_n": 5},
			want:     []string{"Biggest victories:", "1. ", "5. "},
		},
		{
			question: "Compare the 2018 and 2019 seasons",
			tool:     "compare_seasons",
			args:     map[string]any{"competition": "brasileirao", "season_a": 2018, "season_b": 2019},
			want:     []string{"2018 vs 2019", "goals/match", "home win%"},
		},
		{
			question: "What competitions has Palmeiras played in?",
			tool:     "search_teams",
			args:     map[string]any{"query": "Palmeiras"},
			want:     []string{"Palmeiras", "Copa Libertadores", "Copa do Brasil"},
		},
		{
			question: "How much data is loaded?",
			tool:     "dataset_info",
			args:     map[string]any{},
			want:     []string{"unique_matches", "rows_per_file", "fifa_data.csv"},
		},
		{
			question: "Show me the 2018 Copa Libertadores results",
			tool:     "find_matches",
			args:     map[string]any{"competition": "libertadores", "season": 2018, "limit": 10},
			want:     []string{"Copa Libertadores"},
		},
		{
			question: "Head-to-head: Gremio vs Internacional (the Grenal)",
			tool:     "head_to_head",
			args:     map[string]any{"team_a": "Gremio", "team_b": "Internacional"},
			want:     []string{"Grêmio", "Internacional", "meetings", "First meeting"},
		},
	}

	if len(cases) < 20 {
		t.Fatalf("the specification asks for at least 20 answerable questions, this suite has %d", len(cases))
	}

	for _, c := range cases {
		t.Run(c.question, func(t *testing.T) {
			start := time.Now()
			got := call(t, session, ctx, c.tool, c.args)
			if elapsed := time.Since(start); elapsed > 5*time.Second {
				t.Errorf("took %s, budget is 5s", elapsed)
			}
			for _, w := range c.want {
				if !strings.Contains(got, w) {
					t.Errorf("answer to %q is missing %q.\n--- got ---\n%s", c.question, w, got)
				}
			}
		})
	}
}

// TestStructuredContent checks that each tool also returns machine-readable
// JSON alongside its prose, which is what lets a client post-process results.
func TestStructuredContent(t *testing.T) {
	session, ctx := connect(t)

	res, err := session.CallTool(ctx, &mcp.CallToolParams{
		Name:      "league_standings",
		Arguments: map[string]any{"competition": "brasileirao", "season": 2019},
	})
	if err != nil {
		t.Fatal(err)
	}
	if res.StructuredContent == nil {
		t.Fatal("expected structured content alongside the text block")
	}
	raw, err := json.Marshal(res.StructuredContent)
	if err != nil {
		t.Fatal(err)
	}
	var standings struct {
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		Champion    string `json:"champion"`
		Table       []struct {
			Position int    `json:"position"`
			Team     string `json:"team"`
			Points   int    `json:"points"`
		} `json:"table"`
	}
	if err := json.Unmarshal(raw, &standings); err != nil {
		t.Fatalf("structured content is not the documented shape: %v\n%s", err, raw)
	}
	if standings.Season != 2019 || standings.Champion != "Flamengo" {
		t.Errorf("unexpected standings: %+v", standings)
	}
	if len(standings.Table) != 20 || standings.Table[0].Points != 90 {
		t.Errorf("unexpected table head: %+v", standings.Table)
	}
}

func TestToolErrorsAreInformative(t *testing.T) {
	session, ctx := connect(t)

	cases := []struct {
		name   string
		tool   string
		args   map[string]any
		expect string
	}{
		{
			name:   "unknown club",
			tool:   "team_statistics",
			args:   map[string]any{"team": "Manchester United"},
			expect: "no team matching",
		},
		{
			name:   "league table for a knockout cup",
			tool:   "league_standings",
			args:   map[string]any{"competition": "copa do brasil", "season": 2019},
			expect: "find_matches",
		},
		{
			name:   "season with no data",
			tool:   "league_standings",
			args:   map[string]any{"competition": "brasileirao", "season": 1975},
			expect: "no data found",
		},
		{
			name:   "unknown leaderboard metric",
			tool:   "team_leaderboard",
			args:   map[string]any{"metric": "possession"},
			expect: "unknown metric",
		},
		{
			name:   "malformed date",
			tool:   "find_matches",
			args:   map[string]any{"date_from": "last tuesday"},
			expect: "YYYY-MM-DD",
		},
		{
			name:   "player search with no hits",
			tool:   "find_players",
			args:   map[string]any{"name": "Nobody McNobody"},
			expect: "no players matched",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			msg := callExpectingError(t, session, ctx, c.tool, c.args)
			if !strings.Contains(msg, c.expect) {
				t.Errorf("error message %q should contain %q", msg, c.expect)
			}
		})
	}
}

// TestSuggestionsOnNearMiss checks that a misspelled club name comes back with
// candidates rather than a bare failure.
func TestSuggestionsOnNearMiss(t *testing.T) {
	session, ctx := connect(t)
	msg := callExpectingError(t, session, ctx, "team_statistics",
		map[string]any{"team": "Flamengoo FC XYZ"})
	if !strings.Contains(msg, "did you mean") {
		t.Errorf("expected suggestions for a near miss, got %q", msg)
	}
}

// TestTeamNameVariationsThroughProtocol is the end-to-end version of the name
// normalisation requirement: every spelling must return the same answer.
func TestTeamNameVariationsThroughProtocol(t *testing.T) {
	session, ctx := connect(t)

	groups := [][]string{
		{"Flamengo", "Flamengo-RJ", "flamengo - rj", "CR Flamengo"},
		{"Gremio", "Grêmio", "Grêmio - RS", "Gremio RS"},
		{"Sao Paulo", "São Paulo", "São Paulo - SP"},
		{"Atletico-MG", "Atlético Mineiro", "Atlético - MG"},
		{"Sport", "Sport Recife", "Sport Club do Recife"},
	}
	for _, group := range groups {
		var first string
		for i, name := range group {
			got := call(t, session, ctx, "team_statistics", map[string]any{"team": name})
			if i == 0 {
				first = got
				continue
			}
			if got != first {
				t.Errorf("%q and %q gave different answers:\n--- %s ---\n%s\n--- %s ---\n%s",
					group[0], name, group[0], first, name, got)
			}
		}
	}
}

// TestConcurrentToolCalls checks the server handles interleaved requests.
func TestConcurrentToolCalls(t *testing.T) {
	session, ctx := connect(t)
	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			res, err := session.CallTool(ctx, &mcp.CallToolParams{
				Name:      "league_standings",
				Arguments: map[string]any{"season": 2014 + i%8},
			})
			if err != nil {
				t.Errorf("concurrent call %d: %v", i, err)
				return
			}
			if res.IsError {
				t.Errorf("concurrent call %d failed: %s", i, toolText(res))
			}
		}(i)
	}
	wg.Wait()
}

// TestSimpleLookupLatency enforces the specification's 2 second budget for
// simple lookups, measured through the full protocol round trip.
func TestSimpleLookupLatency(t *testing.T) {
	session, ctx := connect(t)
	lookups := []struct {
		tool string
		args map[string]any
	}{
		{"find_matches", map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 1}},
		{"head_to_head", map[string]any{"team_a": "Santos", "team_b": "Palmeiras"}},
		{"find_players", map[string]any{"name": "Neymar"}},
		{"search_teams", map[string]any{"query": "atletico"}},
		{"team_statistics", map[string]any{"team": "Palmeiras", "season": 2019}},
	}
	for _, l := range lookups {
		start := time.Now()
		call(t, session, ctx, l.tool, l.args)
		if elapsed := time.Since(start); elapsed > 2*time.Second {
			t.Errorf("%s took %s, budget is 2s", l.tool, elapsed)
		}
	}
}
