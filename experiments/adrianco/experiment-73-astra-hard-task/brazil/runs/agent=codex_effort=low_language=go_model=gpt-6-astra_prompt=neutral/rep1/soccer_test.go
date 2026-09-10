package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

var once sync.Once
var realDB *Store
var loadErr error

func dataset(t *testing.T) *Store {
	t.Helper()
	once.Do(func() { realDB, loadErr = Load("data/kaggle") })
	if loadErr != nil {
		t.Fatal(loadErr)
	}
	return realDB
}
func TestNormalization(t *testing.T) {
	for _, v := range [][2]string{{"Palmeiras-SP", "palmeiras"}, {"São Paulo FC", "sao paulo"}, {"Sport Club Corinthians Paulista", "corinthians"}, {"Grêmio - RS", "gremio"}, {"Flamengo-RJ", "flamengo"}, {"Atlético - MG", "atletico mg"}, {"Athletico-PR", "athletico pr"}, {"América - RN", "america rn"}, {"Botafogo - SP", "botafogo sp"}} {
		if got := team(v[0]); got != v[1] {
			t.Errorf("team(%q)=%q want %q", v[0], got, v[1])
		}
	}
	if team("América-MG") == team("América-RN") {
		t.Fatal("merged different clubs")
	}
}
func TestDatesAndScores(t *testing.T) {
	for _, v := range []string{"2023-09-24", "24/09/2023", "2023-09-24 18:30:00", "2023-09-24T18:30:00Z"} {
		got, e := parseDate(v)
		if e != nil || got != "2023-09-24" {
			t.Fatalf("%s: %s %v", v, got, e)
		}
	}
	if _, e := parseDate("31/02/2023"); e == nil {
		t.Fatal("accepted impossible date")
	}
	for _, s := range []string{"", "NA", "NaN"} {
		v, e := score(s)
		if e != nil || v != nil {
			t.Fatal(s, v, e)
		}
	}
	for _, s := range []string{"-1", "1.5", "x", "Inf"} {
		if _, e := score(s); e == nil {
			t.Fatal("accepted", s)
		}
	}
	v, e := score("2.0")
	if e != nil || *v != 2 {
		t.Fatal(v, e)
	}
}
func TestAllFilesLoadAndQueryable(t *testing.T) {
	db := dataset(t)
	expected := []int{4180, 1337, 1255, 10296, 6886, 18207}
	for i, f := range files {
		if db.Sources[f] != expected[i] {
			t.Errorf("%s rows=%d want %d", f, db.Sources[f], expected[i])
		}
		if i < 5 && len(db.matches(Filter{Source: f})) == 0 {
			t.Error("not queryable", f)
		}
	}
	if len(db.Players) != 18207 {
		t.Fatal(len(db.Players))
	}
	if len(db.Matches) >= 23954 {
		t.Fatal("no deduplication")
	}
}
func TestGivenResultsWhenTeamStatsThenCorrect(t *testing.T) {
	i := func(n int) *int { return &n }
	ms := []Match{{Home: "a", Away: "b", HomeGoals: i(2), AwayGoals: i(0)}, {Home: "b", Away: "a", HomeGoals: i(1), AwayGoals: i(1)}, {Home: "a", Away: "b", HomeGoals: i(0), AwayGoals: i(3)}, {Home: "a", Away: "b"}}
	r := record("a", ms, "")
	if r.Played != 3 || r.Wins != 1 || r.Draws != 1 || r.Losses != 1 || r.GoalsFor != 3 || r.GoalsAgainst != 4 || r.Points != 4 {
		t.Fatalf("%+v", r)
	}
	if record("a", ms, "home").Played != 2 || record("a", ms, "away").Draws != 1 {
		t.Fatal("venue split")
	}
	s := summary(ms)
	if s["played"] != 3 || s["goals"] != 7 {
		t.Fatal(s)
	}
}
func TestGivenDerbyWhenSearchingThenBothDirections(t *testing.T) {
	db := dataset(t)
	ms := db.matches(Filter{Team: "Flamengo-RJ", Opponent: "Fluminense"})
	if len(ms) == 0 {
		t.Fatal("no derby")
	}
	directions := map[string]bool{}
	for _, m := range ms {
		if !(m.Home == "flamengo" && m.Away == "fluminense" || m.Home == "fluminense" && m.Away == "flamengo") {
			t.Fatal(m)
		}
		if m.Date == "" || m.Competition == "" {
			t.Fatal(m)
		}
		directions[m.Home] = true
	}
	if len(directions) != 2 {
		t.Fatal("missing reverse fixture")
	}
}
func TestKnown2019Standings(t *testing.T) {
	db := dataset(t)
	rows := table(db.matches(Filter{Season: 2019, Competition: "Serie A"}), Filter{})
	if len(rows) != 20 {
		t.Fatalf("teams=%d: %+v", len(rows), rows)
	}
	if rows[0].Team != "flamengo" || rows[0].Points != 90 || rows[0].Played != 38 {
		t.Fatalf("champion record: %+v", rows[0])
	}
}
func TestTwentySampleQuestions(t *testing.T) {
	db := dataset(t)
	cases := []struct {
		question, tool string
		f              Filter
	}{
		{"Show all Fla-Flu matches", "search_matches", Filter{Team: "Flamengo", Opponent: "Fluminense"}},
		{"Palmeiras matches in 2023", "search_matches", Filter{Team: "Palmeiras", Season: 2023}},
		{"Copa do Brasil finals", "search_matches", Filter{Competition: "Copa do Brasil", Stage: "final"}},
		{"Corinthians home record 2022", "team_stats", Filter{Team: "Corinthians", Venue: "home", Season: 2022}},
		{"Most goals Serie A 2023", "statistics", Filter{Competition: "Serie A", Season: 2023, Sort: "goals"}},
		{"Palmeiras versus Santos", "head_to_head", Filter{Team: "Palmeiras", Opponent: "Santos"}},
		{"All Brazilian players", "search_players", Filter{Nationality: "Brazil"}},
		{"Highest rated Flamengo players", "search_players", Filter{Club: "Flamengo"}},
		{"Sao Paulo forwards", "search_players", Filter{Club: "São Paulo FC", Position: "forwards"}},
		{"2019 league winner from results", "standings", Filter{Competition: "Serie A", Season: 2019}},
		{"2018 Libertadores knockout results", "competition_info", Filter{Competition: "Libertadores", Season: 2018}},
		{"2020 bottom of league table", "standings", Filter{Competition: "Serie A", Season: 2020}},
		{"Average Serie A goals", "statistics", Filter{Competition: "Serie A"}},
		{"Best away record", "statistics", Filter{Venue: "away", Sort: "win_rate"}},
		{"Biggest wins", "search_matches", Filter{Sort: "biggest_win"}},
		{"Latest Flamengo Corinthians score", "search_matches", Filter{Team: "Flamengo", Opponent: "Corinthians", Limit: 1}},
		{"Who is Gabriel Barbosa", "search_players", Filter{Name: "Gabriel"}},
		{"Flamengo squad and match history", "team_profile", Filter{Team: "Flamengo"}},
		{"Derbies in 2023", "search_matches", Filter{Season: 2023, Derby: true}},
		{"Palmeiras competitions", "team_stats", Filter{Team: "Palmeiras"}},
		{"Compare 2018 and 2019", "statistics", Filter{From: "2018-01-01", To: "2019-12-31"}},
		{"Explore Flamengo relationships", "graph", Filter{Team: "Flamengo"}},
	}
	for _, tc := range cases {
		t.Run(tc.question, func(t *testing.T) {
			start := time.Now()
			v, e := db.Query(tc.tool, tc.f)
			if e != nil {
				t.Fatal(e)
			}
			if v == nil {
				t.Fatal("nil response")
			}
			if time.Since(start) > 2*time.Second {
				t.Fatal("query exceeded simple lookup budget")
			}
			if p, ok := v.(map[string]any); ok {
				if total, ok := p["total"].(int); ok && total == 0 && tc.tool != "search_players" {
					t.Fatal("unexpected no matches")
				}
			}
		})
	}
}
func TestPlayerFilteringAndPagination(t *testing.T) {
	db := dataset(t)
	v, e := db.Query("search_players", Filter{Nationality: "Brazil", Limit: 2})
	if e != nil {
		t.Fatal(e)
	}
	p := v.(map[string]any)
	players := p["items"].([]Player)
	if len(players) != 2 || players[0].Nationality != "Brazil" || players[0].Overall < players[1].Overall || len(players[0].Attributes) < 60 {
		t.Fatal(p)
	}
	v, _ = db.Query("search_players", Filter{Nationality: "Brazil", Limit: 2, Offset: 2})
	if v.(map[string]any)["items"].([]Player)[0].ID == players[0].ID {
		t.Fatal("pagination repeated")
	}
}
func TestFiltersAndValidation(t *testing.T) {
	db := dataset(t)
	ms := db.matches(Filter{Team: "Palmeiras", Season: 2023, Venue: "home", From: "2023-01-01", To: "2023-06-30"})
	if len(ms) == 0 {
		t.Fatal("empty")
	}
	for _, m := range ms {
		if m.Home != "palmeiras" || m.Date > "2023-06-30" || m.Season != 2023 {
			t.Fatal(m)
		}
	}
	for _, f := range []Filter{{Limit: 501}, {Offset: -1}, {Venue: "bad"}, {From: "bad"}, {From: "2023-01-02", To: "2023-01-01"}, {Opponent: "Santos"}} {
		if _, e := db.Query("search_matches", f); e == nil {
			t.Fatal("accepted invalid filter", f)
		}
	}
	v, _ := db.Query("search_matches", Filter{Team: "nonexistent"})
	if v.(map[string]any)["total"] != 0 {
		t.Fatal(v)
	}
}
func TestLoaderDedupAndMalformedInput(t *testing.T) {
	dir := t.TempDir()
	name := files[0]
	path := filepath.Join(dir, name)
	csv := "datetime,home_team,away_team,home_goal,away_goal,season,round\n2023-01-01,Flamengo-RJ,Palmeiras-SP,2,1,2023,1\n2023-01-01,Flamengo,Palmeiras,2,1,2023,1\n"
	if e := os.WriteFile(path, []byte(csv), 0600); e != nil {
		t.Fatal(e)
	}
	db := &Store{Sources: map[string]int{}}
	if e := db.loadFile(path, name, map[string]int{}); e != nil {
		t.Fatal(e)
	}
	if len(db.Matches) != 1 || db.Sources[name] != 2 {
		t.Fatal(db)
	}
	if e := os.WriteFile(path, []byte("wrong\n1\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := db.loadFile(path, name, map[string]int{}); e == nil {
		t.Fatal("missing header accepted")
	}
	if _, e := Load(dir); e == nil {
		t.Fatal("missing datasets accepted")
	}
}
func TestMCPStdio(t *testing.T) {
	s := &Server{DB: dataset(t)}
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","limit":1}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_stats","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"missing"}`,
		`{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"search_matches","arguments":{"limit":"bad"}}}`,
		`not json`,
		`{"jsonrpc":"2.0","id":7,"method":"ping"}`,
	}, "\n")
	var out bytes.Buffer
	if e := s.Serve(strings.NewReader(input), &out); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 8 {
		t.Fatalf("got %d responses", len(lines))
	}
	decoded := []map[string]any{}
	for _, line := range lines {
		var r map[string]any
		if e := json.Unmarshal([]byte(line), &r); e != nil {
			t.Fatal(e)
		}
		decoded = append(decoded, r)
	}
	if len(decoded[1]["result"].(map[string]any)["tools"].([]any)) != 10 {
		t.Fatal("tool catalog")
	}
	if decoded[2]["result"].(map[string]any)["isError"] != false {
		t.Fatal(decoded[2])
	}
	if decoded[3]["result"].(map[string]any)["isError"] != true {
		t.Fatal(decoded[3])
	}
	for i, code := range map[int]float64{4: -32601, 5: -32602, 6: -32700} {
		if decoded[i]["error"].(map[string]any)["code"] != code {
			t.Fatal(decoded[i])
		}
	}
}
func TestMCPBeforeInitialization(t *testing.T) {
	s := &Server{DB: dataset(t)}
	v := s.handle([]byte(`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`)).(map[string]any)
	if v["error"] == nil {
		t.Fatal(v)
	}
}
func BenchmarkLookup(b *testing.B) {
	db, e := Load("data/kaggle")
	if e != nil {
		b.Fatal(e)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		db.Query("search_matches", Filter{Team: "Flamengo", Opponent: "Fluminense"})
	}
}
func BenchmarkAggregate(b *testing.B) {
	db, e := Load("data/kaggle")
	if e != nil {
		b.Fatal(e)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		db.Query("statistics", Filter{})
	}
}

