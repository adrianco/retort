package main

import (
	"strings"
	"sync"
	"testing"
	"time"
)

var (
	storeOnce sync.Once
	testStore *Store
	storeErr  error
)

// loadTestStore loads the real datasets once for all tests.
func loadTestStore(t testing.TB) *Store {
	t.Helper()
	storeOnce.Do(func() { testStore, storeErr = LoadStore("data/kaggle") })
	if storeErr != nil {
		t.Fatalf("LoadStore: %v", storeErr)
	}
	return testStore
}

func mustTeam(t *testing.T, s *Store, name string) *Team {
	t.Helper()
	team, err := s.ResolveTeam(name)
	if err != nil {
		t.Fatalf("ResolveTeam(%q): %v", name, err)
	}
	return team
}

func TestAllSixFilesLoaded(t *testing.T) {
	s := loadTestStore(t)
	want := map[string]int{
		SrcBrasileirao: 4180, SrcCup: 1337, SrcLibertadores: 1255,
		SrcExtended: 10296, SrcHistorical: 6886, SrcFIFA: 18207,
	}
	if len(s.Files) != len(want) {
		t.Fatalf("loaded %d files, want %d", len(s.Files), len(want))
	}
	for _, f := range s.Files {
		if f.Rows != want[f.Name] {
			t.Errorf("%s: %d rows, want %d", f.Name, f.Rows, want[f.Name])
		}
		if f.Loaded == 0 {
			t.Errorf("%s: nothing loaded", f.Name)
		}
		// Only rows without a score (e.g. "NA") may be skipped.
		if f.Skipped > f.Rows/20 {
			t.Errorf("%s: too many skipped rows (%d)", f.Name, f.Skipped)
		}
	}
	if len(s.Players) != 18207 {
		t.Errorf("players = %d, want 18207", len(s.Players))
	}
	if s.LoadTime > 5*time.Second {
		t.Errorf("loading took %s", s.LoadTime)
	}
}

func TestEveryMatchSourceIsQueryable(t *testing.T) {
	s := loadTestStore(t)
	seen := map[string]int{}
	for _, m := range s.Matches {
		for _, src := range m.Sources {
			seen[src]++
		}
	}
	for _, src := range matchSources {
		if seen[src] == 0 {
			t.Errorf("no matches reference source %s", src)
		}
	}
}

func TestTeamNameVariationsResolveToSameTeam(t *testing.T) {
	s := loadTestStore(t)
	groups := [][]string{
		{"Palmeiras", "Palmeiras-SP", "palmeiras - sp", "Sociedade Esportiva Palmeiras", "PALMEIRAS"},
		{"São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo FC", "sao paulo - SP"},
		{"Corinthians", "Corinthians-SP", "Sport Club Corinthians Paulista"},
		{"Athletico-PR", "Atletico-PR", "Athletico Paranaense", "Atlético Paranaense", "Athletico"},
		{"Atlético-MG", "Atletico Mineiro", "Atlético Mineiro - MG"},
		{"Vasco", "Vasco da Gama", "Vasco da Gama-RJ", "Vasco Da Gama RJ"},
		{"Grêmio", "Gremio", "Gremio-RS", "Grêmio - RS"},
		{"Bragantino", "Red Bull Bragantino", "Red Bull Bragantino-SP"},
		{"Sport", "Sport Recife", "Sport-PE"},
	}
	for _, g := range groups {
		first := mustTeam(t, s, g[0])
		for _, name := range g[1:] {
			if got := mustTeam(t, s, name); got != first {
				t.Errorf("%q resolved to %s, but %q resolved to %s", name, got.Key, g[0], first.Key)
			}
		}
	}
	// Same base name, different clubs.
	if mustTeam(t, s, "Flamengo") == mustTeam(t, s, "Flamengo-PI") {
		t.Error("Flamengo-RJ and Flamengo-PI must be different teams")
	}
	if mustTeam(t, s, "Botafogo") == mustTeam(t, s, "Botafogo-PB") {
		t.Error("Botafogo-RJ and Botafogo-PB must be different teams")
	}
	if mustTeam(t, s, "Guarani") == mustTeam(t, s, "Guaraní (PAR)") {
		t.Error("Guarani-SP and Guaraní (Paraguay) must be different teams")
	}
	// Argentina's River Plate must not be merged with River Plate-SE.
	rp := mustTeam(t, s, "River Plate")
	if rp.Key != "river plate" || len(rp.Matches) < 50 {
		t.Errorf("River Plate resolved to %s with %d matches", rp.Key, len(rp.Matches))
	}
	// Accented display names are preferred.
	if n := mustTeam(t, s, "sao paulo").Name; n != "São Paulo" {
		t.Errorf("display name = %q, want São Paulo", n)
	}
	if _, err := s.ResolveTeam("Manchester United"); err == nil {
		t.Error("expected unknown team error")
	}
}

