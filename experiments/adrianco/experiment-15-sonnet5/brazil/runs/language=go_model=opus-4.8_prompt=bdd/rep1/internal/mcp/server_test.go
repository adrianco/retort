package mcp

import (
	"bufio"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"brazilian-soccer-mcp/internal/soccer"
)

// testServer builds a server over a tiny in-memory store.
func testServer() *Server {
	s := soccer.NewStore()
	fla := "Flamengo"
	pal := "Palmeiras"
	d := func(x string) time.Time { t, _ := time.Parse("2006-01-02", x); return t }
	mk := func(home, away string, hg, ag int, date string) soccer.Match {
		return soccer.Match{
			Competition: soccer.CompBrasileirao, Season: 2019, Date: d(date),
			HomeTeam: home, AwayTeam: away,
			HomeKey: soccer.NormalizeTeam(home), AwayKey: soccer.NormalizeTeam(away),
			HomeGoals: hg, AwayGoals: ag,
			HomeShots: -1, AwayShots: -1, HomeCorners: -1, AwayCorners: -1,
		}
	}
	s.AddMatches([]soccer.Match{
		mk(fla, pal, 3, 0, "2019-09-01"),
		mk(pal, fla, 1, 1, "2019-05-15"),
	})
	s.AddPlayers([]soccer.Player{
		{Name: "Gabriel Barbosa", NameKey: soccer.NormalizeName("Gabriel Barbosa"),
			Nationality: "Brazil", Overall: 84, Club: fla, ClubKey: soccer.NormalizeTeam(fla), Position: "ST"},
	})
	s.Index()
	return NewServer(s)
}

// roundTrip feeds a single request line through the server and returns the
// decoded response.
func roundTrip(t *testing.T, srv *Server, req string) Response {
	t.Helper()
	var out strings.Builder
	if err := srv.Serve(strings.NewReader(req+"\n"), &out); err != nil {
		t.Fatalf("serve error: %v", err)
	}
	var resp Response
	line := strings.TrimSpace(out.String())
	if line == "" {
		t.Fatalf("expected a response, got none")
	}
	if err := json.Unmarshal([]byte(line), &resp); err != nil {
		t.Fatalf("bad response JSON %q: %v", line, err)
	}
	return resp
}

// callTool decodes the ToolResult text from a tools/call response.
func callToolText(t *testing.T, srv *Server, name string, args map[string]any) (string, bool) {
	t.Helper()
	params, _ := json.Marshal(map[string]any{"name": name, "arguments": args})
	req, _ := json.Marshal(Request{JSONRPC: "2.0", ID: json.RawMessage(`1`), Method: "tools/call", Params: params})
	resp := roundTrip(t, srv, string(req))
	if resp.Error != nil {
		t.Fatalf("unexpected rpc error: %+v", resp.Error)
	}
	b, _ := json.Marshal(resp.Result)
	var tr ToolResult
	if err := json.Unmarshal(b, &tr); err != nil {
		t.Fatalf("bad tool result: %v", err)
	}
	if len(tr.Content) == 0 {
		return "", tr.IsError
	}
	return tr.Content[0].Text, tr.IsError
}

// Behaviour: the MCP handshake and discovery methods work.

