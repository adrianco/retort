package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

const dataDir = "data/kaggle"

// loadTestDB loads the real CSVs once for integration tests.
func loadTestDB(t *testing.T) *Database {
	t.Helper()
	db, err := LoadDatabase(dataDir)
	if err != nil {
		t.Fatalf("LoadDatabase: %v", err)
	}
	if len(db.Matches) == 0 {
		t.Fatal("no matches loaded")
	}
	if len(db.Players) == 0 {
		t.Fatal("no players loaded")
	}
	return db
}

// --- Unit tests for data normalization ---

func TestNormalize(t *testing.T) {
	cases := []struct {
		in, want string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Santos", "Santos"},
		{"  Corinthians-SP  ", "Corinthians"},
		{"América - MG", "América - MG"},
	}
	for _, c := range cases {
		got := normalize(c.in)
		if got != c.want {
			t.Errorf("normalize(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestParseDate(t *testing.T) {
	cases := []struct {
		in   string
		year int
	}{
		{"2023-09-24", 2023},
		{"2012-05-19 18:30:00", 2012},
		{"29/03/2003", 2003},
	}
	for _, c := range cases {
		t.Run(c.in, func(t *testing.T) {
			d, err := parseDate(c.in)
			if err != nil {
				t.Fatalf("parseDate(%q) error: %v", c.in, err)
			}
			if d.Year() != c.year {
				t.Errorf("parseDate(%q).Year = %d, want %d", c.in, d.Year(), c.year)
			}
		})
	}
}

// --- Integration tests using real data ---

func TestLoadDatabase_MatchCount(t *testing.T) {
	db := loadTestDB(t)
	// We expect at least 20,000 matches across all 5 files.
	if len(db.Matches) < 20000 {
		t.Errorf("expected >= 20000 matches, got %d", len(db.Matches))
	}
	t.Logf("Loaded %d matches", len(db.Matches))
}

func TestLoadDatabase_PlayerCount(t *testing.T) {
	db := loadTestDB(t)
	if len(db.Players) < 10000 {
		t.Errorf("expected >= 10000 players, got %d", len(db.Players))
	}
	t.Logf("Loaded %d players", len(db.Players))
}

func TestFilterMatches_ByTeam(t *testing.T) {
	db := loadTestDB(t)
	matches := db.FilterMatches("Flamengo", "", 0)
	if len(matches) == 0 {
		t.Fatal("expected matches for Flamengo, got none")
	}
	t.Logf("Flamengo matches: %d", len(matches))
	// Verify all matches actually involve Flamengo.
	for _, m := range matches[:min(10, len(matches))] {
		ht := normalizeLower(m.HomeTeam)
		at := normalizeLower(m.AwayTeam)
		if !strings.Contains(ht, "flamengo") && !strings.Contains(at, "flamengo") {
			t.Errorf("match %v does not involve Flamengo", m)
		}
	}
}

func TestFilterMatches_BySeason(t *testing.T) {
	db := loadTestDB(t)
	// "brasileirao" matches "Brasileirão Serie A" via accent-insensitive search.
	matches := db.FilterMatches("", "brasileirao", 2019)
	if len(matches) == 0 {
		t.Fatal("expected matches for Brasileirão 2019")
	}
	t.Logf("Brasileirão 2019 matches: %d", len(matches))
	for _, m := range matches {
		if m.Season != 2019 {
			t.Errorf("match season = %d, want 2019", m.Season)
		}
	}
}

func TestFilterMatchesH2H(t *testing.T) {
	db := loadTestDB(t)
	matches := db.FilterMatchesH2H("Flamengo", "Fluminense")
	if len(matches) == 0 {
		t.Fatal("expected head-to-head matches for Flamengo vs Fluminense")
	}
	t.Logf("Flamengo vs Fluminense: %d matches", len(matches))
}

func TestStandings_2019(t *testing.T) {
	db := loadTestDB(t)
	standings := db.Standings("brasileirao", 2019)
	if len(standings) == 0 {
		t.Fatal("expected standings for Brasileirão 2019")
	}
	t.Logf("Standings leader: %s (%d pts)", standings[0].Team, standings[0].Points)
	// Flamengo was the 2019 champion.
	if !strings.Contains(strings.ToLower(standings[0].Team), "flamengo") {
		t.Logf("Note: leader is %s (Flamengo expected as 2019 champion)", standings[0].Team)
	}
}

func TestTeamStats(t *testing.T) {
	db := loadTestDB(t)
	// Use 2019 which is covered by both Brasileirao_Matches.csv and novo_campeonato_brasileiro.csv.
	matches := db.FilterMatches("Corinthians", "brasileirao", 2019)
	rec := TeamStats("Corinthians", matches, false)
	if rec.Matches == 0 {
		t.Fatal("expected Corinthians matches in 2019 Brasileirão")
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Errorf("W+D+L (%d+%d+%d=%d) != Matches (%d)",
			rec.Wins, rec.Draws, rec.Losses, rec.Wins+rec.Draws+rec.Losses, rec.Matches)
	}
	t.Logf("Corinthians 2019: %dW %dD %dL in %d matches", rec.Wins, rec.Draws, rec.Losses, rec.Matches)
}

func TestBiggestWins(t *testing.T) {
	db := loadTestDB(t)
	wins := db.BiggestWins(5, "", 0)
	if len(wins) == 0 {
		t.Fatal("expected biggest wins")
	}
	// Verify descending order by goal diff.
	for i := 1; i < len(wins); i++ {
		prev := abs(wins[i-1].HomeGoals - wins[i-1].AwayGoals)
		curr := abs(wins[i].HomeGoals - wins[i].AwayGoals)
		if prev < curr {
			t.Errorf("not sorted: [%d] diff=%d, [%d] diff=%d", i-1, prev, i, curr)
		}
	}
	t.Logf("Biggest win: %s %d-%d %s (diff %d)",
		wins[0].HomeTeam, wins[0].HomeGoals, wins[0].AwayGoals, wins[0].AwayTeam,
		abs(wins[0].HomeGoals-wins[0].AwayGoals))
}

func TestFilterPlayers_Brazilian(t *testing.T) {
	db := loadTestDB(t)
	players := db.FilterPlayers("", "Brazil", "", "")
	if len(players) == 0 {
		t.Fatal("expected Brazilian players")
	}
	t.Logf("Brazilian players: %d", len(players))
	// Verify sorted by overall.
	for i := 1; i < len(players) && i < 50; i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Errorf("not sorted by overall at %d: %d < %d", i, players[i-1].Overall, players[i].Overall)
		}
	}
}

func TestFilterPlayers_ByClub(t *testing.T) {
	db := loadTestDB(t)
	players := db.FilterPlayers("", "", "Flamengo", "")
	t.Logf("Flamengo players: %d", len(players))
	// Each player's club should contain "flamengo".
	for _, p := range players {
		if !strings.Contains(strings.ToLower(p.Club), "flamengo") {
			t.Errorf("player %s club %q doesn't contain 'flamengo'", p.Name, p.Club)
		}
	}
}

func TestFilterPlayers_ByName(t *testing.T) {
	db := loadTestDB(t)
	players := db.FilterPlayers("Neymar", "", "", "")
	if len(players) == 0 {
		t.Fatal("expected to find Neymar")
	}
	t.Logf("Found %s, Overall %d, Club %s", players[0].Name, players[0].Overall, players[0].Club)
}

func TestGoalsPerMatch(t *testing.T) {
	db := loadTestDB(t)
	// "brasileirao" matches "Brasileirão Serie A" via accent-insensitive search.
	matches := db.FilterMatches("", "brasileirao", 0)
	if len(matches) == 0 {
		t.Fatal("expected brasileirao matches")
	}
	gpm := GoalsPerMatch(matches)
	if gpm < 1.0 || gpm > 6.0 {
		t.Errorf("suspicious goals per match: %.2f", gpm)
	}
	t.Logf("Brasileirão goals per match: %.2f (from %d matches)", gpm, len(matches))
}

func TestHomeWinRate(t *testing.T) {
	db := loadTestDB(t)
	matches := db.FilterMatches("", "", 0)
	hwr := HomeWinRate(matches)
	if hwr < 20 || hwr > 80 {
		t.Errorf("suspicious home win rate: %.1f%%", hwr)
	}
	t.Logf("Overall home win rate: %.1f%%", hwr)
}

// --- MCP protocol tests ---

func TestMCPInitialize(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	req := Request{
		JSONRPC: "2.0",
		ID:      1,
		Method:  "initialize",
		Params:  json.RawMessage(`{"protocolVersion":"2024-11-05","capabilities":{}}`),
	}
	resp := server.handleRequest(req)
	if resp.Error != nil {
		t.Fatalf("initialize error: %v", resp.Error)
	}
	result, ok := resp.Result.(InitializeResult)
	if !ok {
		t.Fatalf("unexpected result type: %T", resp.Result)
	}
	if result.ProtocolVersion == "" {
		t.Error("expected non-empty protocol version")
	}
	if result.Capabilities.Tools == nil {
		t.Error("expected tools capability")
	}
}

func TestMCPToolsList(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	req := Request{
		JSONRPC: "2.0",
		ID:      2,
		Method:  "tools/list",
	}
	resp := server.handleRequest(req)
	if resp.Error != nil {
		t.Fatalf("tools/list error: %v", resp.Error)
	}
	result, ok := resp.Result.(ToolsListResult)
	if !ok {
		t.Fatalf("unexpected result type: %T", resp.Result)
	}
	if len(result.Tools) == 0 {
		t.Fatal("expected at least one tool")
	}
	t.Logf("Tools available: %d", len(result.Tools))
	for _, tool := range result.Tools {
		if tool.Name == "" {
			t.Error("tool with empty name")
		}
	}
}

func TestMCPToolCall_SearchMatches(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	params := CallToolParams{
		Name:      "search_matches",
		Arguments: json.RawMessage(`{"team":"Flamengo","season":2019,"limit":5}`),
	}
	paramsJSON, _ := json.Marshal(params)
	req := Request{
		JSONRPC: "2.0",
		ID:      3,
		Method:  "tools/call",
		Params:  paramsJSON,
	}
	resp := server.handleRequest(req)
	if resp.Error != nil {
		t.Fatalf("tools/call error: %v", resp.Error)
	}
	result, ok := resp.Result.(CallToolResult)
	if !ok {
		t.Fatalf("unexpected result type: %T", resp.Result)
	}
	if result.IsError {
		t.Fatalf("tool returned error: %v", result.Content)
	}
	if len(result.Content) == 0 || result.Content[0].Text == "" {
		t.Fatal("expected non-empty result")
	}
	t.Logf("search_matches result:\n%s", result.Content[0].Text)
}

func TestMCPToolCall_TeamStats(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	params := CallToolParams{
		Name:      "get_team_stats",
		Arguments: json.RawMessage(`{"team":"Palmeiras","competition":"brasileirao","season":2022}`),
	}
	paramsJSON, _ := json.Marshal(params)
	req := Request{
		JSONRPC: "2.0",
		ID:      4,
		Method:  "tools/call",
		Params:  paramsJSON,
	}
	resp := server.handleRequest(req)
	if resp.Error != nil {
		t.Fatalf("tools/call error: %v", resp.Error)
	}
	result := resp.Result.(CallToolResult)
	t.Logf("team stats result:\n%s", result.Content[0].Text)
}

func TestMCPToolCall_Standings(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	params := CallToolParams{
		Name:      "get_standings",
		Arguments: json.RawMessage(`{"competition":"brasileirao","season":2019,"limit":5}`),
	}
	paramsJSON, _ := json.Marshal(params)
	req := Request{
		JSONRPC: "2.0",
		ID:      5,
		Method:  "tools/call",
		Params:  paramsJSON,
	}
	resp := server.handleRequest(req)
	result := resp.Result.(CallToolResult)
	if result.IsError {
		t.Fatalf("standings error: %v", result.Content[0].Text)
	}
	t.Logf("standings result:\n%s", result.Content[0].Text)
}

func TestMCPToolCall_SearchPlayers(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	params := CallToolParams{
		Name:      "search_players",
		Arguments: json.RawMessage(`{"nationality":"Brazil","limit":5}`),
	}
	paramsJSON, _ := json.Marshal(params)
	req := Request{
		JSONRPC: "2.0",
		ID:      6,
		Method:  "tools/call",
		Params:  paramsJSON,
	}
	resp := server.handleRequest(req)
	result := resp.Result.(CallToolResult)
	if result.IsError {
		t.Fatalf("search_players error: %s", result.Content[0].Text)
	}
	if !strings.Contains(result.Content[0].Text, "Brazil") {
		t.Error("expected 'Brazil' in result")
	}
	t.Logf("search_players result:\n%s", result.Content[0].Text)
}

func TestMCPToolCall_H2H(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	params := CallToolParams{
		Name:      "search_matches",
		Arguments: json.RawMessage(`{"team":"Flamengo","team2":"Fluminense","limit":5}`),
	}
	paramsJSON, _ := json.Marshal(params)
	req := Request{
		JSONRPC: "2.0",
		ID:      7,
		Method:  "tools/call",
		Params:  paramsJSON,
	}
	resp := server.handleRequest(req)
	result := resp.Result.(CallToolResult)
	if result.IsError {
		t.Fatalf("h2h error: %s", result.Content[0].Text)
	}
	t.Logf("H2H result:\n%s", result.Content[0].Text)
}

func TestMCPToolCall_CompetitionStats(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	params := CallToolParams{
		Name:      "get_competition_stats",
		Arguments: json.RawMessage(`{"competition":"brasileirao","season":2019}`),
	}
	paramsJSON, _ := json.Marshal(params)
	req := Request{
		JSONRPC: "2.0",
		ID:      8,
		Method:  "tools/call",
		Params:  paramsJSON,
	}
	resp := server.handleRequest(req)
	result := resp.Result.(CallToolResult)
	if result.IsError {
		t.Fatalf("competition_stats error: %s", result.Content[0].Text)
	}
	t.Logf("competition_stats result:\n%s", result.Content[0].Text)
}

// TestMCPRun tests the full stdio-based JSON-RPC loop.
func TestMCPRun(t *testing.T) {
	db := loadTestDB(t)
	server := NewServer(db)

	requests := []map[string]interface{}{
		{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": map[string]interface{}{
			"protocolVersion": "2024-11-05",
			"capabilities":    map[string]interface{}{},
		}},
		{"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
		{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": map[string]interface{}{
			"name":      "search_matches",
			"arguments": map[string]interface{}{"team": "Santos", "limit": 3},
		}},
	}

	var input bytes.Buffer
	for _, r := range requests {
		data, _ := json.Marshal(r)
		input.Write(data)
		input.WriteByte('\n')
	}

	var output bytes.Buffer
	server.Run(&input, &output)

	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	if len(lines) != len(requests) {
		t.Fatalf("expected %d responses, got %d", len(requests), len(lines))
	}
	for i, line := range lines {
		var resp Response
		if err := json.Unmarshal([]byte(line), &resp); err != nil {
			t.Fatalf("response %d parse error: %v", i, err)
		}
		if resp.Error != nil {
			t.Errorf("response %d error: %v", i, resp.Error)
		}
	}
}

