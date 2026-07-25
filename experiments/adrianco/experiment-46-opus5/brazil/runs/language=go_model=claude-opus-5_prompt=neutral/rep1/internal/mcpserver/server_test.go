// server_test.go - BDD scenarios exercised through a real MCP session.
//
// Context
//
//	These tests connect an MCP client to the server over the SDK's in-memory
//	transport, so every assertion travels the full protocol path: JSON-RPC
//	initialize, tools/list, tools/call with schema validation, and the
//	text + structured content that comes back. Nothing calls a handler
//	directly, which means the argument schemas, the defaults and the error
//	envelopes are all covered.
//
//	The centrepiece is TestFeatureSampleQuestions: the 26 natural language
//	questions from the specification, each mapped to the tool call an LLM would
//	make, each asserted on the substance of the answer and each timed against
//	the specification's latency budget.
package mcpserver

import (
	"context"
	"encoding/json"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/bdd"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

var (
	loadOnce    sync.Once
	loadedGraph *soccer.Graph
	loadErr     error
)

func testGraph(t *testing.T) *soccer.Graph {
	t.Helper()
	loadOnce.Do(func() {
		dir, err := soccer.FindDataDir()
		if err != nil {
			loadErr = err
			return
		}
		loadedGraph, loadErr = soccer.Load(dir)
	})
	if loadErr != nil {
		t.Fatalf("loading datasets: %v", loadErr)
	}
	return loadedGraph
}

// session connects a client to a fresh server over the in-memory transport.
func session(t *testing.T) (context.Context, *mcp.ClientSession) {
	t.Helper()
	ctx := context.Background()
	srv := New(testGraph(t))

	serverTransport, clientTransport := mcp.NewInMemoryTransports()
	if _, err := srv.MCP().Connect(ctx, serverTransport, nil); err != nil {
		t.Fatalf("server connect: %v", err)
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "1.0.0"}, nil)
	cs, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatalf("client connect: %v", err)
	}
	t.Cleanup(func() { cs.Close() })
	return ctx, cs
}

// call invokes a tool and returns its text content, failing on a tool error.
func call(t *testing.T, ctx context.Context, cs *mcp.ClientSession, name string, args map[string]any) (string, *mcp.CallToolResult) {
	t.Helper()
	res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		t.Fatalf("calling %s: %v", name, err)
	}
	body := textOf(res)
	if res.IsError {
		t.Fatalf("tool %s returned an error: %s", name, body)
	}
	return body, res
}

// callExpectingError invokes a tool that is expected to fail.
func callExpectingError(t *testing.T, ctx context.Context, cs *mcp.ClientSession, name string, args map[string]any) string {
	t.Helper()
	res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		return err.Error()
	}
	if !res.IsError {
		t.Fatalf("tool %s unexpectedly succeeded: %s", name, textOf(res))
	}
	return textOf(res)
}

func textOf(res *mcp.CallToolResult) string {
	var b strings.Builder
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			b.WriteString(tc.Text)
		}
	}
	return b.String()
}