func Test_given_initialize_when_called_then_protocol_version_returned(t *testing.T) {
	// Given a server
	srv := testServer()
	// When initialize is called
	resp := roundTrip(t, srv, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
	// Then a result with the protocol version is returned
	if resp.Error != nil {
		t.Fatalf("unexpected error: %+v", resp.Error)
	}
	b, _ := json.Marshal(resp.Result)
	if !strings.Contains(string(b), ProtocolVersion) {
		t.Errorf("expected protocol version in result, got %s", b)
	}
}

func Test_given_notification_when_received_then_no_response(t *testing.T) {
	// Given a server
	srv := testServer()
	// When an initialized notification (no id) is sent
	var out strings.Builder
	if err := srv.Serve(strings.NewReader(`{"jsonrpc":"2.0","method":"notifications/initialized"}`+"\n"), &out); err != nil {
		t.Fatalf("serve error: %v", err)
	}
	// Then nothing is written back
	if strings.TrimSpace(out.String()) != "" {
		t.Errorf("expected no response to notification, got %q", out.String())
	}
}

func Test_given_tools_list_when_called_then_expected_tools_present(t *testing.T) {
	// Given a server
	srv := testServer()
	// When tools/list is called
	resp := roundTrip(t, srv, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	// Then the core tools are advertised
	b, _ := json.Marshal(resp.Result)
	for _, want := range []string{"search_matches", "head_to_head", "team_record", "standings", "search_players", "match_statistics"} {
		if !strings.Contains(string(b), `"`+want+`"`) {
			t.Errorf("expected tool %q in list", want)
		}
	}
}

func Test_given_unknown_method_when_called_then_method_not_found_error(t *testing.T) {
	// Given a server
	srv := testServer()
	// When an unknown method is called
	resp := roundTrip(t, srv, `{"jsonrpc":"2.0","id":3,"method":"does/not/exist"}`)
	// Then a method-not-found error is returned
	if resp.Error == nil || resp.Error.Code != CodeMethodNotFound {
		t.Fatalf("expected method-not-found error, got %+v", resp.Error)
	}
}

// Behaviour: tools/call dispatches to handlers and formats answers.

func Test_given_head_to_head_tool_when_called_then_summary_returned(t *testing.T) {
	// Given a server
	srv := testServer()
	// When head_to_head is called for Flamengo vs Palmeiras
	text, isErr := callToolText(t, srv, "head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Palmeiras"})
	// Then a human-readable summary of the two meetings is returned
	if isErr {
		t.Fatalf("unexpected error result: %s", text)
	}
	if !strings.Contains(text, "Matches: 2") {
		t.Errorf("expected 2 matches in summary, got: %s", text)
	}
}

func Test_given_search_players_tool_when_called_then_player_listed(t *testing.T) {
	// Given a server
	srv := testServer()
	// When searching Brazilian players
	text, _ := callToolText(t, srv, "search_players", map[string]any{"nationality": "Brazil"})
	// Then the Brazilian player is listed
	if !strings.Contains(text, "Gabriel Barbosa") {
		t.Errorf("expected Gabriel Barbosa in output, got: %s", text)
	}
}

func Test_given_missing_required_arg_when_tool_called_then_error_result(t *testing.T) {
	// Given a server
	srv := testServer()
	// When team_record is called without a team
	text, isErr := callToolText(t, srv, "team_record", map[string]any{})
	// Then an error result explains the missing argument
	if !isErr {
		t.Fatalf("expected an error result, got: %s", text)
	}
}

func Test_given_unknown_tool_when_called_then_error_result(t *testing.T) {
	// Given a server
	srv := testServer()
	// When an unknown tool is invoked
	text, isErr := callToolText(t, srv, "no_such_tool", map[string]any{})
	// Then an error result is returned (not a crash)
	if !isErr || !strings.Contains(text, "unknown tool") {
		t.Fatalf("expected unknown-tool error, got: %s", text)
	}
}

// Behaviour: multiple requests over one stream each get a response line.

func Test_given_multiple_requests_when_served_then_each_gets_a_line(t *testing.T) {
	// Given a server and two requests on one stream
	srv := testServer()
	input := `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}` + "\n" +
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}` + "\n"
	// When served
	var out strings.Builder
	if err := srv.Serve(strings.NewReader(input), &out); err != nil {
		t.Fatalf("serve error: %v", err)
	}
	// Then exactly two response lines are produced
	sc := bufio.NewScanner(strings.NewReader(strings.TrimSpace(out.String())))
	n := 0
	for sc.Scan() {
		n++
	}
	if n != 2 {
		t.Fatalf("expected 2 response lines, got %d", n)
	}
}
