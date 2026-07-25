package query

import (
	"sort"

	"soccer-mcp/models"
)

// StatisticalQuery handles statistical analysis queries
type StatisticalQuery struct {
	store *models.DataStore
}

// NewStatisticalQuery creates a new StatisticalQuery instance
func NewStatisticalQuery(store *models.DataStore) *StatisticalQuery {
	return &StatisticalQuery{store: store}
}

// GetAverageGoalsPerMatch calculates average goals per match
func (q *StatisticalQuery) GetAverageGoalsPerMatch(limit int) (float64, int, error) {
	var totalGoals int
	var matchCount int

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		totalGoals += match.HomeGoals + match.AwayGoals
		matchCount++
	}

	if matchCount == 0 {
		return 0, 0, nil
	}

	avg := float64(totalGoals) / float64(matchCount)
	return avg, matchCount, nil
}

// GetHomeWinRate calculates home win rate
func (q *StatisticalQuery) GetHomeWinRate(limit int) (float64, int, error) {
	var homeWins int
	var homeMatches int

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		homeMatches++
		if match.HomeGoals > match.AwayGoals {
			homeWins++
		}
	}

	if homeMatches == 0 {
		return 0, 0, nil
	}

	rate := float64(homeWins) / float64(homeMatches) * 100
	return rate, homeMatches, nil
}

// GetTopWinners finds teams with most wins
func (q *StatisticalQuery) GetTopWinners(limit int) ([]models.TeamStats, error) {
	teamStats := make(map[string]*models.TeamStats)

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if _, exists := teamStats[match.HomeTeam]; !exists {
			teamStats[match.HomeTeam] = &models.TeamStats{TeamName: match.HomeTeam}
		}
		if _, exists := teamStats[match.AwayTeam]; !exists {
			teamStats[match.AwayTeam] = &models.TeamStats{TeamName: match.AwayTeam}
		}

		homeStats := teamStats[match.HomeTeam]
		awayStats := teamStats[match.AwayTeam]

		homeStats.Matches++
		awayStats.Matches++

		if match.HomeGoals > match.AwayGoals {
			homeStats.Wins++
		} else if match.HomeGoals < match.AwayGoals {
			awayStats.Wins++
		} else {
			homeStats.Draws++
			awayStats.Draws++
		}

		homeStats.GoalsFor += match.HomeGoals
		homeStats.GoalsAgainst += match.AwayGoals
		awayStats.GoalsFor += match.AwayGoals
		awayStats.GoalsAgainst += match.HomeGoals
	}

	var standings []models.TeamStats
	for _, stats := range teamStats {
		stats.GoalDiff = stats.GoalsFor - stats.GoalsAgainst
		stats.Points = stats.Wins*3 + stats.Draws
		standings = append(standings, *stats)
	}

	// Sort by wins (descending)
	sort.Slice(standings, func(i, j int) bool {
		return standings[i].Wins > standings[j].Wins
	})

	if limit > 0 && len(standings) > limit {
		standings = standings[:limit]
	}

	return standings, nil
}

// GetBiggestWins finds matches with biggest goal differences
func (q *StatisticalQuery) GetBiggestWins(limit int) ([]models.Match, error) {
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
		match.GoalDiff = goalDiff
		if goalDiff >= 3 {
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

// GetBestAwayRecords finds teams with best away records
func (q *StatisticalQuery) GetBestAwayRecords(limit int) ([]models.TeamStats, error) {
	teamStats := make(map[string]*models.TeamStats)

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if _, exists := teamStats[match.AwayTeam]; !exists {
			teamStats[match.AwayTeam] = &models.TeamStats{TeamName: match.AwayTeam}
		}

		awayStats := teamStats[match.AwayTeam]
		awayStats.AwayMatches++
		awayStats.GoalsFor += match.AwayGoals
		awayStats.GoalsAgainst += match.HomeGoals

		if match.AwayGoals > match.HomeGoals {
			awayStats.AwayWins++
			awayStats.Points += 3
		} else if match.AwayGoals == match.HomeGoals {
			awayStats.AwayDraws++
			awayStats.Points += 1
		} else {
			awayStats.AwayLosses++
		}
	}

	var standings []models.TeamStats
	for _, stats := range teamStats {
		stats.GoalDiff = stats.GoalsFor - stats.GoalsAgainst
		standings = append(standings, *stats)
	}

	// Sort by away points (descending)
	sort.Slice(standings, func(i, j int) bool {
		return standings[i].Points > standings[j].Points
	})

	if limit > 0 && len(standings) > limit {
		standings = standings[:limit]
	}

	return standings, nil
}

// GetTeamPerformanceTrend calculates a team's performance trend
func (q *StatisticalQuery) GetTeamPerformanceTrend(team string, limit int) ([]models.Match, error) {
	var matches []models.Match

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if match.HomeTeam == team || match.AwayTeam == team {
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

// GetRecentResults gets recent results for a team
func (q *StatisticalQuery) GetRecentResults(team string, limit int) ([]models.Match, error) {
	return q.GetTeamPerformanceTrend(team, limit)
}

// GetHeadToHeadStats calculates head-to-head statistics
func (q *StatisticalQuery) GetHeadToHeadStats(team1, team2 string) (*models.HeadToHead, error) {
	h2h := &models.HeadToHead{
		Team1: team1,
		Team2: team2,
	}

	matchQuery := NewMatchQuery(q.store)
	matches, err := matchQuery.FindMatchesByTeams(team1, team2, 0)
	if err != nil {
		return nil, err
	}

	h2h.Matches = matches

	for _, match := range matches {
		team1Scored := 0
		team2Scored := 0

		if match.HomeTeam == team1 {
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

// GetGoalsPerGameBySeason calculates average goals per game by season
func (q *StatisticalQuery) GetGoalsPerGameBySeason() (map[int]float64, error) {
	type seasonData struct {
		totalGoals int
		matchCount int
	}
	seasonStats := make(map[int]*seasonData)

	allMatches := append(
		append(append(q.store.BrasileiraoMatches, q.store.CopaDoBrasilMatches...), q.store.LibertadoresMatches...),
		q.store.ExtendedMatches...,
	)
	allMatches = append(allMatches, q.store.HistoricalMatches...)

	for _, match := range allMatches {
		if _, exists := seasonStats[match.Season]; !exists {
			seasonStats[match.Season] = &seasonData{}
		}
		seasonStats[match.Season].totalGoals += match.HomeGoals + match.AwayGoals
		seasonStats[match.Season].matchCount++
	}

	seasonAvg := make(map[int]float64)
	for season, stats := range seasonStats {
		seasonAvg[season] = float64(stats.totalGoals) / float64(stats.matchCount)
	}

	return seasonAvg, nil
}
