// Package server provides the MCP server for Brazilian soccer data.
package server

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Data directory path - resolved at runtime based on module location
var DataDir string

func init() {
	// Try to find the data directory relative to the module root
	// Go tests run from the package directory, so we need to resolve relative to module root
	// The module root is one level up from the server package directory
	moduleRoot, _ := filepath.Abs("..")
	dataPath := filepath.Join(moduleRoot, "data", "kaggle")
	if _, err := os.Stat(dataPath); err == nil {
		DataDir = dataPath
	} else {
		// Fallback to relative path if module root doesn't work
		DataDir = "data/kaggle"
	}
}

// Match represents a soccer match
type Match struct {
	ID             string
	Datetime       time.Time
	HomeTeam       string
	HomeTeamState  string
	AwayTeam       string
	AwayTeamState  string
	HomeGoal       int
	AwayGoal       int
	Season         int
	Round          int
	Stage          string
	Tournament     string
	HomeCorner     int
	AwayCorner     int
	HomeAttack     int
	AwayAttack     int
	HomeShot       int
	AwayShot       int
	Time           string
	Date           string
	HtResult       string
	AtResult       string
	TotalCorners   int
	HomePenalty    int
	AwayPenalty    int
	HomeYellowCard int
	AwayYellowCard int
	HomeRedCard    int
	AwayRedCard    int
}

// Player represents a FIFA player
type Player struct {
	ID              int
	Name            string
	Age             int
	Nationality     string
	Overall         int
	Potential       int
	Club            string
	Position        string
	JerseyNumber    int
	Height          string
	Weight          string
	PreferredFoot   string
	InternationalReputation int
	WeakFoot        int
	SkillMoves      int
	WorkRate        string
	BodyType        string
	PositionList    []string
	// Skill ratings
	Crossing       int
	Finishing      int
	HeadingAccuracy int
	ShortPassing   int
	Volleys        int
	Dribbling      int
	Curve          int
	FKAccuracy     int
	LongPassing    int
	BallControl    int
	Acceleration   int
	SprintSpeed    int
	Agility        int
	Reactions      int
	Balance        int
	ShotPower      int
	Jumping        int
	Stamina        int
	Strength       int
	LongShots      int
	Aggression     int
	Interceptions int
	Positioning    int
	Vision         int
	Penalties      int
	Composure      int
	Marking        int
	StandingTackle int
	SlidingTackle int
	GKDiving       int
	GKHandling     int
	GKKicking      int
	GKPositioning  int
	GKReflexes     int
}

// TeamStats represents aggregated statistics for a team
type TeamStats struct {
	TeamName     string
	Season       int
	Competition  string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	GoalDiff     int
	Points       int
	HomeMatches  int
	HomeWins     int
	HomeDraws    int
	HomeLosses   int
	HomeGF       int
	HomeGA       int
	AwayMatches  int
	AwayWins     int
	AwayDraws    int
	AwayLosses   int
	AwayGF       int
	AwayGA       int
}

// CompetitionTable represents a league table for a competition
type CompetitionTable struct {
	Competition string
	Season      int
	Teams       []TeamStanding
}

// TeamStanding represents a team's position in a league table
type TeamStanding struct {
	Team          string
	Played        int
	Won           int
	Drawn         int
	Lost          int
	GoalsFor      int
	GoalsAgainst  int
	GoalDifference int
	Points        int
}

// Result represents a query result
type Result struct {
	Matches   []Match
	Players   []Player
	TeamStats []TeamStats
	Table     CompetitionTable
	Message   string
	Count     int
	Error     string
}

// DataStore represents the data storage interface
type DataStore struct {
	BrasileiraoMatches    []Match
	CopaDoBrasilMatches   []Match
	CopaLibertadoresMatches []Match
	BRFootballMatches     []Match
	NovoCampeonatoMatches []Match
	Players               []Player
}

// LoadCSV loads a CSV file and returns the data
func LoadCSV(filePath string) ([][]string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	return records, nil
}

