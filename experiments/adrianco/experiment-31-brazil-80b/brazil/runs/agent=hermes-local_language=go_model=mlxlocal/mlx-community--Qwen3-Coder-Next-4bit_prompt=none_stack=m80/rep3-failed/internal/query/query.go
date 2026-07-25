// Package query provides query handlers for the Brazilian Soccer MCP Server
package query

import (
	"fmt"
	"sort"
	"strings"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/models"
)

// Server represents the MCP server with data access
type Server struct {
	MatchData *data.MatchData
	PlayerData *data.PlayerData
}

// New creates a new query server
func New(matchData *data.MatchData, playerData *data.PlayerData) *Server {
	return &Server{
		MatchData:  matchData,
		PlayerData: playerData,
	}
}

// Query handles incoming queries
func (s *Server) Query(req models.QueryRequest) models.QueryResponse {
	switch req.Type {
	case "match":
		return s.handleMatchQuery(req)
	case "team":
		return s.handleTeamQuery(req)
	case "player":
		return s.handlePlayerQuery(req)
	case "competition":
		return s.handleCompetitionQuery(req)
	case "statistics":
		return s.handleStatisticsQuery(req)
	default:
		return models.QueryResponse{
			Success: false,
			Error:   fmt.Sprintf("unknown query type: %s", req.Type),
		}
	}
}

// Match Queries

