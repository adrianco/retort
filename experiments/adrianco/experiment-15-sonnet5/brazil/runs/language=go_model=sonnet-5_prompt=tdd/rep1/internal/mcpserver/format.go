// Package mcpserver exposes the Brazilian soccer knowledge graph in
// internal/soccer as an MCP server, formatting query results into
// human-readable text for LLM consumption.
package mcpserver

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/soccer"
)

// FormatMatch renders a single match as "YYYY-MM-DD: Home G-G Away
// (Competition[ Round N])".
func FormatMatch(m soccer.Match) string {
	suffix := m.Competition
	if m.Round != "" {
		suffix = fmt.Sprintf("%s Round %s", m.Competition, m.Round)
	} else if m.Stage != "" {
		suffix = fmt.Sprintf("%s, %s", m.Competition, m.Stage)
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)",
		m.Date.Format("2006-01-02"), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, suffix)
}

// FormatMatches renders a list of matches, one per line.
func FormatMatches(matches []soccer.Match) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	lines := make([]string, len(matches))
	for i, m := range matches {
		lines[i] = FormatMatch(m)
	}
	return strings.Join(lines, "\n")
}

// FormatHeadToHead renders a head-to-head summary along with the matches
// found.
func FormatHeadToHead(r soccer.HeadToHeadResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s:\n", r.TeamA, r.TeamB)
	b.WriteString(FormatMatches(r.Matches))
	fmt.Fprintf(&b, "\n\nHead-to-head: %s %d wins, %s %d wins, %d draws",
		r.TeamA, r.TeamAWins, r.TeamB, r.TeamBWins, r.Draws)
	return b.String()
}

// FormatTeamRecord renders a team's win/loss/draw record.
func FormatTeamRecord(r soccer.TeamRecord) string {
	return fmt.Sprintf("%s record:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %.1f%%",
		r.Team, r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate)
}

// FormatStandings renders a computed competition table.
func FormatStandings(table []soccer.StandingEntry, competition string, season int) string {
	if len(table) == 0 {
		return "No standings available."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Standings (calculated from matches):\n", season, competition)
	for i, e := range table {
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL), GF %d GA %d GD %d\n",
			i+1, e.Team, e.Points, e.Wins, e.Draws, e.Losses, e.GoalsFor, e.GoalsAgainst, e.GoalDiff)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStatsSummary renders aggregate match statistics.
func FormatStatsSummary(sum soccer.Summary) string {
	return fmt.Sprintf("Matches: %d\nAverage goals per match: %.2f\nHome win rate: %.1f%%\nAway win rate: %.1f%%\nDraw rate: %.1f%%",
		sum.TotalMatches, sum.AvgGoalsPerMatch, sum.HomeWinRate, sum.AwayWinRate, sum.DrawRate)
}

// FormatPlayers renders a list of players, one per line.
func FormatPlayers(players []soccer.Player) string {
	if len(players) == 0 {
		return "No players found."
	}
	lines := make([]string, len(players))
	for i, p := range players {
		lines[i] = fmt.Sprintf("%d. %s - Overall: %d, Position: %s, Club: %s", i+1, p.Name, p.Overall, p.Position, p.Club)
	}
	return strings.Join(lines, "\n")
}
