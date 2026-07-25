package main

import (
	"fmt"
	"os"
	"strings"
)

// Server represents the MCP server
type Server struct {
	Data *DataStore
}

// NewServer creates a new MCP server instance
func NewServer() *Server {
	return &Server{
		Data: NewDataStore(),
	}
}

// LoadData loads all CSV files from the data directory
func (s *Server) LoadData(dataDir string) error {
	// Check if data directory exists
	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		return fmt.Errorf("data directory not found: %s", dataDir)
	}

	// Define file paths
	files := map[string]string{
		"brasileirao":     "data/kaggle/Brasileirao_Matches.csv",
		"copa_brasil":     "data/kaggle/Brazilian_Cup_Matches.csv",
		"libertadores":    "data/kaggle/Libertadores_Matches.csv",
		"br_football":     "data/kaggle/BR-Football-Dataset.csv",
		"novo_campeonato": "data/kaggle/novo_campeonato_brasileiro.csv",
		"players":         "data/kaggle/fifa_data.csv",
	}

	// Load each file
	if err := s.Data.LoadBrasileiraoMatches(files["brasileirao"]); err != nil {
		return fmt.Errorf("failed to load brasileirao matches: %w", err)
	}

	if err := s.Data.LoadCopaDoBrasilMatches(files["copa_brasil"]); err != nil {
		return fmt.Errorf("failed to load copa do brasil matches: %w", err)
	}

	if err := s.Data.LoadCopaLibertadoresMatches(files["libertadores"]); err != nil {
		return fmt.Errorf("failed to load libertadores matches: %w", err)
	}

	if err := s.Data.LoadBRFootballMatches(files["br_football"]); err != nil {
		return fmt.Errorf("failed to load BR Football matches: %w", err)
	}

	if err := s.Data.LoadNovoCampeonatoMatches(files["novo_campeonato"]); err != nil {
		return fmt.Errorf("failed to load novo campeonato matches: %w", err)
	}

	if err := s.Data.LoadPlayers(files["players"]); err != nil {
		return fmt.Errorf("failed to load players: %w", err)
	}

	return nil
}

// Query handles natural language queries about Brazilian soccer
func (s *Server) Query(query string) (string, error) {
	query = strings.ToLower(query)

	// Match queries
	if strings.Contains(query, "match") || strings.Contains(query, "game") || strings.Contains(query, "play") {
		if strings.Contains(query, "flamengo") && strings.Contains(query, "fluminense") {
			return s.queryMatchesBetweenTeams("Flamengo", "Fluminense")
		}
		if strings.Contains(query, "palmeiras") && strings.Contains(query, "santos") {
			return s.queryMatchesBetweenTeams("Palmeiras", "Santos")
		}
		if strings.Contains(query, "corinthians") && strings.Contains(query, "palmeiras") {
			return s.queryMatchesBetweenTeams("Corinthians", "Palmeiras")
		}
		if strings.Contains(query, "flamengo") && strings.Contains(query, "corinthians") {
			return s.queryMatchesBetweenTeams("Flamengo", "Corinthians")
		}
		if strings.Contains(query, "when did flamengo last play") {
			// Extract team from query
			team := extractTeamFromQuery(query, "last play")
			if team != "" {
				return s.queryLastMatch("Flamengo", team)
			}
		}
		if strings.Contains(query, "what matches did") && strings.Contains(query, "play in") {
			return s.queryMatchesByTeamAndSeason(query)
		}
		if strings.Contains(query, "find all") && strings.Contains(query, "finals") {
			return s.queryFinals(query)
		}
	}

	// Team queries
	if strings.Contains(query, "record") || strings.Contains(query, "stats") || strings.Contains(query, "statistics") {
		if strings.Contains(query, "corinthians") && strings.Contains(query, "2022") {
			return s.queryTeamStats("Corinthians", 2022)
		}
		if strings.Contains(query, "palmeiras") && strings.Contains(query, "2023") {
			return s.queryTeamStats("Palmeiras", 2023)
		}
		if strings.Contains(query, "best home record") {
			return s.queryBestHomeRecord()
		}
		if strings.Contains(query, "compare") && strings.Contains(query, "head-to-head") {
			return s.queryHeadToHeadComparison(query)
		}
	}

	// Player queries
	if strings.Contains(query, "player") || strings.Contains(query, "fifa") {
		if strings.Contains(query, "brazilian") {
			return s.queryBrazilianPlayers(query)
		}
		if strings.Contains(query, "flamengo") {
			return s.queryPlayersByClub("Flamengo")
		}
		if strings.Contains(query, "forwards") {
			return s.queryForwards(query)
		}
		if strings.Contains(query, "who is") && strings.Contains(query, "barbosa") {
			return s.queryPlayerByName("Gabriel Barbosa")
		}
	}

	// Competition queries
	if strings.Contains(query, "won") || strings.Contains(query, "champion") {
		if strings.Contains(query, "2019") && strings.Contains(query, "brasileirão") {
			return s.queryChampion(2019, "Brasileirão")
		}
		if strings.Contains(query, "2018") && strings.Contains(query, "libertadores") {
			return s.queryLibertadoresBracket(2018)
		}
		if strings.Contains(query, "relegated") && strings.Contains(query, "2020") {
			return s.queryRelegated(2020)
		}
	}

	// Statistical queries
	if strings.Contains(query, "average") || strings.Contains(query, "avg") {
		if strings.Contains(query, "goals") && strings.Contains(query, "per match") {
			return s.queryAverageGoalsPerMatch()
		}
		if strings.Contains(query, "home win") {
			return s.queryHomeWinRate()
		}
	}
	if strings.Contains(query, "biggest wins") || strings.Contains(query, "biggest victory") {
		return s.queryBiggestWins()
	}

	// Default response
	return s.queryDefault(query), nil
}

