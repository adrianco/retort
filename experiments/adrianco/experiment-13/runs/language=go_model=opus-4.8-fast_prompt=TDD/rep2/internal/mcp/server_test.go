package mcp

import (
	"encoding/json"
	"strings"
	"testing"
	"time"

	"brazilian-soccer-mcp/internal/soccer"
)

func testServer() *Server {
	d := func(s string) time.Time { tv, _ := soccer.ParseDate(s); return tv }
	kb := &soccer.KB{
		Matches: []soccer.Match{
			{Competition: soccer.CompBrasileirao, Season: 2019, HasDate: true, Date: d("2019-10-27"),
				HomeTeam: "Flamengo-RJ", AwayTeam: "Gremio-RS", HomeGoals: 5, AwayGoals: 0,
				HasScore: true, Source: "Brasileirao_Matches.csv"},
			{Competition: soccer.CompBrasileirao, Season: 2019, HasDate: true, Date: d("2019-05-01"),
				HomeTeam: "Gremio-RS", AwayTeam: "Flamengo-RJ", HomeGoals: 1, AwayGoals: 1,
				HasScore: true, Source: "Brasileirao_Matches.csv"},
		},
		Players: []soccer.Player{
			{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain", Position: "LW"},
			{ID: 2, Name: "Casemiro", Nationality: "Brazil", Overall: 89, Club: "Real Madrid", Position: "CDM"},
		},
	}
	return New(kb)
}

// roundTrip marshals params, dispatches a request, and returns the decoded response.
func roundTrip(t *testing.T, s *Server, method string, params interface{}) response {
	t.Helper()
	var raw json.RawMessage
	if params != nil {
		b, err := json.Marshal(params)
		if err != nil {
			t.Fatal(err)
		}
		raw = b
	}
	req := request{JSONRPC: "2.0", ID: json.RawMessage(`1`), Method: method, Params: raw}
	resp, ok := s.handle(req)
	if !ok {
		t.Fatalf("method %q produced no response", method)
	}
	return *resp
}

func TestInitialize(t *testing.T) {
	s := testServer()
	resp := roundTrip(t, s, "initialize", map[string]any{"protocolVersion": "2024-11-05"})
	if resp.Error != nil {
		t.Fatalf("error: %+v", resp.Error)
	}
	res, _ := json.Marshal(resp.Result)
	if !strings.Contains(string(res), "serverInfo") || !strings.Contains(string(res), "protocolVersion") {
		t.Errorf("initialize result missing fields: %s", res)
	}
}

func TestInitializedNotificationHasNoResponse(t *testing.T) {
	s := testServer()
	req := request{JSONRPC: "2.0", Method: "notifications/initialized"}
	if _, ok := s.handle(req); ok {
		t.Error("notification should not produce a response")
	}
}

func TestToolsList(t *testing.T) {
	s := testServer()
	resp := roundTrip(t, s, "tools/list", nil)
	if resp.Error != nil {
		t.Fatalf("error: %+v", resp.Error)
	}
	b, _ := json.Marshal(resp.Result)
	var lr struct {
		Tools []struct {
			Name        string          `json:"name"`
			Description string          `json:"description"`
			InputSchema json.RawMessage `json:"inputSchema"`
		} `json:"tools"`
	}
	if err := json.Unmarshal(b, &lr); err != nil {
		t.Fatal(err)
	}
	want := map[string]bool{
		"search_matches": false, "head_to_head": false, "team_record": false,
		"search_players": false, "standings": false, "competition_stats": false,
	}
	for _, tool := range lr.Tools {
		if _, ok := want[tool.Name]; ok {
			want[tool.Name] = true
		}
		if tool.Description == "" || len(tool.InputSchema) == 0 {
			t.Errorf("tool %q missing description or schema", tool.Name)
		}
	}
	for name, found := range want {
		if !found {
			t.Errorf("tool %q not advertised", name)
		}
	}
}

// callText dispatches tools/call and returns the concatenated text content.
func callText(t *testing.T, s *Server, name string, args map[string]any) (string, bool) {
	t.Helper()
	resp := roundTrip(t, s, "tools/call", map[string]any{"name": name, "arguments": args})
	if resp.Error != nil {
		t.Fatalf("transport error: %+v", resp.Error)
	}
	b, _ := json.Marshal(resp.Result)
	var cr struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(b, &cr); err != nil {
		t.Fatal(err)
	}
	var sb strings.Builder
	for _, c := range cr.Content {
		sb.WriteString(c.Text)
	}
	return sb.String(), cr.IsError
}

func TestCallSearchPlayers(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "search_players", map[string]any{"nationality": "Brazil"})
	if isErr {
		t.Fatalf("unexpected tool error: %s", out)
	}
	if !strings.Contains(out, "Neymar Jr") || !strings.Contains(out, "Casemiro") {
		t.Errorf("output missing players:\n%s", out)
	}
	// Highest-rated should be listed first.
	if strings.Index(out, "Neymar Jr") > strings.Index(out, "Casemiro") {
		t.Errorf("players not sorted by rating:\n%s", out)
	}
}

func TestCallStandings(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "standings", map[string]any{"competition": "Brasileirão", "season": 2019})
	if isErr {
		t.Fatalf("unexpected tool error: %s", out)
	}
	if !strings.Contains(out, "Flamengo") {
		t.Errorf("standings missing Flamengo:\n%s", out)
	}
}

func TestCallSearchMatches(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "search_matches", map[string]any{"team": "Flamengo"})
	if isErr {
		t.Fatalf("unexpected tool error: %s", out)
	}
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "5-0") {
		t.Errorf("matches output unexpected:\n%s", out)
	}
}

func TestCallUnknownToolIsError(t *testing.T) {
	s := testServer()
	out, isErr := callText(t, s, "no_such_tool", map[string]any{})
	if !isErr {
		t.Errorf("expected tool error for unknown tool, got: %s", out)
	}
}
