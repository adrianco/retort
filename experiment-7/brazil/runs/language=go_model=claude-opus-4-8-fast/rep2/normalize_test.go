// Brazilian Soccer MCP Server
//
// File: normalize_test.go
// Responsibility: Unit tests for the normalization layer — team-name folding,
// state-suffix handling, accent stripping, date parsing and numeric coercion.
// These are the foundation the query engine relies on, so they are tested in
// isolation with table-driven cases.
package main

import "testing"

func TestStripAccents(t *testing.T) {
	cases := map[string]string{
		"São Paulo": "Sao Paulo",
		"Grêmio":    "Gremio",
		"Avaí":      "Avai",
		"Fortaleza": "Fortaleza",
		"Atlético":  "Atletico",
	}
	for in, want := range cases {
		if got := stripAccents(in); got != want {
			t.Errorf("stripAccents(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestTeamBaseKey(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":   "palmeiras",
		"Palmeiras":      "palmeiras",
		"Flamengo - RJ":  "flamengo",
		"Grêmio-RS":      "gremio",
		"Nacional (URU)": "nacional",
		"São Paulo-SP":   "sao paulo",
	}
	for in, want := range cases {
		if got := teamBaseKey(in); got != want {
			t.Errorf("teamBaseKey(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestTeamFullKeyDistinguishesClubs(t *testing.T) {
	// Two different clubs that share a base name must not collide.
	mg := teamFullKey("Atletico-MG", "")
	pr := teamFullKey("Atletico-PR", "")
	if mg == pr {
		t.Fatalf("Atletico-MG and Atletico-PR collided: both %q", mg)
	}
	if mg != "atletico-mg" || pr != "atletico-pr" {
		t.Errorf("unexpected keys: mg=%q pr=%q", mg, pr)
	}
	// A name without a suffix should adopt the state column.
	if k := teamFullKey("Atletico", "MG"); k != "atletico-mg" {
		t.Errorf("teamFullKey with state column = %q, want atletico-mg", k)
	}
}

func TestSideMatchesQuery(t *testing.T) {
	// Bare query is suffix-insensitive.
	if !sideMatchesQuery("Flamengo", "flamengo-rj", "flamengo") {
		t.Error("bare 'Flamengo' should match flamengo-rj")
	}
	// Suffixed query is exact.
	if sideMatchesQuery("Atletico-MG", "atletico-pr", "atletico") {
		t.Error("'Atletico-MG' must not match atletico-pr")
	}
	if !sideMatchesQuery("Atletico-MG", "atletico-mg", "atletico") {
		t.Error("'Atletico-MG' should match atletico-mg")
	}
}

func TestParseDate(t *testing.T) {
	cases := []struct {
		in   string
		ok   bool
		year int
	}{
		{"2012-05-19 18:30:00", true, 2012},
		{"2023-09-24", true, 2023},
		{"29/03/2003", true, 2003},
		{"NA", false, 0},
		{"", false, 0},
		{"not-a-date", false, 0},
	}
	for _, c := range cases {
		got, ok := parseDate(c.in)
		if ok != c.ok {
			t.Errorf("parseDate(%q) ok = %v, want %v", c.in, ok, c.ok)
			continue
		}
		if ok && got.Year() != c.year {
			t.Errorf("parseDate(%q) year = %d, want %d", c.in, got.Year(), c.year)
		}
	}
}

func TestAtoi(t *testing.T) {
	cases := []struct {
		in   string
		want int
		ok   bool
	}{
		{"3", 3, true},
		{"4.0", 4, true},
		{`"7"`, 7, true},
		{"NA", 0, false},
		{"", 0, false},
	}
	for _, c := range cases {
		got, ok := atoi(c.in)
		if got != c.want || ok != c.ok {
			t.Errorf("atoi(%q) = (%d,%v), want (%d,%v)", c.in, got, ok, c.want, c.ok)
		}
	}
}
