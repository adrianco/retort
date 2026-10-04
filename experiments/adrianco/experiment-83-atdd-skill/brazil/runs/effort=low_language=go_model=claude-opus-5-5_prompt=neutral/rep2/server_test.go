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
	testDB     *DB
	testDBOnce sync.Once
)

func loadTestDB(t *testing.T) *DB {
	t.Helper()
	testDBOnce.Do(func() {
		db, err := LoadDB("data/kaggle")
		if err != nil {
			t.Fatalf("LoadDB: %v", err)
		}
		testDB = db
	})
	if testDB == nil {
		t.Fatal("database not loaded")
	}
	return testDB
}

func TestNormalization(t *testing.T) {
	cases := []struct {
		name, query string
		want        bool
	}{
		{"Palmeiras-SP", "Palmeiras", true},
		{"Flamengo - RJ", "flamengo", true},
		{"São Paulo - SP", "Sao Paulo", true},
		{"Sao Paulo-SP", "São Paulo", true},
		{"Grêmio - RS", "Gremio", true},
		{"Sport Club Corinthians Paulista", "Corinthians", true},
		{"Atletico-MG", "Atlético Mineiro", true},
		{"Atletico Mineiro", "Atletico-MG", true},
		{"Athletico-PR", "Atletico Paranaense", true},
		{"Atletico-PR", "Atletico Mineiro", false},
		{"Fluminense-RJ", "Flamengo", false},
		{"Red Bull Bragantino-SP", "Bragantino", true},
	}
	for _, c := range cases {
		if got := TeamMatches(c.name, c.query); got != c.want {
			t.Errorf("TeamMatches(%q,%q)=%v want %v (key %q, query %v)", c.name, c.query, got, c.want, TeamKey(c.name), TeamTokens(c.query))
		}
	}
	if DisplayName("Palmeiras-SP") != "Palmeiras" || DisplayName("América - MG") != "América-MG" {
		t.Errorf("DisplayName wrong: %q %q", DisplayName("Palmeiras-SP"), DisplayName("América - MG"))
	}
}

func TestParseDate(t *testing.T) {
	want := time.Date(2003, 3, 29, 0, 0, 0, 0, time.UTC)
	for _, s := range []string{"2003-03-29", "29/03/2003", "2003-03-29 00:00:00"} {
		d, err := ParseDate(s)
		if err != nil || !d.Equal(want) {
			t.Errorf("ParseDate(%q)=%v,%v", s, d, err)
		}
	}
	if _, err := ParseDate("garbage"); err == nil {
		t.Error("expected error")
	}
}

func TestNormalizeCompetition(t *testing.T) {
	for in, want := range map[string]string{"Brasileirão": CompSerieA, "serie a": CompSerieA, "Copa do Brasil": CompCopaDoBrasil,
		"libertadores": CompLibertadores, "Serie B": CompSerieB} {
		if got := NormalizeCompetition(in); got != want {
			t.Errorf("%q -> %q want %q", in, got, want)
		}
	}
}

func TestAllFilesLoaded(t *testing.T) {
	db := loadTestDB(t)
	min := map[string]int{"Brasileirao_Matches.csv": 4000, "Brazilian_Cup_Matches.csv": 1300, "Libertadores_Matches.csv": 1200,
		"BR-Football-Dataset.csv": 10000, "novo_campeonato_brasileiro.csv": 6800, "fifa_data.csv": 18000}
	for f, n := range min {
		if db.Sources[f] < n {
			t.Errorf("%s loaded %d rows, want >= %d", f, db.Sources[f], n)
		}
	}
	// every source queryable
	seen := map[string]bool{}
	for _, m := range db.Matches {
		seen[m.Source] = true
	}
	if len(seen) != 5 {
		t.Errorf("match sources = %v", seen)
	}
}

func TestDeduplicatedSeason(t *testing.T) {
	db := loadTestDB(t)
	// 2018 Serie A is in three files; de-duplication should yield 380 matches.
	if n := len(db.FindMatches(MatchFilter{Competition: "Brasileirão", Season: 2018})); n != 380 {
		t.Errorf("2018 Serie A matches = %d, want 380", n)
	}
}

func TestStandings(t *testing.T) {
	db := loadTestDB(t)
	tab, _ := db.Standings(2019, "")
	if len(tab) != 20 || tab[0].Team != "Flamengo" || tab[0].Points != 90 {
		t.Fatalf("2019 standings top = %+v (n=%d)", tab[0], len(tab))
	}
	tab, _ = db.Standings(2010, "")
	if tab[0].Team != "Fluminense" {
		t.Errorf("2010 champion = %s, want Fluminense", tab[0].Team)
	}
}

