package query

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"soccer-mcp/models"
)

// MatchQuery handles match-related queries
type MatchQuery struct {
	store *models.DataStore
}

// NewMatchQuery creates a new MatchQuery instance
func NewMatchQuery(store *models.DataStore) *MatchQuery {
	return &MatchQuery{store: store}
}

// FindMatchesByTeams finds matches between two teams
func (q *MatchQuery) FindMatchesByTeams(team1, team2 string, limit int) ([]models.Match, error) {
	var matches []models.Match
	team1 = normalizeTeamName(team1)
	team2 = normalizeTeamName(team2)

	// Search all match datasets
	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if (match.HomeTeam == team1 && match.AwayTeam == team2) ||
			(match.HomeTeam == team2 && match.AwayTeam == team1) {
			matches = append(matches, match)
		}
	}

	// Sort by date (most recent first)
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date.After(matches[j].Date)
	})

	if limit > 0 && len(matches) > limit {
		matches = matches[:limit]
	}

	return matches, nil
}

// FindMatchesByTeam finds all matches for a specific team
func (q *MatchQuery) FindMatchesByTeam(team string, season int, competition string, limit int) ([]models.Match, error) {
	var matches []models.Match
	team = normalizeTeamName(team)

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if (match.HomeTeam == team || match.AwayTeam == team) {
			// Filter by season if specified
			if season > 0 && match.Season != season {
				continue
			}
			// Filter by competition if specified
			if competition != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(competition)) {
				continue
			}
			matches = append(matches, match)
		}
	}

	// Sort by date (most recent first)
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date.After(matches[j].Date)
	})

	if limit > 0 && len(matches) > limit {
		matches = matches[:limit]
	}

	return matches, nil
}

// FindMatchesByDateRange finds matches within a date range
func (q *MatchQuery) FindMatchesByDateRange(startDate, endDate time.Time, limit int) ([]models.Match, error) {
	var matches []models.Match

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if !match.Date.IsZero() {
			if (match.Date.After(startDate) || match.Date.Equal(startDate)) &&
				(match.Date.Before(endDate) || match.Date.Equal(endDate)) {
				matches = append(matches, match)
			}
		}
	}

	// Sort by date
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date.Before(matches[j].Date)
	})

	if limit > 0 && len(matches) > limit {
		matches = matches[:limit]
	}

	return matches, nil
}

// FindMatchesByCompetition finds matches in a specific competition
func (q *MatchQuery) FindMatchesByCompetition(competition string, season int, limit int) ([]models.Match, error) {
	var matches []models.Match

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(competition)) {
			if season > 0 && match.Season != season {
				continue
			}
			matches = append(matches, match)
		}
	}

	// Sort by date
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date.Before(matches[j].Date)
	})

	if limit > 0 && len(matches) > limit {
		matches = matches[:limit]
	}

	return matches, nil
}

// GetTeamStats calculates statistics for a team in a specific season
func (q *MatchQuery) GetTeamStats(team string, season int) (*models.TeamStats, error) {
	team = normalizeTeamName(team)
	stats := &models.TeamStats{
		TeamName: team,
	}

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if match.Season != season {
			continue
		}
		if match.HomeTeam == team || match.AwayTeam == team {
			stats.Matches++
			if match.HomeTeam == team {
				stats.HomeMatches++
				if match.HomeGoals > match.AwayGoals {
					stats.Wins++
					stats.HomeWins++
				} else if match.HomeGoals == match.AwayGoals {
					stats.Draws++
					stats.HomeDraws++
				} else {
					stats.Losses++
					stats.HomeLosses++
				}
				stats.GoalsFor += match.HomeGoals
				stats.GoalsAgainst += match.AwayGoals
			} else {
				stats.AwayMatches++
				if match.AwayGoals > match.HomeGoals {
					stats.Wins++
					stats.AwayWins++
				} else if match.AwayGoals == match.HomeGoals {
					stats.Draws++
					stats.AwayDraws++
				} else {
					stats.Losses++
					stats.AwayLosses++
				}
				stats.GoalsFor += match.AwayGoals
				stats.GoalsAgainst += match.HomeGoals
			}
		}
	}

	stats.GoalDiff = stats.GoalsFor - stats.GoalsAgainst
	// 3 points for win, 1 for draw
	stats.Points = stats.Wins*3 + stats.Draws

	return stats, nil
}

// GetHeadToHead calculates head-to-head record between two teams
func (q *MatchQuery) GetHeadToHead(team1, team2 string) (*models.HeadToHead, error) {
	h2h := &models.HeadToHead{
		Team1: team1,
		Team2: team2,
	}

	matches, err := q.FindMatchesByTeams(team1, team2, 0)
	if err != nil {
		return nil, err
	}

	h2h.Matches = matches

	for _, match := range matches {
		team1Scored := 0
		team2Scored := 0

		if match.HomeTeam == normalizeTeamName(team1) {
			team1Scored = match.HomeGoals
			team2Scored = match.AwayGoals
		} else {
			team1Scored = match.AwayGoals
			team2Scored = match.HomeGoals
		}

		if team1Scored > team2Scored {
			h2h.Team1Wins++
			h2h.Team1Goals += team1Scored
			h2h.Team2Goals += team2Scored
		} else if team2Scored > team1Scored {
			h2h.Team2Wins++
			h2h.Team1Goals += team1Scored
			h2h.Team2Goals += team2Scored
		} else {
			h2h.Draws++
			h2h.Team1Goals += team1Scored
			h2h.Team2Goals += team2Scored
		}
	}

	return h2h, nil
}

// GetBiggestWins finds the biggest victories in matches
func (q *MatchQuery) GetBiggestWins(limit int) ([]models.Match, error) {
	var wins []models.Match

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		goalDiff := match.HomeGoals - match.AwayGoals
		if goalDiff < 0 {
			goalDiff = -goalDiff
		}
		if goalDiff >= 3 {
			match.GoalDiff = goalDiff
			wins = append(wins, match)
		}
	}

	// Sort by goal difference (descending)
	sort.Slice(wins, func(i, j int) bool {
		return wins[i].GoalDiff > wins[j].GoalDiff
	})

	if limit > 0 && len(wins) > limit {
		wins = wins[:limit]
	}

	return wins, nil
}

// GetAverageGoals calculates average goals per match for a competition
func (q *MatchQuery) GetAverageGoals(competition string, season int) (float64, int, error) {
	var totalGoals int
	var matchCount int

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if competition != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(competition)) {
			continue
		}
		if season > 0 && match.Season != season {
			continue
		}
		totalGoals += match.HomeGoals + match.AwayGoals
		matchCount++
	}

	if matchCount == 0 {
		return 0, 0, fmt.Errorf("no matches found")
	}

	avg := float64(totalGoals) / float64(matchCount)
	return avg, matchCount, nil
}

// normalizeTeamName is a helper to normalize team names
func normalizeTeamName(name string) string {
	if name == "" {
		return ""
	}
	// Simple normalization - remove spaces and convert to lowercase for comparison
	return strings.ToLower(strings.TrimSpace(name))
}
