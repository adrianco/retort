// Context: Finer-grained unit tests for the internals that the acceptance suite
// drives indirectly — name normalization, competition resolution, score/date
// parsing. These guard the tricky data-cleaning rules (state-suffix stripping,
// accent folding, multiple date formats, float-encoded goals) that make the
// black-box acceptance scenarios pass.
package main

import "testing"

func TestNormTeamStripsSuffixesAndAccents(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":   "palmeiras",
		"Flamengo-RJ":    "flamengo",
		"América - MG":   "america",
		"Nacional (URU)": "nacional",
		"Barcelona-EQU":  "barcelona",
		"São Paulo":      "sao paulo",
		"Sao Paulo":      "sao paulo",
		"Grêmio":         "gremio",
		"Atlético-MG":    "atletico",
	}
	for in, want := range cases {
		if got := normTeam(in); got != want {
			t.Errorf("normTeam(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestDisplayTeamKeepsAccents(t *testing.T) {
	if got := displayTeam("São Paulo-SP"); got != "São Paulo" {
		t.Errorf("displayTeam = %q, want %q", got, "São Paulo")
	}
}

func TestResolveCompetition(t *testing.T) {
	cases := map[string]string{
		"Libertadores":      "Copa Libertadores",
		"copa libertadores": "Copa Libertadores",
		"Copa do Brasil":    "Copa do Brasil",
		"Brasileirão":       "Brasileirão",
		"brasileirao":       "Brasileirão",
		"Serie A":           "Brasileirão",
		"":                  "",
	}
	for in, want := range cases {
		if got := resolveCompetition(in); got != want {
			t.Errorf("resolveCompetition(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseGoalAcceptsFloats(t *testing.T) {
	if g, ok := parseGoal("2.0"); !ok || g != 2 {
		t.Errorf("parseGoal(2.0) = %d,%v want 2,true", g, ok)
	}
	if g, ok := parseGoal("3"); !ok || g != 3 {
		t.Errorf("parseGoal(3) = %d,%v want 3,true", g, ok)
	}
	if _, ok := parseGoal(""); ok {
		t.Errorf("parseGoal(empty) should report not-ok")
	}
}

func TestParseDateFormats(t *testing.T) {
	for _, s := range []string{"2012-05-19 18:30:00", "2023-09-24", "29/03/2003"} {
		if _, ok := parseDate(s); !ok {
			t.Errorf("parseDate(%q) failed", s)
		}
	}
	if _, ok := parseDate("not-a-date"); ok {
		t.Errorf("parseDate(garbage) should fail")
	}
}