// queryMatchesBetweenTeams finds matches between two teams
func (s *Server) queryMatchesBetweenTeams(team1, team2 string) (string, error) {
	matches := s.Data.GetMatchesByTeams(team1, team2)

	if len(matches) == 0 {
		return fmt.Sprintf("No matches found between %s and %s in the dataset.", team1, team2), nil
	}

	// Sort by date descending (most recent first)
	for i := 0; i < len(matches)-1; i++ {
		for j := i + 1; j < len(matches); j++ {
			if matches[j].Datetime.After(matches[i].Datetime) {
				matches[i], matches[j] = matches[j], matches[i]
			}
		}
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("%s vs %s matches:\n", team1, team2))

	count := 0
	for _, m := range matches {
		if count >= 15 {
			break
		}
		result.WriteString(fmt.Sprintf("- %s: %s %d-%d %s\n",
			m.Datetime.Format("2006-01-02"),
			m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam))
		count++
	}

	if len(matches) > 15 {
		result.WriteString(fmt.Sprintf("\n... and %d more matches in the dataset\n", len(matches)-15))
	}

	// Calculate head-to-head record
	h2h := s.Data.GetHeadToHead(team1, team2)
	result.WriteString(fmt.Sprintf("\nHead-to-head record: %s %d wins, %s %d wins, %d draws\n",
		team1, h2h.Wins, team2, h2h.Losses, h2h.Draws))

	return result.String(), nil
}

// queryLastMatch finds the most recent match for a team
func (s *Server) queryLastMatch(team1, team2 string) (string, error) {
	matches := s.Data.GetMatchesByTeams(team1, team2)

	if len(matches) == 0 {
		return fmt.Sprintf("No matches found between %s and %s in the dataset.", team1, team2), nil
	}

	// Find most recent match
	var lastMatch Match
	for _, m := range matches {
		if m.Datetime.After(lastMatch.Datetime) {
			lastMatch = m
		}
	}

	return fmt.Sprintf("%s last played %s on %s: %s %d-%d %s",
		team1, team2,
		lastMatch.Datetime.Format("2006-01-02"),
		lastMatch.HomeTeam, lastMatch.HomeGoal, lastMatch.AwayGoal, lastMatch.AwayTeam), nil
}

