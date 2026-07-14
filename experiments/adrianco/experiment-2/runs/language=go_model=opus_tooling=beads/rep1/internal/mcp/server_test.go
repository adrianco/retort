package mcp

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"brsoccer/internal/data"
)

func testDB() *data.DB {
	return &data.DB{
		Matches: []data.Match{
			{HomeTeam: "Flamengo", AwayTeam: "Fluminense", HomeGoals: 2, AwayGoals: 1, Season: 2023, Competition: "Brasileirão Série A"},
		},
		Players: []data.Player{
			{Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "PSG", Position: "LW"},
		},
	}
}

// Feature: MCP initialize handshake
func TestMCPInitialize(t *testing.T) {
	s := NewServer("test", "0.0.1")
	RegisterSoccerTools(s, testDB())
	in := strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}` + "\n")
	var out bytes.Buffer
	if err := s.Serve(in, &out); err != nil {
		t.Fatal(err)
	}
	var resp Response
	if err := json.Unmarshal(out.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	if resp.Error != nil {
		t.Fatalf("error: %v", resp.Error)
	}
}

// Feature: Tool listing advertises all registered tools
func TestMCPToolsList(t *testing.T) {
	s := NewServer("test", "0.0.1")
	RegisterSoccerTools(s, testDB())
	in := strings.NewReader(`{"jsonrpc":"2.0","id":2,"method":"tools/list"}` + "\n")
	var out bytes.Buffer
	if err := s.Serve(in, &out); err != nil {
		t.Fatal(err)
	}
	var resp struct {
		Result struct {
			Tools []ToolSchema `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(out.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	if len(resp.Result.Tools) < 5 {
		t.Errorf("expected at least 5 tools, got %d", len(resp.Result.Tools))
	}
}

// Feature: tools/call executes handler and returns content
func TestMCPToolCall(t *testing.T) {
	s := NewServer("test", "0.0.1")
	RegisterSoccerTools(s, testDB())
	msg := `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Flamengo"}}}` + "\n"
	var out bytes.Buffer
	if err := s.Serve(strings.NewReader(msg), &out); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out.String(), "Flamengo") {
		t.Errorf("expected response to reference Flamengo, got: %s", out.String())
	}
}

// Feature: Notifications receive no reply
func TestMCPNotification(t *testing.T) {
	s := NewServer("test", "0.0.1")
	in := strings.NewReader(`{"jsonrpc":"2.0","method":"notifications/initialized"}` + "\n")
	var out bytes.Buffer
	if err := s.Serve(in, &out); err != nil {
		t.Fatal(err)
	}
	if out.Len() != 0 {
		t.Errorf("expected no output for notification, got: %s", out.String())
	}
}