func TestCrossFileDeduplication(t *testing.T) {
	s := loadTestStore(t)
	// Série A 2012-2019 is present in three files; each season must still
	// have exactly 380 unique fixtures.
	for season := 2006; season <= 2022; season++ {
		if n := len(s.FindMatches(MatchFilter{Competition: CompSerieA, Season: season})); n != 380 {
			t.Errorf("Série A %d has %d matches, want 380", season, n)
		}
	}
	// Each club plays 38 Série A matches per season.
	for _, team := range []string{"Flamengo", "Palmeiras", "Vitória", "Athletico-PR"} {
		n := len(s.FindMatches(MatchFilter{Team: mustTeam(t, s, team), Competition: CompSerieA, Season: 2017}))
		if n != 38 {
			t.Errorf("%s played %d Série A 2017 matches, want 38", team, n)
		}
	}
	// Extended stats from BR-Football are attached to merged fixtures.
	withStats := 0
	for _, m := range s.FindMatches(MatchFilter{Competition: CompSerieA, Season: 2019}) {
		if m.Stats != nil && len(m.Sources) > 1 {
			withStats++
		}
	}
	if withStats < 300 {
		t.Errorf("only %d merged 2019 matches carry extended stats", withStats)
	}
}

func TestStandings2019(t *testing.T) {
	s := loadTestStore(t)
	rows, source, n := s.Standings(CompSerieA, 2019)
	if n != 380 || len(rows) != 20 {
		t.Fatalf("2019: %d matches, %d teams (source %s)", n, len(rows), source)
	}
	top := rows[0]
	if top.Team.Name != "Flamengo" || top.Points() != 90 || top.Won != 28 || top.Drawn != 6 || top.Lost != 4 {
		t.Errorf("2019 champion row = %s %d pts %d/%d/%d", top.Team.Name, top.Points(), top.Won, top.Drawn, top.Lost)
	}
	if rows[1].Team.Name != "Santos" || rows[1].Points() != 74 || rows[2].Team.Name != "Palmeiras" {
		t.Errorf("2019 2nd/3rd = %s %d, %s", rows[1].Team.Name, rows[1].Points(), rows[2].Team.Name)
	}
}

func TestRelegated2020(t *testing.T) {
	s := loadTestStore(t)
	rows, _, _ := s.Standings(CompSerieA, 2020)
	var bottom []string
	for _, r := range rows[len(rows)-4:] {
		bottom = append(bottom, r.Team.Name)
	}
	want := "Vasco da Gama,Goiás,Coritiba,Botafogo"
	if got := strings.Join(bottom, ","); got != want {
		t.Errorf("2020 relegated = %s, want %s", got, want)
	}
	if rows[0].Team.Name != "Flamengo" {
		t.Errorf("2020 champion = %s", rows[0].Team.Name)
	}
}

func TestChampionsAcrossSeasons(t *testing.T) {
	s := loadTestStore(t)
	want := map[int]string{
		2003: "Cruzeiro", 2009: "Flamengo", 2012: "Fluminense", 2015: "Corinthians",
		2016: "Palmeiras", 2018: "Palmeiras", 2021: "Atlético Mineiro", 2022: "Palmeiras",
	}
	for season, champ := range want {
		rows, _, _ := s.Standings(CompSerieA, season)
		if len(rows) == 0 || rows[0].Team.Name != champ {
			got := "none"
			if len(rows) > 0 {
				got = rows[0].Team.Name
			}
			t.Errorf("%d champion = %s, want %s", season, got, champ)
		}
	}
}

func TestTeamRecordCorinthiansHome2022(t *testing.T) {
	s := loadTestStore(t)
	c := mustTeam(t, s, "Corinthians")
	ms := s.FindMatches(MatchFilter{Team: c, Venue: "home", Season: 2022, Competition: CompSerieA})
	r := TeamRecord(c, ms)
	// 15 scored rows in Brasileirao_Matches.csv + 4 rows that are "NA" there
	// but present in BR-Football-Dataset.csv.
	if r.Played != 19 || r.Won != 12 || r.Drawn != 4 || r.Lost != 3 || r.GF != 24 || r.GA != 11 {
		t.Errorf("Corinthians home 2022 = %+v", r)
	}
	for _, m := range ms {
		if m.Home != c {
			t.Fatalf("venue filter returned away match %s", fmtMatch(m))
		}
	}
}

