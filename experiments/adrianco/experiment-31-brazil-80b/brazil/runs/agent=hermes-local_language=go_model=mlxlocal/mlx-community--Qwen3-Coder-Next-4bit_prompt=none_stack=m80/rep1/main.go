package main

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"
)

// Match represents a soccer match
type Match struct {
	ID            string  `json:"id"`
	Tournament    string  `json:"tournament"`
	Date          string  `json:"date"`
	HomeTeam      string  `json:"home_team"`
	AwayTeam      string  `json:"away_team"`
	HomeTeamState string  `json:"home_team_state"`
	AwayTeamState string  `json:"away_team_state"`
	HomeGoal      int     `json:"home_goal"`
	AwayGoal      int     `json:"away_goal"`
	Season        int     `json:"season"`
	Round         int     `json:"round"`
	Stage         string  `json:"stage"`
	HomeCorner    int     `json:"home_corner"`
	AwayCorner    int     `json:"away_corner"`
	HomeAttack    int     `json:"home_attack"`
	AwayAttack    int     `json:"away_attack"`
	HomeShot      int     `json:"home_shot"`
	AwayShot      int     `json:"away_shot"`
	HTResult      string  `json:"ht_result"`
	ATResult      string  `json:"at_result"`
	TotalCorners  int     `json:"total_corners"`
}

// Player represents a soccer player
type Player struct {
	ID              int    `json:"id"`
	Name            string `json:"name"`
	Age             int    `json:"age"`
	Nationality     string `json:"nationality"`
	Overall         int    `json:"overall"`
	Potential       int    `json:"potential"`
	Club            string `json:"club"`
	Position        string `json:"position"`
	JerseyNumber    int    `json:"jersey_number"`
	Height          string `json:"height"`
	Weight          string `json:"weight"`
	Crossing        int    `json:"crossing"`
	Finishing       int    `json:"finishing"`
	HeadingAccuracy int    `json:"heading_accuracy"`
	ShortPassing    int    `json:"short_passing"`
	Volleys         int    `json:"volleys"`
	Dribbling       int    `json:"dribbling"`
	Curve           int    `json:"curve"`
	FKAccuracy      int    `json:"fk_accuracy"`
	LongPassing     int    `json:"long_passing"`
	BallControl     int    `json:"ball_control"`
	Acceleration    int    `json:"acceleration"`
	SprintSpeed     int    `json:"sprint_speed"`
	Agility         int    `json:"agility"`
	Reactions       int    `json:"reactions"`
	Balance         int    `json:"balance"`
	ShotPower       int    `json:"shot_power"`
	Jumping         int    `json:"jumping"`
	Stamina         int    `json:"stamina"`
	Strength        int    `json:"strength"`
	LongShots       int    `json:"long_shots"`
	Aggression      int    `json:"aggression"`
	Interceptions   int    `json:"interceptions"`
	Positioning     int    `json:"positioning"`
	Vision          int    `json:"vision"`
	Penalties       int    `json:"penalties"`
	Composure       int    `json:"composure"`
	Marking         int    `json:"marking"`
	StandingTackle  int    `json:"standing_tackle"`
	SlidingTackle   int    `json:"sliding_tackle"`
	GKDiving        int    `json:"gk_diving"`
	GKHandling      int    `json:"gk_handling"`
	GKKicking       int    `json:"gk_kicking"`
	GKPositioning   int    `json:"gk_positioning"`
	GKReflexes      int    `json:"gk_reflexes"`
}

// TeamStats represents aggregated team statistics
type TeamStats struct {
	TeamName     string `json:"team_name"`
	Matches      int    `json:"matches"`
	Wins         int    `json:"wins"`
	Draws        int    `json:"draws"`
	Losses       int    `json:"losses"`
	GoalsFor     int    `json:"goals_for"`
	GoalsAgainst int    `json:"goals_against"`
	GoalDiff     int    `json:"goal_diff"`
	Points       int    `json:"points"`
	HomeMatches  int    `json:"home_matches"`
	HomeWins     int    `json:"home_wins"`
	HomeDraws    int    `json:"home_draws"`
	HomeLosses   int    `json:"home_losses"`
	HomeGF       int    `json:"home_gf"`
	HomeGA       int    `json:"home_ga"`
	AwayMatches  int    `json:"away_matches"`
	AwayWins     int    `json:"away_wins"`
	AwayDraws    int    `json:"away_draws"`
	AwayLosses   int    `json:"away_losses"`
	AwayGF       int    `json:"away_gf"`
	AwayGA       int    `json:"away_ga"`
}

