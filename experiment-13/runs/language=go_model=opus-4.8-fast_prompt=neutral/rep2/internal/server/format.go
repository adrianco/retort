// Context: formatting helpers that render soccer query results in the
// human-readable answer style from TASK.md (match lines, head-to-head summary,
// standings tables, player lists). Kept separate from tool wiring so the
// formatting can be unit-tested independently.
package server

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/soccer"
)

// formatMatchLine renders one match like:
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)".
func formatMatchLine(m soccer.Match) string {
	date := "date unknown"
	if m.HasDate {
		date = m.Date.Format("2006-01-02")
	} else if m.Season != 0 {
		date = fmt.Sprintf("%d", m.Season)
	}
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	ctx := m.Competition
	switch {
	case m.Round != "" && m.Round != "0":
		ctx += " Round " + m.Round
	case m.Stage != "":
		ctx += " " + m.Stage
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", date, m.HomeTeam, score, m.AwayTeam, ctx)
}

func formatMatchList(matches []soccer.Match, limit int) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	shown := matches
	truncated := 0
	if limit > 0 && len(matches) > limit {
		shown = matches[:limit]
		truncated = len(matches) - limit
	}
	var b strings.Builder
	for _, m := range shown {
		b.WriteString("- ")
		b.WriteString(formatMatchLine(m))
		b.WriteString("\n")
	}
	if truncated > 0 {
		fmt.Fprintf(&b, "... (%d more match(es))\n", truncated)
	}
	return strings.TrimRight(b.String(), "\n")
}

func formatRecord(name string, r soccer.Record) string {
	return fmt.Sprintf(
		"%s:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Points: %d\n- Win rate: %.1f%%",
		name, r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgst, r.Points, r.WinRate())
}

func formatPlayer(i int, p soccer.Player) string {
	parts := []string{fmt.Sprintf("%d. %s", i, p.Name)}
	if p.Overall != 0 {
		parts = append(parts, fmt.Sprintf("Overall: %d", p.Overall))
	}
	if p.Position != "" {
		parts = append(parts, "Position: "+p.Position)
	}
	if p.Club != "" {
		parts = append(parts, "Club: "+p.Club)
	}
	if p.Nationality != "" {
		parts = append(parts, "Nationality: "+p.Nationality)
	}
	return strings.Join(parts, " - ")
}
