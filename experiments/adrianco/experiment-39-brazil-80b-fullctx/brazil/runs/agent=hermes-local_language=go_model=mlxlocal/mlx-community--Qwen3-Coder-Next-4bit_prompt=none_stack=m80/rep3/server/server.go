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
	store      *models.DataStore
	matchQuery *query.MatchQuery
	playerQuery *query.PlayerQuery
	compQuery  *query.CompetitionQuery
	statQuery  *query.StatisticalQuery
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

// Query handles natural language queries
func (s *SoccerServer) Query(queryStr string) (*models.MCPResponse, error) {
	startTime := time.Now()

	// Try to parse and answer the query
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

	return formatMatchList(matches, 10), nil
}

// answerTeamMatchQuery answers queries about matches between two teams
func (s *SoccerServer) answerTeamMatchQuery(queryStr, team1, team2 string) (interface{}, error) {
	h2h, err := s.matchQuery.GetHeadToHead(team1, team2)
	if err != nil {
		return nil, err
	}

	return formatHeadToHead(h2h), nil
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

	return formatMatchList(matches, 0), nil
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
		return formatPlayerList(players), nil
	}

	if contains(queryLower, "casemiro") {
		players, err := s.playerQuery.FindPlayersByName("Casemiro", 5)
		if err != nil {
			return nil, err
		}
		return formatPlayerList(players), nil
	}

	if contains(queryLower, "aliss") {
		players, err := s.playerQuery.FindPlayersByName("Alisson", 5)
		if err != nil {
			return nil, err
		}
		return formatPlayerList(players), nil
	}

	// Check for Brazilian players
	if contains(queryLower, "brazilian") {
		players, err := s.playerQuery.FindTopBrazilianPlayers(10)
		if err != nil {
			return nil, err
		}
		return formatTopBrazilianPlayers(players), nil
	}

	// Check for club players
	if contains(queryLower, "flamengo") {
		players, err := s.playerQuery.FindPlayersByClub("Flamengo", 10)
		if err != nil {
			return nil, err
		}
		return formatClubPlayers("Flamengo", players), nil
	}

	if contains(queryLower, "palmeiras") {
		players, err := s.playerQuery.FindPlayersByClub("Palmeiras", 10)
		if err != nil {
			return nil, err
		}
		return formatClubPlayers("Palmeiras", players), nil
	}

	if contains(queryLower, "corinthians") {
		players, err := s.playerQuery.FindPlayersByClub("Corinthians", 10)
		if err != nil {
			return nil, err
		}
		return formatClubPlayers("Corinthians", players), nil
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
		return formatTeamStats(stats), nil
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

	return formatTeamStats(allStats), nil
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
			return formatChampion(champion, season), nil
		}

		if contains(queryLower, "relegat") {
			relegated, err := s.compQuery.GetRelegatedTeams(season)
			if err != nil {
				return nil, err
			}
			return formatRelegatedTeams(relegated), nil
		}

		standings, err := s.compQuery.GetStandings("Brasileirão", season)
		if err != nil {
			return nil, err
		}
		return formatStandings(standings, "Brasileirão", season), nil
	}

	// Check for Copa do Brasil
	if contains(queryLower, "copa do brasil") || contains(queryLower, "copa-brasil") {
		standings, err := s.compQuery.GetStandings("Copa do Brasil", season)
		if err != nil {
			return nil, err
		}
		return formatStandings(standings, "Copa do Brasil", season), nil
	}

	// Check for Libertadores
	if contains(queryLower, "libertadores") {
		standings, err := s.compQuery.GetStandings("Libertadores", season)
		if err != nil {
			return nil, err
		}
		return formatStandings(standings, "Libertadores", season), nil
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
		return formatStatisticalResult("Average goals per match", fmt.Sprintf("%.2f (based on %d matches)", avg, count)), nil
	}

	// Home win rate
	if contains(queryLower, "home win") || contains(queryLower, "home record") {
		rate, count, err := s.statQuery.GetHomeWinRate(0)
		if err != nil {
			return nil, err
		}
		return formatStatisticalResult("Home win rate", fmt.Sprintf("%.1f%% (based on %d matches)", rate, count)), nil
	}

	// Biggest wins
	if contains(queryLower, "biggest wins") || contains(queryLower, "biggest victories") {
		wins, err := s.statQuery.GetBiggestWins(10)
		if err != nil {
			return nil, err
		}
		return formatBiggestWins(wins), nil
	}

	// Top winners
	if contains(queryLower, "top winners") || contains(queryLower, "most wins") {
		wins, err := s.statQuery.GetTopWinners(10)
		if err != nil {
			return nil, err
		}
		return formatTopWinners(wins), nil
	}

	// Best away record
	if contains(queryLower, "best away") || contains(queryLower, "away record") {
		records, err := s.statQuery.GetBestAwayRecords(10)
		if err != nil {
			return nil, err
		}
		return formatBestAwayRecords(records), nil
	}

	return nil, fmt.Errorf("could not understand statistical query")
}