// Competition represents a tournament/competition
type Competition struct {
	Name      string     `json:"name"`
	Seasons   []int      `json:"seasons"`
	Matches   []Match    `json:"matches"`
	Standings []TeamStats `json:"standings"`
}

// SoccerServer implements the soccer data server
type SoccerServer struct {
	matches      []Match
	players      []Player
	competitions map[string]*Competition
}

// NewSoccerServer creates a new soccer server
func NewSoccerServer() *SoccerServer {
	return &SoccerServer{
		matches:      []Match{},
		players:      []Player{},
		competitions: make(map[string]*Competition),
	}
}

// Matches returns the matches slice
func (s *SoccerServer) Matches() []Match {
	return s.matches
}

// Players returns the players slice
func (s *SoccerServer) Players() []Player {
	return s.players
}

// LoadData loads all CSV files from the data directory
func (s *SoccerServer) LoadData(dataDir string) error {
	// Load Brasileirão matches
	if err := s.loadBrasileiraoMatches(filepath.Join(dataDir, "Brasileirao_Matches.csv")); err != nil {
		log.Printf("Warning: Could not load Brasileirão matches: %v", err)
	}

	// Load Copa do Brasil matches
	if err := s.loadCopaDoBrasilMatches(filepath.Join(dataDir, "Brazilian_Cup_Matches.csv")); err != nil {
		log.Printf("Warning: Could not load Copa do Brasil matches: %v", err)
	}

	// Load Libertadores matches
	if err := s.loadLibertadoresMatches(filepath.Join(dataDir, "Libertadores_Matches.csv")); err != nil {
		log.Printf("Warning: Could not load Libertadores matches: %v", err)
	}

	// Load Extended match statistics
	if err := s.loadExtendedMatches(filepath.Join(dataDir, "BR-Football-Dataset.csv")); err != nil {
		log.Printf("Warning: Could not load extended matches: %v", err)
	}

	// Load historical Brasileirão
	if err := s.loadHistoricalBrasileirao(filepath.Join(dataDir, "novo_campeonato_brasileiro.csv")); err != nil {
		log.Printf("Warning: Could not load historical Brasileirão: %v", err)
	}

	// Load player data
	if err := s.loadPlayers(filepath.Join(dataDir, "fifa_data.csv")); err != nil {
		log.Printf("Warning: Could not load player data: %v", err)
	}

	log.Printf("Loaded %d matches and %d players", len(s.matches), len(s.players))
	return nil
}

// loadBrasileiraoMatches loads Brasileirão Serie A matches
func (s *SoccerServer) loadBrasileiraoMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(bufio.NewReader(file))
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	for i, record := range records {
		if i == 0 { // Skip header
			continue
		}
		if len(record) < 9 {
			continue
		}

		homeGoal, _ := strconv.Atoi(record[5])
		awayGoal, _ := strconv.Atoi(record[6])
		season, _ := strconv.Atoi(record[7])
		round, _ := strconv.Atoi(record[8])

		// Parse date
		date, err := time.Parse("2006-01-02 15:04:05", record[0])
		if err != nil {
			date, err = time.Parse("2006-01-02", record[0])
			if err != nil {
				continue
			}
		}

		// Extract team name without state suffix
		homeTeam := extractTeamName(record[1])
		awayTeam := extractTeamName(record[3])

		match := Match{
			ID:            uuid.New().String(),
			Tournament:    "Brasileirão",
			Date:          date.Format("2006-01-02"),
			HomeTeam:      homeTeam,
			AwayTeam:      awayTeam,
			HomeTeamState: record[2],
			AwayTeamState: record[4],
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Season:        season,
			Round:         round,
		}
		s.matches = append(s.matches, match)
	}

	log.Printf("Loaded %d Brasileirão matches", len(s.matches))
	return nil
}