func TestHeadToHeadIsSymmetric(t *testing.T) {
	s := loadTestStore(t)
	a, b := mustTeam(t, s, "Palmeiras"), mustTeam(t, s, "Santos")
	ms := s.FindMatches(MatchFilter{Team: a, Opponent: b})
	ra, rb := TeamRecord(a, ms), TeamRecord(b, ms)
	if len(ms) < 30 || ra.Won != rb.Lost || ra.Lost != rb.Won || ra.Drawn != rb.Drawn || ra.GF != rb.GA {
		t.Errorf("asymmetric head-to-head: %+v vs %+v over %d matches", ra, rb, len(ms))
	}
	for _, m := range ms {
		if !m.Involves(a) || !m.Involves(b) {
			t.Fatalf("match %s does not involve both teams", fmtMatch(m))
		}
	}
	if DerbyName(a, b) != "Clássico da Saudade" {
		t.Errorf("derby = %q", DerbyName(a, b))
	}
}

func TestFindMatchesFilters(t *testing.T) {
	s := loadTestStore(t)
	from, _, _ := parseDate("2019-05-01")
	to, _, _ := parseDate("2019-06-30")
	ms := s.FindMatches(MatchFilter{DateFrom: from, DateTo: to, Competition: CompLibertadores})
	if len(ms) == 0 {
		t.Fatal("no Libertadores matches in May-June 2019")
	}
	for _, m := range ms {
		if m.Date.Before(from) || m.Date.After(to.Add(24*time.Hour)) || m.Competition != CompLibertadores {
			t.Errorf("filter leak: %s", fmtMatch(m))
		}
	}
	finals := s.FindMatches(MatchFilter{Competition: CompCopaBrasil, Stage: "final"})
	seasons := map[int]int{}
	for _, m := range finals {
		seasons[m.Season]++
	}
	for y := 2012; y <= 2023; y++ {
		if seasons[y] != 2 {
			t.Errorf("Copa do Brasil %d final has %d legs, want 2", y, seasons[y])
		}
	}
}

func TestSeasonInferenceForDelayed2020(t *testing.T) {
	s := loadTestStore(t)
	// The 2020 Brasileirão ended in February 2021.
	ms := s.FindMatches(MatchFilter{Competition: CompSerieA, Season: 2020})
	late := 0
	for _, m := range ms {
		if m.Date.Year() == 2021 {
			late++
		}
	}
	if late == 0 {
		t.Error("expected 2020 season matches played in 2021")
	}
}

func TestPlayers(t *testing.T) {
	s := loadTestStore(t)
	br := s.FindPlayers(PlayerFilter{Nationality: "Brazilian"})
	if len(br) != 827 {
		t.Errorf("Brazilian players = %d, want 827", len(br))
	}
	if br[0].Name != "Neymar Jr" || br[0].Overall != 92 {
		t.Errorf("top Brazilian = %s %d", br[0].Name, br[0].Overall)
	}
	gk := s.FindPlayers(PlayerFilter{Nationality: "Brazil", Position: "goalkeepers"})
	if len(gk) == 0 || gk[0].Name != "Ederson" { // FIFA 19: Ederson 86, Alisson 85
		t.Errorf("top Brazilian GK = %v", gk)
	}
	for _, p := range gk {
		if p.Position != "GK" {
			t.Fatalf("position filter leak: %s %s", p.Name, p.Position)
		}
	}
	// Accent-insensitive name search.
	if ps := s.FindPlayers(PlayerFilter{Name: "aníbão"}); len(ps) == 0 {
		t.Error("accent-insensitive name search failed")
	}
	// FIFA clubs link to match-data teams (cross-file graph edge).
	santos := mustTeam(t, s, "Santos")
	if len(santos.Players) != 20 {
		t.Errorf("Santos FIFA squad = %d players", len(santos.Players))
	}
	linked := 0
	for _, team := range s.Teams {
		if len(team.Players) > 0 {
			linked++
		}
	}
	if linked != 15 {
		t.Errorf("%d Brazilian clubs linked to FIFA squads, want 15", linked)
	}
	// "Santos Laguna" players must not be linked to Santos-SP.
	for _, p := range santos.Players {
		if p.Club != "Santos" {
			t.Errorf("player %s from %s linked to Santos", p.Name, p.Club)
		}
	}
}