func TestFeatureMCPProtocol(t *testing.T) {
	bdd.Feature(t, "MCP protocol surface")

	bdd.Scenario(t, "a client can initialize and discover the tool set", func(s *bdd.S) {
		ctx, cs := session(s.T)
		var tools *mcp.ListToolsResult
		s.Given("an MCP client connected to the server", nil)
		s.When("it lists the available tools", func() {
			var err error
			tools, err = cs.ListTools(ctx, nil)
			if err != nil {
				s.Fatalf("ListTools: %v", err)
			}
		})
		s.Then("all 18 tools are advertised with descriptions and schemas", func() {
			if len(tools.Tools) != 18 {
				s.Errorf("advertised %d tools, want 18", len(tools.Tools))
			}
			for _, tool := range tools.Tools {
				if tool.Description == "" {
					s.Errorf("tool %s has no description", tool.Name)
				}
				if tool.InputSchema == nil {
					s.Errorf("tool %s has no input schema", tool.Name)
				}
				if tool.OutputSchema == nil {
					s.Errorf("tool %s has no output schema", tool.Name)
				}
			}
		})
		s.And("the tools cover all five capability areas of the specification", func() {
			have := map[string]bool{}
			for _, tool := range tools.Tools {
				have[tool.Name] = true
			}
			for _, want := range []string{
				"find_matches", "match_details", "find_derbies", // match queries
				"search_teams", "team_profile", "team_stats", "head_to_head", // team queries
				"search_players", "player_profile", "club_squad", // player queries
				"list_competitions", "competition_standings", "compare_seasons", // competition queries
				"competition_stats", "team_leaderboard", "notable_matches", // statistics
				"graph_summary", "list_datasets", // provenance
			} {
				if !have[want] {
					s.Errorf("tool %s is missing", want)
				}
			}
		})
		s.And("the server sends usage instructions with initialize", func() {
			if res := cs.InitializeResult(); res == nil || !strings.Contains(res.Instructions, "Brazilian football") {
				s.Error("initialize did not carry server instructions")
			}
		})
	})

	bdd.Scenario(t, "tools return both readable text and structured content", func(s *bdd.S) {
		ctx, cs := session(s.T)
		var res *mcp.CallToolResult
		var body string
		s.Given("a connected client", nil)
		s.When("head_to_head is called", func() {
			body, res = call(s.T, ctx, cs, "head_to_head", map[string]any{
				"team_a": "Flamengo", "team_b": "Fluminense", "limit": 3,
			})
		})
		s.Then("the text block is human readable", func() {
			if !strings.Contains(body, "Fla-Flu") {
				s.Errorf("text does not name the derby:\n%s", body)
			}
			if !strings.Contains(body, "Head-to-head in dataset:") {
				s.Errorf("text has no head-to-head summary:\n%s", body)
			}
		})
		s.And("the structured content carries the same numbers", func() {
			if res.StructuredContent == nil {
				s.Fatal("no structured content")
			}
			var h struct {
				AWins   int `json:"club_a_wins"`
				BWins   int `json:"club_b_wins"`
				Draws   int `json:"draws"`
				Played  int `json:"played"`
				Matches []struct {
					ID string `json:"id"`
				} `json:"matches"`
			}
			raw, err := json.Marshal(res.StructuredContent)
			if err != nil {
				s.Fatalf("marshal: %v", err)
			}
			if err := json.Unmarshal(raw, &h); err != nil {
				s.Fatalf("unmarshal structured content: %v", err)
			}
			if h.AWins+h.BWins+h.Draws != h.Played {
				s.Errorf("structured content is inconsistent: %+v", h)
			}
			if len(h.Matches) != 3 {
				s.Errorf("limit was not applied: %d matches", len(h.Matches))
			}
			if !strings.Contains(body, "Flamengo "+itoa(h.AWins)+" wins") {
				s.Errorf("text and structured win counts disagree:\n%s", body)
			}
		})
	})

	bdd.Scenario(t, "match ids from a search can be used to fetch full detail", func(s *bdd.S) {
		ctx, cs := session(s.T)
		var matchID, detail string
		s.Given("a connected client", nil)
		s.When("find_matches returns a match and its id is fetched", func() {
			_, res := call(s.T, ctx, cs, "find_matches", map[string]any{
				"team": "Palmeiras", "season": 2019, "competition": "Serie A", "limit": 1,
			})
			var out struct {
				Matches []struct {
					ID string `json:"id"`
				} `json:"matches"`
			}
			raw, _ := json.Marshal(res.StructuredContent)
			if err := json.Unmarshal(raw, &out); err != nil || len(out.Matches) == 0 {
				s.Fatalf("no match id returned: %v", err)
			}
			matchID = out.Matches[0].ID
			detail, _ = call(s.T, ctx, cs, "match_details", map[string]any{"match_id": matchID})
		})
		s.Then("the detail names the stadium and the source files", func() {
			if !strings.Contains(detail, matchID) {
				s.Errorf("detail does not echo the id:\n%s", detail)
			}
			if !strings.Contains(detail, "Sources:") {
				s.Errorf("detail does not cite its sources:\n%s", detail)
			}
			if !strings.Contains(detail, "Competition: Brasileirão Série A") {
				s.Errorf("detail does not state the competition:\n%s", detail)
			}
		})
	})

	bdd.Scenario(t, "errors are actionable rather than empty results", func(s *bdd.S) {
		ctx, cs := session(s.T)
		s.Given("a connected client", nil)
		s.Then("an unknown club explains how to find the right name", func() {
			msg := callExpectingError(s.T, ctx, cs, "team_stats", map[string]any{"team": "Real Madrid"})
			if !strings.Contains(msg, "search_teams") {
				s.Errorf("error was not actionable: %s", msg)
			}
		})
		s.And("an unknown competition lists the known ones", func() {
			msg := callExpectingError(s.T, ctx, cs, "competition_standings",
				map[string]any{"competition": "Premier League", "season": 2019})
			if !strings.Contains(msg, "Copa do Brasil") {
				s.Errorf("error did not list the competitions: %s", msg)
			}
		})
		s.And("an unavailable season lists the available ones", func() {
			msg := callExpectingError(s.T, ctx, cs, "competition_standings",
				map[string]any{"competition": "Libertadores", "season": 1975})
			if !strings.Contains(msg, "2013") {
				s.Errorf("error did not list the seasons: %s", msg)
			}
		})
		s.And("an unknown match id explains where ids come from", func() {
			msg := callExpectingError(s.T, ctx, cs, "match_details", map[string]any{"match_id": "nope"})
			if !strings.Contains(msg, "find_matches") {
				s.Errorf("error was not actionable: %s", msg)
			}
		})
		s.And("a missing required argument is rejected by the schema", func() {
			msg := callExpectingError(s.T, ctx, cs, "head_to_head", map[string]any{"team_a": "Flamengo"})
			if msg == "" {
				s.Error("expected a schema validation message")
			}
		})
		s.And("an unknown metric lists the supported ones", func() {
			msg := callExpectingError(s.T, ctx, cs, "team_leaderboard", map[string]any{"metric": "vibes"})
			if !strings.Contains(msg, "goal_difference") {
				s.Errorf("error did not list the metrics: %s", msg)
			}
		})
	})

	bdd.Scenario(t, "resources expose provenance and graph shape", func(s *bdd.S) {
		ctx, cs := session(s.T)
		var resources *mcp.ListResourcesResult
		s.Given("a connected client", nil)
		s.When("it lists and reads the resources", func() {
			var err error
			resources, err = cs.ListResources(ctx, nil)
			if err != nil {
				s.Fatalf("ListResources: %v", err)
			}
		})
		s.Then("both resources are readable JSON", func() {
			if len(resources.Resources) != 2 {
				s.Fatalf("advertised %d resources, want 2", len(resources.Resources))
			}
			for _, r := range resources.Resources {
				got, err := cs.ReadResource(ctx, &mcp.ReadResourceParams{URI: r.URI})
				if err != nil {
					s.Fatalf("reading %s: %v", r.URI, err)
				}
				if len(got.Contents) == 0 {
					s.Fatalf("resource %s is empty", r.URI)
				}
				var any1 any
				if err := json.Unmarshal([]byte(got.Contents[0].Text), &any1); err != nil {
					s.Errorf("resource %s is not valid JSON: %v", r.URI, err)
				}
			}
		})
		s.And("the dataset resource attributes every source and licence", func() {
			got, err := cs.ReadResource(ctx, &mcp.ReadResourceParams{URI: "brazilian-soccer://datasets"})
			if err != nil {
				s.Fatalf("read: %v", err)
			}
			for _, want := range []string{"CC BY 4.0", "CC0 Public Domain", "Apache 2.0", "kaggle.com"} {
				if !strings.Contains(got.Contents[0].Text, want) {
					s.Errorf("dataset resource does not mention %q", want)
				}
			}
		})
	})
}

