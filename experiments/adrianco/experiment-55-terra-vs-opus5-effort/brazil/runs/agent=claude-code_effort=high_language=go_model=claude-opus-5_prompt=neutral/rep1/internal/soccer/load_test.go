// load_test.go asserts the structural invariants of the loaded graph: that all
// six datasets are read, that overlapping datasets are merged rather than
// double-counted, and that the reconstructed league seasons are internally
// consistent.
package soccer

import (
	"fmt"
	"testing"
	"time"
)

func TestAllDatasetsLoad(t *testing.T) {
	g := LoadTestGraph(t)

	if got := len(g.Stats.Datasets); got != len(SourceFiles) {
		t.Fatalf("loaded %d datasets, want %d", got, len(SourceFiles))
	}
	for _, d := range g.Stats.Datasets {
		if d.RowsUsed == 0 {
			t.Errorf("%s contributed no rows", d.File)
		}
		if d.License == "" {
			t.Errorf("%s has no recorded licence", d.File)
		}
		// Every dataset should be almost entirely usable.
		if float64(d.RowsUsed) < 0.95*float64(d.RowsRead) {
			t.Errorf("%s: only %d of %d rows were usable", d.File, d.RowsUsed, d.RowsRead)
		}
	}
	if len(g.Players) != 18207 {
		t.Errorf("players = %d, want 18207", len(g.Players))
	}
	if len(g.Matches) < 15000 {
		t.Errorf("matches = %d, expected well over 15000", len(g.Matches))
	}
}

func TestOverlappingDatasetsAreMerged(t *testing.T) {
	g := LoadTestGraph(t)

	// Série A 2014-2019 is present in three of the five match files. If the
	// loader did not merge duplicates each season would hold far more than the
	// 380 matches a 20-club double round-robin can contain.
	if g.Stats.MergedDuplicates == 0 {
		t.Fatal("no duplicate rows were merged; the datasets are known to overlap")
	}
	for season := 2003; season <= 2022; season++ {
		st, err := g.Standings(CompSerieA, season)
		if err != nil {
			t.Errorf("Standings(%d): %v", season, err)
			continue
		}
		expected := expectedSerieAMatches(season)
		if st.MatchesUsed != expected {
			t.Errorf("Série A %d has %d matches, want %d", season, st.MatchesUsed, expected)
		}
		if !st.Complete {
			t.Errorf("Série A %d should be a complete season: %s", season, st.Note)
		}
	}

	// A merged match should record every file it came from.
	multi := 0
	for _, m := range g.Matches {
		if len(m.Sources) > 1 {
			multi++
		}
	}
	if multi == 0 {
		t.Error("no match records provenance from more than one dataset")
	}
}

func expectedSerieAMatches(season int) int {
	switch {
	case season <= 2004:
		return 24 * 23
	case season == 2005:
		return 22 * 21
	default:
		return 20 * 19
	}
}

func TestNoDuplicateLeagueFixtures(t *testing.T) {
	g := LoadTestGraph(t)

	// Two records of the same pairing months apart are two real matches — the
	// 2009 Brasileirão genuinely lists Botafogo at home against Flamengo twice,
	// because the source mislabels the venue of one leg. What must never
	// survive is the same fixture recorded twice from two different datasets,
	// which shows up as near-identical dates.
	seen := map[string][]*Match{}
	for _, m := range g.Matches {
		if competitionCatalog[m.Competition].Kind != "league" {
			continue
		}
		key := fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.HomeTeamID, m.AwayTeamID)
		for _, prev := range seen[key] {
			if d := prev.Date.Sub(m.Date); d < 10*24*time.Hour && d > -10*24*time.Hour {
				t.Fatalf("un-merged duplicate fixture: %s on %s and %s",
					key, FormatDate(prev.Date), FormatDate(m.Date))
			}
		}
		seen[key] = append(seen[key], m)
	}
}

func TestEveryMatchIsWellFormed(t *testing.T) {
	g := LoadTestGraph(t)

	for _, m := range g.Matches {
		if m.HomeTeamID == m.AwayTeamID {
			t.Fatalf("match %s has the same club on both sides", m.ID)
		}
		if _, ok := g.Teams[m.HomeTeamID]; !ok {
			t.Fatalf("match %s references unknown home team %q", m.ID, m.HomeTeamID)
		}
		if _, ok := g.Teams[m.AwayTeamID]; !ok {
			t.Fatalf("match %s references unknown away team %q", m.ID, m.AwayTeamID)
		}
		if m.Date.IsZero() {
			t.Fatalf("match %s has no date", m.ID)
		}
		if m.HomeGoals < 0 || m.AwayGoals < 0 {
			t.Fatalf("match %s has negative goals", m.ID)
		}
		if m.Season < 2000 || m.Season > 2030 {
			t.Fatalf("match %s has an implausible season %d", m.ID, m.Season)
		}
	}
}

func TestSeasonSpillIsCorrected(t *testing.T) {
	g := LoadTestGraph(t)

	// The COVID-delayed 2020 Série A finished in February 2021. Those matches
	// must count towards 2020, not 2021.
	spill := 0
	for _, m := range g.CompetitionMatches(CompSerieA) {
		if m.Date.Year() == 2021 && m.Date.Month() <= 2 {
			spill++
			if m.Season != 2020 {
				t.Errorf("match on %s assigned to season %d, want 2020", FormatDate(m.Date), m.Season)
			}
		}
	}
	if spill == 0 {
		t.Error("expected to find 2020 Série A matches played in early 2021")
	}
}

func TestPlayerMoneyParsing(t *testing.T) {
	g := LoadTestGraph(t)

	p, err := g.PlayerProfile("Neymar", 0)
	if err != nil {
		t.Fatalf("PlayerProfile: %v", err)
	}
	if p.Overall != 92 {
		t.Errorf("Neymar overall = %d, want 92", p.Overall)
	}
	if p.Nationality != "Brazil" {
		t.Errorf("Neymar nationality = %q", p.Nationality)
	}
	if len(p.Skills) < 30 {
		t.Errorf("only %d skill attributes parsed", len(p.Skills))
	}
}

func TestParseMoney(t *testing.T) {
	cases := map[string]float64{
		"€110.5M": 110_500_000,
		"€565K":   565_000,
		"€0":      0,
		"":        0,
	}
	for in, want := range cases {
		if got := parseMoney(in); got != want {
			t.Errorf("parseMoney(%q) = %v, want %v", in, got, want)
		}
	}
}
