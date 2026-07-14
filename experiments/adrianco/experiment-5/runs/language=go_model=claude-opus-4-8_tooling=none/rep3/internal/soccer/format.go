// Context: text formatters. The MCP tools return human-readable strings shaped
// like the "Example answer format" blocks in TASK.md so an LLM (or a person)
// can use the output directly.
package soccer

import (
	"fmt"
	"strings"
)

// FormatMatch renders one fixture, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)".
func FormatMatch(m Match) string {
	date := m.DateStr
	if date == "" {
		date = "????-??-??"
	}
	var score string
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoal, m.AwayGoal)
	} else {
		score = "vs"
	}
	ctx := m.Competition
	if m.Stage != "" {
		ctx += " " + m.Stage
	} else if m.Round != "" {
		ctx += " Round " + m.Round
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", date, m.HomeTeam, score, m.AwayTeam, strings.TrimSpace(ctx))
}

// FormatMatchList renders up to limit matches plus a "(N more)" footer.
func FormatMatchList(title string, ms []Match, limit int) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title)
		b.WriteString("\n")
	}
	if len(ms) == 0 {
		b.WriteString("No matches found.")
		return b.String()
	}
	shown := ms
	if limit > 0 && len(ms) > limit {
		shown = ms[:limit]
	}
	for _, m := range shown {
		b.WriteString("- ")
		b.WriteString(FormatMatch(m))
		b.WriteString("\n")
	}
	if len(ms) > len(shown) {
		fmt.Fprintf(&b, "- ... (%d more matches in dataset)\n", len(ms)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatTeamRecord renders a TeamRecord block.
func FormatTeamRecord(r TeamRecord) string {
	var b strings.Builder
	title := r.Team + " record"
	var quals []string
	if r.Venue != "" {
		title = r.Team + " " + r.Venue + " record"
	}
	if r.Season != 0 {
		quals = append(quals, fmt.Sprintf("%d", r.Season))
	}
	if r.Competition != "" {
		quals = append(quals, r.Competition)
	}
	if len(quals) > 0 {
		title += " (" + strings.Join(quals, " ") + ")"
	}
	b.WriteString(title)
	b.WriteString(":\n")
	fmt.Fprintf(&b, "- Matches: %d\n", r.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", r.GoalsFor, r.GoalsAgst)
	fmt.Fprintf(&b, "- Points: %d\n", r.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%", r.WinRate())
	return b.String()
}

// FormatHeadToHead renders the H2H summary plus recent matches.
func FormatHeadToHead(h HeadToHead, limit int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s head-to-head (in dataset):\n", h.TeamA, h.TeamB)
	fmt.Fprintf(&b, "- Matches: %d\n", len(h.Matches))
	fmt.Fprintf(&b, "- %s wins: %d, %s wins: %d, Draws: %d\n", h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
	fmt.Fprintf(&b, "- Goals: %s %d, %s %d\n", h.TeamA, h.AGoals, h.TeamB, h.BGoals)
	if len(h.Matches) > 0 {
		b.WriteString("\nMatches:\n")
		b.WriteString(FormatMatchList("", h.Matches, limit))
	}
	return b.String()
}

// FormatPlayer renders a single player line.
func FormatPlayer(p Player) string {
	parts := []string{fmt.Sprintf("Overall: %d", p.Overall)}
	if p.Position != "" {
		parts = append(parts, "Position: "+p.Position)
	}
	if p.Club != "" {
		parts = append(parts, "Club: "+p.Club)
	}
	if p.Nationality != "" {
		parts = append(parts, "Nationality: "+p.Nationality)
	}
	if p.Age != 0 {
		parts = append(parts, fmt.Sprintf("Age: %d", p.Age))
	}
	return fmt.Sprintf("%s - %s", p.Name, strings.Join(parts, ", "))
}

// FormatPlayerList renders a numbered, ranked player list.
func FormatPlayerList(title string, ps []Player, limit int) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title)
		b.WriteString("\n")
	}
	if len(ps) == 0 {
		b.WriteString("No players found.")
		return b.String()
	}
	shown := ps
	if limit > 0 && len(ps) > limit {
		shown = ps[:limit]
	}
	for i, p := range shown {
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(p))
	}
	if len(ps) > len(shown) {
		fmt.Fprintf(&b, "... (%d more players in dataset)\n", len(ps)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStandings renders a league table.
func FormatStandings(title string, table []TeamRecord, limit int) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title)
		b.WriteString("\n")
	}
	if len(table) == 0 {
		b.WriteString("No standings could be computed.")
		return b.String()
	}
	shown := table
	if limit > 0 && len(table) > limit {
		shown = table[:limit]
	}
	for i, r := range shown {
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL), GF %d GA %d (GD %+d)\n",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgst, r.GoalDiff())
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatCompetitionStats renders the aggregate statistics block.
func FormatCompetitionStats(c CompetitionSummary) string {
	var b strings.Builder
	title := "Statistics"
	var quals []string
	if c.Season != 0 {
		quals = append(quals, fmt.Sprintf("%d", c.Season))
	}
	if c.Competition != "" {
		quals = append(quals, c.Competition)
	}
	if len(quals) > 0 {
		title += " (" + strings.Join(quals, " ") + ")"
	}
	b.WriteString(title)
	b.WriteString(":\n")
	fmt.Fprintf(&b, "- Matches: %d\n", c.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", c.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", c.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%)\n", c.HomeWins, c.HomeWinRate())
	fmt.Fprintf(&b, "- Away wins: %d (%.1f%%)\n", c.AwayWins, c.AwayWinRate())
	fmt.Fprintf(&b, "- Draws: %d (%.1f%%)", c.Draws, c.DrawRate())
	return b.String()
}
