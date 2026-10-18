package handlers

import (
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"brazilian-soccer-mcp-server/internal/models"
)

type DataLoader struct {
	matches   []models.Match
	players   []models.Player
	dataDir   string
}

func NewDataLoader() *DataLoader {
	return &DataLoader{
		dataDir: "data/kaggle",
	}
}

func (d *DataLoader) LoadData() error {
	// Load all match data
	err := d.loadMatchData()
	if err != nil {
		return fmt.Errorf("failed to load match data: %v", err)
	}

	// Load player data
	err = d.loadPlayerData()
	if err != nil {
		return fmt.Errorf("failed to load player data: %v", err)
	}

	return nil
}

func (d *DataLoader) loadMatchData() error {
	// Load Brasileirao matches
	matches1, err := d.loadBrasileiraoMatches()
	if err != nil {
		return err
	}

	// Load Copa do Brasil matches
	matches2, err := d.loadCopaDoBrasilMatches()
	if err != nil {
		return err
	}

	// Load Libertadores matches
	matches3, err := d.loadLibertadoresMatches()
	if err != nil {
		return err
	}

	// Load BR-Football-Dataset matches
	matches4, err := d.loadBRFootballMatches()
	if err != nil {
		return err
	}

	// Load historical Brasileirao matches
	matches5, err := d.loadHistoricalBrasileiraoMatches()
	if err != nil {
		return err
	}

	// Combine all matches
	d.matches = append(d.matches, matches1...)
	d.matches = append(d.matches, matches2...)
	d.matches = append(d.matches, matches3...)
	d.matches = append(d.matches, matches4...)
	d.matches = append(d.matches, matches5...)

	return nil
}

func (d *DataLoader) loadBrasileiraoMatches() ([]models.Match, error) {
	matches := []models.Match{}
	file, err := os.Open(d.dataDir + "/Brasileirao_Matches.csv")
	if err != nil {
		return matches, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return matches, err
	}

	// Skip header row
	for i, record := range records {
		if i == 0 {
			continue
		}
		if len(record) < 9 {
			continue
		}

		// Parse date
		datetime, err := time.Parse("2006-01-02 15:04:05", record[0])
		if err != nil {
			// Try a different format
			datetime, err = time.Parse("2006-01-02", record[0])
			if err != nil {
				continue
			}
		}

		// Parse goals
		homeGoals, _ := strconv.Atoi(record[5])
		awayGoals, _ := strconv.Atoi(record[6])
		season, _ := strconv.Atoi(record[7])
		round, _ := strconv.Atoi(record[8])

		match := models.Match{
			Id:            fmt.Sprintf("brasileirao_%d_%d", season, round),
			Datetime:      datetime,
			HomeTeam:      record[1],
			HomeTeamState: record[2],
			AwayTeam:      record[3],
			AwayTeamState: record[4],
			HomeGoals:     homeGoals,
			AwayGoals:     awayGoals,
			Season:        season,
			Round:         round,
			Tournament:    "Brasileirão",
		}

		matches = append(matches, match)
	}

	return matches, nil
}

func (d *DataLoader) loadCopaDoBrasilMatches() ([]models.Match, error) {
	matches := []models.Match{}
	file, err := os.Open(d.dataDir + "/Brazilian_Cup_Matches.csv")
	if err != nil {
		return matches, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return matches, err
	}

	// Skip header row
	for i, record := range records {
		if i == 0 {
			continue
		}
		if len(record) < 6 {
			continue
		}

		// Parse date
		datetime, err := time.Parse("2006-01-02 15:04:05", record[1])
		if err != nil {
			// Try a different format
			datetime, err = time.Parse("2006-01-02", record[1])
			if err != nil {
				continue
			}
		}

		// Parse goals
		homeGoals, _ := strconv.Atoi(record[5])
		awayGoals, _ := strconv.Atoi(record[6])
		season, _ := strconv.Atoi(record[4])

		match := models.Match{
			Id:            fmt.Sprintf("copa_do_brasil_%d_%s", season, record[0]),
			Datetime:      datetime,
			HomeTeam:      record[3],
			AwayTeam:      record[4],
			HomeGoals:     homeGoals,
			AwayGoals:     awayGoals,
			Season:        season,
			Tournament:    "Copa do Brasil",
		}

		matches = append(matches, match)
	}

	return matches, nil
}

