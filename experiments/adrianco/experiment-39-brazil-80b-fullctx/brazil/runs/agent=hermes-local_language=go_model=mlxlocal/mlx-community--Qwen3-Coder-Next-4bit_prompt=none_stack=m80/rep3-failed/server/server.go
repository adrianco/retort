package server

import (
	"fmt"
	"strings"
	"time"

	"soccer-mcp/loader"
	"soccer-mcp/models"
	"soccer-mcp/query"
)

// SoccerServer represents the MCP server for Brazilian soccer data
type SoccerServer struct {
	store       *models.DataStore
	matchQuery  *query.MatchQuery
	playerQuery *query.PlayerQuery
	compQuery   *query.CompetitionQuery
	statQuery   *query.StatisticalQuery
}

// NewSoccerServer creates a new soccer MCP server
func NewSoccerServer(dataDir string) (*SoccerServer, error) {
	store, err := loader.LoadData(dataDir)
	if err != nil {
		return nil, fmt.Errorf("failed to load data: %w", err)
	}

	return &SoccerServer{
		store:       store,
		matchQuery:  query.NewMatchQuery(store),
		playerQuery: query.NewPlayerQuery(store),
		compQuery:   query.NewCompetitionQuery(store),
		statQuery:   query.NewStatisticalQuery(store),
	}, nil
}

// Run starts the MCP server
func (s *SoccerServer) Run() error {
	fmt.Println("Brazilian Soccer MCP Server is running...")
	fmt.Println("Use the Query() method to ask questions about Brazilian soccer.")

	// Example usage
	result, err := s.Query("Who won the 2019 Brasileirão?")
	if err != nil {
		return err
	}
	fmt.Printf("Example query result: %v\n", result)

	return nil
}

// Query handles natural language queries
func (s *SoccerServer) Query(queryStr string) (*models.MCPResponse, error) {
	startTime := time.Now()

	result, err := s.parseAndAnswer(queryStr)
	if err != nil {
		return &models.MCPResponse{
			Success: false,
			Error:   err.Error(),
			Metadata: models.Metadata{
				Timestamp: startTime.Format(time.RFC3339),
				Duration:  time.Since(startTime).String(),
			},
		}, nil
	}

	return &models.MCPResponse{
		Success: true,
		Data:    result,
		Metadata: models.Metadata{
			Timestamp: startTime.Format(time.RFC3339),
			Duration:  time.Since(startTime).String(),
		},
	}, nil
}

// parseAndAnswer parses the query and returns an appropriate response
func (s *SoccerServer) parseAndAnswer(queryStr string) (interface{}, error) {
	queryLower := stringLower(queryStr)

	// Match queries
	if containsAny(queryLower, []string{"match", "game", "score", "result", "vs", "versus", "vs.", "fla-flu", "derby"}) {
		if containsAny(queryLower, []string{"flamengo", "fluminense"}) {
			return s.answerTeamMatchQuery(queryStr, "Flamengo", "Fluminense")
		}
		if containsAny(queryLower, []string{"palmeiras", "santos"}) {
			return s.answerTeamMatchQuery(queryStr, "Palmeiras", "Santos")
		}
		if containsAny(queryLower, []string{"corinthians", "santos"}) {
			return s.answerTeamMatchQuery(queryStr, "Corinthians", "Santos")
		}
		return s.answerMatchQuery(queryStr)
	}

	// Player queries
	if containsAny(queryLower, []string{"player", "fifa", "neymar", "cr7", "messi", "alisson", "casemiro"}) {
		return s.answerPlayerQuery(queryStr)
	}

	// Team queries
	if containsAny(queryLower, []string{"team", "record", "stats", "statistics", "corinthians", "palmeiras", "flamengo", "santos"}) {
		return s.answerTeamQuery(queryStr)
	}

	// Competition queries
	if containsAny(queryLower, []string{"competition", "champion", "winner", "standings", "league", "bra", "brasileirão", "copa", "libertadores"}) {
		return s.answerCompetitionQuery(queryStr)
	}

	// Statistical queries
	if containsAny(queryLower, []string{"average", "total", "most", "best", "record", "biggest", "win", "score"}) {
		return s.answerStatisticalQuery(queryStr)
	}

	return s.answerGeneralQuery(queryStr)
}

