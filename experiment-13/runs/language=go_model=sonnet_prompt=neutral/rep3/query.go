package main

import (
	"fmt"
	"math"
	"sort"
	"strings"
)

// MatchFilter holds criteria for filtering matches
type MatchFilter struct {
	Team        string // matches either home or away (normalized)
	HomeTeam    string
	AwayTeam    string
	Competition string
	Season      int
	StartDate   string
	EndDate     string
}

// competitionMatches checks if a match's competition matches the filter string,
// handling common aliases (e.g. "Brasileirao" matches "Serie A").
func competitionMatches(matchComp, filter string) bool {
	if filter == "" {
		return true
	}
	mc := strings.ToLower(matchComp)
	f := strings.ToLower(filter)
	if strings.Contains(mc, f) {
		return true
	}
	// Brasileirao aliases
	brAliases := []string{"brasileirao", "serie a", "campeonato brasileiro"}
	isBRFilter := containsAny(f, brAliases)
	isBRMatch := containsAny(mc, brAliases)
	if isBRFilter && isBRMatch {
		return true
	}
	// Libertadores aliases
	libAliases := []string{"libertadores"}
	if containsAny(f, libAliases) && containsAny(mc, libAliases) {
		return true
	}
	return false
}

func containsAny(s string, parts []string) bool {
	for _, p := range parts {
		if strings.Contains(s, p) {
			return true
		}
	}
	return false
}

// FilterMatches returns matches that satisfy all non-zero filter fields.
// Only primary dataset matches are returned to avoid duplicates.
func (db *Database) FilterMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range db.Matches {
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		if !m.IsPrimary {
			continue
		}
		if f.Competition != "" && !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.StartDate != "" && m.Date < f.StartDate {
			continue
		}
		if f.EndDate != "" && m.Date > f.EndDate {
			continue
		}
		if f.Team != "" && !teamMatches(m.HomeNorm, f.Team) && !teamMatches(m.AwayNorm, f.Team) {
			continue
		}
		if f.HomeTeam != "" && !teamMatches(m.HomeNorm, f.HomeTeam) {
			continue
		}
		if f.AwayTeam != "" && !teamMatches(m.AwayNorm, f.AwayTeam) {
			continue
		}
		out = append(out, m)
	}
	// Sort by date desc
	sort.Slice(out, func(i, j int) bool {
		return out[i].Date > out[j].Date
	})
	return out
}

// HeadToHead returns all matches between two teams and a summary
func (db *Database) HeadToHead(team1, team2, competition string, season int) ([]Match, TeamStats, TeamStats) {
	var matches []Match
	for _, m := range db.Matches {
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		if !m.IsPrimary {
			continue
		}
		t1home := teamMatches(m.HomeNorm, team1) && teamMatches(m.AwayNorm, team2)
		t1away := teamMatches(m.AwayNorm, team1) && teamMatches(m.HomeNorm, team2)
		if !t1home && !t1away {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		matches = append(matches, m)
	}
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date > matches[j].Date
	})

	var s1, s2 TeamStats
	s1.Team = team1
	s2.Team = team2
	for _, m := range matches {
		t1home := teamMatches(m.HomeNorm, team1)
		var g1, g2 int
		if t1home {
			g1, g2 = m.HomeGoal, m.AwayGoal
		} else {
			g1, g2 = m.AwayGoal, m.HomeGoal
		}
		s1.Matches++
		s2.Matches++
		s1.GoalsFor += g1
		s1.GoalsAgainst += g2
		s2.GoalsFor += g2
		s2.GoalsAgainst += g1
		switch {
		case g1 > g2:
			s1.Wins++
			s2.Losses++
			s1.Points += 3
		case g2 > g1:
			s2.Wins++
			s1.Losses++
			s2.Points += 3
		default:
			s1.Draws++
			s2.Draws++
			s1.Points++
			s2.Points++
		}
	}
	return matches, s1, s2
}

// TeamStatsByFilter calculates stats for a team matching the given filter criteria
func (db *Database) TeamStatsByFilter(team, competition string, season int) TeamStats {
	stats := TeamStats{Team: team}
	for _, m := range db.Matches {
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		if !m.IsPrimary {
			continue // avoid double-counting from supplemental datasets
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}

		isHome := teamMatches(m.HomeNorm, team)
		isAway := teamMatches(m.AwayNorm, team)
		if !isHome && !isAway {
			continue
		}

		stats.Matches++
		var goalsFor, goalsAgainst int
		if isHome {
			goalsFor, goalsAgainst = m.HomeGoal, m.AwayGoal
		} else {
			goalsFor, goalsAgainst = m.AwayGoal, m.HomeGoal
		}
		stats.GoalsFor += goalsFor
		stats.GoalsAgainst += goalsAgainst

		switch {
		case goalsFor > goalsAgainst:
			stats.Wins++
			stats.Points += 3
		case goalsFor == goalsAgainst:
			stats.Draws++
			stats.Points++
		default:
			stats.Losses++
		}
	}
	return stats
}

