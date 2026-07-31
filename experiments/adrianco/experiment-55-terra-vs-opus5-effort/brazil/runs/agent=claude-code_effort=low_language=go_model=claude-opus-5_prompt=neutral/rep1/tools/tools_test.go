// tools_test.go drives the whole server end to end: the real datasets are
// loaded, the tools are registered on an MCP server, and every sample question
// from the specification is asked as a tools/call JSON-RPC request. Each case
// asserts on the text the model would actually receive.
package tools

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/soccer"
)

var (
	once   sync.Once
	server *mcp.Server
	setErr error
)

const dataDir = "../data/kaggle"

// srv builds the server once for the whole test binary.
func srv(t testing.TB) *mcp.Server {
	t.Helper()
	once.Do(func() {
		if _, err := os.Stat(filepath.Clean(dataDir)); err != nil {
			setErr = err
			return
		}
		var store *soccer.Store
		store, setErr = soccer.Load(dataDir)
		if setErr != nil {
			return
		}
		server = mcp.NewServer("brazilian-soccer", "test", Instructions)
		Register(server, store)
	})
	if setErr != nil {
		t.Skipf("datasets not available: %v", setErr)
	}
	return server
}

// ask performs a tools/call and returns the text content plus the error flag.
func ask(t *testing.T, tool string, args map[string]any) (string, bool) {
	t.Helper()
	raw, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{"name": tool, "arguments": args},
	})
	if err != nil {
		t.Fatal(err)
	}
	resp, send := srv(t).HandleMessage(raw)
	if !send {
		t.Fatal("expected a response")
	}
	if resp.Error != nil {
		t.Fatalf("%s: protocol error %v", tool, resp.Error)
	}
	res, ok := resp.Result.(*mcp.CallToolResult)
	if !ok {
		t.Fatalf("%s: unexpected result type %T", tool, resp.Result)
	}
	var b strings.Builder
	for _, c := range res.Content {
		b.WriteString(c.Text)
	}
	return b.String(), res.IsError
}

// mustAsk fails the test if the tool reported an error.
func mustAsk(t *testing.T, tool string, args map[string]any) string {
	t.Helper()
	out, isErr := ask(t, tool, args)
	if isErr {
		t.Fatalf("%s returned an error: %s", tool, out)
	}
	return out
}

func TestToolCatalogue(t *testing.T) {
	tools := srv(t).Tools()
	if len(tools) < 12 {
		t.Fatalf("expected the full tool catalogue, got %d", len(tools))
	}
	seen := map[string]bool{}
	for _, tl := range tools {
		if tl.Description == "" {
			t.Errorf("tool %q has no description", tl.Name)
		}
		if tl.InputSchema.Type != "object" {
			t.Errorf("tool %q has a non-object input schema", tl.Name)
		}
		for _, req := range tl.InputSchema.Required {
			if _, ok := tl.InputSchema.Properties[req]; !ok {
				t.Errorf("tool %q requires %q which is not declared", tl.Name, req)
			}
		}
		seen[tl.Name] = true
	}
	for _, want := range []string{
		"search_matches", "head_to_head", "team_stats", "standings", "rank_teams",
		"competition_stats", "biggest_wins", "search_players", "get_player",
		"club_squads", "list_teams", "list_competitions", "dataset_info",
	} {
		if !seen[want] {
			t.Errorf("tool %q is missing", want)
		}
	}
}

