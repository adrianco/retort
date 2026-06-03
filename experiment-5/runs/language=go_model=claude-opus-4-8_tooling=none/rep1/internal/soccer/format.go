// Context:
//   - This file renders query results as the human-readable text the MCP tools
//     return to the LLM/user. The formats mirror the example answer layouts in
//     the specification (match lists with date + score + competition, team
//     records with win rate, standings tables, player rankings, etc.).
//   - Keeping formatting here (rather than in the MCP layer) lets the same
//     rendering be unit-tested directly and keeps the tool handlers thin.
package soccer

import (
	"fmt"
	"strings"
)

// FormatDate renders a match date, or "date unknown" when absent.
func (m Match) FormatDate() string {
	if !m.HasDate {
		return "date unknown"
	}
	return m.Date.Format("2006-01-02")
}

// Line renders a single match as one summary line.
func (m Match) Line() string {
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	ctx := m.Competition
	switch {
	case m.Round != "":
		ctx += " Round " + m.Round
	case m.Stage != "":
		ctx += " - " + m.Stage
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", m.FormatDate(), m.HomeTeam, score, m.AwayTeam, ctx)
}

// FormatMatches renders a list of matches with an optional title and a cap on
// how many lines to print (the rest are summarised as "... (N more)").
func FormatMatches(title string, matches []Match, max int) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title)
		b.WriteString("\n")
	}
	if len(matches) == 0 {
		b.WriteString("No matches found.")
		return b.String()
	}
	shown := matches
	if max > 0 && len(matches) > max {
		shown = matches[:max]
	}
	for _, m := range shown {
		b.WriteString("- ")
		b.WriteString(m.Line())
		b.WriteString("\n")
	}
	if len(matches) > len(shown) {
		fmt.Fprintf(&b, "... (%d more match(es))\n", len(matches)-len(shown))
	}
	fmt.Fprintf(&b, "\nTotal: %d match(es).", len(matches))
	return b.String()
}

// FormatHeadToHead renders a head-to-head summary.
func (h HeadToHead) Format(maxMatches int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head: %s vs %s\n", h.Team1, h.Team2)
	if len(h.Matches) == 0 {
		b.WriteString("No matches found between these teams.")
		return b.String()
	}
	fmt.Fprintf(&b, "Record: %s %d wins, %s %d wins, %d draws\n",
		h.Team1, h.Team1Wins, h.Team2, h.Team2Wins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n\n", h.Team1, h.Team1Goals, h.Team2, h.Team2Goals)
	b.WriteString(FormatMatches("Matches:", h.Matches, maxMatches))
	return b.String()
}

// Format renders a team record.
func (r TeamRecord) Format() string {
	var b strings.Builder
	header := r.Team + " record"
	var quals []string
	if r.Season != 0 {
		quals = append(quals, fmt.Sprintf("%d", r.Season))
	}
	if r.Competition != "" {
		quals = append(quals, canonicalCompetition(r.Competition))
	}
	if r.Venue != "" {
		quals = append(quals, strings.ToLower(r.Venue))
	}
	if len(quals) > 0 {
		header += " (" + strings.Join(quals, " ") + ")"
	}
	b.WriteString(header + ":\n")
	fmt.Fprintf(&b, "- Matches: %d\n", r.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n", r.GoalsFor, r.GoalsAgainst, r.GoalDiff())
	fmt.Fprintf(&b, "- Points: %d\n", r.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%", r.WinRate()*100)
	return b.String()
}

// FormatStandings renders a computed league table.
func FormatStandings(competition string, season int, table []Standing, max int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d Standings (calculated from matches):\n", canonicalCompetition(competition), season)
	if len(table) == 0 {
		b.WriteString("No results available for this competition/season.")
		return b.String()
	}
	shown := table
	if max > 0 && len(table) > max {
		shown = table[:max]
	}
	for _, row := range shown {
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW %dD %dL, GD %+d)\n",
			row.Position, row.Team, row.Points(), row.Wins, row.Draws, row.Losses, row.GoalDiff())
	}
	if len(table) > len(shown) {
		fmt.Fprintf(&b, "... (%d more)\n", len(table)-len(shown))
	}
	if len(table) > 0 {
		fmt.Fprintf(&b, "\nChampion: %s", table[0].Team)
	}
	return b.String()
}

// Format renders league aggregate statistics.
func (l LeagueStats) Format() string {
	var b strings.Builder
	scope := canonicalCompetition(l.Competition)
	if l.Season != 0 {
		scope = fmt.Sprintf("%s %d", scope, l.Season)
	}
	fmt.Fprintf(&b, "%s statistics:\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", l.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", l.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", l.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Away wins: %d, Draws: %d\n",
		l.HomeWins, l.HomeWinRate()*100, l.AwayWins, l.Draws)
	if len(l.BiggestWins) > 0 {
		b.WriteString("\nBiggest wins:\n")
		for i, m := range l.BiggestWins {
			fmt.Fprintf(&b, "%d. %s\n", i+1, m.Line())
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

// Line renders a single player as one summary line.
func (p Player) Line() string {
	parts := []string{p.Name}
	if p.Overall > 0 {
		parts = append(parts, fmt.Sprintf("Overall: %d", p.Overall))
	}
	if p.Position != "" {
		parts = append(parts, "Position: "+p.Position)
	}
	if p.Club != "" {
		parts = append(parts, "Club: "+p.Club)
	}
	if p.Nationality != "" {
		parts = append(parts, p.Nationality)
	}
	return strings.Join(parts, " - ")
}

// FormatPlayers renders a ranked player list.
func FormatPlayers(title string, players []Player, max int) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title + "\n")
	}
	if len(players) == 0 {
		b.WriteString("No players found.")
		return b.String()
	}
	shown := players
	if max > 0 && len(players) > max {
		shown = players[:max]
	}
	for i, p := range shown {
		fmt.Fprintf(&b, "%d. %s\n", i+1, p.Line())
	}
	if len(players) > len(shown) {
		fmt.Fprintf(&b, "... (%d more player(s))\n", len(players)-len(shown))
	}
	fmt.Fprintf(&b, "\nTotal: %d player(s).", len(players))
	return b.String()
}