// answerGeneralQuery handles general queries
func (s *SoccerServer) answerGeneralQuery(queryStr string) (interface{}, error) {
	return map[string]interface{}{
		"message":   "I can answer questions about Brazilian soccer matches, players, teams, and competitions.",
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
		return "No matches found."
	}

	var result string
	if limit > 0 && len(matches) > limit {
		matches = matches[:limit]
		result = fmt.Sprintf("Found %d matches (showing %d):\n\n", len(matches), limit)
	} else {
		result = fmt.Sprintf("Found %d matches:\n\n", len(matches))
	}

	for i, match := range matches {
		result += fmt.Sprintf("%d. %s: %s vs %s\n", i+1, match.Date.Format("2006-01-02"), match.HomeTeam, match.AwayTeam)
		result += fmt.Sprintf("   Score: %d-%d | Competition: %s\n", match.HomeGoals, match.AwayGoals, match.Tournament)
		if match.Round > 0 {
			result += fmt.Sprintf("   Round: %d\n", match.Round)
		}
	}
	return result
}

// formatHeadToHead formats head-to-head record for display
func formatHeadToHead(h2h *models.HeadToHead) string {
	result := fmt.Sprintf("%s vs %s Head-to-Head:\n", h2h.Team1, h2h.Team2)
	result += fmt.Sprintf("Total Matches: %d\n", len(h2h.Matches))
	result += fmt.Sprintf("%s Wins: %d\n", h2h.Team1, h2h.Team1Wins)
	result += fmt.Sprintf("%s Wins: %d\n", h2h.Team2, h2h.Team2Wins)
	result += fmt.Sprintf("Draws: %d\n", h2h.Draws)
	result += fmt.Sprintf("%s Goals: %d\n", h2h.Team1, h2h.Team1Goals)
	result += fmt.Sprintf("%s Goals: %d\n", h2h.Team2, h2h.Team2Goals)

	if len(h2h.Matches) > 0 {
		result += "\nRecent Matches:\n"
		for i := 0; i < len(h2h.Matches) && i < 5; i++ {
			match := h2h.Matches[i]
			result += fmt.Sprintf("- %s: %s %d-%d %s\n",
				match.Date.Format("2006-01-02"),
				match.HomeTeam, match.HomeGoals, match.AwayGoals, match.AwayTeam)
		}
	}

	return result
}

// formatTeamStats formats team statistics for display
func formatTeamStats(stats *models.TeamStats) string {
	result := fmt.Sprintf("Team: %s\n", stats.TeamName)
	result += fmt.Sprintf("Total Matches: %d\n", stats.Matches)
	result += fmt.Sprintf("Wins: %d | Draws: %d | Losses: %d\n", stats.Wins, stats.Draws, stats.Losses)
	result += fmt.Sprintf("Goals For: %d | Goals Against: %d | Goal Diff: %d\n",
		stats.GoalsFor, stats.GoalsAgainst, stats.GoalDiff)
	result += fmt.Sprintf("Points: %d\n", stats.Points)

	if stats.Matches > 0 {
		winRate := float64(stats.Wins) / float64(stats.Matches) * 100
		result += fmt.Sprintf("Win Rate: %.1f%%\n", winRate)
	}

	result += fmt.Sprintf("\nHome Record: %dW-%dD-%dL\n", stats.HomeWins, stats.HomeDraws, stats.HomeLosses)
	result += fmt.Sprintf("Away Record: %dW-%dD-%dL\n", stats.AwayWins, stats.AwayDraws, stats.AwayLosses)

	return result
}

// formatPlayerList formats a list of players for display
func formatPlayerList(players []models.Player) string {
	if len(players) == 0 {
		return "No players found."
	}

	var result string
	result = fmt.Sprintf("Found %d players:\n\n", len(players))

	for i, player := range players {
		result += fmt.Sprintf("%d. %s - %s (%d)\n", i+1, player.Name, player.Position, player.Overall)
		result += fmt.Sprintf("   Age: %d | Club: %s\n", player.Age, player.Club)
		result += fmt.Sprintf("   Potential: %d\n", player.Potential)
	}
	return result
}