// TestSample20Questions ensures at least 20 types of questions can be answered.
func TestSample20Questions(t *testing.T) {
	db := loadTestDB(t)
	s := NewServer(db)

	type question struct {
		desc   string
		tool   string
		args   string
		expect string // substring expected in result
	}

	questions := []question{
		{"When did Flamengo last play Corinthians?", "search_matches", `{"team":"Flamengo","team2":"Corinthians","limit":1}`, "Flamengo"},
		{"All Flamengo vs Fluminense matches", "search_matches", `{"team":"Flamengo","team2":"Fluminense"}`, "Head-to-head"},
		{"Palmeiras matches in 2022", "search_matches", `{"team":"Palmeiras","season":2022}`, "Palmeiras"},
		{"Copa do Brasil matches 2021", "search_matches", `{"competition":"copa do brasil","season":2021}`, "Copa do Brasil"},
		{"Copa Libertadores matches 2019", "search_matches", `{"competition":"libertadores","season":2019}`, ""},
		{"Corinthians home record 2022", "get_team_stats", `{"team":"Corinthians","season":2022,"home_only":true}`, "home"},
		{"Santos overall record all time", "get_team_stats", `{"team":"Santos"}`, "Matches"},
		{"Brasileirao 2019 standings", "get_standings", `{"competition":"brasileirao serie a","season":2019,"limit":10}`, "Pos"},
		{"Copa do Brasil 2018 standings", "get_standings", `{"competition":"copa do brasil","season":2018}`, ""},
		{"Biggest wins all time", "get_biggest_wins", `{"limit":5}`, "Biggest wins"},
		{"Biggest wins Brasileirao 2019", "get_biggest_wins", `{"competition":"brasileirao","season":2019,"limit":5}`, "Biggest wins"},
		{"Find Neymar", "search_players", `{"name":"Neymar"}`, "Neymar"},
		{"Top Brazilian players", "search_players", `{"nationality":"Brazil","limit":10}`, "Brazil"},
		{"Flamengo FIFA players", "search_players", `{"club":"Flamengo"}`, ""},
		{"All forwards from Sao Paulo", "search_players", `{"club":"Sao Paulo","position":"ST"}`, ""},
		{"Average goals Brasileirao", "get_competition_stats", `{"competition":"brasileirao"}`, "Goals Per Match"},
		{"Brasileirao 2022 season stats", "get_competition_stats", `{"competition":"brasileirao","season":2022}`, ""},
		{"List teams in Libertadores 2019", "list_teams", `{"competition":"libertadores","season":2019}`, "Teams in"},
		{"List all teams in Brasileirao", "list_teams", `{"competition":"brasileirao"}`, "Teams in"},
		{"Who scored most goals 2019", "get_competition_stats", `{"season":2019}`, "Top Scoring"},
	}

	passed := 0
	for _, q := range questions {
		t.Run(q.desc, func(t *testing.T) {
			result, err := s.callTool(q.tool, json.RawMessage(q.args))
			if err != nil {
				t.Errorf("error: %v", err)
				return
			}
			if result == "" {
				t.Error("empty result")
				return
			}
			if q.expect != "" && !strings.Contains(result, q.expect) {
				t.Errorf("expected %q in result, got: %.200s", q.expect, result)
				return
			}
			passed++
			shortResult := result
			if len(shortResult) > 150 {
				shortResult = shortResult[:150] + "..."
			}
			t.Logf("OK: %s", fmt.Sprintf("%.80s", shortResult))
		})
	}
	t.Logf("Passed: %d/%d questions", passed, len(questions))
}
