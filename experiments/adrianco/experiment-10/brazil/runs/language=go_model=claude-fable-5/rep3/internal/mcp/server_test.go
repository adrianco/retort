// BDD (Given/When/Then) tests for the MCP protocol layer.
//
// Context: drives the stdio JSON-RPC server end-to-end with the real
// datasets — handshake, tool discovery, tool calls and error handling —
// and proves the "at least 20 sample questions can be answered" success
// criterion from TASK.md by running 20 question-shaped tool calls.
package mcp

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"testing"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/query"
)

var (
	testOnce sync.Once
	testSrv  *Server
	testErr  error
)

func server(t *testing.T) *Server {
	t.Helper()
	testOnce.Do(func() {
		var dir string
		dir, testErr = data.FindDataDir(".")
		if testErr != nil {
			return
		}
		var ds *data.Dataset
		ds, testErr = data.LoadDataset(dir)
		if testErr != nil {
			return
		}
		testSrv = NewServer("brazilian-soccer-mcp", "test", BuildTools(query.New(ds)), nil)
	})
	if testErr != nil {
		t.Fatalf("loading datasets: %v", testErr)
	}
	return testSrv
}

// roundTrip sends newline-delimited JSON-RPC requests and decodes the
// responses in order.
func roundTrip(t *testing.T, s *Server, requests ...string) []map[string]any {
	t.Helper()
	in := strings.NewReader(strings.Join(requests, "\n") + "\n")
	var out bytes.Buffer
	if err := s.Serve(in, &out); err != nil {
		t.Fatalf("serve: %v", err)
	}
	var responses []map[string]any
	dec := json.NewDecoder(&out)
	for dec.More() {
		var m map[string]any
		if err := dec.Decode(&m); err != nil {
			t.Fatalf("decoding response: %v", err)
		}
		responses = append(responses, m)
	}
	return responses
}

// callTool runs one tools/call and returns the text content.
func callTool(t *testing.T, s *Server, name string, args map[string]any) (string, bool) {
	t.Helper()
	params, _ := json.Marshal(map[string]any{"name": name, "arguments": args})
	req := fmt.Sprintf(`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":%s}`, params)
	resps := roundTrip(t, s, req)
	if len(resps) != 1 {
		t.Fatalf("got %d responses, want 1", len(resps))
	}
	if errObj := resps[0]["error"]; errObj != nil {
		t.Fatalf("tools/call %s returned protocol error: %v", name, errObj)
	}
	result := resps[0]["result"].(map[string]any)
	content := result["content"].([]any)
	text := content[0].(map[string]any)["text"].(string)
	isError, _ := result["isError"].(bool)
	return text, isError
}

func TestScenarioInitializeHandshake(t *testing.T) {
	// Given a running MCP server
	s := server(t)

	// When a client sends initialize, the initialized notification and ping
	resps := roundTrip(t, s,
		`{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":1,"method":"ping"}`,
	)

	// Then it answers initialize and ping but not the notification
	if len(resps) != 2 {
		t.Fatalf("got %d responses, want 2", len(resps))
	}
	result := resps[0]["result"].(map[string]any)
	if result["protocolVersion"] == "" {
		t.Error("initialize response missing protocolVersion")
	}
	info := result["serverInfo"].(map[string]any)
	if info["name"] != "brazilian-soccer-mcp" {
		t.Errorf("serverInfo.name = %v", info["name"])
	}
}

