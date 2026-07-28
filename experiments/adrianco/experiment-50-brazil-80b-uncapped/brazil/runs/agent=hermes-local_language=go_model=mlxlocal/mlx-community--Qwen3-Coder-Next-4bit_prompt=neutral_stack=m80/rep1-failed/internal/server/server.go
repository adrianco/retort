package server

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/models"
	"brazilian-soccer-mcp/internal/store"
)

// Server represents the MCP server
type Server struct {
	db *store.Database
}

// NewServer creates a new MCP server
func NewServer(db *store.Database) *Server {
	return &Server{db: db}
}

// QueryRequest represents a query from the MCP client
type QueryRequest struct {
	QueryType string                 `json:"query_type"`
	Params    map[string]interface{} `json:"params"`
}

// QueryResponse represents the response to a query
type QueryResponse struct {
	Success    bool                   `json:"success"`
	Message    string                 `json:"message"`
	Data       interface{}            `json:"data,omitempty"`
	Error      string                 `json:"error,omitempty"`
	Timestamp  string                 `json:"timestamp"`
	ProcessingTimeMs int            `json:"processing_time_ms,omitempty"`
}

// ExecuteQuery processes a query and returns a response
func (s *Server) ExecuteQuery(query string) *QueryResponse {
	startTime := time.Now()

	request, err := parseQuery(query)
	if err != nil {
		return &QueryResponse{
			Success: false,
			Error:   fmt.Sprintf("Failed to parse query: %v", err),
			Timestamp: time.Now().Format(time.RFC3339),
		}
	}

	response := s.handleQuery(request)
	response.Timestamp = time.Now().Format(time.RFC3339)
	response.ProcessingTimeMs = int(time.Since(startTime).Milliseconds())

	return response
}

// parseQuery parses a natural language query into a structured request
func parseQuery(query string) (*QueryRequest, error) {
	query = strings.TrimSpace(query)
	queryLower := strings.ToLower(query)

	request := &QueryRequest{
		Params: make(map[string]interface{}),
	}

	// Determine query type based on keywords
	if strings.Contains(queryLower, "head to head") || strings.Contains(queryLower, "h2h") {
		request.QueryType = "head_to_head"
	} else if strings.Contains(queryLower, "standings") || strings.Contains(queryLower, "table") ||
		strings.Contains(queryLower, "winner") || strings.Contains(queryLower, "champion") {
		request.QueryType = "standings"
	} else if strings.Contains(queryLower, "top scorer") || strings.Contains(queryLower, "best player") ||
		strings.Contains(queryLower, "highest rated") {
		request.QueryType = "top_scorers"
	} else if strings.Contains(queryLower, "brazilian player") || strings.Contains(queryLower, "brazilian players") {
		request.QueryType = "brazilian_players"
	} else if strings.Contains(queryLower, "player") && strings.Contains(queryLower, "club") {
		request.QueryType = "players_by_club"
	} else if strings.Contains(queryLower, "player") {
		request.QueryType = "player_search"
	} else if strings.Contains(queryLower, "biggest win") || strings.Contains(queryLower, "biggest victory") ||
		strings.Contains(queryLower, "largest margin") {
		request.QueryType = "big_wins"
	} else if strings.Contains(queryLower, "average goal") || strings.Contains(queryLower, "goals per match") {
		request.QueryType = "average_goals"
	} else if strings.Contains(queryLower, "home win") || strings.Contains(queryLower, "home record") {
		request.QueryType = "home_win_rate"
	} else if strings.Contains(queryLower, "team record") || strings.Contains(queryLower, "team stats") ||
		strings.Contains(queryLower, "team statistics") {
		request.QueryType = "team_stats"
	} else if strings.Contains(queryLower, "last time") || strings.Contains(queryLower, "most recent") ||
		strings.Contains(queryLower, "last match") {
		request.QueryType = "last_match"
	} else if strings.Contains(queryLower, "when did") || strings.Contains(queryLower, "match") ||
		strings.Contains(queryLower, "score") {
		request.QueryType = "match_search"
	} else if strings.Contains(queryLower, "compare") || strings.Contains(queryLower, "head to head") {
		request.QueryType = "compare_teams"
	} else if strings.Contains(queryLower, "team") {
		request.QueryType = "team_search"
	} else {
		request.QueryType = "general"
	}

	// Extract parameters from the query
	extractParams(request, query)

	return request, nil
}