// answerMatchQuery handles general match queries
func (s *SoccerServer) answerMatchQuery(queryStr string) (interface{}, error) {
	// Try to extract team names
	teams := extractTeams(queryStr)
	if len(teams) >= 2 {
		return s.answerTeamMatchQuery(queryStr, teams[0], teams[1])
	}

	// Try to extract season
	season := extractSeason(queryStr)
	if season > 0 {
		return s.answerSeasonQuery(queryStr, season)
	}

	// Generic match search
	matches, err := s.matchQuery.FindMatchesByTeam("", 0, "", 10)
	if err != nil {
		return nil, err
	}

	return s.formatMatchesResult(matches), nil
}

// answerTeamMatchQuery answers queries about matches between two teams
func (s *SoccerServer) answerTeamMatchQuery(queryStr, team1, team2 string) (interface{}, error) {
	h2h, err := s.matchQuery.GetHeadToHead(team1, team2)
	if err != nil {
		return nil, err
	}

	return s.formatHeadToHeadResult(h2h), nil
}

// answerSeasonQuery answers queries about a specific season
func (s *SoccerServer) answerSeasonQuery(queryStr string, season int) (interface{}, error) {
	// Find matches in the specified season
	matches, err := s.matchQuery.FindMatchesByDateRange(
		time.Date(season, 1, 1, 0, 0, 0, 0, time.UTC),
		time.Date(season+1, 1, 1, 0, 0, 0, 0, time.UTC),
		0,
	)
	if err != nil {
		return nil, err
	}

	return s.formatMatchesResult(matches), nil
}

// answerPlayerQuery handles player-related queries
func (s *SoccerServer) answerPlayerQuery(queryStr string) (interface{}, error) {
	queryLower := stringLower(queryStr)

	// Check for specific players
	if contains(queryLower, "neymar") {
		players, err := s.playerQuery.FindPlayersByName("Neymar", 5)
		if err != nil {
			return nil, err
		}
		return s.formatPlayersResult(players), nil
	}

	if contains(queryLower, "casemiro") {
		players, err := s.playerQuery.FindPlayersByName("Casemiro", 5)
		if err != nil {
			return nil, err
		}
		return s.formatPlayersResult(players), nil
	}

	if contains(queryLower, "aliss") {
		players, err := s.playerQuery.FindPlayersByName("Alisson", 5)
		if err != nil {
			return nil, err
		}
		return s.formatPlayersResult(players), nil
	}

	// Check for Brazilian players
	if contains(queryLower, "brazilian") {
		players, err := s.playerQuery.FindTopBrazilianPlayers(10)
		if err != nil {
			return nil, err
		}
		return s.formatPlayersResult(players), nil
	}

	// Check for club players
	if contains(queryLower, "flamengo") {
		players, err := s.playerQuery.FindPlayersByClub("Flamengo", 10)
		if err != nil {
			return nil, err
		}
		return s.formatPlayersResult(players), nil
	}

	if contains(queryLower, "palmeiras") {
		players, err := s.playerQuery.FindPlayersByClub("Palmeiras", 10)
		if err != nil {
			return nil, err
		}
		return s.formatPlayersResult(players), nil
	}

	if contains(queryLower, "corinthians") {
		players, err := s.playerQuery.FindPlayersByClub("Corinthians", 10)
		if err != nil {
			return nil, err
		}
		return s.formatPlayersResult(players), nil
	}

	return nil, fmt.Errorf("could not understand player query")
}

