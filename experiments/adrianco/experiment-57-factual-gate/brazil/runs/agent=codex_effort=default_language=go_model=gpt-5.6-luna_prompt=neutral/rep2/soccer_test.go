package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func testStore() *Store {
	return &Store{Matches: []Match{{Competition: "Brasileirão", Home: "Flamengo-RJ", Away: "Fluminense-RJ", Date: "2023-09-03", Season: 2023, HomeGoals: 2, AwayGoals: 1}, {Competition: "Brasileirão", Home: "Fluminense-RJ", Away: "Flamengo-RJ", Date: "2023-05-28", Season: 2023, HomeGoals: 1, AwayGoals: 0}, {Competition: "Copa do Brasil", Home: "Flamengo", Away: "Santos", Date: "2022-01-01", Season: 2022, HomeGoals: 0, AwayGoals: 0}}, Players: []Player{{Name: "Neymar Jr", Nationality: "Brazil", Club: "Paris Saint-Germain", Position: "LW", Overall: 92}, {Name: "Alisson", Nationality: "Brazil", Club: "Liverpool", Position: "GK", Overall: 89}}}
}
func TestSearchAndStats(t *testing.T) {
	s := testStore()
	got := s.SearchMatches("Flamengo", "Brasileirão", "", "", 2023, 0)
	if len(got) != 2 {
		t.Fatalf("matches=%d", len(got))
	}
	st := s.Stats("Flamengo", "Brasileirão", 2023, false, false)
	if st.Wins != 1 || st.Losses != 1 || st.GoalsFor != 2 {
		t.Fatalf("stats=%+v", st)
	}
}
func TestPlayersAndAverage(t *testing.T) {
	s := testStore()
	p := s.SearchPlayers("", "Brazil", "", "", 90, 0)
	if len(p) != 1 || p[0].Name != "Neymar Jr" {
		t.Fatalf("players=%+v", p)
	}
	a := s.Average("Brasileirão", 2023)
	if a["matches"] != 2 || a["goals"] != 4 {
		t.Fatalf("average=%v", a)
	}
	table := s.Standings("Brasileirão", 2023)
	if len(table) != 2 || table[0].Team != "Flamengo-RJ" || table[0].Points != 3 {
		t.Fatalf("standings=%+v", table)
	}
}

func TestHeadToHead(t *testing.T) {
	h := testStore().HeadToHead("Flamengo", "Fluminense", "Brasileirão", 2023)
	if h.Matches != 2 || h.AWins != 1 || h.BWins != 1 || h.Draws != 0 {
		t.Fatalf("head-to-head=%+v", h)
	}
}

func TestLoadStoreDeduplicatesOverlappingFixtures(t *testing.T) {
	got := deduplicateMatches([]Match{
		{Competition: "Brasileirão", Home: "Palmeiras-SP", Away: "Santos-SP", Date: "2019-01-01", Season: 2019, HomeGoals: 2, AwayGoals: 0},
		{Competition: "Brasileiro", Home: "Palmeiras", Away: "Santos", Date: "2019-01-01", HomeGoals: 2, AwayGoals: 0},
	})
	if len(got) != 1 || got[0].Season != 2019 {
		t.Fatalf("deduplicated matches=%+v", got)
	}
}
func TestMCPProtocol(t *testing.T) {
	s := testStore()
	in := strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"tools/list"}` + "\n" + `{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"team_stats","arguments":{"team":"Flamengo","season":2023}}}` + "\n")
	var out bytes.Buffer
	if err := Serve(in, &out, s); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("responses=%d", len(lines))
	}
	var r map[string]any
	if err := json.Unmarshal([]byte(lines[1]), &r); err != nil {
		t.Fatal(err)
	}
	if r["result"] == nil {
		t.Fatalf("missing result: %s", lines[1])
	}
}
