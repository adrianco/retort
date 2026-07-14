// The in-memory store indexes all loaded data and provides query functions
// for the MCP server tools. It uses maps for fast team-based lookups.
package main

import (
	"sort"
	"strings"
)

// Store holds all loaded matches and players with lookup indexes.
type Store struct {
	Matches []Match
	Players []Player

	// teamMatches maps lowercase normalized team name -> indices into Matches
	teamMatches map[string][]int
}

// NewStore creates an empty store with initialized indexes.
func NewStore() *Store {
	return &Store{
		teamMatches: make(map[string][]int),
	}
}

// AddMatches adds matches and builds indexes.
func (s *Store) AddMatches(matches []Match) {
	for i, m := range matches {
		s.Matches = append(s.Matches, m)
		s.teamMatches[strings.ToLower(m.HomeTeam)] = append(s.teamMatches[strings.ToLower(m.HomeTeam)], i)
		s.teamMatches[strings.ToLower(m.AwayTeam)] = append(s.teamMatches[strings.ToLower(m.AwayTeam)], i)
	}
}

// AddPlayers adds players to the store.
func (s *Store) AddPlayers(players []Player) {
	s.Players = append(s.Players, players...)
}

// SearchMatches finds matches involving a team, filtered by optional criteria.
func (s *Store) SearchMatches(team, competition, season, dateStart, dateEnd string) []Match {
	var indices []int
	key := strings.ToLower(strings.TrimSpace(team))

	if key == "" {
		// No team filter: return all or return matches from competition
		indices = allIndices(s, competition)
	} else {
		indices = s.teamMatches[key]
	}

	result := make([]Match, 0, len(indices))
	for _, idx := range indices {
		m := s.Matches[idx]

		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != "" {
			seasonNum := parseInt(season)
			if m.Season != seasonNum {
				continue
			}
		}
		if dateStart != "" && m.DateTime < dateStart {
			continue
		}
		if dateEnd != "" && m.DateTime > dateEnd {
			continue
		}
		result = append(result, m)
	}

	sortMatches(result)
	return result
}

// TeamStats computes win/draw/loss/goals for a team.
func (s *Store) TeamStats(team, competition, season string) TeamStats {
	key := strings.ToLower(strings.TrimSpace(team))
	var stats TeamStats
	stats.TeamName = team

	for _, idx := range s.teamMatches[key] {
		m := s.Matches[idx]

		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != "" {
			seasonNum := parseInt(season)
			if m.Season != seasonNum {
				continue
			}
		}

		stats.Matches++
		stats.GoalsFor += m.HomeScore
		stats.GoalsAgainst += m.AwayScore

		if m.HomeTeam == team && m.HomeScore > m.AwayScore {
			stats.Wins++
		} else if m.HomeTeam == team && m.HomeScore == m.AwayScore {
			stats.Draws++
		} else if m.AwayTeam == team && m.AwayScore > m.HomeScore {
			stats.Wins++
		} else if m.AwayTeam == team && m.AwayScore == m.HomeScore {
			stats.Draws++
		} else {
			stats.Losses++
		}
	}

	if stats.Matches > 0 {
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}
	return stats
}

// HeadToHead computes head-to-head between two teams.
func (s *Store) HeadToHead(team1, team2 string) H2HRecord {
	h1 := strings.ToLower(strings.TrimSpace(team1))
	h2 := strings.ToLower(strings.TrimSpace(team2))
	record := H2HRecord{
		Team1:   team1,
		Team2:   team2,
		Matches: []Match{},
	}

	seen := make(map[int]bool)
	for _, idx := range s.teamMatches[h1] {
		if s.teamMatches[h2] != nil {
			for _, idx2 := range s.teamMatches[h2] {
				if idx == idx2 && !seen[idx] {
					seen[idx] = true
					m := s.Matches[idx]
					record.Matches = append(record.Matches, m)
					record.TotalMatches++

					if m.HomeScore > m.AwayScore {
						if strings.EqualFold(m.HomeTeam, team1) {
							record.Team1Wins++
						} else {
							record.Team2Wins++
						}
					} else if m.HomeScore < m.AwayScore {
						if strings.EqualFold(m.HomeTeam, team2) {
							record.Team1Wins++
						} else {
							record.Team2Wins++
						}
					} else {
						record.Draws++
					}
					break
				}
			}
		}
	}

	sortMatches(record.Matches)
	return record
}

