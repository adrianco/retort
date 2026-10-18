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
var testGraph *Graph
var loadErr error

func dataset(t *testing.T) *Graph {
	t.Helper()
	once.Do(func() { testGraph, loadErr = LoadGraph("data/kaggle") })
	if loadErr != nil {
		t.Fatal(loadErr)
	}
	return testGraph
}
func TestNormalizationAndDates(t *testing.T) {
	for _, pair := range [][2]string{{"Palmeiras-SP", "Palmeiras"}, {"Flamengo - RJ", "Flamengo"}, {"Sport Club Corinthians Paulista", "Corinthians"}, {"São Paulo FC", "Sao Paulo"}, {"Grêmio-RS", "Gremio"}, {"Atletico - PR", "Athletico Paranaense - PR"}, {"Atlético - MG", "Atletico Mineiro"}, {"América - MG", "America MG"}, {"A.b.c. - RN", "ABC"}, {"Sa\u0303o Paulo", "São Paulo"}} {
		if teamKey(pair[0]) != teamKey(pair[1]) {
			t.Errorf("%q != %q: %s / %s", pair[0], pair[1], teamKey(pair[0]), teamKey(pair[1]))
		}
	}
	for _, pair := range [][2]string{{"América-MG", "América-RN"}, {"Botafogo-PB", "Botafogo-RJ"}, {"Flamengo-PI", "Flamengo-RJ"}} {
		if teamKey(pair[0]) == teamKey(pair[1]) {
			t.Errorf("distinct clubs collapsed: %v", pair)
		}
	}
	for _, s := range []string{"2023-09-24", "24/09/2023", "2023-09-24 12:34:56", "2023-09-24T12:34:56Z"} {
		v, e := parseDate(s)
		if e != nil || v.Format("2006-01-02") != "2023-09-24" {
			t.Fatalf("date %s: %v", s, e)
		}
	}
	if _, e := parseDate("31/02/2023"); e == nil {
		t.Fatal("accepted impossible date")
	}
}
func TestAllDatasetsAndProvenance(t *testing.T) {
	g := dataset(t)
	want := []int{4180, 1337, 1255, 10296, 6886, 18207}
	if len(g.Sources) != 6 {
		t.Fatal(g.Sources)
	}
	for i, s := range g.Sources {
		if s.Rows != want[i] {
			t.Errorf("%s rows=%d", s.File, s.Rows)
		}
		if i < 5 && len(g.FindMatches(Query{Source: s.File})) == 0 {
			t.Errorf("source not queryable: %s", s.File)
		}
	}
	if len(g.Players) != 18207 {
		t.Fatal(len(g.Players))
	}
	merged := 0
	for _, m := range g.Matches {
		if len(m.Sources) > 1 {
			merged++
		}
		for _, s := range m.Sources {
			if m.Attributes[s] == nil {
				t.Fatal("missing provenance")
			}
		}
	}
	if merged == 0 {
		t.Fatal("no merged matches")
	}
	t.Logf("%d matches, %d merged, %d players", len(g.Matches), merged, len(g.Players))
}
func TestGivenMatchesWhenRequestingRecordThenExactStatistics(t *testing.T) {
	a, b, c := 2, 1, 0
	ms := []*Match{{Home: "a", Away: "b", HomeGoals: &a, AwayGoals: &b}, {Home: "b", Away: "a", HomeGoals: &c, AwayGoals: &c}, {Home: "a", Away: "b", HomeGoals: &c, AwayGoals: &b}, {Home: "a", Away: "b"}}
	r := recordFor(ms, "a", "")
	if r.Played != 3 || r.Wins != 1 || r.Draws != 1 || r.Losses != 1 || r.GoalsFor != 2 || r.GoalsAgainst != 2 || r.Points != 4 {
		t.Fatalf("bad record %+v", r)
	}
	if recordFor(ms, "a", "home").Played != 2 || recordFor(ms, "a", "away").Draws != 1 {
		t.Fatal("bad venue records")
	}
	s := summarize(ms)
	if s.Matches != 4 || s.Played != 3 || s.Goals != 4 || s.HomeWins != 1 || s.AwayWins != 1 || s.Draws != 1 {
		t.Fatalf("bad summary %+v", s)
	}
}
func TestGivenDerbyWhenSearchingThenBothOrientations(t *testing.T) {
	g := dataset(t)
	q := Query{Team: "Flamengo-RJ", Opponent: "Fluminense", Competition: "Serie A"}
	ms := g.FindMatches(q)
	if len(ms) == 0 {
		t.Fatal("no derby matches")
	}
	orient := map[string]bool{}
	for _, m := range ms {
		if m.Home != "flamengo" && m.Away != "flamengo" || m.Home != "fluminense" && m.Away != "fluminense" || m.Competition != "Brasileirão" {
			t.Fatal(m)
		}
		orient[m.Home] = true
	}
	if len(orient) != 2 {
		t.Fatal("missing reverse fixture")
	}
	q.Venue = "home"
	for _, m := range g.FindMatches(q) {
		if m.Home != "flamengo" {
			t.Fatal(m)
		}
	}
}
func TestCupStageMapping(t *testing.T) {
	g := dataset(t)
	for year := 2012; year <= 2020; year++ {
		ms := g.FindMatches(Query{Competition: "Copa do Brasil", Season: year, Stage: "final", Source: "Brazilian_Cup_Matches.csv"})
		if len(ms) != 2 {
			t.Errorf("%d finals = %d", year, len(ms))
		}
	}
	if len(g.FindMatches(Query{Competition: "Copa do Brasil", Season: 2021, Stage: "final", Source: "Brazilian_Cup_Matches.csv"})) != 0 {
		t.Fatal("partial season promoted to final")
	}
	if stage(&Match{Competition: "Libertadores", Stage: "semifinals"}) == "final" {
		t.Fatal("semifinals matched final")
	}
}
func TestPlayerFilters(t *testing.T) {
	g := dataset(t)
	ps := g.FindPlayers(Query{Nationality: "Brazil"})
	if len(ps) == 0 {
		t.Fatal("no Brazilians")
	}
	for i, p := range ps {
		if p.Nationality != "Brazil" {
			t.Fatal(p)
		}
		if i > 0 && ps[i-1].Overall < p.Overall {
			t.Fatal("not rating sorted")
		}
	}
	ps = g.FindPlayers(Query{Name: "Neymar"})
	if len(ps) != 1 || ps[0].Attributes["Dribbling"] == "" {
		t.Fatal("name/attributes query failed")
	}
	for _, p := range g.FindPlayers(Query{Club: "São Paulo FC", Position: "forwards"}) {
		if teamKey(p.Club) != "sao paulo" {
			t.Fatal(p)
		}
	}
}
func TestDateRangeAndPagination(t *testing.T) {
	g := dataset(t)
	ms := g.FindMatches(Query{From: "2019-01-01", To: "2019-12-31", Season: 2019})
	if len(ms) == 0 {
		t.Fatal("empty year")
	}
	for _, m := range ms {
		if m.Date < "2019-01-01" || m.Date > "2019-12-31" {
			t.Fatal(m)
		}
	}
	p := page(ms, Query{Limit: 2, Offset: 1})
	if len(p["items"].([]*Match)) != 2 || p["next_offset"] != 3 || p["total"] != len(ms) {
		t.Fatal(p)
	}
	if len(page(ms, Query{Offset: len(ms) + 20})["items"].([]*Match)) != 0 {
		t.Fatal("past end")
	}
}
func TestStandings2019(t *testing.T) {
	rs := records(dataset(t).FindMatches(Query{Competition: "Serie A", Season: 2019}), "")
	t.Logf("standings: %+v", rs)
	if len(rs) != 20 || rs[0].Team != "flamengo" || rs[0].Points != 90 || rs[0].Played != 38 {
		t.Fatalf("unexpected 2019 standings: %+v", rs)
	}
}