// NormalizeTeamName normalizes team names for consistent matching
func NormalizeTeamName(name string) string {
	// Remove state suffix like -SP, -RJ, -PE
	name = strings.TrimSpace(name)
	name = strings.Split(name, "-")[0]
	name = strings.TrimSpace(name)
	return name
}

// LoadBrasileiraoMatches loads Brasileirao match data
func (ds *DataStore) LoadBrasileiraoMatches() error {
	filePath := filepath.Join(DataDir, "Brasileirao_Matches.csv")
	records, err := LoadCSV(filePath)
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header
	for _, record := range records[1:] {
		if len(record) < 9 {
			continue
		}

		match := Match{}
		match.ID = fmt.Sprintf("brasileirao-%d", len(ds.BrasileiraoMatches)+1)

		// Parse datetime
		if record[0] != "" {
			if dt, err := time.Parse("2006-01-02 15:04:05", record[0]); err == nil {
				match.Datetime = dt
			}
		}

		match.HomeTeam = strings.TrimSpace(record[1])
		match.HomeTeamState = strings.TrimSpace(record[2])
		match.AwayTeam = strings.TrimSpace(record[3])
		match.AwayTeamState = strings.TrimSpace(record[4])

		if record[5] != "" {
			match.HomeGoal, _ = strconv.Atoi(record[5])
		}
		if record[6] != "" {
			match.AwayGoal, _ = strconv.Atoi(record[6])
		}
		if record[7] != "" {
			match.Season, _ = strconv.Atoi(record[7])
		}
		if record[8] != "" {
			match.Round, _ = strconv.Atoi(record[8])
		}

		ds.BrasileiraoMatches = append(ds.BrasileiraoMatches, match)
	}

	return nil
}

// LoadCopaDoBrasilMatches loads Copa do Brasil match data
func (ds *DataStore) LoadCopaDoBrasilMatches() error {
	filePath := filepath.Join(DataDir, "Brazilian_Cup_Matches.csv")
	records, err := LoadCSV(filePath)
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header
	for _, record := range records[1:] {
		if len(record) < 7 {
			continue
		}

		match := Match{}
		match.ID = fmt.Sprintf("copa-brasil-%d", len(ds.CopaDoBrasilMatches)+1)

		// Parse datetime
		if record[1] != "" {
			if dt, err := time.Parse("2006-01-02 15:04:05", record[1]); err == nil {
				match.Datetime = dt
			} else if dt, err := time.Parse("2006-01-02", record[1]); err == nil {
				match.Datetime = dt
			}
		}

		match.HomeTeam = strings.TrimSpace(record[2])
		match.AwayTeam = strings.TrimSpace(record[3])

		if record[4] != "" {
			match.HomeGoal, _ = strconv.Atoi(record[4])
		}
		if record[5] != "" {
			match.AwayGoal, _ = strconv.Atoi(record[5])
		}
		if record[6] != "" {
			match.Season, _ = strconv.Atoi(record[6])
		}

		// Parse round
		if record[0] != "" {
			match.Round, _ = strconv.Atoi(strings.TrimSpace(record[0]))
		}

		ds.CopaDoBrasilMatches = append(ds.CopaDoBrasilMatches, match)
	}

	return nil
}

// LoadCopaLibertadoresMatches loads Copa Libertadores match data
func (ds *DataStore) LoadCopaLibertadoresMatches() error {
	filePath := filepath.Join(DataDir, "Libertadores_Matches.csv")
	records, err := LoadCSV(filePath)
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header
	for _, record := range records[1:] {
		if len(record) < 7 {
			continue
		}

		match := Match{}
		match.ID = fmt.Sprintf("libertadores-%d", len(ds.CopaLibertadoresMatches)+1)

		// Parse datetime
		if record[0] != "" {
			if dt, err := time.Parse("2006-01-02 15:04:05", record[0]); err == nil {
				match.Datetime = dt
			}
		}

		match.HomeTeam = strings.TrimSpace(record[1])
		match.AwayTeam = strings.TrimSpace(record[2])

		if record[3] != "" {
			match.HomeGoal, _ = strconv.Atoi(record[3])
		}
		if record[4] != "" {
			match.AwayGoal, _ = strconv.Atoi(record[4])
		}
		if record[5] != "" {
			match.Season, _ = strconv.Atoi(record[5])
		}
		if len(record) > 6 && record[6] != "" {
			match.Stage = strings.TrimSpace(record[6])
		}

		ds.CopaLibertadoresMatches = append(ds.CopaLibertadoresMatches, match)
	}

	return nil
}

