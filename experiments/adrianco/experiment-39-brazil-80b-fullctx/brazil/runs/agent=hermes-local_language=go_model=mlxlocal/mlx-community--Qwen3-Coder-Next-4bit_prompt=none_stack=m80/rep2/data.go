package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Match represents a soccer match
type Match struct {
	ID             string
	DateTime       time.Time
	HomeTeam       string
	HomeTeamState  string
	AwayTeam       string
	AwayTeamState  string
	HomeGoals      int
	AwayGoals      int
	Season         string
	Round          int
	Competition    string
	Stage          string // For Libertadores
	HomeCorner     int
	AwayCorner     int
	HomeAttack     int
	AwayAttack     int
	HomeShots      int
	AwayShots      int
	HTResult       string
	ATResult       string
	TotalCorners   int
	HomeYellow     int
	AwayYellow     int
	HomeRed        int
	AwayRed        int
	Stadium        string
	Winner         string
}

// MatchDataStore manages match data from multiple CSV files
type MatchDataStore struct {
	matches []Match
}

// NewMatchDataStore creates a new match data store
func NewMatchDataStore(dataDir string) *MatchDataStore {
	return &MatchDataStore{
		matches: []Match{},
	}
}

// LoadCSV loads matches from a CSV file
func (s *MatchDataStore) LoadCSV(filePath string, fileName string) error {
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1 // Allow variable number of fields
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in file")
	}

	// Determine file type based on headers
	headers := records[0]

	var loaded int
	switch {
	case strings.Contains(fileName, "Brasileirao"):
		loaded, err = s.loadBrasileirao(records, headers)
	case strings.Contains(fileName, "Cup"):
		loaded, err = s.loadCup(records, headers)
	case strings.Contains(fileName, "Libertadores"):
		loaded, err = s.loadLibertadores(records, headers)
	case strings.Contains(fileName, "BR-Football"):
		loaded, err = s.loadBRFootball(records, headers)
	case strings.Contains(fileName, "novo_campeonato"):
		loaded, err = s.loadNovoCampeonato(records, headers)
	default:
		return fmt.Errorf("unknown file type: %s", fileName)
	}

	if err != nil {
		return err
	}

	fmt.Printf("  Loaded %d matches from %s\n", loaded, fileName)
	return nil
}

