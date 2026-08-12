package main

import (
	"fmt"
	"strings"
)

func formatMatches(title string, matches []Match, limit int) string {
	if len(matches) == 0 {
		return "No matching matches were found in the provided datasets."
	}
	total := len(matches)
	if limit <= 0 {
		limit = 20
	}
	if len(matches) > limit {
		matches = matches[:limit]
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s (%d found):\n", title, total)
	for _, m := range matches {
		detail := m.Competition
		if m.Stage != "" {
			detail += " " + m.Stage
		} else if m.Round != "" {
			detail += " Round " + m.Round
		}
		fmt.Fprintf(&b, "- %s: %s %d-%d %s (%s)\n", m.Date.Format("2006-01-02"), displayTeam(m.HomeTeam), m.HomeGoals, m.AwayGoals, displayTeam(m.AwayTeam), strings.TrimSpace(detail))
	}
	if total > len(matches) {
		fmt.Fprintf(&b, "... (%d more matches)\n", total-len(matches))
	}
	return strings.TrimSpace(b.String())
}

func formatPlayers(title string, players []Player, limit int) string {
	if len(players) == 0 {
		return "No matching players were found in the provided FIFA dataset."
	}
	total := len(players)
	if limit <= 0 {
		limit = 20
	}
	if len(players) > limit {
		players = players[:limit]
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s (%d found):\n", title, total)
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s — Overall: %d, Position: %s, Club: %s, Nationality: %s\n", i+1, p.Name, p.Overall, p.Position, emptyAs(p.Club, "Unattached"), p.Nationality)
	}
	if total > len(players) {
		fmt.Fprintf(&b, "... (%d more players)\n", total-len(players))
	}
	return strings.TrimSpace(b.String())
}

func formatTeamStats(s TeamStats) string {
	if s.Matches == 0 {
		return "No matching team matches were found in the provided datasets."
	}
	context := ""
	if s.Season != 0 {
		context += fmt.Sprintf(" %d", s.Season)
	}
	if s.Competition != "" {
		context += " " + displayCompetition(s.Competition)
	}
	return fmt.Sprintf("%s%s record:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Points: %d\n- Win rate: %.1f%%", s.Team, context, s.Matches, s.Wins, s.Draws, s.Losses, s.GoalsFor, s.GoalsAgainst, s.Points, s.WinRate)
}

func formatHeadToHead(h HeadToHead, limit int) string {
	if h.Matches == 0 {
		return "No head-to-head matches were found in the provided datasets."
	}
	return fmt.Sprintf("%s vs %s head-to-head: %d matches — %s %d wins, %s %d wins, %d draws; goals %d-%d.\n%s", h.Team1, h.Team2, h.Matches, h.Team1, h.Team1Wins, h.Team2, h.Team2Wins, h.Draws, h.Goals1, h.Goals2, formatMatches("Meetings", h.Results, limit))
}

func formatStandings(title string, table []Standing, limit int) string {
	if len(table) == 0 {
		return "No standings can be calculated from the matching dataset records."
	}
	if limit <= 0 {
		limit = 20
	}
	if len(table) > limit {
		table = table[:limit]
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s (calculated from match results):\n", title)
	for _, s := range table {
		fmt.Fprintf(&b, "%d. %s — %d pts (%dW, %dD, %dL), GD %+d\n", s.Position, s.Team, s.Points, s.Wins, s.Draws, s.Losses, s.GoalDiff)
	}
	return strings.TrimSpace(b.String())
}

func formatCompetitionStats(s CompetitionStats) string {
	if s.Matches == 0 {
		return "No matching matches were found for this statistical analysis."
	}
	context := strings.TrimSpace(fmt.Sprintf("%d %s", s.Season, displayCompetition(s.Competition)))
	return fmt.Sprintf("%s statistics:\n- Matches: %d\n- Goals: %d (%.2f per match)\n- Home wins: %d (%.1f%%)\n- Away wins: %d (%.1f%%)\n- Draws: %d (%.1f%%)", context, s.Matches, s.Goals, s.GoalsPerMatch, s.HomeWins, s.HomeWinRate, s.AwayWins, s.AwayWinRate, s.Draws, s.DrawRate)
}

func formatSeasonComparison(a, b CompetitionStats) string {
	return formatCompetitionStats(a) + "\n\n" + formatCompetitionStats(b)
}
func emptyAs(s, fallback string) string {
	if strings.TrimSpace(s) == "" {
		return fallback
	}
	return s
}
