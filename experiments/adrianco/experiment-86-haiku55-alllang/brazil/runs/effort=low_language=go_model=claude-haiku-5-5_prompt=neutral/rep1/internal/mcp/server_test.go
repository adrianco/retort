package mcp

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/data"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := data.LoadDir("../data/testdata")
	if err != nil {
		t.Fatalf("LoadDir: %v", err)
	}
	return NewServer(store)
}

// send runs newline-delimited requests through the server and returns the decoded replies.
func send(t *testing.T, s *Server, lines ...string) []map[string]any {
	t.Helper()
	var out bytes.Buffer
	if err := s.Serve(strings.NewReader(strings.Join(lines, "\n")+"\n"), &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var replies []map[string]any
	for _, l := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if l == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(l), &m); err != nil {
			t.Fatalf("bad reply %q: %v", l, err)
		}
		replies = append(replies, m)
	}
	return replies
}

func callTool(t *testing.T, s *Server, name, args string) string {
	t.Helper()
	req := `{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"` + name + `","arguments":` + args + `}}`
	replies := send(t, s, req)
	if len(replies) != 1 {
		t.Fatalf("got %d replies", len(replies))
	}
	result, ok := replies[0]["result"].(map[string]any)
	if !ok {
		t.Fatalf("no result: %v", replies[0])
	}
	content := result["content"].([]any)
	return content[0].(map[string]any)["text"].(string)
}

// Scenario: a client initializes, lists tools and receives the server capabilities.
func TestInitializeAndListTools(t *testing.T) {
	s := newTestServer(t)
	// Given a connected MCP client
	// When it sends initialize, the initialized notification, and tools/list
	replies := send(t, s,
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)

	// Then there are two replies: the notification is not answered
	if len(replies) != 2 {
		t.Fatalf("got %d replies, want 2", len(replies))
	}
	init := replies[0]["result"].(map[string]any)
	if init["serverInfo"].(map[string]any)["name"] != "brazilian-soccer-mcp" {
		t.Errorf("serverInfo = %v", init["serverInfo"])
	}
	// And every required capability tool is listed with a schema
	tools := replies[1]["result"].(map[string]any)["tools"].([]any)
	names := map[string]bool{}
	for _, raw := range tools {
		tl := raw.(map[string]any)
		names[tl["name"].(string)] = true
		if tl["inputSchema"] == nil || tl["description"] == "" {
			t.Errorf("tool %v lacks schema or description", tl["name"])
		}
	}
	for _, want := range []string{"search_matches", "team_record", "head_to_head", "standings", "league_stats", "search_players", "team_profile"} {
		if !names[want] {
			t.Errorf("missing tool %s", want)
		}
	}
}

// Scenario: a head-to-head question is answered through tools/call.
func TestSearchMatchesToolCall(t *testing.T) {
	s := newTestServer(t)
	// Given the fixture match data is loaded
	// When the model asks for Flamengo vs Fluminense matches
	text := callTool(t, s, "search_matches", `{"team_a":"Flamengo","team_b":"Fluminense"}`)
	// Then the matches are listed with dates, scores and competitions
	for _, want := range []string{
		"2 matches found",
		"- 2023-05-28: Fluminense 1-0 Flamengo (Brasileirão Serie A, Round 8)",
		"- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Serie A, Round 22)",
	} {
		if !strings.Contains(text, want) {
			t.Errorf("response missing %q:\n%s", want, text)
		}
	}
}

// Scenario: the example team record in the spec is reproduced from match data.
func TestTeamRecordToolCall(t *testing.T) {
	s := newTestServer(t)
	// Given Palmeiras' 2023 Brasileirão results
	// When the team record is requested for 2023
	text := callTool(t, s, "team_record", `{"team":"Palmeiras","season":2023,"competition":"Brasileirão"}`)
	// Then the record shows wins, draws, goals and win rate
	for _, want := range []string{"Matches: 2", "Wins: 1, Draws: 1, Losses: 0", "Goals For: 4, Goals Against: 1", "Win rate: 50.0%"} {
		if !strings.Contains(text, want) {
			t.Errorf("missing %q in:\n%s", want, text)
		}
	}
}

// Scenario: a standings question returns a table with the leader first.
func TestStandingsToolCall(t *testing.T) {
	s := newTestServer(t)
	// Given the 2023 Brasileirão results
	// When the 2023 standings are requested
	text := callTool(t, s, "standings", `{"competition":"Brasileirão","season":2023}`)
	// Then Palmeiras lead with 4 points
	if !strings.Contains(text, "1. Palmeiras - 4 pts") {
		t.Errorf("unexpected standings:\n%s", text)
	}
}

// Scenario: a cross-file question combines match results and FIFA squad data.
func TestTeamProfileCombinesFiles(t *testing.T) {
	s := newTestServer(t)
	// Given Flamengo appear in match files and in the FIFA dataset
	// When the club profile is requested
	text := callTool(t, s, "team_profile", `{"team":"Flamengo"}`)
	// Then the profile includes both the match record and the squad summary
	if !strings.Contains(text, "Match record") || !strings.Contains(text, "Squad in FIFA dataset: 3 players") {
		t.Errorf("profile:\n%s", text)
	}
}

// Scenario: player search by nationality and position group.
func TestSearchPlayersToolCall(t *testing.T) {
	s := newTestServer(t)
	// Given the FIFA player fixture
	// When Brazilian goalkeepers are requested
	text := callTool(t, s, "search_players", `{"nationality":"Brazilian","position":"goalkeeper"}`)
	// Then only Alisson is returned
	if !strings.Contains(text, "1 players:") || !strings.Contains(text, "Alisson") {
		t.Errorf("players:\n%s", text)
	}
}

// Scenario: bad arguments are reported in-band so the model can correct them.
func TestToolErrorsAreInBand(t *testing.T) {
	s := newTestServer(t)
	// Given a date in an unsupported format
	// When a match search is made with it
	req := `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"from":"next week"}}}`
	replies := send(t, s, req)
	result := replies[0]["result"].(map[string]any)
	// Then the result is flagged isError with the reason, not a protocol error
	if result["isError"] != true || replies[0]["error"] != nil {
		t.Fatalf("reply = %v", replies[0])
	}
	if !strings.Contains(result["content"].([]any)[0].(map[string]any)["text"].(string), "unrecognised date") {
		t.Errorf("reply = %v", replies[0])
	}
}

// Scenario: protocol-level mistakes get JSON-RPC errors.
func TestProtocolErrors(t *testing.T) {
	s := newTestServer(t)
	tests := []struct {
		name string
		line string
		code float64
	}{
		{"malformed JSON", `{"jsonrpc":`, -32700},
		{"unknown method", `{"jsonrpc":"2.0","id":1,"method":"resources/list"}`, -32601},
		{"unknown tool", `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nope"}}`, -32602},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Given an invalid request
			// When it is sent to the server
			replies := send(t, s, tt.line)
			// Then a JSON-RPC error with the expected code is returned
			errObj, ok := replies[0]["error"].(map[string]any)
			if !ok || errObj["code"] != tt.code {
				t.Fatalf("reply = %v, want error code %v", replies[0], tt.code)
			}
		})
	}
}

// Scenario: ping is answered with an empty result.
func TestPing(t *testing.T) {
	s := newTestServer(t)
	// Given a client health check
	// When it sends ping
	replies := send(t, s, `{"jsonrpc":"2.0","id":9,"method":"ping"}`)
	// Then the server replies with an empty result for the same id
	if len(replies) != 1 || replies[0]["id"] != float64(9) {
		t.Fatalf("reply = %v", replies)
	}
}
