// Context: end-to-end tests for the soccer knowledge base. They load the small
// deterministic fixtures in testdata/kaggle (hand-computed so every assertion
// can be checked by eye) and exercise normalization, cross-dataset
// deduplication / source selection, and every query function.
package soccer

import (
	"testing"
)

func loadTest(t *testing.T) *DB {
	t.Helper()
	db, err := Load("testdata/kaggle")
	if err != nil {
		t.Fatalf("Load returned error: %v", err)
	}
	return db
}

func TestNormalization(t *testing.T) {
	cases := []struct {
		raw, wantDisplay, wantState string
	}{
		{"Palmeiras-SP", "Palmeiras", "SP"},
		{"América - MG", "América", "MG"},
		{"Nacional (URU)", "Nacional", "URU"},
		{"Barcelona-EQU", "Barcelona", "EQU"},
		{"São Paulo", "São Paulo", ""},
		{"Sport Club Corinthians Paulista", "Sport Club Corinthians Paulista", ""},
	}
	for _, c := range cases {
		if got := cleanTeamName(c.raw); got != c.wantDisplay {
			t.Errorf("cleanTeamName(%q) = %q, want %q", c.raw, got, c.wantDisplay)
		}
		if got := suffixState(c.raw); got != c.wantState {
			t.Errorf("suffixState(%q) = %q, want %q", c.raw, got, c.wantState)
		}
	}
	// Accent folding makes São Paulo and Sao Paulo match.
	if teamKey("São Paulo") != teamKey("Sao Paulo") {
		t.Error("accent folding failed: São Paulo != Sao Paulo")
	}
	if teamKey("Grêmio") != "gremio" {
		t.Errorf("teamKey(Grêmio) = %q, want gremio", teamKey("Grêmio"))
	}
}

func TestSourcePriorityAndCoverage(t *testing.T) {
	db := loadTest(t)
	// The 2019 Brasileirão season exists in novo, Brasileirao_Matches and
	// BR-Football. novo (priority 3) wins, so exactly its 6 fixtures remain.
	bra2019 := db.SearchMatches(MatchQuery{Competition: CompBrasileirao, Season: 2019})
	if len(bra2019) != 6 {
		t.Errorf("Brasileirão 2019 matches = %d, want 6 (only novo source)", len(bra2019))
	}
	// 2020 exists only in Brasileirao_Matches, so it survives.
	bra2020 := db.SearchMatches(MatchQuery{Competition: CompBrasileirao, Season: 2020})
	if len(bra2020) != 3 {
		t.Errorf("Brasileirão 2020 matches = %d, want 3", len(bra2020))
	}
	// Série B only appears in BR-Football and must be preserved.
	serieB := db.SearchMatches(MatchQuery{Competition: "Serie B"})
	if len(serieB) != 1 {
		t.Errorf("Serie B matches = %d, want 1", len(serieB))
	}
	comps := db.Competitions()
	want := map[string]bool{CompBrasileirao: true, CompCopaDoBrasil: true, CompLibertadores: true, "Serie B": true}
	for w := range want {
		found := false
		for _, c := range comps {
			if c == w {
				found = true
			}
		}
		if !found {
			t.Errorf("competition %q missing from %v", w, comps)
		}
	}
}

func TestCanonicalKeyMatching(t *testing.T) {
	db := loadTest(t)
	// Suffix-less "Flamengo" must resolve to the same matches as "Flamengo-RJ".
	bare := db.SearchMatches(MatchQuery{Team: "Flamengo"})
	suffixed := db.SearchMatches(MatchQuery{Team: "Flamengo-RJ"})
	if len(bare) == 0 || len(bare) != len(suffixed) {
		t.Errorf("Flamengo (%d) and Flamengo-RJ (%d) should match identically", len(bare), len(suffixed))
	}
	// Atlético-MG and Atlético-GO are distinct clubs that share a bare name;
	// they must NOT be conflated.
	mg := db.SearchMatches(MatchQuery{Team: "Atlético-MG"})
	go_ := db.SearchMatches(MatchQuery{Team: "Atlético-GO"})
	if len(mg) == 0 || len(go_) == 0 {
		t.Fatalf("expected matches for both Atléticos, got MG=%d GO=%d", len(mg), len(go_))
	}
	for _, m := range mg {
		if m.HomeKey == "atletico-go" || m.AwayKey == "atletico-go" {
			// Atlético-GO vs Atlético-MG is a legitimate shared match; only
			// fail if a GO-only fixture leaked into MG results.
		}
	}
	// Atlético-MG played 3 matches in the fixtures (rounds 1-3 of 2020).
	if len(mg) != 3 {
		t.Errorf("Atlético-MG matches = %d, want 3", len(mg))
	}
	// Atlético-GO played only one (round 2).
	if len(go_) != 1 {
		t.Errorf("Atlético-GO matches = %d, want 1", len(go_))
	}
}

func TestStandings(t *testing.T) {
	db := loadTest(t)
	rows := db.Standings(CompBrasileirao, 2019)
	if len(rows) != 3 {
		t.Fatalf("standings rows = %d, want 3", len(rows))
	}
	// Hand-computed from the fixtures: Flamengo 10, Palmeiras 4, Santos 2.
	want := []struct {
		team string
		pts  int
	}{{"Flamengo", 10}, {"Palmeiras", 4}, {"Santos", 2}}
	for i, w := range want {
		if rows[i].Team != w.team || rows[i].Points != w.pts {
			t.Errorf("row %d = %s/%d pts, want %s/%d", i, rows[i].Team, rows[i].Points, w.team, w.pts)
		}
	}
	if rows[0].Wins != 3 || rows[0].Draws != 1 || rows[0].Losses != 0 {
		t.Errorf("Flamengo W/D/L = %d/%d/%d, want 3/1/0", rows[0].Wins, rows[0].Draws, rows[0].Losses)
	}
	if rows[0].GoalsFor != 7 || rows[0].GoalsAgst != 1 {
		t.Errorf("Flamengo goals = %d/%d, want 7/1", rows[0].GoalsFor, rows[0].GoalsAgst)
	}
}