func (s *Server) handleMatchQuery(req models.QueryRequest) models.QueryResponse {
	params := req.Params

	// Find matches by criteria
	matches := s.MatchData.GetAllMatches()

	// Filter by home team
	if team, ok := params["home_team"].(string); ok && team != "" {
		matches = filterByTeam(matches, team, true)
	}

	// Filter by away team
	if team, ok := params["away_team"].(string); ok && team != "" {
		matches = filterByTeam(matches, team, false)
	}

	// Filter by team (either home or away)
	if team, ok := params["team"].(string); ok && team != "" {
		var filtered []models.Match
		for _, m := range matches {
			if strings.Contains(strings.ToLower(m.HomeTeam), strings.ToLower(team)) ||
				strings.Contains(strings.ToLower(m.AwayTeam), strings.ToLower(team)) {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}

	// Filter by competition
	if comp, ok := params["competition"].(string); ok && comp != "" {
		matches = filterByCompetition(matches, comp)
	}

	// Filter by season
	if season, ok := params["season"].(int); ok {
		matches = filterBySeason(matches, season)
	}

	// Filter by round
	if round, ok := params["round"].(int); ok {
		matches = filterByRound(matches, round)
	}

	// Calculate head-to-head if both teams specified
	homeTeam := ""
	homeOk := false
	if ht, ok := params["home_team"].(string); ok {
		homeTeam, homeOk = ht, ok
	}
	awayTeam := ""
	awayOk := false
	if at, ok := params["away_team"].(string); ok {
		awayTeam, awayOk = at, ok
	}
	if homeOk && awayOk && homeTeam != "" && awayTeam != "" {
		return s.getHeadToHead(homeTeam, awayTeam)
	}

	// Return matches
	return models.QueryResponse{
		Success: true,
		Data:    matches,
		Total:   len(matches),
	}
}

func filterByTeam(matches []models.Match, team string, isHome bool) []models.Match {
	var filtered []models.Match
	for _, m := range matches {
		mTeam := m.HomeTeam
		if !isHome {
			mTeam = m.AwayTeam
		}
		if strings.Contains(strings.ToLower(mTeam), strings.ToLower(team)) {
			filtered = append(filtered, m)
		}
	}
	return filtered
}

func filterByCompetition(matches []models.Match, competition string) []models.Match {
	var filtered []models.Match
	for _, m := range matches {
		if strings.Contains(strings.ToLower(m.Competition), strings.ToLower(competition)) {
			filtered = append(filtered, m)
		}
	}
	return filtered
}

func filterBySeason(matches []models.Match, season int) []models.Match {
	var filtered []models.Match
	for _, m := range matches {
		if m.Season == season {
			filtered = append(filtered, m)
		}
	}
	return filtered
}

func filterByRound(matches []models.Match, round int) []models.Match {
	var filtered []models.Match
	for _, m := range matches {
		if m.Round == round {
			filtered = append(filtered, m)
		}
	}
	return filtered
}

func (s *Server) getHeadToHead(team1, team2 string) models.QueryResponse {
	matches := s.MatchData.GetAllMatches()

	var headToHead []models.Match
	team1Wins := 0
	team2Wins := 0
	draws := 0
	team1Goals := 0
	team2Goals := 0

	for _, m := range matches {
		if (strings.Contains(strings.ToLower(m.HomeTeam), strings.ToLower(team1)) && strings.Contains(strings.ToLower(m.AwayTeam), strings.ToLower(team2))) ||
			(strings.Contains(strings.ToLower(m.HomeTeam), strings.ToLower(team2)) && strings.Contains(strings.ToLower(m.AwayTeam), strings.ToLower(team1))) {
			headToHead = append(headToHead, m)

			if strings.Contains(strings.ToLower(m.HomeTeam), strings.ToLower(team1)) {
				team1Goals += m.HomeGoal
				team2Goals += m.AwayGoal
				if m.HomeGoal > m.AwayGoal {
					team1Wins++
				} else if m.AwayGoal > m.HomeGoal {
					team2Wins++
				} else {
					draws++
				}
			} else {
				team1Goals += m.AwayGoal
				team2Goals += m.HomeGoal
				if m.AwayGoal > m.HomeGoal {
					team1Wins++
				} else if m.HomeGoal > m.AwayGoal {
					team2Wins++
				} else {
					draws++
				}
			}
		}
	}

	// Sort by date (most recent first)
	sort.Slice(headToHead, func(i, j int) bool {
		return headToHead[i].Datetime.After(headToHead[j].Datetime)
	})

	return models.QueryResponse{
		Success: true,
		Data: models.HeadToHead{
			Team1:         team1,
			Team2:         team2,
			Matches:       headToHead,
			Team1Wins:     team1Wins,
			Team2Wins:     team2Wins,
			Draws:         draws,
			Team1Goals:    team1Goals,
			Team2Goals:    team2Goals,
		},
		Total: len(headToHead),
	}
}

// Team Queries

func (s *Server) handleTeamQuery(req models.QueryRequest) models.QueryResponse {
	params := req.Params
	teamName := ""
	if name, ok := params["team"].(string); ok {
		teamName = name
	}

	if competition, ok := params["competition"].(string); ok {
		return s.getTeamStatistics(teamName, competition)
	}

	return s.getTeamStatistics(teamName, "")
}

func (s *Server) getTeamStatistics(teamName, competition string) models.QueryResponse {
	matches := s.MatchData.GetAllMatches()
	if competition != "" {
		matches = filterByCompetition(matches, competition)
	}

	teamStats := calculateTeamStats(matches, teamName)

	return models.QueryResponse{
		Success: true,
		Data:    teamStats,
		Total:   1,
	}
}

func calculateTeamStats(matches []models.Match, teamName string) models.TeamStats {
	var stats models.TeamStats
	stats.Team = teamName

	for _, m := range matches {
		isHome := strings.Contains(strings.ToLower(m.HomeTeam), strings.ToLower(teamName))
		isAway := strings.Contains(strings.ToLower(m.AwayTeam), strings.ToLower(teamName))

		if !isHome && !isAway {
			continue
		}

		stats.Matches++
		stats.GoalsFor += getTeamGoals(m, teamName, true)
		stats.GoalsAgainst += getTeamGoals(m, teamName, false)

		if isHome {
			if m.HomeGoal > m.AwayGoal {
				stats.Wins++
				stats.HomeWins++
			} else if m.HomeGoal < m.AwayGoal {
				stats.Losses++
				stats.HomeLosses++
			} else {
				stats.Draws++
				stats.HomeDraws++
			}
		} else {
			if m.AwayGoal > m.HomeGoal {
				stats.Wins++
				stats.AwayWins++
			} else if m.AwayGoal < m.HomeGoal {
				stats.Losses++
				stats.AwayLosses++
			} else {
				stats.Draws++
				stats.AwayDraws++
			}
		}
	}

	stats.Points = stats.Wins*3 + stats.Draws
	if stats.Matches > 0 {
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}

	return stats
}

func getTeamGoals(m models.Match, teamName string, forGoals bool) int {
	isHome := strings.Contains(strings.ToLower(m.HomeTeam), strings.ToLower(teamName))
	if forGoals {
		if isHome {
			return m.HomeGoal
		}
		return m.AwayGoal
	}
	if isHome {
		return m.AwayGoal
	}
	return m.HomeGoal
}

// Player Queries

func (s *Server) handlePlayerQuery(req models.QueryRequest) models.QueryResponse {
	params := req.Params

	players := s.PlayerData.Players

	// Filter by name
	if name, ok := params["name"].(string); ok && name != "" {
		var filtered []models.Player
		for _, p := range players {
			if strings.Contains(strings.ToLower(p.Name), strings.ToLower(name)) {
				filtered = append(filtered, p)
			}
		}
		players = filtered
	}

	// Filter by nationality
	if nationality, ok := params["nationality"].(string); ok && nationality != "" {
		var filtered []models.Player
		for _, p := range players {
			if strings.Contains(strings.ToLower(p.Nationality), strings.ToLower(nationality)) {
				filtered = append(filtered, p)
			}
		}
		players = filtered
	}

	// Filter by club
	if club, ok := params["club"].(string); ok && club != "" {
		var filtered []models.Player
		for _, p := range players {
			if strings.Contains(strings.ToLower(p.Club), strings.ToLower(club)) {
				filtered = append(filtered, p)
			}
		}
		players = filtered
	}

	// Filter by position
	if position, ok := params["position"].(string); ok && position != "" {
		var filtered []models.Player
		for _, p := range players {
			if strings.Contains(strings.ToLower(p.Position), strings.ToLower(position)) {
				filtered = append(filtered, p)
			}
		}
		players = filtered
	}

	// Sort by overall rating
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	return models.QueryResponse{
		Success: true,
		Data:    players,
		Total:   len(players),
	}
}

// Competition Queries

func (s *Server) handleCompetitionQuery(req models.QueryRequest) models.QueryResponse {
	params := req.Params
	competition := ""
	if comp, ok := params["competition"].(string); ok {
		competition = comp
	}

	season := 0
	if s, ok := params["season"].(int); ok {
		season = s
	}

	return s.getCompetitionStandings(competition, season)
}

func (s *Server) getCompetitionStandings(competition string, season int) models.QueryResponse {
	matches := s.MatchData.GetAllMatches()
	if competition != "" {
		matches = filterByCompetition(matches, competition)
	}
	if season > 0 {
		matches = filterBySeason(matches, season)
	}

	standings := calculateStandings(matches)

	return models.QueryResponse{
		Success: true,
		Data:    standings,
		Total:   len(standings),
	}
}

func calculateStandings(matches []models.Match) []models.CompetitionResult {
	teamStats := make(map[string]*models.CompetitionResult)

	for _, m := range matches {
		// Skip matches without season
		if m.Season == 0 {
			continue
		}

		homeTeam := normalizeTeamName(m.HomeTeam)
		awayTeam := normalizeTeamName(m.AwayTeam)

		if _, ok := teamStats[homeTeam]; !ok {
			teamStats[homeTeam] = &models.CompetitionResult{
				Team: homeTeam,
			}
		}
		if _, ok := teamStats[awayTeam]; !ok {
			teamStats[awayTeam] = &models.CompetitionResult{
				Team: awayTeam,
			}
		}

		homeStats := teamStats[homeTeam]
		awayStats := teamStats[awayTeam]

		homeStats.Matches++
		awayStats.Matches++

		homeStats.GoalsFor += m.HomeGoal
		homeStats.GoalsAgainst += m.AwayGoal
		awayStats.GoalsFor += m.AwayGoal
		awayStats.GoalsAgainst += m.HomeGoal

		if m.HomeGoal > m.AwayGoal {
			homeStats.Wins++
			homeStats.Points += 3
			awayStats.Losses++
		} else if m.HomeGoal < m.AwayGoal {
			awayStats.Wins++
			awayStats.Points += 3
			homeStats.Losses++
		} else {
			homeStats.Draws++
			awayStats.Draws++
			homeStats.Points++
			awayStats.Points++
		}
	}

	var standings []models.CompetitionResult
	for _, stats := range teamStats {
		stats.GoalDifference = stats.GoalsFor - stats.GoalsAgainst
		standings = append(standings, *stats)
	}

	// Sort by points, then goal difference, then goals for
	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalDifference != standings[j].GoalDifference {
			return standings[i].GoalDifference > standings[j].GoalDifference
		}
		return standings[i].GoalsFor > standings[j].GoalsFor
	})

	return standings
}