// formatTopBrazilianPlayers formats top Brazilian players for display
func formatTopBrazilianPlayers(players []models.Player) string {
	result := "Top Brazilian Players:\n\n"
	for i, player := range players {
		if i >= 10 {
			break
		}
		result += fmt.Sprintf("%d. %s - Overall: %d, Position: %s, Club: %s\n",
			i+1, player.Name, player.Overall, player.Position, player.Club)
	}
	return result
}

// formatClubPlayers formats players at a specific club
func formatClubPlayers(club string, players []models.Player) string {
	result := fmt.Sprintf("Players at %s (%d):\n\n", club, len(players))
	for i, player := range players {
		if i >= 10 {
			break
		}
		result += fmt.Sprintf("%d. %s - %s (Overall: %d)\n",
			i+1, player.Name, player.Position, player.Overall)
	}
	return result
}

// formatStandings formats league standings for display
func formatStandings(standings []models.TeamStats, competition string, season int) string {
	result := fmt.Sprintf("%s %d Standings:\n\n", competition, season)
	result += fmt.Sprintf("%-3s %-25s %3s %3s %3s %3s %4s %4s %4s\n",
		"#", "Team", "MP", "W", "D", "L", "GF", "GA", "GD")
	result += fmt.Sprintf("%s\n", stringRepeat("-", 70))

	for i, team := range standings {
		if i >= 20 {
			break
		}
		result += fmt.Sprintf("%-3d %-25s %3d %3d %3d %3d %4d %4d %4d\n",
			i+1, team.TeamName, team.Matches, team.Wins, team.Draws, team.Losses,
			team.GoalsFor, team.GoalsAgainst, team.GoalDiff)
	}
	return result
}

// formatChampion formats champion information
func formatChampion(stats *models.TeamStats, season int) string {
	if stats == nil {
		return "No champion found."
	}
	return fmt.Sprintf("%s won the %d season with %d points!", stats.TeamName, season, stats.Points)
}

// formatRelegatedTeams formats relegated teams
func formatRelegatedTeams(teams []models.TeamStats) string {
	result := "Relegated Teams:\n\n"
	for i, team := range teams {
		result += fmt.Sprintf("%d. %s\n", i+1, team.TeamName)
	}
	return result
}

// formatBiggestWins formats biggest wins
func formatBiggestWins(wins []models.Match) string {
	result := "Biggest Victories:\n\n"
	for i, match := range wins {
		if i >= 10 {
			break
		}
		result += fmt.Sprintf("%d. %s: %s %d-%d %s (Goal Diff: %d)\n",
			i+1, match.Date.Format("2006-01-02"),
			match.HomeTeam, match.HomeGoals, match.AwayGoals, match.AwayTeam,
			match.GoalDiff)
	}
	return result
}

// formatTopWinners formats top winners
func formatTopWinners(wins []models.TeamStats) string {
	result := "Teams with Most Wins:\n\n"
	for i, team := range wins {
		if i >= 10 {
			break
		}
		result += fmt.Sprintf("%d. %s: %d wins\n", i+1, team.TeamName, team.Wins)
	}
	return result
}

// formatBestAwayRecords formats best away records
func formatBestAwayRecords(records []models.TeamStats) string {
	result := "Best Away Records:\n\n"
	for i, team := range records {
		if i >= 10 {
			break
		}
		result += fmt.Sprintf("%d. %s: %dW-%dD-%dL (%d pts)\n",
			i+1, team.TeamName, team.AwayWins, team.AwayDraws, team.AwayLosses, team.Points)
	}
	return result
}

// formatStatisticalResult formats a statistical result
func formatStatisticalResult(label, value string) string {
	return fmt.Sprintf("%s:\n%s", label, value)
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

func stringRepeat(s string, count int) string {
	result := ""
	for i := 0; i < count; i++ {
		result += s
	}
	return result
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
	// Look for year patterns like 2023, 2022, etc.
	seasons := []int{2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012, 2011, 2010}
	queryLower := stringLower(query)

	for _, season := range seasons {
		if contains(queryLower, fmt.Sprintf("%d", season)) {
			return season
		}
	}
	return 0
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
