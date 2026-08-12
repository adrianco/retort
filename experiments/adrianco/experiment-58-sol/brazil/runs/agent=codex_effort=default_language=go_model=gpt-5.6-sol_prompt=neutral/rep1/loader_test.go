package main

import (
	"path/filepath"
	"testing"
	"time"
)

func TestLoadAllProvidedDatasets(t *testing.T) {
	s, err := LoadStore(filepath.Join("data", "kaggle"))
	if err != nil {
		t.Fatal(err)
	}
	if len(s.matches) != 23954 {
		t.Fatalf("loaded %d matches, want 23954", len(s.matches))
	}
	if len(s.players) != 18207 {
		t.Fatalf("loaded %d players, want 18207", len(s.players))
	}
	for _, source := range []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv"} {
		if got := s.Matches(MatchFilter{Source: source, Limit: 1}); len(got) != 1 {
			t.Errorf("source %s is not queryable", source)
		}
	}
	if got := s.Players(PlayerFilter{Name: "L. Messi", Limit: 1}); len(got) != 1 || got[0].Overall != 94 {
		t.Fatalf("FIFA data not queryable: %+v", got)
	}
	standings := s.Standings("Brasileirão", 2019, 1)
	if len(standings) != 1 || normalizeTeam(standings[0].Team) != "flamengo" || standings[0].Matches != 38 || standings[0].Points != 90 {
		t.Fatalf("2019 standings should use one authoritative feed: %+v", standings)
	}
	start := time.Now()
	if got := s.Matches(MatchFilter{Team: "Flamengo", Season: 2022, Limit: 20}); len(got) == 0 {
		t.Fatal("expected a Flamengo match")
	}
	// The requirement is <2s for simple lookups. The MCP process loads once at startup,
	// so this measures the steady-state path (even under the race detector).
	if elapsed := time.Since(start); elapsed > 2*time.Second {
		t.Errorf("lookups took %s, want <=2s", elapsed)
	}
}

func TestParseSupportedDateFormats(t *testing.T) {
	for _, date := range []string{"2023-09-24", "2012-05-19 18:30:00", "29/03/2003"} {
		if _, err := parseDate(date); err != nil {
			t.Errorf("parseDate(%q): %v", date, err)
		}
	}
}
