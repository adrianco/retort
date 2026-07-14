// format.go - human-readable rendering of query results.
//
// Context
// -------
// MCP tool results are returned as text content, so each query result needs a
// concise, readable rendering. These helpers live in the soccer package (rather
// than the command layer) so tests can assert on the exact answer strings, and
// so the rendering stays close to the data structures it describes. The output
// style follows the example answer formats in the specification.
package soccer

import (
	"fmt"
	"strings"
)

// ParseCompetition maps a free-form competition string supplied by a user to a
// canonical competition key. It returns ("", false) when the input is empty and
// (CompOther-or-best-guess, true) otherwise. An unrecognised but non-empty value
// yields its folded form so callers can still filter (and get no matches).
func ParseCompetition(s string) (key string, ok bool) {
	t := strings.ToLower(FoldAccents(strings.TrimSpace(s)))
	if t == "" {
		return "", false
	}
	switch {
	case strings.Contains(t, "copa do brasil"), strings.Contains(t, "cup"), t == "copadobrasil":
		return CompCopaDoBrasil, true
	case strings.Contains(t, "libertadores"):
		return CompLibertadores, true
	case strings.Contains(t, "serie b"), strings.Contains(t, "serieb"):
		return CompSerieB, true
	case strings.Contains(t, "serie c"), strings.Contains(t, "seriec"):
		return CompSerieC, true
	case strings.Contains(t, "serie a"), strings.Contains(t, "seriea"),
		strings.Contains(t, "brasileir"), strings.Contains(t, "brazilian league"):
		return CompBrasileirao, true
	default:
		return t, true
	}
}

// FormatMatch renders a single match on one line, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)".
func FormatMatch(m *Match) string {
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	var ctx []string
	ctx = append(ctx, CompetitionName(m.Competition))
	if m.Stage != "" {
		ctx = append(ctx, m.Stage)
	} else if m.Round != "" {
		ctx = append(ctx, "Round "+m.Round)
	}
	return fmt.Sprintf("%s: %s %s %s (%s)",
		m.DateString(), m.HomeTeam, score, m.AwayTeam, strings.Join(ctx, ", "))
}

// FormatMatchList renders a list of matches with an optional cap, appending a
// "... (N more)" note when truncated.
func FormatMatchList(matches []*Match, limit int) string {
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
		fmt.Fprintf(&b, "- ... (%d more match(es) in dataset)\n", len(matches)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatHeadToHead renders an H2HResult in the specification's style.
func FormatHeadToHead(r H2HResult, limit int) string {
	if r.Total == 0 {
		return fmt.Sprintf("No matches found between %s and %s in the dataset.", r.TeamA, r.TeamB)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head (%d matches in dataset):\n", r.TeamA, r.TeamB, r.Total)
	fmt.Fprintf(&b, "%s %d wins, %s %d wins, %d draws\n", r.TeamA, r.AWins, r.TeamB, r.BWins, r.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n\n", r.TeamA, r.AGoals, r.TeamB, r.BGoals)
	b.WriteString("Matches:\n")
	b.WriteString(FormatMatchList(r.Matches, limit))
	return b.String()
}

// FormatTeamStats renders a TeamStats block.
func FormatTeamStats(s TeamStats) string {
	scope := scopeLabel(s.Competition, s.Season)
	venue := ""
	switch s.Venue {
	case "home":
		venue = " home"
	case "away":
		venue = " away"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s%s record%s:\n", s.Team, venue, scope)
	fmt.Fprintf(&b, "- Matches: %d\n", s.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", s.Wins, s.Draws, s.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n", s.GoalsFor, s.GoalsAgainst, s.GoalDiff())
	fmt.Fprintf(&b, "- Points: %d\n", s.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%", s.WinRate()*100)
	return b.String()
}

// scopeLabel builds a " (2023 Brasileirão Série A)"-style suffix.
func scopeLabel(competition string, season int) string {
	var parts []string
	if season != 0 {
		parts = append(parts, fmt.Sprintf("%d", season))
	}
	if competition != "" {
		parts = append(parts, CompetitionName(competition))
	}
	if len(parts) == 0 {
		return " (all competitions, all seasons)"
	}
	return " (" + strings.Join(parts, " ") + ")"
}

// FormatStandings renders a league table.
func FormatStandings(rows []StandingRow, competition string, season int, limit int) string {
	if len(rows) == 0 {
		return fmt.Sprintf("No standings could be computed%s.", scopeLabel(competition, season))
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Standings%s (calculated from matches):\n", scopeLabel(competition, season))
	shown := rows
	if limit > 0 && len(rows) > limit {
		shown = rows[:limit]
	}
	for _, r := range shown {
		marker := ""
		if r.Position == 1 {
			marker = " — Champion"
		}
		fmt.Fprintf(&b, "%2d. %s — %d pts (%dW %dD %dL, GD %+d)%s\n",
			r.Position, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalDiff(), marker)
	}
	if len(rows) > len(shown) {
		fmt.Fprintf(&b, "... (%d more team(s))\n", len(rows)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayer renders a single player on one line.
func FormatPlayer(p *Player) string {
	club := p.Club
	if club == "" {
		club = "Free agent"
	}
	return fmt.Sprintf("%s — Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s",
		p.Name, p.Overall, p.Potential, dash(p.Position), p.Age, dash(p.Nationality), club)
}

// FormatPlayerList renders a numbered, capped list of players.
func FormatPlayerList(players []*Player, limit int) string {
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
		fmt.Fprintf(&b, "... (%d more player(s) match)\n", len(players)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatGoalStats renders aggregate scoring metrics.
func FormatGoalStats(gs GoalStats, competition string, season int) string {
	if gs.Matches == 0 {
		return fmt.Sprintf("No scored matches found%s.", scopeLabel(competition, season))
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Scoring statistics%s:\n", scopeLabel(competition, season))
	fmt.Fprintf(&b, "- Matches: %d\n", gs.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", gs.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", gs.AvgGoals)
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%)\n", gs.HomeWins, gs.HomeWinRate*100)
	fmt.Fprintf(&b, "- Away wins: %d (%.1f%%)\n", gs.AwayWins, gs.AwayWinRate*100)
	fmt.Fprintf(&b, "- Draws: %d (%.1f%%)", gs.Draws, gs.DrawRate*100)
	return b.String()
}

// FormatTeamRecordsTable renders a ranked list of team records (for best
// home/away record and top-scoring team answers).
func FormatTeamRecordsTable(title string, recs []TeamStats, limit int) string {
	if len(recs) == 0 {
		return "No team records found."
	}
	var b strings.Builder
	b.WriteString(title + "\n")
	shown := recs
	if limit > 0 && len(recs) > limit {
		shown = recs[:limit]
	}
	for i, r := range shown {
		fmt.Fprintf(&b, "%d. %s — %d matches, %dW %dD %dL, GF %d, GA %d, win rate %.1f%%\n",
			i+1, r.Team, r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate()*100)
	}
	return strings.TrimRight(b.String(), "\n")
}

func dash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}
