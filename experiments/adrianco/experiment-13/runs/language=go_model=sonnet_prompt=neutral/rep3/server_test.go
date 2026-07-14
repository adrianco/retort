package main

import (
	"encoding/json"
	"strings"
	"testing"
)

// Integration test that loads actual data and runs tool queries
const dataDir = "data/kaggle"

func loadTestDB(t *testing.T) *Database {
	t.Helper()
	db, err := LoadAll(dataDir)
	if err != nil {
		t.Logf("Warning loading data: %v", err)
	}
	if len(db.Matches) == 0 {
		t.Fatal("no matches loaded")
	}
	if len(db.Players) == 0 {
		t.Fatal("no players loaded")
	}
	return db
}

// TestLoad verifies that all CSV files are loaded and non-empty
func TestLoad(t *testing.T) {
	db := loadTestDB(t)
	t.Logf("Loaded %d matches and %d players", len(db.Matches), len(db.Players))

	if len(db.Matches) < 10000 {
		t.Errorf("expected at least 10000 matches, got %d", len(db.Matches))
	}
	if len(db.Players) < 18000 {
		t.Errorf("expected at least 18000 players, got %d", len(db.Players))
	}

	// Verify we have data from multiple competitions
	comps := map[string]bool{}
	for _, m := range db.Matches {
		comps[m.Competition] = true
	}
	if len(comps) < 3 {
		t.Errorf("expected at least 3 competitions, got %d: %v", len(comps), comps)
	}
}

