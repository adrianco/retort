package soccer

import "testing"

func TestCleanTeamName(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":         "Palmeiras",
		"América - MG":         "América",
		"Nacional (URU)":       "Nacional",
		"Barcelona-EQU":        "Barcelona",
		"  Santos-SP ":         "Santos",
		"Sport Club do Recife": "Sport Club do Recife",
		"Flamengo":             "Flamengo",
	}
	for in, want := range cases {
		if got := CleanTeamName(in); got != want {
			t.Errorf("CleanTeamName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestDisplayNameKeepsSuffix(t *testing.T) {
	cases := map[string]string{
		"América - MG": "América-MG",
		"Palmeiras-SP": "Palmeiras-SP",
		"Flamengo":     "Flamengo",
	}
	for in, want := range cases {
		if got := DisplayName(in); got != want {
			t.Errorf("DisplayName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestNormalizeKeyFoldsAccents(t *testing.T) {
	// Given two spellings of the same club, When normalized, Then the keys match.
	if NormalizeKey("São Paulo-SP") != NormalizeKey("Sao Paulo") {
		t.Errorf("accent folding failed: %q vs %q",
			NormalizeKey("São Paulo-SP"), NormalizeKey("Sao Paulo"))
	}
	if NormalizeKey("Grêmio-RS") != "gremio" {
		t.Errorf("NormalizeKey(Grêmio-RS) = %q, want gremio", NormalizeKey("Grêmio-RS"))
	}
}

func TestTeamMatches(t *testing.T) {
	tests := []struct {
		name  string
		team  string
		query string
		want  bool
	}{
		{"plain matches suffixed", "Flamengo-RJ", "Flamengo", true},
		{"accent-insensitive", "São Paulo-SP", "Sao Paulo", true},
		{"empty query matches all", "Santos-SP", "", true},
		{"non-match", "Santos-SP", "Flamengo", false},
		{"suffixed query disambiguates", "Atlético-GO", "Atletico-MG", false},
		{"suffixed query exact", "Atlético-MG", "Atletico-MG", true},
		{"unsuffixed query matches any atletico", "Atlético-GO", "Atletico", true},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := TeamMatches(tc.team, tc.query); got != tc.want {
				t.Errorf("TeamMatches(%q, %q) = %v, want %v", tc.team, tc.query, got, tc.want)
			}
		})
	}
}
