package server

import (
	"fmt"
	"sort"
)

// MCP server implementation for Brazilian Soccer

// Server represents the MCP server
type Server struct {
	store *DataStore
}

// NewServer creates a new MCP server
func NewServer() *Server {
	store := &DataStore{}
	return &Server{store: store}
}

// Initialize loads all data from CSV files
func (s *Server) Initialize() error {
	return s.store.LoadAllData()
}

// Query processes a natural language query
func (s *Server) Query(query string) QueryResult {
	qe := NewQueryEngine(s.store)
	return qe.Query(query)
}

// GetMatchesByTeams finds matches between two teams
func (s *Server) GetMatchesByTeams(team1, team2 string) []Match {
	return s.store.GetMatchesByTeams(team1, team2, 20)
}

// GetTeamStats calculates statistics for a team
func (s *Server) GetTeamStats(team string, season int) TeamStats {
	return s.store.GetTeamStats(team, season, "")
}

// GetPlayerByName searches for players by name
func (s *Server) GetPlayerByName(name string) []Player {
	return s.store.GetPlayerByName(name, 20)
}

// GetPlayersByClub gets all players from a specific club
func (s *Server) GetPlayersByClub(club string) []Player {
	return s.store.GetPlayersByClub(club)
}

// GetPlayersByNationality gets players from a specific nationality
func (s *Server) GetPlayersByNationality(nationality string) []Player {
	return s.store.GetPlayersByNationality(nationality)
}

// GetBrasileiraoTable calculates the Brasileirão league table for a season
func (s *Server) GetBrasileiraoTable(season int) CompetitionTable {
	qe := NewQueryEngine(s.store)
	return qe.calculateLeagueTable("Brasileirão", season)
}

// GetTeamList returns all unique teams in the data
func (s *Server) GetTeamList() []string {
	return s.store.GetTeamList()
}

// GetHeadToHead calculates head-to-head statistics between two teams
func (s *Server) GetHeadToHead(team1, team2 string) (int, int, int) {
	return s.store.GetHeadToHead(team1, team2)
}

// GetMatchHistory gets the match history for a team
func (s *Server) GetMatchHistory(team string) []Match {
	return s.store.GetTeamMatchHistory(team, 10)
}

// GetStatisticalAnalysis calculates statistical analysis
func (s *Server) GetStatisticalAnalysis() QueryResult {
	// Calculate average goals
	allMatches := append(append(append(append(
		s.store.BrasileiraoMatches,
		s.store.CopaDoBrasilMatches...),
		s.store.CopaLibertadoresMatches...),
		s.store.BRFootballMatches...),
		s.store.NovoCampeonatoMatches...)

	if len(allMatches) == 0 {
		return QueryResult{
			Message: "No matches found in the dataset",
			Count:   0,
		}
	}

	totalGoals := 0
	for _, match := range allMatches {
		totalGoals += match.HomeGoal + match.AwayGoal
	}

	avgGoals := float64(totalGoals) / float64(len(allMatches))

	// Count home wins, away wins, draws
	homeWins := 0
	awayWins := 0
	draws := 0
	for _, match := range allMatches {
		if match.HomeGoal > match.AwayGoal {
			homeWins++
		} else if match.HomeGoal < match.AwayGoal {
			awayWins++
		} else {
			draws++
		}
	}

	homeWinRate := float64(homeWins) / float64(len(allMatches)) * 100

	message := "Statistical Analysis:\n"
	message += fmt.Sprintf("- Average goals per match: %.2f\n", avgGoals)
	message += fmt.Sprintf("- Home wins: %d (%.1f%%)\n", homeWins, homeWinRate)
	message += fmt.Sprintf("- Draws: %d\n", draws)
	message += fmt.Sprintf("- Away wins: %d\n", awayWins)

	return QueryResult{
		Message: message,
		Count:   1,
	}
}

// GetBiggestWins finds the biggest wins in the dataset
func (s *Server) GetBiggestWins() QueryResult {
	allMatches := append(append(append(append(
		s.store.BrasileiraoMatches,
		s.store.CopaDoBrasilMatches...),
		s.store.CopaLibertadoresMatches...),
		s.store.BRFootballMatches...),
		s.store.NovoCampeonatoMatches...)

	if len(allMatches) == 0 {
		return QueryResult{
			Message: "No matches found in the dataset",
			Count:   0,
		}
	}

	// Calculate goal difference for each match
	type matchDiff struct {
		match Match
		diff  int
	}

	var diffs []matchDiff
	for _, match := range allMatches {
		diff := intAbs(match.HomeGoal - match.AwayGoal)
		diffs = append(diffs, matchDiff{match: match, diff: diff})
	}

	// Sort by goal difference descending
	sort.Slice(diffs, func(i, j int) bool {
		return diffs[i].diff > diffs[j].diff
	})

	message := "Biggest victories in dataset:\n"
	count := 0
	for _, d := range diffs {
		if d.diff > 0 {
			message += fmt.Sprintf("- %s: %s %d-%d %s (%s)\n",
				d.match.Datetime.Format("2006-01-02"),
				d.match.HomeTeam, d.match.HomeGoal, d.match.AwayGoal, d.match.AwayTeam,
				getCompetitionName(&d.match))
			count++
			if count >= 10 {
				break
			}
		}
	}

	return QueryResult{
		Message: message,
		Count:   count,
	}
}

