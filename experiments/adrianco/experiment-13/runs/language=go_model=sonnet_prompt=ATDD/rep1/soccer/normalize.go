package soccer

import (
	"regexp"
	"strings"
)

// stateSuffixRe matches Brazilian state suffixes like "-SP", " - RJ", "–MG", etc.
var stateSuffixRe = regexp.MustCompile(`(?i)\s*[-–]\s*[A-Z]{2}$`)

// NormalizeTeamName strips state suffixes and lowercases a team name for comparison.
func NormalizeTeamName(name string) string {
	normalized := stateSuffixRe.ReplaceAllString(strings.TrimSpace(name), "")
	normalized = strings.TrimSpace(normalized)
	return strings.ToLower(normalized)
}

// TeamsMatch returns true if two team names refer to the same team after normalization.
func TeamsMatch(team1, team2 string) bool {
	return NormalizeTeamName(team1) == NormalizeTeamName(team2)
}

// TeamMatchesSearch returns true if the team name contains the search term (after normalization).
func TeamMatchesSearch(team, searchTerm string) bool {
	if searchTerm == "" {
		return true
	}
	return strings.Contains(NormalizeTeamName(team), NormalizeTeamName(searchTerm))
}
