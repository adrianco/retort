package soccer

import "testing"

func TestNormalizeTeamKey(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"plain lowercase", "flamengo", "flamengo"},
		{"state suffix with hyphen no space", "Flamengo-RJ", "flamengo"},
		{"state suffix with spaced hyphen", "América - MG", "america"},
		{"accents stripped", "São Paulo", "sao paulo"},
		{"gremio accent", "Grêmio", "gremio"},
		{"extra whitespace collapsed", "  Palmeiras   SP ", "palmeiras sp"},
		{"periods removed from abbreviation", "A.b.c. - RN", "abc"},
		{"already uppercase abbreviation with suffix", "ABC - RN", "abc"},
		{"mixed case suffix", "Cuiaba-MT", "cuiaba"},
		{"non team-suffix hyphen kept", "Barcelona-EQU", "barcelona-equ"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := NormalizeTeamKey(tc.in)
			if got != tc.want {
				t.Errorf("NormalizeTeamKey(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

func TestNormalizeTeamKeyAliases(t *testing.T) {
	cases := []struct {
		a, b string
	}{
		{"Atletico-MG", "Atlético Mineiro"},
		{"Athletico-PR", "Atlético Paranaense"},
		{"Flamengo-RJ", "Flamengo"},
	}
	for _, tc := range cases {
		ka := NormalizeTeamKey(tc.a)
		kb := NormalizeTeamKey(tc.b)
		if ka != kb {
			t.Errorf("expected alias match: NormalizeTeamKey(%q)=%q != NormalizeTeamKey(%q)=%q", tc.a, ka, tc.b, kb)
		}
	}
}