// GetBestHomeRecord finds teams with the best home records
func (s *Server) GetBestHomeRecord() QueryResult {
	allMatches := append(append(append(append(
		s.store.BrasileiraoMatches,
		s.store.CopaDoBrasilMatches...),
		s.store.CopaLibertadoresMatches...),
		s.store.BRFootballMatches...),
		s.store.NovoCampeonatoMatches...)

	teamStats := make(map[string]*TeamStats)

	for _, match := range allMatches {
		homeTeam := NormalizeTeamName(match.HomeTeam)

		if _, exists := teamStats[homeTeam]; !exists {
			teamStats[homeTeam] = &TeamStats{TeamName: homeTeam}
		}

		stats := teamStats[homeTeam]
		stats.HomeMatches++
		stats.HomeGF += match.HomeGoal
		stats.HomeGA += match.AwayGoal

		if match.HomeGoal > match.AwayGoal {
			stats.HomeWins++
			stats.Points += 3
		} else if match.HomeGoal == match.AwayGoal {
			stats.HomeDraws++
			stats.Points += 1
		} else {
			stats.HomeLosses++
		}
	}

	// Convert to slice and sort
	var teams []TeamStats
	for _, stats := range teamStats {
		teams = append(teams, *stats)
	}

	sort.Slice(teams, func(i, j int) bool {
		return float64(teams[i].HomeWins)/float64(teams[i].HomeMatches) >
			float64(teams[j].HomeWins)/float64(teams[j].HomeMatches)
	})

	message := "Teams with best home records:\n"
	count := 0
	for _, stats := range teams {
		if stats.HomeMatches > 0 {
			winRate := float64(stats.HomeWins) / float64(stats.HomeMatches) * 100
			message += fmt.Sprintf("- %s: %d wins in %d home matches (%.1f%% win rate)\n",
				stats.TeamName, stats.HomeWins, stats.HomeMatches, winRate)
			count++
			if count >= 10 {
				break
			}
		}
	}

	return QueryResult{
		Message: message,
		Count:   count,
	}
}

// FindTeamByName finds a team in the data by name
func (s *Server) FindTeamByName(name string) []string {
	return s.store.FindTeamByName(name)
}

// GetTeamStatsForSeason calculates team statistics for a specific season
func (s *Server) GetTeamStatsForSeason(team string, season int) TeamStats {
	return s.store.GetTeamStats(team, season, "")
}

// GetTeamStatsForCompetition calculates team statistics for a specific competition
func (s *Server) GetTeamStatsForCompetition(team string, competition string) TeamStats {
	return s.store.GetTeamStats(team, 0, competition)
}

// GetPlayerCount returns the total number of players in the dataset
func (s *Server) GetPlayerCount() int {
	return len(s.store.Players)
}

// GetMatchCount returns the total number of matches in the dataset
func (s *Server) GetMatchCount() int {
	return len(s.store.BrasileiraoMatches) +
		len(s.store.CopaDoBrasilMatches) +
		len(s.store.CopaLibertadoresMatches) +
		len(s.store.BRFootballMatches) +
		len(s.store.NovoCampeonatoMatches)
}

// GetTeamCount returns the total number of unique teams in the dataset
func (s *Server) GetTeamCount() int {
	return len(s.store.GetTeamList())
}

// GetPlayersByPosition gets players by position
func (s *Server) GetPlayersByPosition(position string) []Player {
	return s.store.GetPlayersByPosition(position)
}

// GetPlayersByNationalityCount returns the count of players from a nationality
func (s *Server) GetPlayersByNationalityCount(nationality string) int {
	players := s.store.GetPlayersByNationality(nationality)
	return len(players)
}

// GetBrazilianPlayers returns all Brazilian players
func (s *Server) GetBrazilianPlayers() []Player {
	return s.store.GetPlayersByNationality("Brazil")
}

// GetTopBrazilianPlayers returns the top Brazilian players by overall rating
func (s *Server) GetTopBrazilianPlayers(limit int) []Player {
	brazilianPlayers := s.store.GetPlayersByNationality("Brazil")
	if len(brazilianPlayers) > limit {
		return brazilianPlayers[:limit]
	}
	return brazilianPlayers
}

// GetPlayersByClubCount returns the count of players at a club
func (s *Server) GetPlayersByClubCount(club string) int {
	players := s.store.GetPlayersByClub(club)
	return len(players)
}

// GetTopPlayersByClub returns the top players at a club
func (s *Server) GetTopPlayersByClub(club string, limit int) []Player {
	players := s.store.GetPlayersByClub(club)
	if len(players) > limit {
		return players[:limit]
	}
	return players
}

// intAbs returns the absolute value of an integer
func intAbs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
