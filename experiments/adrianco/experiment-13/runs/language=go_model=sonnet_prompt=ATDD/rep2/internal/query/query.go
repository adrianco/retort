package query

import (
	"sort"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/loader"
)

// MatchFilter defines criteria for finding matches.
type MatchFilter struct {
	Team1       string
	Team2       string
	Team        string
	Competition string
	Season      int
	DateFrom    time.Time
	DateTo      time.Time
}

// TeamStatsFilter defines criteria for team statistics.
type TeamStatsFilter struct {
	Team        string
	Competition string
	Season      int
}

// PlayerFilter defines criteria for player search.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Limit       int
}

// StandingsFilter for competition standings.
type StandingsFilter struct {
	Competition string
	Season      int
}

// MatchResult is a match with normalized names for output.
type MatchResult struct {
	Competition string
	HomeTeam    string
	AwayTeam    string
	HomeGoal    int
	AwayGoal    int
	Season      int
	Date        time.Time
	Round       string
	Stage       string
}

// TeamStats holds aggregated stats.
type TeamStats struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
}

// StandingRow is one row in a standings table.
type StandingRow struct {
	Position     int
	Team         string
	Points       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	GoalDiff     int
	Matches      int
}

// H2H holds head-to-head summary.
type H2H struct {
	Team1Wins int
	Team2Wins int
	Draws     int
}

func containsTeam(name, query string) bool {
	name = strings.ToLower(loader.NormalizeTeam(name))
	query = strings.ToLower(loader.NormalizeTeam(query))
	return strings.Contains(name, query) || strings.Contains(query, name)
}

func competitionMatches(comp, filter string) bool {
	if filter == "" {
		return true
	}
	cl := strings.ToLower(comp)
	fl := strings.ToLower(filter)
	// Aliases
	switch fl {
	case "brasileirao", "serie a", "brasileirao serie a":
		return strings.Contains(cl, "brasileirao") || strings.Contains(cl, "série a") || strings.Contains(cl, "serie a")
	case "copa do brasil", "copa brasil":
		return strings.Contains(cl, "copa do brasil")
	case "libertadores", "copa libertadores":
		return strings.Contains(cl, "libertadores")
	}
	return strings.Contains(cl, fl)
}

// FindMatches returns matches matching the given filter.
func FindMatches(ds *loader.Dataset, f MatchFilter) ([]MatchResult, H2H) {
	var results []MatchResult

	for _, m := range ds.Matches {
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.DateFrom.IsZero() && m.Date.Before(f.DateFrom) {
			continue
		}
		if !f.DateTo.IsZero() && m.Date.After(f.DateTo) {
			continue
		}

		if f.Team1 != "" && f.Team2 != "" {
			// Must have both teams
			home1away2 := containsTeam(m.HomeTeam, f.Team1) && containsTeam(m.AwayTeam, f.Team2)
			home2away1 := containsTeam(m.HomeTeam, f.Team2) && containsTeam(m.AwayTeam, f.Team1)
			if !home1away2 && !home2away1 {
				continue
			}
		} else if f.Team != "" {
			if !containsTeam(m.HomeTeam, f.Team) && !containsTeam(m.AwayTeam, f.Team) {
				continue
			}
		}

		results = append(results, MatchResult{
			Competition: m.Competition,
			HomeTeam:    m.HomeTeam,
			AwayTeam:    m.AwayTeam,
			HomeGoal:    m.HomeGoal,
			AwayGoal:    m.AwayGoal,
			Season:      m.Season,
			Date:        m.Date,
			Round:       m.Round,
			Stage:       m.Stage,
		})
	}

	// Deduplicate: same date+home+away+competition+goals
	results = deduplicateMatches(results)

	// Sort by date descending
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date.After(results[j].Date)
	})

	h2h := H2H{}
	if f.Team1 != "" && f.Team2 != "" {
		for _, r := range results {
			isTeam1Home := containsTeam(r.HomeTeam, f.Team1)
			if isTeam1Home {
				switch {
				case r.HomeGoal > r.AwayGoal:
					h2h.Team1Wins++
				case r.HomeGoal < r.AwayGoal:
					h2h.Team2Wins++
				default:
					h2h.Draws++
				}
			} else {
				switch {
				case r.AwayGoal > r.HomeGoal:
					h2h.Team1Wins++
				case r.AwayGoal < r.HomeGoal:
					h2h.Team2Wins++
				default:
					h2h.Draws++
				}
			}
		}
	}

	return results, h2h
}

func deduplicateMatches(matches []MatchResult) []MatchResult {
	seen := make(map[string]bool)
	var out []MatchResult
	for _, m := range matches {
		key := m.Date.Format("2006-01-02") + "|" + m.HomeTeam + "|" + m.AwayTeam + "|" + m.Competition
		if !seen[key] {
			seen[key] = true
			out = append(out, m)
		}
	}
	return out
}

