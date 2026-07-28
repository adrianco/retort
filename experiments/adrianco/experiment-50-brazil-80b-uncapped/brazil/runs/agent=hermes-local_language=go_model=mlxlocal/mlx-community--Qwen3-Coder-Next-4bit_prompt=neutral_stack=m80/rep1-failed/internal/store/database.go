package store

import (
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/models"
)

// Database represents the soccer data database
type Database struct {
	loader *DataLoader
}

// NewDatabase creates a new Database instance
func NewDatabase(loader *DataLoader) *Database {
	return &Database{loader: loader}
}

// LoadData loads all data from CSV files
func LoadData(dataPath string) (*Database, error) {
	loader := NewDataLoader(dataPath)
	err := loader.LoadAll()
	if err != nil {
		return nil, err
	}
	return NewDatabase(loader), nil
}

// MatchCount returns the number of matches in the database
func (db *Database) MatchCount() int {
	return db.loader.MatchCount()
}

// PlayerCount returns the number of players in the database
func (db *Database) PlayerCount() int {
	return db.loader.PlayerCount()
}

// FindMatchesByTeams finds matches where either team played
func (db *Database) FindMatchesByTeams(team1, team2 string) []models.Match {
	team1 = normalizeTeamName(team1)
	team2 = normalizeTeamName(team2)

	var matches []models.Match
	for _, match := range db.loader.matches {
		if (match.HomeTeam == team1 && match.AwayTeam == team2) ||
			(match.HomeTeam == team2 && match.AwayTeam == team1) {
			matches = append(matches, match)
		}
	}
	return matches
}

// FindMatchesByTeam finds all matches for a specific team
func (db *Database) FindMatchesByTeam(team string, season int) []models.Match {
	team = normalizeTeamName(team)

	var matches []models.Match
	for _, match := range db.loader.matches {
		if match.HomeTeam == team || match.AwayTeam == team {
			if season > 0 && match.Season != season {
				continue
			}
			matches = append(matches, match)
		}
	}
	return matches
}

// FindMatchesByDateRange finds matches within a date range
func (db *Database) FindMatchesByDateRange(start, end string) []models.Match {
	// Parse dates
	var startDate, endDate time.Time
	var err1, err2 error
	if start != "" {
		startDate, err1 = time.Parse("2006-01-02", start)
		if err1 != nil {
			startDate, err1 = time.Parse("02/01/2006", start)
		}
	}
	if end != "" {
		endDate, err2 = time.Parse("2006-01-02", end)
		if err2 != nil {
			endDate, err2 = time.Parse("02/01/2006", end)
		}
	}

	var matches []models.Match
	for _, match := range db.loader.matches {
		if startDate.IsZero() && endDate.IsZero() {
			matches = append(matches, match)
			continue
		}
		if !startDate.IsZero() && match.Datetime.Before(startDate) {
			continue
		}
		if !endDate.IsZero() && match.Datetime.After(endDate) {
			continue
		}
		matches = append(matches, match)
	}
	return matches
}

// FindMatchesByCompetition finds matches by competition
func (db *Database) FindMatchesByCompetition(competition string) []models.Match {
	competition = strings.ToLower(competition)
	var matches []models.Match
	for _, match := range db.loader.matches {
		tournament := strings.ToLower(match.Tournament)
		// Check tournament field first
		if tournament != "" && strings.Contains(tournament, competition) {
			matches = append(matches, match)
			continue
		}
		// Check stage for Libertadores
		if match.Stage != "" && strings.Contains(strings.ToLower(match.Stage), competition) {
			matches = append(matches, match)
			continue
		}
		// Check date range for Brasileirão (May-Oct)
		if competition == "brasileirão" || competition == "brasileirao" {
			if match.Season > 0 && !strings.Contains(strings.ToLower(match.Tournament), "copa") &&
				!strings.Contains(strings.ToLower(match.Tournament), "libertadores") {
				matches = append(matches, match)
			}
		}
	}
	return matches
}

// FindMatchesBySeason finds matches for a specific season
func (db *Database) FindMatchesBySeason(season int) []models.Match {
	var matches []models.Match
	for _, match := range db.loader.matches {
		if match.Season == season {
			matches = append(matches, match)
		}
	}
	return matches
}

