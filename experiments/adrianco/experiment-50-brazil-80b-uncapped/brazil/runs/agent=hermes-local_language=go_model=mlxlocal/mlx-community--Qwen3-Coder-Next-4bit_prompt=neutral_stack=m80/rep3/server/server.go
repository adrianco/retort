package server

import (
	"fmt"
	"sort"
	"strings"

	"github.com/retort-2b804a4c50ba/brazilian-soccer-mcp/data"
)

// MCPServer represents the MCP server
type MCPServer struct {
	loader *data.Loader
}

// NewMCPServer creates a new MCP server
func NewMCPServer(loader *data.Loader) *MCPServer {
	return &MCPServer{loader: loader}
}

// FindMatchesByTeams finds matches between two teams
func (s *MCPServer) FindMatchesByTeams(team1, team2 string) ([]data.Match, error) {
	matches := s.loader.GetMatchesByTeams(team1, team2)
	if len(matches) == 0 {
		return nil, fmt.Errorf("no matches found between %s and %s", team1, team2)
	}
	return matches, nil
}

// FindMatchesByTeam finds all matches for a single team
func (s *MCPServer) FindMatchesByTeam(team string) ([]data.Match, error) {
	matches := s.loader.GetMatchesByTeam(team)
	if len(matches) == 0 {
		return nil, fmt.Errorf("no matches found for %s", team)
	}
	return matches, nil
}

// FindMatchesBySeason finds matches in a specific season
func (s *MCPServer) FindMatchesBySeason(season string) ([]data.Match, error) {
	matches := s.loader.GetMatchesBySeason(season)
	if len(matches) == 0 {
		return nil, fmt.Errorf("no matches found for season %s", season)
	}
	return matches, nil
}

// FindMatchesByCompetition finds matches in a specific competition
func (s *MCPServer) FindMatchesByCompetition(competition string) ([]data.Match, error) {
	matches := s.loader.GetMatchesByCompetition(competition)
	if len(matches) == 0 {
		return nil, fmt.Errorf("no matches found for competition %s", competition)
	}
	return matches, nil
}

// GetMatchCountByTeam returns match count for a team
func (s *MCPServer) GetMatchCountByTeam(team string) (int, error) {
	matches := s.loader.GetMatchesByTeam(team)
	return len(matches), nil
}

// GetTeamStatistics calculates statistics for a team
func (s *MCPServer) GetTeamStatistics(team, season, competition string) (*data.TeamStatistics, error) {
	matches := s.loader.GetAllMatches()
	team = data.NormalizeTeamName(team)
	
	stats := &data.TeamStatistics{Team: team}
	
	for _, m := range matches {
		// Filter by season if specified
		if season != "" && m.Season != season {
			continue
		}
		// Filter by competition if specified
		if competition != "" && m.Competition != competition {
			continue
		}
		
		// Check if team played in this match
		isHome := m.HomeTeam == team
		isAway := m.AwayTeam == team
		
		if !isHome && !isAway {
			continue
		}
		
		stats.Matches++
		stats.GoalsFor += m.HomeGoals
		stats.GoalsAgainst += m.AwayGoals
		
		if isHome {
			if m.HomeGoals > m.AwayGoals {
				stats.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				stats.Draws++
			} else {
				stats.Losses++
			}
		} else {
			if m.AwayGoals > m.HomeGoals {
				stats.Wins++
			} else if m.AwayGoals == m.HomeGoals {
				stats.Draws++
			} else {
				stats.Losses++
			}
		}
	}
	
	if stats.Matches > 0 {
		stats.Points = stats.Wins*3 + stats.Draws
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}
	
	return stats, nil
}