// loadCopaDoBrasilMatches loads Copa do Brasil matches
func (s *SoccerServer) loadCopaDoBrasilMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(bufio.NewReader(file))
	reader.FieldsPerRecord = -1
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	for i, record := range records {
		if i == 0 { // Skip header
			continue
		}
		if len(record) < 7 {
			continue
		}

		homeGoal, _ := strconv.Atoi(record[4])
		awayGoal, _ := strconv.Atoi(record[5])
		season, _ := strconv.Atoi(record[6])

		// Parse date
		date, err := time.Parse("2006-01-02 15:04:05", record[1])
		if err != nil {
			date, err = time.Parse("2006-01-02", record[1])
			if err != nil {
				continue
			}
		}

		match := Match{
			ID:         uuid.New().String(),
			Tournament: "Copa do Brasil",
			Date:       date.Format("2006-01-02"),
			HomeTeam:   record[2],
			AwayTeam:   record[3],
			HomeGoal:   homeGoal,
			AwayGoal:   awayGoal,
			Season:     season,
			Round:      parseRound(record[0]),
		}
		s.matches = append(s.matches, match)
	}

	log.Printf("Loaded %d Copa do Brasil matches", len(s.matches))
	return nil
}

// loadLibertadoresMatches loads Copa Libertadores matches
func (s *SoccerServer) loadLibertadoresMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(bufio.NewReader(file))
	reader.FieldsPerRecord = -1
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	for i, record := range records {
		if i == 0 { // Skip header
			continue
		}
		if len(record) < 7 {
			continue
		}

		homeGoal, _ := strconv.Atoi(record[3])
		awayGoal, _ := strconv.Atoi(record[4])
		season, _ := strconv.Atoi(record[5])

		// Parse date
		date, err := time.Parse("2006-01-02 15:04:05", record[0])
		if err != nil {
			date, err = time.Parse("2006-01-02", record[0])
			if err != nil {
				continue
			}
		}

		match := Match{
			ID:         uuid.New().String(),
			Tournament: "Copa Libertadores",
			Date:       date.Format("2006-01-02"),
			HomeTeam:   record[1],
			AwayTeam:   record[2],
			HomeGoal:   homeGoal,
			AwayGoal:   awayGoal,
			Season:     season,
			Stage:      record[6],
		}
		s.matches = append(s.matches, match)
	}

	log.Printf("Loaded %d Libertadores matches", len(s.matches))
	return nil
}

// loadExtendedMatches loads extended match statistics
func (s *SoccerServer) loadExtendedMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(bufio.NewReader(file))
	reader.FieldsPerRecord = -1
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	for i, record := range records {
		if i == 0 { // Skip header
			continue
		}
		if len(record) < 16 {
			continue
		}

		homeGoal, _ := strconv.Atoi(record[2])
		awayGoal, _ := strconv.Atoi(record[3])
		homeCorner, _ := strconv.Atoi(record[5])
		awayCorner, _ := strconv.Atoi(record[6])
		homeAttack, _ := strconv.Atoi(record[7])
		awayAttack, _ := strconv.Atoi(record[8])
		homeShot, _ := strconv.Atoi(record[9])
		awayShot, _ := strconv.Atoi(record[10])
		totalCorners, _ := strconv.Atoi(record[15])

		// Parse date
		date, err := time.Parse("2006-01-02", record[12])
		if err != nil {
			continue
		}

		match := Match{
			ID:           uuid.New().String(),
			Tournament:   record[0],
			Date:         date.Format("2006-01-02"),
			HomeTeam:     record[1],
			AwayTeam:     record[4],
			HomeGoal:     homeGoal,
			AwayGoal:     awayGoal,
			HomeCorner:   homeCorner,
			AwayCorner:   awayCorner,
			HomeAttack:   homeAttack,
			AwayAttack:   awayAttack,
			HomeShot:     homeShot,
			AwayShot:     awayShot,
			TotalCorners: totalCorners,
			HTResult:     record[14],
			ATResult:     record[15],
		}
		s.matches = append(s.matches, match)
	}

	log.Printf("Loaded %d extended matches", len(s.matches))
	return nil
}

