package main

import (
	"regexp"
	"strings"
)

// stateCodeRe matches a trailing state-code suffix in the form "-XX" or " - XX"
// where XX is exactly 2 uppercase ASCII letters (Brazilian state codes).
// It does NOT match suffixes like "(URU)" which are country codes in parentheses.
var stateCodeRe = regexp.MustCompile(`\s*-\s*[A-Z]{2}$`)

// NormalizeTeam strips Brazilian state-code suffixes from team names.
// Examples:
//
//	"Palmeiras-SP"  → "Palmeiras"
//	"América - MG"  → "América"
//	"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ" → "Boavista Sport Club (antigo Esporte Clube Barreira)"
//	"Nacional (URU)" → "Nacional (URU)"   (country code in parens, not stripped)
func NormalizeTeam(name string) string {
	return strings.TrimSpace(stateCodeRe.ReplaceAllString(name, ""))
}

// TeamMatches returns true if the query string matches the team name after
// normalization. Matching is case-insensitive substring: the normalized query
// must be contained within the normalized team name.
func TeamMatches(query, teamName string) bool {
	normalizedQuery := strings.ToLower(NormalizeTeam(query))
	normalizedTeam := strings.ToLower(NormalizeTeam(teamName))
	return strings.Contains(normalizedTeam, normalizedQuery)
}
