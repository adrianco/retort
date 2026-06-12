package soccer

import "testing"

func TestSearchPlayersByNationalitySorted(t *testing.T) {
	kb := testKB()
	got := kb.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(got) != 3 {
		t.Fatalf("Brazilian players = %d, want 3", len(got))
	}
	// Sorted by Overall descending.
	if got[0].Name != "Neymar Jr" || got[2].Name != "Bruno Henrique" {
		t.Errorf("unexpected order: %v", []string{got[0].Name, got[1].Name, got[2].Name})
	}
}

func TestSearchPlayersByName(t *testing.T) {
	kb := testKB()
	got := kb.SearchPlayers(PlayerFilter{Name: "gabriel"})
	if len(got) != 1 || got[0].Name != "Gabriel Barbosa" {
		t.Fatalf("name search = %+v", got)
	}
}

func TestSearchPlayersByClubPositionRatingAndLimit(t *testing.T) {
	kb := testKB()
	got := kb.SearchPlayers(PlayerFilter{Club: "Flamengo"})
	if len(got) != 2 {
		t.Fatalf("Flamengo players = %d, want 2", len(got))
	}
	got = kb.SearchPlayers(PlayerFilter{Club: "Flamengo", Position: "ST"})
	if len(got) != 1 || got[0].Name != "Gabriel Barbosa" {
		t.Fatalf("position filter = %+v", got)
	}
	got = kb.SearchPlayers(PlayerFilter{MinOverall: 90})
	if len(got) != 2 { // Messi 94, Neymar 92
		t.Fatalf("min overall = %d, want 2", len(got))
	}
	got = kb.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 1})
	if len(got) != 1 || got[0].Name != "Neymar Jr" {
		t.Fatalf("limit = %+v", got)
	}
}
