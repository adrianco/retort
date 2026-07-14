package main

import "testing"

func TestNormalizeTeamName(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Atletico-MG", "Atletico"},
		{"Sport-PE", "Sport"},
		{"Palmeiras", "Palmeiras"},
		{"Flamengo", "Flamengo"},
		{"  Corinthians  ", "Corinthians"},
		{"Santos-SP", "Santos"},
	}
	for _, c := range cases {
		got := normalizeTeamName(c.input)
		if got != c.expected {
			t.Errorf("normalizeTeamName(%q) = %q, want %q", c.input, got, c.expected)
		}
	}
}

func TestTeamNameKey(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "palmeiras"},
		{"São Paulo", "sao paulo"},
		{"Grêmio", "gremio"},
		{"Atlético Mineiro", "atletico mineiro"},
		{"FLAMENGO", "flamengo"},
		{"Fortaleza", "fortaleza"},
	}
	for _, c := range cases {
		got := teamNameKey(c.input)
		if got != c.expected {
			t.Errorf("teamNameKey(%q) = %q, want %q", c.input, got, c.expected)
		}
	}
}

func TestTeamContains(t *testing.T) {
	cases := []struct {
		teamName string
		query    string
		expected bool
	}{
		{"Palmeiras-SP", "palmeiras", true},
		{"Palmeiras-SP", "Palmeiras", true},
		{"Flamengo-RJ", "Flamen", true},
		{"São Paulo", "sao paulo", true},
		{"Grêmio", "Gremio", true},
		{"Corinthians", "Santos", false},
		{"Santos-SP", "Santos", true},
	}
	for _, c := range cases {
		got := teamContains(c.teamName, c.query)
		if got != c.expected {
			t.Errorf("teamContains(%q, %q) = %v, want %v", c.teamName, c.query, got, c.expected)
		}
	}
}

func TestRemoveAccents(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"São Paulo", "Sao Paulo"},
		{"Grêmio", "Gremio"},
		{"Atlético", "Atletico"},
		{"Avaí", "Avai"},
		{"Fortaleza", "Fortaleza"},
		{"Ceará", "Ceara"},
	}
	for _, c := range cases {
		got := removeAccents(c.input)
		if got != c.expected {
			t.Errorf("removeAccents(%q) = %q, want %q", c.input, got, c.expected)
		}
	}
}

func TestParseDate(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"2012-05-19 18:30:00", "2012-05-19"},
		{"2023-09-24", "2023-09-24"},
		{"29/03/2003", "2003-03-29"},
		{"2013-02-12 20:15:00", "2013-02-12"},
	}
	for _, c := range cases {
		got := parseDate(c.input)
		if got != c.expected {
			t.Errorf("parseDate(%q) = %q, want %q", c.input, got, c.expected)
		}
	}
}

func TestCompetitionKey(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"brasileirao", "brasileirao"},
		{"Brasileirão", "brasileirao"},
		{"serie a", "brasileirao"},
		{"Copa do Brasil", "copa_do_brasil"},
		{"copa do brasil", "copa_do_brasil"},
		{"libertadores", "libertadores"},
		{"Copa Libertadores", "libertadores"},
		{"all", "all"},
		{"", "all"},
	}
	for _, c := range cases {
		got := competitionKey(c.input)
		if got != c.expected {
			t.Errorf("competitionKey(%q) = %q, want %q", c.input, got, c.expected)
		}
	}
}
