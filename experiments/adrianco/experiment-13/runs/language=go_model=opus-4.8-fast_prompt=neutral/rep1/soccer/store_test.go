package soccer

import (
	"testing"
	"time"
)

// buildStore creates a finalized store from inline matches for white-box tests.
func buildStore(raw []struct {
	home, away   string
	hg, ag       int
	season       int
	day          string
	source, comp string
}) *Store {
	s := newStore()
	for _, r := range raw {
		var d time.Time
		if r.day != "" {
			d, _ = time.Parse("2006-01-02", r.day)
		}
		comp := r.comp
		if comp == "" {
			comp = CompSerieA
		}
		src := r.source
		if src == "" {
			src = "test.csv"
		}
		m := Match{Competition: comp, Season: r.season, Date: d, HomeGoals: r.hg, AwayGoals: r.ag, Source: src}
		s.addMatch(&m, r.home, r.away)
	}
	s.finalize()
	return s
}

type row = struct {
	home, away   string
	hg, ag       int
	season       int
	day          string
	source, comp string
}

func TestStateDisambiguation(t *testing.T) {
	s := buildStore([]row{
		{home: "Atlético-MG", away: "Cruzeiro-MG", hg: 1, ag: 0, season: 2019, day: "2019-05-01"},
		{home: "Athletico-PR", away: "Coritiba-PR", hg: 2, ag: 2, season: 2019, day: "2019-05-02"},
		{home: "Flamengo", away: "Atlético-MG", hg: 3, ag: 1, season: 2019, day: "2019-05-03"},
	})
	// The two Atléticos must remain distinct clubs.
	mg, _, _, okMG := s.ResolveTeam("Atlético-MG")
	pr, _, _, okPR := s.ResolveTeam("Athletico-PR")
	if !okMG || !okPR {
		t.Fatalf("resolve failed: mg=%v pr=%v", okMG, okPR)
	}
	if mg == pr {
		t.Fatalf("Atlético-MG and Athletico-PR collapsed to same key %q", mg)
	}
	if mg != "atletico mg" || pr != "atletico pr" {
		t.Errorf("keys = %q / %q, want atletico mg / atletico pr", mg, pr)
	}
}

func TestResolveTeamAmbiguous(t *testing.T) {
	s := buildStore([]row{
		{home: "Atlético-MG", away: "X-MG", hg: 1, ag: 0, season: 2019, day: "2019-05-01"},
		{home: "Athletico-PR", away: "Y-PR", hg: 1, ag: 0, season: 2019, day: "2019-05-02"},
	})
	// A bare "Atletico" is ambiguous between MG and PR.
	_, _, cands, ok := s.ResolveTeam("Atletico")
	if ok {
		t.Fatalf("expected ambiguity, got a confident match")
	}
	if len(cands) < 2 {
		t.Errorf("want >=2 candidates, got %v", cands)
	}
}

func TestExactDuplicateRowsDropped(t *testing.T) {
	// Two identical rows from the SAME source collapse to one.
	s := buildStore([]row{
		{home: "Flamengo-RJ", away: "Vasco-RJ", hg: 2, ag: 1, season: 2015, day: "2015-06-01", source: "a.csv"},
		{home: "Flamengo-RJ", away: "Vasco-RJ", hg: 2, ag: 1, season: 2015, day: "2015-06-01", source: "a.csv"},
	})
	if len(s.Matches) != 1 {
		t.Errorf("want 1 row after exact-dup removal, got %d", len(s.Matches))
	}
}

func TestCrossSourceKeptThenCleaned(t *testing.T) {
	// The same fixture from two sources is KEPT at load (so completeness can be
	// judged later) but CleanBySource keeps only the richer source per season.
	s := buildStore([]row{
		{home: "Flamengo-RJ", away: "Vasco-RJ", hg: 2, ag: 1, season: 2015, day: "2015-06-01", source: "Brasileirao_Matches.csv"},
		{home: "Flamengo", away: "Vasco", hg: 2, ag: 1, season: 2015, day: "2015-06-02", source: "BR-Football-Dataset.csv"},
	})
	if len(s.Matches) != 2 {
		t.Fatalf("want both rows kept at load, got %d", len(s.Matches))
	}
	clean := CleanBySource(s.Matches)
	if len(clean) != 1 {
		t.Errorf("CleanBySource should keep 1 source's row, got %d", len(clean))
	}
	if clean[0].Source != "Brasileirao_Matches.csv" {
		t.Errorf("tie should prefer curated source, got %s", clean[0].Source)
	}
}

func TestFindMatchesFilters(t *testing.T) {
	s := buildStore([]row{
		{home: "Flamengo", away: "Santos-SP", hg: 1, ag: 0, season: 2018, day: "2018-05-01"},
		{home: "Flamengo", away: "Santos-SP", hg: 2, ag: 2, season: 2019, day: "2019-05-01"},
		{home: "Palmeiras", away: "Flamengo", hg: 0, ag: 0, season: 2019, day: "2019-06-01"},
	})
	fk, _, _, _ := s.ResolveTeam("Flamengo")
	if got := s.FindMatches(MatchFilter{TeamKey: fk}); len(got) != 3 {
		t.Errorf("Flamengo matches = %d, want 3", len(got))
	}
	if got := s.FindMatches(MatchFilter{TeamKey: fk, Season: 2019}); len(got) != 2 {
		t.Errorf("Flamengo 2019 = %d, want 2", len(got))
	}
	if got := s.FindMatches(MatchFilter{HomeKey: fk}); len(got) != 2 {
		t.Errorf("Flamengo home = %d, want 2", len(got))
	}
	sk, _, _, _ := s.ResolveTeam("Santos-SP")
	if got := s.FindMatches(MatchFilter{TeamKey: fk, OpponentKey: sk}); len(got) != 2 {
		t.Errorf("Flamengo vs Santos = %d, want 2", len(got))
	}
}

func TestResolveCompetition(t *testing.T) {
	cases := map[string]string{
		"Brasileirão":    CompSerieA,
		"brasileirao":    CompSerieA,
		"Serie A":        CompSerieA,
		"Copa do Brasil": CompCopaBrasil,
		"libertadores":   CompLibertadores,
		"":               "",
	}
	for in, want := range cases {
		got, ok := ResolveCompetition(in)
		if !ok || got != want {
			t.Errorf("ResolveCompetition(%q) = (%q,%v), want %q", in, got, ok, want)
		}
	}
	if _, ok := ResolveCompetition("Premier League"); ok {
		t.Errorf("unknown competition should not resolve")
	}
}