func normalizeTeamName(name string) string {
	// Remove state suffix
	re := strings.LastIndex(name, "-")
	if re != -1 {
		return strings.TrimSpace(name[:re])
	}
	return strings.TrimSpace(name)
}

// Statistics Queries

func (s *Server) handleStatisticsQuery(req models.QueryRequest) models.QueryResponse {
	params := req.Params
	competition := ""
	if comp, ok := params["competition"].(string); ok {
		competition = comp
	}

	matches := s.MatchData.GetAllMatches()
	if competition != "" {
		matches = filterByCompetition(matches, competition)
	}

	stats := calculateMatchStatistics(matches)

	return models.QueryResponse{
		Success: true,
		Data:    stats,
		Total:   1,
	}
}

func calculateMatchStatistics(matches []models.Match) map[string]interface{} {
	if len(matches) == 0 {
		return map[string]interface{}{
			"total_matches":     0,
			"average_goals":     0,
			"home_win_rate":     0,
			"draw_rate":         0,
			"away_win_rate":     0,
			"total_goals":       0,
		}
	}

	totalGoals := 0
	homeWins := 0
	awayWins := 0
	draws := 0

	for _, m := range matches {
		totalGoals += m.HomeGoal + m.AwayGoal
		if m.HomeGoal > m.AwayGoal {
			homeWins++
		} else if m.HomeGoal < m.AwayGoal {
			awayWins++
		} else {
			draws++
		}
	}

	return map[string]interface{}{
		"total_matches":     len(matches),
		"average_goals":     float64(totalGoals) / float64(len(matches)),
		"home_win_rate":     float64(homeWins) / float64(len(matches)) * 100,
		"draw_rate":         float64(draws) / float64(len(matches)) * 100,
		"away_win_rate":     float64(awayWins) / float64(len(matches)) * 100,
		"total_goals":       totalGoals,
	}
}

