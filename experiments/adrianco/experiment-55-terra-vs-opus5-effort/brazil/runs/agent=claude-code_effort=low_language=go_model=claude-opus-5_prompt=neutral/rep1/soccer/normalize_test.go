// normalize_test.go covers the team name and competition normalisation rules
// in isolation, without touching the CSV data.
package soccer

import "testing"

func TestCanonicalTeamHandlesNameVariations(t *testing.T) {
	same := [][]string{
		{"Palmeiras-SP", "Palmeiras", "palmeiras", "Sociedade Esportiva Palmeiras"},
		{"Flamengo-RJ", "Flamengo", "FLAMENGO"},
		{"São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo FC"},
		{"Grêmio", "Gremio", "Gremio-RS"},
		{"Athletico-PR", "Atlético-PR", "Athletico Paranaense", "Athletico Paranaense - PR"},
		{"Atlético-MG", "Atletico Mineiro", "América - MG"[0:0] + "Atletico-MG"},
		{"Vasco", "Vasco da Gama-RJ", "Vasco da Gama - RJ", "Vasco Da Gama RJ"},
		{"Sport-PE", "Sport Recife"},
		{"América - MG", "America-MG", "America MG", "América Mineiro"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Boavista"},
	}
	for _, group := range same {
		want := CanonicalTeam(group[0])
		if want == "" {
			t.Fatalf("CanonicalTeam(%q) is empty", group[0])
		}
		for _, name := range group[1:] {
			if got := CanonicalTeam(name); got != want {
				t.Errorf("CanonicalTeam(%q) = %q, want %q (same as %q)", name, got, want, group[0])
			}
		}
	}
}

func TestCanonicalTeamKeepsDistinctClubsApart(t *testing.T) {
	distinct := [][2]string{
		{"Atlético-MG", "Athletico-PR"},
		{"Atlético-MG", "Atlético-GO"},
		{"América-MG", "América-RN"},
		{"Fluminense", "Fluminense PI"},
		{"Flamengo", "Fluminense"},
		{"Nacional (URU)", "Atlético Nacional"},
	}
	for _, d := range distinct {
		if CanonicalTeam(d[0]) == CanonicalTeam(d[1]) {
			t.Errorf("%q and %q collapsed to the same key %q", d[0], d[1], CanonicalTeam(d[0]))
		}
	}
}

func TestTeamMatchesIsForgiving(t *testing.T) {
	cases := []struct {
		query, canonical string
		want             bool
	}{
		{"Flamengo", CanonicalTeam("Flamengo-RJ"), true},
		{"flamengo", CanonicalTeam("Flamengo"), true},
		{"Atletico", CanonicalTeam("Atlético-MG"), true}, // no state given: matches either
		{"Atlético-GO", CanonicalTeam("Atlético-MG"), false},
		{"Sao Paulo", CanonicalTeam("São Paulo-SP"), true},
		{"Santos", CanonicalTeam("Flamengo"), false},
	}
	for _, c := range cases {
		if got := TeamMatches(c.query, c.canonical); got != c.want {
			t.Errorf("TeamMatches(%q, %q) = %v, want %v", c.query, c.canonical, got, c.want)
		}
	}
}

func TestFoldAccents(t *testing.T) {
	cases := map[string]string{
		"São Paulo": "sao paulo",
		"Grêmio":    "gremio",
		"Avaí":      "avai",
		"Fortaleza": "fortaleza",
		"Atlético":  "atletico",
	}
	for in, want := range cases {
		if got := FoldAccents(in); got != want {
			t.Errorf("FoldAccents(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestResolveCompetition(t *testing.T) {
	cases := map[string]string{
		"Brasileirão":       CompSerieA,
		"brasileirao":       CompSerieA,
		"Serie A":           CompSerieA,
		"Série B":           CompSerieB,
		"Copa do Brasil":    CompCopaBrasil,
		"Libertadores":      CompLibertadores,
		"Copa Libertadores": CompLibertadores,
		"handball":          "",
	}
	for in, want := range cases {
		if got := ResolveCompetition(in); got != want {
			t.Errorf("ResolveCompetition(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestPositionMatches(t *testing.T) {
	if !PositionMatches("forward", "ST") {
		t.Error("forward should match ST")
	}
	if !PositionMatches("GK", "GK") {
		t.Error("GK should match GK")
	}
	if PositionMatches("goalkeeper", "CB") {
		t.Error("goalkeeper should not match CB")
	}
	if !PositionMatches("", "CB") {
		t.Error("empty filter should match anything")
	}
}