// answerTeamQuery handles team-related queries
func (s *SoccerServer) answerTeamQuery(queryStr string) (interface{}, error) {
	queryLower := stringLower(queryStr)
	season := extractSeason(queryStr)

	// Check for specific teams
	if contains(queryLower, "corinthians") {
		return s.answerTeamStats("Corinthians", season)
	}

	if contains(queryLower, "palmeiras") {
		return s.answerTeamStats("Palmeiras", season)
	}

	if contains(queryLower, "flamengo") {
		return s.answerTeamStats("Flamengo", season)
	}

	if contains(queryLower, "santos") {
		return s.answerTeamStats("Santos", season)
	}

	if contains(queryLower, "grêmio") || contains(queryLower, "gremio") {
		return s.answerTeamStats("Grêmio", season)
	}

	return nil, fmt.Errorf("could not understand team query")
}

// answerTeamStats answers stats for a specific team
func (s *SoccerServer) answerTeamStats(team string, season int) (interface{}, error) {
	if season > 0 {
		stats, err := s.matchQuery.GetTeamStats(team, season)
		if err != nil {
			return nil, err
		}
		return s.formatTeamStatsResult(stats), nil
	}

	// Get stats for all seasons
	allStats := &models.TeamStats{TeamName: team}
	seasons := []int{2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015}

	for _, se := range seasons {
		stats, err := s.matchQuery.GetTeamStats(team, se)
		if err == nil {
			allStats.Matches += stats.Matches
			allStats.Wins += stats.Wins
			allStats.Draws += stats.Draws
			allStats.Losses += stats.Losses
			allStats.GoalsFor += stats.GoalsFor
			allStats.GoalsAgainst += stats.GoalsAgainst
		}
	}

	allStats.GoalDiff = allStats.GoalsFor - allStats.GoalsAgainst
	allStats.Points = allStats.Wins*3 + allStats.Draws

	return s.formatTeamStatsResult(allStats), nil
}

// answerCompetitionQuery handles competition-related queries
func (s *SoccerServer) answerCompetitionQuery(queryStr string) (interface{}, error) {
	queryLower := stringLower(queryStr)
	season := extractSeason(queryStr)

	// Check for Brasileirão
	if contains(queryLower, "brasileirão") || contains(queryLower, "brasileirao") || contains(queryLower, "brasileiro") {
		if contains(queryLower, "champion") || contains(queryLower, "winner") {
			champion, err := s.compQuery.GetChampion("Brasileirão", season)
			if err != nil {
				return nil, err
			}
			return s.formatTeamStatsResult(champion), nil
		}

		if contains(queryLower, "relegat") {
			relegated, err := s.compQuery.GetRelegatedTeams(season)
			if err != nil {
				return nil, err
			}
			return s.formatBestAwayRecordsResult(relegated), nil
		}

		standings, err := s.compQuery.GetStandings("Brasileirão", season)
		if err != nil {
			return nil, err
		}
		return s.formatStandingsResult(standings, "Brasileirão", season), nil
	}

	// Check for Copa do Brasil
	if contains(queryLower, "copa do brasil") || contains(queryLower, "copa-brasil") {
		standings, err := s.compQuery.GetStandings("Copa do Brasil", season)
		if err != nil {
			return nil, err
		}
		return s.formatStandingsResult(standings, "Copa do Brasil", season), nil
	}

	// Check for Libertadores
	if contains(queryLower, "libertadores") {
		standings, err := s.compQuery.GetStandings("Libertadores", season)
		if err != nil {
			return nil, err
		}
		return s.formatStandingsResult(standings, "Libertadores", season), nil
	}

	return nil, fmt.Errorf("could not understand competition query")
}

