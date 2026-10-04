// data_test.go — loading, parsing and de-duplication of the six CSV files.
package main

import (
	"sync"
	"testing"
	"time"
	"unicode/utf8"
)

var (
	storeOnce sync.Once
	store     *Store
	storeErr  error
	loadTime  time.Duration
)

// testStore loads the real data once for all tests.
func testStore(t testing.TB) *Store {
	t.Helper()
	storeOnce.Do(func() {
		start := time.Now()
		store, storeErr = LoadStore("data/kaggle")
		loadTime = time.Since(start)
	})
	if storeErr != nil {
		t.Fatalf("LoadStore: %v", storeErr)
	}
	return store
}

func TestAllSixFilesLoad(t *testing.T) {
	s := testStore(t)
	want := map[string]int{ // rows in each file
		SrcBrasileirao: 4180, SrcCup: 1337, SrcLibertadores: 1255,
		SrcBRFootball: 10296, SrcHistorical: 6886, SrcFIFA: 18207,
	}
	if len(s.Sources) != 6 {
		t.Fatalf("loaded %d sources, want 6", len(s.Sources))
	}
	for _, src := range s.Sources {
		if src.Rows != want[src.File] {
			t.Errorf("%s: %d rows, want %d", src.File, src.Rows, want[src.File])
		}
		// Only unplayed fixtures (NA scores) may be skipped.
		if src.Skipped > 100 {
			t.Errorf("%s: %d rows skipped", src.File, src.Skipped)
		}
	}
	if len(s.Players) != 18207 {
		t.Errorf("players = %d", len(s.Players))
	}
	// Every match file contributes matches.
	bySrc := map[string]int{}
	for _, m := range s.Matches {
		for _, src := range m.Sources {
			bySrc[src]++
		}
	}
	for _, f := range []string{SrcBrasileirao, SrcCup, SrcLibertadores, SrcBRFootball, SrcHistorical} {
		if bySrc[f] == 0 {
			t.Errorf("no matches from %s", f)
		}
	}
	t.Logf("load time %s, %d unique matches", loadTime, len(s.Matches))
	if loadTime > 5*time.Second {
		t.Errorf("loading took %s", loadTime)
	}
}

func TestParseDateFormats(t *testing.T) {
	cases := []struct {
		in      string
		want    string
		hasTime bool
	}{
		{"2023-09-24", "2023-09-24 00:00", false},
		{"29/03/2003", "2003-03-29 00:00", false},
		{"2012-05-19 18:30:00", "2012-05-19 18:30", true},
	}
	for _, c := range cases {
		got, ht, err := ParseDate(c.in)
		if err != nil || got.Format("2006-01-02 15:04") != c.want || ht != c.hasTime {
			t.Errorf("ParseDate(%q) = %v %v %v", c.in, got, ht, err)
		}
	}
	if _, _, err := ParseDate("NA"); err == nil {
		t.Error("NA should not parse")
	}
}

func TestParseGoals(t *testing.T) {
	if n, err := parseGoals("2.0"); err != nil || n != 2 {
		t.Errorf("parseGoals(2.0) = %d %v", n, err)
	}
	for _, bad := range []string{"NA", "-", ""} {
		if _, err := parseGoals(bad); err == nil {
			t.Errorf("parseGoals(%q) should fail", bad)
		}
	}
}

// Série A appears in up to three files; after merging every complete season
// must have exactly 380 games (20 teams) — no duplicates, nothing lost.
func TestSerieADeduplicated(t *testing.T) {
	s := testStore(t)
	for y := 2006; y <= 2022; y++ {
		ms := s.Filter(MatchFilter{Competitions: []string{CompSerieA}, Season: y, Canonical: true})
		rs, sm := s.Standings(CompSerieA, y)
		if len(sm) != 380 || len(rs) != 20 {
			t.Errorf("Série A %d: %d matches (%d canonical), %d teams; want 380/20", y, len(sm), len(ms), len(rs))
		}
		for _, r := range rs {
			if r.Played != 38 {
				t.Errorf("Série A %d: %s played %d", y, r.Team.Name, r.Played)
			}
		}
	}
	// 2012-2019 is in all three files (2012-2013 in two) and must be merged.
	merged := 0
	for _, m := range s.Filter(MatchFilter{Competitions: []string{CompSerieA}, Season: 2018}) {
		if len(m.Sources) == 3 {
			merged++
		}
	}
	if merged != 380 {
		t.Errorf("2018: %d games merged from all three files, want 380", merged)
	}
}