// FindPlayerByName finds a player by name
func (db *Database) FindPlayerByName(name string) *models.Player {
	name = strings.ToLower(name)
	for _, player := range db.loader.players {
		if strings.Contains(strings.ToLower(player.Name), name) {
			return &player
		}
	}
	return nil
}

// FindPlayersByName finds multiple players by name
func (db *Database) FindPlayersByName(name string) []models.Player {
	name = strings.ToLower(name)
	var players []models.Player
	for _, player := range db.loader.players {
		if strings.Contains(strings.ToLower(player.Name), name) {
			players = append(players, player)
		}
	}
	return players
}

// FindPlayersByNationality finds players by nationality
func (db *Database) FindPlayersByNationality(nationality string) []models.Player {
	nationality = strings.ToLower(nationality)
	var players []models.Player
	for _, player := range db.loader.players {
		if strings.Contains(strings.ToLower(player.Nationality), nationality) {
			players = append(players, player)
		}
	}
	return players
}

// FindPlayersByClub finds players by club
func (db *Database) FindPlayersByClub(club string) []models.Player {
	club = normalizeTeamName(club)
	var players []models.Player
	for _, player := range db.loader.players {
		if player.Club == club {
			players = append(players, player)
		}
	}
	return players
}

// FindPlayersByPosition finds players by position
func (db *Database) FindPlayersByPosition(position string) []models.Player {
	position = strings.ToUpper(position)
	var players []models.Player
	for _, player := range db.loader.players {
		if strings.Contains(strings.ToUpper(player.Position), position) {
			players = append(players, player)
		}
	}
	return players
}

// GetTeamStats calculates statistics for a team
func (db *Database) GetTeamStats(team string, season int) *models.TeamStats {
	team = normalizeTeamName(team)
	stats := &models.TeamStats{TeamName: team}

	for _, match := range db.loader.matches {
		if match.Season > 0 && match.Season != season {
			continue
		}

		if match.HomeTeam == team {
			stats.Matches++
			stats.GoalsFor += match.HomeGoal
			stats.GoalsAgainst += match.AwayGoal
			stats.HomeMatches++
			if match.HomeGoal > match.AwayGoal {
				stats.Wins++
				stats.HomeWins++
			} else if match.HomeGoal == match.AwayGoal {
				stats.Draws++
				stats.HomeDraws++
			} else {
				stats.Losses++
				stats.HomeLosses++
			}
		} else if match.AwayTeam == team {
			stats.Matches++
			stats.GoalsFor += match.AwayGoal
			stats.GoalsAgainst += match.HomeGoal
			stats.AwayMatches++
			if match.AwayGoal > match.HomeGoal {
				stats.Wins++
				stats.AwayWins++
			} else if match.AwayGoal == match.HomeGoal {
				stats.Draws++
				stats.AwayDraws++
			} else {
				stats.Losses++
				stats.AwayLosses++
			}
		}
	}

	stats.Points = stats.Wins*3 + stats.Draws
	if stats.Matches > 0 {
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}

	return stats
}

// GetHeadToHead calculates head-to-head between two teams
func (db *Database) GetHeadToHead(team1, team2 string) *models.HeadToHead {
	team1 = normalizeTeamName(team1)
	team2 = normalizeTeamName(team2)
	h2h := &models.HeadToHead{Team1: team1, Team2: team2}

	for _, match := range db.loader.matches {
		if (match.HomeTeam == team1 && match.AwayTeam == team2) ||
			(match.HomeTeam == team2 && match.AwayTeam == team1) {
			h2h.Matches++
			h2h.Team1Goals += match.HomeGoal
			h2h.Team2Goals += match.AwayGoal

			if match.HomeTeam == team1 {
				if match.HomeGoal > match.AwayGoal {
					h2h.Team1Wins++
				} else if match.HomeGoal < match.AwayGoal {
					h2h.Team2Wins++
				} else {
					h2h.Draws++
				}
			} else {
				if match.AwayGoal > match.HomeGoal {
					h2h.Team1Wins++
				} else if match.AwayGoal < match.HomeGoal {
					h2h.Team2Wins++
				} else {
					h2h.Draws++
				}
			}
		}
	}

	return h2h
}