// extractParams extracts parameters from the query
func extractParams(request *QueryRequest, query string) {
	queryLower := strings.ToLower(query)

	// Extract team names
	teamNames := []string{"flamengo", "fluminense", "palmeiras", "sao paulo", "corinthians",
		" santos", "grêmio", "gremio", "internacional", "vasco", "botafogo",
		"atletico", "são paulo", "santos", "fortaleza", "bahia", "bragantino",
		"coritiba", "cuiaba", "athletico paranaense", "cruzeiro", "juventude",
		"ponte preta", "figueirense", "avaí", "avai", "chapecoense", "sport",
		"nautico", "guarani", "américa", "america", "vila nova", "goiás", "goias"}

	teams := []string{}
	for _, team := range teamNames {
		if strings.Contains(queryLower, team) {
			teams = append(teams, team)
		}
	}
	if len(teams) > 0 {
		request.Params["teams"] = teams
	}

	// Extract season
	if strings.Contains(queryLower, "2023") || strings.Contains(queryLower, "2023") {
		request.Params["season"] = 2023
	} else if strings.Contains(queryLower, "2022") {
		request.Params["season"] = 2022
	} else if strings.Contains(queryLower, "2021") {
		request.Params["season"] = 2021
	} else if strings.Contains(queryLower, "2020") {
		request.Params["season"] = 2020
	} else if strings.Contains(queryLower, "2019") {
		request.Params["season"] = 2019
	} else if strings.Contains(queryLower, "2018") {
		request.Params["season"] = 2018
	} else if strings.Contains(queryLower, "2017") {
		request.Params["season"] = 2017
	} else if strings.Contains(queryLower, "2016") {
		request.Params["season"] = 2016
	} else if strings.Contains(queryLower, "2015") {
		request.Params["season"] = 2015
	} else if strings.Contains(queryLower, "2014") {
		request.Params["season"] = 2014
	} else if strings.Contains(queryLower, "2013") {
		request.Params["season"] = 2013
	} else if strings.Contains(queryLower, "2012") {
		request.Params["season"] = 2012
	}

	// Extract competition
	if strings.Contains(queryLower, "brasileirão") || strings.Contains(queryLower, "brasileirao") {
		request.Params["competition"] = "brasileirao"
	} else if strings.Contains(queryLower, "copa do brasil") || strings.Contains(queryLower, "copa do brasileiro") {
		request.Params["competition"] = "copa do brasil"
	} else if strings.Contains(queryLower, "libertadores") || strings.Contains(queryLower, "libertador") {
		request.Params["competition"] = "libertadores"
	} else if strings.Contains(queryLower, "série a") || strings.Contains(queryLower, "serie a") {
		request.Params["competition"] = "brasileirao"
	}

	// Extract player name
	if strings.Contains(queryLower, "neymar") {
		request.Params["player"] = "neymar"
	} else if strings.Contains(queryLower, "messi") {
		request.Params["player"] = "messi"
	} else if strings.Contains(queryLower, "ronaldo") || strings.Contains(queryLower, "cristiano") {
		request.Params["player"] = "cristiano ronaldo"
	} else if strings.Contains(queryLower, "neymar Jr") || strings.Contains(queryLower, "neymar jr") {
		request.Params["player"] = "neymar"
	}

	// Extract threshold for big wins
	if strings.Contains(queryLower, "5") {
		request.Params["threshold"] = 5
	} else if strings.Contains(queryLower, "6") {
		request.Params["threshold"] = 6
	} else if strings.Contains(queryLower, "4") {
		request.Params["threshold"] = 4
	}
}