// GetHeadToHead calculates head-to-head record between two teams
func (s *MCPServer) GetHeadToHead(team1, team2 string) (map[string]interface{}, error) {
	matches := s.loader.GetMatchesByTeams(team1, team2)
	
	team1 = data.NormalizeTeamName(team1)
	team2 = data.NormalizeTeamName(team2)
	
	result := map[string]interface{}{
		"team1":        team1,
		"team2":        team2,
		"matches":      len(matches),
		"team1_wins":   0,
		"team2_wins":   0,
		"draws":        0,
		"team1_goals":  0,
		"team2_goals":  0,
		"matches_list": []data.Match{},
	}
	
	for _, m := range matches {
		if m.HomeTeam == team1 {
			result["team1_goals"] = result["team1_goals"].(int) + m.HomeGoals
			result["team2_goals"] = result["team2_goals"].(int) + m.AwayGoals
			
			if m.HomeGoals > m.AwayGoals {
				result["team1_wins"] = result["team1_wins"].(int) + 1
			} else if m.HomeGoals < m.AwayGoals {
				result["team2_wins"] = result["team2_wins"].(int) + 1
			} else {
				result["draws"] = result["draws"].(int) + 1
			}
		} else {
			result["team1_goals"] = result["team1_goals"].(int) + m.AwayGoals
			result["team2_goals"] = result["team2_goals"].(int) + m.HomeGoals
			
			if m.AwayGoals > m.HomeGoals {
				result["team1_wins"] = result["team1_wins"].(int) + 1
			} else if m.AwayGoals < m.HomeGoals {
				result["team2_wins"] = result["team2_wins"].(int) + 1
			} else {
				result["draws"] = result["draws"].(int) + 1
			}
		}
		
		result["matches_list"] = append(result["matches_list"].([]data.Match), m)
	}
	
	return result, nil
}

// GetTeamCompetitions returns all competitions a team has played in
func (s *MCPServer) GetTeamCompetitions(team string) ([]string, error) {
	matches := s.loader.GetMatchesByTeam(team)
	competitions := make(map[string]bool)
	
	for _, m := range matches {
		competitions[m.Competition] = true
	}
	
	result := make([]string, 0, len(competitions))
	for comp := range competitions {
		result = append(result, comp)
	}
	sort.Strings(result)
	
	return result, nil
}

// CalculateStandings calculates league standings for a competition
func (s *MCPServer) CalculateStandings(competition, season string) []data.CompetitionStandings {
	matches := s.loader.GetAllMatches()
	
	// Map to track team standings
	standings := make(map[string]*data.CompetitionStandings)
	
	for _, m := range matches {
		if m.Competition != competition {
			continue
		}
		if season != "" && m.Season != season {
			continue
		}
		
		// Initialize teams if not exists
		if standings[m.HomeTeam] == nil {
			standings[m.HomeTeam] = &data.CompetitionStandings{Team: m.HomeTeam}
		}
		if standings[m.AwayTeam] == nil {
			standings[m.AwayTeam] = &data.CompetitionStandings{Team: m.AwayTeam}
		}
		
		// Update home team stats
		standings[m.HomeTeam].Matches++
		standings[m.HomeTeam].GoalsFor += m.HomeGoals
		standings[m.HomeTeam].GoalsAgainst += m.AwayGoals
		
		// Update away team stats
		standings[m.AwayTeam].Matches++
		standings[m.AwayTeam].GoalsFor += m.AwayGoals
		standings[m.AwayTeam].GoalsAgainst += m.HomeGoals
		
		// Determine winner
		if m.HomeGoals > m.AwayGoals {
			standings[m.HomeTeam].Wins++
			standings[m.HomeTeam].Points += 3
			standings[m.AwayTeam].Losses++
		} else if m.HomeGoals < m.AwayGoals {
			standings[m.AwayTeam].Wins++
			standings[m.AwayTeam].Points += 3
			standings[m.HomeTeam].Losses++
		} else {
			standings[m.HomeTeam].Draws++
			standings[m.HomeTeam].Points += 1
			standings[m.AwayTeam].Draws++
			standings[m.AwayTeam].Points += 1
		}
		
		// Update goal difference
		standings[m.HomeTeam].GoalDiff = standings[m.HomeTeam].GoalsFor - standings[m.HomeTeam].GoalsAgainst
		standings[m.AwayTeam].GoalDiff = standings[m.AwayTeam].GoalsFor - standings[m.AwayTeam].GoalsAgainst
	}
	
	// Convert to slice and sort
	result := make([]data.CompetitionStandings, 0, len(standings))
	for _, s := range standings {
		result = append(result, *s)
	}
	
	// Sort by points (descending), then goal difference (descending), then goals for (descending)
	sort.Slice(result, func(i, j int) bool {
		if result[i].Points != result[j].Points {
			return result[i].Points > result[j].Points
		}
		if result[i].GoalDiff != result[j].GoalDiff {
			return result[i].GoalDiff > result[j].GoalDiff
		}
		return result[i].GoalsFor > result[j].GoalsFor
	})
	
	return result
}