// Standings calculates the Brasileirão table for a given season
func (db *Database) Standings(season int, competition string) []TeamStats {
	if competition == "" {
		competition = "Brasileirao"
	}
	// Use raw lowercase team name as key to keep "Atletico-MG" and "Atletico-PR" separate
	teamMap := make(map[string]*TeamStats)
	displayName := make(map[string]string) // display name for the key

	for _, m := range db.Matches {
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		if !m.IsPrimary {
			continue // only use canonical datasets for standings
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if m.Season != season {
			continue
		}
		for _, isHome := range []bool{true, false} {
			var teamRaw string
			var goalsFor, goalsAgainst int
			if isHome {
				teamRaw = m.HomeTeam
				goalsFor, goalsAgainst = m.HomeGoal, m.AwayGoal
			} else {
				teamRaw = m.AwayTeam
				goalsFor, goalsAgainst = m.AwayGoal, m.HomeGoal
			}
			// Use lowercase raw name as key to avoid merging different teams
			// (e.g., "Atletico-MG" and "Atletico-PR" must stay separate)
			teamKey := strings.ToLower(removeDiacritics(strings.TrimSpace(teamRaw)))
			if _, ok := teamMap[teamKey]; !ok {
				teamMap[teamKey] = &TeamStats{Team: teamRaw}
				displayName[teamKey] = teamRaw
			}
			s := teamMap[teamKey]
			s.Matches++
			s.GoalsFor += goalsFor
			s.GoalsAgainst += goalsAgainst
			switch {
			case goalsFor > goalsAgainst:
				s.Wins++
				s.Points += 3
			case goalsFor == goalsAgainst:
				s.Draws++
				s.Points++
			default:
				s.Losses++
			}
		}
	}

	standings := make([]TeamStats, 0, len(teamMap))
	for _, s := range teamMap {
		standings = append(standings, *s)
	}
	sort.Slice(standings, func(i, j int) bool {
		a, b := standings[i], standings[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		return a.GoalDiff() > b.GoalDiff()
	})
	return standings
}

// BiggestWins returns matches sorted by goal difference (descending)
func (db *Database) BiggestWins(competition string, season int, limit int) []Match {
	var matches []Match
	for _, m := range db.Matches {
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		if !m.IsPrimary {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		diff := m.HomeGoal - m.AwayGoal
		if diff < 0 {
			diff = -diff
		}
		if diff >= 3 { // Only include notable wins
			matches = append(matches, m)
		}
	}
	sort.Slice(matches, func(i, j int) bool {
		di := int(math.Abs(float64(matches[i].HomeGoal - matches[i].AwayGoal)))
		dj := int(math.Abs(float64(matches[j].HomeGoal - matches[j].AwayGoal)))
		if di != dj {
			return di > dj
		}
		// Secondary: total goals
		ti := matches[i].HomeGoal + matches[i].AwayGoal
		tj := matches[j].HomeGoal + matches[j].AwayGoal
		return ti > tj
	})
	if limit > 0 && len(matches) > limit {
		matches = matches[:limit]
	}
	return matches
}

// CompetitionStats returns aggregate statistics for a competition/season
type CompStats struct {
	Competition   string
	Season        int
	TotalMatches  int
	TotalGoals    int
	HomeWins      int
	Draws         int
	AwayWins      int
	AvgGoals      float64
	HomeWinRate   float64
}

func (db *Database) CompetitionStats(competition string, season int) CompStats {
	stats := CompStats{Competition: competition, Season: season}
	for _, m := range db.Matches {
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		if !m.IsPrimary {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		stats.TotalMatches++
		stats.TotalGoals += m.HomeGoal + m.AwayGoal
		switch {
		case m.HomeGoal > m.AwayGoal:
			stats.HomeWins++
		case m.HomeGoal == m.AwayGoal:
			stats.Draws++
		default:
			stats.AwayWins++
		}
	}
	if stats.TotalMatches > 0 {
		stats.AvgGoals = float64(stats.TotalGoals) / float64(stats.TotalMatches)
		stats.HomeWinRate = float64(stats.HomeWins) / float64(stats.TotalMatches) * 100
	}
	return stats
}

// SearchPlayers filters FIFA player data
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	MaxAge      int
}

func (db *Database) SearchPlayers(f PlayerFilter) []Player {
	var out []Player
	for _, p := range db.Players {
		if f.Name != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(f.Name)) {
			continue
		}
		if f.Nationality != "" && !strings.Contains(strings.ToLower(p.Nationality), strings.ToLower(f.Nationality)) {
			continue
		}
		if f.Club != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(f.Club)) {
			continue
		}
		if f.Position != "" && !strings.Contains(strings.ToLower(p.Position), strings.ToLower(f.Position)) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxAge > 0 && p.Age > f.MaxAge {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].Overall > out[j].Overall
	})
	return out
}

// FormatMatch returns a human-readable match description
func FormatMatch(m Match) string {
	winner := "Draw"
	switch {
	case m.HomeGoal > m.AwayGoal:
		winner = m.HomeTeam + " wins"
	case m.AwayGoal > m.HomeGoal:
		winner = m.AwayTeam + " wins"
	}

	s := fmt.Sprintf("%s: %s %d-%d %s (%s, Season %d",
		m.Date, m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam, m.Competition, m.Season)
	if m.Round != "" {
		s += fmt.Sprintf(", Round %s", m.Round)
	}
	if m.Stage != "" {
		s += fmt.Sprintf(", %s", m.Stage)
	}
	s += fmt.Sprintf(") [%s]", winner)
	return s
}

// FormatStats returns a human-readable team stats string
func FormatStats(s TeamStats) string {
	return fmt.Sprintf("%s: %d matches, %dW/%dD/%dL, Goals: %d-%d (diff %+d), Points: %d, Win rate: %.1f%%",
		s.Team, s.Matches, s.Wins, s.Draws, s.Losses,
		s.GoalsFor, s.GoalsAgainst, s.GoalDiff(),
		s.Points, s.WinRate())
}

// FormatPlayer returns a human-readable player string
func FormatPlayer(p Player) string {
	return fmt.Sprintf("%s (Overall: %d, Potential: %d, Club: %s, Position: %s, Age: %d, Nationality: %s, Value: %s)",
		p.Name, p.Overall, p.Potential, p.Club, p.Position, p.Age, p.Nationality, p.Value)
}