// loadHistoricalBrasileirao loads historical Brasileirão data (2003-2019)
func (s *SoccerServer) loadHistoricalBrasileirao(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(bufio.NewReader(file))
	reader.FieldsPerRecord = -1
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	for i, record := range records {
		if i == 0 { // Skip header
			continue
		}
		if len(record) < 11 {
			continue
		}

		// Parse date in DD/MM/YYYY format
		date, err := time.Parse("02/01/2006", record[1])
		if err != nil {
			continue
		}

		homeGoal, _ := strconv.Atoi(record[6])
		awayGoal, _ := strconv.Atoi(record[7])
		season, _ := strconv.Atoi(record[2])
		round, _ := strconv.Atoi(record[3])

		match := Match{
			ID:            uuid.New().String(),
			Tournament:    "Brasileirão",
			Date:          date.Format("2006-01-02"),
			HomeTeam:      record[4],
			AwayTeam:      record[5],
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Season:        season,
			Round:         round,
			HomeTeamState: record[8],
			AwayTeamState: record[9],
		}
		s.matches = append(s.matches, match)
	}

	log.Printf("Loaded %d historical Brasileirão matches", len(s.matches))
	return nil
}

// loadPlayers loads FIFA player data
func (s *SoccerServer) loadPlayers(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(bufio.NewReader(file))
	reader.FieldsPerRecord = -1
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	for i, record := range records {
		if i == 0 { // Skip header
			continue
		}
		if len(record) < 100 {
			continue
		}

		id, _ := strconv.Atoi(record[1])
		age, _ := strconv.Atoi(record[2])
		overall, _ := strconv.Atoi(record[6])
		potential, _ := strconv.Atoi(record[7])
		jerseyNumber, _ := strconv.Atoi(record[11])

		// Parse numeric skill fields
		crossing := parseSkill(record[35])
		finishing := parseSkill(record[36])
		headingAccuracy := parseSkill(record[37])
		shortPassing := parseSkill(record[38])
		volleys := parseSkill(record[39])
		dribbling := parseSkill(record[40])
		curve := parseSkill(record[41])
		fkAccuracy := parseSkill(record[42])
		longPassing := parseSkill(record[43])
		ballControl := parseSkill(record[44])
		acceleration := parseSkill(record[45])
		sprintSpeed := parseSkill(record[46])
		agility := parseSkill(record[47])
		reactions := parseSkill(record[48])
		balance := parseSkill(record[49])
		shotPower := parseSkill(record[50])
		jumping := parseSkill(record[51])
		stamina := parseSkill(record[52])
		strength := parseSkill(record[53])
		longShots := parseSkill(record[54])
		aggression := parseSkill(record[55])
		interceptions := parseSkill(record[56])
		positioning := parseSkill(record[57])
		vision := parseSkill(record[58])
		penalties := parseSkill(record[59])
		composure := parseSkill(record[60])
		marking := parseSkill(record[61])
		standingTackle := parseSkill(record[62])
		slidingTackle := parseSkill(record[63])
		gkDiving := parseSkill(record[64])
		gkHandling := parseSkill(record[65])
		gkKicking := parseSkill(record[66])
		gkPositioning := parseSkill(record[67])
		gkReflexes := parseSkill(record[68])

		player := Player{
			ID:              id,
			Name:            record[2],
			Age:             age,
			Nationality:     record[5],
			Overall:         overall,
			Potential:       potential,
			Club:            record[8],
			Position:        record[12],
			JerseyNumber:    jerseyNumber,
			Height:          record[13],
			Weight:          record[14],
			Crossing:        crossing,
			Finishing:       finishing,
			HeadingAccuracy: headingAccuracy,
			ShortPassing:    shortPassing,
			Volleys:         volleys,
			Dribbling:       dribbling,
			Curve:           curve,
			FKAccuracy:      fkAccuracy,
			LongPassing:     longPassing,
			BallControl:     ballControl,
			Acceleration:    acceleration,
			SprintSpeed:     sprintSpeed,
			Agility:         agility,
			Reactions:       reactions,
			Balance:         balance,
			ShotPower:       shotPower,
			Jumping:         jumping,
			Stamina:         stamina,
			Strength:        strength,
			LongShots:       longShots,
			Aggression:      aggression,
			Interceptions:   interceptions,
			Positioning:     positioning,
			Vision:          vision,
			Penalties:       penalties,
			Composure:       composure,
			Marking:         marking,
			StandingTackle:  standingTackle,
			SlidingTackle:   slidingTackle,
			GKDiving:        gkDiving,
			GKHandling:      gkHandling,
			GKKicking:       gkKicking,
			GKPositioning:   gkPositioning,
			GKReflexes:      gkReflexes,
		}
		s.players = append(s.players, player)
	}

	log.Printf("Loaded %d players", len(s.players))
	return nil
}

