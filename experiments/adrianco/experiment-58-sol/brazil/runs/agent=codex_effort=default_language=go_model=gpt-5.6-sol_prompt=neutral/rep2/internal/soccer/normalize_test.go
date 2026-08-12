package soccer

import "testing"

func TestNormalizeTeamVariations(t *testing.T) {
	tests := map[string]string{
		"Palmeiras-SP":                           "palmeiras",
		"América - MG":                           "america",
		"São Paulo FC":                           "sao paulo",
		"Sport Club Corinthians Paulista":        "corinthians",
		"Boavista Sport Club (antigo nome) - RJ": "boavista sport club",
		"Grêmio":                                 "gremio",
	}
	for input, want := range tests {
		if got := NormalizeTeam(input); got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", input, got, want)
		}
	}
}

func TestParseSupportedDates(t *testing.T) {
	for _, input := range []string{"2023-09-24", "2023-09-24 20:00:00", "29/03/2003"} {
		got, err := parseDate(input)
		if err != nil {
			t.Fatalf("parseDate(%q): %v", input, err)
		}
		if got.Year() < 2000 {
			t.Fatalf("parseDate(%q) returned %v", input, got)
		}
	}
}
