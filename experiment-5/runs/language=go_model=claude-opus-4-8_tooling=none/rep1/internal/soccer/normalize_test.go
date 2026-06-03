// Context:
//   - BDD-style (Given/When/Then) unit tests for the name- and
//     competition-normalization layer. These run without any data files: they
//     pin down the exact behaviour the rest of the system relies on, in
//     particular that disambiguating state suffixes are preserved in identity
//     keys while user queries match loosely.
package soccer

import "testing"

func TestNormalizeTeam_StripsAccentsAndKeepsSuffix(t *testing.T) {
	// Given a set of raw team names from the datasets
	cases := map[string]string{
		"Palmeiras-SP":   "palmeiras-sp",
		"Grêmio":         "gremio",
		"São Paulo":      "sao paulo",
		"Atlético-MG":    "atletico-mg",
		"América - MG":   "america-mg",
		"Nacional (URU)": "nacional",
		"Flamengo":       "flamengo",
	}
	for raw, want := range cases {
		// When normalized
		got := NormalizeTeam(raw)
		// Then accents are folded, casing lowered and the suffix retained
		if got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", raw, got, want)
		}
	}
}

func TestCleanTeamName_StripsSuffixForDisplay(t *testing.T) {
	// Given a name carrying a state suffix
	// When cleaned for display
	// Then the suffix is removed but accents/casing are preserved
	if got := CleanTeamName("Grêmio-RS"); got != "Grêmio" {
		t.Errorf("CleanTeamName = %q, want %q", got, "Grêmio")
	}
	if got := CleanTeamName("Nacional (URU)"); got != "Nacional" {
		t.Errorf("CleanTeamName = %q, want %q", got, "Nacional")
	}
}

func TestTeamMatches_LooseButSuffixAware(t *testing.T) {
	// Given the normalized identity key for Flamengo
	flamengo := NormalizeTeam("Flamengo-RJ")

	// When a bare query is used, Then it matches
	if !TeamMatches("Flamengo", flamengo) {
		t.Errorf("expected 'Flamengo' to match %q", flamengo)
	}

	// Given two distinct Atlético clubs
	atleticoMG := NormalizeTeam("Atlético-MG")
	atleticoGO := NormalizeTeam("Atlético-GO")

	// When queried with the disambiguating suffix
	// Then only the intended club matches
	if !TeamMatches("Atletico-MG", atleticoMG) {
		t.Errorf("expected 'Atletico-MG' to match %q", atleticoMG)
	}
	if TeamMatches("Atletico-MG", atleticoGO) {
		t.Errorf("'Atletico-MG' must NOT match %q", atleticoGO)
	}
}

func TestCompetitionMatches_Shorthands(t *testing.T) {
	// Given canonical competition names
	// When matched against user shorthands, Then they resolve correctly
	if !CompetitionMatches("brasileirao", CompSerieA) {
		t.Error("'brasileirao' should match Série A")
	}
	if !CompetitionMatches("Serie A", CompSerieA) {
		t.Error("'Serie A' should match Série A")
	}
	if !CompetitionMatches("libertadores", CompLibertadores) {
		t.Error("'libertadores' should match Libertadores")
	}
	if CompetitionMatches("Serie A", CompSerieB) {
		t.Error("'Serie A' must not match Série B")
	}
	// And an empty query matches everything
	if !CompetitionMatches("", CompCopaDoBrasil) {
		t.Error("empty competition query should match anything")
	}
}

func TestCanonicalCompetition_MapsRawLabels(t *testing.T) {
	cases := map[string]string{
		"Serie A":             CompSerieA,
		"Serie B":             CompSerieB,
		"Serie C":             CompSerieC,
		"Copa do Brasil":      CompCopaDoBrasil,
		"Copa Libertadores":   CompLibertadores,
		"Brasileirao Serie A": CompSerieA,
	}
	for raw, want := range cases {
		if got := canonicalCompetition(raw); got != want {
			t.Errorf("canonicalCompetition(%q) = %q, want %q", raw, got, want)
		}
	}
}
