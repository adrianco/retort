// server_test.go exercises the server the way a client does: over a real MCP
// session (in-memory transports, full JSON-RPC round trip), not by calling Go
// methods. It checks the protocol surface - initialize, tools/list, tools/call,
// resources, prompts - and then answers the specification's sample questions
// through that session.
package mcpserver

import (
	"context"
	"encoding/json"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

var (
	sharedGraph *soccer.Graph
	sharedErr   error
	sharedOnce  sync.Once
)

// newSession starts an in-process client/server pair sharing one loaded graph.
func newSession(t *testing.T) (*mcp.ClientSession, *Server) {
	t.Helper()
	sharedOnce.Do(func() { sharedGraph, sharedErr = soccer.Load("") })
	if sharedErr != nil {
		t.Fatalf("loading data: %v", sharedErr)
	}
	srv := NewWithGraph(sharedGraph)
	ctx := context.Background()
	serverTransport, clientTransport := mcp.NewInMemoryTransports()
	if _, err := srv.MCP().Connect(ctx, serverTransport, nil); err != nil {
		t.Fatalf("connecting server: %v", err)
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "1.0.0"}, nil)
	session, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatalf("connecting client: %v", err)
	}
	t.Cleanup(func() { session.Close() })
	return session, srv
}

// callTool runs a tool and returns its text rendering plus its structured payload.
func callTool(t *testing.T, session *mcp.ClientSession, name string, args map[string]any) (string, map[string]any) {
	t.Helper()
	res, err := session.CallTool(context.Background(), &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		t.Fatalf("calling %s: %v", name, err)
	}
	if res.IsError {
		t.Fatalf("tool %s reported an error: %s", name, textOf(res))
	}
	return textOf(res), structuredOf(t, res)
}

// callToolExpectingError runs a tool that should fail and returns the message.
func callToolExpectingError(t *testing.T, session *mcp.ClientSession, name string, args map[string]any) string {
	t.Helper()
	res, err := session.CallTool(context.Background(), &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		return err.Error()
	}
	if !res.IsError {
		t.Fatalf("tool %s unexpectedly succeeded: %s", name, textOf(res))
	}
	return textOf(res)
}

func textOf(res *mcp.CallToolResult) string {
	var parts []string
	for _, c := range res.Content {
		if text, ok := c.(*mcp.TextContent); ok {
			parts = append(parts, text.Text)
		}
	}
	return strings.Join(parts, "\n")
}

func structuredOf(t *testing.T, res *mcp.CallToolResult) map[string]any {
	t.Helper()
	if res.StructuredContent == nil {
		return nil
	}
	raw, err := json.Marshal(res.StructuredContent)
	if err != nil {
		t.Fatalf("re-marshalling structured content: %v", err)
	}
	var out map[string]any
	if err := json.Unmarshal(raw, &out); err != nil {
		t.Fatalf("decoding structured content: %v", err)
	}
	return out
}

func TestInitializeAdvertisesTheServer(t *testing.T) {
	session, _ := newSession(t)
	info := session.InitializeResult()
	if info.ServerInfo.Name != "brazilian-soccer" {
		t.Errorf("server name = %q", info.ServerInfo.Name)
	}
	if info.ServerInfo.Version != Version {
		t.Errorf("server version = %q, want %q", info.ServerInfo.Version, Version)
	}
	if info.Capabilities.Tools == nil {
		t.Error("the server does not advertise tool support")
	}
	if info.Capabilities.Resources == nil {
		t.Error("the server does not advertise resource support")
	}
	if info.Capabilities.Prompts == nil {
		t.Error("the server does not advertise prompt support")
	}
	if !strings.Contains(info.Instructions, "Brasileirão") {
		t.Errorf("instructions do not describe the data: %q", info.Instructions)
	}
}