// queryMatchesByTeamAndSeason finds matches for a team in a specific season
func (s *Server) queryMatchesByTeamAndSeason(query string) (string, error) {
	// Extract team and season from query
	var team string
	var season int

	teams := []string{"Palmeiras", "Flamengo", "São Paulo", "Corinthians", "Santos", "Grêmio", "Internacional"}
	for _, t := range teams {
		if strings.Contains(query, strings.ToLower(t)) {
			team = t
			break
		}
	}

	if team == "" {
		return "I couldn't identify the team. Try asking about Palmeiras, Flamengo, São Paulo, Corinthians, or Santos.", nil
	}

	// Extract year
	for i := 2003; i <= 2024; i++ {
		if strings.Contains(query, fmt.Sprintf("%d", i)) {
			season = i
			break
		}
	}

	if season == 0 {
		return "I couldn't identify the season. Try asking about a specific year like 2023.", nil
	}

	matches := s.Data.GetMatchesByTeam(team)
	var seasonMatches []Match
	for _, m := range matches {
		if m.Season == season {
			seasonMatches = append(seasonMatches, m)
		}
	}

	if len(seasonMatches) == 0 {
		return fmt.Sprintf("%s did not play in the %d season in the datasets.", team, season), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("%s matches in %d:\n", team, season))

	count := 0
	for _, m := range seasonMatches {
		if count >= 20 {
			break
		}
		result.WriteString(fmt.Sprintf("- %s: %s %d-%d %s\n",
			m.Datetime.Format("2006-01-02"),
			m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam))
		count++
	}

	if len(seasonMatches) > 20 {
		result.WriteString(fmt.Sprintf("\n... and %d more matches\n", len(seasonMatches)-20))
	}

	return result.String(), nil
}

// queryFinals finds final matches
func (s *Server) queryFinals(query string) (string, error) {
	var finals []Match

	allMatches := append(append(append(append(
		s.Data.BrasileiraoMatches,
		s.Data.CopaDoBrasilMatches...),
		s.Data.CopaLibertadoresMatches...),
		s.Data.BRFootballMatches...),
		s.Data.NovoCampeonatoMatches...)

	for _, m := range allMatches {
		if strings.Contains(strings.ToLower(m.Round), "final") ||
			strings.Contains(strings.ToLower(m.Stage), "final") ||
			strings.Contains(strings.ToLower(m.Tournament), "final") {
			finals = append(finals, m)
		}
	}

	if len(finals) == 0 {
		return "No finals found in the dataset.", nil
	}

	var result strings.Builder
	result.WriteString("Final matches in the dataset:\n\n")

	count := 0
	for _, m := range finals {
		if count >= 10 {
			break
		}
		result.WriteString(fmt.Sprintf("- %s: %s %d-%d %s (%s)\n",
			m.Datetime.Format("2006-01-02"),
			m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam,
			m.Tournament))
		count++
	}

	return result.String(), nil
}

// queryTeamStats returns statistics for a team in a season
func (s *Server) queryTeamStats(team string, season int) (string, error) {
	stats := s.Data.GetTeamStats(team, season)

	if stats.Matches == 0 {
		return fmt.Sprintf("No data found for %s in season %d.", team, season), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("%s record in %d:\n", team, season))
	result.WriteString(fmt.Sprintf("- Matches: %d\n", stats.Matches))
	result.WriteString(fmt.Sprintf("- Wins: %d, Draws: %d, Losses: %d\n", stats.Wins, stats.Draws, stats.Losses))
	result.WriteString(fmt.Sprintf("- Goals For: %d, Goals Against: %d\n", stats.GoalsFor, stats.GoalsAgainst))
	result.WriteString(fmt.Sprintf("- Points: %d\n", stats.Points))
	result.WriteString(fmt.Sprintf("- Win rate: %.1f%%\n", stats.WinRate))
	result.WriteString(fmt.Sprintf("- Average goals per match: %.2f\n", stats.AvgGoalsPerMatch))

	return result.String(), nil
}

