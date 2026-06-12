package main

import (
	"fmt"
	"sort"
	"strings"
)

const defaultLimit = 20

func (s *Server) toolSearchMatches(team, team2, competition string, season, limit int) (string, error) {
	if limit <= 0 {
		limit = defaultLimit
	}

	var matches []Match
	if team2 != "" && team != "" {
		matches = s.db.FilterMatchesH2H(team, team2)
	} else {
		matches = s.db.FilterMatches(team, competition, season)
	}

	// Sort descending by date.
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].DateTime.After(matches[j].DateTime)
	})

	total := len(matches)
	if len(matches) > limit {
		matches = matches[:limit]
	}

	if total == 0 {
		return "No matches found matching the given criteria.", nil
	}

	var sb strings.Builder
	if team2 != "" && team != "" {
		fmt.Fprintf(&sb, "Head-to-head: %s vs %s\n", team, team2)
		// Compute H2H stats over full result set.
		all := s.db.FilterMatchesH2H(team, team2)
		t1wins, t2wins, draws := 0, 0, 0
		t1q := strings.ToLower(strings.TrimSpace(team))
		for _, m := range all {
			ht := normalizeLower(m.HomeTeam)
			t1home := strings.Contains(ht, t1q)
			if t1home {
				if m.HomeGoals > m.AwayGoals {
					t1wins++
				} else if m.HomeGoals == m.AwayGoals {
					draws++
				} else {
					t2wins++
				}
			} else {
				if m.AwayGoals > m.HomeGoals {
					t1wins++
				} else if m.AwayGoals == m.HomeGoals {
					draws++
				} else {
					t2wins++
				}
			}
		}
		fmt.Fprintf(&sb, "Total: %d matches | %s wins: %d, %s wins: %d, draws: %d\n\n",
			len(all), team, t1wins, team2, t2wins, draws)
	} else {
		qualifier := "all competitions"
		if competition != "" {
			qualifier = competition
		}
		if season > 0 {
			qualifier += fmt.Sprintf(" %d", season)
		}
		if team != "" {
			fmt.Fprintf(&sb, "Matches for %s (%s): %d total, showing %d\n\n", team, qualifier, total, len(matches))
		} else {
			fmt.Fprintf(&sb, "Matches (%s): %d total, showing %d\n\n", qualifier, total, len(matches))
		}
	}

	for _, m := range matches {
		dateStr := "unknown"
		if !m.DateTime.IsZero() {
			dateStr = m.DateTime.Format("2006-01-02")
		}
		winner := "Draw"
		if m.HomeGoals > m.AwayGoals {
			winner = m.HomeTeam + " win"
		} else if m.AwayGoals > m.HomeGoals {
			winner = m.AwayTeam + " win"
		}
		roundInfo := ""
		if m.Round != "" {
			roundInfo = fmt.Sprintf(" (Round %s)", m.Round)
		} else if m.Stage != "" {
			roundInfo = fmt.Sprintf(" (%s)", m.Stage)
		}
		fmt.Fprintf(&sb, "  %s: %s %d-%d %s [%s%s] %s\n",
			dateStr,
			m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam,
			m.Competition, roundInfo,
			winner,
		)
	}
	if total > limit {
		fmt.Fprintf(&sb, "  ... and %d more matches\n", total-limit)
	}

	return sb.String(), nil
}

func (s *Server) toolTeamStats(team, competition string, season int, homeOnly bool) (string, error) {
	if team == "" {
		return "", fmt.Errorf("team name is required")
	}
	matches := s.db.FilterMatches(team, competition, season)
	rec := TeamStats(team, matches, homeOnly)

	qualifier := "all competitions"
	if competition != "" {
		qualifier = competition
	}
	if season > 0 {
		qualifier += fmt.Sprintf(" %d", season)
	}
	scope := "overall"
	if homeOnly {
		scope = "home"
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "=== %s — %s record (%s) ===\n", team, scope, qualifier)
	fmt.Fprintf(&sb, "Matches:  %d\n", rec.Matches)
	fmt.Fprintf(&sb, "Wins:     %d\n", rec.Wins)
	fmt.Fprintf(&sb, "Draws:    %d\n", rec.Draws)
	fmt.Fprintf(&sb, "Losses:   %d\n", rec.Losses)
	fmt.Fprintf(&sb, "Points:   %d\n", rec.Points)
	fmt.Fprintf(&sb, "Goals For: %d\n", rec.GoalsFor)
	fmt.Fprintf(&sb, "Goals Against: %d\n", rec.GoalsAgainst)
	fmt.Fprintf(&sb, "Goal Difference: %+d\n", rec.GoalsFor-rec.GoalsAgainst)
	fmt.Fprintf(&sb, "Win Rate: %.1f%%\n", rec.WinRate())

	if rec.Matches == 0 {
		fmt.Fprintf(&sb, "\nNote: no matches found for this criteria.\n")
	}
	return sb.String(), nil
}