// Helper functions
func extractTeamName(name string) string {
	// Remove state suffix like "-SP", "-RJ", etc.
	parts := strings.Split(name, "-")
	if len(parts) > 1 && len(parts[len(parts)-1]) == 2 {
		return strings.TrimSpace(parts[0])
	}
	return strings.TrimSpace(name)
}

func parseRound(round string) int {
	// Try to parse round as a number
	if r, err := strconv.Atoi(round); err == nil {
		return r
	}
	// Try to extract number from string like "1st" or "Final"
	var num int
	for _, char := range round {
		if char >= '0' && char <= '9' {
			num = num*10 + int(char-'0')
		}
	}
	return num
}

func parseSkill(skill string) int {
	// Skills can be in format like "88+2" or just "88"
	skill = strings.TrimSpace(skill)
	if strings.Contains(skill, "+") {
		parts := strings.Split(skill, "+")
		if len(parts) == 2 {
			base, _ := strconv.Atoi(parts[0])
			modifier, _ := strconv.Atoi(parts[1])
			return base + modifier
		}
	}
	val, _ := strconv.Atoi(skill)
	return val
}

// GetMatchesByTeams finds matches between two teams
func (s *SoccerServer) GetMatchesByTeams(team1, team2 string) []Match {
	var results []Match
	team1Lower := strings.ToLower(team1)
	team2Lower := strings.ToLower(team2)

	for _, match := range s.matches {
		homeLower := strings.ToLower(match.HomeTeam)
		awayLower := strings.ToLower(match.AwayTeam)

		if (homeLower == team1Lower && awayLower == team2Lower) ||
			(homeLower == team2Lower && awayLower == team1Lower) {
			results = append(results, match)
		}
	}

	// Sort by date (most recent first)
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date > results[j].Date
	})

	return results
}

// GetMatchesByTeam finds all matches for a team
func (s *SoccerServer) GetMatchesByTeam(team string) []Match {
	var results []Match
	teamLower := strings.ToLower(team)

	for _, match := range s.matches {
		homeLower := strings.ToLower(match.HomeTeam)
		awayLower := strings.ToLower(match.AwayTeam)

		if homeLower == teamLower || awayLower == teamLower {
			results = append(results, match)
		}
	}

	// Sort by date (most recent first)
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date > results[j].Date
	})

	return results
}

// GetMatchesByDateRange finds matches within a date range
func (s *SoccerServer) GetMatchesByDateRange(startDate, endDate string) []Match {
	var results []Match

	for _, match := range s.matches {
		if match.Date >= startDate && match.Date <= endDate {
			results = append(results, match)
		}
	}

	// Sort by date
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date < results[j].Date
	})

	return results
}

// GetMatchesByTournament finds matches for a tournament
func (s *SoccerServer) GetMatchesByTournament(tournament string) []Match {
	var results []Match
	tournamentLower := strings.ToLower(tournament)

	for _, match := range s.matches {
		if strings.Contains(strings.ToLower(match.Tournament), tournamentLower) {
			results = append(results, match)
		}
	}

	// Sort by date
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date < results[j].Date
	})

	return results
}

// GetMatchesBySeason finds matches for a specific season
func (s *SoccerServer) GetMatchesBySeason(season int) []Match {
	var results []Match

	for _, match := range s.matches {
		if match.Season == season {
			results = append(results, match)
		}
	}

	// Sort by date
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date < results[j].Date
	})

	return results
}