// answerStatisticalQuery handles statistical queries
func (s *SoccerServer) answerStatisticalQuery(queryStr string) (interface{}, error) {
	queryLower := stringLower(queryStr)

	// Average goals per match
	if contains(queryLower, "average goals") || contains(queryLower, "goals per match") {
		avg, count, err := s.statQuery.GetAverageGoalsPerMatch(0)
		if err != nil {
			return nil, err
		}
		return map[string]interface{}{
			"average_goals_per_match": fmt.Sprintf("%.2f", avg),
			"match_count":             count,
		}, nil
	}

	// Home win rate
	if contains(queryLower, "home win") || contains(queryLower, "home record") {
		rate, count, err := s.statQuery.GetHomeWinRate(0)
		if err != nil {
			return nil, err
		}
		return map[string]interface{}{
			"home_win_rate": fmt.Sprintf("%.1f%%", rate),
			"match_count":   count,
		}, nil
	}

	// Biggest wins
	if contains(queryLower, "biggest wins") || contains(queryLower, "biggest victories") {
		wins, err := s.statQuery.GetBiggestWins(10)
		if err != nil {
			return nil, err
		}
		return s.formatBiggestWinsResult(wins), nil
	}

	// Top winners
	if contains(queryLower, "top winners") || contains(queryLower, "most wins") {
		wins, err := s.statQuery.GetTopWinners(10)
		if err != nil {
			return nil, err
		}
		return s.formatBestAwayRecordsResult(wins), nil
	}

	// Best away record
	if contains(queryLower, "best away") || contains(queryLower, "away record") {
		records, err := s.statQuery.GetBestAwayRecords(10)
		if err != nil {
			return nil, err
		}
		return s.formatBestAwayRecordsResult(records), nil
	}

	return nil, fmt.Errorf("could not understand statistical query")
}

// answerGeneralQuery handles general queries
func (s *SoccerServer) answerGeneralQuery(queryStr string) (interface{}, error) {
	return map[string]interface{}{
		"message": "I can answer questions about Brazilian soccer matches, players, teams, and competitions.",
		"examples": []string{
			"Show me Flamengo vs Fluminense matches",
			"What is Palmeiras' record in 2023?",
			"Who won the 2019 Brasileirão?",
			"Find all Brazilian players in the dataset",
			"What's the average goals per match?",
		},
	}, nil
}

// formatMatchList formats a list of matches for display
func formatMatchList(matches []models.Match, limit int) string {
	if len(matches) == 0 {
		return "No matches found"
	}

	var result string
	result += fmt.Sprintf("Found %d matches:\n\n", len(matches))

	for i, match := range matches {
		if i >= limit {
			result += fmt.Sprintf("... and %d more matches", len(matches)-i)
			break
		}
		result += fmt.Sprintf("%d. %s vs %s (%d-%d) - %s (%d)\n",
			i+1, match.HomeTeam, match.AwayTeam,
			match.HomeGoals, match.AwayGoals,
			match.Tournament, match.Season)
	}

	return strings.TrimSpace(result)
}

// formatHeadToHead formats head-to-head record for display
func formatHeadToHead(h2h *models.HeadToHead) string {
	if h2h == nil {
		return "No head-to-head data found"
	}

	result := fmt.Sprintf("Head-to-Head Record:\n")
	result += fmt.Sprintf("%s vs %s\n", h2h.Team1, h2h.Team2)
	result += fmt.Sprintf("Total Matches: %d\n", len(h2h.Matches))
	result += fmt.Sprintf("%s Wins: %d\n", h2h.Team1, h2h.Team1Wins)
	result += fmt.Sprintf("%s Wins: %d\n", h2h.Team2, h2h.Team2Wins)
	result += fmt.Sprintf("Draws: %d\n", h2h.Draws)

	return strings.TrimSpace(result)
}

// formatTeamStats formats team statistics for display
func formatTeamStats(stats *models.TeamStats) string {
	if stats == nil {
		return "No stats found"
	}

	result := fmt.Sprintf("%s Statistics:\n", stats.TeamName)
	result += fmt.Sprintf("Matches: %d\n", stats.Matches)
	result += fmt.Sprintf("Wins: %d\n", stats.Wins)
	result += fmt.Sprintf("Draws: %d\n", stats.Draws)
	result += fmt.Sprintf("Losses: %d\n", stats.Losses)
	result += fmt.Sprintf("Goals For: %d\n", stats.GoalsFor)
	result += fmt.Sprintf("Goals Against: %d\n", stats.GoalsAgainst)
	result += fmt.Sprintf("Points: %d\n", stats.Points)

	return strings.TrimSpace(result)
}

