package mcp

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/data"
)

// formatMatch renders a match as "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Serie A, Round 22)".
func formatMatch(m data.Match) string {
	label := m.Competition
	if m.Stage != "" {
		label += ", " + m.Stage
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)",
		m.Date.Format("2006-01-02"), m.Home.Display, m.HomeGoals, m.AwayGoals, m.Away.Display, label)
}

// formatPlayer renders a player as "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain".
func formatPlayer(p data.Player) string {
	return fmt.Sprintf("%s - Overall: %d, Position: %s, Club: %s, Nationality: %s",
		p.Name, p.Overall, p.Position, p.Club, p.Nationality)
}

// scopeLabel describes the filters applied to a record, e.g. "2022, Brasileirão, home".
func scopeLabel(season int, competition, venue string) string {
	var parts []string
	if season != 0 {
		parts = append(parts, fmt.Sprint(season))
	}
	if competition != "" {
		parts = append(parts, competition)
	}
	if venue != "" {
		parts = append(parts, venue)
	}
	if len(parts) == 0 {
		return "all seasons and competitions"
	}
	return strings.Join(parts, ", ")
}

func seasonText(season int) string {
	if season == 0 {
		return "all seasons"
	}
	return fmt.Sprint(season)
}