// GetTeamStats calculates statistics for a team
func (s *SoccerServer) GetTeamStats(team string, season int) TeamStats {
	teamLower := strings.ToLower(team)
	var stats TeamStats
	stats.TeamName = team

	for _, match := range s.matches {
		homeLower := strings.ToLower(match.HomeTeam)
		awayLower := strings.ToLower(match.AwayTeam)

		if (homeLower == teamLower || awayLower == teamLower) &&
			(season == 0 || match.Season == season) {
			stats.Matches++
			stats.GoalsFor += match.HomeGoal
			stats.GoalsAgainst += match.AwayGoal

			if homeLower == teamLower {
				stats.HomeMatches++
				stats.HomeGF += match.HomeGoal
				stats.HomeGA += match.AwayGoal

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
			} else {
				stats.AwayMatches++
				stats.AwayGF += match.HomeGoal
				stats.AwayGA += match.AwayGoal

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
	}

	stats.GoalDiff = stats.GoalsFor - stats.GoalsAgainst
	stats.Points = stats.Wins*3 + stats.Draws

	return stats
}

// GetHeadToHead calculates head-to-head record between two teams
func (s *SoccerServer) GetHeadToHead(team1, team2 string) (int, int, int) {
	team1Lower := strings.ToLower(team1)
	team2Lower := strings.ToLower(team2)
	team1Wins := 0
	team2Wins := 0
	draws := 0

	for _, match := range s.matches {
		homeLower := strings.ToLower(match.HomeTeam)
		awayLower := strings.ToLower(match.AwayTeam)

		if (homeLower == team1Lower && awayLower == team2Lower) ||
			(homeLower == team2Lower && awayLower == team1Lower) {
			if match.HomeGoal > match.AwayGoal {
				if homeLower == team1Lower {
					team1Wins++
				} else {
					team2Wins++
				}
			} else if match.HomeGoal < match.AwayGoal {
				if awayLower == team1Lower {
					team1Wins++
				} else {
					team2Wins++
				}
			} else {
				draws++
			}
		}
	}

	return team1Wins, team2Wins, draws
}

// GetPlayerByName searches for a player by name
func (s *SoccerServer) GetPlayerByName(name string) []Player {
	var results []Player
	nameLower := strings.ToLower(name)

	for _, player := range s.players {
		if strings.Contains(strings.ToLower(player.Name), nameLower) {
			results = append(results, player)
		}
	}

	// Sort by overall rating (highest first)
	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})

	return results
}

// GetPlayersByClub finds players by club
func (s *SoccerServer) GetPlayersByClub(club string) []Player {
	var results []Player
	clubLower := strings.ToLower(club)

	for _, player := range s.players {
		if strings.Contains(strings.ToLower(player.Club), clubLower) {
			results = append(results, player)
		}
	}

	// Sort by overall rating
	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})

	return results
}

// GetPlayersByPosition finds players by position
func (s *SoccerServer) GetPlayersByPosition(position string) []Player {
	var results []Player
	posLower := strings.ToLower(position)

	for _, player := range s.players {
		if strings.Contains(strings.ToLower(player.Position), posLower) {
			results = append(results, player)
		}
	}

	// Sort by overall rating
	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})

	return results
}

// GetBrazilianPlayers finds all Brazilian players
func (s *SoccerServer) GetBrazilianPlayers() []Player {
	var results []Player

	for _, player := range s.players {
		if strings.Contains(strings.ToLower(player.Nationality), "brazil") ||
			strings.Contains(strings.ToLower(player.Nationality), "brasil") {
			results = append(results, player)
		}
	}

	// Sort by overall rating
	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})

	return results
}

// GetTopScorersBySeason finds top scorers for a season
func (s *SoccerServer) GetTopScorersBySeason(season int) []struct {
	Team  string
	Goals int
} {
	goalsByTeam := make(map[string]int)

	for _, match := range s.matches {
		if season == 0 || match.Season == season {
			goalsByTeam[match.HomeTeam] += match.HomeGoal
			goalsByTeam[match.AwayTeam] += match.AwayGoal
		}
	}

	var results []struct {
		Team  string
		Goals int
	}
	for team, goals := range goalsByTeam {
		results = append(results, struct {
			Team  string
			Goals int
		}{team, goals})
	}

	// Sort by goals descending
	sort.Slice(results, func(i, j int) bool {
		return results[i].Goals > results[j].Goals
	})

	return results
}

// GetBiggestWins finds matches with the largest goal differences
func (s *SoccerServer) GetBiggestWins(limit int) []Match {
	type matchDiff struct {
		match Match
		diff  int
	}

	var diffs []matchDiff
	for _, match := range s.matches {
		diff := abs(match.HomeGoal - match.AwayGoal)
		if diff > 2 { // Only significant wins
			diffs = append(diffs, matchDiff{match, diff})
		}
	}

	// Sort by goal difference descending
	sort.Slice(diffs, func(i, j int) bool {
		return diffs[i].diff > diffs[j].diff
	})

	var results []Match
	for i := 0; i < min(limit, len(diffs)); i++ {
		results = append(results, diffs[i].match)
	}

	return results
}

