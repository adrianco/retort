package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func ptr(n int) *int { return &n }
func fixture() *Store {
	return &Store{Matches: []Match{
		{ID: "1", Date: "2023-09-03", Competition: "Brasileirão", Season: 2023, Home: "flamengo", Away: "fluminense", HomeGoals: ptr(2), AwayGoals: ptr(1)},
		{ID: "2", Date: "2023-05-28", Competition: "Brasileirão", Season: 2023, Home: "fluminense", Away: "flamengo", HomeGoals: ptr(0), AwayGoals: ptr(0)},
		{ID: "3", Date: "2022-06-01", Competition: "Copa do Brasil", Season: 2022, Home: "palmeiras", Away: "flamengo", HomeGoals: ptr(3), AwayGoals: ptr(0), Stage: "semifinals"},
		{ID: "4", Date: "2022-07-01", Competition: "Copa do Brasil", Season: 2022, Home: "palmeiras", Away: "flamengo", Stage: "final"},
	}, Players: []Player{{ID: "1", Name: "José Silva", Nationality: "Brazil", Club: "flamengo", Position: "ST", Overall: 85}, {ID: "2", Name: "Other", Nationality: "Argentina", Club: "palmeiras", Position: "GK", Overall: 80}}}
}
func TestGivenMatchesWhenSearchingThenCriteriaHold(t *testing.T) {
	s := fixture()
	cases := []struct {
		name string
		q    Query
		want int
	}{
		{"either direction", Query{Team: "Clube de Regatas do Flamengo", Opponent: "Fluminense-RJ"}, 2},
		{"home only", Query{Team: "Flamengo", Venue: "home"}, 1},
		{"away only", Query{Team: "Flamengo", Venue: "away"}, 3},
		{"season", Query{Team: "Flamengo", Season: 2023}, 2},
		{"inclusive dates", Query{From: "2023-05-28", To: "2023-05-28"}, 1},
		{"competition alias", Query{Competition: "Serie A"}, 2},
		{"exact final", Query{Stage: "final"}, 1},
		{"derbies", Query{Derbies: true}, 2},
		{"no invented results", Query{Team: "unknown"}, 0},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := len(s.matches(c.q)); got != c.want {
				t.Fatalf("got %d want %d", got, c.want)
			}
		})
	}
}
func TestGivenResultsWhenAggregatingThenRecordsAreCorrect(t *testing.T) {
	rs := records(fixture().Matches, "")
	for _, r := range rs {
		if r.Team == "flamengo" {
			if r.Played != 3 || r.Wins != 1 || r.Draws != 1 || r.Losses != 1 || r.GoalsFor != 2 || r.GoalsAgainst != 4 || r.Points != 4 {
				t.Fatalf("bad record: %+v", r)
			}
		}
	}
	home := records(fixture().Matches, "home")
	if len(home) != 3 {
		t.Fatal(home)
	}
	sum := summary(fixture().Matches)
	if sum["played"] != 3 || sum["goals"] != 6 || sum["average_goals"] != 2.0 {
		t.Fatal(sum)
	}
	if summary(nil)["average_goals"] != 0.0 {
		t.Fatal("empty average")
	}
}
func TestNormalizationAndDates(t *testing.T) {
	for in, want := range map[string]string{"São Paulo-SP": "sao paulo", "São Paulo FC": "sao paulo", "Grêmio-RS": "gremio", "São Paulo": "sao paulo", "Sport Club Corinthians Paulista": "corinthians", "Athletico-PR": "atletico pr", "América - MG": "america mg", "América-RN": "america rn"} {
		if got := team(in); got != want {
			t.Errorf("%s: %s != %s", in, got, want)
		}
	}
	for _, v := range []string{"2003-03-29", "29/03/2003", "2003-03-29 18:30:00", "2003-03-29T18:30:00Z"} {
		if got, e := date(v); e != nil || got != "2003-03-29" {
			t.Fatalf("%s %s %v", v, got, e)
		}
	}
	if _, e := date("2023-02-30"); e == nil {
		t.Fatal("invalid date accepted")
	}
}
func TestGivenPlayersWhenFilteringThenAttributesMatch(t *testing.T) {
	s := fixture()
	ps := s.players(Query{Name: "Jose", Nationality: "Brazil", Club: "Flamengo-RJ", Position: "forward", MinRating: 85})
	if len(ps) != 1 || ps[0].ID != "1" {
		t.Fatal(ps)
	}
	if len(s.players(Query{MinRating: 90})) != 0 {
		t.Fatal("rating")
	}
}
func TestValidationAndPagination(t *testing.T) {
	for _, q := range []Query{{Limit: 501}, {Offset: -1}, {From: "2023-02-30"}, {From: "2023-02-01", To: "2022-01-01"}, {Venue: "side"}, {Source: "fake"}, {Sort: "fake"}, {GroupBy: "fake"}} {
		if q.validate() == nil {
			t.Fatalf("accepted %+v", q)
		}
	}
	a, b := window(10, Query{Offset: 100})
	if a != 10 || b != 10 {
		t.Fatal(a, b)
	}
	for name, q := range map[string]Query{"head_to_head": {Team: "Flamengo", Opponent: "Flamengo-RJ"}, "team_profile": {}, "standings": {Competition: "Libertadores", Season: 2023}, "competition_results": {}} {
		if _, e := fixture().Call(name, q); e == nil {
			t.Fatal(name)
		}
	}
}
func TestMCPTransport(t *testing.T) {
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team":"Flamengo","opponent":"Fluminense"}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_matches","arguments":{"limit":-1}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"fake"}}`,
		`{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"search_matches","arguments":{"limit":"bad"}}}`,
		`{"jsonrpc":"2.0","id":7,"method":"ping"}`,
		`{"jsonrpc":"2.0","id":8,"method":"fake"}`,
		`bad json`,
		`[]`,
	}, "\n") + "\n"
	var out bytes.Buffer
	if e := Serve(strings.NewReader(input), &out, fixture()); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 11 {
		t.Fatalf("%d responses: %s", len(lines), out.String())
	}
	var responses []map[string]any
	for _, line := range lines {
		var r map[string]any
		if e := json.Unmarshal([]byte(line), &r); e != nil {
			t.Fatal(e)
		}
		responses = append(responses, r)
	}
	for _, i := range []int{0, 5, 8, 9, 10} {
		if responses[i]["error"] == nil {
			t.Errorf("response %d has no error", i)
		}
	}
	if responses[3]["result"].(map[string]any)["isError"] != false {
		t.Fatal(responses[3])
	}
	if responses[4]["result"].(map[string]any)["isError"] != true {
		t.Fatal(responses[4])
	}
	if responses[6]["result"].(map[string]any)["isError"] != true {
		t.Fatal(responses[6])
	}
	if len(responses[2]["result"].(map[string]any)["tools"].([]any)) != 8 {
		t.Fatal("tools missing")
	}
}
func TestAllDatasetsAndTwentySampleQuestions(t *testing.T) {
	start := time.Now()
	s, e := Load("data/kaggle")
	if e != nil {
		t.Fatal(e)
	}
	t.Logf("loaded in %s: %d matches, %d players, %d warnings", time.Since(start), len(s.Matches), len(s.Players), len(s.Warnings))
	want := map[string]int{"Brasileirao_Matches.csv": 4180, "Brazilian_Cup_Matches.csv": 1337, "Libertadores_Matches.csv": 1255, "BR-Football-Dataset.csv": 10296, "novo_campeonato_brasileiro.csv": 6886, "fifa_data.csv": 18207}
	for fn, n := range want {
		if s.Counts[fn] != n {
			t.Errorf("%s: %d != %d", fn, s.Counts[fn], n)
		}
	}
	seen := map[string]bool{}
	merged := 0
	for _, m := range s.Matches {
		k := m.Date + m.Competition + m.Home + m.Away
		if seen[k] {
			t.Fatal("duplicate", k)
		}
		seen[k] = true
		if len(m.Sources) > 1 {
			merged++
		}
	}
	if merged == 0 {
		t.Fatal("no cross-source merging")
	}
	cases := []struct {
		question, tool string
		q              Query
	}{
		{"Show Flamengo vs Fluminense", "search_matches", Query{Team: "Flamengo", Opponent: "Fluminense"}},
		{"Palmeiras in 2023", "search_matches", Query{Team: "Palmeiras", Season: 2023}},
		{"Cup finals", "search_matches", Query{Competition: "Copa do Brasil", Stage: "final"}},
		{"Corinthians home record 2022", "team_profile", Query{Team: "Corinthians", Venue: "home", Season: 2022}},
		{"Most goals in Serie A 2023", "standings", Query{Competition: "Serie A", Season: 2023, Sort: "goals"}},
		{"Palmeiras Santos head to head", "head_to_head", Query{Team: "Palmeiras", Opponent: "Santos"}},
		{"Brazilian players", "search_players", Query{Nationality: "Brazil"}},
		{"Highest rated at Flamengo", "search_players", Query{Club: "Flamengo"}},
		{"Sao Paulo forwards", "search_players", Query{Club: "São Paulo FC", Position: "forward"}},
		{"2019 league table", "standings", Query{Competition: "Brasileirão", Season: 2019}},
		{"2018 Libertadores fixtures", "competition_results", Query{Competition: "Libertadores", Season: 2018}},
		{"2020 relegation candidates", "standings", Query{Competition: "Brasileirão", Season: 2020}},
		{"Average league goals", "statistics", Query{Competition: "Brasileirão"}},
		{"Best away record", "statistics", Query{Venue: "away", Sort: "win_rate"}},
		{"Biggest wins", "search_matches", Query{Sort: "biggest_win"}},
		{"Last Flamengo Corinthians score", "search_matches", Query{Team: "Flamengo", Opponent: "Corinthians", Limit: 1}},
		{"Find Gabriel", "search_players", Query{Name: "Gabriel"}},
		{"Flamengo player and match relationships", "team_profile", Query{Team: "Flamengo"}},
		{"2023 derbies", "search_matches", Query{Season: 2023, Derbies: true}},
		{"Palmeiras competition appearances", "team_profile", Query{Team: "Palmeiras"}},
		{"Best home record", "statistics", Query{Venue: "home", Sort: "win_rate"}},
		{"Top Brazilian players", "search_players", Query{Nationality: "Brazil", MinRating: 85}},
		{"Compare 2018 and 2019", "statistics", Query{From: "2018-01-01", To: "2019-12-31", GroupBy: "season"}},
		{"Coverage", "data_info", Query{}},
	}
	for _, c := range cases {
		t.Run(c.question, func(t *testing.T) {
			start := time.Now()
			v, e := s.Call(c.tool, c.q)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = json.Marshal(v); e != nil {
				t.Fatal(e)
			}
			if time.Since(start) > 2*time.Second {
				t.Fatal("query exceeded 2 seconds")
			}
		})
	}
	for _, fn := range files[:5] {
		if len(s.matches(Query{Source: fn})) == 0 {
			t.Fatal("unqueryable source", fn)
		}
	}
	// Regression: different source dates must not inflate the round-robin table.
	table := records(s.matches(Query{Competition: "Serie A", Season: 2019}), "")
	if len(table) != 20 || table[0].Team != "flamengo" || table[0].Points != 90 || table[0].Played != 38 || table[1].Team != "santos" || table[1].Points != 74 || table[2].Team != "palmeiras" || table[2].Points != 74 {
		t.Fatalf("incorrect 2019 standings: %+v", table)
	}
	for _, r := range table {
		if r.Played != 38 {
			t.Fatalf("duplicate or missing league fixtures: %+v", r)
		}
	}
	profile, e := s.Call("team_profile", Query{Team: "Fluminense", Season: 2019})
	if e != nil {
		t.Fatal(e)
	}
	if profile.(map[string]any)["match_total"].(int) == 0 || profile.(map[string]any)["player_total"].(int) == 0 {
		t.Fatal("missing cross-file relationships")
	}
	if len(s.players(Query{Club: "Flamengo"})) != 0 {
		t.Fatal("invented Flamengo roster")
	}
	for _, m := range s.matches(Query{Competition: "Serie A", From: "2021-01-01", To: "2021-02-28"}) {
		if m.Season != 2020 {
			t.Fatalf("calendar year mistaken for season: %+v", m)
		}
	}
	finals := s.matches(Query{Competition: "Copa do Brasil", Stage: "final"})
	if len(finals) == 0 {
		t.Fatal("no finals")
	}
	for _, m := range finals {
		if m.Stage != "final" {
			t.Fatal(m)
		}
	}
}
func TestLoaderRejectsMissingFilesAndColumns(t *testing.T) {
	dir := t.TempDir()
	if _, e := Load(dir); e == nil {
		t.Fatal("missing files accepted")
	}
	if e := os.WriteFile(filepath.Join(dir, files[0]), []byte("datetime\n2023-01-01\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e := Load(dir); e == nil || !strings.Contains(e.Error(), "missing column") {
		t.Fatal(e)
	}
}