func (s *Server) toolStandings(competition string, season int, limit int) (string, error) {
	if limit <= 0 {
		limit = 20
	}
	standings := s.db.Standings(competition, season)
	if len(standings) == 0 {
		return "No data found for the specified competition/season.", nil
	}

	qualifier := competition
	if qualifier == "" {
		qualifier = "all competitions"
	}
	if season > 0 {
		qualifier = fmt.Sprintf("%s %d", qualifier, season)
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "=== Standings: %s ===\n", qualifier)
	fmt.Fprintf(&sb, "%-4s %-30s %4s %4s %4s %4s %5s %5s %5s\n",
		"Pos", "Team", "P", "W", "D", "L", "GF", "GA", "Pts")
	fmt.Fprintf(&sb, "%s\n", strings.Repeat("-", 70))

	show := standings
	if len(show) > limit {
		show = show[:limit]
	}
	for i, r := range show {
		team := r.Team
		if len(team) > 29 {
			team = team[:29]
		}
		fmt.Fprintf(&sb, "%-4d %-30s %4d %4d %4d %4d %5d %5d %5d\n",
			i+1, team, r.Matches, r.Wins, r.Draws, r.Losses,
			r.GoalsFor, r.GoalsAgainst, r.Points)
	}
	if len(standings) > limit {
		fmt.Fprintf(&sb, "... and %d more teams\n", len(standings)-limit)
	}
	return sb.String(), nil
}

func (s *Server) toolBiggestWins(competition string, season, limit int) (string, error) {
	if limit <= 0 {
		limit = 10
	}
	matches := s.db.BiggestWins(limit, competition, season)

	qualifier := "all data"
	if competition != "" {
		qualifier = competition
	}
	if season > 0 {
		qualifier += fmt.Sprintf(" %d", season)
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "=== Biggest wins (%s) ===\n", qualifier)
	for i, m := range matches {
		diff := abs(m.HomeGoals - m.AwayGoals)
		dateStr := "unknown"
		if !m.DateTime.IsZero() {
			dateStr = m.DateTime.Format("2006-01-02")
		}
		stageInfo := ""
		if m.Stage != "" {
			stageInfo = " [" + m.Stage + "]"
		} else if m.Round != "" {
			stageInfo = " [Round " + m.Round + "]"
		}
		fmt.Fprintf(&sb, "%2d. %s: %s %d-%d %s (%s%s, diff: %d)\n",
			i+1, dateStr,
			m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam,
			m.Competition, stageInfo, diff)
	}
	return sb.String(), nil
}

