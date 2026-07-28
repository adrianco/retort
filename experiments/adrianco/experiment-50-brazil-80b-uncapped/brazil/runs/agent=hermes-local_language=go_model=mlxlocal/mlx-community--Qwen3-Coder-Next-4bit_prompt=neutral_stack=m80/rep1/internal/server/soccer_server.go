package server

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/models"
	"brazilian-soccer-mcp/internal/store"
)

// SoccerServer represents the soccer data server with MCP tools
type SoccerServer struct {
	db *store.Database
}

// NewSoccerServer creates a new soccer server
func NewSoccerServer(db *store.Database) *SoccerServer {
	return &SoccerServer{db: db}
}

// FindMatchesByTeam finds matches by team name
func (s *SoccerServer) FindMatchesByTeam(team string, season int) []models.Match {
	return s.db.FindMatchesByTeam(team, season)
}

// FindMatchesByTeams finds matches between two teams
func (s *SoccerServer) FindMatchesByTeams(team1, team2 string) []models.Match {
	return s.db.FindMatchesByTeams(team1, team2)
}

// FindMatchesBySeason finds matches by season
func (s *SoccerServer) FindMatchesBySeason(season int) []models.Match {
	return s.db.FindMatchesBySeason(season)
}

// FindMatchesByCompetition finds matches by competition
func (s *SoccerServer) FindMatchesByCompetition(competition string) []models.Match {
	return s.db.FindMatchesByCompetition(competition)
}

// FindPlayerByName finds a player by name
func (s *SoccerServer) FindPlayerByName(name string) *models.Player {
	return s.db.FindPlayerByName(name)
}

// FindPlayersByName finds multiple players by name
func (s *SoccerServer) FindPlayersByName(name string) []models.Player {
	return s.db.FindPlayersByName(name)
}

// FindPlayersByNationality finds players by nationality
func (s *SoccerServer) FindPlayersByNationality(nationality string) []models.Player {
	return s.db.FindPlayersByNationality(nationality)
}

// FindPlayersByClub finds players by club
func (s *SoccerServer) FindPlayersByClub(club string) []models.Player {
	return s.db.FindPlayersByClub(club)
}

// GetTeamStats gets team statistics
func (s *SoccerServer) GetTeamStats(team string, season int) *models.TeamStats {
	return s.db.GetTeamStats(team, season)
}

// GetHeadToHead gets head-to-head record between two teams
func (s *SoccerServer) GetHeadToHead(team1, team2 string) *models.HeadToHead {
	return s.db.GetHeadToHead(team1, team2)
}

// GetBigWins gets matches with large goal differences
func (s *SoccerServer) GetBigWins(threshold int) []models.BigWin {
	return s.db.GetBigWins(threshold)
}

// CalculateLeagueStandings calculates league standings
func (s *SoccerServer) CalculateLeagueStandings(competition string, season int) []models.CompetitionResult {
	return s.db.CalculateLeagueStandings(competition, season)
}

// GetAverageGoalsPerMatch gets average goals per match
func (s *SoccerServer) GetAverageGoalsPerMatch(competition string, season int) float64 {
	return s.db.GetAverageGoalsPerMatch(competition, season)
}

// GetHomeWinRate gets home win rate
func (s *SoccerServer) GetHomeWinRate(competition string, season int) float64 {
	return s.db.GetHomeWinRate(competition, season)
}

// GetTopScorers gets top scoring players
func (s *SoccerServer) GetTopScorers(limit int) []models.Player {
	return s.db.GetTopScorers(limit)
}

// GetBrazilianPlayers gets all Brazilian players
func (s *SoccerServer) GetBrazilianPlayers() []models.Player {
	return s.db.GetBrazilianPlayers()
}

// GetTopBrazilianPlayers gets top-rated Brazilian players
func (s *SoccerServer) GetTopBrazilianPlayers(limit int) []models.Player {
	return s.db.GetTopBrazilianPlayers(limit)
}

// GetPlayersByClub gets players by club
func (s *SoccerServer) GetPlayersByClub(club string) []models.Player {
	return s.db.GetPlayersByClub(club)
}

