package soccer

import "testing"

func TestCleanTeamName(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":   "Palmeiras",
		"América - MG":   "América",
		"Nacional (URU)": "Nacional",
		"Barcelona-EQU":  "Barcelona",
		`"Flamengo-RJ"`:  "Flamengo",
		"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ": "Boavista Sport Club",
		"Santos": "Santos",
	}
	for in, want := range cases {
		if got := CleanTeamName(in); got != want {
			t.Errorf("CleanTeamName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestTeamKeyNormalization(t *testing.T) {
	// All of these must collapse onto the same canonical key.
	groups := [][]string{
		{"Palmeiras", "Palmeiras-SP", `"Palmeiras-SP"`},
		{"São Paulo", "Sao Paulo", "São Paulo-SP"},
		{"Grêmio", "Gremio", "Gremio-RS"},
		{"Atlético Mineiro", "Atletico Mineiro"},
	}
	for _, g := range groups {
		first := TeamKey(g[0])
		if first == "" {
			t.Fatalf("empty key for %q", g[0])
		}
		for _, name := range g[1:] {
			if got := TeamKey(name); got != first {
				t.Errorf("TeamKey(%q)=%q, want %q (to match %q)", name, got, first, g[0])
			}
		}
	}
}

func TestTeamKeyFullNameContainsShort(t *testing.T) {
	// A full club name should contain the short form so queries match.
	full := TeamKey("Sport Club Corinthians Paulista")
	short := TeamKey("Corinthians")
	if !teamKeyMatches(full, short) {
		t.Errorf("expected %q to match query %q", full, short)
	}
}

func TestSplitTeam(t *testing.T) {
	cases := []struct {
		raw                string
		base, region, disp string
	}{
		{"Atletico-MG", "atletico", "mg", "Atletico"},
		{"Atlético-GO", "atletico", "go", "Atlético"},
		{"Nacional (URU)", "nacional", "uru", "Nacional"},
		{"Flamengo-RJ", "flamengo", "rj", "Flamengo"},
		{"Atletico Mineiro", "atletico mineiro", "", "Atletico Mineiro"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club", "rj", "Boavista Sport Club"},
	}
	for _, c := range cases {
		base, region, disp := splitTeam(c.raw)
		if base != c.base || region != c.region || disp != c.disp {
			t.Errorf("splitTeam(%q) = (%q,%q,%q), want (%q,%q,%q)",
				c.raw, base, region, disp, c.base, c.region, c.disp)
		}
	}
}

func TestNormalizeCompetition(t *testing.T) {
	cases := map[string]string{
		"Serie A":           CompBrasileiraoA,
		"Brasileirão":       CompBrasileiraoA,
		"Serie B":           CompBrasileiraoB,
		"Serie C":           CompBrasileiraoC,
		"Copa do Brasil":    CompCopaDoBrasil,
		"Libertadores":      CompLibertadores,
		"Copa Libertadores": CompLibertadores,
	}
	for in, want := range cases {
		if got := NormalizeCompetition(in); got != want {
			t.Errorf("NormalizeCompetition(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestCompetitionMatches(t *testing.T) {
	if !competitionMatches(CompBrasileiraoA, "Brasileirão") {
		t.Error("expected Brasileirão query to match Série A")
	}
	if competitionMatches(CompBrasileiraoA, "Libertadores") {
		t.Error("did not expect Libertadores query to match Série A")
	}
	if !competitionMatches(CompLibertadores, "") {
		t.Error("empty competition query should match everything")
	}
}
