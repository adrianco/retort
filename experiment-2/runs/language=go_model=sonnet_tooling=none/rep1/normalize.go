// Package main - Brazilian Soccer MCP Server
// normalize.go: Team name normalization, date parsing, and utility functions.
// Handles the various naming conventions across datasets (with/without state suffixes)
// and multiple date formats used in the CSV files.
package main

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"
)

var statePattern = regexp.MustCompile(`\s*[-–]\s*[A-Z]{2}$`)

// normalizeTeamName strips state suffixes like "-SP", " - RJ", etc.
// "Palmeiras-SP" -> "Palmeiras", "América - MG" -> "América"
func normalizeTeamName(name string) string {
	name = strings.TrimSpace(name)
	name = statePattern.ReplaceAllString(name, "")
	return strings.TrimSpace(name)
}

// teamMatches checks if a team name contains or matches a query string (case-insensitive).
// Also checks the normalized version of the team name.
func teamMatches(team, query string) bool {
	if query == "" {
		return true
	}
	normalizedTeam := strings.ToLower(normalizeTeamName(team))
	normalizedQuery := strings.ToLower(strings.TrimSpace(query))
	return strings.Contains(normalizedTeam, normalizedQuery)
}

// parseGoals parses a goal count from a string, handling both integer and float formats.
func parseGoals(s string) int {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "nan") || strings.EqualFold(s, "null") {
		return 0
	}
	n, err := strconv.Atoi(s)
	if err == nil {
		return n
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	// Guard against NaN/Inf
	if f != f || f > 1e9 || f < -1e9 {
		return 0
	}
	return int(f)
}

var dateFormats = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05Z",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006",
}

// parseDate parses a date string in various formats.
func parseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, fmt.Errorf("empty date string")
	}
	for _, layout := range dateFormats {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("cannot parse date: %q", s)
}

// parseSeason parses a season year from a string.
func parseSeason(s string) int {
	s = strings.TrimSpace(s)
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}

// formatDate formats a time.Time as "YYYY-MM-DD".
func formatDate(t time.Time) string {
	if t.IsZero() {
		return "unknown"
	}
	return t.Format("2006-01-02")
}

// goalDiff calculates the absolute goal difference in a match.
func goalDiff(homeGoals, awayGoals int) int {
	d := homeGoals - awayGoals
	if d < 0 {
		return -d
	}
	return d
}

// clampInt clamps an integer to a max value.
func clampInt(n, max int) int {
	if n > max {
		return max
	}
	return n
}