func TestTeamRecordConsistency(t *testing.T) {
	db := loadTestDB(t)
	home, _ := db.TeamRecord("Corinthians", 2022, "Brasileirão", "home")
	away, _ := db.TeamRecord("Corinthians", 2022, "Brasileirão", "away")
	all, _ := db.TeamRecord("Corinthians", 2022, "Brasileirão", "")
	if home.Played != 19 || away.Played != 19 || all.Played != 38 {
		t.Errorf("played home=%d away=%d all=%d", home.Played, away.Played, all.Played)
	}
	if home.Wins+home.Draws+home.Losses != home.Played {
		t.Error("W+D+L != played")
	}
}

func TestHeadToHeadSymmetry(t *testing.T) {
	db := loadTestDB(t)
	a := db.FindMatches(MatchFilter{Team: "Palmeiras", Opponent: "Santos"})
	b := db.FindMatches(MatchFilter{Team: "Santos", Opponent: "Palmeiras"})
	if len(a) == 0 || len(a) != len(b) {
		t.Errorf("h2h counts %d vs %d", len(a), len(b))
	}
	for _, m := range a {
		if !(TeamMatches(m.HomeTeam, "Palmeiras") && TeamMatches(m.AwayTeam, "Santos")) &&
			!(TeamMatches(m.HomeTeam, "Santos") && TeamMatches(m.AwayTeam, "Palmeiras")) {
			t.Errorf("unexpected match %s", FormatMatch(m))
		}
	}
}

func TestDateRange(t *testing.T) {
	db := loadTestDB(t)
	from, _ := ParseDate("2019-01-01")
	to, _ := ParseDate("31/03/2019")
	ms := db.FindMatches(MatchFilter{Team: "Flamengo", DateFrom: from, DateTo: to})
	if len(ms) == 0 {
		t.Fatal("no matches in range")
	}
	for _, m := range ms {
		if m.Date.Before(from) || m.Date.After(to.Add(24*time.Hour)) {
			t.Errorf("out of range: %s", FormatMatch(m))
		}
	}
}

func TestPlayers(t *testing.T) {
	db := loadTestDB(t)
	br := db.FindPlayers(PlayerFilter{Nationality: "Brazilian"})
	if len(br) < 800 || br[0].Name != "Neymar Jr" {
		t.Errorf("brazilians=%d top=%s", len(br), br[0].Name)
	}
	fw := db.FindPlayers(PlayerFilter{Club: "Santos", Position: "forward"})
	for _, p := range fw {
		if !positionMatches(p.Position, "forward") {
			t.Errorf("%s is %s", p.Name, p.Position)
		}
	}
	if len(db.FindPlayers(PlayerFilter{Name: "messi"})) == 0 {
		t.Error("messi not found")
	}
}