// LoadBRFootballMatches loads BR-Football-Dataset match data
func (ds *DataStore) LoadBRFootballMatches() error {
	filePath := filepath.Join(DataDir, "BR-Football-Dataset.csv")
	records, err := LoadCSV(filePath)
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header
	for _, record := range records[1:] {
		if len(record) < 18 {
			continue
		}

		match := Match{}
		match.ID = fmt.Sprintf("br-football-%d", len(ds.BRFootballMatches)+1)
		match.Tournament = strings.TrimSpace(record[0])
		match.HomeTeam = strings.TrimSpace(record[1])

		if record[2] != "" {
			match.HomeGoal, _ = strconv.Atoi(strings.TrimSpace(record[2]))
		}
		if record[3] != "" {
			match.AwayGoal, _ = strconv.Atoi(strings.TrimSpace(record[3]))
		}
		match.AwayTeam = strings.TrimSpace(record[4])

		if record[5] != "" {
			match.HomeCorner, _ = strconv.Atoi(strings.TrimSpace(record[5]))
		}
		if record[6] != "" {
			match.AwayCorner, _ = strconv.Atoi(strings.TrimSpace(record[6]))
		}
		if record[7] != "" {
			match.HomeAttack, _ = strconv.Atoi(strings.TrimSpace(record[7]))
		}
		if record[8] != "" {
			match.AwayAttack, _ = strconv.Atoi(strings.TrimSpace(record[8]))
		}
		if record[9] != "" {
			match.HomeShot, _ = strconv.Atoi(strings.TrimSpace(record[9]))
		}
		if record[10] != "" {
			match.AwayShot, _ = strconv.Atoi(strings.TrimSpace(record[10]))
		}
		match.Time = strings.TrimSpace(record[11])
		match.Date = strings.TrimSpace(record[12])

		if record[13] != "" {
			match.HtResult = strings.TrimSpace(record[13])
		}
		if record[14] != "" {
			match.AtResult = strings.TrimSpace(record[14])
		}
		if record[16] != "" {
			match.TotalCorners, _ = strconv.Atoi(strings.TrimSpace(record[16]))
		}

		// Parse date
		if record[12] != "" {
			if dt, err := time.Parse("2006-01-02", record[12]); err == nil {
				match.Datetime = dt
			}
		}

		ds.BRFootballMatches = append(ds.BRFootballMatches, match)
	}

	return nil
}

// LoadNovoCampeonatoMatches loads novo_campeonato_brasileiro match data
func (ds *DataStore) LoadNovoCampeonatoMatches() error {
	filePath := filepath.Join(DataDir, "novo_campeonato_brasileiro.csv")
	records, err := LoadCSV(filePath)
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header
	for _, record := range records[1:] {
		if len(record) < 12 {
			continue
		}

		match := Match{}
		match.ID = strings.TrimSpace(record[0])

		// Parse date in Brazilian format DD/MM/YYYY
		if record[1] != "" {
			if dt, err := time.Parse("02/01/2006", record[1]); err == nil {
				match.Datetime = dt
			}
		}
		match.Date = strings.TrimSpace(record[1])

		if record[2] != "" {
			match.Season, _ = strconv.Atoi(record[2])
		}
		if record[3] != "" {
			match.Round, _ = strconv.Atoi(record[3])
		}
		match.HomeTeam = strings.TrimSpace(record[4])
		match.AwayTeam = strings.TrimSpace(record[5])

		if record[6] != "" {
			match.HomeGoal, _ = strconv.Atoi(record[6])
		}
		if record[7] != "" {
			match.AwayGoal, _ = strconv.Atoi(record[7])
		}
		match.HomeTeamState = strings.TrimSpace(record[8])
		match.AwayTeamState = strings.TrimSpace(record[9])

		// Extract winner
		if record[10] != "" {
			winner := strings.TrimSpace(record[10])
			if winner == "Mandante" {
				match.HtResult = "WON"
			} else if winner == "Visitante" {
				match.HtResult = "LOST"
			} else if winner == "Empate" {
				match.HtResult = "DRAW"
			}
		}

		// Arena
		if len(record) > 11 && record[11] != "" {
			match.HomeTeamState = strings.TrimSpace(record[11])
		}

		ds.NovoCampeonatoMatches = append(ds.NovoCampeonatoMatches, match)
	}

	return nil
}