// queryBestHomeRecord finds the team with the best home record
func (s *Server) queryBestHomeRecord() (string, error) {
	// Calculate home records for all teams
	teamHomeStats := make(map[string]*TeamStats)

	allMatches := append(append(append(append(
		s.Data.BrasileiraoMatches,
		s.Data.CopaDoBrasilMatches...),
		s.Data.CopaLibertadoresMatches...),
		s.Data.BRFootballMatches...),
		s.Data.NovoCampeonatoMatches...)

	for _, m := range allMatches {
		if m.HomeTeam != "" {
			if _, exists := teamHomeStats[m.HomeTeam]; !exists {
				teamHomeStats[m.HomeTeam] = &TeamStats{TeamName: m.HomeTeam}
			}
			stats := teamHomeStats[m.HomeTeam]
			stats.HomeMatches++
			stats.HomeGoalsFor += m.HomeGoal
			stats.HomeGoalsAgainst += m.AwayGoal

			if m.HomeGoal > m.AwayGoal {
				stats.HomeWins++
			} else if m.HomeGoal == m.AwayGoal {
				stats.HomeDraws++
			} else {
				stats.HomeLosses++
			}
		}
	}

	// Sort by home win rate
	type teamWinRate struct {
		Team    string
		Wins    int
		Matches int
		Rate    float64
	}

	var rates []teamWinRate
	for team, stats := range teamHomeStats {
		if stats.HomeMatches > 0 {
			rates = append(rates, teamWinRate{
				Team:    team,
				Wins:    stats.HomeWins,
				Matches: stats.HomeMatches,
				Rate:    float64(stats.HomeWins) / float64(stats.HomeMatches) * 100,
			})
		}
	}

	// Sort by win rate
	for i := 0; i < len(rates)-1; i++ {
		for j := i + 1; j < len(rates); j++ {
			if rates[j].Rate > rates[i].Rate {
				rates[i], rates[j] = rates[j], rates[i]
			}
		}
	}

	var result strings.Builder
	result.WriteString("Teams with best home records:\n\n")

	count := 0
	for _, r := range rates {
		if count >= 10 {
			break
		}
		result.WriteString(fmt.Sprintf("%d. %s - %.1f%% win rate (%d wins in %d home matches)\n",
			count+1, r.Team, r.Rate, r.Wins, r.Matches))
		count++
	}

	return result.String(), nil
}

// queryHeadToHeadComparison compares two teams head-to-head
func (s *Server) queryHeadToHeadComparison(query string) (string, error) {
	teams := []string{"Palmeiras", "Santos", "Corinthians", "Flamengo", "Fluminense", "São Paulo", "Grêmio"}
	var team1, team2 string

	for _, t := range teams {
		if strings.Contains(query, strings.ToLower(t)) {
			if team1 == "" {
				team1 = t
			} else if team2 == "" {
				team2 = t
			}
		}
	}

	if team1 == "" || team2 == "" {
		return "I couldn't identify both teams for comparison. Try: 'compare Palmeiras and Santos head-to-head'", nil
	}

	h2h := s.Data.GetHeadToHead(team1, team2)

	var result strings.Builder
	result.WriteString(fmt.Sprintf("%s vs %s Head-to-Head:\n\n", team1, team2))
	result.WriteString(fmt.Sprintf("Total matches: %d\n", h2h.Matches))
	result.WriteString(fmt.Sprintf("%s wins: %d\n", team1, h2h.Wins))
	result.WriteString(fmt.Sprintf("%s wins: %d\n", team2, h2h.Losses))
	result.WriteString(fmt.Sprintf("Draws: %d\n", h2h.Draws))
	result.WriteString(fmt.Sprintf("\nGoals scored by %s: %d\n", team1, h2h.GoalsFor))
	result.WriteString(fmt.Sprintf("Goals scored by %s: %d\n", team2, h2h.GoalsAgainst))

	return result.String(), nil
}