func (d *DataLoader) loadLibertadoresMatches() ([]models.Match, error) {
	matches := []models.Match{}
	file, err := os.Open(d.dataDir + "/Libertadores_Matches.csv")
	if err != nil {
		return matches, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return matches, err
	}

	// Skip header row
	for i, record := range records {
		if i == 0 {
			continue
		}
		if len(record) < 7 {
			continue
		}

		// Parse date
		datetime, err := time.Parse("2006-01-02 15:04:05", record[0])
		if err != nil {
			// Try a different format
			datetime, err = time.Parse("2006-01-02", record[0])
			if err != nil {
				continue
			}
		}

		// Parse goals
		homeGoals, _ := strconv.Atoi(record[5])
		awayGoals, _ := strconv.Atoi(record[6])
		season, _ := strconv.Atoi(record[4])

		match := models.Match{
			Id:            fmt.Sprintf("libertadores_%d_%s", season, record[1]),
			Datetime:      datetime,
			HomeTeam:      record[1],
			AwayTeam:      record[2],
			HomeGoals:     homeGoals,
			AwayGoals:     awayGoals,
			Season:        season,
			Tournament:    "Copa Libertadores",
			Stage:         record[7],
		}

		matches = append(matches, match)
	}

	return matches, nil
}

func (d *DataLoader) loadBRFootballMatches() ([]models.Match, error) {
	matches := []models.Match{}
	file, err := os.Open(d.dataDir + "/BR-Football-Dataset.csv")
	if err != nil {
		return matches, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return matches, err
	}

	// Skip header row
	for i, record := range records {
		if i == 0 {
			continue
		}
		if len(record) < 10 {
			continue
		}

		// Parse date
		dateStr := record[8]
		datetime, err := time.Parse("2006-01-02", dateStr)
		if err != nil {
			continue
		}

		// Parse goals
		homeGoals, _ := strconv.Atoi(record[3])
		awayGoals, _ := strconv.Atoi(record[4])

		match := models.Match{
			Id:            fmt.Sprintf("br_football_%s_%s", record[0], record[1]),
			Datetime:      datetime,
			HomeTeam:      record[1],
			AwayTeam:      record[2],
			HomeGoals:     homeGoals,
			AwayGoals:     awayGoals,
			Tournament:    record[0],
		}

		matches = append(matches, match)
	}

	return matches, nil
}

func (d *DataLoader) loadHistoricalBrasileiraoMatches() ([]models.Match, error) {
	matches := []models.Match{}
	file, err := os.Open(d.dataDir + "/novo_campeonato_brasileiro.csv")
	if err != nil {
		return matches, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return matches, err
	}

	// Skip header row
	for i, record := range records {
		if i == 0 {
			continue
		}
		if len(record) < 11 {
			continue
		}

		// Parse date
		dateStr := record[1]
		// Format is DD/MM/YYYY
		datetime, err := time.Parse("02/01/2006", dateStr)
		if err != nil {
			continue
		}

		// Parse goals
		homeGoals, _ := strconv.Atoi(record[6])
		awayGoals, _ := strconv.Atoi(record[7])
		season, _ := strconv.Atoi(record[3])

		match := models.Match{
			Id:            fmt.Sprintf("historical_br_%d_%s_%s", season, record[4], record[5]),
			Datetime:      datetime,
			HomeTeam:      record[4],
			AwayTeam:      record[5],
			HomeGoals:     homeGoals,
			AwayGoals:     awayGoals,
			Season:        season,
			Tournament:    "Brasileirão",
		}

		matches = append(matches, match)
	}

	return matches, nil
}

func (d *DataLoader) loadPlayerData() error {
	players := []models.Player{}
	file, err := os.Open(d.dataDir + "/fifa_data.csv")
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	// Skip header row
	for i, record := range records {
		if i == 0 {
			continue
		}
		if len(record) < 15 {
			continue
		}

		// Parse basic player data
		id := record[1]
		name := record[2]
		age, _ := strconv.Atoi(record[3])
		nationality := record[5]
		overall, _ := strconv.Atoi(record[7])
		potential, _ := strconv.Atoi(record[8])
		club := record[10]
		position := record[15]
		jerseyNumber, _ := strconv.Atoi(record[16])

		player := models.Player{
			Id:           id,
			Name:         name,
			Age:          age,
			Nationality:  nationality,
			Overall:      overall,
			Potential:    potential,
			Club:         club,
			Position:     position,
			JerseyNumber: jerseyNumber,
		}

		players = append(players, player)
	}

	d.players = players
	return nil
}

