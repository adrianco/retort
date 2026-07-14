// Context
// -------
// Unit tests for the normalization helpers. These are data-independent and fast,
// covering the team-name and date-format edge cases called out in the spec's
// "Data Quality Notes" (state suffixes, accents, multiple date formats).
package soccer

import "testing"

func TestNormalizeTeamName(t *testing.T) {
	// Given various source spellings, When normalized, Then the state/country
	// suffix is removed while accents are preserved.
	cases := map[string]string{
		"Palmeiras-SP":             "Palmeiras",
		"Flamengo-RJ":              "Flamengo",
		"Nacional (URU)":           "Nacional",
		"Barcelona-EQU":            "Barcelona",
		"São Paulo":                "São Paulo",
		"Atlético-MG":              "Atlético",
		"Boavista Sport Club - RJ": "Boavista Sport Club",
	}
	for in, want := range cases {
		if got := NormalizeTeamName(in); got != want {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestTeamKeyUnifiesVariants(t *testing.T) {
	// Given two spellings of the same club, When keyed, Then keys are equal.
	if TeamKey("Palmeiras-SP") != TeamKey("Palmeiras") {
		t.Error("expected Palmeiras-SP and Palmeiras to share a key")
	}
	if TeamKey("São Paulo") != TeamKey("Sao Paulo") {
		t.Error("expected accented and ASCII São Paulo to share a key")
	}
}

func TestStateFromName(t *testing.T) {
	cases := map[string]string{
		"Atletico-MG":    "MG",
		"Nacional (URU)": "URU",
		"Palmeiras":      "",
		"Barcelona-EQU":  "EQU",
	}
	for in, want := range cases {
		if got := StateFromName(in); got != want {
			t.Errorf("StateFromName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseDateFormats(t *testing.T) {
	// Given the three documented date formats, When parsed, Then each yields
	// the same calendar date.
	inputs := []string{"2019-09-24", "2019-09-24 18:30:00", "24/09/2019"}
	for _, in := range inputs {
		got, _, ok := ParseDate(in)
		if !ok {
			t.Fatalf("ParseDate(%q) failed", in)
		}
		if got.Year() != 2019 || got.Month() != 9 || got.Day() != 24 {
			t.Errorf("ParseDate(%q) = %v, want 2019-09-24", in, got)
		}
	}
	if _, _, ok := ParseDate("not a date"); ok {
		t.Error("expected ParseDate to fail on garbage input")
	}
}