// LoadPlayers loads FIFA player data
func (ds *DataStore) LoadPlayers() error {
	filePath := filepath.Join(DataDir, "fifa_data.csv")
	records, err := LoadCSV(filePath)
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Column mapping from the CSV header
	colIndex := make(map[string]int)
	if len(records) > 0 {
		for i, col := range records[0] {
			// Clean column name
			col = strings.TrimSpace(strings.ReplaceAll(col, "\u00ef\u00bb\u00bf", ""))
			colIndex[col] = i
		}
	}

	// Skip header
	for _, record := range records[1:] {
		if len(record) < 3 {
			continue
		}

		player := Player{}

		// Get column indices with defaults
		idIdx := colIndex["ID"]
		nameIdx := colIndex["Name"]
		ageIdx := colIndex["Age"]
		nationalityIdx := colIndex["Nationality"]
		overallIdx := colIndex["Overall"]
		potentialIdx := colIndex["Potential"]
		clubIdx := colIndex["Club"]
		positionIdx := colIndex["Position"]
		jerseyIdx := colIndex["Jersey Number"]

		if idIdx >= 0 && idIdx < len(record) {
			id, _ := strconv.Atoi(record[idIdx])
			player.ID = id
		}
		if nameIdx >= 0 && nameIdx < len(record) {
			player.Name = strings.TrimSpace(record[nameIdx])
		}
		if ageIdx >= 0 && ageIdx < len(record) {
			player.Age, _ = strconv.Atoi(record[ageIdx])
		}
		if nationalityIdx >= 0 && nationalityIdx < len(record) {
			player.Nationality = strings.TrimSpace(record[nationalityIdx])
		}
		if overallIdx >= 0 && overallIdx < len(record) {
			player.Overall, _ = strconv.Atoi(record[overallIdx])
		}
		if potentialIdx >= 0 && potentialIdx < len(record) {
			player.Potential, _ = strconv.Atoi(record[potentialIdx])
		}
		if clubIdx >= 0 && clubIdx < len(record) {
			player.Club = strings.TrimSpace(record[clubIdx])
		}
		if positionIdx >= 0 && positionIdx < len(record) {
			player.Position = strings.TrimSpace(record[positionIdx])
		}
		if jerseyIdx >= 0 && jerseyIdx < len(record) {
			player.JerseyNumber, _ = strconv.Atoi(record[jerseyIdx])
		}

		// Extract position list
		if player.Position != "" {
			player.PositionList = strings.Split(player.Position, ",")
		}

		// Parse additional attributes
		ds.parsePlayerAttributes(player, record, colIndex)

		ds.Players = append(ds.Players, player)
	}

	return nil
}