// GetTeamStats calculates stats for a team.
func GetTeamStats(ds *loader.Dataset, f TeamStatsFilter) *TeamStats {
	stats := &TeamStats{Team: f.Team}

	for _, m := range ds.Matches {
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}

		isHome := containsTeam(m.HomeTeam, f.Team)
		isAway := containsTeam(m.AwayTeam, f.Team)

		if !isHome && !isAway {
			continue
		}

		stats.Matches++
		if isHome {
			stats.GoalsFor += m.HomeGoal
			stats.GoalsAgainst += m.AwayGoal
			switch {
			case m.HomeGoal > m.AwayGoal:
				stats.Wins++
				stats.Points += 3
			case m.HomeGoal == m.AwayGoal:
				stats.Draws++
				stats.Points++
			default:
				stats.Losses++
			}
		} else {
			stats.GoalsFor += m.AwayGoal
			stats.GoalsAgainst += m.HomeGoal
			switch {
			case m.AwayGoal > m.HomeGoal:
				stats.Wins++
				stats.Points += 3
			case m.AwayGoal == m.HomeGoal:
				stats.Draws++
				stats.Points++
			default:
				stats.Losses++
			}
		}
	}

	return stats
}

// FindPlayers returns players matching the filter, sorted by overall desc.
func FindPlayers(ds *loader.Dataset, f PlayerFilter) []loader.Player {
	var results []loader.Player

	for _, p := range ds.Players {
		if f.Name != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(f.Name)) {
			continue
		}
		if f.Nationality != "" && !strings.EqualFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(f.Club)) {
			continue
		}
		results = append(results, p)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})

	if f.Limit > 0 && len(results) > f.Limit {
		results = results[:f.Limit]
	}

	return results
}

// GetStandings computes a league table from match results.
func GetStandings(ds *loader.Dataset, f StandingsFilter) []StandingRow {
	table := make(map[string]*StandingRow)

	for _, m := range ds.Matches {
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}

		ensureRow(table, m.HomeTeam)
		ensureRow(table, m.AwayTeam)

		home := table[m.HomeTeam]
		away := table[m.AwayTeam]

		home.Matches++
		away.Matches++
		home.GoalsFor += m.HomeGoal
		home.GoalsAgainst += m.AwayGoal
		away.GoalsFor += m.AwayGoal
		away.GoalsAgainst += m.HomeGoal

		switch {
		case m.HomeGoal > m.AwayGoal:
			home.Wins++
			home.Points += 3
			away.Losses++
		case m.HomeGoal < m.AwayGoal:
			away.Wins++
			away.Points += 3
			home.Losses++
		default:
			home.Draws++
			away.Draws++
			home.Points++
			away.Points++
		}
	}

	rows := make([]StandingRow, 0, len(table))
	for _, r := range table {
		r.GoalDiff = r.GoalsFor - r.GoalsAgainst
		rows = append(rows, *r)
	}

	sort.Slice(rows, func(i, j int) bool {
		if rows[i].Points != rows[j].Points {
			return rows[i].Points > rows[j].Points
		}
		if rows[i].Wins != rows[j].Wins {
			return rows[i].Wins > rows[j].Wins
		}
		return rows[i].GoalDiff > rows[j].GoalDiff
	})

	for i := range rows {
		rows[i].Position = i + 1
	}

	return rows
}

func ensureRow(table map[string]*StandingRow, team string) {
	if _, ok := table[team]; !ok {
		table[team] = &StandingRow{Team: team}
	}
}

// Statistics holds aggregate stats for a competition/season.
type Statistics struct {
	TotalMatches     int
	TotalGoals       int
	HomeWins         int
	AwayWins         int
	Draws            int
	AvgGoalsPerMatch float64
	HomeWinRate      float64
}

// GetStatistics calculates aggregate stats.
func GetStatistics(ds *loader.Dataset, f StandingsFilter) Statistics {
	var s Statistics

	for _, m := range ds.Matches {
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		s.TotalMatches++
		s.TotalGoals += m.HomeGoal + m.AwayGoal
		switch {
		case m.HomeGoal > m.AwayGoal:
			s.HomeWins++
		case m.HomeGoal < m.AwayGoal:
			s.AwayWins++
		default:
			s.Draws++
		}
	}

	if s.TotalMatches > 0 {
		s.AvgGoalsPerMatch = float64(s.TotalGoals) / float64(s.TotalMatches)
		s.HomeWinRate = float64(s.HomeWins) / float64(s.TotalMatches)
	}

	return s
}
