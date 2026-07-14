// Context: Brazilian Soccer MCP Server.
// File: dedup_test.go
// Purpose: Tests for cross-dataset match deduplication. The provided files
// overlap heavily (the same Brasileirão fixture appears in up to three files),
// which would otherwise multiply standings, head-to-head and statistics.
package soccer

import "testing"

func TestDedupeMatchesAcrossSources(t *testing.T) {
	in := []Match{
		// Same fixture from three different source files (note name variation
		// and the "Serie A" competition label that should fold into Brasileirão).
		{Competition: CompBrasileirao, Season: 2019, Round: "30", HasDate: true, Date: d("2019-11-03"),
			HomeTeam: "Flamengo", AwayTeam: "Corinthians", HomeGoals: 4, AwayGoals: 1, HasScore: true, Source: "novo"},
		{Competition: CompBrasileirao, Season: 2019, HasDate: true, Date: d("2019-11-03"),
			HomeTeam: "Flamengo", AwayTeam: "Corinthians", HomeGoals: 4, AwayGoals: 1, HasScore: true, Source: "brasileirao"},
		{Competition: "Serie A", Season: 2019, HasDate: true, Date: d("2019-11-03"),
			HomeTeam: "Flamengo", AwayTeam: "Corinthians", HomeGoals: 4, AwayGoals: 1, HasScore: true, Source: "br-football"},
		// A genuinely different fixture (reverse leg) must survive.
		{Competition: CompBrasileirao, Season: 2019, Round: "11", HasDate: true, Date: d("2019-07-21"),
			HomeTeam: "Corinthians", AwayTeam: "Flamengo", HomeGoals: 1, AwayGoals: 1, HasScore: true, Source: "novo"},
		// Same teams/season but a different competition is a different match.
		{Competition: CompCopaDoBrasil, Season: 2019, HasDate: true, Date: d("2019-06-04"),
			HomeTeam: "Flamengo", AwayTeam: "Corinthians", HomeGoals: 1, AwayGoals: 0, HasScore: true, Source: "novo"},
	}
	out := dedupeMatches(in)
	if len(out) != 3 {
		t.Fatalf("dedupeMatches kept %d, want 3", len(out))
	}
	// The surviving Brasileirão home fixture should retain the richer record
	// (the one carrying a round number).
	var found bool
	for _, m := range out {
		if m.HomeTeam == "Flamengo" && m.AwayTeam == "Corinthians" && m.Competition == CompBrasileirao {
			found = true
			if m.Round != "30" {
				t.Errorf("kept record without round info: %+v", m)
			}
		}
	}
	if !found {
		t.Errorf("expected the deduped Flamengo-Corinthians Brasileirão fixture to survive")
	}
}

func TestBRFootballMapsSerieAToBrasileirao(t *testing.T) {
	// Already covered indirectly, but assert the competition normalization that
	// makes cross-file dedup possible.
	if got := normalizeCompetitionFamily("Serie A"); got != normalizeCompetitionFamily(CompBrasileirao) {
		t.Errorf("Serie A family %q != Brasileirão family %q", got, normalizeCompetitionFamily(CompBrasileirao))
	}
	if normalizeCompetitionFamily("Serie B") == normalizeCompetitionFamily(CompBrasileirao) {
		t.Errorf("Serie B should not fold into Brasileirão")
	}
}
