package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

var loaded *Store
var loadErr error
var once sync.Once

func realStore(t testing.TB) *Store {
	t.Helper()
	once.Do(func() { loaded, loadErr = LoadStore("data/kaggle") })
	if loadErr != nil {
		t.Fatal(loadErr)
	}
	return loaded
}
func TestNormalizationAndDates(t *testing.T) {
	for _, tc := range [][2]string{{"Palmeiras-SP", "Palmeiras"}, {"Flamengo - RJ", "Clube de Regatas do Flamengo"}, {"São Paulo FC", "Sao Paulo-SP"}, {"Sport Club Corinthians Paulista", "Corinthians-SP"}, {"Grêmio", "Gremio-RS"}, {"Atlético - MG", "Atletico Mineiro"}, {"Atlético-PR", "Athletico Paranaense"}, {"América - MG", "America MG"}, {"Vasco Da Gama RJ", "Vasco"}, {"Fortaleza FC", "Fortaleza-CE"}} {
		if NormalizeTeam(tc[0]) != NormalizeTeam(tc[1]) {
			t.Errorf("aliases differ: %v", tc)
		}
	}
	if NormalizeTeam("América-MG") == NormalizeTeam("América-RN") || NormalizeTeam("Botafogo-SP") == NormalizeTeam("Botafogo-RJ") {
		t.Fatal("distinct clubs conflated")
	}
	for _, s := range []string{"2023-09-24", "24/09/2023", "2023-09-24 20:30:00", "2023-09-24T20:30:00Z"} {
		d, e := parseDate(s)
		if e != nil || d.Format("2006-01-02") != "2023-09-24" {
			t.Fatalf("date %s: %v", s, e)
		}
	}
	for _, s := range []string{"2023-02-30", "yesterday", "09/24/2023"} {
		if _, e := parseDate(s); e == nil {
			t.Fatalf("accepted %s", s)
		}
	}
	for _, s := range []string{"NaN", "-1", "1.5", "Inf"} {
		if _, e := number(s); e == nil {
			t.Errorf("accepted integer %s", s)
		}
	}
}
func TestAllSixDatasetsAndProvenance(t *testing.T) {
	s := realStore(t)
	want := map[string]int{"Brasileirao_Matches.csv": 4180, "Brazilian_Cup_Matches.csv": 1337, "Libertadores_Matches.csv": 1255, "BR-Football-Dataset.csv": 10296, "novo_campeonato_brasileiro.csv": 6886, "fifa_data.csv": 18207}
	if len(s.Sources) != 6 {
		t.Fatal("missing sources")
	}
	for _, src := range s.Sources {
		if src.Rows != want[src.File] || src.License == "" || src.URL == "" {
			t.Errorf("bad source: %+v", src)
		}
	}
	seen := map[string]int{}
	for _, m := range s.Matches {
		for _, src := range m.Sources {
			seen[src.File]++
			if len(src.Fields) == 0 || src.Row < 2 {
				t.Fatal("lost source fields")
			}
		}
	}
	for f, n := range want {
		if f != "fifa_data.csv" && seen[f] != n {
			t.Errorf("lost rows %s: %d != %d", f, seen[f], n)
		}
	}
	if len(s.Players) != 18207 {
		t.Fatal("missing players")
	}
	if s.Players[0].Attributes["Finishing"] != "95" {
		t.Fatal("lost FIFA attribute")
	}
}
func TestGivenFullDataWhen2019StandingsThenNoDoubleCounting(t *testing.T) {
	s := realStore(t)
	ms, e := s.FindMatches(Filter{Competition: "Serie A", Season: 2019})
	if e != nil {
		t.Fatal(e)
	}
	if len(ms) != 380 {
		t.Fatalf("got %d fixtures; likely duplicate aliases", len(ms))
	}
	rs := records(ms, "")
	if len(rs) != 20 {
		t.Fatal(len(rs))
	}
	want := Record{Team: "flamengo", Played: 38, Wins: 28, Draws: 6, Losses: 4, GoalsFor: 86, GoalsAgainst: 37, GoalDifference: 49, Points: 90, WinRate: 100 * 28.0 / 38}
	if rs[0] != want {
		t.Fatalf("standings: %+v want %+v", rs[0], want)
	}
	for _, r := range rs {
		if r.Played != 38 {
			t.Errorf("inconsistent table %+v", r)
		}
	}
}
func TestGivenMatchesWhenFilteredThenEveryResultMatches(t *testing.T) {
	s := realStore(t)
	f := Filter{Team: "Flamengo-RJ", Opponent: "Fluminense", Season: 2022, Competition: "Brasileirão", From: "01/01/2022", To: "31/12/2022"}
	ms, e := s.FindMatches(f)
	if e != nil || len(ms) != 2 {
		t.Fatalf("matches %d: %v", len(ms), e)
	}
	for _, m := range ms {
		if !derby(m.Home, m.Away) || m.HomeGoals == nil || m.Competition != "Brasileirão" {
			t.Fatalf("bad match %+v", m)
		}
	}
	f.Venue = "home"
	ms, e = s.FindMatches(f)
	if e != nil || len(ms) != 1 || ms[0].Home != "flamengo" {
		t.Fatal(ms, e)
	}
	f = Filter{Competition: "Copa do Brasil", Stage: "final", Season: 2020}
	ms, e = s.FindMatches(f)
	if e != nil || len(ms) != 2 {
		t.Fatalf("finals %d %v", len(ms), e)
	}
	for _, file := range datasetFiles[:5] {
		ms, e = s.FindMatches(Filter{Source: file})
		if e != nil || len(ms) == 0 {
			t.Fatalf("unqueryable %s", file)
		}
	}
}
func TestGivenTeamWhenHomeStatsThenCorrectRecord(t *testing.T) {
	s := realStore(t)
	v, e := s.TeamStats(Filter{Team: "Corinthians", Season: 2022, Competition: "Serie A", Venue: "home"})
	if e != nil {
		t.Fatal(e)
	}
	r := v.(map[string]any)["record"].(Record)
	if r.Played != 19 || r.Played != r.Wins+r.Draws+r.Losses || r.Points != r.Wins*3+r.Draws {
		t.Fatalf("bad record %+v", r)
	}
	v, e = s.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 5})
	if e != nil {
		t.Fatal(e)
	}
	ps := v.(map[string]any)["players"].([]Player)
	if len(ps) != 5 || ps[0].Nationality != "Brazil" || ps[0].Overall < ps[4].Overall {
		t.Fatal(ps)
	}
}
func TestGivenSmallGraphWhenAggregatedThenExactResults(t *testing.T) {
	s := &Store{teams: map[string][]int{"a": {0, 1, 2}, "b": {0, 1, 2}}, playersByClub: map[string][]int{"a": {0}}, Players: []Player{{ID: "1", Name: "Player", Club: "a", Overall: 80}}}
	score := func(i int) *int { return &i }
	s.Matches = []Match{{ID: "match:1", Home: "a", Away: "b", HomeGoals: score(3), AwayGoals: score(1), Season: 2020, Competition: "Brasileirão", Date: "2020-01-01"}, {ID: "match:2", Home: "b", Away: "a", HomeGoals: score(2), AwayGoals: score(2), Season: 2020, Competition: "Brasileirão", Date: "2020-02-01"}, {ID: "match:3", Home: "a", Away: "b", Season: 2020, Competition: "Brasileirão"}}
	v, e := s.Statistics(Filter{})
	if e != nil {
		t.Fatal(e)
	}
	m := v.(map[string]any)
	if m["played"] != 2 || m["goals_per_match"] != 4.0 || m["home_win_rate_percent"] != 50.0 {
		t.Fatal(m)
	}
	r := teamRecord(s.Matches, "a")
	if r.Played != 2 || r.Wins != 1 || r.Draws != 1 || r.GoalsFor != 5 || r.GoalsAgainst != 3 {
		t.Fatal(r)
	}
	g, e := s.Graph("a", 500, 0)
	if e != nil {
		t.Fatal(e)
	}
	gm := g.(map[string]any)
	if gm["total_edges"] != 5 {
		t.Fatal(gm)
	}
	nodes := gm["nodes"].(map[string]any)
	if _, ok := nodes["player:1"]; !ok {
		t.Fatal("missing player relationship")
	}
	ms, e := s.FindMatches(Filter{To: "2020-12-31"})
	if e != nil || len(ms) != 2 {
		t.Fatal("unknown date included in bounded search", ms, e)
	}
}
func TestValidationAndPagination(t *testing.T) {
	s := realStore(t)
	for _, f := range []Filter{{Venue: "invalid"}, {Opponent: "a"}, {Team: "a", Opponent: "a"}, {From: "bad"}, {From: "2021-01-01", To: "2020-01-01"}, {Limit: 501}, {Offset: -1}, {Season: -1}, {Source: "bad.csv"}, {Sort: "wrong"}, {Venue: "home"}} {
		if _, e := s.FindMatches(f); e == nil {
			t.Errorf("accepted %+v", f)
		}
	}
	for _, name := range []string{"search_matches", "search_players", "team_graph", "dataset_info"} {
		if _, e := s.Call(name, json.RawMessage(`{"unknown":1}`)); e == nil {
			t.Errorf("accepted unknown argument for %s", name)
		}
	}
	if _, e := s.Standings(Filter{Competition: "Libertadores", Season: 2018}); e == nil {
		t.Fatal("cup standings misleading")
	}
	if _, e := s.FindPlayers(PlayerFilter{MinOverall: 101}); e == nil {
		t.Fatal("invalid rating")
	}
	v, e := s.Call("search_matches", json.RawMessage(`{"team":"does not exist"}`))
	if e != nil || v.(map[string]any)["total"] != 0 {
		t.Fatal(v, e)
	}
	ms, _ := s.FindMatches(Filter{Team: "Palmeiras"})
	page := matchPage(ms, Filter{Offset: len(ms) + 20, Limit: 5}).(map[string]any)
	if len(page["matches"].([]Match)) != 0 || page["next_offset"] != nil {
		t.Fatal(page)
	}
}
func TestMCPStdioLifecycleAndErrors(t *testing.T) {
	s := realStore(t)
	input := strings.Join([]string{
		`garbage`, `[]`, `{"jsonrpc":"2.0","id":0,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","limit":1}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_stats","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"bogus"}}`,
		`{"jsonrpc":"2.0","method":"notifications/cancelled","params":{"requestId":999}}`,
		`{"jsonrpc":"2.0","id":6,"method":"unknown"}`,
		`{"jsonrpc":"2.0","id":7,"method":"ping"}`,
	}, "\n") + "\n"
	var out bytes.Buffer
	if e := Serve(strings.NewReader(input), &out, s); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 10 {
		t.Fatalf("got %d replies: %s", len(lines), out.String())
	}
	rs := []map[string]any{}
	for _, line := range lines {
		var r map[string]any
		if e := json.Unmarshal([]byte(line), &r); e != nil {
			t.Fatal(e)
		}
		rs = append(rs, r)
	}
	for i, code := range map[int]float64{0: -32700, 1: -32600, 2: -32002, 7: -32602, 8: -32601} {
		if rs[i]["error"].(map[string]any)["code"] != code {
			t.Fatal(rs[i])
		}
	}
	if rs[3]["id"] != "init" {
		t.Fatal("string ID lost")
	}
	if len(rs[4]["result"].(map[string]any)["tools"].([]any)) != 9 {
		t.Fatal("tools missing")
	}
	if rs[5]["result"].(map[string]any)["isError"] != false || rs[6]["result"].(map[string]any)["isError"] != true {
		t.Fatal("tool errors mishandled")
	}
}
func TestLoaderErrors(t *testing.T) {
	d := t.TempDir()
	if _, e := LoadStore(d); e == nil {
		t.Fatal("missing files accepted")
	}
	p := filepath.Join(d, datasetFiles[0])
	if e := os.WriteFile(p, []byte("nonsense\n1\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e := LoadStore(d); e == nil || !strings.Contains(e.Error(), "missing column") {
		t.Fatal(e)
	}
	if e := os.WriteFile(p, []byte("datetime,home_team,away_team,home_goal,away_goal,season\n2020-02-31,a,b,1,0,2020\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e := LoadStore(d); e == nil || !strings.Contains(e.Error(), "row 2") {
		t.Fatal(e)
	}
}

// These scenarios correspond to the twenty natural-language examples in README.md.
func TestTwentySampleQuestions(t *testing.T) {
	s := realStore(t)
	cases := []struct{ name, args string }{
		{"search_matches", `{"team":"Flamengo","opponent":"Fluminense"}`},
		{"search_matches", `{"team":"Palmeiras","season":2023}`},
		{"search_matches", `{"competition":"Copa do Brasil","stage":"final"}`},
		{"search_matches", `{"team":"Flamengo","opponent":"Corinthians","limit":1}`},
		{"team_stats", `{"team":"Corinthians","season":2022,"venue":"home"}`},
		{"head_to_head", `{"team":"Palmeiras","opponent":"Santos"}`},
		{"search_players", `{"nationality":"Brazil"}`},
		{"search_players", `{"club":"Flamengo"}`},
		{"search_players", `{"club":"São Paulo FC","position":"forward"}`},
		{"search_players", `{"name":"Gabriel"}`},
		{"standings", `{"competition":"Brasileirão","season":2019}`},
		{"competition_results", `{"competition":"Libertadores","season":2018}`},
		{"statistics", `{"competition":"Brasileirão"}`},
		{"statistics", `{"competition":"Serie A","season":2023}`},
		{"search_matches", `{"sort":"biggest_wins","limit":10}`},
		{"search_matches", `{"derbies":true,"season":2023}`},
		{"team_stats", `{"team":"Palmeiras"}`},
		{"statistics", `{"competition":"Brasileirão","season":2018}`},
		{"statistics", `{"competition":"Brasileirão","season":2019}`},
		{"team_graph", `{"team":"Flamengo","limit":500}`},
	}
	for i, tc := range cases {
		t.Run(fmt.Sprint(i+1), func(t *testing.T) {
			start := time.Now()
			v, e := s.Call(tc.name, json.RawMessage(tc.args))
			if e != nil {
				t.Fatal(e)
			}
			if _, e = json.Marshal(v); e != nil {
				t.Fatal(e)
			}
			if time.Since(start) > 2*time.Second {
				t.Fatal("query exceeded 2 seconds")
			}
			if v == nil {
				t.Fatal("nil result")
			}
		})
	}
}
func BenchmarkLookup(b *testing.B) {
	s := realStore(b)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = s.FindMatches(Filter{Team: "Flamengo", Opponent: "Corinthians"})
	}
}
func BenchmarkAggregate(b *testing.B) {
	s := realStore(b)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = s.Statistics(Filter{})
	}
}

func TestPostponedFixturesAndCrossYearSeasons(t *testing.T) {
	s := realStore(t)
	for _, year := range []int{2014, 2020, 2021, 2022} {
		ms, err := s.FindMatches(Filter{Competition: "Brasileirão", Season: year})
		if err != nil || len(ms) != 380 {
			t.Fatalf("season %d: %d matches, %v", year, len(ms), err)
		}
	}
	ms, err := s.FindMatches(Filter{Competition: "Copa do Brasil", Season: 2020, Stage: "final"})
	if err != nil || len(ms) != 2 {
		t.Fatalf("2020 finals: %d %v", len(ms), err)
	}
	for _, m := range ms {
		if !strings.HasPrefix(m.Date, "2021-") {
			t.Fatalf("expected cross-year final: %+v", m)
		}
		if len(m.Sources) < 2 {
			t.Fatal("extended final did not merge")
		}
	}
	ms, err = s.FindMatches(Filter{Competition: "Copa do Brasil", Season: 2021, Stage: "final", Source: "Brazilian_Cup_Matches.csv"})
	if err != nil || len(ms) != 0 {
		t.Fatal("incomplete source's last round mislabeled final", ms, err)
	}
}