// parsePlayerAttributes parses skill rating attributes from the record
func (ds *DataStore) parsePlayerAttributes(player Player, record []string, colIndex map[string]int) {
	// Map of attribute names to player struct fields
	attributes := map[string]*int{
		"Crossing":       &player.Crossing,
		"Finishing":      &player.Finishing,
		"HeadingAccuracy": &player.HeadingAccuracy,
		"ShortPassing":   &player.ShortPassing,
		"Volleys":        &player.Volleys,
		"Dribbling":      &player.Dribbling,
		"Curve":          &player.Curve,
		"FKAccuracy":     &player.FKAccuracy,
		"LongPassing":    &player.LongPassing,
		"BallControl":    &player.BallControl,
		"Acceleration":   &player.Acceleration,
		"SprintSpeed":    &player.SprintSpeed,
		"Agility":        &player.Agility,
		"Reactions":      &player.Reactions,
		"Balance":        &player.Balance,
		"ShotPower":      &player.ShotPower,
		"Jumping":        &player.Jumping,
		"Stamina":        &player.Stamina,
		"Strength":       &player.Strength,
		"LongShots":      &player.LongShots,
		"Aggression":     &player.Aggression,
		"Interceptions":  &player.Interceptions,
		"Positioning":    &player.Positioning,
		"Vision":         &player.Vision,
		"Penalties":      &player.Penalties,
		"Composure":      &player.Composure,
		"Marking":        &player.Marking,
		"StandingTackle": &player.StandingTackle,
		"SlidingTackle":  &player.SlidingTackle,
		"GKDiving":       &player.GKDiving,
		"GKHandling":     &player.GKHandling,
		"GKKicking":      &player.GKKicking,
		"GKPositioning":  &player.GKPositioning,
		"GKReflexes":     &player.GKReflexes,
	}

	for attrName, field := range attributes {
		if idx, ok := colIndex[attrName]; ok && idx < len(record) {
			if record[idx] != "" {
				// Handle values with +/- (e.g., "88+2")
				valStr := strings.TrimSpace(record[idx])
				valStr = strings.Split(valStr, "+")[0]
				valStr = strings.Split(valStr, "-")[0]
				val, err := strconv.Atoi(valStr)
				if err == nil {
					*field = val
				}
			}
		}
	}

	// Parse Preferred Foot
	if idx, ok := colIndex["Preferred Foot"]; ok && idx < len(record) {
		player.PreferredFoot = strings.TrimSpace(record[idx])
	}

	// Parse International Reputation
	if idx, ok := colIndex["International Reputation"]; ok && idx < len(record) {
		if record[idx] != "" {
			player.InternationalReputation, _ = strconv.Atoi(record[idx])
		}
	}

	// Parse Weak Foot
	if idx, ok := colIndex["Weak Foot"]; ok && idx < len(record) {
		if record[idx] != "" {
			player.WeakFoot, _ = strconv.Atoi(record[idx])
		}
	}

	// Parse Skill Moves
	if idx, ok := colIndex["Skill Moves"]; ok && idx < len(record) {
		if record[idx] != "" {
			player.SkillMoves, _ = strconv.Atoi(record[idx])
		}
	}

	// Parse Work Rate
	if idx, ok := colIndex["Work Rate"]; ok && idx < len(record) {
		player.WorkRate = strings.TrimSpace(record[idx])
	}

	// Parse Body Type
	if idx, ok := colIndex["Body Type"]; ok && idx < len(record) {
		player.BodyType = strings.TrimSpace(record[idx])
	}

	// Parse Height and Weight
	if idx, ok := colIndex["Height"]; ok && idx < len(record) {
		player.Height = strings.TrimSpace(record[idx])
	}
	if idx, ok := colIndex["Weight"]; ok && idx < len(record) {
		player.Weight = strings.TrimSpace(record[idx])
	}
}

// LoadAllData loads all data from CSV files
func (ds *DataStore) LoadAllData() error {
	fmt.Println("Loading Brasileirao matches...")
	if err := ds.LoadBrasileiraoMatches(); err != nil {
		return err
	}
	fmt.Printf("Loaded %d Brasileirao matches\n", len(ds.BrasileiraoMatches))

	fmt.Println("Loading Copa do Brasil matches...")
	if err := ds.LoadCopaDoBrasilMatches(); err != nil {
		return err
	}
	fmt.Printf("Loaded %d Copa do Brasil matches\n", len(ds.CopaDoBrasilMatches))

	fmt.Println("Loading Copa Libertadores matches...")
	if err := ds.LoadCopaLibertadoresMatches(); err != nil {
		return err
	}
	fmt.Printf("Loaded %d Copa Libertadores matches\n", len(ds.CopaLibertadoresMatches))

	fmt.Println("Loading BR Football matches...")
	if err := ds.LoadBRFootballMatches(); err != nil {
		return err
	}
	fmt.Printf("Loaded %d BR Football matches\n", len(ds.BRFootballMatches))

	fmt.Println("Loading Novo Campeonato matches...")
	if err := ds.LoadNovoCampeonatoMatches(); err != nil {
		return err
	}
	fmt.Printf("Loaded %d Novo Campeonato matches\n", len(ds.NovoCampeonatoMatches))

	fmt.Println("Loading players...")
	if err := ds.LoadPlayers(); err != nil {
		return err
	}
	fmt.Printf("Loaded %d players\n", len(ds.Players))

	return nil
}

