package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"sync"
	"testing"
	"time"
)

var (
	dbOnce sync.Once
	testDB *DB
	dbErr  error
)

// givenDataLoaded is the shared "Given the match data is loaded" step.
func givenDataLoaded(t *testing.T) *Server {
	t.Helper()
	dbOnce.Do(func() { testDB, dbErr = LoadDB("data/kaggle") })
	if dbErr != nil {
		t.Fatalf("load: %v", dbErr)
	}
	return NewServer(testDB)
}

func call(t *testing.T, s *Server, tool string, args Args) string {
	t.Helper()
	start := time.Now()
	out, err := s.CallTool(tool, args)
	if err != nil {
		t.Fatalf("%s(%v): %v", tool, args, err)
	}
	if d := time.Since(start); d > 2*time.Second {
		t.Errorf("%s took %v", tool, d)
	}
	return out
}

func mustContain(t *testing.T, out string, subs ...string) {
	t.Helper()
	for _, s := range subs {
		if !strings.Contains(out, s) {
			t.Errorf("output missing %q:\n%s", s, out)
		}
	}
}

func TestNormalizeTeam(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP": "palmeiras", "Palmeiras": "palmeiras", "São Paulo": "sao paulo", "Sao Paulo-SP": "sao paulo",
		"Grêmio": "gremio", "Atlético-MG": "atletico mineiro", "Atletico Mineiro": "atletico mineiro",
		"Atlético - PR": "athletico paranaense", "Athletico-PR": "athletico paranaense", "Athletico Paranaense": "athletico paranaense",
		"Vasco da Gama-RJ": "vasco", "Vasco Da Gama RJ": "vasco", "Botafogo RJ": "botafogo", "Botafogo SP": "botafogo sp",
		"Sport Club Corinthians Paulista": "corinthians", "EC Bahia": "bahia", "Fortaleza FC": "fortaleza",
		"Flamengo - RJ": "flamengo", "Nacional (URU)": "nacional", "Red Bull Bragantino-SP": "bragantino",
	}
	for in, want := range cases {
		if got := NormalizeTeam(in); got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseDate(t *testing.T) {
	for in, want := range map[string]string{"2023-09-24": "2023-09-24", "29/03/2003": "2003-03-29", "2012-05-19 18:30:00": "2012-05-19"} {
		d, _, err := ParseDate(in)
		if err != nil || d.Format("2006-01-02") != want {
			t.Errorf("ParseDate(%q) = %v, %v", in, d, err)
		}
	}
}

// Scenario: All 6 CSV files are loadable and queryable
func TestAllFilesLoaded(t *testing.T) {
	s := givenDataLoaded(t)
	want := map[string]int{"Brasileirao_Matches.csv": 4180, "Brazilian_Cup_Matches.csv": 1337, "Libertadores_Matches.csv": 1255,
		"BR-Football-Dataset.csv": 10296, "novo_campeonato_brasileiro.csv": 6886, "fifa_data.csv": 18207}
	for f, n := range want {
		if testDB.Files[f] != n {
			t.Errorf("%s: loaded %d rows, want %d", f, testDB.Files[f], n)
		}
	}
	srcs := map[string]bool{}
	for _, m := range testDB.Matches {
		srcs[m.Source] = true
	}
	if len(srcs) != 5 {
		t.Errorf("matches from %d sources, want 5", len(srcs))
	}
	mustContain(t, call(t, s, "dataset_info", Args{}), "fifa_data.csv: 18207 rows")
}

// Scenario: Find matches between two teams
func TestFindMatchesBetweenTeams(t *testing.T) {
	s := givenDataLoaded(t)
	ms := testDB.Find(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	if len(ms) < 20 {
		t.Fatalf("expected many Fla-Flu matches, got %d", len(ms))
	}
	for _, m := range ms {
		if m.Date.IsZero() || m.Competition == "" {
			t.Errorf("match missing date/competition: %+v", m)
		}
		pair := map[string]bool{m.HomeKey: true, m.AwayKey: true}
		if !pair["flamengo"] || !pair["fluminense"] {
			t.Errorf("wrong teams: %s vs %s", m.Home, m.Away)
		}
	}
	out := call(t, s, "head_to_head", Args{"team_a": "Flamengo-RJ", "team_b": "Fluminense"})
	mustContain(t, out, "Fla-Flu", "Head-to-head in dataset", "wins", "draws")
}

// Scenario: Get team statistics
func TestTeamStatistics(t *testing.T) {
	s := givenDataLoaded(t)
	out := call(t, s, "team_stats", Args{"team": "Palmeiras", "season": float64(2023)})
	mustContain(t, out, "Wins:", "Draws:", "Losses:", "Goals For:", "Goals Against:", "Win rate:")
	r, _ := testDB.TeamRecord(MatchFilter{Team: "Corinthians", Season: 2022, Competition: "Brasileirão", Venue: "home"})
	if r.Played != 19 || r.W+r.D+r.L != 19 {
		t.Errorf("Corinthians 2022 home record: %+v, want 19 matches", r)
	}
}

// Scenario: Standings calculated from matches; "Who won the 2019 Brasileirão?"
func TestStandings2019(t *testing.T) {
	s := givenDataLoaded(t)
	table := testDB.Standings(2019, "")
	if len(table) != 20 {
		t.Fatalf("2019 table has %d teams, want 20", len(table))
	}
	top := table[0]
	if top.Team != "flamengo" || top.Points() != 90 || top.W != 28 || top.D != 6 || top.L != 4 {
		t.Errorf("2019 champion = %+v, want Flamengo 90pts 28-6-4", top)
	}
	for _, r := range table {
		if r.Played != 38 {
			t.Errorf("%s played %d, want 38 (dedup across sources)", r.Team, r.Played)
		}
	}
	out := call(t, s, "standings", Args{"season": float64(2019)})
	mustContain(t, out, "1. Flamengo - 90 pts (28W, 6D, 4L)", "Champion", "Relegated")
}

// Scenario: Copa do Brasil finals and Libertadores stages
func TestCupFinals(t *testing.T) {
	s := givenDataLoaded(t)
	ms := testDB.Find(MatchFilter{Competition: "Copa do Brasil", Stage: "final"})
	if len(ms) == 0 {
		t.Fatal("no Copa do Brasil finals")
	}
	for _, m := range ms {
		if m.Competition != CompCopaBrasil {
			t.Errorf("unexpected competition %s", m.Competition)
		}
	}
	out := call(t, s, "search_matches", Args{"competition": "Libertadores", "season": float64(2018), "stage": "final"})
	mustContain(t, out, "Libertadores 2018, final")
}

func TestMatchesBySeasonAndDateRange(t *testing.T) {
	s := givenDataLoaded(t)
	out := call(t, s, "search_matches", Args{"team": "Palmeiras", "season": float64(2023)})
	mustContain(t, out, "Palmeiras", "2023")
	from, _, _ := ParseDate("01/06/2019")
	to, _, _ := ParseDate("2019-06-30")
	for _, m := range testDB.Find(MatchFilter{Team: "Santos", From: from, To: to}) {
		if m.Date.Before(from) || m.Date.After(to.Add(24*time.Hour)) {
			t.Errorf("match out of range: %v", m.Date)
		}
	}
	// home venue filter
	for _, m := range testDB.Find(MatchFilter{Team: "Grêmio", Venue: "home", Season: 2018}) {
		if m.HomeKey != "gremio" {
			t.Errorf("home filter returned away match %s", testDB.FormatMatch(m))
		}
	}
}

func TestLastMeeting(t *testing.T) {
	givenDataLoaded(t)
	ms := testDB.Find(MatchFilter{Team: "Flamengo", Opponent: "Corinthians"})
	if len(ms) < 2 || ms[0].Date.Before(ms[1].Date) {
		t.Fatal("matches should be sorted most recent first")
	}
}

func TestTeamNameVariationsGiveSameResults(t *testing.T) {
	givenDataLoaded(t)
	a := len(testDB.Find(MatchFilter{Team: "São Paulo"}))
	for _, v := range []string{"Sao Paulo", "Sao Paulo-SP", "São Paulo - SP", "sao paulo"} {
		if b := len(testDB.Find(MatchFilter{Team: v})); b != a {
			t.Errorf("%q gives %d matches, São Paulo gives %d", v, b, a)
		}
	}
}

func TestStatisticalAnalysis(t *testing.T) {
	s := givenDataLoaded(t)
	out := call(t, s, "competition_stats", Args{"competition": "Brasileirão"})
	mustContain(t, out, "Average goals per match: 2.", "Home win rate:", "Biggest victories:")
	out = call(t, s, "team_rankings", Args{"metric": "away_record", "competition": "Brasileirão"})
	mustContain(t, out, "1. ")
	out = call(t, s, "team_rankings", Args{"metric": "goals_scored", "competition": "Serie A", "season": float64(2019)})
	mustContain(t, out, "1. Flamengo")
	out = call(t, s, "compare_seasons", Args{"seasons": "2018,2019"})
	mustContain(t, out, "2018:", "2019:", "Champion: Palmeiras", "Champion: Flamengo")
}

func TestPlayerQueries(t *testing.T) {
	s := givenDataLoaded(t)
	br := testDB.FindPlayers(PlayerFilter{Nationality: "Brazilian"})
	if len(br) < 500 {
		t.Errorf("only %d Brazilian players", len(br))
	}
	if br[0].Name != "Neymar Jr" {
		t.Errorf("top Brazilian = %s, want Neymar Jr", br[0].Name)
	}
	mustContain(t, call(t, s, "player_details", Args{"name": "Neymar"}), "Neymar Jr", "Paris Saint-Germain", "Dribbling")
	// Gabriel Barbosa is not in FIFA 19; we should get a clear answer with similar names.
	mustContain(t, call(t, s, "player_details", Args{"name": "Gabriel Barbosa"}), "No player named", "Similar names", "Gabriel Jesus")
	mustContain(t, call(t, s, "search_players", Args{"club": "Flamengo"}), "Found 0 players", "not licensed")
	gremio := testDB.FindPlayers(PlayerFilter{Club: "Gremio"})
	if len(gremio) == 0 {
		t.Error("no players at Grêmio (accent-insensitive club search)")
	}
	for _, p := range testDB.FindPlayers(PlayerFilter{Club: "Santos", Position: "forward"}) {
		if !positionMatches("forward", p.Position) {
			t.Errorf("%s is %s", p.Name, p.Position)
		}
	}
	mustContain(t, call(t, s, "brazilian_clubs_players", Args{"brazilian_only": true}), "Brazilian players at Brazilian clubs", "avg rating")
}

// Cross-file query: match record + FIFA players for one club.
func TestCrossFileTeamProfile(t *testing.T) {
	s := givenDataLoaded(t)
	out := call(t, s, "team_profile", Args{"team": "Cruzeiro"})
	mustContain(t, out, "Cruzeiro record", "Competitions for Cruzeiro", "FIFA players at Cruzeiro")
}

func TestDerbiesAndCompetitions(t *testing.T) {
	s := givenDataLoaded(t)
	mustContain(t, call(t, s, "derbies", Args{"season": float64(2023)}), "Fla-Flu", "Grenal")
	mustContain(t, call(t, s, "team_competitions", Args{"team": "Palmeiras"}), "Brasileirão", "Copa do Brasil", "Libertadores")
}

// At least 20 sample questions are answerable without error, fast.
func TestTwentySampleQuestions(t *testing.T) {
	s := givenDataLoaded(t)
	qs := []struct {
		tool string
		args Args
	}{
		{"head_to_head", Args{"team_a": "Flamengo", "team_b": "Fluminense"}},
		{"search_matches", Args{"team": "Palmeiras", "season": 2023.0}},
		{"search_matches", Args{"competition": "Copa do Brasil", "stage": "final"}},
		{"team_stats", Args{"team": "Corinthians", "season": 2022.0, "venue": "home"}},
		{"team_rankings", Args{"metric": "goals_scored", "season": 2023.0, "competition": "Brasileirão"}},
		{"head_to_head", Args{"team_a": "Palmeiras", "team_b": "Santos"}},
		{"search_players", Args{"nationality": "Brazil"}},
		{"search_players", Args{"club": "Cruzeiro"}},
		{"search_players", Args{"club": "Grêmio", "position": "forward"}},
		{"standings", Args{"season": 2019.0}},
		{"search_matches", Args{"competition": "Libertadores", "season": 2018.0, "stage": "semifinals"}},
		{"standings", Args{"season": 2020.0}},
		{"competition_stats", Args{"competition": "Brasileirão"}},
		{"team_rankings", Args{"metric": "away_record"}},
		{"competition_stats", Args{}},
		{"search_matches", Args{"team": "Flamengo", "opponent": "Corinthians", "limit": 1.0}},
		{"player_details", Args{"name": "Gabriel Barbosa"}},
		{"derbies", Args{"season": 2023.0}},
		{"team_competitions", Args{"team": "Palmeiras"}},
		{"team_rankings", Args{"metric": "home_record"}},
		{"search_players", Args{"nationality": "Brazil", "limit": 10.0}},
		{"compare_seasons", Args{"seasons": "2018,2019"}},
		{"team_profile", Args{"team": "Grêmio"}},
		{"search_matches", Args{"team": "Santos", "date_from": "2015-01-01", "date_to": "31/12/2015"}},
	}
	for _, q := range qs {
		if out := call(t, s, q.tool, q.args); len(out) < 20 {
			t.Errorf("%s: suspiciously short output %q", q.tool, out)
		}
	}
}

func TestErrorsReported(t *testing.T) {
	s := givenDataLoaded(t)
	if _, err := s.CallTool("team_stats", Args{"team": "Nonexistent United"}); err == nil {
		t.Error("expected unknown team error")
	}
	if _, err := s.CallTool("nope", Args{}); err == nil {
		t.Error("expected unknown tool error")
	}
}

// MCP protocol round trip over the stdio transport.
func TestMCPProtocol(t *testing.T) {
	s := givenDataLoaded(t)
	in := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_stats","arguments":{"team":"Nowhere FC"}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"bogus"}`,
	}, "\n")
	var out bytes.Buffer
	if err := s.Serve(strings.NewReader(in), &out); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 5 {
		t.Fatalf("got %d responses, want 5 (notification has none):\n%s", len(lines), out.String())
	}
	var resps []map[string]any
	for _, l := range lines {
		var r map[string]any
		if err := json.Unmarshal([]byte(l), &r); err != nil {
			t.Fatal(err)
		}
		resps = append(resps, r)
	}
	if resps[0]["result"].(map[string]any)["protocolVersion"] != protocolVersion {
		t.Error("bad initialize result")
	}
	if n := len(resps[1]["result"].(map[string]any)["tools"].([]any)); n < 10 {
		t.Errorf("only %d tools listed", n)
	}
	res := resps[2]["result"].(map[string]any)
	text := res["content"].([]any)[0].(map[string]any)["text"].(string)
	mustContain(t, text, "Flamengo - 90 pts")
	if resps[3]["result"].(map[string]any)["isError"] != true {
		t.Error("unknown team should be isError")
	}
	if resps[4]["error"] == nil {
		t.Error("unknown method should error")
	}
}
