package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func ptr(n int) *int { return &n }
func fixture() *Graph {
	return &Graph{Matches: []Match{
		{ID: "1", Date: "2023-01-01", Home: "flamengo", Away: "fluminense", HomeGoals: ptr(2), AwayGoals: ptr(1), Competition: "Brasileirão", Season: 2023},
		{ID: "2", Date: "2023-02-01", Home: "fluminense", Away: "flamengo", HomeGoals: ptr(0), AwayGoals: ptr(0), Competition: "Brasileirão", Season: 2023},
		{ID: "3", Date: "2023-03-01", Home: "palmeiras", Away: "flamengo", HomeGoals: ptr(3), AwayGoals: ptr(0), Competition: "Copa do Brasil", Season: 2023, Stage: "final"},
		{ID: "4", Date: "2024-01-01", Home: "flamengo", Away: "palmeiras", Competition: "Brasileirão", Season: 2024},
	}, Players: []Player{{ID: "1", Name: "José", Club: "flamengo", Nationality: "Brazil", Overall: 90, Position: "ST"}}}
}
func TestNormalization(t *testing.T) {
	for input, want := range map[string]string{"Flamengo-RJ": "flamengo", "São Paulo FC": "sao paulo", "Sport Club Corinthians Paulista": "corinthians", "Grêmio-RS": "gremio"} {
		if got := team(input); got != want {
			t.Errorf("%s: %s != %s", input, got, want)
		}
	}
	for _, s := range []string{"2023-09-24", "24/09/2023", "2023-09-24 18:30:00"} {
		if d, e := parseDate(s); e != nil || d != "2023-09-24" {
			t.Fatal(s, d, e)
		}
	}
	if _, e := parseDate("2023-02-30"); e == nil {
		t.Fatal("invalid date accepted")
	}
	if score("1.0") == nil || *score("1.0") != 1 || score("NaN") != nil || score("-1") != nil {
		t.Fatal("score parsing")
	}
}
func TestMatchFilters(t *testing.T) {
	g := fixture()
	for _, tc := range []struct {
		f Filter
		n int
	}{{Filter{Team: "Flamengo-RJ", Opponent: "Fluminense"}, 2}, {Filter{Team: "flamengo", Venue: "home", Season: 2023}, 1}, {Filter{Team: "flamengo", Venue: "away"}, 2}, {Filter{From: "2023-02-01", To: "2023-03-01"}, 2}, {Filter{Competition: "Copa do Brasil", Stage: "final"}, 1}, {Filter{Derbies: true}, 2}} {
		if got := len(g.matches(tc.f)); got != tc.n {
			t.Errorf("%+v got %d", tc.f, got)
		}
	}
	m := g.matches(Filter{Sort: "biggest_win"})
	if m[0].ID != "3" {
		t.Fatal(m)
	}
	if len(page(m, Filter{Offset: 100})) != 0 {
		t.Fatal("pagination")
	}
}
func TestStatistics(t *testing.T) {
	g := fixture()
	v, e := g.Query("head_to_head", Filter{Team: "flamengo", Opponent: "fluminense"})
	if e != nil {
		t.Fatal(e)
	}
	r := v.(map[string]any)["record"].(Record)
	if r.Played != 2 || r.Wins != 1 || r.Draws != 1 || r.Points != 4 || r.GoalsFor != 2 || r.GoalsAgainst != 1 || r.WinRate != 50 {
		t.Fatal(r)
	}
	v, e = g.Query("statistics", Filter{})
	if e != nil {
		t.Fatal(e)
	}
	s := v.(map[string]any)
	if s["played"] != 3 || s["average_goals"] != float64(2) {
		t.Fatal(s)
	}
	v, e = g.Query("standings", Filter{Competition: "Serie A", Season: 2023})
	if e != nil {
		t.Fatal(e)
	}
	rs := v.(map[string]any)["standings"].([]Record)
	if rs[0].Team != "flamengo" || rs[0].Points != 4 {
		t.Fatal(rs)
	}
	if _, e = g.Query("standings", Filter{Competition: "Copa do Brasil", Season: 2023}); e == nil {
		t.Fatal("cup league table accepted")
	}
	ps := g.players(Filter{Name: "jose", Nationality: "Brazil", Club: "Flamengo-RJ", Position: "forwards"})
	if len(ps) != 1 {
		t.Fatal(ps)
	}
}
func TestRealDatasets(t *testing.T) {
	start := time.Now()
	g, e := Load("data/kaggle")
	if e != nil {
		t.Fatal(e)
	}
	for name, n := range g.Sources {
		if n == 0 {
			t.Fatal(name)
		}
		if name != "fifa_data.csv" && len(g.matches(Filter{Source: name})) == 0 {
			t.Fatal("source not queryable", name)
		}
	}
	if len(g.Sources) != 6 || len(g.Players) != 18207 {
		t.Fatal(g.Sources, len(g.Players))
	}
	t.Logf("Loaded %d unique matches and %d players in %s; %d conflicts", len(g.Matches), len(g.Players), time.Since(start), len(g.Warnings))
	cases := []struct {
		name string
		f    Filter
	}{
		{"search_matches", Filter{Team: "Flamengo", Opponent: "Fluminense"}},
		{"search_matches", Filter{Team: "Palmeiras", Season: 2023}},
		{"search_matches", Filter{Competition: "Copa do Brasil", Round: "final"}},
		{"team_info", Filter{Team: "Corinthians", Venue: "home", Season: 2022}},
		{"statistics", Filter{Competition: "Serie A", Season: 2023, Sort: "goals"}},
		{"head_to_head", Filter{Team: "Palmeiras", Opponent: "Santos"}},
		{"search_players", Filter{Nationality: "Brazil"}},
		{"search_players", Filter{Club: "Flamengo"}},
		{"search_players", Filter{Club: "São Paulo FC", Position: "forwards"}},
		{"standings", Filter{Competition: "Brasileirão", Season: 2019}},
		{"search_matches", Filter{Competition: "Libertadores", Season: 2018}},
		{"standings", Filter{Competition: "Brasileirão", Season: 2020}},
		{"statistics", Filter{Competition: "Brasileirão"}},
		{"statistics", Filter{Venue: "away"}},
		{"search_matches", Filter{Sort: "biggest_win"}},
		{"search_matches", Filter{Team: "Flamengo", Opponent: "Corinthians", Limit: 1}},
		{"search_players", Filter{Name: "Gabriel Barbosa"}},
		{"search_matches", Filter{Derbies: true, Season: 2023}},
		{"team_info", Filter{Team: "Palmeiras"}},
		{"statistics", Filter{Venue: "home"}},
		{"statistics", Filter{From: "2018-01-01", To: "2019-12-31"}},
	}
	for _, tc := range cases {
		start = time.Now()
		v, e := g.Query(tc.name, tc.f)
		if e != nil {
			t.Fatal(tc, e)
		}
		if _, e = json.Marshal(v); e != nil {
			t.Fatal(e)
		}
		if time.Since(start) > 2*time.Second {
			t.Fatal("slow query", tc)
		}
	}
	// The overlapping 2019 sources must still produce the known complete 380-game season.
	ms := g.matches(Filter{Competition: "Brasileirão", Season: 2019})
	t.Logf("2019 matches: %d", len(ms))
	rs := records(ms, "")
	if len(rs) == 0 || rs[0].Team != "flamengo" || rs[0].Points != 90 {
		t.Fatalf("2019 leader: %+v", rs)
	}
}
func TestProtocol(t *testing.T) {
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team":"flamengo","opponent":"fluminense"}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_matches","arguments":{"limit":-1}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"bogus"}`,
		`{broken`,
	}, "\n")
	var out bytes.Buffer
	if e := Serve(fixture(), strings.NewReader(input), &out); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 6 {
		t.Fatal(out.String())
	}
	for i, line := range lines {
		var v map[string]any
		if e := json.Unmarshal([]byte(line), &v); e != nil {
			t.Fatal(e)
		}
		if i == 2 && v["result"].(map[string]any)["isError"] != false {
			t.Fatal(v)
		}
		if i == 3 && v["result"].(map[string]any)["isError"] != true {
			t.Fatal(v)
		}
		if i >= 4 && v["error"] == nil {
			t.Fatal(v)
		}
	}
}

func TestValidationAndEmptyResults(t *testing.T) {
	g := fixture()
	for _, f := range []Filter{{Venue: "sideways"}, {Limit: 1001}, {Offset: -1}, {From: "yesterday"}, {From: "2024-01-01", To: "2023-01-01"}} {
		if _, e := g.Query("search_matches", f); e == nil {
			t.Fatalf("accepted %+v", f)
		}
	}
	v, e := g.Query("statistics", Filter{Team: "no such team"})
	if e != nil {
		t.Fatal(e)
	}
	if v.(map[string]any)["average_goals"] != float64(0) {
		t.Fatal(v)
	}
	if _, e := Load(t.TempDir()); e == nil {
		t.Fatal("missing sources accepted")
	}
}

func TestSourceProvenance(t *testing.T) {
	g, e := Load("data/kaggle")
	if e != nil {
		t.Fatal(e)
	}
	sum := 0
	for _, n := range g.Sources {
		sum += n
	}
	records := len(g.Players)
	merged := false
	unknown := false
	for _, m := range g.Matches {
		records += len(m.Records)
		if len(m.Sources) > 1 {
			merged = true
		}
		if m.Date == "" {
			unknown = true
		}
		if len(m.Sources) != len(m.Records) {
			t.Fatal("lost provenance")
		}
	}
	if records != sum || !merged || !unknown {
		t.Fatalf("records=%d source rows=%d merged=%v unknown=%v", records, sum, merged, unknown)
	}
}
