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
	testDB   *DB
	loadOnce sync.Once
	loadErr  error
)

func db(t *testing.T) *DB {
	t.Helper()
	loadOnce.Do(func() { testDB, loadErr = LoadDB("data/kaggle") })
	if loadErr != nil {
		t.Fatalf("load: %v", loadErr)
	}
	return testDB
}

func call(t *testing.T, tool string, args Args) string {
	t.Helper()
	s := &Server{DB: db(t)}
	start := time.Now()
	out, err := s.Call(tool, args)
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

func TestTeamKeyNormalization(t *testing.T) {
	groups := [][]string{
		{"Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "palmeiras", "SE Palmeiras"},
		{"São Paulo", "Sao Paulo-SP", "Sao Paulo", "São Paulo FC"},
		{"Grêmio", "Gremio-RS", "Gremio RS", "Grêmio - RS"},
		{"Atlético-MG", "Atletico Mineiro", "Atlético - MG", "Atletico-MG"},
		{"Athletico-PR", "Atletico-PR", "Atlético Paranaense - PR", "Atletico Paranaense", "Atlético Paranaense"},
		{"Vasco da Gama-RJ", "Vasco", "Vasco Da Gama RJ"},
		{"Red Bull Bragantino-SP", "Bragantino", "RB Bragantino"},
		{"Sport Club Corinthians Paulista", "Corinthians-SP", "Corinthians"},
		{"Juventude", "EC Juventude", "Juventude-RS"},
	}
	for _, g := range groups {
		want := TeamKey(g[0])
		for _, n := range g[1:] {
			if got := TeamKey(n); got != want {
				t.Errorf("TeamKey(%q)=%q, want %q (as %q)", n, got, want, g[0])
			}
		}
	}
	if TeamKey("Atlético-GO") == TeamKey("Atlético-MG") {
		t.Error("Atlético-GO and Atlético-MG must differ")
	}
	if TeamKey("Botafogo-SP") == TeamKey("Botafogo-RJ") {
		t.Error("Botafogo-SP and Botafogo-RJ must differ")
	}
}

func TestParseDate(t *testing.T) {
	for _, s := range []string{"2023-09-24", "29/03/2003", "2012-05-19 18:30:00"} {
		if _, err := ParseDate(s); err != nil {
			t.Errorf("ParseDate(%q): %v", s, err)
		}
	}
	d, _ := ParseDate("29/03/2003")
	if d.Day() != 29 || d.Month() != 3 || d.Year() != 2003 {
		t.Errorf("bad Brazilian date: %v", d)
	}
}

func TestAllFilesLoaded(t *testing.T) {
	d := db(t)
	want := map[string]int{SrcBrasileirao: 4000, SrcCup: 1300, SrcLib: 1200, SrcBRFootball: 10000, SrcHistorical: 6800, SrcFIFA: 18000}
	for f, n := range want {
		if d.Counts[f] < n {
			t.Errorf("%s: loaded %d, want >= %d", f, d.Counts[f], n)
		}
	}
	// UTF-8 handled
	if d.Name(TeamKey("Gremio")) != "Grêmio" {
		t.Errorf("display name %q", d.Name("gremio"))
	}
}

func TestStandings2019(t *testing.T) {
	out := call(t, "standings", Args{"season": 2019.0, "limit": 3.0})
	mustContain(t, out, "1. Flamengo - 90 pts (28W, 6D, 4L", "Champion", "Santos - 74 pts", "Palmeiras - 74 pts")
}

func TestRelegated2020(t *testing.T) {
	out := call(t, "standings", Args{"season": 2020.0})
	mustContain(t, out, "Botafogo - 27 pts", "Relegated")
	if strings.Count(out, "Relegated") != 4 {
		t.Errorf("expected 4 relegated teams:\n%s", out)
	}
}

func TestStandingsHistorical(t *testing.T) {
	// 2003-2011 only from novo_campeonato_brasileiro.csv
	out := call(t, "standings", Args{"season": 2003.0, "limit": 1.0})
	mustContain(t, out, "1. Cruzeiro", "Champion")
}

func TestCorinthiansHome2022(t *testing.T) {
	out := call(t, "team_record", Args{"team": "Corinthians", "season": 2022.0, "venue": "home", "competition": "Brasileirão"})
	mustContain(t, out, "Matches: 19", "Win rate:")
}

func TestFlaFlu(t *testing.T) {
	out := call(t, "head_to_head", Args{"team1": "Flamengo", "team2": "Fluminense"})
	mustContain(t, out, "Fla-Flu", "Head-to-head in dataset", "Flamengo", "wins", "draws")
	h, _ := db(t).HeadToHead("Flamengo", "Fluminense", "")
	if len(h.Matches) < 30 || h.AWins+h.BWins+h.Draws != len(h.Matches) {
		t.Errorf("bad h2h: %+v", h)
	}
	// all match datasets contribute
	srcs := map[string]bool{}
	for _, m := range h.Matches {
		srcs[m.Source] = true
	}
	if len(srcs) < 3 {
		t.Errorf("h2h used only sources %v", srcs)
	}
}

func TestPalmeiras2023Matches(t *testing.T) {
	out := call(t, "search_matches", Args{"team": "Palmeiras", "season": 2023.0})
	mustContain(t, out, "Palmeiras", "2023-")
	ms, _ := db(t).Filter(MatchFilter{Team: "Palmeiras", Season: 2023})
	for _, m := range ms {
		if m.Season != 2023 || (m.HomeKey != "palmeiras" && m.AwayKey != "palmeiras") {
			t.Fatalf("bad match %s", FormatMatch(m))
		}
	}
}

func TestDateRange(t *testing.T) {
	ms, err := db(t).Filter(MatchFilter{Team: "Santos", From: mustDate("2015-01-01"), To: mustDate("31/03/2015")})
	if err != nil || len(ms) == 0 {
		t.Fatalf("no matches: %v", err)
	}
	for _, m := range ms {
		if m.Date.Year() != 2015 || m.Date.Month() > 3 {
			t.Errorf("out of range: %s", FormatMatch(m))
		}
	}
}

func TestCupFinals(t *testing.T) {
	out := call(t, "search_matches", Args{"competition": "Copa do Brasil", "stage": "final"})
	mustContain(t, out, "Palmeiras 2-0 Grêmio", "Copa do Brasil Round 8")
	out = call(t, "search_matches", Args{"competition": "Libertadores", "stage": "final", "season": 2018.0})
	mustContain(t, out, "River Plate", "Boca Juniors", "final")
}

func TestLastFlamengoCorinthians(t *testing.T) {
	ms, _ := db(t).Filter(MatchFilter{Team: "Flamengo", Opponent: "Corinthians"})
	if len(ms) == 0 {
		t.Fatal("none")
	}
	out := call(t, "search_matches", Args{"team": "Flamengo", "opponent": "Corinthians", "limit": 1.0})
	mustContain(t, out, FormatMatch(ms[len(ms)-1]))
}

func TestPlayers(t *testing.T) {
	out := call(t, "search_players", Args{"nationality": "Brazil", "limit": 3.0})
	mustContain(t, out, "1. Neymar Jr - Overall: 92", "Position: LW", "Paris Saint-Germain")
	out = call(t, "search_players", Args{"name": "neymar"})
	mustContain(t, out, "Neymar Jr")
	out = call(t, "search_players", Args{"club": "Santos", "limit": 50.0})
	if strings.Contains(out, "Santos Laguna") {
		t.Error("club filter matched Santos Laguna")
	}
	out = call(t, "search_players", Args{"club": "Grêmio", "position": "forward"})
	mustContain(t, out, "Club: Grêmio")
	for _, l := range strings.Split(out, "\n")[1:] {
		if l != "" && !strings.Contains(l, "Position: ") {
			continue
		}
		if strings.Contains(l, "Position: GK") || strings.Contains(l, "Position: CB") {
			t.Errorf("non-forward: %s", l)
		}
	}
	out = call(t, "players_by_club", Args{})
	mustContain(t, out, "Grêmio: 20 players", "avg rating")
	if strings.Contains(out, "Boavista FC") {
		t.Error("Portuguese Boavista counted as Brazilian club")
	}
}

func TestStatsAndRankings(t *testing.T) {
	out := call(t, "competition_stats", Args{"competition": "Brasileirão"})
	mustContain(t, out, "Average goals per match: 2.", "Home win rate")
	out = call(t, "competition_stats", Args{"competition": "Brasileirão", "compare_seasons": "2018,2019"})
	mustContain(t, out, "2018 Brasileirão", "2019 Brasileirão", "champion: Palmeiras", "champion: Flamengo")
	out = call(t, "rank_teams", Args{"venue": "home", "competition": "Brasileirão", "min_matches": 50.0})
	mustContain(t, out, "1. ", "home matches")
	out = call(t, "rank_teams", Args{"metric": "goals_for", "season": 2023.0, "competition": "Serie A", "limit": 1.0})
	mustContain(t, out, "1. ")
	out = call(t, "biggest_wins", Args{"competition": "Brasileirão", "limit": 5.0})
	mustContain(t, out, "1. ")
}

func TestDerbiesAndOverview(t *testing.T) {
	out := call(t, "derbies", Args{"season": 2023.0})
	mustContain(t, out, "Fla-Flu", "Derby matches")
	out = call(t, "team_overview", Args{"team": "Palmeiras"})
	mustContain(t, out, "Brasileirão", "Copa do Brasil", "Libertadores")
	// cross-file: match data + FIFA player data
	out = call(t, "team_overview", Args{"team": "Cruzeiro"})
	mustContain(t, out, "FIFA players at club", "Libertadores")
}

func TestNoDoubleCounting(t *testing.T) {
	// 2022 source file is missing one match, so it is not checked
	for _, y := range []int{2012, 2016, 2019} {
		for _, r := range db(t).Standings(CompBrasileirao, y) {
			if r.Played != 38 {
				t.Errorf("%d %s played %d", y, r.Team, r.Played)
			}
		}
	}
}

func TestUnknownTeamError(t *testing.T) {
	s := &Server{DB: db(t)}
	if _, err := s.Call("team_record", Args{"team": "Xyzzy United"}); err == nil {
		t.Error("expected error")
	}
}

func TestMCPProtocol(t *testing.T) {
	s := &Server{DB: db(t)}
	in := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":1}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"nope","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"bogus"}`,
	}, "\n")
	var out bytes.Buffer
	if err := s.Serve(strings.NewReader(in), &out); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 5 {
		t.Fatalf("want 5 responses, got %d:\n%s", len(lines), out.String())
	}
	var resp []map[string]any
	for _, l := range lines {
		var m map[string]any
		if err := json.Unmarshal([]byte(l), &m); err != nil {
			t.Fatal(err)
		}
		resp = append(resp, m)
	}
	if resp[0]["result"].(map[string]any)["serverInfo"] == nil {
		t.Error("no serverInfo")
	}
	if n := len(resp[1]["result"].(map[string]any)["tools"].([]any)); n != len(Tools) {
		t.Errorf("tools/list returned %d", n)
	}
	text := resp[2]["result"].(map[string]any)["content"].([]any)[0].(map[string]any)["text"].(string)
	mustContain(t, text, "Flamengo - 90 pts")
	if resp[3]["result"].(map[string]any)["isError"] != true {
		t.Error("unknown tool should be isError")
	}
	if resp[4]["error"] == nil {
		t.Error("unknown method should error")
	}
}