// Sample natural-language questions mapped to tool calls with expected content.
func TestSampleQuestions(t *testing.T) {
	db := loadTestDB(t)
	cases := []struct {
		q    string
		tool string
		args string
		want []string
	}{
		{"Show me all Flamengo vs Fluminense matches", "head_to_head", `{"team1":"Flamengo","team2":"Fluminense"}`, []string{"Fla-Flu", "Head-to-head", "Flamengo"}},
		{"What matches did Palmeiras play in 2023?", "search_matches", `{"team":"Palmeiras","season":2023}`, []string{"Found", "Palmeiras", "2023-"}},
		{"Find all Copa do Brasil finals", "search_matches", `{"competition":"Copa do Brasil","round":"final"}`, []string{"Copa do Brasil Round"}},
		{"Libertadores finals", "search_matches", `{"competition":"Libertadores","round":"final"}`, []string{"Copa Libertadores final"}},
		{"What is Corinthians' home record in 2022?", "team_record", `{"team":"Corinthians","season":2022,"venue":"home","competition":"Brasileirão"}`, []string{"Corinthians home record", "Matches: 19", "Win rate"}},
		{"Which team scored the most goals in Serie A 2023?", "team_rankings", `{"metric":"goals_for","season":2023,"competition":"Serie A"}`, []string{"1. "}},
		{"Compare Palmeiras and Santos head-to-head", "head_to_head", `{"team1":"Palmeiras","team2":"Santos"}`, []string{"Palmeiras", "Santos", "wins"}},
		{"Find all Brazilian players", "search_players", `{"nationality":"Brazil"}`, []string{"Neymar Jr"}},
		{"Highest-rated players at Flamengo?", "search_players", `{"club":"Flamengo"}`, []string{"does not include"}},
		{"Highest-rated players at Grêmio?", "search_players", `{"club":"Gremio"}`, []string{"Club: Grêmio"}},
		{"Forwards from Santos", "search_players", `{"club":"Santos","position":"forward"}`, []string{"Club: Santos", "Position: ST"}},
		{"Who won the 2019 Brasileirão?", "standings", `{"season":2019}`, []string{"Champion: Flamengo"}},
		{"Show the 2018 Copa Libertadores bracket", "search_matches", `{"competition":"Libertadores","season":2018,"round":"quarterfinals"}`, []string{"quarterfinals"}},
		{"Which teams were relegated in 2020?", "standings", `{"season":2020}`, []string{"Relegation zone", "Botafogo"}},
		{"Average goals per match in 2019 Brasileirão", "compare_seasons", `{"seasons":[2019]}`, []string{"/match"}},
		{"Brazilian players at Brazilian clubs", "players_by_club", `{"brazilian_clubs_only":true}`, []string{"avg rating"}},
		{"Show me all derbies in 2023", "derbies", `{"season":2023}`, []string{"Fla-Flu", "Grenal"}},
		{"What competitions has Palmeiras played in?", "team_competitions", `{"team":"Palmeiras"}`, []string{"Copa Libertadores", "Copa do Brasil", "Brasileirão Serie A"}},
		{"Which team has the best home record?", "team_rankings", `{"metric":"win_rate","venue":"home"}`, []string{"home matches", "win rate"}},
		{"Who are the top Brazilian players?", "search_players", `{"nationality":"Brazil","min_overall":85}`, []string{"Neymar Jr", "Casemiro"}},
		{"Compare the 2018 and 2019 seasons", "compare_seasons", `{"seasons":[2018,2019]}`, []string{"2018:", "2019:", "leader: Flamengo"}},
		{"Matches in the 2003 Brasileirão (historical file)", "search_matches", `{"competition":"Brasileirão","season":2003,"team":"Cruzeiro"}`, []string{"Cruzeiro"}},
		{"Serie B matches with stats", "search_matches", `{"competition":"Serie B","limit":3}`, []string{"shots", "corners"}},
		{"Tell me about Grêmio (players + matches)", "team_profile", `{"team":"Grêmio"}`, []string{"record", "FIFA players at club", "Grêmio"}},
		{"Neymar's attributes", "player_details", `{"name":"Neymar"}`, []string{"Dribbling", "Paris"}},
		{"Matches between dates", "search_matches", `{"team":"Santos","date_from":"01/05/2015","date_to":"2015-06-30"}`, []string{"2015-0"}},
	}
	for _, c := range cases {
		var a args
		if err := json.Unmarshal([]byte(c.args), &a); err != nil {
			t.Fatal(err)
		}
		start := time.Now()
		out, err := db.CallTool(c.tool, a)
		if el := time.Since(start); el > 2*time.Second {
			t.Errorf("%q took %v", c.q, el)
		}
		if err != nil {
			t.Errorf("%q: %v", c.q, err)
			continue
		}
		for _, w := range c.want {
			if !strings.Contains(out, w) {
				t.Errorf("%q: output missing %q:\n%s", c.q, w, out)
				break
			}
		}
	}
}

func TestMCPProtocol(t *testing.T) {
	db := loadTestDB(t)
	in := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"top":1}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"nope","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"bogus"}`,
	}, "\n")
	var out bytes.Buffer
	if err := db.Serve(strings.NewReader(in), &out); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 5 {
		t.Fatalf("got %d responses:\n%s", len(lines), out.String())
	}
	var resps []map[string]any
	for _, l := range lines {
		var r map[string]any
		if err := json.Unmarshal([]byte(l), &r); err != nil {
			t.Fatal(err)
		}
		resps = append(resps, r)
	}
	if resps[0]["result"].(map[string]any)["serverInfo"] == nil {
		t.Error("initialize missing serverInfo")
	}
	tools := resps[1]["result"].(map[string]any)["tools"].([]any)
	if len(tools) != len(Tools) {
		t.Errorf("tools/list returned %d", len(tools))
	}
	text := resps[2]["result"].(map[string]any)["content"].([]any)[0].(map[string]any)["text"].(string)
	if !strings.Contains(text, "Flamengo") {
		t.Errorf("standings call: %s", text)
	}
	if resps[3]["result"].(map[string]any)["isError"] != true {
		t.Error("unknown tool should be isError")
	}
	if resps[4]["error"] == nil {
		t.Error("unknown method should error")
	}
}

func TestAggregatePerformance(t *testing.T) {
	db := loadTestDB(t)
	start := time.Now()
	db.TeamRankings("win_rate", 0, "", "home", 0, 10)
	db.CompareSeasons([]int{2015, 2016, 2017, 2018, 2019}, "")
	db.PlayersByClub("Brazil", true, 20)
	if el := time.Since(start); el > 5*time.Second {
		t.Errorf("aggregate queries took %v", el)
	}
}