// queryBrazilianPlayers finds Brazilian players
func (s *Server) queryBrazilianPlayers(query string) (string, error) {
	brazilianPlayers := s.Data.GetBrazilianPlayers()

	if len(brazilianPlayers) == 0 {
		return "No Brazilian players found in the dataset.", nil
	}

	var result strings.Builder
	result.WriteString("Brazilian players in the dataset:\n\n")

	// Sort by overall rating
	for i := 0; i < len(brazilianPlayers)-1; i++ {
		for j := i + 1; j < len(brazilianPlayers); j++ {
			if brazilianPlayers[j].Overall > brazilianPlayers[i].Overall {
				brazilianPlayers[i], brazilianPlayers[j] = brazilianPlayers[j], brazilianPlayers[i]
			}
		}
	}

	count := 0
	for _, p := range brazilianPlayers {
		if count >= 20 {
			break
		}
		result.WriteString(fmt.Sprintf("%d. %s - Overall: %d, Position: %s, Club: %s\n",
			count+1, p.Name, p.Overall, p.Position, p.Club))
		count++
	}

	if len(brazilianPlayers) > 20 {
		result.WriteString(fmt.Sprintf("\n... and %d more Brazilian players\n", len(brazilianPlayers)-20))
	}

	return result.String(), nil
}

// queryPlayersByClub finds players by club
func (s *Server) queryPlayersByClub(club string) (string, error) {
	players := s.Data.GetPlayersByClub(club)

	if len(players) == 0 {
		return fmt.Sprintf("No players found for %s in the dataset.", club), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("Players at %s:\n\n", club))

	// Sort by overall rating
	for i := 0; i < len(players)-1; i++ {
		for j := i + 1; j < len(players); j++ {
			if players[j].Overall > players[i].Overall {
				players[i], players[j] = players[j], players[i]
			}
		}
	}

	count := 0
	for _, p := range players {
		if count >= 15 {
			break
		}
		result.WriteString(fmt.Sprintf("%d. %s - Overall: %d, Position: %s, Jersey: %d\n",
			count+1, p.Name, p.Overall, p.Position, p.JerseyNumber))
		count++
	}

	if len(players) > 15 {
		result.WriteString(fmt.Sprintf("\n... and %d more players\n", len(players)-15))
	}

	return result.String(), nil
}

// queryForwards finds forwards from a club
func (s *Server) queryForwards(query string) (string, error) {
	// Extract club from query
	club := ""
	clubs := []string{"Flamengo", "Palmeiras", "Corinthians", "Santos", "São Paulo", "Grêmio", "Internacional"}
	for _, c := range clubs {
		if strings.Contains(query, strings.ToLower(c)) {
			club = c
			break
		}
	}

	if club == "" {
		return "I couldn't identify the club. Try asking about forwards from Flamengo, Palmeiras, or another Brazilian club.", nil
	}

	players := s.Data.GetPlayersByClub(club)
	var forwards []Player
	for _, p := range players {
		if strings.Contains(strings.ToLower(p.Position), "forward") || strings.Contains(strings.ToLower(p.Position), "striker") {
			forwards = append(forwards, p)
		}
	}

	if len(forwards) == 0 {
		return fmt.Sprintf("No forwards found for %s in the dataset.", club), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("Forwards at %s:\n\n", club))

	// Sort by overall rating
	for i := 0; i < len(forwards)-1; i++ {
		for j := i + 1; j < len(forwards); j++ {
			if forwards[j].Overall > forwards[i].Overall {
				forwards[i], forwards[j] = forwards[j], forwards[i]
			}
		}
	}

	count := 0
	for _, p := range forwards {
		if count >= 10 {
			break
		}
		result.WriteString(fmt.Sprintf("%d. %s - Overall: %d, Position: %s\n",
			count+1, p.Name, p.Overall, p.Position))
		count++
	}

	return result.String(), nil
}

