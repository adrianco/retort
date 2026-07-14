// Context: Presentation layer for the Brazilian Soccer MCP server. These
// functions turn query results from the store into the human-readable, domain
// language text that each MCP tool returns to the calling LLM (match lists with
// scores, team records, head-to-head tallies, league standings, aggregate
// statistics and player listings). Keeping formatting here keeps the store
// purely about data and the tools purely about argument handling.
package main

import (
	"fmt"
	"strings"
)

const maxListed = 50

// plural renders "1 win" / "2 wins" (and "1 match" / "2 matches").
func plural(n int, noun string) string {
	if n == 1 {
		return fmt.Sprintf("%d %s", n, noun)
	}
	if noun == "match" {
		return fmt.Sprintf("%d matches", n)
	}
	return fmt.Sprintf("%d %ss", n, noun)
}

// matchLine renders a single match result line.
func matchLine(m Match) string {
	score := "?-?"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	extra := m.Competition
	switch {
	case m.Stage != "":
		extra += " - " + m.Stage
	case m.Round != "":
		extra += " Round " + m.Round
	}
	return fmt.Sprintf("- %s: %s %s %s (%s)", m.dateString(), m.HomeTeam, score, m.AwayTeam, extra)
}

func listMatches(matches []Match) string {
	var b strings.Builder
	limit := len(matches)
	if limit > maxListed {
		limit = maxListed
	}
	for i := 0; i < limit; i++ {
		b.WriteString(matchLine(matches[i]))
		b.WriteByte('\n')
	}
	if len(matches) > limit {
		fmt.Fprintf(&b, "... and %d more\n", len(matches)-limit)
	}
	return b.String()
}

// formatFindMatches renders the result of a match search. When both a team and
// an opponent were specified it appends a head-to-head summary.
func formatFindMatches(label string, matches []Match, h2h *HeadToHead, aName, bName string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Found %s for %s:\n", plural(len(matches), "match"), label)
	if len(matches) == 0 {
		b.WriteString("(no matches found in the dataset)\n")
		return b.String()
	}
	b.WriteString(listMatches(matches))
	if h2h != nil {
		fmt.Fprintf(&b, "\nHead-to-head (these teams): %s %s, %s %s, %s\n",
			aName, plural(h2h.AWins, "win"),
			bName, plural(h2h.BWins, "win"),
			plural(h2h.Draws, "draw"))
	}
	return b.String()
}

func formatTeamRecord(team string, season int, hasSeason bool, competition, venue string, r TeamRecord) string {
	scope := venueLabel(venue) + " record"
	var quals []string
	if hasSeason {
		quals = append(quals, itoa(season))
	}
	if competition != "" {
		quals = append(quals, competition)
	}
	header := fmt.Sprintf("%s %s", team, scope)
	if len(quals) > 0 {
		header += " (" + strings.Join(quals, ", ") + ")"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", header)
	fmt.Fprintf(&b, "- Matches: %d\n", r.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", r.GoalsFor, r.GoalsAgainst)
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", r.WinRate())
	return b.String()
}

func venueLabel(venue string) string {
	switch venue {
	case "home":
		return "home"
	case "away":
		return "away"
	default:
		return "overall"
	}
}

func formatHeadToHead(aName, bName string, h HeadToHead) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head: %s vs %s\n", aName, bName)
	fmt.Fprintf(&b, "Total matches: %d\n", len(h.Matches))
	fmt.Fprintf(&b, "- %s wins: %d\n", aName, h.AWins)
	fmt.Fprintf(&b, "- %s wins: %d\n", bName, h.BWins)
	fmt.Fprintf(&b, "- Draws: %d\n", h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", aName, h.AGoals, bName, h.BGoals)
	if len(h.Matches) > 0 {
		b.WriteString("\nMatches:\n")
		b.WriteString(listMatches(h.Matches))
	}
	return b.String()
}

func formatStandings(competition string, season int, table []Standing) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d Final Standings (calculated from matches):\n", competition, season)
	if len(table) == 0 {
		b.WriteString("(no matches found for this competition and season)\n")
		return b.String()
	}
	for i, st := range table {
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL) GF:%d GA:%d GD:%+d\n",
			i+1, st.Team, st.Points, st.Wins, st.Draws, st.Losses,
			st.GoalsFor, st.GoalsAgainst, st.GoalDiff())
	}
	return b.String()
}

func formatStatistics(scope string, stat Statistics) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics (%s):\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", stat.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", stat.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", stat.AvgGoals())
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", stat.HomeWinRate())
	fmt.Fprintf(&b, "- Draw rate: %.1f%%\n", stat.DrawRate())
	fmt.Fprintf(&b, "- Away win rate: %.1f%%\n", stat.AwayWinRate())
	if len(stat.BiggestWins) > 0 {
		b.WriteString("\nBiggest victories:\n")
		for i, m := range stat.BiggestWins {
			margin := abs(m.HomeGoals - m.AwayGoals)
			fmt.Fprintf(&b, "%d. %s: %s %d-%d %s (margin %d)\n",
				i+1, m.dateString(), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, margin)
		}
	}
	return b.String()
}

func formatPlayers(players []Player, limit int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Found %s:\n", plural(len(players), "player"))
	if len(players) == 0 {
		b.WriteString("(no players found in the dataset)\n")
		return b.String()
	}
	shown := len(players)
	if limit > 0 && limit < shown {
		shown = limit
	}
	for i := 0; i < shown; i++ {
		p := players[i]
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, dashIfEmpty(p.Position), dashIfEmpty(p.Club), dashIfEmpty(p.Nationality))
	}
	if len(players) > shown {
		fmt.Fprintf(&b, "... and %d more\n", len(players)-shown)
	}
	return b.String()
}

func dashIfEmpty(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}
