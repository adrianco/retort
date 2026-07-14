// Context: Brazilian Soccer MCP Server.
// File: canonical_test.go
// Purpose: Tests for canonicalizing the major Brazilian clubs to a single
// display name so that the many spelling variants across datasets (state
// suffixes, "FC"/"EC" tags, "da Gama", "Mineiro"/"Paranaense") collapse into
// one entity for dedup, standings and head-to-head.
package soccer

import "testing"

func TestCanonicalName(t *testing.T) {
	groups := map[string][]string{
		"Vasco":        {"Vasco", "Vasco da Gama-RJ", "Vasco Da Gama RJ"},
		"São Paulo":    {"São Paulo", "Sao Paulo-SP", "Sao Paulo FC"},
		"Fortaleza":    {"Fortaleza", "Fortaleza-CE", "Fortaleza FC"},
		"Atlético-MG":  {"Atlético-MG", "Atletico-MG", "Atletico Mineiro"},
		"Athletico-PR": {"Athletico-PR", "Atletico-PR", "Athletico Paranaense"},
		"Grêmio":       {"Grêmio", "Gremio-RS"},
		"Botafogo-RJ":  {"Botafogo-RJ", "Botafogo RJ"},
	}
	for want, variants := range groups {
		for _, v := range variants {
			if got := CanonicalName(v); got != want {
				t.Errorf("CanonicalName(%q) = %q, want %q", v, got, want)
			}
		}
	}
}

func TestCanonicalNameDistinguishesDifferentClubs(t *testing.T) {
	// The two Atléticos are different clubs and must not be merged.
	if CanonicalName("Atletico Mineiro") == CanonicalName("Athletico Paranaense") {
		t.Errorf("Atlético-MG and Athletico-PR must stay distinct")
	}
}

func TestCanonicalNameFallsBackToClean(t *testing.T) {
	// An unknown club is just cleaned, not dropped.
	if got := CanonicalName("Some Random FC-XX"); got == "" {
		t.Errorf("CanonicalName dropped an unknown club: %q", got)
	}
}