func TestScenarioToolDiscovery(t *testing.T) {
	// Given an initialized MCP server
	s := server(t)

	// When the client lists tools
	resps := roundTrip(t, s, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`)

	// Then all nine soccer tools are advertised with schemas
	tools := resps[0]["result"].(map[string]any)["tools"].([]any)
	want := []string{
		"search_matches", "head_to_head", "team_stats", "league_standings",
		"search_players", "player_details", "competition_stats", "biggest_wins", "list_teams",
	}
	if len(tools) != len(want) {
		t.Fatalf("got %d tools, want %d", len(tools), len(want))
	}
	names := map[string]bool{}
	for _, tl := range tools {
		m := tl.(map[string]any)
		names[m["name"].(string)] = true
		if m["description"] == "" || m["inputSchema"] == nil {
			t.Errorf("tool %v missing description or inputSchema", m["name"])
		}
	}
	for _, w := range want {
		if !names[w] {
			t.Errorf("tool %q not advertised", w)
		}
	}
}

func TestScenarioUnknownMethodAndTool(t *testing.T) {
	// Given a running MCP server
	s := server(t)

	// When the client calls an unknown method
	resps := roundTrip(t, s, `{"jsonrpc":"2.0","id":1,"method":"no/such/method"}`)
	// Then it gets a method-not-found error
	if resps[0]["error"] == nil {
		t.Error("expected error for unknown method")
	}

	// When the client calls an unknown tool
	resps = roundTrip(t, s, `{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"no_such_tool","arguments":{}}}`)
	// Then it gets an invalid-params error
	if resps[0]["error"] == nil {
		t.Error("expected error for unknown tool")
	}
}

func TestScenarioToolErrorsAreReported(t *testing.T) {
	// Given a running MCP server
	s := server(t)

	// When a tool is called with a team that does not exist
	text, isError := callTool(t, s, "team_stats", map[string]any{"team": "Real Madrid Castilla XYZ"})

	// Then the call returns an MCP tool error, not a protocol failure
	if !isError {
		t.Errorf("expected isError=true, got text: %s", text)
	}
}

func TestScenarioTwentySampleQuestions(t *testing.T) {
	// Given the full dataset behind the MCP server
	s := server(t)

	// When 20 sample questions from TASK.md are asked via tool calls
	questions := []struct {
		question string
		tool     string
		args     map[string]any
		expect   string // substring that must appear in the answer
	}{
		{"Show me all Flamengo vs Fluminense matches", "search_matches",
			map[string]any{"team": "Flamengo", "opponent": "Fluminense"}, "Flamengo"},
		{"What matches did Palmeiras play in 2023?", "search_matches",
			map[string]any{"team": "Palmeiras", "season": 2023}, "Palmeiras"},
		{"Find all Copa do Brasil matches of Gremio", "search_matches",
			map[string]any{"team": "Gremio", "competition": "Copa do Brasil"}, "Copa do Brasil"},
		{"When did Flamengo last play Corinthians?", "search_matches",
			map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 1}, "Flamengo"},
		{"What is Corinthians' home record in 2022?", "team_stats",
			map[string]any{"team": "Corinthians", "season": 2022, "competition": "serie a", "venue": "home"}, "Win rate"},
		{"How did Santos do in 2019?", "team_stats",
			map[string]any{"team": "Santos", "season": 2019}, "Wins"},
		{"Compare Palmeiras and Santos head-to-head", "head_to_head",
			map[string]any{"team1": "Palmeiras", "team2": "Santos"}, "head-to-head"},
		{"Compare Flamengo and Vasco head-to-head", "head_to_head",
			map[string]any{"team1": "Flamengo", "team2": "Vasco"}, "wins"},
		{"Who won the 2019 Brasileirão?", "league_standings",
			map[string]any{"season": 2019}, "Champion"},
		{"Show the 2015 Brasileirão table", "league_standings",
			map[string]any{"season": 2015}, "pts"},
		{"Which teams were relegated in 2020?", "league_standings",
			map[string]any{"season": 2020}, "20."},
		{"Who is Gabriel Jesus?", "player_details",
			map[string]any{"name": "Gabriel Jesus"}, "Nationality"},
		{"Find all Brazilian players in the dataset", "search_players",
			map[string]any{"nationality": "Brazil"}, "Brazil"},
		{"Who are the highest-rated players at Santos?", "search_players",
			map[string]any{"club": "Santos", "limit": 5}, "Overall"},
		{"Show me all goalkeepers from Brazil", "search_players",
			map[string]any{"nationality": "Brazil", "position": "GK"}, "GK"},
		{"Who are the top Brazilian players?", "search_players",
			map[string]any{"nationality": "Brazil", "min_overall": 85}, "Neymar"},
		{"What's the average goals per match in the Brasileirão?", "competition_stats",
			map[string]any{"competition": "serie a"}, "Average goals per match"},
		{"How many matches were played in the 2018 season overall?", "competition_stats",
			map[string]any{"season": 2018}, "Matches"},
		{"Show me the biggest wins in the dataset", "biggest_wins",
			map[string]any{"limit": 10}, "1."},
		{"What teams are called Botafogo?", "list_teams",
			map[string]any{"query": "Botafogo"}, "Botafogo"},
	}
	if len(questions) < 20 {
		t.Fatalf("only %d sample questions, want at least 20", len(questions))
	}

	for _, q := range questions {
		t.Run(q.question, func(t *testing.T) {
			text, isError := callTool(t, s, q.tool, q.args)
			// Then each question gets a substantive, well-formed answer
			if isError {
				t.Fatalf("tool error: %s", text)
			}
			if !strings.Contains(text, q.expect) {
				t.Errorf("answer to %q missing %q:\n%s", q.question, q.expect, text)
			}
		})
	}
}
