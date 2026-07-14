// format.go renders query results as human-readable text, following the answer
// formats illustrated in the specification.
package soccer

import (
	"fmt"
	"strings"
)

// FormatMatch renders a single match line, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)".
func FormatMatch(m Match) string {
	score := "(no score)"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	var ctx []string
	ctx = append(ctx, m.Competition)
	if m.Season != 0 {
		ctx = append(ctx, fmt.Sprintf("%d", m.Season))
	}
	if m.Round != "" {
		ctx = append(ctx, "Round "+m.Round)
	}
	if m.Stage != "" {
		ctx = append(ctx, m.Stage)
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", m.DateString(), m.HomeTeam, score, m.AwayTeam, strings.Join(ctx, ", "))
}

// FormatMatches renders a list of matches with an optional heading and a cap on
// how many lines to print (0 = all).
func FormatMatches(heading string, matches []Match, max int) string {
	var b strings.Builder
	if heading != "" {
		b.WriteString(heading)
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
		b.WriteString(FormatMatch(m))
		b.WriteString("\n")
	}
	if len(matches) > len(shown) {
		fmt.Fprintf(&b, "... (%d more matches)\n", len(matches)-len(shown))
	}
	fmt.Fprintf(&b, "\nTotal: %d match(es).", len(matches))
	return b.String()
}

// FormatHeadToHead renders a head-to-head summary.
func FormatHeadToHead(h HeadToHead, maxMatches int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head (all competitions in dataset):\n", h.TeamA, h.TeamB)
	if len(h.Matches) == 0 {
		b.WriteString("No matches found between these teams.")
		return b.String()
	}
	fmt.Fprintf(&b, "Played: %d | %s wins: %d | %s wins: %d | Draws: %d\n",
		len(h.Matches), h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d - %d %s\n\n", h.TeamA, h.AGoals, h.BGoals, h.TeamB)
	b.WriteString(FormatMatches("Matches (most recent first):", h.Matches, maxMatches))
	return b.String()
}

// FormatTeamRecord renders a single team's record.
func FormatTeamRecord(r TeamRecord, competition string, season int, venue string) string {
	var scope []string
	if season != 0 {
		scope = append(scope, fmt.Sprintf("%d", season))
	}
	if competition != "" {
		scope = append(scope, competition)
	}
	switch strings.ToLower(venue) {
	case "home":
		scope = append(scope, "home only")
	case "away":
		scope = append(scope, "away only")
	}
	scopeStr := "all competitions"
	if len(scope) > 0 {
		scopeStr = strings.Join(scope, ", ")
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s record (%s):\n", r.Team, scopeStr)
	fmt.Fprintf(&b, "- Matches: %d\n", r.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n", r.GoalsFor, r.GoalsAgainst, r.GoalDiff())
	fmt.Fprintf(&b, "- Win rate: %.1f%%", r.WinRate()*100)
	return b.String()
}

// FormatStandings renders a league table.
func FormatStandings(records []TeamRecord, competition string, season int, max int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s — Final Standings (calculated from matches):\n", season, competition)
	if len(records) == 0 {
		b.WriteString("No data for this competition/season.")
		return b.String()
	}
	shown := records
	if max > 0 && len(records) > max {
		shown = records[:max]
	}
	for i, r := range shown {
		marker := ""
		if i == 0 {
			marker = " - Champion"
		}
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW, %dD, %dL, GD %+d)%s\n",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalDiff(), marker)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayers renders a numbered list of players.
func FormatPlayers(heading string, players []Player, max int) string {
	var b strings.Builder
	if heading != "" {
		b.WriteString(heading)
		b.WriteString("\n")
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
		club := p.Club
		if club == "" {
			club = "Free agent"
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s\n",
			i+1, p.Name, p.Overall, p.Potential, dash(p.Position), p.Age, dash(p.Nationality), club)
	}
	if len(players) > len(shown) {
		fmt.Fprintf(&b, "... (%d more players)\n", len(players)-len(shown))
	}
	fmt.Fprintf(&b, "\nTotal: %d player(s).", len(players))
	return b.String()
}

// FormatClubSummaries renders player-count-by-club summaries.
func FormatClubSummaries(heading string, summaries []ClubSummary, max int) string {
	var b strings.Builder
	if heading != "" {
		b.WriteString(heading)
		b.WriteString("\n")
	}
	if len(summaries) == 0 {
		b.WriteString("No clubs found.")
		return b.String()
	}
	shown := summaries
	if max > 0 && len(summaries) > max {
		shown = summaries[:max]
	}
	for _, c := range shown {
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f)\n", c.Club, c.Count, c.AvgOverall)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStats renders aggregate competition statistics.
func FormatStats(c CompetitionStats) string {
	var b strings.Builder
	scope := c.Competition
	if scope == "" {
		scope = "All competitions"
	}
	if c.Season != 0 {
		scope = fmt.Sprintf("%s %d", scope, c.Season)
	}
	fmt.Fprintf(&b, "%s — aggregate statistics (provided data):\n", scope)
	fmt.Fprintf(&b, "- Matches with scores: %d\n", c.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", c.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", c.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Away wins: %d (%.1f%%), Draws: %d (%.1f%%)\n",
		c.HomeWins, pct(c.HomeWins, c.Matches),
		c.AwayWins, pct(c.AwayWins, c.Matches),
		c.Draws, pct(c.Draws, c.Matches))
	if len(c.BiggestWins) > 0 {
		b.WriteString("\nBiggest victories (by margin):\n")
		for i, m := range c.BiggestWins {
			fmt.Fprintf(&b, "%d. %s\n", i+1, FormatMatch(m))
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

func pct(n, total int) float64 {
	if total == 0 {
		return 0
	}
	return float64(n) / float64(total) * 100
}

func dash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}