// formatPlayerList formats a list of players for display
func formatPlayerList(players []models.Player) string {
	if len(players) == 0 {
		return "No players found"
	}

	var result string
	result += fmt.Sprintf("Found %d players:\n\n", len(players))

	for i, player := range players {
		result += fmt.Sprintf("%d. %s (%s) - %s, Overall: %d\n",
			i+1, player.Name, player.Position, player.Club, player.Overall)
	}

	return strings.TrimSpace(result)
}

// formatTopBrazilianPlayers formats top Brazilian players for display
func formatTopBrazilianPlayers(players []models.Player) string {
	if len(players) == 0 {
		return "No Brazilian players found"
	}

	var result string
	result += fmt.Sprintf("Top Brazilian Players:\n\n")

	for i, player := range players {
		result += fmt.Sprintf("%d. %s - Overall: %d, Position: %s, Club: %s\n",
			i+1, player.Name, player.Overall, player.Position, player.Club)
	}

	return strings.TrimSpace(result)
}

// formatClubPlayers formats players for a specific club
func formatClubPlayers(club string, players []models.Player) string {
	if len(players) == 0 {
		return fmt.Sprintf("No players found for %s", club)
	}

	var result string
	result += fmt.Sprintf("Players for %s:\n\n", club)

	for i, player := range players {
		result += fmt.Sprintf("%d. %s - %s, Overall: %d\n",
			i+1, player.Name, player.Position, player.Overall)
	}

	return strings.TrimSpace(result)
}

// formatStandings formats league standings for display
func formatStandings(standings []models.TeamStats, competition string, season int) string {
	if len(standings) == 0 {
		return "No standings found"
	}

	var result string
	result += fmt.Sprintf("%s %d Standings:\n\n", competition, season)

	for i, team := range standings {
		result += fmt.Sprintf("%d. %s - %d pts (%dW-%dD-%dL)\n",
			i+1, team.TeamName, team.Points, team.Wins, team.Draws, team.Losses)
	}

	return strings.TrimSpace(result)
}

// formatChampion formats the champion information
func formatChampion(stats *models.TeamStats, season int) string {
	if stats == nil {
		return "No champion found"
	}

	return fmt.Sprintf("%d Champion: %s (%d pts)",
		season, stats.TeamName, stats.Points)
}

// formatRelegatedTeams formats relegated teams information
func formatRelegatedTeams(teams []models.TeamStats) string {
	if len(teams) == 0 {
		return "No relegated teams found"
	}

	var result string
	result += "Relegated Teams:\n\n"

	for i, team := range teams {
		result += fmt.Sprintf("%d. %s (%d pts)\n",
			i+1, team.TeamName, team.Points)
	}

	return strings.TrimSpace(result)
}

// formatBiggestWins formats biggest wins for display
func formatBiggestWins(matches []models.Match) string {
	if len(matches) == 0 {
		return "No big wins found"
	}

	var result string
	result += "Biggest Wins:\n\n"

	for i, match := range matches {
		if i >= 10 {
			break
		}
		result += fmt.Sprintf("%d. %s %d-%d %s (Goal Diff: %d)\n",
			i+1, match.HomeTeam, match.HomeGoals, match.AwayGoals,
			match.AwayTeam, match.GoalDiff)
	}

	return strings.TrimSpace(result)
}

// formatTopWinners formats top winners for display
func formatTopWinners(teams []models.TeamStats) string {
	if len(teams) == 0 {
		return "No winners found"
	}

	var result string
	result += "Top Winners:\n\n"

	for i, team := range teams {
		result += fmt.Sprintf("%d. %s - %d wins\n",
			i+1, team.TeamName, team.Wins)
	}

	return strings.TrimSpace(result)
}

// formatBestAwayRecords formats best away records for display
func formatBestAwayRecords(records []models.TeamStats) string {
	if len(records) == 0 {
		return "No away records found"
	}

	var result string
	result += "Best Away Records:\n\n"

	for i, team := range records {
		result += fmt.Sprintf("%d. %s - %d pts (%dW-%dD-%dL)\n",
			i+1, team.TeamName, team.Points, team.AwayWins, team.AwayDraws, team.AwayLosses)
	}

	return strings.TrimSpace(result)
}