// GetBigWins finds matches with large goal differences
func (db *Database) GetBigWins(threshold int) []models.BigWin {
	var bigWins []models.BigWin

	for _, match := range db.loader.matches {
		goalDiff := match.HomeGoal - match.AwayGoal
		if goalDiff < 0 {
			goalDiff = -goalDiff
		}

		if goalDiff >= threshold {
			bigWin := models.BigWin{
				Date:       match.Datetime,
				Tournament: match.Tournament,
				GoalDiff:   goalDiff,
			}

			if match.HomeGoal > match.AwayGoal {
				bigWin.HomeTeam = match.HomeTeam
				bigWin.AwayTeam = match.AwayTeam
				bigWin.HomeGoal = match.HomeGoal
				bigWin.AwayGoal = match.AwayGoal
			} else {
				bigWin.HomeTeam = match.AwayTeam
				bigWin.AwayTeam = match.HomeTeam
				bigWin.HomeGoal = match.AwayGoal
				bigWin.AwayGoal = match.HomeGoal
			}

			bigWins = append(bigWins, bigWin)
		}
	}

	// Sort by goal difference (descending)
	for i := 0; i < len(bigWins)-1; i++ {
		for j := i + 1; j < len(bigWins); j++ {
			if bigWins[j].GoalDiff > bigWins[i].GoalDiff {
				bigWins[i], bigWins[j] = bigWins[j], bigWins[i]
			}
		}
	}

	return bigWins
}

// CalculateLeagueStandings calculates standings for a league
func (db *Database) CalculateLeagueStandings(competition string, season int) []models.CompetitionResult {
	var standings []models.CompetitionResult
	teamStats := make(map[string]*models.TeamStats)

	for _, match := range db.loader.matches {
		if match.Season != season {
			continue
		}

		// Check if this is the right competition
		isCorrectCompetition := false
		if competition == "brasileirão" || competition == "brasileirao" {
			isCorrectCompetition = strings.Contains(strings.ToLower(match.Tournament), "brasileirao")
		} else {
			isCorrectCompetition = strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(competition))
		}

		if !isCorrectCompetition && match.Tournament != "" {
			continue
		}

		// Initialize team stats if needed
		for _, team := range []string{match.HomeTeam, match.AwayTeam} {
			if teamStats[team] == nil {
				teamStats[team] = &models.TeamStats{TeamName: team}
			}
		}

		// Update home team stats
		homeStats := teamStats[match.HomeTeam]
		homeStats.Matches++
		homeStats.GoalsFor += match.HomeGoal
		homeStats.GoalsAgainst += match.AwayGoal

		if match.HomeGoal > match.AwayGoal {
			homeStats.Wins++
			homeStats.Points += 3
		} else if match.HomeGoal == match.AwayGoal {
			homeStats.Draws++
			homeStats.Points += 1
		} else {
			homeStats.Losses++
		}

		// Update away team stats
		awayStats := teamStats[match.AwayTeam]
		awayStats.Matches++
		awayStats.GoalsFor += match.AwayGoal
		awayStats.GoalsAgainst += match.HomeGoal

		if match.AwayGoal > match.HomeGoal {
			awayStats.Wins++
			awayStats.Points += 3
		} else if match.AwayGoal == match.HomeGoal {
			awayStats.Draws++
			awayStats.Points += 1
		} else {
			awayStats.Losses++
		}
	}

	// Convert map to slice for sorting
	for _, stats := range teamStats {
		if stats.Matches > 0 {
			standings = append(standings, models.CompetitionResult{
				TeamName:     stats.TeamName,
				Matches:      stats.Matches,
				Wins:         stats.Wins,
				Draws:        stats.Draws,
				Losses:       stats.Losses,
				GoalsFor:     stats.GoalsFor,
				GoalsAgainst: stats.GoalsAgainst,
				Points:       stats.Points,
			})
		}
	}

	// Sort by points (descending), then goal difference, then goals for
	for i := 0; i < len(standings)-1; i++ {
		for j := i + 1; j < len(standings); j++ {
			swap := false
			if standings[j].Points > standings[i].Points {
				swap = true
			} else if standings[j].Points == standings[i].Points {
				jGD := standings[j].GoalsFor - standings[j].GoalsAgainst
				iGD := standings[i].GoalsFor - standings[i].GoalsAgainst
				if jGD > iGD {
					swap = true
				} else if jGD == iGD && standings[j].GoalsFor > standings[i].GoalsFor {
					swap = true
				}
			}

			if swap {
				standings[i], standings[j] = standings[j], standings[i]
			}
		}
	}

	return standings
}

