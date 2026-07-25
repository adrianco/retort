package query

import (
	"sort"
	"strings"

	"soccer-mcp/models"
)

// CompetitionQuery handles competition-related queries
type CompetitionQuery struct {
	store *models.DataStore
}

// NewCompetitionQuery creates a new CompetitionQuery instance
func NewCompetitionQuery(store *models.DataStore) *CompetitionQuery {
	return &CompetitionQuery{store: store}
}

// GetStandings calculates standings for a competition in a season
func (q *CompetitionQuery) GetStandings(competition string, season int) ([]models.TeamStats, error) {
	var standings []models.TeamStats
	teamStats := make(map[string]*models.TeamStats)

	// Collect all matches for the specified competition and season
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

		// Initialize team stats if not exists
		if _, exists := teamStats[match.HomeTeam]; !exists {
			teamStats[match.HomeTeam] = &models.TeamStats{TeamName: match.HomeTeam}
		}
		if _, exists := teamStats[match.AwayTeam]; !exists {
			teamStats[match.AwayTeam] = &models.TeamStats{TeamName: match.AwayTeam}
		}

		homeStats := teamStats[match.HomeTeam]
		awayStats := teamStats[match.AwayTeam]

		// Update home team stats
		homeStats.Matches++
		homeStats.HomeMatches++
		homeStats.GoalsFor += match.HomeGoals
		homeStats.GoalsAgainst += match.AwayGoals

		// Update away team stats
		awayStats.Matches++
		awayStats.AwayMatches++
		awayStats.GoalsFor += match.AwayGoals
		awayStats.GoalsAgainst += match.HomeGoals

		// Determine winner and update points
		if match.HomeGoals > match.AwayGoals {
			homeStats.Wins++
			homeStats.HomeWins++
			homeStats.Points += 3
			awayStats.Losses++
			awayStats.AwayLosses++
		} else if match.HomeGoals < match.AwayGoals {
			awayStats.Wins++
			awayStats.AwayWins++
			awayStats.Points += 3
			homeStats.Losses++
			homeStats.HomeLosses++
		} else {
			homeStats.Draws++
			homeStats.HomeDraws++
			awayStats.Draws++
			awayStats.AwayDraws++
			homeStats.Points += 1
			awayStats.Points += 1
		}
	}

	// Convert map to slice
	for _, stats := range teamStats {
		stats.GoalDiff = stats.GoalsFor - stats.GoalsAgainst
		standings = append(standings, *stats)
	}

	// Sort by points (descending), then goal difference (descending), then goals for (descending)
	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalDiff != standings[j].GoalDiff {
			return standings[i].GoalDiff > standings[j].GoalDiff
		}
		return standings[i].GoalsFor > standings[j].GoalsFor
	})

	return standings, nil
}

// GetCompetitionResults gets all results for a competition
func (q *CompetitionQuery) GetCompetitionResults(competition string, season int, limit int) ([]models.Match, error) {
	var results []models.Match

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
			results = append(results, match)
		}
	}

	// Sort by date
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date.Before(results[j].Date)
	})

	if limit > 0 && len(results) > limit {
		results = results[:limit]
	}

	return results, nil
}

// GetChampion finds the champion of a competition in a season
func (q *CompetitionQuery) GetChampion(competition string, season int) (*models.TeamStats, error) {
	standings, err := q.GetStandings(competition, season)
	if err != nil {
		return nil, err
	}

	if len(standings) == 0 {
		return nil, nil
	}

	// Return first team (highest ranked)
	return &standings[0], nil
}

// GetRelegatedTeams finds teams that were relegated (bottom 4 in Brasileirão)
func (q *CompetitionQuery) GetRelegatedTeams(season int) ([]models.TeamStats, error) {
	standings, err := q.GetStandings("Brasileirão", season)
	if err != nil {
		return nil, err
	}

	if len(standings) < 4 {
		return standings, nil
	}

	// Get last 4 teams (relegated)
	relegated := standings[len(standings)-4:]
	return relegated, nil
}

// GetTopScorersTeam finds the team with most goals scored
func (q *CompetitionQuery) GetTopScorersTeam(competition string, season int) (*models.TeamStats, error) {
	standings, err := q.GetStandings(competition, season)
	if err != nil {
		return nil, err
	}

	if len(standings) == 0 {
		return nil, nil
	}

	// Find team with most goals for
	var topScorer *models.TeamStats
	maxGoals := -1
	for i := range standings {
		if standings[i].GoalsFor > maxGoals {
			maxGoals = standings[i].GoalsFor
			topScorer = &standings[i]
		}
	}

	return topScorer, nil
}

// GetBestDefense finds the team with least goals conceded
func (q *CompetitionQuery) GetBestDefense(competition string, season int) (*models.TeamStats, error) {
	standings, err := q.GetStandings(competition, season)
	if err != nil {
		return nil, err
	}

	if len(standings) == 0 {
		return nil, nil
	}

	// Find team with least goals against
	var bestDefense *models.TeamStats
	minGoalsAgainst := int(^uint(0) >> 1) // Max int
	for i := range standings {
		if standings[i].GoalsAgainst < minGoalsAgainst {
			minGoalsAgainst = standings[i].GoalsAgainst
			bestDefense = &standings[i]
		}
	}

	return bestDefense, nil
}