// handleQuery handles the parsed query
func (s *Server) handleQuery(request *QueryRequest) *QueryResponse {
	switch request.QueryType {
	case "match_search":
		return s.handleMatchSearch(request)
	case "team_search":
		return s.handleTeamSearch(request)
	case "player_search":
		return s.handlePlayerSearch(request)
	case "team_stats":
		return s.handleTeamStats(request)
	case "head_to_head":
		return s.handleHeadToHead(request)
	case "standings":
		return s.handleStandings(request)
	case "top_scorers":
		return s.handleTopScorers(request)
	case "brazilian_players":
		return s.handleBrazilianPlayers(request)
	case "players_by_club":
		return s.handlePlayersByClub(request)
	case "big_wins":
		return s.handleBigWins(request)
	case "average_goals":
		return s.handleAverageGoals(request)
	case "home_win_rate":
		return s.handleHomeWinRate(request)
	case "compare_teams":
		return s.handleCompareTeams(request)
	case "last_match":
		return s.handleLastMatch(request)
	default:
		return &QueryResponse{
			Success: false,
			Error:   fmt.Sprintf("Unknown query type: %s", request.QueryType),
		}
	}
}

// handleMatchSearch handles match search queries
func (s *Server) handleMatchSearch(request *QueryRequest) *QueryResponse {
	teams, _ := request.Params["teams"].([]string)
	season, _ := request.Params["season"].(int)
	competition, _ := request.Params["competition"].(string)

	var matches []models.Match

	if len(teams) == 2 {
		// Search for matches between two teams
		matches = s.db.FindMatchesByTeams(teams[0], teams[1])
	} else if len(teams) == 1 {
		// Search for matches by a single team
		matches = s.db.FindMatchesByTeam(teams[0], season)
	} else if season > 0 {
		matches = s.db.FindMatchesBySeason(season)
	} else if competition != "" {
		matches = s.db.FindMatchesByCompetition(competition)
	} else {
		matches = s.db.FindMatchesByDateRange("", "")
	}

	if len(matches) == 0 {
		return &QueryResponse{
			Success: true,
			Message: "No matches found matching your criteria",
		}
	}

	// Limit results
	if len(matches) > 20 {
		matches = matches[:20]
	}

	// Format the response
	result := formatMatches(matches)
	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Found %d match(es)", len(matches)),
		Data:    result,
	}
}

// handleTeamSearch handles team search queries
func (s *Server) handleTeamSearch(request *QueryRequest) *QueryResponse {
	teams, _ := request.Params["teams"].([]string)
	season, _ := request.Params["season"].(int)

	if len(teams) == 0 {
		return &QueryResponse{
			Success: false,
			Error:   "Please specify a team",
		}
	}

	team := teams[0]
	stats := s.db.GetTeamStats(team, season)

	result := map[string]interface{}{
		"team":         stats.TeamName,
		"season":       season,
		"matches":      stats.Matches,
		"wins":         stats.Wins,
		"draws":        stats.Draws,
		"losses":       stats.Losses,
		"goals_for":    stats.GoalsFor,
		"goals_against": stats.GoalsAgainst,
		"points":       stats.Points,
		"win_rate":     fmt.Sprintf("%.1f%%", stats.WinRate),
		"home_record": map[string]interface{}{
			"matches":   stats.HomeMatches,
			"wins":      stats.HomeWins,
			"draws":     stats.HomeDraws,
			"losses":    stats.HomeLosses,
		},
		"away_record": map[string]interface{}{
			"matches":   stats.AwayMatches,
			"wins":      stats.AwayWins,
			"draws":     stats.AwayDraws,
			"losses":    stats.AwayLosses,
		},
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Statistics for %s", team),
		Data:    result,
	}
}