// GetMatchesByTeams finds matches between two teams
func (ds *DataStore) GetMatchesByTeams(team1, team2 string, limit int) []Match {
	var matches []Match
	team1Norm := NormalizeTeamName(team1)
	team2Norm := NormalizeTeamName(team2)

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, match := range allMatches {
		homeNorm := NormalizeTeamName(match.HomeTeam)
		awayNorm := NormalizeTeamName(match.AwayTeam)

		// Check if either team is involved
		if (homeNorm == team1Norm && awayNorm == team2Norm) ||
			(homeNorm == team2Norm && awayNorm == team1Norm) {
			matches = append(matches, match)
			if limit > 0 && len(matches) >= limit {
				break
			}
		}
	}

	// Sort by date descending
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Datetime.After(matches[j].Datetime)
	})

	return matches
}

// GetTeamStats calculates statistics for a team
func (ds *DataStore) GetTeamStats(team string, season int, competition string) TeamStats {
	teamNorm := NormalizeTeamName(team)
	stats := TeamStats{TeamName: team, Season: season}

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, match := range allMatches {
		// Filter by competition if specified
		if competition != "" {
			if match.Tournament != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(competition)) {
				continue
			}
			// Check Brasileirão
			if strings.Contains(strings.ToLower(match.HomeTeam), "brasileirao") || strings.Contains(strings.ToLower(match.AwayTeam), "brasileirao") {
				// Keep if competition is "brasileirao" or "brasileirão"
			} else if competition == "brasileirao" || competition == "brasileirão" {
				continue
			}
		}

		// Filter by season if specified
		if season > 0 && match.Season != season {
			continue
		}

		homeNorm := NormalizeTeamName(match.HomeTeam)
		awayNorm := NormalizeTeamName(match.AwayTeam)

		if homeNorm == teamNorm {
			stats.Matches++
			stats.GoalsFor += match.HomeGoal
			stats.GoalsAgainst += match.AwayGoal
			if match.HomeGoal > match.AwayGoal {
				stats.Wins++
				stats.Points += 3
			} else if match.HomeGoal == match.AwayGoal {
				stats.Draws++
				stats.Points += 1
			} else {
				stats.Losses++
			}
			stats.HomeMatches++
			stats.HomeGF += match.HomeGoal
			stats.HomeGA += match.AwayGoal
			if match.HomeGoal > match.AwayGoal {
				stats.HomeWins++
			} else if match.HomeGoal == match.AwayGoal {
				stats.HomeDraws++
			} else {
				stats.HomeLosses++
			}
		} else if awayNorm == teamNorm {
			stats.Matches++
			stats.GoalsFor += match.AwayGoal
			stats.GoalsAgainst += match.HomeGoal
			if match.AwayGoal > match.HomeGoal {
				stats.Wins++
				stats.Points += 3
			} else if match.AwayGoal == match.HomeGoal {
				stats.Draws++
				stats.Points += 1
			} else {
				stats.Losses++
			}
			stats.AwayMatches++
			stats.AwayGF += match.AwayGoal
			stats.AwayGA += match.HomeGoal
			if match.AwayGoal > match.HomeGoal {
				stats.AwayWins++
			} else if match.AwayGoal == match.HomeGoal {
				stats.AwayDraws++
			} else {
				stats.AwayLosses++
			}
		}
	}

	stats.GoalDiff = stats.GoalsFor - stats.GoalsAgainst

	return stats
}