// CompareTeams compares two teams
func (s *SoccerServer) CompareTeams(team1, team2 string) map[string]interface{} {
	h2h := s.db.GetHeadToHead(team1, team2)
	stats1 := s.db.GetTeamStats(team1, 0)
	stats2 := s.db.GetTeamStats(team2, 0)

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

	return result
}

// GetLastMatch gets the last match for a team
func (s *SoccerServer) GetLastMatch(team string) *models.Match {
	matches := s.db.FindMatchesByTeam(team, 0)
	if len(matches) == 0 {
		return nil
	}

	// Find the most recent match
	var lastMatch *models.Match
	for i := range matches {
		if lastMatch == nil || matches[i].Datetime.After(lastMatch.Datetime) {
			lastMatch = &matches[i]
		}
	}

	return lastMatch
}

// GetTeamNameVariations returns possible variations of a team name
func (s *SoccerServer) GetTeamNameVariations(team string) []string {
	// Common variations
	variations := []string{
		team,
		team + "-SP",
		team + "-RJ",
		team + "-MG",
		team + "-PE",
		team + "-SC",
		team + "-BA",
		team + "-PR",
		team + "-RS",
		team + "-GO",
		team + "-DF",
		team + "-ES",
		team + "-AM",
		team + "-AL",
		team + "-SE",
		team + "-TO",
		team + "-AP",
		team + "-AC",
		team + "-RO",
		team + "-RR",
		team + "-PA",
	}
	return variations
}

// FormatMatch formats a match for display
func (s *SoccerServer) FormatMatch(match models.Match) string {
	date := match.Datetime.Format("2006-01-02 15:04:05")
	return fmt.Sprintf("%s: %s %d-%d %s (Season %d, Round %d)",
		date, match.HomeTeam, match.HomeGoal, match.AwayGoal, match.AwayTeam, match.Season, match.Round)
}

// FormatTeamStats formats team stats for display
func (s *SoccerServer) FormatTeamStats(team string, stats *models.TeamStats, season int) string {
	winRate := 0.0
	if stats.Matches > 0 {
		winRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}

	return fmt.Sprintf("%s (%d) - Matches: %d, Wins: %d, Draws: %d, Losses: %d, GF: %d, GA: %d, Points: %d, Win Rate: %.1f%%",
		team, season, stats.Matches, stats.Wins, stats.Draws, stats.Losses, stats.GoalsFor, stats.GoalsAgainst, stats.Points, winRate)
}

// FormatHeadToHead formats head-to-head for display
func (s *SoccerServer) FormatHeadToHead(h2h *models.HeadToHead) string {
	return fmt.Sprintf("%s vs %s: %d matches (%d-%d-%d)",
		h2h.Team1, h2h.Team2, h2h.Matches, h2h.Team1Wins, h2h.Team2Wins, h2h.Draws)
}

// FormatBigWin formats a big win for display
func (s *SoccerServer) FormatBigWin(win models.BigWin) string {
	return fmt.Sprintf("%s: %s %d-%d %s (Goal Diff: %d)",
		win.Date.Format("2006-01-02"), win.HomeTeam, win.HomeGoal, win.AwayGoal, win.AwayTeam, win.GoalDiff)
}

// FormatPlayer formats a player for display
func (s *SoccerServer) FormatPlayer(player models.Player) string {
	return fmt.Sprintf("%s (%d years old, %s) - Overall: %d, Club: %s, Position: %s",
		player.Name, player.Age, player.Nationality, player.Overall, player.Club, player.Position)
}

// FormatStandings formats standings for display
func (s *SoccerServer) FormatStandings(standings []models.CompetitionResult, competition string, season int) string {
	var lines []string
	lines = append(lines, fmt.Sprintf("%s %d Standings:", competition, season))
	for i, team := range standings {
		lines = append(lines, fmt.Sprintf("%d. %s - %d pts (%dW-%dD-%dL)",
			i+1, team.TeamName, team.Points, team.Wins, team.Draws, team.Losses))
	}
	return strings.Join(lines, "\n")
}
