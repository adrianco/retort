package mcp

import (
	"fmt"
	"strings"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/query"
)

func formatMatches(matches []data.Match) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	var b strings.Builder
	for _, m := range matches {
		date := m.Date.Format("2006-01-02")
		extra := ""
		if m.Round != "" && m.Round != string(m.Competition) {
			extra = fmt.Sprintf(" (%s Round %s)", competitionShort(m.Competition), m.Round)
		} else if m.Stage != "" {
			extra = fmt.Sprintf(" (%s — %s)", competitionShort(m.Competition), m.Stage)
		} else {
			extra = fmt.Sprintf(" (%s)", competitionShort(m.Competition))
		}
		fmt.Fprintf(&b, "- %s: %s %d-%d %s%s\n", date, m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam, extra)
	}
	return strings.TrimRight(b.String(), "\n")
}

func competitionShort(c data.Competition) string {
	switch c {
	case data.CompBrasileirao:
		return "Brasileirão"
	case data.CompCopaBrasil:
		return "Copa do Brasil"
	case data.CompLibertadores:
		return "Libertadores"
	case data.CompExtended:
		return "BR-Football"
	case data.CompHistorical:
		return "Brasileirão Hist."
	default:
		return string(c)
	}
}

func formatHeadToHead(h query.HeadToHead, limit int) string {
	if h.TotalGames == 0 {
		return fmt.Sprintf("No matches found between %s and %s.", h.TeamA, h.TeamB)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head:\n", h.TeamA, h.TeamB)
	fmt.Fprintf(&b, "Matches: %d | %s wins: %d | %s wins: %d | Draws: %d\n", h.TotalGames, h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", h.TeamA, h.AGoals, h.TeamB, h.BGoals)
	if len(h.Matches) > 0 {
		b.WriteString("\nRecent matches:\n")
		shown := h.Matches
		if limit > 0 && len(shown) > limit {
			shown = shown[:limit]
		}
		b.WriteString(formatMatches(shown))
		if remaining := h.TotalGames - len(shown); remaining > 0 {
			fmt.Fprintf(&b, "\n... (%d more in dataset)", remaining)
		}
	}
	return b.String()
}

func formatRecord(r query.TeamRecord) string {
	if r.Matches == 0 {
		return fmt.Sprintf("No matches found for %s.", r.Team)
	}
	venue := r.HomeOrAway
	if venue == "" {
		venue = "all venues"
	}
	header := fmt.Sprintf("%s record", r.Team)
	if r.Competition != "" {
		header += " — " + r.Competition
	}
	if r.Season > 0 {
		header += fmt.Sprintf(" (%d)", r.Season)
	}
	header += " — " + venue
	return fmt.Sprintf(`%s
- Matches: %d
- Wins: %d, Draws: %d, Losses: %d
- Goals For: %d, Goals Against: %d (diff %+d)
- Points (3-1-0): %d
- Win rate: %.1f%%`, header, r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalsFor-r.GoalsAgainst, r.Points, r.WinRate())
}

func formatTopScorers(records []query.TeamRecord) string {
	if len(records) == 0 {
		return "No data."
	}
	var b strings.Builder
	b.WriteString("Top scoring teams:\n")
	for i, r := range records {
		fmt.Fprintf(&b, "%d. %s — %d goals in %d matches (W%d D%d L%d)\n", i+1, r.Team, r.GoalsFor, r.Matches, r.Wins, r.Draws, r.Losses)
	}
	return strings.TrimRight(b.String(), "\n")
}

func formatPlayers(players []data.Player) string {
	if len(players) == 0 {
		return "No players found."
	}
	var b strings.Builder
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s — Overall %d, Position %s, Club %s, Nationality %s, Age %d\n",
			i+1, p.Name, p.Overall, valueOrDash(p.Position), valueOrDash(p.Club), valueOrDash(p.Nationality), p.Age)
	}
	return strings.TrimRight(b.String(), "\n")
}

func valueOrDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

func formatClubSummaries(summaries []query.ClubSummary, nationality string) string {
	if len(summaries) == 0 {
		return fmt.Sprintf("No players found for nationality %q.", nationality)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Clubs with most %s players:\n", nationality)
	for i, s := range summaries {
		fmt.Fprintf(&b, "%d. %s — %d players (avg %.1f, top %d)\n", i+1, s.Club, s.PlayerCount, s.AverageOverall, s.TopOverall)
	}
	return strings.TrimRight(b.String(), "\n")
}

func formatStandings(rows []query.Standing, comp string, season int) string {
	if len(rows) == 0 {
		return fmt.Sprintf("No data for %s %d.", comp, season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d standings:\n", comp, season)
	fmt.Fprintf(&b, "Pos  Team                            P   W   D   L   GF   GA   GD   Pts\n")
	for _, r := range rows {
		fmt.Fprintf(&b, "%2d.  %-30.30s  %3d %3d %3d %3d  %3d  %3d  %+4d  %3d\n",
			r.Position, r.Team, r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff, r.Points)
	}
	return strings.TrimRight(b.String(), "\n")
}

func formatStats(s query.Stats) string {
	if s.Matches == 0 {
		return "No matches matched the filter."
	}
	var b strings.Builder
	if s.Competition != "" {
		fmt.Fprintf(&b, "Competition: %s\n", s.Competition)
	}
	if s.Season > 0 {
		fmt.Fprintf(&b, "Season: %d\n", s.Season)
	}
	fmt.Fprintf(&b, "Matches: %d\n", s.Matches)
	fmt.Fprintf(&b, "Total goals: %d (avg %.2f per match)\n", s.TotalGoals, s.AvgGoals)
	fmt.Fprintf(&b, "Home wins: %d (%.1f%%)\n", s.HomeWins, s.HomeWinRate)
	fmt.Fprintf(&b, "Away wins: %d (%.1f%%)\n", s.AwayWins, s.AwayWinRate)
	fmt.Fprintf(&b, "Draws: %d (%.1f%%)\n", s.Draws, s.DrawRate)
	fmt.Fprintf(&b, "Home goals avg: %.2f, away goals avg: %.2f", s.HomeGoalsAvg, s.AwayGoalsAvg)
	return b.String()
}