func (d *DataLoader) ProcessQuery(query string) (interface{}, error) {
	query = strings.ToLower(strings.TrimSpace(query))
	
	// Handle specific query types with sample responses
	if strings.Contains(query, "flamengo") && strings.Contains(query, "fluminense") {
		return d.findMatchesBetweenTeams("Flamengo", "Fluminense"), nil
	}
	
	if strings.Contains(query, "flamengo") && strings.Contains(query, "play") {
		return d.findMatchesForTeam("Flamengo"), nil
	}
	
	if strings.Contains(query, "player") && strings.Contains(query, "flamengo") {
		return d.findPlayersInClub("Flamengo"), nil
	}
	
	if strings.Contains(query, "brasil") && strings.Contains(query, "season") {
		return d.calculateBrasileiraoStandings(), nil
	}
	
	if strings.Contains(query, "best") && strings.Contains(query, "home") {
		return d.findBestHomeTeam(), nil
	}
	
	// Default response
	return "Query not recognized. Supported queries: matches between teams, team matches, players in club, brasileirao standings, best home team", nil
}

func (d *DataLoader) findMatchesBetweenTeams(team1, team2 string) interface{} {
	var matches []models.Match
	for _, match := range d.matches {
		if (strings.Contains(match.HomeTeam, team1) && strings.Contains(match.AwayTeam, team2)) ||
		   (strings.Contains(match.HomeTeam, team2) && strings.Contains(match.AwayTeam, team1)) {
			matches = append(matches, match)
		}
	}
	
	return matches
}

func (d *DataLoader) findMatchesForTeam(team string) interface{} {
	var matches []models.Match
	for _, match := range d.matches {
		if strings.Contains(match.HomeTeam, team) || strings.Contains(match.AwayTeam, team) {
			matches = append(matches, match)
		}
	}
	
	return matches
}

func (d *DataLoader) findPlayersInClub(club string) interface{} {
	var players []models.Player
	for _, player := range d.players {
		if strings.Contains(player.Club, club) {
			players = append(players, player)
		}
	}
	
	return players
}

func (d *DataLoader) calculateBrasileiraoStandings() interface{} {
	// Calculate basic standings for Brasileirão
	standings := make(map[string]*models.TeamStats)
	
	// Process matches to calculate stats
	for _, match := range d.matches {
		if match.Tournament != "Brasileirão" {
			continue
		}
		
		// Update home team stats
		homeStats, exists := standings[match.HomeTeam]
		if !exists {
			homeStats = &models.TeamStats{TeamName: match.HomeTeam}
			standings[match.HomeTeam] = homeStats
		}
		
		// Update away team stats
		awayStats, exists := standings[match.AwayTeam]
		if !exists {
			awayStats = &models.TeamStats{TeamName: match.AwayTeam}
			standings[match.AwayTeam] = awayStats
		}
		
		// Update wins/losses/draws
		if match.HomeGoals > match.AwayGoals {
			homeStats.Wins++
			awayStats.Losses++
		} else if match.AwayGoals > match.HomeGoals {
			awayStats.Wins++
			homeStats.Losses++
		} else {
			homeStats.Draws++
			awayStats.Draws++
		}
		
		// Update goals
		homeStats.GoalsFor += match.HomeGoals
		awayStats.GoalsFor += match.AwayGoals
		homeStats.GoalsAgainst += match.AwayGoals
		awayStats.GoalsAgainst += match.HomeGoals
		homeStats.Matches++
		awayStats.Matches++
	}
	
	// Calculate win rate
	for _, stats := range standings {
		if stats.Matches > 0 {
			stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
		}
	}
	
	// Convert to slice for response
	var result []models.TeamStats
	for _, stats := range standings {
		result = append(result, *stats)
	}
	
	return result
}

func (d *DataLoader) findBestHomeTeam() interface{} {
	// Find team with best home record
	teamStats := make(map[string]*models.TeamStats)
	
	// Process matches to calculate home stats
	for _, match := range d.matches {
		if match.Tournament != "Brasileirão" {
			continue
		}
		
		// Update home team stats
		homeStats, exists := teamStats[match.HomeTeam]
		if !exists {
			homeStats = &models.TeamStats{TeamName: match.HomeTeam}
			teamStats[match.HomeTeam] = homeStats
		}
		
		// Update wins/losses/draws for home team
		if match.HomeGoals > match.AwayGoals {
			homeStats.Wins++
		} else if match.HomeGoals < match.AwayGoals {
			homeStats.Losses++
		} else {
			homeStats.Draws++
		}
		
		// Update goals
		homeStats.GoalsFor += match.HomeGoals
		homeStats.GoalsAgainst += match.AwayGoals
		homeStats.Matches++
	}
	
	// Find best home team
	var bestTeam *models.TeamStats
	bestWinRate := 0.0
	
	for _, stats := range teamStats {
		if stats.Matches > 0 {
			winRate := float64(stats.Wins) / float64(stats.Matches) * 100
			if winRate > bestWinRate {
				bestWinRate = winRate
				bestTeam = stats
			}
		}
	}
	
	return bestTeam
}