// TestSampleQuestions walks the sample questions listed in the specification.
// Each entry names the question, the tool an LLM would pick, its arguments and
// the substrings the answer must contain.
func TestSampleQuestions(t *testing.T) {
	cases := []struct {
		question string
		tool     string
		args     map[string]any
		want     []string
	}{
		// --- Match queries
		{
			"Show me all Flamengo vs Fluminense matches",
			"search_matches", map[string]any{"team": "Flamengo", "opponent": "Fluminense", "limit": 5},
			[]string{"Flamengo", "Fluminense", "more matches in dataset"},
		},
		{
			"What matches did Palmeiras play in 2023?",
			"search_matches", map[string]any{"team": "Palmeiras", "season": 2023},
			[]string{"Palmeiras", "2023"},
		},
		{
			"Find all Copa do Brasil finals",
			"search_matches", map[string]any{"competition": "Copa do Brasil", "stage": "final", "limit": 5},
			[]string{"Copa do Brasil", "final"},
		},
		{
			"When did Flamengo last play Corinthians, and what was the score?",
			"search_matches", map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
			[]string{"Flamengo", "Corinthians"},
		},
		{
			"Show me the Fla-Flu matches in 2023",
			"search_matches", map[string]any{"team": "Flamengo", "opponent": "Fluminense", "from": "2023-01-01", "to": "2023-12-31"},
			[]string{"2023-"},
		},
		{
			"Which matches were played in round 22 of the 2019 Brasileirao?",
			"search_matches", map[string]any{"competition": "Brasileirao", "season": 2019, "round": "22", "limit": 50},
			[]string{"round 22"},
		},

		// --- Team queries
		{
			"What is Corinthians' home record in 2022?",
			"team_stats", map[string]any{"team": "Corinthians", "season": 2022, "competition": "Serie A", "venue": "home"},
			[]string{"Corinthians", "19 matches", "win rate"},
		},
		{
			"Compare Palmeiras and Santos head-to-head",
			"head_to_head", map[string]any{"team_a": "Palmeiras", "team_b": "Santos", "limit": 5},
			[]string{"Palmeiras", "Santos", "wins", "draws"},
		},
		{
			"Which team scored the most goals in Serie A 2019?",
			"rank_teams", map[string]any{"competition": "Serie A", "season": 2019, "metric": "goals_for", "limit": 3},
			[]string{"Teams ranked by goals_for", "GF"},
		},
		{
			"Which team has the best home record?",
			"rank_teams", map[string]any{"competition": "Serie A", "venue": "home", "metric": "win_rate", "min_matches": 100, "limit": 5},
			[]string{"win rate"},
		},
		{
			"Which team has the best away record in 2019?",
			"rank_teams", map[string]any{"competition": "Serie A", "season": 2019, "venue": "away", "metric": "points", "limit": 5},
			[]string{"pts"},
		},
		{
			"What competitions has Palmeiras played in?",
			"list_teams", map[string]any{"query": "Palmeiras", "limit": 3},
			[]string{"Palmeiras", "Copa Libertadores", "Copa do Brasil"},
		},

		// --- Player queries
		{
			// The FIFA 19 data has no Gabriel Barbosa entry, so get_player falls
			// back to the name parts and offers the Gabriels it does have.
			"Who is Gabriel Barbosa?",
			"get_player", map[string]any{"name": "Gabriel Barbosa"},
			[]string{"Overall", "Nationality"},
		},
		{
			"Find all Brazilian players in the dataset",
			"search_players", map[string]any{"nationality": "Brazil", "limit": 5},
			[]string{"Brazil", "more players matched"},
		},
		{
			"Who are the top Brazilian players?",
			"search_players", map[string]any{"nationality": "Brazil", "limit": 3, "sort_by": "overall"},
			[]string{"Neymar"},
		},
		{
			"Which players play for Gremio?",
			"search_players", map[string]any{"club": "Gremio", "limit": 5},
			[]string{"Overall"},
		},
		{
			"Show me all forwards from Santos",
			"search_players", map[string]any{"club": "Santos", "position": "forward", "limit": 10},
			[]string{"Santos"},
		},
		{
			"Which Brazilian clubs have the deepest squads?",
			"club_squads", map[string]any{"nationality": "Brazil", "limit": 5},
			[]string{"players (avg rating"},
		},

		// --- Competition queries
		{
			"Who won the 2019 Brasileirao?",
			"standings", map[string]any{"season": 2019, "top": 5},
			[]string{"Flamengo", "90 pts", "Champion"},
		},
		{
			"Which teams were relegated in 2020?",
			"standings", map[string]any{"season": 2020, "bottom": 4},
			[]string{"17.", "20."},
		},
		{
			"Show the 2018 Copa Libertadores knockout matches",
			"search_matches", map[string]any{"competition": "Libertadores", "season": 2018, "stage": "final"},
			[]string{"Copa Libertadores"},
		},
		{
			"What competitions are covered by the data?",
			"list_competitions", map[string]any{},
			[]string{"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"},
		},

		// --- Statistical analysis
		{
			"What's the average goals per match in the Brasileirao?",
			"competition_stats", map[string]any{"competition": "Brasileirao"},
			[]string{"per match", "home wins"},
		},
		{
			"Show me the biggest wins in the dataset",
			"biggest_wins", map[string]any{"limit": 5},
			[]string{"Biggest victories"},
		},
		{
			"Compare the 2018 and 2019 seasons",
			"competition_stats", map[string]any{"competition": "Serie A", "season": 2018},
			[]string{"Matches: 380"},
		},
		{
			"How much data is loaded?",
			"dataset_info", map[string]any{},
			[]string{"matches", "players"},
		},
	}

	if len(cases) < 20 {
		t.Fatalf("the specification asks for at least 20 answerable questions, only %d covered", len(cases))
	}

	for _, c := range cases {
		t.Run(c.question, func(t *testing.T) {
			start := time.Now()
			out := mustAsk(t, c.tool, c.args)
			if d := time.Since(start); d > 5*time.Second {
				t.Errorf("answering took %s, budget is 5s", d)
			}
			for _, want := range c.want {
				if !strings.Contains(out, want) {
					t.Errorf("answer does not mention %q:\n%s", want, out)
				}
			}
		})
	}
}