// GetBigWins returns matches with large goal differences
func (s *Server) GetBigWins(minGoalDiff int) models.QueryResponse {
	matches := s.MatchData.GetAllMatches()
	var bigWins []models.BigWin

	for _, m := range matches {
		diff := m.HomeGoal - m.AwayGoal
		if diff < 0 {
			diff = -diff
		}
		if diff >= minGoalDiff {
			bigWins = append(bigWins, models.BigWin{
				Match:          m,
				GoalDifference: diff,
			})
		}
	}

	// Sort by goal difference (descending)
	sort.Slice(bigWins, func(i, j int) bool {
		return bigWins[i].GoalDifference > bigWins[j].GoalDifference
	})

	return models.QueryResponse{
		Success: true,
		Data:    bigWins,
		Total:   len(bigWins),
	}
}

// GetTopTeamsBySeason returns top teams for a specific season
func (s *Server) GetTopTeamsBySeason(season int, competition string) models.QueryResponse {
	matches := s.MatchData.GetAllMatches()
	if competition != "" {
		matches = filterByCompetition(matches, competition)
	}
	matches = filterBySeason(matches, season)

	standings := calculateStandings(matches)

	// Return top 10
	top := standings
	if len(top) > 10 {
		top = top[:10]
	}

	return models.QueryResponse{
		Success: true,
		Data:    top,
		Total:   len(top),
	}
}

// GetTeamsByPlayer returns teams that have players from the dataset
func (s *Server) GetTeamsByPlayer() models.QueryResponse {
	teams := make(map[string]int)
	for _, p := range s.PlayerData.Players {
		if p.Club != "" {
			teams[p.Club]++
		}
	}

	// Convert to slice and sort by player count
	type teamCount struct {
		Team   string
		Players int
	}
	var teamList []teamCount
	for team, count := range teams {
		teamList = append(teamList, teamCount{Team: team, Players: count})
	}

	sort.Slice(teamList, func(i, j int) bool {
		return teamList[i].Players > teamList[j].Players
	})

	return models.QueryResponse{
		Success: true,
		Data:    teamList,
		Total:   len(teamList),
	}
}