// formatStatisticalResult formats statistical results
func formatStatisticalResult(metric string, value string) string {
	return fmt.Sprintf("%s: %s", metric, value)
}

// formatMatchesResult formats a list of matches for display
func (s *SoccerServer) formatMatchesResult(matches []models.Match) interface{} {
	if len(matches) == 0 {
		return map[string]interface{}{"message": "No matches found", "count": 0}
	}

	result := map[string]interface{}{
		"count":       len(matches),
		"matches":     make([]interface{}, 0, len(matches)),
	}

	for _, match := range matches {
		matchData := map[string]interface{}{
			"id":          match.ID,
			"date":        match.Date.Format("2006-01-02"),
			"home_team":   match.HomeTeam,
			"away_team":   match.AwayTeam,
			"home_goals":  match.HomeGoals,
			"away_goals":  match.AwayGoals,
			"tournament":  match.Tournament,
			"season":      match.Season,
			"round":       match.Round,
			"competition": match.Tournament,
		}
		result["matches"] = append(result["matches"].([]interface{}), matchData)
	}

	return result
}

// formatTeamStatsResult formats team statistics for display
func (s *SoccerServer) formatTeamStatsResult(stats *models.TeamStats) interface{} {
	if stats == nil {
		return map[string]interface{}{"message": "No stats found"}
	}

	result := map[string]interface{}{
		"team":          stats.TeamName,
		"matches":       stats.Matches,
		"wins":          stats.Wins,
		"draws":         stats.Draws,
		"losses":        stats.Losses,
		"goals_for":     stats.GoalsFor,
		"goals_against": stats.GoalsAgainst,
		"goal_diff":     stats.GoalDiff,
		"points":        stats.Points,
	}

	if stats.Matches > 0 {
		result["win_rate"] = fmt.Sprintf("%.1f%%", float64(stats.Wins)/float64(stats.Matches)*100)
	}

	return result
}

// formatHeadToHeadResult formats head-to-head record for display
func (s *SoccerServer) formatHeadToHeadResult(h2h *models.HeadToHead) interface{} {
	if h2h == nil {
		return map[string]interface{}{"message": "No head-to-head data found"}
	}

	result := map[string]interface{}{
		"team1":         h2h.Team1,
		"team2":         h2h.Team2,
		"total_matches": len(h2h.Matches),
		"team1_wins":    h2h.Team1Wins,
		"team2_wins":    h2h.Team2Wins,
		"draws":         h2h.Draws,
		"team1_goals":   h2h.Team1Goals,
		"team2_goals":   h2h.Team2Goals,
	}

	if len(h2h.Matches) > 0 {
		recent := make([]interface{}, 0, len(h2h.Matches))
		for i := 0; i < len(h2h.Matches) && i < 5; i++ {
			match := h2h.Matches[i]
			recent = append(recent, map[string]interface{}{
				"date":       match.Date.Format("2006-01-02"),
				"home_team":  match.HomeTeam,
				"away_team":  match.AwayTeam,
				"home_goals": match.HomeGoals,
				"away_goals": match.AwayGoals,
			})
		}
		result["recent_matches"] = recent
	}

	return result
}

// formatPlayersResult formats a list of players for display
func (s *SoccerServer) formatPlayersResult(players []models.Player) interface{} {
	if len(players) == 0 {
		return map[string]interface{}{"message": "No players found", "count": 0}
	}

	result := map[string]interface{}{
		"count":   len(players),
		"players": make([]interface{}, 0, len(players)),
	}

	for _, player := range players {
		playerData := map[string]interface{}{
			"id":            player.ID,
			"name":          player.Name,
			"age":           player.Age,
			"nationality":   player.Nationality,
			"overall":       player.Overall,
			"potential":     player.Potential,
			"club":          player.Club,
			"position":      player.Position,
		}
		result["players"] = append(result["players"].([]interface{}), playerData)
	}

	return result
}