// GetTopScorers returns top scorers from a competition
func (s *MCPServer) GetTopScorers(competition, season string, limit int) ([]map[string]interface{}, error) {
	// For this dataset, we'll estimate based on team goals
	// In a real implementation, this would use player-goal associations
	
	matches := s.loader.GetAllMatches()
	teamGoals := make(map[string]int)
	
	for _, m := range matches {
		if m.Competition != competition {
			continue
		}
		if season != "" && m.Season != season {
			continue
		}
		
		teamGoals[m.HomeTeam] += m.HomeGoals
		teamGoals[m.AwayTeam] += m.AwayGoals
	}
	
	// Sort teams by goals
	type teamScore struct {
		team  string
		goals int
	}
	
	var scores []teamScore
	for team, goals := range teamGoals {
		scores = append(scores, teamScore{team, goals})
	}
	
	sort.Slice(scores, func(i, j int) bool {
		return scores[i].goals > scores[j].goals
	})
	
	result := make([]map[string]interface{}, 0, limit)
	for i := 0; i < len(scores) && i < limit; i++ {
		result = append(result, map[string]interface{}{
			"team":  scores[i].team,
			"goals": scores[i].goals,
		})
	}
	
	return result, nil
}

// GetBiggestWins returns matches with largest goal differences
func (s *MCPServer) GetBiggestWins(limit int) ([]data.Match, error) {
	matches := s.loader.GetAllMatches()
	
	// Sort by goal difference
	sort.Slice(matches, func(i, j int) bool {
		diffI := abs(matches[i].HomeGoals - matches[i].AwayGoals)
		diffJ := abs(matches[j].HomeGoals - matches[j].AwayGoals)
		return diffI > diffJ
	})
	
	if len(matches) > limit {
		matches = matches[:limit]
	}
	
	return matches, nil
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// GetAverageGoals returns average goals per match
func (s *MCPServer) GetAverageGoals(competition, season string) (float64, error) {
	matches := s.loader.GetAllMatches()
	totalGoals := 0
	count := 0
	
	for _, m := range matches {
		if competition != "" && m.Competition != competition {
			continue
		}
		if season != "" && m.Season != season {
			continue
		}
		
		totalGoals += m.HomeGoals + m.AwayGoals
		count++
	}
	
	if count == 0 {
		return 0, fmt.Errorf("no matches found")
	}
	
	return float64(totalGoals) / float64(count), nil
}

// GetHomeWinRate returns home win rate
func (s *MCPServer) GetHomeWinRate(competition, season string) (float64, error) {
	matches := s.loader.GetAllMatches()
	homeWins := 0
	total := 0
	
	for _, m := range matches {
		if competition != "" && m.Competition != competition {
			continue
		}
		if season != "" && m.Season != season {
			continue
		}
		
		total++
		if m.HomeGoals > m.AwayGoals {
			homeWins++
		}
	}
	
	if total == 0 {
		return 0, fmt.Errorf("no matches found")
	}
	
	return float64(homeWins) / float64(total) * 100, nil
}

// GetRecentMatches returns recent matches
func (s *MCPServer) GetRecentMatches(limit int) ([]data.Match, error) {
	matches := s.loader.GetAllMatches()
	
	// Sort by date (descending)
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date > matches[j].Date
	})
	
	if len(matches) > limit {
		matches = matches[:limit]
	}
	
	return matches, nil
}