func (s *Server) toolSearchPlayers(name, nationality, club, position string, limit int) (string, error) {
	if limit <= 0 {
		limit = defaultLimit
	}
	players := s.db.FilterPlayers(name, nationality, club, position)
	total := len(players)
	if len(players) > limit {
		players = players[:limit]
	}
	if total == 0 {
		return "No players found matching the given criteria.", nil
	}

	var sb strings.Builder
	filters := []string{}
	if name != "" {
		filters = append(filters, "name="+name)
	}
	if nationality != "" {
		filters = append(filters, "nationality="+nationality)
	}
	if club != "" {
		filters = append(filters, "club="+club)
	}
	if position != "" {
		filters = append(filters, "position="+position)
	}
	filterStr := strings.Join(filters, ", ")
	if filterStr == "" {
		filterStr = "all"
	}
	fmt.Fprintf(&sb, "=== Players (%s): %d total, showing %d ===\n\n", filterStr, total, len(players))
	fmt.Fprintf(&sb, "%-4s %-25s %-4s %-12s %-8s %-35s %-6s %s\n",
		"#", "Name", "Age", "Nationality", "Position", "Club", "OVR", "POT")
	fmt.Fprintf(&sb, "%s\n", strings.Repeat("-", 100))
	for i, p := range players {
		pname := p.Name
		if len(pname) > 24 {
			pname = pname[:24]
		}
		pclub := p.Club
		if len(pclub) > 34 {
			pclub = pclub[:34]
		}
		fmt.Fprintf(&sb, "%-4d %-25s %-4d %-12s %-8s %-35s %-6d %d\n",
			i+1, pname, p.Age, p.Nationality[:min(12, len(p.Nationality))],
			p.Position[:min(8, len(p.Position))], pclub, p.Overall, p.Potential)
	}
	if total > limit {
		fmt.Fprintf(&sb, "\n... and %d more players\n", total-limit)
	}
	return sb.String(), nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func (s *Server) toolCompetitionStats(competition string, season int) (string, error) {
	matches := s.db.FilterMatches("", competition, season)
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}

	gpm := GoalsPerMatch(matches)
	hwr := HomeWinRate(matches)

	awayWins := 0
	draws := 0
	for _, m := range matches {
		if m.AwayGoals > m.HomeGoals {
			awayWins++
		} else if m.AwayGoals == m.HomeGoals {
			draws++
		}
	}

	qualifier := competition
	if qualifier == "" {
		qualifier = "all competitions"
	}
	if season > 0 {
		qualifier = fmt.Sprintf("%s %d", qualifier, season)
	}

	topTeams := s.db.TopScoringTeams(competition, season, 5)

	var sb strings.Builder
	fmt.Fprintf(&sb, "=== Competition Stats: %s ===\n\n", qualifier)
	fmt.Fprintf(&sb, "Total Matches:    %d\n", len(matches))
	fmt.Fprintf(&sb, "Goals Per Match:  %.2f\n", gpm)
	fmt.Fprintf(&sb, "Home Win Rate:    %.1f%%\n", hwr)
	fmt.Fprintf(&sb, "Away Win Rate:    %.1f%%\n", float64(awayWins)/float64(len(matches))*100)
	fmt.Fprintf(&sb, "Draw Rate:        %.1f%%\n", float64(draws)/float64(len(matches))*100)

	if len(topTeams) > 0 {
		fmt.Fprintf(&sb, "\nTop Scoring Teams:\n")
		for i, t := range topTeams {
			fmt.Fprintf(&sb, "  %d. %-30s — %d goals in %d matches (%.1f per match)\n",
				i+1, t.Team, t.GoalsFor, t.Matches,
				float64(t.GoalsFor)/float64(t.Matches))
		}
	}

	seasons := s.db.Seasons(competition)
	if len(seasons) > 0 {
		fmt.Fprintf(&sb, "\nAvailable Seasons: ")
		parts := make([]string, len(seasons))
		for i, ss := range seasons {
			parts[i] = fmt.Sprintf("%d", ss)
		}
		fmt.Fprintf(&sb, "%s\n", strings.Join(parts, ", "))
	}

	return sb.String(), nil
}

func (s *Server) toolListTeams(competition string, season int) (string, error) {
	matches := s.db.FilterMatches("", competition, season)
	seen := make(map[string]struct{})
	for _, m := range matches {
		seen[m.HomeTeam] = struct{}{}
		seen[m.AwayTeam] = struct{}{}
	}
	teams := make([]string, 0, len(seen))
	for t := range seen {
		teams = append(teams, t)
	}
	sort.Strings(teams)

	qualifier := competition
	if qualifier == "" {
		qualifier = "all competitions"
	}
	if season > 0 {
		qualifier = fmt.Sprintf("%s %d", qualifier, season)
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "=== Teams in %s: %d teams ===\n\n", qualifier, len(teams))
	for i, t := range teams {
		fmt.Fprintf(&sb, "  %d. %s\n", i+1, t)
	}
	return sb.String(), nil
}
