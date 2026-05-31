// Context:
//   - Project: Brazilian Soccer MCP Server (see TASK.md).
//   - Role of this file: render query results as the human-readable text blocks
//     shown in the specification's "Example answer format" sections. These
//     strings are what the MCP tools return to the calling LLM.
package query

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/data"
)

func matchDate(m data.Match) string {
	if m.HasDate {
		return m.Date.Format("2006-01-02")
	}
	if m.Season != 0 {
		return fmt.Sprintf("%d", m.Season)
	}
	return "????"
}

// titleCase upper-cases the first letter of each space-separated word.
func titleCase(s string) string {
	words := strings.Fields(s)
	for i, w := range words {
		words[i] = strings.ToUpper(w[:1]) + w[1:]
	}
	return strings.Join(words, " ")
}

// roundLabel renders the round/stage annotation for a match line.
func roundLabel(m data.Match) string {
	parts := []string{m.Competition}
	if m.Stage != "" {
		parts = append(parts, titleCase(m.Stage))
	} else if m.Round != "" {
		parts = append(parts, "Round "+m.Round)
	}
	return strings.Join(parts, " ")
}

// FormatMatchLine renders a single match as a one-line summary.
func FormatMatchLine(m data.Match) string {
	return fmt.Sprintf("- %s: %s %d-%d %s (%s)",
		matchDate(m), m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam, roundLabel(m))
}

// FormatMatches renders a list of matches, capping the displayed lines at max
// (0 = all) and noting how many more exist.
func FormatMatches(title string, matches []data.Match, max int) string {
	var b strings.Builder
	if title != "" {
		fmt.Fprintf(&b, "%s\n", title)
	}
	if len(matches) == 0 {
		b.WriteString("No matches found.\n")
		return b.String()
	}
	shown := matches
	if max > 0 && len(matches) > max {
		shown = matches[:max]
	}
	for _, m := range shown {
		b.WriteString(FormatMatchLine(m))
		b.WriteString("\n")
	}
	if len(matches) > len(shown) {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(matches)-len(shown))
	}
	fmt.Fprintf(&b, "\nTotal: %d matches\n", len(matches))
	return b.String()
}

// FormatHeadToHead renders an all-time head-to-head summary.
func (h HeadToHead) Format(maxLines int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head:\n", h.TeamA, h.TeamB)
	if len(h.Matches) == 0 {
		b.WriteString("No matches found between these teams.\n")
		return b.String()
	}
	shown := h.Matches
	if maxLines > 0 && len(shown) > maxLines {
		shown = shown[:maxLines]
	}
	for _, m := range shown {
		b.WriteString(FormatMatchLine(m))
		b.WriteString("\n")
	}
	if len(h.Matches) > len(shown) {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(h.Matches)-len(shown))
	}
	fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws\n",
		h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", h.TeamA, h.AGoals, h.TeamB, h.BGoals)
	return b.String()
}

// Format renders a team statistics block.
func (s TeamStats) Format() string {
	var b strings.Builder
	scope := s.Team
	var quals []string
	if s.Season != 0 {
		quals = append(quals, fmt.Sprintf("%d", s.Season))
	}
	if s.Competition != "" {
		quals = append(quals, s.Competition)
	}
	venue := strings.ToLower(s.Venue)
	if venue == "home" {
		quals = append([]string{"home"}, quals...)
	} else if venue == "away" {
		quals = append([]string{"away"}, quals...)
	}
	if len(quals) > 0 {
		scope = fmt.Sprintf("%s record (%s)", s.Team, strings.Join(quals, " "))
	} else {
		scope = fmt.Sprintf("%s record (all data)", s.Team)
	}
	fmt.Fprintf(&b, "%s:\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", s.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", s.Wins, s.Draws, s.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", s.GoalsFor, s.GoalsAgainst)
	fmt.Fprintf(&b, "- Points: %d\n", s.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", s.WinRate()*100)
	return b.String()
}

// FormatStandings renders a computed league table.
func FormatStandings(competition string, season int, table []TeamStats, max int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from matches):\n", season, competition)
	if len(table) == 0 {
		b.WriteString("No matches found for this competition/season.\n")
		return b.String()
	}
	shown := table
	if max > 0 && len(shown) > max {
		shown = shown[:max]
	}
	for i, s := range shown {
		marker := ""
		if i == 0 {
			marker = " - Champion"
		}
		name := s.Team
		if s.State != "" {
			name = fmt.Sprintf("%s-%s", s.Team, s.State)
		}
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW, %dD, %dL, GD %+d)%s\n",
			i+1, name, s.Points(), s.Wins, s.Draws, s.Losses, s.GoalDiff(), marker)
	}
	if len(table) > len(shown) {
		fmt.Fprintf(&b, "... (%d more teams)\n", len(table)-len(shown))
	}
	return b.String()
}

// Format renders a competition statistics block including biggest wins.
func (cs CompetitionStats) Format() string {
	var b strings.Builder
	scope := cs.Competition
	if scope == "" {
		scope = "All competitions"
	}
	if cs.Season != 0 {
		scope = fmt.Sprintf("%s %d", scope, cs.Season)
	}
	fmt.Fprintf(&b, "%s — statistics (provided data):\n", scope)
	fmt.Fprintf(&b, "Matches: %d\n", cs.Matches)
	fmt.Fprintf(&b, "Average goals per match: %.2f\n", cs.AvgGoalsPerGame)
	fmt.Fprintf(&b, "Home win rate: %.1f%%, Away win rate: %.1f%%, Draw rate: %.1f%%\n",
		cs.HomeWinRate*100, cs.AwayWinRate*100, cs.DrawRate*100)
	if len(cs.BiggestWins) > 0 {
		b.WriteString("\nBiggest victories:\n")
		for i, m := range cs.BiggestWins {
			fmt.Fprintf(&b, "%d. %s\n", i+1, strings.TrimPrefix(FormatMatchLine(m), "- "))
		}
	}
	return b.String()
}

// FormatPlayer renders a single player one-liner.
func FormatPlayer(p data.Player) string {
	pos := p.Position
	if pos == "" {
		pos = "?"
	}
	club := p.Club
	if club == "" {
		club = "Free agent"
	}
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s",
		p.Name, p.Overall, p.Potential, pos, p.Age, p.Nationality, club)
}

// FormatPlayers renders a numbered, ranked list of players.
func FormatPlayers(title string, players []data.Player, max int) string {
	var b strings.Builder
	if title != "" {
		fmt.Fprintf(&b, "%s\n", title)
	}
	if len(players) == 0 {
		b.WriteString("No players found.\n")
		return b.String()
	}
	shown := players
	if max > 0 && len(shown) > max {
		shown = shown[:max]
	}
	for i, p := range shown {
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(p))
	}
	if len(players) > len(shown) {
		fmt.Fprintf(&b, "... (%d more players)\n", len(players)-len(shown))
	}
	fmt.Fprintf(&b, "\nTotal: %d players\n", len(players))
	return b.String()
}