// GetTeamRecordByCompetition gets a team's record in a specific competition
func (s *SoccerServer) GetTeamRecordByCompetition(team, competition string) TeamStats {
	teamLower := strings.ToLower(team)
	compLower := strings.ToLower(competition)
	var stats TeamStats
	stats.TeamName = team

	for _, match := range s.matches {
		if strings.Contains(strings.ToLower(match.Tournament), compLower) {
			homeLower := strings.ToLower(match.HomeTeam)
			awayLower := strings.ToLower(match.AwayTeam)

			if homeLower == teamLower || awayLower == teamLower {
				stats.Matches++
				stats.GoalsFor += match.HomeGoal
				stats.GoalsAgainst += match.AwayGoal

				if homeLower == teamLower {
					if match.HomeGoal > match.AwayGoal {
						stats.Wins++
					} else if match.HomeGoal == match.AwayGoal {
						stats.Draws++
					} else {
						stats.Losses++
					}
				} else {
					if match.AwayGoal > match.HomeGoal {
						stats.Wins++
					} else if match.AwayGoal == match.HomeGoal {
						stats.Draws++
					} else {
						stats.Losses++
					}
				}
			}
		}
	}

	stats.Points = stats.Wins * 3
	return stats
}

// GetSeasonStandings calculates the standings for a season
func (s *SoccerServer) GetSeasonStandings(season int) []TeamStats {
	teamStats := make(map[string]*TeamStats)

	for _, match := range s.matches {
		if match.Season != season {
			continue
		}

		homeTeam := match.HomeTeam
		awayTeam := match.AwayTeam

		if _, exists := teamStats[homeTeam]; !exists {
			teamStats[homeTeam] = &TeamStats{TeamName: homeTeam}
		}
		if _, exists := teamStats[awayTeam]; !exists {
			teamStats[awayTeam] = &TeamStats{TeamName: awayTeam}
		}

		homeStats := teamStats[homeTeam]
		awayStats := teamStats[awayTeam]

		homeStats.Matches++
		homeStats.GoalsFor += match.HomeGoal
		homeStats.GoalsAgainst += match.AwayGoal
		homeStats.HomeMatches++
		homeStats.HomeGF += match.HomeGoal
		homeStats.HomeGA += match.AwayGoal

		awayStats.Matches++
		awayStats.GoalsFor += match.AwayGoal
		awayStats.GoalsAgainst += match.HomeGoal
		awayStats.AwayMatches++
		awayStats.AwayGF += match.AwayGoal
		awayStats.AwayGA += match.HomeGoal

		if match.HomeGoal > match.AwayGoal {
			homeStats.Wins++
			homeStats.HomeWins++
			awayStats.Losses++
			awayStats.AwayLosses++
		} else if match.HomeGoal < match.AwayGoal {
			awayStats.Wins++
			awayStats.AwayWins++
			homeStats.Losses++
			homeStats.HomeLosses++
		} else {
			homeStats.Draws++
			homeStats.HomeDraws++
			awayStats.Draws++
			awayStats.AwayDraws++
		}
	}

	var standings []TeamStats
	for _, stats := range teamStats {
		stats.GoalDiff = stats.GoalsFor - stats.GoalsAgainst
		stats.Points = stats.Wins*3 + stats.Draws
		standings = append(standings, *stats)
	}

	// Sort by points, then goal difference, then goals scored
	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalDiff != standings[j].GoalDiff {
			return standings[i].GoalDiff > standings[j].GoalDiff
		}
		return standings[i].GoalsFor > standings[j].GoalsFor
	})

	return standings
}

// Helper functions
func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// HTTP Handlers