// GetAverageGoalsPerMatch calculates average goals per match
func (db *Database) GetAverageGoalsPerMatch(competition string, season int) float64 {
	var totalGoals, matchCount int

	for _, match := range db.loader.matches {
		if season > 0 && match.Season != season {
			continue
		}

		if competition != "" {
			if strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(competition)) {
				totalGoals += match.HomeGoal + match.AwayGoal
				matchCount++
			}
		} else {
			totalGoals += match.HomeGoal + match.AwayGoal
			matchCount++
		}
	}

	if matchCount == 0 {
		return 0
	}

	return float64(totalGoals) / float64(matchCount)
}

// GetHomeWinRate calculates the home win rate
func (db *Database) GetHomeWinRate(competition string, season int) float64 {
	var homeWins, totalMatches int

	for _, match := range db.loader.matches {
		if season > 0 && match.Season != season {
			continue
		}

		if competition != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(competition)) {
			continue
		}

		totalMatches++
		if match.HomeGoal > match.AwayGoal {
			homeWins++
		}
	}

	if totalMatches == 0 {
		return 0
	}

	return float64(homeWins) / float64(totalMatches) * 100
}

// GetTopScorers finds the top scoring players
func (db *Database) GetTopScorers(limit int) []models.Player {
	// Sort players by overall rating (descending)
	players := make([]models.Player, len(db.loader.players))
	copy(players, db.loader.players)

	for i := 0; i < len(players)-1; i++ {
		for j := i + 1; j < len(players); j++ {
			if players[j].Overall > players[i].Overall {
				players[i], players[j] = players[j], players[i]
			}
		}
	}

	if limit > len(players) {
		limit = len(players)
	}

	return players[:limit]
}

// GetBrazilianPlayers finds all Brazilian players
func (db *Database) GetBrazilianPlayers() []models.Player {
	var brazilianPlayers []models.Player
	for _, player := range db.loader.players {
		if strings.Contains(strings.ToLower(player.Nationality), "brazil") ||
			strings.Contains(strings.ToLower(player.Nationality), "brasil") ||
			strings.Contains(strings.ToLower(player.Nationality), "brazillian") {
			brazilianPlayers = append(brazilianPlayers, player)
		}
	}
	return brazilianPlayers
}

// GetTopBrazilianPlayers gets the top-rated Brazilian players
func (db *Database) GetTopBrazilianPlayers(limit int) []models.Player {
	brazilianPlayers := db.GetBrazilianPlayers()

	// Sort by overall rating
	for i := 0; i < len(brazilianPlayers)-1; i++ {
		for j := i + 1; j < len(brazilianPlayers); j++ {
			if brazilianPlayers[j].Overall > brazilianPlayers[i].Overall {
				brazilianPlayers[i], brazilianPlayers[j] = brazilianPlayers[j], brazilianPlayers[i]
			}
		}
	}

	if limit > len(brazilianPlayers) {
		limit = len(brazilianPlayers)
	}

	return brazilianPlayers[:limit]
}

// GetPlayersByClub gets all players for a specific club
func (db *Database) GetPlayersByClub(club string) []models.Player {
	club = normalizeTeamName(club)
	var players []models.Player
	for _, player := range db.loader.players {
		if player.Club == club {
			players = append(players, player)
		}
	}
	return players
}

// GetBrazilianPlayersByClub gets Brazilian players grouped by club
func (db *Database) GetBrazilianPlayersByClub() map[string][]models.Player {
	clubPlayers := make(map[string][]models.Player)
	for _, player := range db.loader.players {
		if strings.Contains(strings.ToLower(player.Nationality), "brazil") ||
			strings.Contains(strings.ToLower(player.Nationality), "brasil") ||
			strings.Contains(strings.ToLower(player.Nationality), "brazillian") {
			clubPlayers[player.Club] = append(clubPlayers[player.Club], player)
		}
	}
	return clubPlayers
}