// GetLastMatchBetweenTeams returns the most recent match between two teams
func (s *MCPServer) GetLastMatchBetweenTeams(team1, team2 string) (*data.Match, error) {
	matches := s.loader.GetMatchesByTeams(team1, team2)
	
	if len(matches) == 0 {
		return nil, fmt.Errorf("no matches found between %s and %s", team1, team2)
	}
	
	// Sort by date descending
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date > matches[j].Date
	})
	
	return &matches[0], nil
}

// GetMatchesByDateRange returns matches within a date range
func (s *MCPServer) GetMatchesByDateRange(startDate, endDate string) ([]data.Match, error) {
	matches := s.loader.GetAllMatches()
	var result []data.Match
	
	for _, m := range matches {
		if m.Date >= startDate && m.Date <= endDate {
			result = append(result, m)
		}
	}
	
	if len(result) == 0 {
		return nil, fmt.Errorf("no matches found between %s and %s", startDate, endDate)
	}
	
	return result, nil
}

// SearchPlayers searches players by name
func (s *MCPServer) SearchPlayers(name string) ([]data.Player, error) {
	players := s.loader.GetPlayersByName(name)
	if len(players) == 0 {
		return nil, fmt.Errorf("no players found matching %s", name)
	}
	return players, nil
}

// GetPlayersByClub returns players by club
func (s *MCPServer) GetPlayersByClub(club string) ([]data.Player, error) {
	players := s.loader.GetPlayersByClub(club)
	if len(players) == 0 {
		return nil, fmt.Errorf("no players found at %s", club)
	}
	return players, nil
}

// GetPlayersByNationality returns players by nationality
func (s *MCPServer) GetPlayersByNationality(nationality string) ([]data.Player, error) {
	var players []data.Player
	for _, p := range s.loader.GetPlayers() {
		if strings.Contains(strings.ToLower(p.Nationality), strings.ToLower(nationality)) {
			players = append(players, p)
		}
	}
	if len(players) == 0 {
		return nil, fmt.Errorf("no players found for nationality %s", nationality)
	}
	return players, nil
}

// GetBrazilianPlayers returns all Brazilian players
func (s *MCPServer) GetBrazilianPlayers() ([]data.Player, error) {
	players := s.loader.GetBrazilianPlayers()
	if len(players) == 0 {
		return nil, fmt.Errorf("no Brazilian players found")
	}
	return players, nil
}

// GetTopPlayers returns top rated players
func (s *MCPServer) GetTopPlayers(limit int) ([]data.Player, error) {
	players := s.loader.GetBrazilianPlayersByRating(limit)
	if len(players) == 0 {
		return nil, fmt.Errorf("no players found")
	}
	return players, nil
}

// GetPlayersByPosition returns players by position
func (s *MCPServer) GetPlayersByPosition(position string) ([]data.Player, error) {
	players := s.loader.GetPlayersByPosition(position)
	if len(players) == 0 {
		return nil, fmt.Errorf("no players found for position %s", position)
	}
	return players, nil
}

// GetPlayerStats returns detailed stats for a player
func (s *MCPServer) GetPlayerStats(playerID int) (*data.Player, error) {
	for _, p := range s.loader.GetPlayers() {
		if p.ID == playerID {
			return &p, nil
		}
	}
	return nil, fmt.Errorf("player with ID %d not found", playerID)
}

// GetPlayers returns all players
func (s *MCPServer) GetPlayers() []data.Player {
	return s.loader.GetPlayers()
}

// GetPlayerCount returns total player count
func (s *MCPServer) GetPlayerCount() int {
	return s.loader.TotalPlayers()
}
