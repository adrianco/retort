// Package main — Brazilian Soccer MCP Server.
//
// normalize_test.go: Tests for team-name normalization and multi-format date
// parsing. The datasets mix naming conventions ("Palmeiras-SP", "Palmeiras",
// "Nacional (URU)") and date formats (ISO, Brazilian DD/MM/YYYY, with time),
// so these helpers underpin all reliable matching across files.
package main

import (
	"testing"
	"time"
)

func TestNormalizeTeam(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{"Palmeiras-SP", "palmeiras"},
		{"Flamengo-RJ", "flamengo"},
		{"Palmeiras", "palmeiras"},
		{"São Paulo", "sao paulo"},
		{"Grêmio", "gremio"},
		{"Avaí", "avai"},
		{"Nacional (URU)", "nacional"},
		{"Barcelona-EQU", "barcelona"},
		{"América - MG", "america"},
		{"  Santos  ", "santos"},
		{"Atlético-MG", "atletico"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club"},
	}
	for _, c := range cases {
		if got := NormalizeTeam(c.in); got != c.want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestTeamsMatch(t *testing.T) {
	if !TeamsMatch("Palmeiras-SP", "palmeiras") {
		t.Error("expected Palmeiras-SP to match palmeiras")
	}
	if !TeamsMatch("São Paulo", "sao paulo") {
		t.Error("expected accent-insensitive match")
	}
	if TeamsMatch("Flamengo", "Fluminense") {
		t.Error("Flamengo should not match Fluminense")
	}
}

func TestParseDate(t *testing.T) {
	cases := []struct {
		in   string
		want string // RFC3339 date portion
		ok   bool
	}{
		{"2012-05-19 18:30:00", "2012-05-19", true},
		{"2023-09-24", "2023-09-24", true},
		{"29/03/2003", "2003-03-29", true},
		{"", "", false},
		{"not-a-date", "", false},
	}
	for _, c := range cases {
		got, ok := ParseDate(c.in)
		if ok != c.ok {
			t.Errorf("ParseDate(%q) ok = %v, want %v", c.in, ok, c.ok)
			continue
		}
		if ok && got.Format("2006-01-02") != c.want {
			t.Errorf("ParseDate(%q) = %v, want %s", c.in, got.Format(time.RFC3339), c.want)
		}
	}
}
