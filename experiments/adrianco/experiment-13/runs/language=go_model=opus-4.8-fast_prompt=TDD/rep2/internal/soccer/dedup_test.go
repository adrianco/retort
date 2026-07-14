package soccer

import "testing"

// When several datasets cover the same competition+season, DedupedMatches must
// return only the most complete source's matches for that group, leaving
// other groups untouched.
func TestDedupedMatches(t *testing.T) {
	kb := &KB{Matches: []Match{
		// Brasileirão 2019 present in two sources (different naming).
		{Competition: CompBrasileirao, Season: 2019, Source: "Brasileirao_Matches.csv",
			HomeTeam: "Flamengo-RJ", AwayTeam: "Avai-SC", HomeGoals: 6, AwayGoals: 1, HasScore: true},
		{Competition: CompBrasileirao, Season: 2019, Source: "Brasileirao_Matches.csv",
			HomeTeam: "Gremio-RS", AwayTeam: "Avai-SC", HomeGoals: 6, AwayGoals: 1, HasScore: true},
		{Competition: CompBrasileirao, Season: 2019, Source: "novo_campeonato_brasileiro.csv",
			HomeTeam: "Flamengo", AwayTeam: "Avaí", HomeGoals: 6, AwayGoals: 1, HasScore: true},
		// A different competition+season, single source — must be kept.
		{Competition: CompLibertadores, Season: 2019, Source: "Libertadores_Matches.csv",
			HomeTeam: "Flamengo", AwayTeam: "River Plate", HomeGoals: 2, AwayGoals: 1, HasScore: true},
	}}

	got := kb.DedupedMatches(MatchFilter{})
	// Brasileirão 2019: 2 from the bigger source; Libertadores 2019: 1. Total 3.
	if len(got) != 3 {
		t.Fatalf("deduped matches = %d, want 3", len(got))
	}
	for _, m := range got {
		if m.Source == "novo_campeonato_brasileiro.csv" {
			t.Errorf("smaller source should have been dropped: %+v", m)
		}
	}
}