// These scenarios mirror natural-language requests an MCP host translates into tools.
func TestTwentyFourSampleQuestions(t *testing.T) {
	g := dataset(t)
	cases := []struct {
		question, tool string
		q              Query
	}{
		{"Show Flamengo vs Fluminense", "head_to_head", Query{Team: "Flamengo", Opponent: "Fluminense"}},
		{"Palmeiras matches in 2023", "search_matches", Query{Team: "Palmeiras", Season: 2023}},
		{"Copa do Brasil finals", "search_matches", Query{Competition: "Copa do Brasil", Stage: "final"}},
		{"Corinthians home record 2022", "team_profile", Query{Team: "Corinthians", Venue: "home", Season: 2022}},
		{"Most goals in Serie A 2023", "statistics", Query{Competition: "Serie A", Season: 2023, Sort: "goals"}},
		{"Compare Palmeiras and Santos", "head_to_head", Query{Team: "Palmeiras", Opponent: "Santos"}},
		{"Brazilian players", "search_players", Query{Nationality: "Brazil"}},
		{"Highest rated Flamengo players", "search_players", Query{Club: "Flamengo"}},
		{"Sao Paulo forwards", "search_players", Query{Club: "São Paulo FC", Position: "forwards"}},
		{"2019 league winner in dataset", "standings", Query{Competition: "Serie A", Season: 2019}},
		{"2018 Libertadores knockout results", "competition_results", Query{Competition: "Libertadores", Season: 2018}},
		{"2020 bottom league positions", "standings", Query{Competition: "Serie A", Season: 2020}},
		{"Average goals in Brasileirao", "statistics", Query{Competition: "Brasileirão"}},
		{"Best away record", "statistics", Query{Venue: "away", Sort: "win_rate"}},
		{"Biggest victories", "search_matches", Query{Sort: "biggest_win", Limit: 10}},
		{"Last Flamengo Corinthians match", "search_matches", Query{Team: "Flamengo", Opponent: "Corinthians", Limit: 1}},
		{"Who is Gabriel Barbosa", "search_players", Query{Name: "Gabriel Barbosa"}},
		{"Players at Flamengo", "search_players", Query{Club: "Flamengo"}},
		{"Derbies in 2023", "search_matches", Query{Season: 2023, Derbies: true}},
		{"Palmeiras competitions", "team_profile", Query{Team: "Palmeiras"}},
		{"Best home record", "statistics", Query{Venue: "home", Sort: "win_rate"}},
		{"Top Brazilian players", "search_players", Query{Nationality: "Brazil", Limit: 10}},
		{"Compare 2018 and 2019", "statistics", Query{From: "2018-01-01", To: "2019-12-31"}},
		{"Match corners and shots", "search_matches", Query{Source: "BR-Football-Dataset.csv", Limit: 1}},
	}
	for _, tc := range cases {
		t.Run(tc.question, func(t *testing.T) {
			start := time.Now()
			v, e := g.Call(tc.tool, tc.q)
			if e != nil {
				t.Fatal(e)
			}
			b, e := json.Marshal(v)
			if e != nil || len(b) < 2 {
				t.Fatalf("invalid result: %v", e)
			}
			if time.Since(start) > 2*time.Second {
				t.Fatal("query exceeded 2 seconds")
			}
		})
	}
}
func TestValidation(t *testing.T) {
	for _, q := range []Query{{Venue: "side"}, {Limit: 501}, {Offset: -1}, {From: "2020-02-31"}, {From: "2023-01-01", To: "2022-01-01"}, {Opponent: "Santos"}, {Sort: "random"}} {
		if q.validate() == nil {
			t.Errorf("accepted %+v", q)
		}
	}
	g := dataset(t)
	for _, tool := range []string{"head_to_head", "team_profile", "standings", "not_a_tool"} {
		if _, e := g.Call(tool, Query{}); e == nil {
			t.Errorf("accepted %s", tool)
		}
	}
	if _, e := g.Call("standings", Query{Competition: "Libertadores", Season: 2018}); e == nil {
		t.Fatal("invented knockout standings")
	}
}
func TestMCPStdio(t *testing.T) {
	input := strings.Join([]string{
		`{`,
		`{"jsonrpc":"2.0","id":0,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","limit":1}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_matches","arguments":{"limit":-1}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"search_matches","arguments":{"bogus":true}}}`,
		`{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"absent"}}`,
		`{"jsonrpc":"2.0","id":7,"method":"absent"}`,
		`{"jsonrpc":"2.0","method":"notifications/cancelled"}`,
		`{"jsonrpc":"2.0","id":8,"method":"ping"}`,
	}, "\n")
	var out bytes.Buffer
	if e := Serve(dataset(t), strings.NewReader(input), &out); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 10 {
		t.Fatalf("responses %d: %s", len(lines), out.String())
	}
	var rs []map[string]any
	for _, line := range lines {
		var r map[string]any
		if e := json.Unmarshal([]byte(line), &r); e != nil {
			t.Fatal(e)
		}
		rs = append(rs, r)
	}
	for i, code := range map[int]float64{0: -32700, 1: -32002, 7: -32602, 8: -32601} {
		if rs[i]["error"].(map[string]any)["code"] != code {
			t.Fatal(rs[i])
		}
	}
	if rs[2]["id"] != "init" {
		t.Fatal("ID not preserved")
	}
	if len(rs[3]["result"].(map[string]any)["tools"].([]any)) != 8 {
		t.Fatal("tool discovery")
	}
	for _, i := range []int{5, 6} {
		if rs[i]["result"].(map[string]any)["isError"] != true {
			t.Fatal(rs[i])
		}
	}
	if rs[4]["result"].(map[string]any)["isError"] != false {
		t.Fatal(rs[4])
	}
}
func TestCSVFailures(t *testing.T) {
	dir := t.TempDir()
	p := filepath.Join(dir, "bad.csv")
	if e := os.WriteFile(p, []byte("a,b\n1\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := readCSV(p, func(map[string]string) error { return nil }); e == nil || !strings.Contains(e.Error(), "row 2") {
		t.Fatalf("missing row context: %v", e)
	}
	if _, e := LoadGraph(dir); e == nil {
		t.Fatal("missing files ignored")
	}
}
func BenchmarkAggregate(b *testing.B) {
	g, e := LoadGraph("data/kaggle")
	if e != nil {
		b.Fatal(e)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = g.Call("statistics", Query{})
	}
}

func TestCrossFileReconciliationAndUnknownResults(t *testing.T) {
	dir := t.TempDir()
	files := map[string]string{
		"Brasileirao_Matches.csv":        "datetime,home_team,away_team,home_goal,away_goal,season,round\n2021-01-10 21:00:00,Flamengo-RJ,Palmeiras-SP,2,1,2020,28\n2021-01-15,Palmeiras-SP,Flamengo-RJ,NA,NA,2020,29\n",
		"Brazilian_Cup_Matches.csv":      "datetime,home_team,away_team,home_goal,away_goal,season,round\n2020-12-01,Flamengo - RJ,Palmeiras - SP,1,0,2020,8\n",
		"Libertadores_Matches.csv":       "datetime,home_team,away_team,home_goal,away_goal,season,stage\nNA,Flamengo,Palmeiras,-,-,NA,final\n",
		"BR-Football-Dataset.csv":        "date,tournament,home,away,home_goal,away_goal,home_corner\n2021-01-11,Serie A,Flamengo,Palmeiras,2.0,1.0,7.0\n2021-01-12,Serie A,Flamengo,Palmeiras,3.0,0.0,4.0\n",
		"novo_campeonato_brasileiro.csv": "Data,Ano,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Arena\n10/01/2021,2020,Flamengo-RJ,Palmeiras,2,1,RJ,SP,Maracana\n",
		"fifa_data.csv":                  "ID,Name,Nationality,Club,Overall,Potential,Position\n1,Example,Brazil,Flamengo,80,85,ST\n",
	}
	for name, body := range files {
		if e := os.WriteFile(filepath.Join(dir, name), []byte(body), 0600); e != nil {
			t.Fatal(e)
		}
	}
	g, e := LoadGraph(dir)
	if e != nil {
		t.Fatal(e)
	}
	if len(g.Matches) != 5 {
		t.Fatalf("got %d matches; duplicate reconciliation failed", len(g.Matches))
	}
	ms := g.FindMatches(Query{Competition: "Serie A", Season: 2020})
	if len(ms) != 2 {
		t.Fatal("explicit season not retained")
	}
	r := recordFor(ms, "Flamengo", "")
	if r.Played != 1 || r.Points != 3 || r.GoalsFor != 2 {
		t.Fatal(r)
	}
	var merged *Match
	for _, m := range ms {
		if completed(m) {
			merged = m
		}
	}
	if len(merged.Sources) != 3 || merged.Stadium != "Maracana" || merged.Attributes["BR-Football-Dataset.csv"]["home_corner"] != "7.0" {
		t.Fatalf("lost enrichment: %+v", merged)
	}
	if len(g.FindMatches(Query{To: "2022-01-01"})) != 4 {
		t.Fatal("unknown date matched date range")
	}
	v, e := g.Call("team_profile", Query{Team: "Flamengo"})
	if e != nil {
		t.Fatal(e)
	}
	players := v.(map[string]any)["players"].(map[string]any)
	if players["total"] != 1 {
		t.Fatal("player-match traversal failed")
	}
}
func TestPandemicSeasonAndStandingsTotals(t *testing.T) {
	g := dataset(t)
	for _, year := range []int{2018, 2019, 2020, 2021, 2022} {
		ms := g.FindMatches(Query{Competition: "Serie A", Season: year})
		rs := records(ms, "")
		if len(rs) != 20 || len(ms) != 380 {
			t.Errorf("%d: %d teams / %d matches", year, len(rs), len(ms))
		}
		for _, r := range rs {
			if r.Played > 38 {
				t.Errorf("%d duplicate fixtures for %s: %d", year, r.Team, r.Played)
			}
		}
	}
}
