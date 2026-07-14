package soccer

import "testing"

func TestFoldAccents(t *testing.T) {
	cases := map[string]string{
		"São Paulo": "Sao Paulo",
		"Grêmio":    "Gremio",
		"Avaí":      "Avai",
		"Atlético":  "Atletico",
		"Fortaleza": "Fortaleza",
		"Vitória":   "Vitoria",
	}
	for in, want := range cases {
		if got := FoldAccents(in); got != want {
			t.Errorf("FoldAccents(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestSplitBaseState(t *testing.T) {
	cases := []struct {
		raw       string
		wantBase  string
		wantState string
	}{
		{"Palmeiras-SP", "palmeiras", "SP"},
		{"Atlético-MG", "atletico", "MG"},
		{"Athletico-PR", "athletico", "PR"}, // raw base; canonicalized downstream
		{"América - RN", "america", "RN"},
		{"America RN", "america", "RN"},
		{"Nacional (URU)", "nacional", "URU"},
		{"Barcelona-EQU", "barcelona", "EQU"},
		{"Flamengo", "flamengo", ""},
		{"Sao Paulo", "sao paulo", ""},
		{"São Paulo-SP", "sao paulo", "SP"},
	}
	for _, c := range cases {
		base, state := splitBaseState(c.raw)
		if base != c.wantBase || state != c.wantState {
			t.Errorf("splitBaseState(%q) = (%q,%q), want (%q,%q)", c.raw, base, state, c.wantBase, c.wantState)
		}
	}
}

func TestNormalizeTeamAliases(t *testing.T) {
	// Spelled-out BR-Football names map to the state-suffixed identity.
	cases := map[string]string{
		"Atletico Mineiro":    "atletico mg",
		"Atletico Paranaense": "atletico pr",
		"Atletico Goianiense": "atletico go",
		"Palmeiras-SP":        "palmeiras",
		"Flamengo":            "flamengo",
	}
	for in, want := range cases {
		if got := NormalizeTeam(in); got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestDisplayTeam(t *testing.T) {
	cases := map[string]string{
		"Nacional (URU)": "Nacional",
		"Flamengo-RJ":    "Flamengo-RJ", // suffix kept (can be the disambiguator)
		"  Santos  ":     "Santos",
	}
	for in, want := range cases {
		if got := DisplayTeam(in); got != want {
			t.Errorf("DisplayTeam(%q) = %q, want %q", in, got, want)
		}
	}
}