func TestFinalsDoNotIncludeSemifinals(t *testing.T) {
	db := dataset(t)
	ms := db.matches(Filter{Competition: "Libertadores", Stage: "final"})
	if len(ms) == 0 {
		t.Fatal("no finals")
	}
	for _, m := range ms {
		if m.Stage != "final" {
			t.Fatal(m.Stage)
		}
	}
}
func TestStandingsTieBreakAndEmptyStats(t *testing.T) {
	i := func(n int) *int { return &n }
	rows := table([]Match{{Home: "a", Away: "b", HomeGoals: i(2), AwayGoals: i(0)}, {Home: "b", Away: "c", HomeGoals: i(3), AwayGoals: i(0)}, {Home: "c", Away: "a", HomeGoals: i(1), AwayGoals: i(0)}}, Filter{})
	if rows[0].Team != "b" || rows[1].Team != "a" {
		t.Fatal(rows)
	}
	b, e := json.Marshal(summary(nil))
	if e != nil || !bytes.Contains(b, []byte(`"average_goals":0`)) {
		t.Fatal(string(b), e)
	}
}
func TestDedupPreservesSourcesAndAttributes(t *testing.T) {
	db := dataset(t)
	found := false
	for _, m := range db.matches(Filter{Team: "Flamengo", Season: 2019, Competition: "Serie A"}) {
		if len(m.Sources) >= 3 {
			found = true
			if m.Attributes["home_corner"] == "" || m.Stadium == "" {
				t.Fatal("lost enrichment", m)
			}
		}
	}
	if !found {
		t.Fatal("no three-source enrichment")
	}
}
func TestLatestAndGraph(t *testing.T) {
	db := dataset(t)
	ms := db.matches(Filter{Team: "Flamengo", Opponent: "Corinthians"})
	for i := 1; i < len(ms); i++ {
		if ms[i].Date > ms[i-1].Date {
			t.Fatal("wrong date order")
		}
	}
	v, e := db.Query("graph", Filter{Team: "Flamengo", Limit: 2})
	if e != nil {
		t.Fatal(e)
	}
	g := v.(map[string]any)
	ids := map[string]bool{}
	for _, n := range g["nodes"].([]map[string]string) {
		ids[n["id"]] = true
	}
	for _, edge := range g["edges"].([]map[string]string) {
		if !ids[edge["from"]] || !ids[edge["to"]] {
			t.Fatal("dangling edge", edge)
		}
	}
}
func TestAggregatePaginationDoesNotTruncateRecords(t *testing.T) {
	db := dataset(t)
	a, _ := db.Query("team_stats", Filter{Team: "Flamengo", Season: 2019, Competition: "Serie A", Limit: 1})
	b, _ := db.Query("team_stats", Filter{Team: "Flamengo", Season: 2019, Competition: "Serie A", Limit: 100})
	if a.(map[string]any)["record"] != b.(map[string]any)["record"] {
		t.Fatal("pagination changed record")
	}
}