func TestToolsAreDiscoverable(t *testing.T) {
	session, _ := newSession(t)
	found := map[string]*mcp.Tool{}
	for tool, err := range session.Tools(context.Background(), nil) {
		if err != nil {
			t.Fatal(err)
		}
		found[tool.Name] = tool
	}
	for _, want := range toolCatalog {
		tool, ok := found[want.name]
		if !ok {
			t.Errorf("tool %s is not exposed", want.name)
			continue
		}
		if len(tool.Description) < 30 {
			t.Errorf("tool %s has a thin description: %q", want.name, tool.Description)
		}
		if tool.InputSchema == nil {
			t.Errorf("tool %s has no input schema", want.name)
		}
	}
	if len(found) != len(toolCatalog) {
		t.Errorf("server exposes %d tools, the catalogue lists %d", len(found), len(toolCatalog))
	}
}

// TestEveryToolRunsOverTheProtocol calls each tool once with realistic arguments
// and checks that both halves of the result are populated.
func TestEveryToolRunsOverTheProtocol(t *testing.T) {
	session, _ := newSession(t)
	calls := []struct {
		tool string
		args map[string]any
		want string // a substring the text rendering must contain
	}{
		{"search_matches", map[string]any{"team": "Palmeiras", "season": 2023, "limit": 5}, "Palmeiras"},
		{"head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense"}, "Fla-Flu"},
		{"team_stats", map[string]any{"team": "Corinthians", "season": 2022, "venue": "home"}, "Win rate"},
		{"team_profile", map[string]any{"team": "Grêmio"}, "Competitions"},
		{"list_teams", map[string]any{"query": "atletico"}, "Atlético"},
		{"search_players", map[string]any{"nationality": "Brazil", "limit": 3}, "Neymar"},
		{"player_profile", map[string]any{"name": "Neymar"}, "Overall"},
		{"standings", map[string]any{"season": 2019}, "Flamengo"},
		{"champions", map[string]any{"competition": "Libertadores"}, "River Plate"},
		{"competition_bracket", map[string]any{"competition": "Libertadores", "season": 2018}, "final"},
		{"competition_summary", map[string]any{"competition": "Serie A", "seasons": []any{2018, 2019}}, "Comparison"},
		{"team_rankings", map[string]any{"metric": "most_wins", "competition": "Serie A", "season": 2019}, "Flamengo"},
		{"aggregate_stats", map[string]any{"competition": "Serie A", "season": 2019}, "goals per match"},
		{"list_derbies", map[string]any{"season": 2023}, "Fla-Flu"},
		{"dataset_info", map[string]any{}, "Brasileirao_Matches.csv"},
	}
	if len(calls) != len(toolCatalog) {
		t.Fatalf("this test covers %d tools but the server has %d", len(calls), len(toolCatalog))
	}
	for _, c := range calls {
		text, structured := callTool(t, session, c.tool, c.args)
		if !strings.Contains(text, c.want) {
			t.Errorf("%s: text result does not mention %q\n%s", c.tool, c.want, truncate(text, 400))
		}
		if structured == nil {
			t.Errorf("%s: no structured content", c.tool)
		}
		if strings.Contains(text, "%!") {
			t.Errorf("%s: formatting error in the text result", c.tool)
		}
	}
}

// TestToolErrorsAreHelpful checks that bad input comes back as a tool error the
// model can recover from, rather than a protocol failure or an empty answer.
func TestToolErrorsAreHelpful(t *testing.T) {
	session, _ := newSession(t)
	cases := []struct {
		name string
		tool string
		args map[string]any
		want string
	}{
		{"unknown club", "team_stats", map[string]any{"team": "Manchester United"}, "unknown team"},
		{"unknown competition", "standings", map[string]any{"competition": "Premier League", "season": 2019}, "unknown competition"},
		{"missing season", "standings", map[string]any{"competition": "Serie A"}, "required"},
		{"season with no data", "standings", map[string]any{"competition": "Serie A", "season": 1950}, "no Brasileirão Série A matches"},
		{"unknown metric", "team_rankings", map[string]any{"metric": "most_headers"}, "unknown metric"},
		{"unknown venue", "team_stats", map[string]any{"team": "Santos", "venue": "neutral"}, "unknown venue"},
		{"bad date", "search_matches", map[string]any{"date_from": "yesterday"}, "ISO date"},
		{"league bracket", "competition_bracket", map[string]any{"competition": "Serie A", "season": 2019}, "league"},
		{"unknown player", "player_profile", map[string]any{"name": "Zinedine Zidane"}, "no player named"},
		{"missing head to head argument", "head_to_head", map[string]any{"team_a": "Santos"}, "required"},
	}
	for _, c := range cases {
		msg := callToolExpectingError(t, session, c.tool, c.args)
		if !strings.Contains(strings.ToLower(msg), strings.ToLower(c.want)) {
			t.Errorf("%s: error %q does not mention %q", c.name, msg, c.want)
		}
	}
}

