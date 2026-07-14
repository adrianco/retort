package mcp

import (
	"fmt"
	"strings"

	"brsoccer/internal/data"
	"brsoccer/internal/query"
)

func FormatMatches(ms []data.Match, team, vs string) string {
	if len(ms) == 0 {
		return "No matches found."
	}
	var sb strings.Builder
	if team != "" && vs != "" {
		sb.WriteString(fmt.Sprintf("%s vs %s — %d matches:\n", team, vs, len(ms)))
	} else {
		sb.WriteString(fmt.Sprintf("%d matches:\n", len(ms)))
	}
	for _, m := range ms {
		date := "????-??-??"
		if !m.Date.IsZero() {
			date = m.Date.Format("2006-01-02")
		}
		extra := m.Competition
		if m.Round != "" {
			extra += " Round " + m.Round
		}
		if m.Stage != "" {
			extra += " (" + m.Stage + ")"
		}
		sb.WriteString(fmt.Sprintf("  %s: %s %d-%d %s [%s]\n",
			date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, extra))
	}
	return sb.String()
}

func FormatTeamStats(s query.TeamStats) string {
	var sb strings.Builder
	header := s.Team
	if s.Season != 0 {
		header += fmt.Sprintf(" (%d)", s.Season)
	}
	if s.Competition != "" {
		header += " — " + s.Competition
	}
	sb.WriteString(header + "\n")
	sb.WriteString(fmt.Sprintf("  Matches: %d\n", s.Matches))
	sb.WriteString(fmt.Sprintf("  W-D-L: %d-%d-%d (%.1f%% win rate)\n", s.Wins, s.Draws, s.Losses, s.WinRate()))
	sb.WriteString(fmt.Sprintf("  Goals For / Against: %d / %d (diff %+d)\n", s.GoalsFor, s.GoalsAgainst, s.GoalsFor-s.GoalsAgainst))
	sb.WriteString(fmt.Sprintf("  Home W-D-L: %d-%d-%d\n", s.HomeWins, s.HomeDraws, s.HomeLosses))
	sb.WriteString(fmt.Sprintf("  Away W-D-L: %d-%d-%d\n", s.AwayWins, s.AwayDraws, s.AwayLosses))
	sb.WriteString(fmt.Sprintf("  Points (3W+D): %d\n", s.Points))
	return sb.String()
}

func FormatH2H(h query.HeadToHead) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s vs %s head-to-head:\n", h.TeamA, h.TeamB))
	sb.WriteString(fmt.Sprintf("  Matches: %d\n", h.Matches))
	sb.WriteString(fmt.Sprintf("  %s wins: %d, %s wins: %d, Draws: %d\n", h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws))
	sb.WriteString(fmt.Sprintf("  Goals: %s %d - %d %s\n", h.TeamA, h.AGoals, h.BGoals, h.TeamB))
	if len(h.Examples) > 0 {
		sb.WriteString("Recent meetings:\n")
		sb.WriteString(FormatMatches(h.Examples, "", ""))
	}
	return sb.String()
}

func FormatStandings(st []query.TeamStats, season int, competition string) string {
	if len(st) == 0 {
		return "No data for this season/competition."
	}
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s %d standings (computed):\n", competition, season))
	sb.WriteString(fmt.Sprintf("  %-3s %-30s %3s %3s %3s %3s %4s %4s %4s\n", "#", "Team", "P", "W", "D", "L", "GF", "GA", "Pts"))
	for i, s := range st {
		sb.WriteString(fmt.Sprintf("  %-3d %-30s %3d %3d %3d %3d %4d %4d %4d\n",
			i+1, trunc(s.Team, 30), s.Matches, s.Wins, s.Draws, s.Losses, s.GoalsFor, s.GoalsAgainst, s.Points))
	}
	return sb.String()
}

func FormatPlayers(ps []data.Player) string {
	if len(ps) == 0 {
		return "No players found."
	}
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%d players:\n", len(ps)))
	for _, p := range ps {
		sb.WriteString(fmt.Sprintf("  %s — Overall %d, %s, %s @ %s\n",
			p.Name, p.Overall, p.Position, p.Nationality, p.Club))
	}
	return sb.String()
}

func FormatOverall(g query.GlobalStats, comp string, season int) string {
	var sb strings.Builder
	header := "Dataset statistics"
	if comp != "" {
		header += " — " + comp
	}
	if season != 0 {
		header += fmt.Sprintf(" %d", season)
	}
	sb.WriteString(header + "\n")
	sb.WriteString(fmt.Sprintf("  Matches: %d\n", g.TotalMatches))
	sb.WriteString(fmt.Sprintf("  Total goals: %d\n", g.TotalGoals))
	sb.WriteString(fmt.Sprintf("  Average goals/match: %.2f\n", g.AvgGoalsPerMatch))
	sb.WriteString(fmt.Sprintf("  Home wins: %d (%.1f%%)\n", g.HomeWins, g.HomeWinRate))
	sb.WriteString(fmt.Sprintf("  Away wins: %d\n", g.AwayWins))
	sb.WriteString(fmt.Sprintf("  Draws: %d\n", g.Draws))
	return sb.String()
}

func trunc(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n-1]) + "…"
}