// handlePlayerSearch handles player search queries
func (s *Server) handlePlayerSearch(request *QueryRequest) *QueryResponse {
	playerName, _ := request.Params["player"].(string)
	team, _ := request.Params["teams"].([]string)

	var player *models.Player

	if playerName != "" {
		player = s.db.FindPlayerByName(playerName)
	}

	if player == nil && len(team) > 0 {
		players := s.db.FindPlayersByClub(team[0])
		if len(players) > 0 {
			// Return the first player found
			p := players[0]
			player = &p
		}
	}

	if player == nil {
		return &QueryResponse{
			Success: false,
			Error:   "Player not found",
		}
	}

	result := map[string]interface{}{
		"id":            player.ID,
		"name":          player.Name,
		"age":           player.Age,
		"nationality":   player.Nationality,
		"overall":       player.Overall,
		"potential":     player.Potential,
		"club":          player.Club,
		"position":      player.Position,
		"jersey_number": player.JerseyNumber,
		"height":        player.Height,
		"weight":        player.Weight,
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Found player: %s", player.Name),
		Data:    result,
	}
}

// handleTeamStats handles team statistics queries
func (s *Server) handleTeamStats(request *QueryRequest) *QueryResponse {
	teams, _ := request.Params["teams"].([]string)
	season, _ := request.Params["season"].(int)

	if len(teams) == 0 {
		return &QueryResponse{
			Success: false,
			Error:   "Please specify a team",
		}
	}

	team := teams[0]
	stats := s.db.GetTeamStats(team, season)

	result := map[string]interface{}{
		"team":         stats.TeamName,
		"season":       season,
		"matches":      stats.Matches,
		"wins":         stats.Wins,
		"draws":        stats.Draws,
		"losses":       stats.Losses,
		"goals_for":    stats.GoalsFor,
		"goals_against": stats.GoalsAgainst,
		"points":       stats.Points,
		"win_rate":     fmt.Sprintf("%.1f%%", stats.WinRate),
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Statistics for %s", team),
		Data:    result,
	}
}

// handleHeadToHead handles head-to-head queries
func (s *Server) handleHeadToHead(request *QueryRequest) *QueryResponse {
	teams, _ := request.Params["teams"].([]string)

	if len(teams) != 2 {
		return &QueryResponse{
			Success: false,
			Error:   "Please specify exactly two teams",
		}
	}

	h2h := s.db.GetHeadToHead(teams[0], teams[1])

	result := map[string]interface{}{
		"team_1":         h2h.Team1,
		"team_2":         h2h.Team2,
		"matches":        h2h.Matches,
		"team_1_wins":    h2h.Team1Wins,
		"team_2_wins":    h2h.Team2Wins,
		"draws":          h2h.Draws,
		"team_1_goals":   h2h.Team1Goals,
		"team_2_goals":   h2h.Team2Goals,
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Head-to-head between %s and %s", h2h.Team1, h2h.Team2),
		Data:    result,
	}
}

// handleStandings handles standings queries
func (s *Server) handleStandings(request *QueryRequest) *QueryResponse {
	competition, _ := request.Params["competition"].(string)
	season, _ := request.Params["season"].(int)

	if season == 0 {
		season = 2023 // Default to most recent season
	}

	standings := s.db.CalculateLeagueStandings(competition, season)

	if len(standings) == 0 {
		return &QueryResponse{
			Success: false,
			Error:   fmt.Sprintf("No standings found for %s %d", competition, season),
		}
	}

	// Format standings
	result := make([]map[string]interface{}, len(standings))
	for i, team := range standings {
		result[i] = map[string]interface{}{
			"position":      i + 1,
			"team":          team.TeamName,
			"matches":       team.Matches,
			"wins":          team.Wins,
			"draws":         team.Draws,
			"losses":        team.Losses,
			"goals_for":     team.GoalsFor,
			"goals_against": team.GoalsAgainst,
			"points":        team.Points,
		}
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("%d standings for %s %d", len(standings), competition, season),
		Data:    result,
	}
}

