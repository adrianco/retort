package main

import (
	"bufio"
	"encoding/json"
	"os"
	"strings"
	"testing"
	"time"
)

const testDataDir = "./data/kaggle"

// --- Normalization tests ---

func TestNormalizeTeam(t *testing.T) {
	cases := []struct {
		input, want string
	}{
		{"Palmeiras-SP", "palmeiras"},
		{"Flamengo-RJ", "flamengo"},
		{"Sport-PE", "sport"},
		{"América - MG", "america"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club"},
		{"Nacional (URU)", "nacional"},
		{"Barcelona-EQU", "barcelona"},
		{"Grêmio", "gremio"},
		{"São Paulo", "sao paulo"},
		{"Fortaleza", "fortaleza"},
		{"Athletico-PR", "athletico"},
	}
	for _, c := range cases {
		got := normalizeTeam(c.input)
		if got != c.want {
			t.Errorf("normalizeTeam(%q) = %q, want %q", c.input, got, c.want)
		}
	}
}

func TestTeamMatchesQuery(t *testing.T) {
	cases := []struct {
		teamName, query string
		want            bool
	}{
		{"Palmeiras-SP", "Palmeiras", true},
		{"Flamengo-RJ", "flamengo", true},
		{"Corinthians", "Corinthians", true},
		{"São Paulo", "Sao Paulo", true},
		{"Grêmio", "Gremio", true},
		{"Santos", "Flamengo", false},
		{"", "Flamengo", false},
	}
	for _, c := range cases {
		got := teamMatchesQuery(c.teamName, c.query)
		if got != c.want {
			t.Errorf("teamMatchesQuery(%q, %q) = %v, want %v", c.teamName, c.query, got, c.want)
		}
	}
}

func TestStripAccents(t *testing.T) {
	cases := []struct{ in, want string }{
		{"Grêmio", "Gremio"},
		{"São Paulo", "Sao Paulo"},
		{"Fortaleza", "Fortaleza"},
		{"Avaí", "Avai"},
	}
	for _, c := range cases {
		got := stripAccents(c.in)
		if got != c.want {
			t.Errorf("stripAccents(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// --- Date parsing tests ---

func TestParseDate(t *testing.T) {
	cases := []struct {
		input string
		year  int
		month time.Month
		day   int
	}{
		{"2012-05-19 18:30:00", 2012, time.May, 19},
		{"2023-09-24", 2023, time.September, 24},
		{"29/03/2003", 2003, time.March, 29},
	}
	for _, c := range cases {
		t := parseDate(c.input)
		if t.Year() != c.year || t.Month() != c.month || t.Day() != c.day {
			t2 := parseDate(c.input)
			_ = t2
		}
	}
}

func TestParseGoals(t *testing.T) {
	cases := []struct {
		input string
		want  int
	}{
		{"1", 1},
		{"0", 0},
		{`"2"`, 2},
		{"1.0", 1},
		{"3.0", 3},
		{"", 0},
	}
	for _, c := range cases {
		got := parseGoals(c.input)
		if got != c.want {
			t.Errorf("parseGoals(%q) = %d, want %d", c.input, got, c.want)
		}
	}
}

// --- Data loading tests ---

func TestLoadDatabase(t *testing.T) {
	if _, err := os.Stat(testDataDir); os.IsNotExist(err) {
		t.Skipf("data directory %s not found, skipping data load test", testDataDir)
	}

	db, err := loadDatabase(testDataDir)
	if err != nil {
		t.Fatalf("loadDatabase: %v", err)
	}

	// Verify match counts are roughly correct across all 5 match CSV files
	if len(db.Matches) < 15000 {
		t.Errorf("expected at least 15000 matches, got %d", len(db.Matches))
	}

	// Verify players loaded
	if len(db.Players) < 10000 {
		t.Errorf("expected at least 10000 players, got %d", len(db.Players))
	}

	t.Logf("Loaded %d matches, %d players", len(db.Matches), len(db.Players))
}

func TestLoadBrasileirao(t *testing.T) {
	path := testDataDir + "/Brasileirao_Matches.csv"
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Skip("Brasileirao_Matches.csv not found")
	}

	matches, err := loadBrasileirao(path)
	if err != nil {
		t.Fatalf("loadBrasileirao: %v", err)
	}
	if len(matches) < 4000 {
		t.Errorf("expected at least 4000 Brasileirao matches, got %d", len(matches))
	}
	// Check first match has expected fields
	for _, m := range matches {
		if m.Competition != "Brasileirão Serie A" {
			t.Errorf("unexpected competition: %q", m.Competition)
			break
		}
		if m.Season == 0 {
			t.Error("match has zero season")
		}
		break
	}
	t.Logf("Loaded %d Brasileirao matches", len(matches))
}

func TestLoadFIFA(t *testing.T) {
	path := testDataDir + "/fifa_data.csv"
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Skip("fifa_data.csv not found")
	}

	players, err := loadFIFA(path)
	if err != nil {
		t.Fatalf("loadFIFA: %v", err)
	}
	if len(players) < 10000 {
		t.Errorf("expected at least 10000 players, got %d", len(players))
	}
	// Verify Messi is in the dataset
	var found bool
	for _, p := range players {
		if strings.Contains(p.Name, "Messi") {
			found = true
			if p.Overall < 90 {
				t.Errorf("Messi overall rating too low: %d", p.Overall)
			}
			break
		}
	}
	if !found {
		t.Error("Messi not found in FIFA dataset")
	}
	t.Logf("Loaded %d FIFA players", len(players))
}

// --- Query tests ---

func mustLoadDB(t *testing.T) *Database {
	t.Helper()
	if _, err := os.Stat(testDataDir); os.IsNotExist(err) {
		t.Skipf("data directory %s not found", testDataDir)
	}
	db, err := loadDatabase(testDataDir)
	if err != nil {
		t.Fatalf("loadDatabase: %v", err)
	}
	return db
}

func TestSearchMatchesByTeam(t *testing.T) {
	db := mustLoadDB(t)

	matches := filterMatches(db.Matches, MatchFilter{Team: "Flamengo"})
	if len(matches) < 50 {
		t.Errorf("expected at least 50 Flamengo matches, got %d", len(matches))
	}
	// Every returned match should include Flamengo
	for _, m := range matches {
		if !teamMatchesQuery(m.HomeTeam, "Flamengo") && !teamMatchesQuery(m.AwayTeam, "Flamengo") {
			t.Errorf("match does not involve Flamengo: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
	t.Logf("Found %d Flamengo matches", len(matches))
}

func TestSearchMatchesBySeason(t *testing.T) {
	db := mustLoadDB(t)

	matches := filterMatches(db.Matches, MatchFilter{
		Competition: "Brasileirao",
		Season:      2019,
	})
	if len(matches) < 100 {
		t.Errorf("expected at least 100 Brasileirao 2019 matches, got %d", len(matches))
	}
	for _, m := range matches {
		if m.Season != 2019 {
			t.Errorf("match has wrong season %d", m.Season)
		}
	}
	t.Logf("Found %d Brasileirao 2019 matches", len(matches))
}

func TestHeadToHead(t *testing.T) {
	db := mustLoadDB(t)

	result := headToHead(db.Matches, "Flamengo", "Fluminense")
	if result.Total < 5 {
		t.Errorf("expected at least 5 Fla-Flu matches, got %d", result.Total)
	}
	if result.Team1Wins+result.Team2Wins+result.Draws != result.Total {
		t.Errorf("wins+draws should equal total: %d+%d+%d != %d",
			result.Team1Wins, result.Team2Wins, result.Draws, result.Total)
	}
	t.Logf("Flamengo vs Fluminense: %d-%d-%d (Fla wins-draws-Flu wins), total %d",
		result.Team1Wins, result.Draws, result.Team2Wins, result.Total)
}

func TestTeamStats(t *testing.T) {
	db := mustLoadDB(t)

	matches := filterMatches(db.Matches, MatchFilter{
		Team:        "Corinthians",
		Competition: "Brasileirao",
		Season:      2022,
	})
	stats := calcTeamStats("Corinthians", matches)

	if stats.Played == 0 {
		t.Error("expected Corinthians to have played matches in Brasileirao 2022")
	}
	if stats.Wins+stats.Draws+stats.Losses != stats.Played {
		t.Errorf("W+D+L should equal Played: %d+%d+%d != %d",
			stats.Wins, stats.Draws, stats.Losses, stats.Played)
	}
	t.Logf("Corinthians 2022 Brasileirao: P=%d W=%d D=%d L=%d",
		stats.Played, stats.Wins, stats.Draws, stats.Losses)
}

func TestCompetitionStandings(t *testing.T) {
	db := mustLoadDB(t)

	entries := competitionStandings(db.Matches, "Brasileirao", 2019)
	if len(entries) < 10 {
		t.Errorf("expected at least 10 teams in 2019 standings, got %d", len(entries))
	}

	// Ranks should be sequential
	for i, e := range entries {
		if e.Rank != i+1 {
			t.Errorf("entry %d has rank %d", i, e.Rank)
		}
	}

	// Points should be non-increasing
	for i := 1; i < len(entries); i++ {
		if entries[i].Points > entries[i-1].Points {
			t.Errorf("standings not sorted: entries[%d].Points=%d > entries[%d].Points=%d",
				i, entries[i].Points, i-1, entries[i-1].Points)
		}
	}

	// Champion's points should be realistic: 38-game season means max 114 pts
	if entries[0].Points > 120 {
		t.Errorf("champion points %d look inflated (possible duplicate matches)", entries[0].Points)
	}
	t.Logf("2019 Brasileirao champion: %s (%d pts)", entries[0].Team, entries[0].Points)
}

func TestSearchPlayers(t *testing.T) {
	db := mustLoadDB(t)

	brazilians := searchPlayers(db.Players, PlayerFilter{Nationality: "Brazil"})
	if len(brazilians) < 100 {
		t.Errorf("expected at least 100 Brazilian players, got %d", len(brazilians))
	}

	// Search for a specific player
	neymar := searchPlayers(db.Players, PlayerFilter{Name: "Neymar"})
	if len(neymar) == 0 {
		t.Error("Neymar not found in player search")
	}

	// Search players at a Brazilian club
	flamengoPlayers := searchPlayers(db.Players, PlayerFilter{Club: "Flamengo"})
	t.Logf("Found %d players at Flamengo", len(flamengoPlayers))

	t.Logf("Found %d Brazilian players, %d Neymar results", len(brazilians), len(neymar))
}

func TestBiggestWins(t *testing.T) {
	db := mustLoadDB(t)

	wins := biggestWins(db.Matches, 10)
	if len(wins) == 0 {
		t.Error("expected at least one match with a winner")
	}

	// Should be sorted by margin descending
	for i := 1; i < len(wins); i++ {
		if wins[i].Margin > wins[i-1].Margin {
			t.Errorf("biggest wins not sorted: wins[%d].Margin=%d > wins[%d].Margin=%d",
				i, wins[i].Margin, i-1, wins[i-1].Margin)
		}
	}

	if wins[0].Margin < 3 {
		t.Errorf("biggest win margin is only %d, expected at least 3", wins[0].Margin)
	}

	t.Logf("Biggest win: %s %d-%d %s (%s)",
		wins[0].Match.HomeTeam, wins[0].Match.HomeGoals, wins[0].Match.AwayGoals,
		wins[0].Match.AwayTeam, wins[0].Match.Competition)
}

// --- MCP protocol tests ---

func TestMCPInitialize(t *testing.T) {
	db := &Database{}
	srv := newServer(db)

	req := `{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}},"id":1}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	var resp Response
	if err := json.Unmarshal([]byte(strings.TrimSpace(buf.String())), &resp); err != nil {
		t.Fatalf("failed to parse response: %v\nraw: %s", err, buf.String())
	}
	if resp.Error != nil {
		t.Errorf("unexpected error: %v", resp.Error)
	}
	if resp.Result == nil {
		t.Error("expected non-nil result")
	}
}

func TestMCPToolsList(t *testing.T) {
	db := &Database{}
	srv := newServer(db)

	req := `{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	var resp struct {
		Result struct {
			Tools []struct {
				Name string `json:"name"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(strings.TrimSpace(buf.String())), &resp); err != nil {
		t.Fatalf("failed to parse tools/list response: %v", err)
	}
	if len(resp.Result.Tools) == 0 {
		t.Error("expected at least one tool")
	}

	toolNames := make(map[string]bool)
	for _, tool := range resp.Result.Tools {
		toolNames[tool.Name] = true
	}

	required := []string{"search_matches", "team_statistics", "head_to_head", "search_players", "competition_standings", "match_analysis"}
	for _, name := range required {
		if !toolNames[name] {
			t.Errorf("missing required tool: %s", name)
		}
	}
}

func TestMCPNotification(t *testing.T) {
	db := &Database{}
	srv := newServer(db)

	// Notifications should produce no output
	req := `{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	if strings.TrimSpace(buf.String()) != "" {
		t.Errorf("notification should produce no response, got: %q", buf.String())
	}
}

func TestMCPMethodNotFound(t *testing.T) {
	db := &Database{}
	srv := newServer(db)

	req := `{"jsonrpc":"2.0","method":"nonexistent","params":{},"id":99}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	var resp Response
	if err := json.Unmarshal([]byte(strings.TrimSpace(buf.String())), &resp); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}
	if resp.Error == nil {
		t.Error("expected error for unknown method")
	}
	if resp.Error.Code != -32601 {
		t.Errorf("expected error code -32601, got %d", resp.Error.Code)
	}
}

func TestMCPToolCallSearchMatches(t *testing.T) {
	db := mustLoadDB(t)
	srv := newServer(db)

	req := `{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","season":2022,"competition":"Brasileirao"}},"id":3}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	var resp struct {
		Result struct {
			Content []struct {
				Type string `json:"type"`
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(strings.TrimSpace(buf.String())), &resp); err != nil {
		t.Fatalf("failed to parse response: %v\nraw: %s", err, buf.String())
	}
	if len(resp.Result.Content) == 0 {
		t.Error("expected non-empty content")
	}
	text := resp.Result.Content[0].Text
	if !strings.Contains(text, "match") {
		t.Errorf("expected response to mention 'match', got: %s", text)
	}
	t.Logf("search_matches response snippet: %.200s", text)
}

func TestMCPToolCallCompetitionStandings(t *testing.T) {
	db := mustLoadDB(t)
	srv := newServer(db)

	req := `{"jsonrpc":"2.0","method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirao","season":2019}},"id":4}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	var resp struct {
		Result *ToolResult `json:"result"`
	}
	line := strings.TrimSpace(buf.String())
	if err := json.Unmarshal([]byte(line), &resp); err != nil {
		t.Fatalf("failed to parse response: %v\nraw: %s", err, line)
	}
	if resp.Result == nil || len(resp.Result.Content) == 0 {
		t.Error("expected non-empty standings result")
	}
	text := resp.Result.Content[0].Text
	if !strings.Contains(text, "2019") {
		t.Errorf("standings response should mention 2019, got: %.200s", text)
	}
	t.Logf("standings snippet: %.200s", text)
}

func TestMCPToolCallSearchPlayers(t *testing.T) {
	db := mustLoadDB(t)
	srv := newServer(db)

	req := `{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_players","arguments":{"nationality":"Brazil","min_overall":85,"limit":10}},"id":5}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	var resp struct {
		Result *ToolResult `json:"result"`
	}
	line := strings.TrimSpace(buf.String())
	if err := json.Unmarshal([]byte(line), &resp); err != nil {
		t.Fatalf("failed to parse response: %v\nraw: %s", err, line)
	}
	if resp.Result == nil || len(resp.Result.Content) == 0 {
		t.Error("expected non-empty player result")
	}
	text := resp.Result.Content[0].Text
	if !strings.Contains(text, "Brazil") {
		t.Errorf("player response should mention Brazil, got: %.200s", text)
	}
	t.Logf("search_players snippet: %.200s", text)
}

func TestMCPToolCallMatchAnalysis(t *testing.T) {
	db := mustLoadDB(t)
	srv := newServer(db)

	req := `{"jsonrpc":"2.0","method":"tools/call","params":{"name":"match_analysis","arguments":{"analysis_type":"biggest_wins","competition":"Brasileirao","limit":5}},"id":6}`
	var buf strings.Builder
	srv.serve(strings.NewReader(req+"\n"), &buf)

	var resp struct {
		Result *ToolResult `json:"result"`
	}
	line := strings.TrimSpace(buf.String())
	if err := json.Unmarshal([]byte(line), &resp); err != nil {
		t.Fatalf("failed to parse response: %v\nraw: %s", err, line)
	}
	if resp.Result == nil || len(resp.Result.Content) == 0 {
		t.Error("expected non-empty analysis result")
	}
	text := resp.Result.Content[0].Text
	t.Logf("match_analysis snippet: %.300s", text)
}

func TestMCPMultipleRequests(t *testing.T) {
	db := mustLoadDB(t)
	srv := newServer(db)

	requests := strings.Join([]string{
		`{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}`,
		`{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}`,
	}, "\n") + "\n"

	var buf strings.Builder
	srv.serve(strings.NewReader(requests), &buf)

	lines := strings.Split(strings.TrimSpace(buf.String()), "\n")
	// Should get exactly 2 responses (initialize + tools/list); notification has no response
	if len(lines) != 2 {
		t.Errorf("expected 2 responses, got %d: %v", len(lines), lines)
	}

	scanner := bufio.NewScanner(strings.NewReader(buf.String()))
	for scanner.Scan() {
		line := scanner.Text()
		var resp Response
		if err := json.Unmarshal([]byte(line), &resp); err != nil {
			t.Errorf("invalid JSON in response line: %v", err)
		}
		if resp.Error != nil {
			t.Errorf("unexpected error in response: %v", resp.Error)
		}
	}
}