// formatStandingsResult formats league standings for display
func (s *SoccerServer) formatStandingsResult(standings []models.TeamStats, competition string, season int) interface{} {
	if len(standings) == 0 {
		return map[string]interface{}{"message": "No standings found"}
	}

	result := map[string]interface{}{
		"competition": competition,
		"season":      season,
		"count":       len(standings),
		"standings":   make([]interface{}, 0, len(standings)),
	}

	for i, team := range standings {
		teamData := map[string]interface{}{
			"rank":          i + 1,
			"team":          team.TeamName,
			"matches":       team.Matches,
			"wins":          team.Wins,
			"draws":         team.Draws,
			"losses":        team.Losses,
			"goals_for":     team.GoalsFor,
			"goals_against": team.GoalsAgainst,
			"goal_diff":     team.GoalDiff,
			"points":        team.Points,
		}
		result["standings"] = append(result["standings"].([]interface{}), teamData)
	}

	return result
}

// formatBiggestWinsResult formats biggest wins for display
func (s *SoccerServer) formatBiggestWinsResult(wins []models.Match) interface{} {
	if len(wins) == 0 {
		return map[string]interface{}{"message": "No big wins found"}
	}

	result := map[string]interface{}{
		"count":         len(wins),
		"biggest_wins":  make([]interface{}, 0, len(wins)),
	}

	for i, match := range wins {
		if i >= 10 {
			break
		}
		winData := map[string]interface{}{
			"date":        match.Date.Format("2006-01-02"),
			"home_team":   match.HomeTeam,
			"away_team":   match.AwayTeam,
			"home_goals":  match.HomeGoals,
			"away_goals":  match.AwayGoals,
			"goal_diff":   match.GoalDiff,
			"tournament":  match.Tournament,
		}
		result["biggest_wins"] = append(result["biggest_wins"].([]interface{}), winData)
	}

	return result
}

// formatBestAwayRecordsResult formats best away records for display
func (s *SoccerServer) formatBestAwayRecordsResult(records []models.TeamStats) interface{} {
	if len(records) == 0 {
		return map[string]interface{}{"message": "No away records found"}
	}

	result := map[string]interface{}{
		"count":             len(records),
		"best_away_records": make([]interface{}, 0, len(records)),
	}

	for i, team := range records {
		if i >= 10 {
			break
		}
		recordData := map[string]interface{}{
			"team":          team.TeamName,
			"away_matches":  team.AwayMatches,
			"away_wins":     team.AwayWins,
			"away_draws":    team.AwayDraws,
			"away_losses":   team.AwayLosses,
			"away_points":   team.Points,
		}
		result["best_away_records"] = append(result["best_away_records"].([]interface{}), recordData)
	}

	return result
}

// Helper functions
func stringLower(s string) string {
	result := ""
	for _, r := range s {
		if r >= 'A' && r <= 'Z' {
			result += string(r + ('a' - 'A'))
		} else {
			result += string(r)
		}
	}
	return result
}

func contains(s, substr string) bool {
	return strings.Contains(stringLower(s), stringLower(substr))
}

func containsAny(s string, substrs []string) bool {
	for _, substr := range substrs {
		if contains(s, substr) {
			return true
		}
	}
	return false
}

func normalizeTeamName(name string) string {
	if name == "" {
		return ""
	}
	return strings.ToLower(strings.TrimSpace(name))
}

func extractTeams(query string) []string {
	teams := []string{
		"Flamengo", "Fluminense", "Palmeiras", "Santos", "Corinthians",
		"São Paulo", "Grêmio", "Internacional", "Botafogo", "Vasco da Gama",
		"Atlético Mineiro", "Athletico Paranaense", "Bahia", "Fortaleza",
		"Cruzeiro", "Vitória", "Sport", "Santa Cruz", "Bragantino",
	}

	var foundTeams []string
	for _, team := range teams {
		if contains(query, team) {
			foundTeams = append(foundTeams, team)
		}
	}
	return foundTeams
}

func extractSeason(query string) int {
	seasons := []int{2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012, 2011, 2010}
	queryLower := stringLower(query)

	for _, season := range seasons {
		if contains(queryLower, fmt.Sprintf("%d", season)) {
			return season
		}
	}
	return 0
}
