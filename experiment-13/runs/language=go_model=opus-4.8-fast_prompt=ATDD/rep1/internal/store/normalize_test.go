package store

import "testing"

func TestNormalizeTeamFoldsAccentsAndStripsSuffix(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":     "palmeiras",
		"Flamengo-RJ":      "flamengo",
		"Grêmio":           "gremio",
		"Avaí":             "avai",
		"São Paulo":        "sao paulo",
		"Nacional (URU)":   "nacional",
		"América - MG":     "america",
		"Atlético Mineiro": "atletico mineiro",
	}
	for in, want := range cases {
		if got := NormalizeTeam(in); got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestCleanTeamNameRemovesSuffixesForDisplay(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":   "Palmeiras",
		"América - MG":   "América",
		"Nacional (URU)": "Nacional",
		"Flamengo":       "Flamengo",
	}
	for in, want := range cases {
		if got := CleanTeamName(in); got != want {
			t.Errorf("CleanTeamName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseStateSuffix(t *testing.T) {
	if got := parseStateSuffix("Atletico-MG"); got != "mg" {
		t.Errorf("expected mg, got %q", got)
	}
	if got := parseStateSuffix("Flamengo"); got != "" {
		t.Errorf("expected no state, got %q", got)
	}
	if got := parseStateSuffix("Barcelona-EQU"); got != "" {
		t.Errorf("expected no UF for foreign club, got %q", got)
	}
}

func TestIdentityKeyDistinguishesStates(t *testing.T) {
	mg := identityKey("atletico", "mg")
	pr := identityKey("athletico", "pr")
	if mg == pr {
		t.Errorf("expected distinct identity keys, both %q", mg)
	}
	base, state := splitIdentity(mg)
	if base != "atletico" || state != "mg" {
		t.Errorf("splitIdentity(%q) = (%q,%q)", mg, base, state)
	}
	b2, s2 := splitIdentity("flamengo")
	if b2 != "flamengo" || s2 != "" {
		t.Errorf("splitIdentity without state = (%q,%q)", b2, s2)
	}
}

func TestParseDateFormats(t *testing.T) {
	cases := map[string]string{
		"2023-09-24":          "2023-09-24",
		"2012-05-19 18:30:00": "2012-05-19",
		"29/03/2003":          "2003-03-29",
	}
	for in, want := range cases {
		tm, ok := ParseDate(in)
		if !ok {
			t.Errorf("ParseDate(%q) failed", in)
			continue
		}
		if got := tm.Format("2006-01-02"); got != want {
			t.Errorf("ParseDate(%q) = %q, want %q", in, got, want)
		}
	}
	if _, ok := ParseDate("not a date"); ok {
		t.Errorf("expected parse failure for garbage input")
	}
}

func TestNormalizeCompetition(t *testing.T) {
	cases := map[string]string{
		"Serie A":               CompBrasileirao,
		"Campeonato Brasileiro": CompBrasileirao,
		"Brasileirão":           CompBrasileirao,
		"Copa do Brasil":        CompCopaDoBrasil,
		"Copa Libertadores":     CompLibertadores,
		"Serie B":               "Serie B",
	}
	for in, want := range cases {
		if got := NormalizeCompetition(in); got != want {
			t.Errorf("NormalizeCompetition(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseGoalHandlesFloatsAndBlanks(t *testing.T) {
	if v, ok := parseGoal("1.0"); !ok || v != 1 {
		t.Errorf("parseGoal(1.0) = %d,%v", v, ok)
	}
	if v, ok := parseGoal("3"); !ok || v != 3 {
		t.Errorf("parseGoal(3) = %d,%v", v, ok)
	}
	if _, ok := parseGoal(""); ok {
		t.Errorf("parseGoal(empty) should be invalid")
	}
}