// handleTopScorers handles top scorers queries
func (s *Server) handleTopScorers(request *QueryRequest) *QueryResponse {
	limit := 10
	if val, ok := request.Params["limit"].(int); ok {
		limit = val
	}

	topPlayers := s.db.GetTopScorers(limit)

	result := make([]map[string]interface{}, len(topPlayers))
	for i, player := range topPlayers {
		result[i] = map[string]interface{}{
			"rank":          i + 1,
			"name":          player.Name,
			"nationality":   player.Nationality,
			"overall":       player.Overall,
			"potential":     player.Potential,
			"club":          player.Club,
			"position":      player.Position,
		}
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Top %d players by overall rating", limit),
		Data:    result,
	}
}

// handleBrazilianPlayers handles Brazilian players queries
func (s *Server) handleBrazilianPlayers(request *QueryRequest) *QueryResponse {
	limit := 10
	if val, ok := request.Params["limit"].(int); ok {
		limit = val
	}

	brazilianPlayers := s.db.GetTopBrazilianPlayers(limit)

	result := make([]map[string]interface{}, len(brazilianPlayers))
	for i, player := range brazilianPlayers {
		result[i] = map[string]interface{}{
			"rank":          i + 1,
			"name":          player.Name,
			"nationality":   player.Nationality,
			"overall":       player.Overall,
			"potential":     player.Potential,
			"club":          player.Club,
			"position":      player.Position,
		}
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Top %d Brazilian players", limit),
		Data:    result,
	}
}

// handlePlayersByClub handles players by club queries
func (s *Server) handlePlayersByClub(request *QueryRequest) *QueryResponse {
	teams, _ := request.Params["teams"].([]string)

	if len(teams) == 0 {
		return &QueryResponse{
			Success: false,
			Error:   "Please specify a club",
		}
	}

	players := s.db.GetPlayersByClub(teams[0])

	result := make([]map[string]interface{}, len(players))
	for i, player := range players {
		result[i] = map[string]interface{}{
			"rank":          i + 1,
			"name":          player.Name,
			"age":           player.Age,
			"position":      player.Position,
			"overall":       player.Overall,
			"jersey_number": player.JerseyNumber,
		}
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("%d players for %s", len(players), teams[0]),
		Data:    result,
	}
}

// handleBigWins handles big wins queries
func (s *Server) handleBigWins(request *QueryRequest) *QueryResponse {
	threshold := 5
	if val, ok := request.Params["threshold"].(int); ok {
		threshold = val
	}

	bigWins := s.db.GetBigWins(threshold)

	result := make([]map[string]interface{}, len(bigWins))
	for i, win := range bigWins {
		result[i] = map[string]interface{}{
			"rank":          i + 1,
			"date":          win.Date.Format("2006-01-02"),
			"home_team":     win.HomeTeam,
			"away_team":     win.AwayTeam,
			"home_score":    win.HomeGoal,
			"away_score":    win.AwayGoal,
			"goal_diff":     win.GoalDiff,
			"tournament":    win.Tournament,
		}
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Found %d big wins with margin >= %d goals", len(bigWins), threshold),
		Data:    result,
	}
}

// handleAverageGoals handles average goals queries
func (s *Server) handleAverageGoals(request *QueryRequest) *QueryResponse {
	competition, _ := request.Params["competition"].(string)
	season, _ := request.Params["season"].(int)

	avgGoals := s.db.GetAverageGoalsPerMatch(competition, season)

	result := map[string]interface{}{
		"competition": competition,
		"season":      season,
		"average_goals_per_match": fmt.Sprintf("%.2f", avgGoals),
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Average goals per match: %.2f", avgGoals),
		Data:    result,
	}
}

// handleHomeWinRate handles home win rate queries
func (s *Server) handleHomeWinRate(request *QueryRequest) *QueryResponse {
	competition, _ := request.Params["competition"].(string)
	season, _ := request.Params["season"].(int)

	homeWinRate := s.db.GetHomeWinRate(competition, season)

	result := map[string]interface{}{
		"competition":    competition,
		"season":         season,
		"home_win_rate":  fmt.Sprintf("%.1f%%", homeWinRate),
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Home win rate: %.1f%%", homeWinRate),
		Data:    result,
	}
}