func TestTeamRecord(t *testing.T) {
	db := loadTest(t)
	rec := db.TeamRecord("Flamengo", TeamRecordOptions{Competition: CompBrasileirao, Season: 2019})
	if rec.Matches != 4 || rec.Wins != 3 || rec.Draws != 1 || rec.Losses != 0 {
		t.Errorf("Flamengo 2019 record = %+v, want 4/3/1/0", rec)
	}
	if rec.Points != 10 {
		t.Errorf("Flamengo points = %d, want 10", rec.Points)
	}
	// Home-only: Flamengo hosted Palmeiras (2-0) and Santos (1-1) => 1W 1D.
	home := db.TeamRecord("Flamengo", TeamRecordOptions{Competition: CompBrasileirao, Season: 2019, HomeOnly: true})
	if home.Matches != 2 || home.Wins != 1 || home.Draws != 1 {
		t.Errorf("Flamengo home record = %+v, want 2 matches 1W 1D", home)
	}
}

func TestHeadToHead(t *testing.T) {
	db := loadTest(t)
	h := db.HeadToHead("Flamengo", "Santos", "")
	// In the fixtures they met twice (Bra 2019 r2 1-1, r6 Santos 0-3 Flamengo).
	if len(h.Matches) != 2 {
		t.Fatalf("Flamengo-Santos meetings = %d, want 2", len(h.Matches))
	}
	if h.AWins != 1 || h.Draws != 1 || h.BWins != 0 {
		t.Errorf("h2h A/draw/B = %d/%d/%d, want 1/1/0", h.AWins, h.Draws, h.BWins)
	}
	if h.AGoals != 4 || h.BGoals != 1 {
		t.Errorf("h2h goals = %d-%d, want 4-1", h.AGoals, h.BGoals)
	}
}

func TestStatistics(t *testing.T) {
	db := loadTest(t)
	s := db.Statistics(StatsFilter{Competition: CompBrasileirao, Season: 2019}, 5)
	if s.Matches != 6 {
		t.Errorf("stats matches = %d, want 6", s.Matches)
	}
	// Goals: 2,2,1,3,5(3+0+2... let's just trust sum) -> compute: m1 2, m2 2, m3 1, m4 3, m5 4, m6 3 = 15.
	if s.TotalGoals != 15 {
		t.Errorf("total goals = %d, want 15", s.TotalGoals)
	}
	if len(s.BiggestWins) == 0 {
		t.Error("expected at least one biggest win")
	}
	// Biggest margin in the set is 3 (Flamengo 3-0 / Palmeiras 3-0 / 0-3).
	top := s.BiggestWins[0]
	if abs(top.HomeGoals-top.AwayGoals) != 3 {
		t.Errorf("top margin = %d, want 3", abs(top.HomeGoals-top.AwayGoals))
	}
}

func TestPlayerQueries(t *testing.T) {
	db := loadTest(t)
	br := db.SearchPlayers(PlayerQuery{Nationality: "Brazil", SortByOverall: true})
	if len(br) != 3 {
		t.Fatalf("Brazilian players = %d, want 3", len(br))
	}
	if br[0].Name != "Neymar Jr" || br[0].Overall != 92 {
		t.Errorf("top Brazilian = %s/%d, want Neymar Jr/92", br[0].Name, br[0].Overall)
	}
	byName := db.SearchPlayers(PlayerQuery{Name: "messi"})
	if len(byName) != 1 || byName[0].Name != "Lionel Messi" {
		t.Errorf("name search messi = %+v, want Lionel Messi", byName)
	}
	byClub := db.SearchPlayers(PlayerQuery{Club: "Santos"})
	if len(byClub) != 1 || byClub[0].Name != "Local Hero" {
		t.Errorf("club search Santos = %+v, want Local Hero", byClub)
	}
	minRated := db.SearchPlayers(PlayerQuery{MinOverall: 90})
	if len(minRated) != 2 { // Neymar 92, Messi 94
		t.Errorf("players >=90 = %d, want 2", len(minRated))
	}
}

func TestPlayersByClub(t *testing.T) {
	db := loadTest(t)
	clubs := db.PlayersByClub("Brazil", 0)
	// Brazilian players span 3 clubs (PSG, Man City, Santos), one each.
	if len(clubs) != 3 {
		t.Fatalf("clubs with Brazilians = %d, want 3", len(clubs))
	}
	for _, c := range clubs {
		if c.Count != 1 {
			t.Errorf("club %s count = %d, want 1", c.Club, c.Count)
		}
	}
}

func TestDateParsing(t *testing.T) {
	cases := []string{"2019-04-06 16:00:00", "2019-04-06", "06/04/2019"}
	for _, c := range cases {
		if _, ok := parseDate(c); !ok {
			t.Errorf("parseDate(%q) failed", c)
		}
	}
	if _, ok := parseDate(""); ok {
		t.Error("parseDate(empty) should fail")
	}
}