// queryPlayerByName searches for a player by name
func (s *Server) queryPlayerByName(name string) (string, error) {
	player := s.Data.GetPlayerByName(name)

	if player == nil {
		return fmt.Sprintf("Player '%s' not found in the dataset.", name), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("%s:\n", player.Name))
	result.WriteString(fmt.Sprintf("- Age: %d\n", player.Age))
	result.WriteString(fmt.Sprintf("- Nationality: %s\n", player.Nationality))
	result.WriteString(fmt.Sprintf("- Overall: %d\n", player.Overall))
	result.WriteString(fmt.Sprintf("- Potential: %d\n", player.Potential))
	result.WriteString(fmt.Sprintf("- Club: %s\n", player.Club))
	result.WriteString(fmt.Sprintf("- Position: %s\n", player.Position))
	result.WriteString(fmt.Sprintf("- Jersey Number: %d\n", player.JerseyNumber))
	result.WriteString(fmt.Sprintf("- Height: %s\n", player.Height))
	result.WriteString(fmt.Sprintf("- Weight: %s\n", player.Weight))

	return result.String(), nil
}

// queryChampion returns the champion of a season
func (s *Server) queryChampion(season int, tournament string) (string, error) {
	standings := s.Data.GetTeamStandings(tournament, season)

	if len(standings) == 0 {
		return fmt.Sprintf("No data found for %s in %d.", tournament, season), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("%d %s Final Standings:\n\n", season, tournament))

	count := 0
	for _, s := range standings {
		if count >= 20 {
			break
		}
		var championMarker string
		if count == 0 {
			championMarker = " - Champion"
		}
		result.WriteString(fmt.Sprintf("%d. %s - %d pts (%dW, %dD, %dL)%s\n",
			count+1, s.TeamName, s.Points, s.Wins, s.Draws, s.Losses, championMarker))
		count++
	}

	return result.String(), nil
}

// queryLibertadoresBracket returns Libertadores bracket for a season
func (s *Server) queryLibertadoresBracket(season int) (string, error) {
	matches := s.Data.GetMatchesByTournament("Libertadores")

	var seasonMatches []Match
	for _, m := range matches {
		if m.Season == season {
			seasonMatches = append(seasonMatches, m)
		}
	}

	if len(seasonMatches) == 0 {
		return fmt.Sprintf("No Libertadores matches found for %d.", season), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("%d Copa Libertadores:\n\n", season))

	// Group by stage
	stages := make(map[string][]Match)
	for _, m := range seasonMatches {
		stages[m.Stage] = append(stages[m.Stage], m)
	}

	for stage, stageMatches := range stages {
		result.WriteString(fmt.Sprintf("%s:\n", stage))

		count := 0
		for _, m := range stageMatches {
			if count >= 10 {
				break
			}
			result.WriteString(fmt.Sprintf("- %s: %s %d-%d %s\n",
				m.Datetime.Format("2006-01-02"),
				m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam))
			count++
		}

		if len(stageMatches) > 10 {
			result.WriteString(fmt.Sprintf("... and %d more matches in this stage\n", len(stageMatches)-10))
		}
		result.WriteString("\n")
	}

	return result.String(), nil
}

// queryRelegated returns relegated teams
func (s *Server) queryRelegated(season int) (string, error) {
	// Brasileirão has 4 relegated teams (18th, 19th, 20th, 21st in modern format)
	standings := s.Data.GetTeamStandings("Brasileirão", season)

	if len(standings) == 0 {
		return fmt.Sprintf("No Brasileirão data found for %d.", season), nil
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("Teams relegated from %d Brasileirão:\n\n", season))

	count := 0
	for i := len(standings) - 1; i >= 0 && count < 4; i-- {
		result.WriteString(fmt.Sprintf("%d. %s (%d pts)\n", count+1, standings[i].TeamName, standings[i].Points))
		count++
	}

	return result.String(), nil
}