// question is one specification sample question bound to the tool call an LLM
// would make for it, plus the substrings the answer must contain.
type question struct {
	ask      string
	tool     string
	args     map[string]any
	contains []string
	budget   time.Duration
}

func TestFeatureSampleQuestions(t *testing.T) {
	bdd.Feature(t, "Sample questions from the specification")
	ctx, cs := session(t)

	const simple = 2 * time.Second
	const aggregate = 5 * time.Second

	questions := []question{
		// --- Match queries -------------------------------------------------
		{
			ask:      "Show me all Flamengo vs Fluminense matches",
			tool:     "head_to_head",
			args:     map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 5},
			contains: []string{"Fla-Flu", "Head-to-head in dataset", "Flamengo", "Fluminense"},
			budget:   simple,
		},
		{
			ask:      "What matches did Palmeiras play in 2022?",
			tool:     "find_matches",
			args:     map[string]any{"team": "Palmeiras", "season": 2022},
			contains: []string{"Palmeiras matches", "2022"},
			budget:   simple,
		},
		{
			ask:      "Find all Copa do Brasil finals",
			tool:     "find_matches",
			args:     map[string]any{"competition": "Copa do Brasil", "stage": "final", "limit": 10},
			contains: []string{"Copa do Brasil", "Final"},
			budget:   simple,
		},
		{
			ask:      "When did Flamengo last play Corinthians, and what was the score?",
			tool:     "find_matches",
			args:     map[string]any{"team": "Flamengo", "opponent": "Corinthians", "order": "newest", "limit": 1},
			contains: []string{"Flamengo", "Corinthians"},
			budget:   simple,
		},
		{
			ask:      "Which Flamengo matches were played in September 2023?",
			tool:     "find_matches",
			args:     map[string]any{"team": "Flamengo", "date_from": "2023-09", "date_to": "2023-09"},
			contains: []string{"2023-09"},
			budget:   simple,
		},
		{
			ask:      "Show me all derbies in 2023",
			tool:     "find_derbies",
			args:     map[string]any{"season": 2023, "limit": 3},
			contains: []string{"Classic rivalries", "2023"},
			budget:   aggregate,
		},
		{
			ask:      "Show the 2018 Copa Libertadores knockout matches",
			tool:     "find_matches",
			args:     map[string]any{"competition": "Libertadores", "season": 2018, "stage": "final"},
			contains: []string{"Copa Libertadores", "2018", "Final"},
			budget:   simple,
		},

		// --- Team queries --------------------------------------------------
		{
			ask:      "What is Corinthians' home record in 2022?",
			tool:     "team_stats",
			args:     map[string]any{"team": "Corinthians", "season": 2022, "competition": "Serie A", "venue": "home"},
			contains: []string{"home matches only", "Matches: 19", "Win rate"},
			budget:   simple,
		},
		{
			ask:      "Which team scored the most goals in Serie A 2023?",
			tool:     "team_leaderboard",
			args:     map[string]any{"metric": "goals_for", "competition": "Serie A", "season": 2023, "limit": 5},
			contains: []string{"goals_for", "Brasileirão Série A 2023"},
			budget:   aggregate,
		},
		{
			ask:      "Compare Palmeiras and Santos head-to-head",
			tool:     "head_to_head",
			args:     map[string]any{"team_a": "Palmeiras", "team_b": "Santos", "limit": 5},
			contains: []string{"Palmeiras", "Santos", "Head-to-head in dataset"},
			budget:   simple,
		},
		{
			ask:      "What competitions has Palmeiras played in?",
			tool:     "team_profile",
			args:     map[string]any{"team": "Palmeiras"},
			contains: []string{"By competition", "Brasileirão Série A", "Copa Libertadores", "Copa do Brasil"},
			budget:   aggregate,
		},
		{
			ask:      "Which clubs are called Atletico?",
			tool:     "search_teams",
			args:     map[string]any{"query": "atletico", "limit": 8},
			contains: []string{"Atlético Mineiro", "Athletico Paranaense", "id:"},
			budget:   simple,
		},
		{
			ask:      "Tell me about Vasco",
			tool:     "team_profile",
			args:     map[string]any{"team": "Vasco"},
			contains: []string{"Vasco da Gama", "Rio de Janeiro", "Known in the data as"},
			budget:   aggregate,
		},

		// --- Player queries -----------------------------------------------
		{
			ask:      "Find all Brazilian players in the dataset",
			tool:     "search_players",
			args:     map[string]any{"nationality": "Brazil", "limit": 10, "group_by_club": true},
			contains: []string{"Neymar Jr", "nationality Brazil", "By club"},
			budget:   aggregate,
		},
		{
			ask:      "Who are the highest-rated players at Gremio?",
			tool:     "club_squad",
			args:     map[string]any{"club": "Gremio", "limit": 5},
			contains: []string{"Grêmio", "squad in the FIFA dataset", "Overall"},
			budget:   simple,
		},
		{
			ask:      "Which players play for Flamengo?",
			tool:     "club_squad",
			args:     map[string]any{"club": "Flamengo"},
			contains: []string{"not in the FIFA player dataset", "FIFA 19 snapshot"},
			budget:   simple,
		},
		{
			ask:      "Show me all forwards from Santos",
			tool:     "search_players",
			args:     map[string]any{"club": "Santos", "position_group": "Forward"},
			contains: []string{"Forward"},
			budget:   simple,
		},
		{
			ask:      "Who are the top Brazilian players under 21?",
			tool:     "search_players",
			args:     map[string]any{"nationality": "Brazil", "max_age": 21, "sort_by": "potential", "limit": 5},
			contains: []string{"Brazil", "Potential"},
			budget:   aggregate,
		},
		{
			ask:      "Who is Neymar?",
			tool:     "player_profile",
			args:     map[string]any{"name": "Neymar"},
			contains: []string{"Neymar Jr", "Nationality: Brazil", "Best attributes"},
			budget:   simple,
		},

		// --- Competition queries -------------------------------------------
		{
			ask:      "Who won the 2019 Brasileirao?",
			tool:     "competition_standings",
			args:     map[string]any{"competition": "Serie A", "season": 2019},
			contains: []string{"Flamengo", "90", "Champion"},
			budget:   aggregate,
		},
		{
			ask:      "Which teams were relegated in 2020?",
			tool:     "competition_standings",
			args:     map[string]any{"competition": "Serie A", "season": 2020},
			contains: []string{"Relegated", "Vasco da Gama", "Coritiba", "Botafogo", "Goiás"},
			budget:   aggregate,
		},
		{
			ask:      "What competitions and seasons are available?",
			tool:     "list_competitions",
			args:     map[string]any{},
			contains: []string{"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores", "Brasileirão Série B"},
			budget:   aggregate,
		},
		{
			ask:      "Compare the 2018 and 2019 seasons",
			tool:     "compare_seasons",
			args:     map[string]any{"competition": "Serie A", "season_a": 2018, "season_b": 2019},
			contains: []string{"Palmeiras", "Flamengo", "Change from 2018 to 2019", "Goals per match"},
			budget:   aggregate,
		},

		// --- Statistical analysis -----------------------------------------
		{
			ask:      "What's the average goals per match in the Brasileirao?",
			tool:     "competition_stats",
			args:     map[string]any{"competition": "Serie A"},
			contains: []string{"Average goals per match", "Home wins"},
			budget:   aggregate,
		},
		{
			ask:      "Which team has the best away record?",
			tool:     "team_leaderboard",
			args:     map[string]any{"metric": "win_rate", "venue": "away", "competition": "Serie A", "min_matches": 100, "limit": 5},
			contains: []string{"away matches only", "win rate"},
			budget:   aggregate,
		},
		{
			ask:      "Show me the biggest wins in the dataset",
			tool:     "notable_matches",
			args:     map[string]any{"kind": "biggest_wins", "limit": 5},
			contains: []string{"Biggest victories"},
			budget:   aggregate,
		},
		{
			ask:      "Which matches had the most goals?",
			tool:     "notable_matches",
			args:     map[string]any{"kind": "highest_scoring", "competition": "Serie A", "limit": 5},
			contains: []string{"Highest scoring"},
			budget:   aggregate,
		},
		{
			ask:      "Where does this data come from?",
			tool:     "list_datasets",
			args:     map[string]any{},
			contains: []string{"Brasileirao_Matches.csv", "fifa_data.csv", "CC BY 4.0", "licence"},
			budget:   simple,
		},
		{
			ask:      "How big is the knowledge graph?",
			tool:     "graph_summary",
			args:     map[string]any{},
			contains: []string{"Clubs:", "Matches:", "Players:", "Edges:"},
			budget:   aggregate,
		},
	}

	if len(questions) < 20 {
		t.Fatalf("only %d sample questions, the specification asks for at least 20", len(questions))
	}

	for _, q := range questions {
		q := q
		bdd.Scenario(t, q.ask, func(s *bdd.S) {
			var body string
			var elapsed time.Duration
			s.Given("an MCP client connected to the loaded knowledge graph", nil)
			s.When("the model calls "+q.tool, func() {
				start := time.Now()
				body, _ = call(s.T, ctx, cs, q.tool, q.args)
				elapsed = time.Since(start)
			})
			s.Then("the answer contains the expected substance", func() {
				for _, want := range q.contains {
					if !strings.Contains(body, want) {
						s.Errorf("answer is missing %q; got:\n%s", want, body)
					}
				}
				if strings.TrimSpace(body) == "" {
					s.Error("answer is empty")
				}
			})
			s.And("it responds inside the specification's latency budget", func() {
				if elapsed > q.budget {
					s.Errorf("took %s, budget is %s", elapsed, q.budget)
				}
			})
		})
	}
}

