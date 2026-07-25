package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

// Player represents a soccer player
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Club         string
	Position     string
	JerseyNumber int
	Height       float64
	Weight       float64
	Overall      int
	Potential    int
	// Skill ratings
	Crossing      int
	Finishing     int
	Dribbling     int
	Defending   int
	Physicality   int
	Passing       int
	Shooting      int
	Goalkeeping   int
	// Multiple position ratings
	Positions []string
}

// PlayerDataStore manages player data from CSV files
type PlayerDataStore struct {
	players []Player
}

// NewPlayerDataStore creates a new player data store
func NewPlayerDataStore(dataDir string) *PlayerDataStore {
	return &PlayerDataStore{
		players: []Player{},
	}
}

// LoadCSV loads player data from CSV
func (s *PlayerDataStore) LoadCSV(filePath string) error {
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in file")
	}

	loaded, err := s.loadFIFAData(records)
	if err != nil {
		return err
	}

	fmt.Printf("  Loaded %d players from FIFA data\n", loaded)
	return nil
}

// loadFIFAData loads FIFA player data
func (s *PlayerDataStore) loadFIFAData(records [][]string) (int, error) {
	headers := records[0]
	colMap := make(map[string]int)
	for i, h := range headers {
		colMap[strings.TrimSpace(strings.ToLower(h))] = i
	}

	var loaded int
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 20 {
			continue
		}

		player := Player{}

		if idx, ok := colMap["id"]; ok && idx < len(row) {
			player.ID = parseInt(row[idx])
		}
		if idx, ok := colMap["name"]; ok && idx < len(row) {
			player.Name = strings.TrimSpace(row[idx])
		}
		if idx, ok := colMap["age"]; ok && idx < len(row) {
			player.Age = parseInt(row[idx])
		}
		if idx, ok := colMap["nationality"]; ok && idx < len(row) {
			player.Nationality = strings.TrimSpace(row[idx])
		}
		if idx, ok := colMap["club"]; ok && idx < len(row) {
			player.Club = strings.TrimSpace(row[idx])
		}
		if idx, ok := colMap["position"]; ok && idx < len(row) {
			player.Position = strings.TrimSpace(row[idx])
		}
		if idx, ok := colMap["jersey number"]; ok && idx < len(row) {
			player.JerseyNumber = parseInt(row[idx])
		}
		if idx, ok := colMap["height"]; ok && idx < len(row) {
			player.Height = parseFloat(row[idx])
		}
		if idx, ok := colMap["weight"]; ok && idx < len(row) {
			player.Weight = parseFloat(row[idx])
		}
		if idx, ok := colMap["overall"]; ok && idx < len(row) {
			player.Overall = parseInt(row[idx])
		}
		if idx, ok := colMap["potential"]; ok && idx < len(row) {
			player.Potential = parseInt(row[idx])
		}
		if idx, ok := colMap["crossing"]; ok && idx < len(row) {
			player.Crossing = parseInt(row[idx])
		}
		if idx, ok := colMap["finishing"]; ok && idx < len(row) {
			player.Finishing = parseInt(row[idx])
		}
		if idx, ok := colMap["dribbling"]; ok && idx < len(row) {
			player.Dribbling = parseInt(row[idx])
		}
		if idx, ok := colMap["defending"]; ok && idx < len(row) {
			player.Defending = parseInt(row[idx])
		}
		if idx, ok := colMap["physicality"]; ok && idx < len(row) {
			player.Physicality = parseInt(row[idx])
		}
		if idx, ok := colMap["passing"]; ok && idx < len(row) {
			player.Passing = parseInt(row[idx])
		}
		if idx, ok := colMap["shooting"]; ok && idx < len(row) {
			player.Shooting = parseInt(row[idx])
		}
		if idx, ok := colMap["goalkeeping"]; ok && idx < len(row) {
			player.Goalkeeping = parseInt(row[idx])
		}

		// Extract positions from position column (can be multiple)
		if idx, ok := colMap["position"]; ok && idx < len(row) {
			posStr := strings.TrimSpace(row[idx])
			if posStr != "" {
				positions := strings.Split(posStr, ",")
				for _, pos := range positions {
					player.Positions = append(player.Positions, strings.TrimSpace(pos))
				}
			}
		}

		s.players = append(s.players, player)
		loaded++
	}

	return loaded, nil
}

// parseFloat parses a float string
func parseFloat(s string) float64 {
	s = strings.TrimSpace(s)
	if s == "" || s == "-" || s == "N/A" {
		return -1
	}
	// Handle height format like "180 cm" or "5'11""
	if strings.Contains(s, "cm") {
		s = strings.ReplaceAll(s, "cm", "")
	}
	if strings.Contains(s, "'") {
		// Convert feet and inches to cm
		var feet, inches int
		fmt.Sscanf(s, "%d'%d\"", &feet, &inches)
		return float64(feet*30 + inches*2)
	}
	val, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return -1
	}
	return val
}