// GetHeadToHead calculates head-to-head statistics between two teams
func (ds *DataStore) GetHeadToHead(team1, team2 string) (int, int, int) {
	team1Norm := NormalizeTeamName(team1)
	team2Norm := NormalizeTeamName(team2)
	team1Wins := 0
	team2Wins := 0
	draws := 0

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, match := range allMatches {
		homeNorm := NormalizeTeamName(match.HomeTeam)
		awayNorm := NormalizeTeamName(match.AwayTeam)

		// Check if either team is involved
		if (homeNorm == team1Norm && awayNorm == team2Norm) ||
			(homeNorm == team2Norm && awayNorm == team1Norm) {
			if match.HomeGoal > match.AwayGoal {
				if homeNorm == team1Norm {
					team1Wins++
				} else {
					team2Wins++
				}
			} else if match.HomeGoal == match.AwayGoal {
				draws++
			} else {
				if awayNorm == team1Norm {
					team1Wins++
				} else {
					team2Wins++
				}
			}
		}
	}

	return team1Wins, team2Wins, draws
}

// GetPlayerByName searches for players by name
func (ds *DataStore) GetPlayerByName(name string, limit int) []Player {
	var players []Player
	nameLower := strings.ToLower(name)

	for _, player := range ds.Players {
		if strings.Contains(strings.ToLower(player.Name), nameLower) ||
			strings.Contains(strings.ToLower(player.Club), nameLower) {
			players = append(players, player)
			if limit > 0 && len(players) >= limit {
				break
			}
		}
	}

	// Sort by overall rating descending
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	return players
}

// GetPlayersByClub gets all players from a specific club
func (ds *DataStore) GetPlayersByClub(club string) []Player {
	var players []Player
	clubNorm := NormalizeTeamName(club)

	for _, player := range ds.Players {
		clubNormPlayer := NormalizeTeamName(player.Club)
		if clubNormPlayer == clubNorm {
			players = append(players, player)
		}
	}

	// Sort by overall rating descending
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	return players
}

// GetPlayersByNationality gets players from a specific nationality
func (ds *DataStore) GetPlayersByNationality(nationality string) []Player {
	var players []Player
	natLower := strings.ToLower(nationality)

	for _, player := range ds.Players {
		if strings.Contains(strings.ToLower(player.Nationality), natLower) {
			players = append(players, player)
		}
	}

	// Sort by overall rating descending
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	return players
}

// GetPlayersByPosition gets players by position
func (ds *DataStore) GetPlayersByPosition(position string) []Player {
	var players []Player
	posLower := strings.ToLower(position)

	for _, player := range ds.Players {
		if strings.Contains(strings.ToLower(player.Position), posLower) {
			players = append(players, player)
		}
	}

	// Sort by overall rating descending
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	return players
}

// GetTeamMatchHistory gets the match history for a team
func (ds *DataStore) GetTeamMatchHistory(team string, limit int) []Match {
	var matches []Match
	teamNorm := NormalizeTeamName(team)

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, match := range allMatches {
		homeNorm := NormalizeTeamName(match.HomeTeam)
		awayNorm := NormalizeTeamName(match.AwayTeam)

		if homeNorm == teamNorm || awayNorm == teamNorm {
			matches = append(matches, match)
			if limit > 0 && len(matches) >= limit {
				break
			}
		}
	}

	// Sort by date descending
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Datetime.After(matches[j].Datetime)
	})

	return matches
}

// GetMatchResult returns the result of a match
func (ds *DataStore) GetMatchResult(match Match) string {
	if match.HomeGoal > match.AwayGoal {
		return fmt.Sprintf("%d-%d", match.HomeGoal, match.AwayGoal)
	} else if match.HomeGoal < match.AwayGoal {
		return fmt.Sprintf("%d-%d", match.HomeGoal, match.AwayGoal)
	}
	return fmt.Sprintf("%d-%d", match.HomeGoal, match.AwayGoal)
}