func TestFeatureCrossDatasetQueries(t *testing.T) {
	bdd.Feature(t, "Cross-file queries")
	ctx, cs := session(t)

	bdd.Scenario(t, "a club squad is joined to that club's match record", func(s *bdd.S) {
		var body string
		s.Given("player data in fifa_data.csv and match data in five other files", nil)
		s.When("club_squad is called for a club present in both", func() {
			body, _ = call(s.T, ctx, cs, "club_squad", map[string]any{"club": "Atletico Mineiro", "limit": 3})
		})
		s.Then("the answer combines FIFA ratings with the match record", func() {
			for _, want := range []string{"Atlético Mineiro", "Overall", "Match record in the knowledge graph"} {
				if !strings.Contains(body, want) {
					s.Errorf("answer is missing %q; got:\n%s", want, body)
				}
			}
		})
	})

	bdd.Scenario(t, "a Brazilian club name resolves to its FIFA spelling", func(s *bdd.S) {
		var body string
		s.Given(`the FIFA data spelling "Sport Club do Recife" and the match data spelling "Sport-PE"`, nil)
		s.When(`search_players is called with club "Sport"`, func() {
			body, _ = call(s.T, ctx, cs, "search_players", map[string]any{"club": "Sport", "limit": 3})
		})
		s.Then("players from the linked club are returned", func() {
			if strings.Contains(body, "No players matched") {
				s.Errorf("the club link was not followed:\n%s", body)
			}
			if !strings.Contains(body, "Sport Club do Recife") {
				s.Errorf("answer does not name the FIFA club:\n%s", body)
			}
		})
	})

	bdd.Scenario(t, "extended statistics from one file enrich matches found in another", func(s *bdd.S) {
		var detail string
		s.Given("a 2022 Série A match present in both Brasileirao_Matches.csv and BR-Football-Dataset.csv", nil)
		s.When("the match detail is fetched", func() {
			_, res := call(s.T, ctx, cs, "find_matches", map[string]any{
				"team": "Palmeiras", "season": 2022, "competition": "Serie A", "limit": 20,
			})
			var out struct {
				Matches []struct {
					ID      string   `json:"id"`
					Sources []string `json:"sources"`
				} `json:"matches"`
			}
			raw, _ := json.Marshal(res.StructuredContent)
			if err := json.Unmarshal(raw, &out); err != nil {
				s.Fatalf("unmarshal: %v", err)
			}
			for _, m := range out.Matches {
				if len(m.Sources) > 1 {
					detail, _ = call(s.T, ctx, cs, "match_details", map[string]any{"match_id": m.ID})
					break
				}
			}
		})
		s.Then("the detail cites both files and shows shot and corner counts", func() {
			if detail == "" {
				s.Fatal("no multi-source match found")
			}
			if !strings.Contains(detail, "Brasileirao_Matches.csv") || !strings.Contains(detail, "BR-Football-Dataset.csv") {
				s.Errorf("detail does not cite both sources:\n%s", detail)
			}
			if !strings.Contains(detail, "Extended statistics") {
				s.Errorf("detail has no extended statistics:\n%s", detail)
			}
		})
	})
}

// itoa avoids importing strconv just for the assertion above.
func itoa(v int) string {
	if v == 0 {
		return "0"
	}
	var digits []byte
	neg := v < 0
	if neg {
		v = -v
	}
	for v > 0 {
		digits = append([]byte{byte('0' + v%10)}, digits...)
		v /= 10
	}
	if neg {
		return "-" + string(digits)
	}
	return string(digits)
}
