// Package main — Brazilian Soccer MCP Server.
//
// format.go: Human-readable rendering of query results. The MCP server returns
// text content (an LLM reads it), so each formatter mirrors the example answer
// shapes in the specification: match lists with scores and rounds, team records
// with win rates, season standings tables, ranked player lists and aggregate
// statistics.
package main

import (
	"fmt"
	"strings"
)

// dateStr renders a match date, or "(date unknown)" when absent.
func dateStr(m Match) string {
	if m.HasDate {
		return m.Date.Format("2006-01-02")
	}
	return "(date unknown)"
}

// matchLine renders a single match as "DATE: Home H-A Away (Competition Round)".
func matchLine(m Match) string {
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	ctx := m.Competition
	switch {
	case m.Round != "":
		ctx += " Round " + m.Round
	case m.Stage != "":
		ctx += " " + m.Stage
	}
	return fmt.Sprintf("- %s: %s %s %s (%s)", dateStr(m), m.HomeTeam, score, m.AwayTeam, ctx)
}

// FormatMatches renders a match list, showing at most limit lines and a
// trailing summary of how many more exist.
func FormatMatches(matches []Match, limit int) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es):\n", len(matches))
	shown := matches
	if limit > 0 && len(matches) > limit {
		shown = matches[:limit]
	}
	for _, m := range shown {
		b.WriteString(matchLine(m))
		b.WriteByte('\n')
	}
	if len(matches) > len(shown) {
		fmt.Fprintf(&b, "... (%d more not shown)\n", len(matches)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatRecord renders a team's win/draw/loss record and win rate.
func FormatRecord(r Record, venue Venue, scope string) string {
	venueStr := ""
	switch venue {
	case VenueHome:
		venueStr = " home"
	case VenueAway:
		venueStr = " away"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s%s record%s:\n", r.Team, venueStr, scope)
	fmt.Fprintf(&b, "- Matches: %d\n", r.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", r.GoalsFor, r.GoalsAgainst)
	fmt.Fprintf(&b, "- Win rate: %.1f%%", r.WinRate()*100)
	return b.String()
}

// FormatH2H renders a head-to-head summary plus recent meetings.
func FormatH2H(h H2H, recent int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head: %s vs %s\n", h.TeamA, h.TeamB)
	if h.Total() == 0 {
		b.WriteString("No meetings found in dataset.")
		return b.String()
	}
	fmt.Fprintf(&b, "Total meetings: %d — %s %d wins, %s %d wins, %d draws\n",
		h.Total(), h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
	if recent > 0 && len(h.Matches) > 0 {
		b.WriteString("Recent meetings:\n")
		n := recent
		if n > len(h.Matches) {
			n = len(h.Matches)
		}
		for _, m := range h.Matches[:n] {
			b.WriteString(matchLine(m))
			b.WriteByte('\n')
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStandings renders a season league table.
func FormatStandings(comp string, season int, table []StandingRow) string {
	if len(table) == 0 {
		return fmt.Sprintf("No standings available for %s %d.", comp, season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d Final Standings (calculated from matches):\n", comp, season)
	for i, r := range table {
		marker := ""
		if i == 0 {
			marker = " - Champion"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW %dD %dL, GF %d GA %d, GD %+d)%s\n",
			i+1, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAg, r.GoalDiff(), marker)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayers renders a ranked player list.
func FormatPlayers(players []Player) string {
	if len(players) == 0 {
		return "No players found."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s):\n", len(players))
	for i, p := range players {
		club := p.Club
		if club == "" {
			club = "(no club)"
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, p.Position, club, p.Nationality)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStats renders aggregate competition statistics, including the biggest
// wins in the same filtered set.
func FormatStats(s Stats, biggest []Match, scope string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics%s:\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", s.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", s.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", s.AvgGoals)
	fmt.Fprintf(&b, "- Home wins: %d, Away wins: %d, Draws: %d\n", s.HomeWins, s.AwayWins, s.Draws)
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", s.HomeWinRate*100)
	if len(biggest) > 0 {
		b.WriteString("Biggest victories:\n")
		for _, m := range biggest {
			b.WriteString(matchLine(m))
			b.WriteByte('\n')
		}
	}
	return strings.TrimRight(b.String(), "\n")
}
