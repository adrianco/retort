// format.go: human-readable rendering of matches, records, standings and player
// lists. The MCP tools return plain text (LLM-friendly), so these helpers turn
// the analysis structs from stats.go into the answer formats shown in the spec.
package soccer

import (
	"fmt"
	"strings"
)

// formatDate renders a match date as YYYY-MM-DD, or "(date unknown)".
func formatDate(m Match) string {
	if m.Date.IsZero() {
		return "(date unknown)"
	}
	return m.Date.Format("2006-01-02")
}

// matchContext renders the trailing "(Competition Round/Stage)" annotation.
func matchContext(m Match) string {
	parts := []string{m.Competition}
	if m.Round != "" {
		parts = append(parts, "Round "+m.Round)
	}
	if m.Stage != "" {
		parts = append(parts, m.Stage)
	}
	if m.Season != 0 && m.Round == "" && m.Stage == "" {
		parts = append(parts, fmt.Sprintf("%d", m.Season))
	}
	return "(" + strings.Join(parts, " ") + ")"
}

// FormatMatch renders a single match line, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)".
func FormatMatch(m Match) string {
	return fmt.Sprintf("%s: %s %d-%d %s %s",
		formatDate(m), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, matchContext(m))
}

// FormatMatchList renders up to limit matches, with a trailing "(N more)" note.
func FormatMatchList(matches []Match, limit int) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	var b strings.Builder
	shown := matches
	if limit > 0 && len(matches) > limit {
		shown = matches[:limit]
	}
	for _, m := range shown {
		fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
	}
	if len(matches) > len(shown) {
		fmt.Fprintf(&b, "- ... (%d more matches in dataset)\n", len(matches)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatRecord renders a Record as a multi-line block.
func FormatRecord(r Record, title string) string {
	return fmt.Sprintf("%s:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n"+
		"- Goals For: %d, Goals Against: %d (diff %+d)\n- Points: %d\n- Win rate: %.1f%%",
		title, r.Matches, r.Wins, r.Draws, r.Losses,
		r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), r.Points(), r.WinRate()*100)
}

// FormatStandings renders a league table (top limit rows; 0 = all).
func FormatStandings(table []Record, title string, limit int) string {
	if len(table) == 0 {
		return "No standings available."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", title)
	rows := table
	if limit > 0 && len(rows) > limit {
		rows = rows[:limit]
	}
	for i, r := range rows {
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW, %dD, %dL), GF %d GA %d (%+d)\n",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff())
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayer renders a one-line player summary.
func FormatPlayer(p Player) string {
	club := p.Club
	if club == "" {
		club = "(no club)"
	}
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s",
		p.Name, p.Overall, p.Potential, dash(p.Position), p.Age, p.Nationality, club)
}

// FormatPlayerList renders up to limit players as a numbered list.
func FormatPlayerList(players []Player, limit int) string {
	if len(players) == 0 {
		return "No players found."
	}
	var b strings.Builder
	shown := players
	if limit > 0 && len(players) > limit {
		shown = players[:limit]
	}
	for i, p := range shown {
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(p))
	}
	if len(players) > len(shown) {
		fmt.Fprintf(&b, "... (%d more players match)\n", len(players)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

func dash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}