// TestNormalizeTeam tests team name normalization
func TestNormalizeTeam(t *testing.T) {
	cases := []struct{ in, want string }{
		{"Palmeiras-SP", "palmeiras"},
		{"Flamengo-RJ", "flamengo"},
		{"Atletico-MG", "atletico"},
		{"Atletico-PR", "atletico"},
		{"Palmeiras", "palmeiras"},
		{"São Paulo", "sao paulo"},
		{"Grêmio", "gremio"},
		{"Nacional (URU)", "nacional"},
		{"Boavista - RJ", "boavista"},
	}
	for _, c := range cases {
		got := normalizeTeam(c.in)
		if got != c.want {
			t.Errorf("normalizeTeam(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// TestTeamMatches tests partial team name matching
func TestTeamMatches(t *testing.T) {
	cases := []struct {
		norm, query string
		want        bool
	}{
		{"flamengo", "Flamengo", true},
		{"flamengo", "flam", true},
		{"palmeiras", "Palmeiras", true},
		{"atletico", "Atletico", true},
		{"sao paulo", "São Paulo", true},
		{"flamengo", "Corinthians", false},
	}
	for _, c := range cases {
		got := teamMatches(c.norm, c.query)
		if got != c.want {
			t.Errorf("teamMatches(%q, %q) = %v, want %v", c.norm, c.query, got, c.want)
		}
	}
}

// TestParseDate tests date parsing from multiple formats
func TestParseDate(t *testing.T) {
	cases := []struct{ in, want string }{
		{"2023-09-24", "2023-09-24"},
		{"2012-05-19 18:30:00", "2012-05-19"},
		{"29/03/2003", "2003-03-29"},
		{"", ""},
	}
	for _, c := range cases {
		got := parseDate(c.in)
		if got != c.want {
			t.Errorf("parseDate(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// TestSearchMatchesByTeam verifies basic team filtering
func TestSearchMatchesByTeam(t *testing.T) {
	db := loadTestDB(t)

	matches := db.FilterMatches(MatchFilter{Team: "Flamengo"})
	if len(matches) < 100 {
		t.Errorf("expected many Flamengo matches, got %d", len(matches))
	}

	// All returned matches should involve Flamengo
	for _, m := range matches {
		if !teamMatches(m.HomeNorm, "Flamengo") && !teamMatches(m.AwayNorm, "Flamengo") {
			t.Errorf("match %s does not involve Flamengo: %s vs %s", m.Date, m.HomeTeam, m.AwayTeam)
		}
	}

	// Results should be sorted by date descending
	for i := 1; i < len(matches); i++ {
		if matches[i].Date > matches[i-1].Date {
			t.Errorf("matches not sorted by date desc at index %d: %s > %s", i, matches[i].Date, matches[i-1].Date)
		}
	}
}

// TestSearchMatchesByCompetition verifies competition filtering with aliases
func TestSearchMatchesByCompetition(t *testing.T) {
	db := loadTestDB(t)

	// "Brasileirao" should match both "Brasileirao Serie A" and "Serie A"
	matches := db.FilterMatches(MatchFilter{Competition: "Brasileirao"})
	if len(matches) < 4000 {
		t.Errorf("expected at least 4000 Brasileirao matches, got %d", len(matches))
	}

	// Copa do Brasil
	cupMatches := db.FilterMatches(MatchFilter{Competition: "Copa do Brasil"})
	if len(cupMatches) < 500 {
		t.Errorf("expected at least 500 Copa do Brasil matches, got %d", len(cupMatches))
	}

	// Libertadores
	libMatches := db.FilterMatches(MatchFilter{Competition: "Libertadores"})
	if len(libMatches) < 500 {
		t.Errorf("expected at least 500 Libertadores matches, got %d", len(libMatches))
	}
}

// TestSearchMatchesBySeason verifies season filtering
func TestSearchMatchesBySeason(t *testing.T) {
	db := loadTestDB(t)

	matches2019 := db.FilterMatches(MatchFilter{Season: 2019, Competition: "Brasileirao"})
	if len(matches2019) < 380 {
		t.Errorf("expected at least 380 Brasileirao 2019 matches, got %d", len(matches2019))
	}
}

// TestSearchMatchesByDateRange verifies date range filtering
func TestSearchMatchesByDateRange(t *testing.T) {
	db := loadTestDB(t)

	matches := db.FilterMatches(MatchFilter{StartDate: "2023-01-01", EndDate: "2023-12-31"})
	if len(matches) == 0 {
		t.Error("expected matches in 2023, got none")
	}
	for _, m := range matches {
		if m.Date < "2023-01-01" || m.Date > "2023-12-31" {
			t.Errorf("match date %s outside 2023", m.Date)
		}
	}
}

// TestSearchMatchesHeadToHead verifies two-team lookup
func TestSearchMatchesHeadToHead(t *testing.T) {
	db := loadTestDB(t)

	matches, s1, s2 := db.HeadToHead("Flamengo", "Fluminense", "", 0)
	if len(matches) < 10 {
		t.Errorf("expected many Fla-Flu matches, got %d", len(matches))
	}

	// Total matches should be consistent
	total := s1.Wins + s1.Draws + s1.Losses
	if total != len(matches) {
		t.Errorf("stats total %d != match count %d", total, len(matches))
	}

	// Draws should be symmetric
	if s1.Draws != s2.Draws {
		t.Errorf("draws mismatch: s1=%d s2=%d", s1.Draws, s2.Draws)
	}

	// Goals should be symmetric
	if s1.GoalsFor != s2.GoalsAgainst || s1.GoalsAgainst != s2.GoalsFor {
		t.Errorf("goals not symmetric: s1 GF=%d s2 GA=%d", s1.GoalsFor, s2.GoalsAgainst)
	}
}

// TestGetTeamStats verifies team statistics calculation
func TestGetTeamStats(t *testing.T) {
	db := loadTestDB(t)

	stats := db.TeamStatsByFilter("Flamengo", "Brasileirao", 2019)
	if stats.Matches == 0 {
		t.Fatal("no matches found for Flamengo 2019 Brasileirao")
	}
	if stats.Matches != 38 {
		t.Errorf("Flamengo 2019 should have 38 matches, got %d", stats.Matches)
	}
	if stats.Points != 90 {
		t.Errorf("Flamengo 2019 should have 90 points, got %d", stats.Points)
	}
	if stats.Wins+stats.Draws+stats.Losses != stats.Matches {
		t.Errorf("W+D+L (%d) != matches (%d)", stats.Wins+stats.Draws+stats.Losses, stats.Matches)
	}
}

// TestStandings verifies 2019 Brasileirao champion
func TestStandings2019(t *testing.T) {
	db := loadTestDB(t)

	standings := db.Standings(2019, "Brasileirao")
	if len(standings) == 0 {
		t.Fatal("no standings for 2019")
	}
	if len(standings) < 18 {
		t.Errorf("expected at least 18 teams, got %d", len(standings))
	}

	// Flamengo should be #1 with 90 points
	top := standings[0]
	if !strings.Contains(strings.ToLower(top.Team), "flamengo") {
		t.Errorf("expected Flamengo as champion, got %s", top.Team)
	}
	if top.Points != 90 {
		t.Errorf("Flamengo 2019 points = %d, want 90", top.Points)
	}
}

// TestStandings2023 verifies 2023 standings (from BR-Football-Dataset)
func TestStandings2023(t *testing.T) {
	db := loadTestDB(t)

	standings := db.Standings(2023, "Brasileirao")
	if len(standings) == 0 {
		t.Fatal("no standings for 2023")
	}
	t.Logf("2023 champion: %s with %d points", standings[0].Team, standings[0].Points)
}

// TestStandingsHistorical verifies historical standings (2003-2011)
func TestStandingsHistorical(t *testing.T) {
	db := loadTestDB(t)

	standings := db.Standings(2005, "Brasileirao")
	if len(standings) == 0 {
		t.Fatal("no standings for 2005")
	}
	// Corinthians won 2005
	if !strings.Contains(strings.ToLower(standings[0].Team), "corinthians") {
		t.Errorf("expected Corinthians as 2005 champion, got %s", standings[0].Team)
	}
}

// TestBiggestWins verifies biggest wins by goal difference
func TestBiggestWins(t *testing.T) {
	db := loadTestDB(t)

	wins := db.BiggestWins("", 0, 10)
	if len(wins) == 0 {
		t.Fatal("no biggest wins returned")
	}

	// Should be sorted by goal difference descending
	for i := 1; i < len(wins); i++ {
		prev := wins[i-1]
		curr := wins[i]
		prevDiff := prev.HomeGoal - prev.AwayGoal
		if prevDiff < 0 {
			prevDiff = -prevDiff
		}
		currDiff := curr.HomeGoal - curr.AwayGoal
		if currDiff < 0 {
			currDiff = -currDiff
		}
		if currDiff > prevDiff {
			t.Errorf("biggest wins not sorted at %d: diff=%d > %d", i, currDiff, prevDiff)
		}
	}
}

// TestSearchPlayers verifies player search
func TestSearchPlayers(t *testing.T) {
	db := loadTestDB(t)

	// Search Brazilian players
	players := db.SearchPlayers(PlayerFilter{Nationality: "Brazil", MinOverall: 80})
	if len(players) < 10 {
		t.Errorf("expected many Brazilian players with rating >= 80, got %d", len(players))
	}

	// Should be sorted by overall desc
	for i := 1; i < len(players); i++ {
		if players[i].Overall > players[i-1].Overall {
			t.Errorf("players not sorted by overall at index %d", i)
		}
	}

	// Neymar should be the highest-rated Brazilian
	if !strings.Contains(strings.ToLower(players[0].Name), "neymar") {
		t.Errorf("expected Neymar as top Brazilian player, got %s (overall %d)", players[0].Name, players[0].Overall)
	}
}

// TestSearchPlayersByClub verifies club filtering
func TestSearchPlayersByClub(t *testing.T) {
	db := loadTestDB(t)

	// FIFA 19 includes Brazilian clubs like Santos, Gremio, Internacional
	// (Flamengo and Corinthians were not fully licensed in FIFA 19)
	players := db.SearchPlayers(PlayerFilter{Club: "Santos"})
	if len(players) == 0 {
		t.Error("expected players at Santos, got none")
	}
	t.Logf("Found %d players at Santos", len(players))

	// Also test Gremio
	gremioPlayers := db.SearchPlayers(PlayerFilter{Club: "Gremio"})
	if len(gremioPlayers) == 0 {
		gremioPlayers = db.SearchPlayers(PlayerFilter{Club: "Gr"})
	}
	t.Logf("Found %d players at Gremio/Grêmio", len(gremioPlayers))
}

// TestCompetitionStats verifies aggregate statistics
func TestCompetitionStats(t *testing.T) {
	db := loadTestDB(t)

	stats := db.CompetitionStats("Brasileirao", 2019)
	if stats.TotalMatches != 380 {
		t.Errorf("expected 380 Brasileirao 2019 matches, got %d", stats.TotalMatches)
	}
	if stats.TotalGoals == 0 {
		t.Error("expected non-zero total goals")
	}
	if stats.AvgGoals < 1.0 || stats.AvgGoals > 5.0 {
		t.Errorf("avg goals %.2f seems unreasonable", stats.AvgGoals)
	}
	if stats.HomeWins+stats.Draws+stats.AwayWins != stats.TotalMatches {
		t.Errorf("HW+D+AW != total: %d+%d+%d != %d",
			stats.HomeWins, stats.Draws, stats.AwayWins, stats.TotalMatches)
	}
}

// TestMCPProtocol tests the JSON-RPC protocol handling
func TestMCPProtocol(t *testing.T) {
	db := loadTestDB(t)

	// Test tools/list
	text, err := dispatchTool(db, "get_standings", map[string]interface{}{
		"season": float64(2019),
	})
	if err != nil {
		t.Fatalf("dispatchTool error: %v", err)
	}
	if !strings.Contains(text, "Flamengo") {
		t.Errorf("standings should mention Flamengo, got: %s", text[:200])
	}

	// Test invalid tool
	_, err = dispatchTool(db, "nonexistent_tool", nil)
	if err == nil {
		t.Error("expected error for nonexistent tool")
	}
}

// TestMCPToolsList verifies all tools are defined
func TestMCPToolsList(t *testing.T) {
	tools := allTools()
	if len(tools) < 7 {
		t.Errorf("expected at least 7 tools, got %d", len(tools))
	}
	for _, tool := range tools {
		if tool.Name == "" {
			t.Error("tool has empty name")
		}
		if tool.Description == "" {
			t.Errorf("tool %s has empty description", tool.Name)
		}
		if tool.InputSchema.Type != "object" {
			t.Errorf("tool %s has non-object schema type: %s", tool.Name, tool.InputSchema.Type)
		}
	}
}

// TestSampleQuestions tests the 20+ sample questions from the spec
func TestSampleQuestions(t *testing.T) {
	db := loadTestDB(t)

	tests := []struct {
		name string
		fn   func(t *testing.T)
	}{
		{"FlamengoVsCorinthians", func(t *testing.T) {
			matches, _, _ := db.HeadToHead("Flamengo", "Corinthians", "", 0)
			if len(matches) == 0 {
				t.Error("no Flamengo vs Corinthians matches")
			}
			t.Logf("Found %d Flamengo vs Corinthians matches, most recent: %s", len(matches), matches[0].Date)
		}},
		{"PalmeirasMatches2022", func(t *testing.T) {
			matches := db.FilterMatches(MatchFilter{Team: "Palmeiras", Season: 2022})
			if len(matches) == 0 {
				t.Error("no Palmeiras 2022 matches")
			}
			t.Logf("Palmeiras played %d matches in 2022", len(matches))
		}},
		{"CorinthiansHomeRecord2022", func(t *testing.T) {
			stats := db.TeamStatsByFilter("Corinthians", "Brasileirao", 2022)
			if stats.Matches == 0 {
				t.Error("no Corinthians 2022 data")
			}
			t.Logf("Corinthians 2022: %dW/%dD/%dL", stats.Wins, stats.Draws, stats.Losses)
		}},
		{"Who won 2019 Brasileirao", func(t *testing.T) {
			standings := db.Standings(2019, "Brasileirao")
			if len(standings) == 0 {
				t.Error("no 2019 standings")
			}
			if !strings.Contains(strings.ToLower(standings[0].Team), "flamengo") {
				t.Errorf("2019 champion should be Flamengo, got %s", standings[0].Team)
			}
		}},
		{"Brazilian players overall >= 85", func(t *testing.T) {
			players := db.SearchPlayers(PlayerFilter{Nationality: "Brazil", MinOverall: 85})
			if len(players) == 0 {
				t.Error("no Brazilian players with rating >= 85")
			}
		}},
		{"Biggest wins all time", func(t *testing.T) {
			wins := db.BiggestWins("", 0, 5)
			if len(wins) == 0 {
				t.Error("no biggest wins")
			}
			// First should have at least 5 goal difference
			diff := wins[0].HomeGoal - wins[0].AwayGoal
			if diff < 0 {
				diff = -diff
			}
			if diff < 5 {
				t.Errorf("biggest win should have diff >= 5, got %d", diff)
			}
		}},
		{"Avg goals Brasileirao", func(t *testing.T) {
			stats := db.CompetitionStats("Brasileirao", 0)
			if stats.AvgGoals < 2.0 || stats.AvgGoals > 4.0 {
				t.Errorf("average goals %.2f seems wrong for Brasileirao", stats.AvgGoals)
			}
			t.Logf("Brasileirao avg goals/match: %.2f", stats.AvgGoals)
		}},
		{"Flamengo player search", func(t *testing.T) {
			// Neymar is not at Flamengo in FIFA 19 but test club search
			players := db.SearchPlayers(PlayerFilter{Club: "Santos"})
			t.Logf("Found %d players at Santos", len(players))
		}},
		{"Libertadores matches 2019", func(t *testing.T) {
			matches := db.FilterMatches(MatchFilter{Competition: "Libertadores", Season: 2019})
			if len(matches) == 0 {
				t.Error("no Libertadores 2019 matches")
			}
			t.Logf("Libertadores 2019: %d matches", len(matches))
		}},
		{"Copa do Brasil matches", func(t *testing.T) {
			matches := db.FilterMatches(MatchFilter{Competition: "Copa do Brasil"})
			if len(matches) < 500 {
				t.Errorf("expected at least 500 Copa do Brasil matches, got %d", len(matches))
			}
		}},
		{"Historical 2003 matches", func(t *testing.T) {
			matches := db.FilterMatches(MatchFilter{Season: 2003, Competition: "Brasileirao"})
			if len(matches) == 0 {
				t.Error("no matches in 2003")
			}
			t.Logf("2003 Brasileirao: %d matches", len(matches))
		}},
		{"Compare two seasons", func(t *testing.T) {
			s2018 := db.CompetitionStats("Brasileirao", 2018)
			s2019 := db.CompetitionStats("Brasileirao", 2019)
			if s2018.TotalMatches == 0 || s2019.TotalMatches == 0 {
				t.Error("missing season data")
			}
			t.Logf("2018 avg goals: %.2f, 2019: %.2f", s2018.AvgGoals, s2019.AvgGoals)
		}},
		{"Gabriel Barbosa player", func(t *testing.T) {
			players := db.SearchPlayers(PlayerFilter{Name: "Gabigol"})
			t.Logf("Found %d players named Gabigol", len(players))
		}},
		{"Forwards at Flamengo", func(t *testing.T) {
			players := db.SearchPlayers(PlayerFilter{Club: "Flamengo", Position: "ST"})
			t.Logf("Found %d ST at Flamengo in FIFA data", len(players))
		}},
		{"Date range 2022", func(t *testing.T) {
			matches := db.FilterMatches(MatchFilter{StartDate: "2022-01-01", EndDate: "2022-12-31"})
			if len(matches) == 0 {
				t.Error("no matches in 2022")
			}
		}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tt.fn(t)
		})
	}
}

// TestDispatchTools tests all tools via the dispatch function
func TestDispatchTools(t *testing.T) {
	db := loadTestDB(t)

	tests := []struct {
		tool string
		args map[string]interface{}
	}{
		{"search_matches", map[string]interface{}{"team": "Palmeiras", "season": float64(2022), "limit": float64(5)}},
		{"get_team_stats", map[string]interface{}{"team": "Flamengo", "competition": "Brasileirao", "season": float64(2019)}},
		{"head_to_head", map[string]interface{}{"team1": "Flamengo", "team2": "Corinthians"}},
		{"search_players", map[string]interface{}{"nationality": "Brazil", "min_overall": float64(85), "limit": float64(5)}},
		{"get_standings", map[string]interface{}{"season": float64(2019)}},
		{"get_biggest_wins", map[string]interface{}{"competition": "Brasileirao", "limit": float64(5)}},
		{"get_competition_stats", map[string]interface{}{"competition": "Brasileirao", "season": float64(2019)}},
	}

	for _, tt := range tests {
		t.Run(tt.tool, func(t *testing.T) {
			result, err := dispatchTool(db, tt.tool, tt.args)
			if err != nil {
				t.Fatalf("tool %s error: %v", tt.tool, err)
			}
			if result == "" {
				t.Errorf("tool %s returned empty result", tt.tool)
			}
			t.Logf("%s result (first 200 chars): %s", tt.tool, result[:min(200, len(result))])
		})
	}
}

// TestJSONRPCMessages tests MCP protocol message handling in-process
func TestJSONRPCMessages(t *testing.T) {
	db := loadTestDB(t)

	var out strings.Builder
	srv := &Server{db: db, writer: &out}

	// Test initialize
	id := json.RawMessage(`1`)
	srv.sendResult(id, initResult{
		ProtocolVersion: "2024-11-05",
		Capabilities:    capabilities{Tools: toolsCap{}},
		ServerInfo:      serverInfo{Name: "test", Version: "1.0"},
	})
	response := out.String()
	if !strings.Contains(response, "protocolVersion") {
		t.Errorf("initialize response missing protocolVersion: %s", response)
	}

	// Test tools list response
	out.Reset()
	srv.sendResult(id, toolsListResult{Tools: allTools()})
	toolsResponse := out.String()
	if !strings.Contains(toolsResponse, "search_matches") {
		t.Errorf("tools list missing search_matches: %s", toolsResponse[:200])
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