// SearchPlayers finds players matching a name filter, nationality, or club.
func (s *Store) SearchPlayers(name, nationality, club, position string) []Player {
	result := make([]Player, 0, len(s.Players))
	for _, p := range s.Players {
		if name != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(name)) {
			continue
		}
		if nationality != "" && !strings.EqualFold(p.Nationality, nationality) {
			continue
		}
		if club != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(club)) {
			continue
		}
		if position != "" && !strings.Contains(strings.ToLower(p.Position), strings.ToLower(position)) {
			continue
		}
		result = append(result, p)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Overall > result[j].Overall
	})
	return result
}

// CompetitionStandings calculates standings for a competition+season.
func (s *Store) CompetitionStandings(competition, season string) map[string]*StandingsEntry {
	table := make(map[string]*StandingsEntry)

	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != "" {
			seasonNum := parseInt(season)
			if m.Season != seasonNum {
				continue
			}
		}

		ensureTeam(table, m.HomeTeam)
		ensureTeam(table, m.AwayTeam)

		home := table[m.HomeTeam]
		away := table[m.AwayTeam]

		home.Played++
		away.Played++
		home.GoalsFor += m.HomeScore
		home.GoalsAgainst += m.AwayScore
		away.GoalsFor += m.AwayScore
		away.GoalsAgainst += m.HomeScore

		if m.HomeScore > m.AwayScore {
			home.Wins++
			home.Points += 3
			away.Losses++
		} else if m.HomeScore < m.AwayScore {
			away.Wins++
			away.Points += 3
			home.Losses++
		} else {
			home.Draws++
			away.Draws++
			home.Points++
			away.Points++
		}
	}

	return table
}

// BiggestWins finds the biggest victories (goal difference >= 5).
func (s *Store) BiggestWins(competition string, limit int) []BigWin {
	candidates := []Match{}

	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		diff := m.HomeScore - m.AwayScore
		if diff < 0 {
			diff = -diff
		}
		if diff >= 5 {
			candidates = append(candidates, m)
		}
	}

	sort.Slice(candidates, func(i, j int) bool {
		di := absDiff(candidates[i].HomeScore, candidates[i].AwayScore)
		dj := absDiff(candidates[j].HomeScore, candidates[j].AwayScore)
		if di != dj {
			return di > dj
		}
		return candidates[i].DateTime < candidates[j].DateTime
	})

	if limit > 0 && len(candidates) > limit {
		candidates = candidates[:limit]
	}

	result := make([]BigWin, 0, len(candidates))
	for _, m := range candidates {
		result = append(result, BigWin{
			Date:        m.DateTime,
			HomeTeam:    m.HomeTeam,
			AwayTeam:    m.AwayTeam,
			HomeScore:   m.HomeScore,
			AwayScore:   m.AwayScore,
			Competition: m.Competition,
		})
	}
	return result
}

// StatsAnalysis computes overall statistics.
func (s *Store) StatsAnalysis(competition, season string) StatsSummary {
	var totalGoals, homeWins, draws, awayWins int
	var total int

	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != "" {
			seasonNum := parseInt(season)
			if m.Season != seasonNum {
				continue
			}
		}

		total++
		totalGoals += m.HomeScore + m.AwayScore
		if m.HomeScore > m.AwayScore {
			homeWins++
		} else if m.HomeScore == m.AwayScore {
			draws++
		} else {
			awayWins++
		}
	}

	if total == 0 {
		return StatsSummary{}
	}

	return StatsSummary{
		AvgGoalsPerMatch: float64(totalGoals) / float64(total),
		HomeWinRate:      float64(homeWins) / float64(total) * 100,
		DrawRate:         float64(draws) / float64(total) * 100,
		AwayWinRate:      float64(awayWins) / float64(total) * 100,
		TotalMatches:     total,
		TotalGoals:       totalGoals,
	}
}

// Helper functions
func allIndices(s *Store, competition string) []int {
	indices := make([]int, 0, len(s.Matches))
	for i := range s.Matches {
		if competition != "" && !strings.EqualFold(s.Matches[i].Competition, competition) {
			continue
		}
		indices = append(indices, i)
	}
	return indices
}

func ensureTeam(table map[string]*StandingsEntry, team string) {
	if _, ok := table[team]; !ok {
		table[team] = &StandingsEntry{Team: team}
	}
}

func sortMatches(matches []Match) {
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].DateTime < matches[j].DateTime
	})
}

func absDiff(a, b int) int {
	if a > b {
		return a - b
	}
	return b - a
}