func TestStructuredResultsAreUsable(t *testing.T) {
	session, _ := newSession(t)

	_, standings := callTool(t, session, "standings", map[string]any{"season": 2019})
	if standings["champion"] != "Flamengo" {
		t.Errorf("structured champion = %v, want Flamengo", standings["champion"])
	}
	table, ok := standings["table"].([]any)
	if !ok || len(table) != 20 {
		t.Fatalf("structured table has %d rows, want 20", len(table))
	}
	first, _ := table[0].(map[string]any)
	if first["points"].(float64) != 90 {
		t.Errorf("structured points = %v, want 90", first["points"])
	}

	_, matches := callTool(t, session, "search_matches", map[string]any{"team": "Santos", "opponent": "Palmeiras", "limit": 3})
	h2h, ok := matches["head_to_head"].(map[string]any)
	if !ok {
		t.Fatal("naming two clubs should attach a head-to-head summary")
	}
	if h2h["matches"].(float64) == 0 {
		t.Error("head-to-head summary reports no matches")
	}
	list, _ := matches["matches"].([]any)
	if len(list) != 3 {
		t.Errorf("asked for 3 matches, got %d", len(list))
	}
	for _, item := range list {
		m := item.(map[string]any)
		for _, field := range []string{"date", "competition", "home_team", "away_team", "home_goals", "away_goals", "sources"} {
			if _, ok := m[field]; !ok {
				t.Errorf("match is missing the %q field: %v", field, m)
			}
		}
	}
}

func TestResourcesAreReadable(t *testing.T) {
	session, _ := newSession(t)
	ctx := context.Background()
	var uris []string
	for res, err := range session.Resources(ctx, nil) {
		if err != nil {
			t.Fatal(err)
		}
		uris = append(uris, res.URI)
	}
	want := []string{"soccer://datasets", "soccer://teams", "soccer://competitions", "soccer://sample-questions", "soccer://tools"}
	for _, uri := range want {
		found := false
		for _, got := range uris {
			if got == uri {
				found = true
			}
		}
		if !found {
			t.Errorf("resource %s is not published (have %v)", uri, uris)
			continue
		}
		res, err := session.ReadResource(ctx, &mcp.ReadResourceParams{URI: uri})
		if err != nil {
			t.Errorf("reading %s: %v", uri, err)
			continue
		}
		if len(res.Contents) == 0 || len(res.Contents[0].Text) < 100 {
			t.Errorf("resource %s returned little or no content", uri)
		}
	}
}

