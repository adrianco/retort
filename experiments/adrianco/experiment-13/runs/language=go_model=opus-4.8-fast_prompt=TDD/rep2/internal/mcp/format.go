package mcp

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/soccer"
)

// formatMatch renders a single match as a one-line human-readable string, e.g.
// "2019-10-27: Flamengo-RJ 5-0 Gremio-RS (Brasileirão Round 28)".
func formatMatch(m soccer.Match) string {
	var b strings.Builder
	if m.HasDate {
		b.WriteString(m.Date.Format("2006-01-02"))
		b.WriteString(": ")
	}
	if m.HasScore {
		fmt.Fprintf(&b, "%s %d-%d %s", m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam)
	} else {
		fmt.Fprintf(&b, "%s vs %s", m.HomeTeam, m.AwayTeam)
	}

	// Trailing competition context.
	ctx := m.Competition
	switch {
	case m.Round != "":
		ctx += " Round " + m.Round
	case m.Stage != "":
		ctx += " " + m.Stage
	}
	if m.Season != 0 && !m.HasDate {
		ctx += fmt.Sprintf(" %d", m.Season)
	}
	if ctx != "" {
		fmt.Fprintf(&b, " (%s)", ctx)
	}
	return b.String()
}

// writeMatchList writes a bulleted list of matches.
func writeMatchList(b *strings.Builder, matches []soccer.Match) {
	for _, m := range matches {
		b.WriteString("- ")
		b.WriteString(formatMatch(m))
		b.WriteString("\n")
	}
}

// capMatches returns at most n matches.
func capMatches(matches []soccer.Match, n int) []soccer.Match {
	if n > 0 && len(matches) > n {
		return matches[:n]
	}
	return matches
}

// dash returns s, or "-" when s is empty, for tidy table output.
func dash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}

// trunc shortens s to at most n runes.
func trunc(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}
