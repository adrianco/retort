package soccer

import "testing"

func TestRealStandings2019Champion(t *testing.T) {
	kb := loadRealKB(t)
	table := kb.Standings("Brasileirão", 2019)
	if len(table) != 20 {
		t.Fatalf("2019 Serie A teams = %d, want 20", len(table))
	}
	if !TeamsMatch(table[0].Team, "Flamengo") {
		t.Errorf("2019 champion = %q, want Flamengo", table[0].Team)
	}
	// Flamengo won the 2019 Brasileirão with 90 points.
	if table[0].Points() != 90 {
		t.Errorf("champion points = %d, want 90", table[0].Points())
	}
}

func TestRealBrazilianPlayerCount(t *testing.T) {
	kb := loadRealKB(t)
	br := kb.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(br) != 827 {
		t.Errorf("Brazilian players = %d, want 827", len(br))
	}
}

func TestRealPlayerByName(t *testing.T) {
	kb := loadRealKB(t)
	got := kb.SearchPlayers(PlayerFilter{Name: "Neymar"})
	if len(got) == 0 {
		t.Fatal("Neymar not found")
	}
	if got[0].Nationality != "Brazil" {
		t.Errorf("nationality = %q", got[0].Nationality)
	}
}

func TestRealPlayersByBrazilianClub(t *testing.T) {
	kb := loadRealKB(t)
	// Santos is one of the Brazilian clubs present in the FIFA dataset.
	got := kb.SearchPlayers(PlayerFilter{Club: "Santos", Nationality: "Brazil"})
	if len(got) == 0 {
		t.Fatal("no Brazilian players at Santos")
	}
}

func TestRealFlaFluHeadToHead(t *testing.T) {
	kb := loadRealKB(t)
	h := kb.HeadToHead("Flamengo", "Fluminense")
	if len(h.Matches) == 0 {
		t.Fatal("no Fla-Flu matches found")
	}
	total := h.Team1Wins + h.Team2Wins + h.Draws
	if total == 0 {
		t.Errorf("h2h tally empty for %d matches", len(h.Matches))
	}
}

func TestRealCompetitionAverageGoals(t *testing.T) {
	kb := loadRealKB(t)
	cs := kb.CompetitionStats(MatchFilter{Competition: "Brasileirão"})
	if cs.Matches == 0 {
		t.Fatal("no Brasileirão matches")
	}
	avg := cs.AvgGoals()
	// Sanity: real-world league averages sit roughly between 2 and 3.5.
	if avg < 2.0 || avg > 3.5 {
		t.Errorf("avg goals = %.2f, outside sane range", avg)
	}
}
