// Context
// -------
// Human-readable formatters that turn query-layer structs into the text answer
// formats shown in the specification. These are used by the MCP tools/call
// handler to produce the textual content returned to the LLM client.
package soccer

import (
	"fmt"
	"strings"
)

// dateStr renders a match date in ISO form for display.
func dateStr(m Match) string { return m.Date.Format("2006-01-02") }

// FormatMatch renders one match as a single line, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)".
func FormatMatch(m Match) string {
	var ctx []string
	if m.Competition != "" {
		ctx = append(ctx, m.Competition)
	}
	if m.Round != "" {
		ctx = append(ctx, "Round "+m.Round)
	}
	if m.Stage != "" {
		ctx = append(ctx, m.Stage)
	}
	suffix := ""
	if len(ctx) > 0 {
		suffix = " (" + strings.Join(ctx, " ") + ")"
	}
	return fmt.Sprintf("%s: %s %d-%d %s%s", dateStr(m), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, suffix)
}

// FormatMatches renders a list of matches with an optional cap, appending a
// "... (N more)" line when truncated.
func FormatMatches(matches []Match, max int) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	var b strings.Builder
	shown := matches
	if max > 0 && len(matches) > max {
		shown = matches[:max]
	}
	for _, m := range shown {
		fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
	}
	if len(matches) > len(shown) {
		fmt.Fprintf(&b, "- ... (%d more matches in dataset)\n", len(matches)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatH2H renders a head-to-head summary with a sample of recent matches.
func FormatH2H(h H2H, maxMatches int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s:\n", h.TeamA, h.TeamB)
	if len(h.Matches) == 0 {
		b.WriteString("No matches found between these teams in the dataset.")
		return b.String()
	}
	fmt.Fprintln(&b, FormatMatches(h.Matches, maxMatches))
	fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws\n",
		h.TeamA, h.WinsA, h.TeamB, h.WinsB, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d", h.TeamA, h.GoalsA, h.TeamB, h.GoalsB)
	return b.String()
}

// FormatTeamRecord renders a team's aggregate record.
func FormatTeamRecord(r TeamRecord) string {
	var title strings.Builder
	title.WriteString(r.Team)
	switch r.Filter {
	case "home":
		title.WriteString(" home record")
	case "away":
		title.WriteString(" away record")
	default:
		title.WriteString(" record")
	}
	var scope []string
	if r.Season != 0 {
		scope = append(scope, fmt.Sprintf("%d", r.Season))
	}
	if r.Competition != "" {
		scope = append(scope, r.Competition)
	}
	if len(scope) > 0 {
		title.WriteString(" (" + strings.Join(scope, " ") + ")")
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", title.String())
	fmt.Fprintf(&b, "- Matches: %d\n", r.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", r.GoalsFor, r.GoalsAgainst)
	fmt.Fprintf(&b, "- Points: %d\n", r.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%", r.WinRate())
	return b.String()
}

// FormatStandings renders a league table. limit<=0 shows all rows.
func FormatStandings(rows []TeamRecord, competition string, season int, limit int) string {
	if len(rows) == 0 {
		return "No standings available for the requested competition/season."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from matches):\n", season, competition)
	for i, r := range rows {
		if limit > 0 && i >= limit {
			break
		}
		tag := ""
		if i == 0 {
			tag = " - Champion"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GD %+d)%s\n",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalDiff(), tag)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayers renders a numbered list of players.
func FormatPlayers(players []Player, max int) string {
	if len(players) == 0 {
		return "No players found."
	}
	shown := players
	if max > 0 && len(players) > max {
		shown = players[:max]
	}
	var b strings.Builder
	for i, p := range shown {
		club := p.Club
		if club == "" {
			club = "Free agent"
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, emptyDash(p.Position), club, p.Nationality)
	}
	if len(players) > len(shown) {
		fmt.Fprintf(&b, "... (%d more players in dataset)\n", len(players)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

func emptyDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

// FormatStatistics renders competition-wide aggregate statistics.
func FormatStatistics(cs CompetitionStats) string {
	var b strings.Builder
	scope := "all competitions"
	if cs.Competition != "" {
		scope = cs.Competition
	}
	if cs.Season != 0 {
		scope = fmt.Sprintf("%s %d", scope, cs.Season)
	}
	fmt.Fprintf(&b, "Statistics for %s:\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", cs.Matches)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", cs.AvgGoals())
	fmt.Fprintf(&b, "- Home win rate: %.1f%% (Home %d, Away %d, Draws %d)\n",
		cs.HomeWinRate(), cs.HomeWins, cs.AwayWins, cs.Draws)
	if len(cs.BiggestWins) > 0 {
		fmt.Fprintf(&b, "\nBiggest victories:\n")
		for i, m := range cs.BiggestWins {
			fmt.Fprintf(&b, "%d. %s\n", i+1, FormatMatch(m))
		}
	}
	return strings.TrimRight(b.String(), "\n")
}