// FindTeamByName finds a team in the data by name
func (ds *DataStore) FindTeamByName(name string) []string {
	teams := make(map[string]bool)
	nameLower := strings.ToLower(name)

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, match := range allMatches {
		if strings.Contains(strings.ToLower(match.HomeTeam), nameLower) {
			teams[NormalizeTeamName(match.HomeTeam)] = true
		}
		if strings.Contains(strings.ToLower(match.AwayTeam), nameLower) {
			teams[NormalizeTeamName(match.AwayTeam)] = true
		}
	}

	result := make([]string, 0, len(teams))
	for team := range teams {
		result = append(result, team)
	}

	sort.Strings(result)
	return result
}

// GetTeamList returns all unique teams in the data
func (ds *DataStore) GetTeamList() []string {
	teams := make(map[string]bool)

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, match := range allMatches {
		teams[NormalizeTeamName(match.HomeTeam)] = true
		teams[NormalizeTeamName(match.AwayTeam)] = true
	}

	result := make([]string, 0, len(teams))
	for team := range teams {
		result = append(result, team)
	}

	sort.Strings(result)
	return result
}

// calculateLeagueTable calculates the league table for a competition and season
func (ds *DataStore) calculateLeagueTable(competition string, season int) CompetitionTable {
	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	teamStats := make(map[string]*TeamStanding)

	for _, match := range allMatches {
		if match.Season != season {
			continue
		}

		// Check if this match belongs to the specified competition
		if !matchBelongsToCompetitionForStore(&match, competition) {
			continue
		}

		homeTeam := NormalizeTeamName(match.HomeTeam)
		awayTeam := NormalizeTeamName(match.AwayTeam)

		if _, exists := teamStats[homeTeam]; !exists {
			teamStats[homeTeam] = &TeamStanding{Team: homeTeam}
		}
		if _, exists := teamStats[awayTeam]; !exists {
			teamStats[awayTeam] = &TeamStanding{Team: awayTeam}
		}

		homeStats := teamStats[homeTeam]
		awayStats := teamStats[awayTeam]

		homeStats.Played++
		awayStats.Played++
		homeStats.GoalsFor += match.HomeGoal
		homeStats.GoalsAgainst += match.AwayGoal
		awayStats.GoalsFor += match.AwayGoal
		awayStats.GoalsAgainst += match.HomeGoal

		if match.HomeGoal > match.AwayGoal {
			homeStats.Won++
			homeStats.Points += 3
			awayStats.Lost++
		} else if match.HomeGoal < match.AwayGoal {
			awayStats.Won++
			awayStats.Points += 3
			homeStats.Lost++
		} else {
			homeStats.Drawn++
			awayStats.Drawn++
			homeStats.Points += 1
			awayStats.Points += 1
		}
	}

	// Convert to slice and sort
	var teams []TeamStanding
	for _, stats := range teamStats {
		stats.GoalDifference = stats.GoalsFor - stats.GoalsAgainst
		teams = append(teams, *stats)
	}

	sort.Slice(teams, func(i, j int) bool {
		if teams[i].Points == teams[j].Points {
			return teams[i].GoalDifference > teams[j].GoalDifference
		}
		return teams[i].Points > teams[j].Points
	})

	return CompetitionTable{
		Competition: competition,
		Season:      season,
		Teams:       teams,
	}
}

func matchBelongsToCompetitionForStore(match *Match, competition string) bool {
	if competition == "" {
		return true
	}

	compLower := strings.ToLower(competition)

	// Check tournament name
	if match.Tournament != "" && strings.Contains(strings.ToLower(match.Tournament), compLower) {
		return true
	}

	// Check for Brasileirão/Brasileirao
	if compLower == "brasileirao" || compLower == "brasileirão" {
		// Check if it's a Brasileirão match
		if strings.Contains(strings.ToLower(match.HomeTeam), "brasileirao") ||
			strings.Contains(strings.ToLower(match.AwayTeam), "brasileirao") {
			return true
		}
		// Check season 2003-2019 data
		if match.Season >= 2003 && match.Season <= 2019 {
			return true
		}
		return false
	}

	// Check other competitions
	if strings.Contains(strings.ToLower(match.Tournament), compLower) ||
		strings.Contains(strings.ToLower(match.HomeTeam), compLower) ||
		strings.Contains(strings.ToLower(match.AwayTeam), compLower) {
		return true
	}

	return false
}