func TestExtendedStatsAttached(t *testing.T) {
	s := testStore(t)
	n := 0
	for _, m := range s.Matches {
		if m.Stats != nil && m.Stats.HomeShots+m.Stats.AwayShots > 0 {
			n++
		}
	}
	if n < 5000 {
		t.Errorf("only %d matches have shot statistics", n)
	}
	// Arena from the historical file survives merging with higher-priority files.
	ms := s.Filter(MatchFilter{Competitions: []string{CompSerieA}, Season: 2019, HomeTeam: mustTeam(t, s, "Flamengo"), AwayTeam: mustTeam(t, s, "Gremio")})
	if len(ms) != 1 || ms[0].Arena != "Maracanã" || ms[0].Round != "14" {
		t.Errorf("Flamengo v Grêmio 2019: %+v", ms)
	}
}

func TestUTF8Names(t *testing.T) {
	s := testStore(t)
	for _, tm := range s.Teams.Teams() {
		if !utf8.ValidString(tm.Name) {
			t.Errorf("invalid UTF-8 team name %q", tm.Name)
		}
	}
	for _, name := range []string{"São Paulo", "Grêmio", "Avaí", "Criciúma", "Goiás"} {
		tm, _ := s.ResolveTeam(name)
		if tm == nil || tm.Name != name {
			t.Errorf("display name for %q = %v", name, tm)
		}
	}
	found := false
	for _, p := range s.Players {
		if p.Name == "Josué Chiamulera" {
			found = true
		}
	}
	if !found {
		t.Error("accented player name not loaded correctly")
	}
}

func TestCupStagesLabelled(t *testing.T) {
	s := testStore(t)
	finals := s.Filter(MatchFilter{Competitions: []string{CompCopaBrasil}, Stage: "final"})
	seasons := map[int]bool{}
	for _, m := range finals {
		if m.Stage != "final" {
			t.Errorf("stage filter returned %q", m.Stage)
		}
		seasons[m.Season] = true
	}
	for y := 2012; y <= 2020; y++ {
		if !seasons[y] {
			t.Errorf("no Copa do Brasil final for %d", y)
		}
	}
	if len(finals) != 18 { // 9 two-legged finals
		t.Errorf("%d final legs, want 18", len(finals))
	}
}

func TestFIFABrazilianClubsMapped(t *testing.T) {
	s := testStore(t)
	for _, c := range brazilianFIFAClubs {
		var ps []*Player
		for _, p := range s.Players {
			if p.Club == c {
				ps = append(ps, p)
			}
		}
		if len(ps) == 0 || ps[0].ClubTeam == nil {
			t.Errorf("FIFA club %q not linked to a match-data team", c)
			continue
		}
		if s.MatchCount(ps[0].ClubTeam) < 50 {
			t.Errorf("FIFA club %q linked to %s with only %d matches", c, ps[0].ClubTeam.Name, s.MatchCount(ps[0].ClubTeam))
		}
	}
	// Santos Laguna (Mexico) must not be treated as Santos.
	for _, p := range s.Players {
		if p.Club == "Santos Laguna" && p.ClubTeam != nil {
			t.Fatalf("Santos Laguna mapped to %s", p.ClubTeam.Name)
		}
	}
}

func mustTeam(t testing.TB, s *Store, name string) *Team {
	t.Helper()
	tm, _ := s.ResolveTeam(name)
	if tm == nil {
		t.Fatalf("team %q not found", name)
	}
	return tm
}
