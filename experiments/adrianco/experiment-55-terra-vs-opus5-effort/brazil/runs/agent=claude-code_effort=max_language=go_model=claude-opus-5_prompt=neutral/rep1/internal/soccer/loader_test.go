package soccer

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestAllDatasetsLoad is the "all 6 CSV files are loadable and queryable"
// success criterion.
func TestAllDatasetsLoad(t *testing.T) {
	s := testStore(t)
	want := map[string]int{
		SrcBrasileirao:  4180,
		SrcNovo:         6886,
		SrcCup:          1337,
		SrcLibertadores: 1255,
		SrcBRFootball:   10296,
		SrcFIFA:         18207,
	}
	if len(s.Datasets) != len(want) {
		t.Fatalf("loaded %d datasets, want %d", len(s.Datasets), len(want))
	}
	for _, d := range s.Datasets {
		rows, ok := want[d.Key]
		if !ok {
			t.Errorf("unexpected dataset %q", d.Key)
			continue
		}
		if d.Rows != rows {
			t.Errorf("%s: read %d rows, want %d", d.Key, d.Rows, rows)
		}
		if d.Used == 0 {
			t.Errorf("%s: no rows used", d.Key)
		}
		if d.License == "" || d.URL == "" {
			t.Errorf("%s: missing licence or source URL", d.Key)
		}
	}
	if len(s.Players) != 18207 {
		t.Errorf("loaded %d players, want 18207", len(s.Players))
	}
	if len(s.Matches) < 16000 {
		t.Errorf("only %d matches survived the merge", len(s.Matches))
	}
}

func TestCompetitionCoverage(t *testing.T) {
	s := testStore(t)
	want := map[string][2]int{
		CompBrasileirao:  {2003, 2023},
		CompSerieB:       {2014, 2023},
		CompSerieC:       {2014, 2023},
		CompCopaDoBrasil: {2012, 2023},
		CompLibertadores: {2013, 2022},
	}
	for comp, span := range want {
		seasons := s.Seasons(comp)
		if len(seasons) == 0 {
			t.Errorf("%s has no seasons", comp)
			continue
		}
		if seasons[0] != span[0] || seasons[len(seasons)-1] != span[1] {
			t.Errorf("%s covers %d-%d, want %d-%d", comp, seasons[0], seasons[len(seasons)-1], span[0], span[1])
		}
	}
}

// TestOverlappingSourcesAreMerged is the core of the load: Série A 2012-2019
// exists in three files, and every fixture must survive exactly once.
func TestOverlappingSourcesAreMerged(t *testing.T) {
	s := testStore(t)
	// A double round-robin of 20 clubs is 380 matches; 2003-2004 had 24 clubs
	// and 2005 had 22.
	want := map[int]int{
		2003: 552, 2004: 552, 2005: 462,
		2006: 380, 2010: 380, 2012: 380, 2015: 380, 2019: 380, 2020: 380, 2022: 380,
	}
	for season, count := range want {
		if got := len(s.SeasonMatches(CompBrasileirao, season)); got != count {
			t.Errorf("Brasileirão %d has %d matches, want %d (a merge or dedup problem)", season, got, count)
		}
	}

	// No two matches may describe the same fixture.
	seen := map[string]*Match{}
	for _, m := range s.Matches {
		key := fmt.Sprintf("%s|%d|%s|%s", m.CompetitionID, m.Season, m.HomeTeamID, m.AwayTeamID)
		if prev, ok := seen[key]; ok {
			gap := prev.Date.Sub(m.Date)
			if gap < 0 {
				gap = -gap
			}
			if gap <= mergeWindow {
				t.Errorf("duplicate fixture: %s (%s) and %s (%s)", prev.Label(), prev.DateString(), m.Label(), m.DateString())
			}
			continue
		}
		seen[key] = m
	}

	// The merge must actually be joining sources, not just deduplicating.
	multi := 0
	for _, m := range s.Matches {
		if len(m.Sources) > 1 {
			multi++
		}
	}
	if multi < 3000 {
		t.Errorf("only %d matches came from more than one source; the sources are not being joined", multi)
	}
}

// Cross-file enrichment: a Série A fixture that also appears in
// BR-Football-Dataset.csv must carry its shots and corners.
func TestExtendedStatsAreJoined(t *testing.T) {
	s := testStore(t)
	withStats := 0
	for _, m := range s.SeasonMatches(CompBrasileirao, 2019) {
		if m.Stats != nil {
			withStats++
		}
	}
	if withStats == 0 {
		t.Fatal("no 2019 Série A match carries extended statistics")
	}
	page := s.FindMatches(MatchFilter{CompetitionID: CompBrasileirao, Season: 2019, Limit: 0})
	for _, m := range page.Matches {
		if m.Stats == nil {
			continue
		}
		if !m.Stats.HomeCorners.Valid && !m.Stats.HomeShots.Valid && !m.Stats.HomeAttacks.Valid {
			t.Errorf("match %s has an empty statistics block", m.ID)
		}
		if len(m.Sources) < 2 {
			t.Errorf("match %s has statistics but only source %v", m.ID, m.Sources)
		}
		break
	}
}