// TotalPlayers returns the total number of loaded players
func (s *PlayerDataStore) TotalPlayers() int {
	return len(s.players)
}

// SearchPlayers searches for players by name
func (s *PlayerDataStore) SearchPlayers(name string) []Player {
	var result []Player
	nameLower := strings.ToLower(name)
	
	for _, p := range s.players {
		if strings.Contains(strings.ToLower(p.Name), nameLower) {
			result = append(result, p)
		}
	}
	return result
}

// FindPlayersByClub finds players by club name
func (s *PlayerDataStore) FindPlayersByClub(club string) []Player {
	var result []Player
	clubLower := strings.ToLower(club)
	
	for _, p := range s.players {
		if strings.Contains(strings.ToLower(p.Club), clubLower) {
			result = append(result, p)
		}
	}
	return result
}

// FindPlayersByNationality finds players by nationality
func (s *PlayerDataStore) FindPlayersByNationality(nationality string) []Player {
	var result []Player
	natLower := strings.ToLower(nationality)
	
	for _, p := range s.players {
		if strings.Contains(strings.ToLower(p.Nationality), natLower) {
			result = append(result, p)
		}
	}
	return result
}

// FindPlayersByPosition finds players by position
func (s *PlayerDataStore) FindPlayersByPosition(position string) []Player {
	var result []Player
	posLower := strings.ToLower(position)
	
	for _, p := range s.players {
		if strings.Contains(strings.ToLower(p.Position), posLower) {
			result = append(result, p)
		}
	}
	return result
}

// GetTopPlayers returns top players sorted by overall rating
func (s *PlayerDataStore) GetTopPlayers(limit int) []Player {
	players := make([]Player, len(s.players))
	copy(players, s.players)
	
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})
	
	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}
	
	return players
}

// GetTopBrazilianPlayers returns top Brazilian players
func (s *PlayerDataStore) GetTopBrazilianPlayers(limit int) []Player {
	var brazilian []Player
	
	for _, p := range s.players {
		if strings.Contains(strings.ToLower(p.Nationality), "brazil") ||
			strings.Contains(strings.ToLower(p.Nationality), "brasil") {
			brazilian = append(brazilian, p)
		}
	}
	
	sort.Slice(brazilian, func(i, j int) bool {
		return brazilian[i].Overall > brazilian[j].Overall
	})
	
	if limit > 0 && len(brazilian) > limit {
		brazilian = brazilian[:limit]
	}
	
	return brazilian
}

// GetPlayersByClub returns players sorted by rating for a club
func (s *PlayerDataStore) GetPlayersByClub(club string) []Player {
	players := s.FindPlayersByClub(club)
	
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})
	
	return players
}

// GetBrazilianPlayersByClub returns Brazilian players grouped by club
func (s *PlayerDataStore) GetBrazilianPlayersByClub() map[string][]Player {
	clubs := make(map[string][]Player)
	
	for _, p := range s.players {
		if strings.Contains(strings.ToLower(p.Nationality), "brazil") ||
			strings.Contains(strings.ToLower(p.Nationality), "brasil") {
			// Normalize club name
			clubName := normalizeClubName(p.Club)
			clubs[clubName] = append(clubs[clubName], p)
		}
	}
	
	return clubs
}

// normalizeClubName normalizes club names
func normalizeClubName(name string) string {
	name = strings.TrimSpace(name)
	
	// Common Brazilian club name mappings
	clubMap := map[string]string{
		"flamengo":            "Flamengo",
		"fluminense":          "Fluminense",
		"palmeiras":           "Palmeiras",
		"santos":              "Santos",
		"corinthians":         "Corinthians",
		"são paulo":           "São Paulo",
		"sao paulo":           "São Paulo",
		"grêmio":              "Grêmio",
		"gremio":              "Grêmio",
		"internacional":       "Internacional",
		"botafogo":            "Botafogo",
		"vasco":               "Vasco da Gama",
		"vitória":             "Vitória",
		"vitoria":             "Vitória",
		"bahia":               "Bahia",
		"fortaleza":           "Fortaleza",
		"ceará":               "Ceará",
		"ceara":               "Ceará",
		"belém":               "Belém",
		"paraná":              "Paraná",
		"parana":              "Paraná",
		"fla":                 "Flamengo",
		"flu":                 "Fluminense",
		"pal":                 "Palmeiras",
		"sao":                 "São Paulo",
	}
	
	if normalized, ok := clubMap[strings.ToLower(name)]; ok {
		return normalized
	}
	return name
}

// GetPlayerStats returns detailed stats for a player
func (s *PlayerDataStore) GetPlayerStats(playerName string) *Player {
	players := s.SearchPlayers(playerName)
	if len(players) == 0 {
		return nil
	}
	return &players[0]
}