// handleCompareTeams handles team comparison queries
func (s *Server) handleCompareTeams(request *QueryRequest) *QueryResponse {
	teams, _ := request.Params["teams"].([]string)

	if len(teams) != 2 {
		return &QueryResponse{
			Success: false,
			Error:   "Please specify exactly two teams",
		}
	}

	h2h := s.db.GetHeadToHead(teams[0], teams[1])
	stats1 := s.db.GetTeamStats(teams[0], 0)
	stats2 := s.db.GetTeamStats(teams[1], 0)

	result := map[string]interface{}{
		"team_1": map[string]interface{}{
			"name":        stats1.TeamName,
			"matches":     stats1.Matches,
			"wins":        stats1.Wins,
			"draws":       stats1.Draws,
			"losses":      stats1.Losses,
			"goals_for":   stats1.GoalsFor,
			"goals_against": stats1.GoalsAgainst,
			"points":      stats1.Points,
		},
		"team_2": map[string]interface{}{
			"name":        stats2.TeamName,
			"matches":     stats2.Matches,
			"wins":        stats2.Wins,
			"draws":       stats2.Draws,
			"losses":      stats2.Losses,
			"goals_for":   stats2.GoalsFor,
			"goals_against": stats2.GoalsAgainst,
			"points":      stats2.Points,
		},
		"head_to_head": map[string]interface{}{
			"team_1_wins": h2h.Team1Wins,
			"team_2_wins": h2h.Team2Wins,
			"draws":       h2h.Draws,
		},
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Comparison between %s and %s", teams[0], teams[1]),
		Data:    result,
	}
}

// handleLastMatch handles last match queries
func (s *Server) handleLastMatch(request *QueryRequest) *QueryResponse {
	teams, _ := request.Params["teams"].([]string)

	if len(teams) == 0 {
		return &QueryResponse{
			Success: false,
			Error:   "Please specify a team",
		}
	}

	matches := s.db.FindMatchesByTeam(teams[0], 0)
	if len(matches) == 0 {
		return &QueryResponse{
			Success: false,
			Error:   "No matches found for this team",
		}
	}

	// Find the most recent match
	var lastMatch *models.Match
	for i := range matches {
		if lastMatch == nil || matches[i].Datetime.After(lastMatch.Datetime) {
			lastMatch = &matches[i]
		}
	}

	if lastMatch == nil {
		return &QueryResponse{
			Success: false,
			Error:   "Could not find last match",
		}
	}

	result := map[string]interface{}{
		"date":      lastMatch.Datetime.Format("2006-01-02 15:04:05"),
		"home_team": lastMatch.HomeTeam,
		"away_team": lastMatch.AwayTeam,
		"home_score": lastMatch.HomeGoal,
		"away_score": lastMatch.AwayGoal,
		"season":     lastMatch.Season,
		"round":      lastMatch.Round,
		"tournament": lastMatch.Tournament,
	}

	return &QueryResponse{
		Success: true,
		Message: fmt.Sprintf("Last match for %s", teams[0]),
		Data:    result,
	}
}

// formatMatches formats matches for response
func formatMatches(matches []models.Match) []map[string]interface{} {
	result := make([]map[string]interface{}, len(matches))
	for i, match := range matches {
		result[i] = map[string]interface{}{
			"date":       match.Datetime.Format("2006-01-02 15:04:05"),
			"home_team":  match.HomeTeam,
			"away_team":  match.AwayTeam,
			"home_score": match.HomeGoal,
			"away_score": match.AwayGoal,
			"season":     match.Season,
			"round":      match.Round,
			"tournament": match.Tournament,
			"stage":      match.Stage,
		}
	}
	return result
}

// MarshalJSON implements json.Marshaler
func (r *QueryResponse) MarshalJSON() ([]byte, error) {
	type Alias QueryResponse
	return json.Marshal(&struct {
		*Alias
	}{
		Alias: (*Alias)(r),
	})
}