func TestStructuredContentAccompaniesText(t *testing.T) {
	raw, _ := json.Marshal(map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{"name": "standings", "arguments": map[string]any{"season": 2019, "top": 3}},
	})
	resp, _ := srv(t).HandleMessage(raw)
	res := resp.Result.(*mcp.CallToolResult)
	if res.StructuredContent == nil {
		t.Fatal("expected structured content alongside the text rendering")
	}
	// It must survive a JSON round trip for real MCP clients.
	blob, err := json.Marshal(res.StructuredContent)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(blob), "Flamengo") {
		t.Errorf("structured content looks wrong: %s", blob)
	}
}

func TestMissingAndBadArgumentsAreReportedNicely(t *testing.T) {
	cases := []struct {
		tool string
		args map[string]any
		want string
	}{
		{"head_to_head", map[string]any{"team_a": "Flamengo"}, "team_b"},
		{"team_stats", map[string]any{}, "team"},
		{"standings", map[string]any{}, "season"},
		{"get_player", map[string]any{"name": "Zzzqqq Wxyzzy"}, "no player"},
		{"team_stats", map[string]any{"team": "Nowhere FC"}, "unknown team"},
		{"standings", map[string]any{"season": 1899}, "no "},
		{"head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Flamengo-RJ"}, "same club"},
	}
	for _, c := range cases {
		out, isErr := ask(t, c.tool, c.args)
		if !isErr {
			t.Errorf("%s%v should have failed, got:\n%s", c.tool, c.args, out)
			continue
		}
		if !strings.Contains(strings.ToLower(out), c.want) {
			t.Errorf("%s%v error should mention %q, got %q", c.tool, c.args, c.want, out)
		}
	}
}

func TestArgumentsArriveAsStringsOrNumbers(t *testing.T) {
	// LLM clients are inconsistent about JSON types; both spellings must work.
	asInt := mustAsk(t, "standings", map[string]any{"season": 2019, "top": 1})
	asString := mustAsk(t, "standings", map[string]any{"season": "2019", "top": "1"})
	if asInt != asString {
		t.Errorf("string and numeric arguments gave different answers:\n%s\n---\n%s", asInt, asString)
	}
}

func TestAccentInsensitiveTeamNames(t *testing.T) {
	a := mustAsk(t, "team_stats", map[string]any{"team": "São Paulo", "season": 2019, "competition": "Serie A"})
	b := mustAsk(t, "team_stats", map[string]any{"team": "Sao Paulo", "season": 2019, "competition": "Serie A"})
	c := mustAsk(t, "team_stats", map[string]any{"team": "Sao Paulo-SP", "season": 2019, "competition": "Serie A"})
	if a != b || b != c {
		t.Errorf("team name variations gave different answers:\n%s\n---\n%s\n---\n%s", a, b, c)
	}
}