// queryAverageGoalsPerMatch returns average goals per match
func (s *Server) queryAverageGoalsPerMatch() (string, error) {
	avg := s.Data.GetAverageGoalsPerMatch()

	var result strings.Builder
	result.WriteString(fmt.Sprintf("Average goals per match: %.2f\n", avg))
	result.WriteString("\nBreakdown:\n")

	allMatches := append(append(append(append(
		s.Data.BrasileiraoMatches,
		s.Data.CopaDoBrasilMatches...),
		s.Data.CopaLibertadoresMatches...),
		s.Data.BRFootballMatches...),
		s.Data.NovoCampeonatoMatches...)

	var totalGoals int
	for _, m := range allMatches {
		totalGoals += m.HomeGoal + m.AwayGoal
	}

	result.WriteString(fmt.Sprintf("- Total matches analyzed: %d\n", len(allMatches)))
	result.WriteString(fmt.Sprintf("- Total goals scored: %d\n", totalGoals))
	result.WriteString(fmt.Sprintf("- Average goals per match: %.2f\n", avg))

	return result.String(), nil
}

// queryHomeWinRate returns home win rate
func (s *Server) queryHomeWinRate() (string, error) {
	rate := s.Data.GetHomeWinRate()

	var result strings.Builder
	result.WriteString(fmt.Sprintf("Home win rate: %.1f%%\n", rate))
	result.WriteString("\nDetails:\n")

	allMatches := append(append(append(append(
		s.Data.BrasileiraoMatches,
		s.Data.CopaDoBrasilMatches...),
		s.Data.CopaLibertadoresMatches...),
		s.Data.BRFootballMatches...),
		s.Data.NovoCampeonatoMatches...)

	var homeWins, draws, awayWins, total int
	for _, m := range allMatches {
		total++
		if m.HomeGoal > m.AwayGoal {
			homeWins++
		} else if m.HomeGoal == m.AwayGoal {
			draws++
		} else {
			awayWins++
		}
	}

	result.WriteString(fmt.Sprintf("- Total matches: %d\n", total))
	result.WriteString(fmt.Sprintf("- Home wins: %d (%.1f%%)\n", homeWins, float64(homeWins)/float64(total)*100))
	result.WriteString(fmt.Sprintf("- Draws: %d (%.1f%%)\n", draws, float64(draws)/float64(total)*100))
	result.WriteString(fmt.Sprintf("- Away wins: %d (%.1f%%)\n", awayWins, float64(awayWins)/float64(total)*100))

	return result.String(), nil
}

// queryBiggestWins returns biggest victories
func (s *Server) queryBiggestWins() (string, error) {
	wins := s.Data.FindBiggestWins(10)

	if len(wins) == 0 {
		return "No matches found in the dataset.", nil
	}

	var result strings.Builder
	result.WriteString("Biggest victories in Brazilian football (provided data):\n\n")

	for i, m := range wins {
		result.WriteString(fmt.Sprintf("%d. %s: %s %d-%d %s\n",
			i+1, m.Datetime.Format("2012-05-27"),
			m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam))
	}

	return result.String(), nil
}

// queryDefault provides a default response
func (s *Server) queryDefault(query string) string {
	return fmt.Sprintf("I can answer questions about Brazilian soccer matches, teams, players, and competitions.\n\n"+

		"Try asking about:\n"+
		"- Matches between teams (e.g., 'Show me Flamengo vs Fluminense matches')\n"+
		"- Team statistics (e.g., 'What is Palmeiras home record in 2023?')\n"+
		"- Players (e.g., 'Who is Neymar?')\n"+
		"- Competitions (e.g., 'Who won the 2019 Brasileirão?')\n"+
		"- Statistics (e.g., 'What's the average goals per match?')\n\n"+

		"Your query: %s", query)
}

// extractTeamFromQuery extracts a team name from a query string
func extractTeamFromQuery(query, keyword string) string {
	teams := []string{"Palmeiras", "Flamengo", "São Paulo", "Corinthians", "Santos", "Grêmio", "Internacional", "Fluminense", "Botafogo", "Vasco", "Bahia", "Fortaleza", "Ceará", "Bragantino", "Athletico-PR", "Goiás", "Coritiba", "América-MG"}
	queryLower := strings.ToLower(query)

	for _, team := range teams {
		if strings.Contains(queryLower, strings.ToLower(team)) {
			return team
		}
	}
	return ""
}