// Venue data comes only from novo_campeonato_brasileiro.csv and must survive
// the merge into the fixtures that other files also describe.
func TestVenuesAreJoined(t *testing.T) {
	s := testStore(t)
	withVenue := 0
	for _, m := range s.SeasonMatches(CompBrasileirao, 2019) {
		if m.Venue != "" {
			withVenue++
		}
	}
	if withVenue < 300 {
		t.Errorf("only %d of the 2019 fixtures have a stadium, want most of them", withVenue)
	}
}

// Copa do Brasil rounds are numbers; the loader turns them into stage names.
func TestCupStagesAreLabelled(t *testing.T) {
	s := testStore(t)
	finals := map[int]int{}
	for _, m := range s.CompetitionMatches(CompCopaDoBrasil) {
		if StageMatches(m.Stage, "final") {
			finals[m.Season]++
		}
	}
	for season := 2012; season <= 2020; season++ {
		if finals[season] != 2 {
			t.Errorf("Copa do Brasil %d has %d final legs, want 2", season, finals[season])
		}
	}
	// The 2013 final was Athletico-PR against Flamengo.
	page := s.FindMatches(MatchFilter{CompetitionID: CompCopaDoBrasil, Season: 2013, Stage: "final"})
	if page.Total != 2 {
		t.Fatalf("2013 final has %d legs", page.Total)
	}
	for _, m := range page.Matches {
		if !m.Involves("flamengo-rj") || !m.Involves("athletico-pr") {
			t.Errorf("2013 final leg is %s, expected Flamengo v Athletico-PR", m.Label())
		}
	}
}

// The 2020 Série A ran into February 2021 because of the pandemic; matches
// must stay in the season they belong to.
func TestSeasonBoundariesSurviveTheDelayedSeason(t *testing.T) {
	s := testStore(t)
	for _, season := range []int{2020, 2021} {
		if got := len(s.SeasonMatches(CompBrasileirao, season)); got != 380 {
			t.Errorf("Brasileirão %d has %d matches, want 380", season, got)
		}
	}
	late := 0
	for _, m := range s.SeasonMatches(CompBrasileirao, 2020) {
		if m.Date.Year() == 2021 {
			late++
		}
	}
	if late == 0 {
		t.Error("the 2020 season should contain fixtures played in 2021")
	}
}

func TestPlayersAreLinkedToClubs(t *testing.T) {
	s := testStore(t)
	linked := 0
	for _, p := range s.Players {
		if p.TeamID != "" {
			linked++
			if s.Teams.Team(p.TeamID) == nil {
				t.Fatalf("player %s links to unknown club %q", p.Name, p.TeamID)
			}
		}
	}
	if linked < 200 {
		t.Errorf("only %d players are linked to clubs in the match data", linked)
	}
	if squad := s.PlayersForTeam("gremio-rs"); len(squad) == 0 {
		t.Error("Grêmio has no squad linked from the player file")
	}
}

func TestPlayerAttributesAreParsed(t *testing.T) {
	s := testStore(t)
	page := s.FindPlayers(PlayerFilter{Name: "Neymar", Limit: 1})
	if len(page.Players) == 0 {
		t.Fatal("Neymar is missing from the player data")
	}
	p := page.Players[0]
	if p.Overall != 92 || p.Nationality != "Brazil" || p.Position != "LW" {
		t.Errorf("Neymar parsed as overall %d, %s, %s", p.Overall, p.Nationality, p.Position)
	}
	if v, ok := p.Skill("Dribbling"); !ok || v < 90 {
		t.Errorf("Neymar dribbling = %d (present %v)", v, ok)
	}
	if len(p.TopSkills(5)) != 5 {
		t.Error("TopSkills should return five attributes")
	}
}

func TestAnomaliesAreReported(t *testing.T) {
	s := testStore(t)
	if len(s.Anomalies) == 0 {
		t.Error("the loader should report the rows it refused to trust")
	}
	for _, note := range s.Anomalies {
		if note == "" {
			t.Error("empty anomaly note")
		}
	}
}

func TestFindDataDir(t *testing.T) {
	dir, err := FindDataDir("")
	if err != nil {
		t.Fatalf("FindDataDir: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, "Brasileirao_Matches.csv")); err != nil {
		t.Errorf("FindDataDir returned %q, which has no CSVs", dir)
	}
	if _, err := FindDataDir(filepath.Join(t.TempDir(), "nope")); err == nil {
		t.Error("FindDataDir should fail for a directory without the CSVs")
	}
}

func TestLoadIsFastEnough(t *testing.T) {
	start := time.Now()
	s, err := Load(Options{})
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if elapsed := time.Since(start); elapsed > 10*time.Second {
		t.Errorf("loading took %s", elapsed)
	}
	if len(s.Matches) == 0 {
		t.Error("no matches loaded")
	}
}

// The reported anomalies must not depend on Go's map iteration order: the
// model only ever sees the first few of them.
func TestAnomalyOrderIsStable(t *testing.T) {
	first := testStore(t).Anomalies
	for i := 0; i < 3; i++ {
		s, err := Load(Options{SkipPlayers: true})
		if err != nil {
			t.Fatalf("Load: %v", err)
		}
		if len(s.Anomalies) != len(first) {
			t.Fatalf("load %d reported %d anomalies, first load reported %d", i, len(s.Anomalies), len(first))
		}
		for j := range first {
			if s.Anomalies[j] != first[j] {
				t.Fatalf("anomaly %d differs between loads:\n%s\n%s", j, first[j], s.Anomalies[j])
			}
		}
	}
}