func TestPromptsAreAvailable(t *testing.T) {
	session, _ := newSession(t)
	ctx := context.Background()
	names := map[string]bool{}
	for p, err := range session.Prompts(ctx, nil) {
		if err != nil {
			t.Fatal(err)
		}
		names[p.Name] = true
	}
	for _, want := range []string{"club_report", "season_review", "compare_clubs"} {
		if !names[want] {
			t.Errorf("prompt %s is missing", want)
		}
	}
	res, err := session.GetPrompt(ctx, &mcp.GetPromptParams{
		Name:      "season_review",
		Arguments: map[string]string{"competition": "Série A", "season": "2019"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(res.Messages) == 0 {
		t.Fatal("prompt returned no messages")
	}
	text, ok := res.Messages[0].Content.(*mcp.TextContent)
	if !ok || !strings.Contains(text.Text, "2019") {
		t.Errorf("prompt text does not mention the requested season: %+v", res.Messages[0].Content)
	}
}

// SampleQuestion pairs a question from the specification with the tool call that
// answers it and something the answer must contain.
type SampleQuestion struct {
	Question string
	Tool     string
	Args     map[string]any
	Expect   []string
}

// sampleQuestions covers the "at least 20 sample questions" success criterion,
// including at least one from every category the specification lists.
var sampleQuestions = []SampleQuestion{
	// Match queries.
	{"Show me all Flamengo vs Fluminense matches", "head_to_head",
		map[string]any{"team_a": "Flamengo", "team_b": "Fluminense"}, []string{"Fla-Flu", "wins"}},
	{"What matches did Palmeiras play in 2023?", "search_matches",
		map[string]any{"team": "Palmeiras", "season": 2023, "limit": 10}, []string{"Palmeiras", "2023"}},
	{"Find all Copa do Brasil finals", "search_matches",
		map[string]any{"competition": "Copa do Brasil", "stage": "final", "limit": 40}, []string{"final"}},
	{"When did Flamengo last play Corinthians?", "head_to_head",
		map[string]any{"team_a": "Flamengo", "team_b": "Corinthians", "limit": 1}, []string{"last meeting"}},
	{"Show me every match played at the Maracanã", "search_matches",
		map[string]any{"venue": "Maracanã", "limit": 5}, []string{"Maracanã"}},

	// Team queries.
	{"What is Corinthians' home record in 2022?", "team_stats",
		map[string]any{"team": "Corinthians", "competition": "Serie A", "season": 2022, "venue": "home"}, []string{"Matches: 19", "Win rate"}},
	{"Which team scored the most goals in Serie A 2023?", "team_rankings",
		map[string]any{"metric": "most_goals_scored", "competition": "Serie A", "season": 2023, "limit": 3}, []string{"goals"}},
	{"Compare Palmeiras and Santos head-to-head", "head_to_head",
		map[string]any{"team_a": "Palmeiras", "team_b": "Santos"}, []string{"Palmeiras", "Santos", "wins"}},
	{"What competitions has Palmeiras played in?", "team_profile",
		map[string]any{"team": "Palmeiras"}, []string{"Copa Libertadores", "Copa do Brasil", "Série A"}},
	{"Which team has the best away record in Serie A?", "team_rankings",
		map[string]any{"metric": "best_win_rate", "venue": "away", "competition": "Serie A", "min_matches": 100}, []string{"away matches only"}},

	// Player queries.
	{"Find all Brazilian players in the dataset", "search_players",
		map[string]any{"nationality": "Brazil", "limit": 5, "group_by_club": true}, []string{"827", "By club"}},
	{"Who are the highest-rated players at Fluminense?", "search_players",
		map[string]any{"club": "Fluminense", "limit": 5}, []string{"Fluminense", "Overall"}},
	{"Show me all forwards from Santos", "search_players",
		map[string]any{"club": "Santos", "position": "forward"}, []string{"Santos"}},
	{"Who is Neymar?", "player_profile",
		map[string]any{"name": "Neymar"}, []string{"Overall", "Brazil"}},
	{"Which players play for Grêmio?", "team_profile",
		map[string]any{"team": "Grêmio", "squad_limit": 5}, []string{"Squad in the FIFA dataset"}},

	// Competition queries.
	{"Who won the 2019 Brasileirão?", "standings",
		map[string]any{"competition": "Serie A", "season": 2019}, []string{"Champion: Flamengo", "90"}},
	{"Which teams were relegated in 2020?", "standings",
		map[string]any{"competition": "Serie A", "season": 2020}, []string{"Relegated:", "Vasco da Gama"}},
	{"Show the 2018 Copa Libertadores bracket", "competition_bracket",
		map[string]any{"competition": "Libertadores", "season": 2018}, []string{"Semifinals", "River Plate"}},
	{"List every Copa do Brasil winner", "champions",
		map[string]any{"competition": "Copa do Brasil"}, []string{"Palmeiras", "Cruzeiro"}},
	{"Summarise the 2021 Serie B season", "competition_summary",
		map[string]any{"competition": "Serie B", "seasons": []any{2021}}, []string{"per match", "Champion"}},

	// Statistical analysis.
	{"What's the average goals per match in the Brasileirão?", "aggregate_stats",
		map[string]any{"competition": "Serie A"}, []string{"Average goals per match"}},
	{"Show me the biggest wins in the dataset", "aggregate_stats",
		map[string]any{"top": 10}, []string{"Biggest victories"}},
	{"Compare the 2018 and 2019 seasons", "competition_summary",
		map[string]any{"competition": "Serie A", "seasons": []any{2018, 2019}}, []string{"Comparison", "Goals per match"}},
	{"Show me all derbies in 2023", "list_derbies",
		map[string]any{"season": 2023}, []string{"Derby Paulista", "Grenal"}},
	{"How big is the home advantage in Brazilian football?", "aggregate_stats",
		map[string]any{}, []string{"Home advantage"}},

	// Data provenance.
	{"Where does this data come from?", "dataset_info",
		map[string]any{}, []string{"CC BY 4.0", "kaggle"}},
	{"Which clubs are called Atlético?", "list_teams",
		map[string]any{"query": "atletico"}, []string{"Atlético-MG", "Athletico-PR"}},
}

// TestSampleQuestions is the acceptance test for the specification's "at least
// 20 sample questions can be answered" criterion.
func TestSampleQuestions(t *testing.T) {
	session, _ := newSession(t)
	if len(sampleQuestions) < 20 {
		t.Fatalf("only %d sample questions, the specification asks for at least 20", len(sampleQuestions))
	}
	for _, q := range sampleQuestions {
		t.Run(q.Question, func(t *testing.T) {
			start := time.Now()
			text, structured := callTool(t, session, q.Tool, q.Args)
			elapsed := time.Since(start)
			if elapsed > 5*time.Second {
				t.Errorf("answering took %v, the budget is 5s", elapsed)
			}
			if structured == nil {
				t.Error("no structured payload")
			}
			for _, want := range q.Expect {
				if !strings.Contains(strings.ToLower(text), strings.ToLower(want)) {
					t.Errorf("answer does not mention %q\n%s", want, truncate(text, 600))
				}
			}
		})
	}
}

// TestSimpleLookupLatency covers the "< 2 seconds" requirement over the protocol
// rather than in-process, so it includes JSON-RPC encoding.
func TestSimpleLookupLatency(t *testing.T) {
	session, _ := newSession(t)
	lookups := []struct {
		tool string
		args map[string]any
	}{
		{"search_matches", map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 5}},
		{"team_stats", map[string]any{"team": "Santos", "season": 2019}},
		{"player_profile", map[string]any{"name": "Gabriel"}},
		{"standings", map[string]any{"season": 2015}},
		{"list_teams", map[string]any{"query": "flamengo"}},
	}
	for _, l := range lookups {
		start := time.Now()
		callTool(t, session, l.tool, l.args)
		if elapsed := time.Since(start); elapsed > 2*time.Second {
			t.Errorf("%s took %v, the budget for a simple lookup is 2s", l.tool, elapsed)
		}
	}
}

// TestConcurrentToolCalls checks the shared graph really is safe for the
// concurrent requests an MCP client may issue.
func TestConcurrentToolCalls(t *testing.T) {
	session, _ := newSession(t)
	var wg sync.WaitGroup
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			res, err := session.CallTool(context.Background(), &mcp.CallToolParams{
				Name:      "team_stats",
				Arguments: map[string]any{"team": []string{"Flamengo", "Santos", "Palmeiras", "Grêmio"}[i%4], "season": 2019 + i%4},
			})
			if err != nil {
				t.Errorf("concurrent call failed: %v", err)
				return
			}
			if res.IsError {
				t.Errorf("concurrent call errored: %s", textOf(res))
			}
		}(i)
	}
	wg.Wait()
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