// loadBrasileirao loads Brasileirão match data
func (s *MatchDataStore) loadBrasileirao(records [][]string, headers []string) (int, error) {
	colMap := make(map[string]int)
	for i, h := range headers {
		colMap[strings.TrimSpace(strings.ToLower(h))] = i
	}

	var loaded int
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 8 {
			continue
		}

		match := Match{
			Competition: "Brasileirão",
		}

		if idx, ok := colMap["datetime"]; ok && idx < len(row) {
			match.DateTime = parseDateTime(row[idx])
		}
		if idx, ok := colMap["home_team"]; ok && idx < len(row) {
			match.HomeTeam = normalizeTeamName(row[idx])
			match.HomeTeamState = extractState(match.HomeTeam)
		}
		if idx, ok := colMap["away_team"]; ok && idx < len(row) {
			match.AwayTeam = normalizeTeamName(row[idx])
			match.AwayTeamState = extractState(match.AwayTeam)
		}
		if idx, ok := colMap["home_goal"]; ok && idx < len(row) {
			match.HomeGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["away_goal"]; ok && idx < len(row) {
			match.AwayGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["season"]; ok && idx < len(row) {
			match.Season = row[idx]
		}
		if idx, ok := colMap["round"]; ok && idx < len(row) {
			match.Round = parseInt(row[idx])
		}

		if match.HomeGoals >= 0 && match.AwayGoals >= 0 {
			s.matches = append(s.matches, match)
			loaded++
		}
	}

	return loaded, nil
}

// loadCup loads Copa do Brasil match data
func (s *MatchDataStore) loadCup(records [][]string, headers []string) (int, error) {
	colMap := make(map[string]int)
	for i, h := range headers {
		colMap[strings.TrimSpace(strings.ToLower(h))] = i
	}

	var loaded int
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 7 {
			continue
		}

		match := Match{
			Competition: "Copa do Brasil",
		}

		if idx, ok := colMap["round"]; ok && idx < len(row) {
			match.Round = parseInt(row[idx])
		}
		if idx, ok := colMap["datetime"]; ok && idx < len(row) {
			match.DateTime = parseDateTime(row[idx])
		}
		if idx, ok := colMap["home_team"]; ok && idx < len(row) {
			match.HomeTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["away_team"]; ok && idx < len(row) {
			match.AwayTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["home_goal"]; ok && idx < len(row) {
			match.HomeGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["away_goal"]; ok && idx < len(row) {
			match.AwayGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["season"]; ok && idx < len(row) {
			match.Season = row[idx]
		}

		if match.HomeGoals >= 0 && match.AwayGoals >= 0 {
			s.matches = append(s.matches, match)
			loaded++
		}
	}

	return loaded, nil
}

// loadLibertadores loads Copa Libertadores match data
func (s *MatchDataStore) loadLibertadores(records [][]string, headers []string) (int, error) {
	colMap := make(map[string]int)
	for i, h := range headers {
		colMap[strings.TrimSpace(strings.ToLower(h))] = i
	}

	var loaded int
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 7 {
			continue
		}

		match := Match{
			Competition: "Copa Libertadores",
		}

		if idx, ok := colMap["datetime"]; ok && idx < len(row) {
			match.DateTime = parseDateTime(row[idx])
		}
		if idx, ok := colMap["home_team"]; ok && idx < len(row) {
			match.HomeTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["away_team"]; ok && idx < len(row) {
			match.AwayTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["home_goal"]; ok && idx < len(row) {
			match.HomeGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["away_goal"]; ok && idx < len(row) {
			match.AwayGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["season"]; ok && idx < len(row) {
			match.Season = row[idx]
		}
		if idx, ok := colMap["stage"]; ok && idx < len(row) {
			match.Stage = row[idx]
		}

		if match.HomeGoals >= 0 && match.AwayGoals >= 0 {
			s.matches = append(s.matches, match)
			loaded++
		}
	}

	return loaded, nil
}

// loadBRFootball loads BR-Football-Dataset match data
func (s *MatchDataStore) loadBRFootball(records [][]string, headers []string) (int, error) {
	colMap := make(map[string]int)
	for i, h := range headers {
		colMap[strings.TrimSpace(strings.ToLower(h))] = i
	}

	var loaded int
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 10 {
			continue
		}

		match := Match{
			Competition: normalizeCompetition(row[colMap["tournament"]]),
		}

		if idx, ok := colMap["date"]; ok && idx < len(row) {
			match.DateTime = parseDate(row[idx])
		}
		if idx, ok := colMap["home"]; ok && idx < len(row) {
			match.HomeTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["away"]; ok && idx < len(row) {
			match.AwayTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["home_goal"]; ok && idx < len(row) {
			match.HomeGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["away_goal"]; ok && idx < len(row) {
			match.AwayGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["home_corner"]; ok && idx < len(row) {
			match.HomeCorner = parseInt(row[idx])
		}
		if idx, ok := colMap["away_corner"]; ok && idx < len(row) {
			match.AwayCorner = parseInt(row[idx])
		}
		if idx, ok := colMap["home_attack"]; ok && idx < len(row) {
			match.HomeAttack = parseInt(row[idx])
		}
		if idx, ok := colMap["away_attack"]; ok && idx < len(row) {
			match.AwayAttack = parseInt(row[idx])
		}
		if idx, ok := colMap["home_shots"]; ok && idx < len(row) {
			match.HomeShots = parseInt(row[idx])
		}
		if idx, ok := colMap["away_shots"]; ok && idx < len(row) {
			match.AwayShots = parseInt(row[idx])
		}
		if idx, ok := colMap["ht_result"]; ok && idx < len(row) {
			match.HTResult = row[idx]
		}
		if idx, ok := colMap["at_result"]; ok && idx < len(row) {
			match.ATResult = row[idx]
		}
		if idx, ok := colMap["total_corners"]; ok && idx < len(row) {
			match.TotalCorners = parseInt(row[idx])
		}

		if match.HomeGoals >= 0 && match.AwayGoals >= 0 {
			s.matches = append(s.matches, match)
			loaded++
		}
	}

	return loaded, nil
}

// loadNovoCampeonato loads Novo Campeonato Brasileiro data
func (s *MatchDataStore) loadNovoCampeonato(records [][]string, headers []string) (int, error) {
	colMap := make(map[string]int)
	for i, h := range headers {
		colMap[strings.TrimSpace(strings.ToLower(h))] = i
	}

	var loaded int
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 11 {
			continue
		}

		match := Match{
			Competition: "Brasileirão",
		}

		if idx, ok := colMap["data"]; ok && idx < len(row) {
			match.DateTime = parseBrazilianDate(row[idx])
		}
		if idx, ok := colMap["ano"]; ok && idx < len(row) {
			match.Season = row[idx]
		}
		if idx, ok := colMap["rodada"]; ok && idx < len(row) {
			match.Round = parseInt(row[idx])
		}
		if idx, ok := colMap["equipe_mandante"]; ok && idx < len(row) {
			match.HomeTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["equipe_visitante"]; ok && idx < len(row) {
			match.AwayTeam = normalizeTeamName(row[idx])
		}
		if idx, ok := colMap["gols_mandante"]; ok && idx < len(row) {
			match.HomeGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["gols_visitante"]; ok && idx < len(row) {
			match.AwayGoals = parseInt(row[idx])
		}
		if idx, ok := colMap["mandante_uf"]; ok && idx < len(row) {
			match.HomeTeamState = normalizeState(row[idx])
		}
		if idx, ok := colMap["visitante_uf"]; ok && idx < len(row) {
			match.AwayTeamState = normalizeState(row[idx])
		}
		if idx, ok := colMap["vencedor"]; ok && idx < len(row) {
			match.Winner = row[idx]
		}
		if idx, ok := colMap["arena"]; ok && idx < len(row) {
			match.Stadium = row[idx]
		}

		if match.HomeGoals >= 0 && match.AwayGoals >= 0 {
			s.matches = append(s.matches, match)
			loaded++
		}
	}

	return loaded, nil
}

// parseDateTime parses ISO datetime
func parseDateTime(s string) time.Time {
	s = strings.TrimSpace(s)
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02",
	}
	for _, format := range formats {
		if t, err := time.Parse(format, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// parseDate parses date in YYYY-MM-DD format
func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02",
		"02/01/2006",
		"2006/01/02",
	}
	for _, format := range formats {
		if t, err := time.Parse(format, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// parseBrazilianDate parses DD/MM/YYYY format
func parseBrazilianDate(s string) time.Time {
	s = strings.TrimSpace(s)
	t, err := time.Parse("02/01/2006", s)
	if err != nil {
		return time.Time{}
	}
	return t
}

// parseInt parses an integer string
func parseInt(s string) int {
	s = strings.TrimSpace(s)
	if s == "" || s == "-" || s == "N/A" {
		return -1
	}
	val, err := strconv.Atoi(s)
	if err != nil {
		return -1
	}
	return val
}

// normalizeTeamName normalizes team names
func normalizeTeamName(name string) string {
	name = strings.TrimSpace(name)
	// Remove state suffix like -SP, -RJ, etc.
	re := regexp.MustCompile(`[-–][A-Z]{2}$`)
	name = re.ReplaceAllString(name, "")
	name = strings.TrimSpace(name)
	return name
}

// extractState extracts state from team name
func extractState(team string) string {
	re := regexp.MustCompile(`[-–]([A-Z]{2})$`)
	matches := re.FindStringSubmatch(team)
	if len(matches) == 2 {
		return normalizeState(matches[1])
	}
	return ""
}

// normalizeState normalizes state abbreviations
func normalizeState(state string) string {
	state = strings.TrimSpace(state)
	if state == "DF" {
		return "DF"
	}
	return state
}

// normalizeCompetition normalizes competition names
func normalizeCompetition(name string) string {
	name = strings.TrimSpace(name)
	name = strings.ToLower(name)
	
	// Map common variations
	nameMap := map[string]string{
		"brasileirão":        "Brasileirão",
		"brasilieirao":       "Brasileirão",
		"brasileirao":        "Brasileirão",
		"brasileiro":         "Brasileirão",
		"campeonato brasileiro": "Brasileirão",
		"copa do brasil":     "Copa do Brasil",
		"libertadores":       "Copa Libertadores",
		" libertadores":      "Copa Libertadores",
	}
	
	if normalized, ok := nameMap[name]; ok {
		return normalized
	}
	return name
}

// TotalMatches returns the total number of loaded matches
func (s *MatchDataStore) TotalMatches() int {
	return len(s.matches)
}

// FindMatchesByTeam finds matches involving a team
func (s *MatchDataStore) FindMatchesByTeam(teamName string) []Match {
	var result []Match
	teamLower := strings.ToLower(teamName)
	
	for _, m := range s.matches {
		if strings.Contains(strings.ToLower(m.HomeTeam), teamLower) ||
			strings.Contains(strings.ToLower(m.AwayTeam), teamLower) {
			result = append(result, m)
		}
	}
	return result
}

// FindTeams returns unique team names
func (s *MatchDataStore) FindTeams(teamName string) []string {
	teams := make(map[string]bool)
	teamLower := strings.ToLower(teamName)
	
	for _, m := range s.matches {
		if strings.Contains(strings.ToLower(m.HomeTeam), teamLower) {
			teams[m.HomeTeam] = true
		}
		if strings.Contains(strings.ToLower(m.AwayTeam), teamLower) {
			teams[m.AwayTeam] = true
		}
	}
	
	var result []string
	for team := range teams {
		result = append(result, team)
	}
	return result
}

// GetTeamStats returns statistics for a team in a specific season
func (s *MatchDataStore) GetTeamStats(teamName string, season string) TeamStats {
	stats := TeamStats{
		Team: teamName,
	}
	
	teamLower := strings.ToLower(teamName)
	
	for _, m := range s.matches {
		if m.Season != season && season != "" {
			continue
		}
		
		if strings.Contains(strings.ToLower(m.HomeTeam), teamLower) {
			stats.Matches++
			stats.GoalsFor += m.HomeGoals
			stats.GoalsAgainst += m.AwayGoals
			if m.HomeGoals > m.AwayGoals {
				stats.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				stats.Draws++
			} else {
				stats.Losses++
			}
		} else if strings.Contains(strings.ToLower(m.AwayTeam), teamLower) {
			stats.Matches++
			stats.GoalsFor += m.AwayGoals
			stats.GoalsAgainst += m.HomeGoals
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
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}
	
	return stats
}

// TeamStats represents team statistics
type TeamStats struct {
	Team        string
	Matches     int
	Wins        int
	Draws       int
	Losses      int
	GoalsFor    int
	GoalsAgainst int
	Points      int
	WinRate     float64
}

// GetBrasileiraoStandings calculates standings for a season
func (s *MatchDataStore) GetBrasileiraoStandings(season string) []TeamStanding {
	standings := make(map[string]*TeamStanding)
	
	for _, m := range s.matches {
		if m.Season != season && season != "" {
			continue
		}
		if m.Competition != "Brasileirão" {
			continue
		}
		
		if standings[m.HomeTeam] == nil {
			standings[m.HomeTeam] = &TeamStanding{Team: m.HomeTeam}
		}
		if standings[m.AwayTeam] == nil {
			standings[m.AwayTeam] = &TeamStanding{Team: m.AwayTeam}
		}
		
		standings[m.HomeTeam].Played++
		standings[m.AwayTeam].Played++
		standings[m.HomeTeam].GoalsFor += m.HomeGoals
		standings[m.HomeTeam].GoalsAgainst += m.AwayGoals
		standings[m.AwayTeam].GoalsFor += m.AwayGoals
		standings[m.AwayTeam].GoalsAgainst += m.HomeGoals
		
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
	}
	
	var result []TeamStanding
	for _, standing := range standings {
		result = append(result, *standing)
	}
	
	// Sort by points, then goal difference, then goals scored
	sort.Slice(result, func(i, j int) bool {
		if result[i].Points != result[j].Points {
			return result[i].Points > result[j].Points
		}
		diffI := result[i].GoalsFor - result[i].GoalsAgainst
		diffJ := result[j].GoalsFor - result[j].GoalsAgainst
		if diffI != diffJ {
			return diffI > diffJ
		}
		return result[i].GoalsFor > result[j].GoalsFor
	})
	
	return result
}

// TeamStanding represents a team's standing
type TeamStanding struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
}