func matchesHandler(w http.ResponseWriter, r *http.Request) {
	team1 := r.URL.Query().Get("team1")
	team2 := r.URL.Query().Get("team2")
	seasonStr := r.URL.Query().Get("season")
	tournament := r.URL.Query().Get("tournament")
	season := 0
	if seasonStr != "" {
		season, _ = strconv.Atoi(seasonStr)
	}

	var matches []Match
	if team1 != "" && team2 != "" {
		matches = server.GetMatchesByTeams(team1, team2)
		if season > 0 {
			var filtered []Match
			for _, m := range matches {
				if m.Season == season {
					filtered = append(filtered, m)
				}
			}
			matches = filtered
		}
	} else if tournament != "" {
		matches = server.GetMatchesByTournament(tournament)
		if season > 0 {
			var filtered []Match
			for _, m := range matches {
				if m.Season == season {
					filtered = append(filtered, m)
				}
			}
			matches = filtered
		}
	} else if season > 0 {
		matches = server.GetMatchesBySeason(season)
	} else {
		matches = server.Matches()
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(matches)
}

func teamStatsHandler(w http.ResponseWriter, r *http.Request) {
	team := r.URL.Query().Get("team")
	seasonStr := r.URL.Query().Get("season")
	season := 0
	if seasonStr != "" {
		season, _ = strconv.Atoi(seasonStr)
	}

	if team == "" {
		http.Error(w, "team parameter required", http.StatusBadRequest)
		return
	}

	stats := server.GetTeamStats(team, season)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

func headToHeadHandler(w http.ResponseWriter, r *http.Request) {
	team1 := r.URL.Query().Get("team1")
	team2 := r.URL.Query().Get("team2")

	if team1 == "" || team2 == "" {
		http.Error(w, "team1 and team2 parameters required", http.StatusBadRequest)
		return
	}

	t1Wins, t2Wins, draws := server.GetHeadToHead(team1, team2)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"team1":       team1,
		"team1_wins":  t1Wins,
		"team2":       team2,
		"team2_wins":  t2Wins,
		"draws":       draws,
	})
}

func playersHandler(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	club := r.URL.Query().Get("club")
	position := r.URL.Query().Get("position")
	brazilian := r.URL.Query().Get("brazilian")

	var players []Player
	if name != "" {
		players = server.GetPlayerByName(name)
	} else if club != "" {
		players = server.GetPlayersByClub(club)
	} else if position != "" {
		players = server.GetPlayersByPosition(position)
	} else if brazilian == "true" {
		players = server.GetBrazilianPlayers()
		if club != "" {
			var filtered []Player
			for _, p := range players {
				if strings.Contains(strings.ToLower(p.Club), strings.ToLower(club)) {
					filtered = append(filtered, p)
				}
			}
			players = filtered
		}
	} else {
		players = server.Players()
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(players)
}

func standingsHandler(w http.ResponseWriter, r *http.Request) {
	seasonStr := r.URL.Query().Get("season")
	if seasonStr == "" {
		http.Error(w, "season parameter required", http.StatusBadRequest)
		return
	}
	season, _ := strconv.Atoi(seasonStr)

	standings := server.GetSeasonStandings(season)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(standings)
}

func biggestWinsHandler(w http.ResponseWriter, r *http.Request) {
	limitStr := r.URL.Query().Get("limit")
	limit := 10
	if limitStr != "" {
		limit, _ = strconv.Atoi(limitStr)
	}

	wins := server.GetBiggestWins(limit)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(wins)
}

func teamRecordHandler(w http.ResponseWriter, r *http.Request) {
	team := r.URL.Query().Get("team")
	competition := r.URL.Query().Get("competition")

	if team == "" || competition == "" {
		http.Error(w, "team and competition parameters required", http.StatusBadRequest)
		return
	}

	record := server.GetTeamRecordByCompetition(team, competition)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(record)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "ok",
		"matches":   len(server.Matches()),
		"players":   len(server.Players()),
		"tournaments": len(server.competitions),
	})
}

var server *SoccerServer

func main() {
	// Get data directory
	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		// Default to data/kaggle relative to executable
		execPath, err := os.Executable()
		if err != nil {
			dataDir = "./data/kaggle"
		} else {
			dataDir = filepath.Join(filepath.Dir(execPath), "data", "kaggle")
		}
	}

	// Initialize server
	server = NewSoccerServer()

	// Load data
	log.Printf("Loading data from: %s", dataDir)
	if err := server.LoadData(dataDir); err != nil {
		log.Printf("Error loading data: %v", err)
	}

	log.Printf("Loaded %d matches and %d players", len(server.Matches()), len(server.Players()))

	// Setup routes
	http.HandleFunc("/api/matches", matchesHandler)
	http.HandleFunc("/api/team-stats", teamStatsHandler)
	http.HandleFunc("/api/head-to-head", headToHeadHandler)
	http.HandleFunc("/api/players", playersHandler)
	http.HandleFunc("/api/standings", standingsHandler)
	http.HandleFunc("/api/biggest-wins", biggestWinsHandler)
	http.HandleFunc("/api/team-record", teamRecordHandler)
	http.HandleFunc("/health", healthHandler)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("Starting server on port %s...", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Error serving HTTP server: %v", err)
	}
}
