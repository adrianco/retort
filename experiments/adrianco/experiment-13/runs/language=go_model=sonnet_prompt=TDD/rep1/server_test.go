package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func sendRequest(t *testing.T, db *Database, req string) map[string]interface{} {
	t.Helper()
	var out strings.Builder
	RunMCPServer(db, strings.NewReader(req+"\n"), &out)
	line := strings.TrimSpace(out.String())
	if line == "" {
		return nil
	}
	var result map[string]interface{}
	if err := json.Unmarshal([]byte(line), &result); err != nil {
		t.Fatalf("unmarshal response: %v\nresponse was: %s", err, line)
	}
	return result
}

func getResult(t *testing.T, resp map[string]interface{}) map[string]interface{} {
	t.Helper()
	r, ok := resp["result"].(map[string]interface{})
	if !ok {
		t.Fatalf("no result in response: %v", resp)
	}
	return r
}

func getToolText(t *testing.T, resp map[string]interface{}) string {
	t.Helper()
	r := getResult(t, resp)
	content, ok := r["content"].([]interface{})
	if !ok || len(content) == 0 {
		t.Fatalf("no content in result: %v", r)
	}
	item := content[0].(map[string]interface{})
	return item["text"].(string)
}

func TestServerInitialize(t *testing.T) {
	db := testDB()
	resp := sendRequest(t, db, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}`)
	result := getResult(t, resp)
	if result["protocolVersion"] != "2024-11-05" {
		t.Errorf("protocolVersion = %v, want 2024-11-05", result["protocolVersion"])
	}
	info := result["serverInfo"].(map[string]interface{})
	if info["name"] != "brazilian-soccer-mcp" {
		t.Errorf("serverInfo.name = %v, want brazilian-soccer-mcp", info["name"])
	}
}

func TestServerToolsList(t *testing.T) {
	db := testDB()
	resp := sendRequest(t, db, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	result := getResult(t, resp)
	tools := result["tools"].([]interface{})
	if len(tools) < 6 {
		t.Errorf("expected at least 6 tools, got %d", len(tools))
	}
	names := make(map[string]bool)
	for _, tool := range tools {
		t := tool.(map[string]interface{})
		names[t["name"].(string)] = true
	}
	for _, want := range []string{"search_matches", "get_head_to_head", "get_team_stats", "get_standings", "search_players", "get_statistics"} {
		if !names[want] {
			t.Errorf("tool %q not in list", want)
		}
	}
}

func TestServerToolCallSearchMatches(t *testing.T) {
	db := testDB()
	req := `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","season":2023}}}`
	resp := sendRequest(t, db, req)
	text := getToolText(t, resp)
	if !strings.Contains(text, "Flamengo") {
		t.Errorf("expected Flamengo in response, got: %s", text)
	}
	if !strings.Contains(text, "2023") {
		t.Errorf("expected 2023 in response, got: %s", text)
	}
}

func TestServerToolCallHeadToHead(t *testing.T) {
	db := testDB()
	req := `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_head_to_head","arguments":{"team1":"Flamengo","team2":"Corinthians"}}}`
	resp := sendRequest(t, db, req)
	text := getToolText(t, resp)
	if !strings.Contains(text, "Head-to-head") {
		t.Errorf("expected Head-to-head in response, got: %s", text)
	}
	if !strings.Contains(text, "wins") {
		t.Errorf("expected wins in response, got: %s", text)
	}
}

func TestServerToolCallTeamStats(t *testing.T) {
	db := testDB()
	req := `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_team_stats","arguments":{"team":"Palmeiras","competition":"brasileirao"}}}`
	resp := sendRequest(t, db, req)
	text := getToolText(t, resp)
	if !strings.Contains(text, "Palmeiras") {
		t.Errorf("expected Palmeiras in response, got: %s", text)
	}
	if !strings.Contains(text, "Wins") {
		t.Errorf("expected Wins in response, got: %s", text)
	}
}

func TestServerToolCallStandings(t *testing.T) {
	db := testDB()
	req := `{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"get_standings","arguments":{"competition":"brasileirao","season":2023}}}`
	resp := sendRequest(t, db, req)
	text := getToolText(t, resp)
	if !strings.Contains(text, "Standings") {
		t.Errorf("expected Standings in response, got: %s", text)
	}
}

func TestServerToolCallSearchPlayers(t *testing.T) {
	db := testDB()
	req := `{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"search_players","arguments":{"nationality":"Brazil"}}}`
	resp := sendRequest(t, db, req)
	text := getToolText(t, resp)
	if !strings.Contains(text, "Brazil") {
		t.Errorf("expected Brazil in response, got: %s", text)
	}
}

func TestServerToolCallStatistics(t *testing.T) {
	db := testDB()
	req := `{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"get_statistics","arguments":{"competition":"brasileirao"}}}`
	resp := sendRequest(t, db, req)
	text := getToolText(t, resp)
	if !strings.Contains(text, "goals per match") {
		t.Errorf("expected 'goals per match' in response, got: %s", text)
	}
}

func TestServerUnknownTool(t *testing.T) {
	db := testDB()
	req := `{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"unknown_tool","arguments":{}}}`
	resp := sendRequest(t, db, req)
	text := getToolText(t, resp)
	if !strings.Contains(text, "Error") {
		t.Errorf("expected Error in response for unknown tool, got: %s", text)
	}
	result := getResult(t, resp)
	if result["isError"] != true {
		t.Error("expected isError=true for unknown tool")
	}
}

func TestServerUnknownMethod(t *testing.T) {
	db := testDB()
	var out strings.Builder
	RunMCPServer(db, strings.NewReader(`{"jsonrpc":"2.0","id":10,"method":"unknown/method"}`+"\n"), &out)
	line := strings.TrimSpace(out.String())
	var resp map[string]interface{}
	json.Unmarshal([]byte(line), &resp)
	if resp["error"] == nil {
		t.Error("expected error for unknown method")
	}
}

func TestServerNotificationNoResponse(t *testing.T) {
	db := testDB()
	var out strings.Builder
	RunMCPServer(db, strings.NewReader(`{"jsonrpc":"2.0","method":"notifications/initialized"}`+"\n"), &out)
	if strings.TrimSpace(out.String()) != "" {
		t.Errorf("expected no response to notification, got: %s", out.String())
	}
}
