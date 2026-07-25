package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Match represents a soccer match
type Match struct {
	ID           string
	Datetime     time.Time
	HomeTeam     string
	HomeTeamState string
	AwayTeam     string
	AwayTeamState string
	HomeGoal     int
	AwayGoal     int
	Season       int
	Round        string
	Stage        string
	Tournament   string
}

// TeamStats represents aggregated statistics for a team
type TeamStats struct {
	TeamName       string
	Matches        int
	Wins           int
	Draws          int
	Losses         int
	GoalsFor       int
	GoalsAgainst   int
	Points         int
	HomeMatches    int
	HomeWins       int
	HomeDraws      int
	HomeLosses     int
	AwayMatches    int
	AwayWins       int
	AwayDraws      int
	AwayLosses     int
	AvgGoalsPerMatch float64
	WinRate        float64
	HomeGoalsFor   int
	HomeGoalsAgainst int
	AwayGoalsFor   int
	AwayGoalsAgainst int
}

// Player represents a FIFA player record
type Player struct {
	ID                int
	Name              string
	Age               int
	Nationality       string
	Overall           int
	Potential         int
	Club              string
	Position          string
	JerseyNumber      int
	Height            string
	Weight            string
	PreferredFoot     string
	InternationalReputation int
	WeakFoot          int
	SkillMoves        int
	WorkRate          string
	BodyType          string
	LS                int
	ST                int
	RS                int
	LW                int
	LF                int
	CF                int
	RF                int
	RW                int
	LAM               int
	CAM               int
	RAM               int
	LM                int
	LCM               int
	CM                int
	RCM               int
	RM                int
	LWB               int
	LDM               int
	CDM               int
	RDM               int
	RWB               int
	LB                int
	LCB               int
	CB                int
	RCB               int
	RB                int
	Crossing          int
	Finishing         int
	HeadingAccuracy   int
	ShortPassing      int
	Volleys           int
	Dribbling         int
	Curve             int
	FKAccuracy        int
	LongPassing       int
	BallControl       int
	Acceleration      int
	SprintSpeed       int
	Agility           int
	Reactions         int
	Balance           int
	ShotPower         int
	Jumping           int
	Stamina           int
	Strength          int
	LongShots         int
	Aggression        int
	Interceptions     int
	Positioning       int
	Vision            int
	Penalties         int
	Composure         int
	Marking           int
	StandingTackle    int
	SlidingTackle     int
	GKDiving          int
	GKHandling        int
	GKKicking         int
	GKPositioning     int
	GKReflexes        int
}

// Competition represents a tournament/competition
type Competition struct {
	Name        string
	Season      int
	TeamStats   map[string]*TeamStats
	Standings   []TeamStanding
}

// TeamStanding represents a team's position in a competition
type TeamStanding struct {
	TeamName   string
	Matches    int
	Wins       int
	Draws      int
	Losses     int
	GoalsFor   int
	GoalsAgainst int
	Points     int
}

// DataStore holds all loaded data
type DataStore struct {
	BrasileiraoMatches      []Match
	CopaDoBrasilMatches     []Match
	CopaLibertadoresMatches []Match
	BRFootballMatches       []Match
	NovoCampeonatoMatches   []Match
	Players                 []Player
}

// NewDataStore creates a new empty data store
func NewDataStore() *DataStore {
	return &DataStore{
		BrasileiraoMatches:      []Match{},
		CopaDoBrasilMatches:     []Match{},
		CopaLibertadoresMatches: []Match{},
		BRFootballMatches:       []Match{},
		NovoCampeonatoMatches:   []Match{},
		Players:                 []Player{},
	}
}

// LoadBrasileiraoMatches loads the Brasileirao CSV file
func (ds *DataStore) LoadBrasileiraoMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	for i, record := range records {
		if i == 0 { // skip header
			continue
		}
		if len(record) < 9 {
			continue
		}

		datetime, err := time.Parse("2006-01-02 15:04:05", record[0])
		if err != nil {
			continue
		}

		homeTeamState := ""
		if len(record) > 2 {
			homeTeamState = record[2]
		}
		awayTeamState := ""
		if len(record) > 4 {
			awayTeamState = record[4]
		}

		homeGoal, _ := strconv.Atoi(record[5])
		awayGoal, _ := strconv.Atoi(record[6])
		season, _ := strconv.Atoi(record[7])
		round := record[8]

		ds.BrasileiraoMatches = append(ds.BrasileiraoMatches, Match{
			ID:            fmt.Sprintf("brasileirao-%d-%s", season, record[0]),
			Datetime:      datetime,
			HomeTeam:      normalizeTeamName(record[1]),
			HomeTeamState: homeTeamState,
			AwayTeam:      normalizeTeamName(record[3]),
			AwayTeamState: awayTeamState,
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Season:        season,
			Round:         round,
		})
	}

	return nil
}

// LoadCopaDoBrasilMatches loads the Copa do Brasil CSV file
func (ds *DataStore) LoadCopaDoBrasilMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1 // allow variable fields
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	for i, record := range records {
		if i == 0 { // skip header
			continue
		}
		if len(record) < 7 {
			continue
		}

		datetime, err := time.Parse("2006-01-02 15:04:05", record[1])
		if err != nil {
			continue
		}

		round := record[0]
		homeTeam := normalizeTeamName(record[2])
		awayTeam := normalizeTeamName(record[3])
		homeGoal, _ := strconv.Atoi(record[4])
		awayGoal, _ := strconv.Atoi(record[5])
		season, _ := strconv.Atoi(record[6])

		ds.CopaDoBrasilMatches = append(ds.CopaDoBrasilMatches, Match{
			ID:           fmt.Sprintf("copa-brasil-%d-%s", season, record[1]),
			Datetime:     datetime,
			HomeTeam:     homeTeam,
			AwayTeam:     awayTeam,
			HomeGoal:     homeGoal,
			AwayGoal:     awayGoal,
			Season:       season,
			Round:        round,
			Tournament:   "Copa do Brasil",
		})
	}

	return nil
}

// LoadCopaLibertadoresMatches loads the Copa Libertadores CSV file
func (ds *DataStore) LoadCopaLibertadoresMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	for i, record := range records {
		if i == 0 { // skip header
			continue
		}
		if len(record) < 7 {
			continue
		}

		datetime, err := time.Parse("2006-01-02 15:04:05", record[0])
		if err != nil {
			continue
		}

		homeTeam := normalizeTeamName(record[1])
		awayTeam := normalizeTeamName(record[2])
		homeGoal, _ := strconv.Atoi(record[3])
		awayGoal, _ := strconv.Atoi(record[4])
		season, _ := strconv.Atoi(record[5])
		stage := record[6]

		ds.CopaLibertadoresMatches = append(ds.CopaLibertadoresMatches, Match{
			ID:        fmt.Sprintf("libertadores-%d-%s", season, record[0]),
			Datetime:  datetime,
			HomeTeam:  homeTeam,
			AwayTeam:  awayTeam,
			HomeGoal:  homeGoal,
			AwayGoal:  awayGoal,
			Season:    season,
			Stage:     stage,
			Tournament: "Copa Libertadores",
		})
	}

	return nil
}

// LoadBRFootballMatches loads the extended match statistics CSV file
func (ds *DataStore) LoadBRFootballMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	for i, record := range records {
		if i == 0 { // skip header
			continue
		}
		if len(record) < 18 {
			continue
		}

		datetime, err := time.Parse("2006-01-02", record[13])
		if err != nil {
			continue
		}

		homeGoal := 0
		awayGoal := 0
		if record[2] != "" {
			homeGoal, _ = strconv.Atoi(record[2])
		}
		if record[3] != "" {
			awayGoal, _ = strconv.Atoi(record[3])
		}

		ds.BRFootballMatches = append(ds.BRFootballMatches, Match{
			ID:         fmt.Sprintf("br-football-%s-%s", record[13], record[1]),
			Datetime:   datetime,
			HomeTeam:   normalizeTeamName(record[1]),
			AwayTeam:   normalizeTeamName(record[4]),
			HomeGoal:   homeGoal,
			AwayGoal:   awayGoal,
			Tournament: record[0],
		})
	}

	return nil
}

// LoadNovoCampeonatoMatches loads the historical Brasileirao CSV file
func (ds *DataStore) LoadNovoCampeonatoMatches(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	for i, record := range records {
		if i == 0 { // skip header
			continue
		}
		if len(record) < 12 {
			continue
		}

		// Date format: DD/MM/YYYY
		dateStr := record[1]
		datetime, err := time.Parse("02/01/2006", dateStr)
		if err != nil {
			continue
		}

		season, _ := strconv.Atoi(record[2])
		round, _ := strconv.Atoi(record[3])
		homeTeam := normalizeTeamName(record[4])
		awayTeam := normalizeTeamName(record[5])
		homeGoal, _ := strconv.Atoi(record[6])
		awayGoal, _ := strconv.Atoi(record[7])

		ds.NovoCampeonatoMatches = append(ds.NovoCampeonatoMatches, Match{
			ID:        fmt.Sprintf("novo-%d-%d", season, round),
			Datetime:  datetime,
			HomeTeam:  homeTeam,
			AwayTeam:  awayTeam,
			HomeGoal:  homeGoal,
			AwayGoal:  awayGoal,
			Season:    season,
			Round:     strconv.Itoa(round),
		})
	}

	return nil
}

// LoadPlayers loads the FIFA player CSV file
func (ds *DataStore) LoadPlayers(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read CSV: %w", err)
	}

	for i, record := range records {
		if i == 0 { // skip header
			continue
		}
		if len(record) < 22 {
			continue
		}

		id, _ := strconv.Atoi(record[1])
		name := strings.TrimSpace(record[2])
		// Skip BOM and header rows
		if name == "" || strings.HasPrefix(name, "ID") || strings.Contains(name, "Name") {
			continue
		}

		age, _ := strconv.Atoi(record[3])
		nationality := record[5]
		overall, _ := strconv.Atoi(record[7])
		potential, _ := strconv.Atoi(record[8])
		club := strings.TrimSpace(record[9])
		position := record[21]
		jerseyNumber, _ := strconv.Atoi(record[22])

		ds.Players = append(ds.Players, Player{
			ID:       id,
			Name:     name,
			Age:      age,
			Nationality: nationality,
			Overall:  overall,
			Potential: potential,
			Club:     club,
			Position: position,
			JerseyNumber: jerseyNumber,
		})
	}

	return nil
}

// normalizeTeamName normalizes team names for consistent matching
func normalizeTeamName(name string) string {
	if name == "" {
		return ""
	}
	// Remove state suffix like -SP, -RJ, etc.
	replacer := strings.NewReplacer(
		"-AC", "", "-AL", "", "-AM", "", "-AP", "", "-BA", "", "-CE", "",
		"-DF", "", "-ES", "", "-GO", "", "-MA", "", "-MG", "", "-MS", "",
		"-MT", "", "-PA", "", "-PB", "", "-PE", "", "-PI", "", "-PR", "",
		"-RJ", "", "-RN", "", "-RO", "", "-RR", "", "-RS", "", "-SC", "",
		"-SE", "", "-SP", "", "-TO", "",
		"(", "", ")", "", "Sport Club ", "", "Clube de Regatas ", "",
		"Esporte Clube ", "", "Associação Desportiva ", "",
		"Clube Atlético ", "", "Sociedade Esportiva ", "",
		"Real Brasileiro", "Real", "São Paulo FC", "São Paulo",
		"Botafogo de Futebol e Regatas", "Botafogo",
		"Clube de Regatas do Flamengo", "Flamengo",
		"Grêmio Recreativo Bragantino", "Bragantino",
		"Atlético Clube Goianiense", "Atlético-GO",
		"Clube de Regatas Brasil", "CRB",
		"Vila Nova Futebol Clube", "Vila Nova",
		"Santa Cruz Futebol Clube", "Santa Cruz",
		"Petrolina", "Petrolina",
		"Atlético", "Atlético",
		"América", "América",
		"Botafogo-SP", "Botafogo-SP",
		"Boavista", "Boavista",
		"CR Vasco da Gama", "Vasco",
		"Fluminense FC", "Fluminense",
		"Corinthians Paulista", "Corinthians",
		"Palmeiras", "Palmeiras",
		"Santos FC", "Santos",
		"São Paulo FC", "São Paulo",
		"Vasco da Gama", "Vasco",
		"Guarani FC", "Guarani",
		"Athletico Paranaense", "Atlético-PR",
		"Paraná Clube", "Paraná",
		"Ceará SC", "Ceará",
		"Fortaleza EC", "Fortaleza",
		"Bahia SC", "Bahia",
		"Vitória EC", "Vitória",
		"Santa Cruz", "Santa Cruz",
		"Sport Recife", "Sport",
		"Santa Cruz FC", "Santa Cruz",
		"Brasiliense", "Brasiliense",
		"Brasília", "Brasília",
		"Ceilândia", "Ceilândia",
		"Gama", "Gama",
		"Novohorizontino", "Novohorizontino",
		"Oeste", "Oeste",
		"Mirassol", "Mirassol",
		"Guaratinguetá", "Guaratinguetá",
		"Barueri", "Barueri",
		"Coritiba", "Coritiba",
		"Paraná", "Paraná",
		"Paysandu", "Paysandu",
		"Avaí", "Avaí",
		"Juventude", "Juventude",
		"Vila Nova", "Vila Nova",
		"Goiás", "Goiás",
		"Vasco da Gama", "Vasco",
		"CR Vasco da Gama", "Vasco",
		"Botafogo FR", "Botafogo",
		"Botafogo da Bahia", "Botafogo-BA",
		"Boavista RJ", "Boavista",
		"América RN", "América-RN",
		"América MG", "América-MG",
		"América SP", "América-SP",
		"Real Brasileiro", "Real",
		"Real SP", "Real-SP",
	)
	normalized := replacer.Replace(name)
	// Remove extra spaces
	normalized = strings.Join(strings.Fields(normalized), " ")
	return normalized
}

// GetMatchesByTeams returns all matches between two teams
func (ds *DataStore) GetMatchesByTeams(team1, team2 string) []Match {
	var matches []Match
	team1 = normalizeTeamName(team1)
	team2 = normalizeTeamName(team2)

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, m := range allMatches {
		if (m.HomeTeam == team1 && m.AwayTeam == team2) ||
			(m.HomeTeam == team2 && m.AwayTeam == team1) {
			matches = append(matches, m)
		}
	}

	return matches
}

// GetMatchesByTeam returns all matches for a given team
func (ds *DataStore) GetMatchesByTeam(team string) []Match {
	var matches []Match
	team = normalizeTeamName(team)

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, m := range allMatches {
		if m.HomeTeam == team || m.AwayTeam == team {
			matches = append(matches, m)
		}
	}

	return matches
}

// GetMatchesBySeason returns matches for a given season
func (ds *DataStore) GetMatchesBySeason(season int) []Match {
	var matches []Match

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, m := range allMatches {
		if m.Season == season {
			matches = append(matches, m)
		}
	}

	return matches
}

// GetMatchesByTournament returns matches for a given tournament
func (ds *DataStore) GetMatchesByTournament(tournament string) []Match {
	var matches []Match

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	for _, m := range allMatches {
		if strings.Contains(strings.ToLower(m.Tournament), strings.ToLower(tournament)) ||
			strings.Contains(strings.ToLower(tournament), strings.ToLower(m.Tournament)) {
			matches = append(matches, m)
		}
	}

	return matches
}

// GetTeamStats returns statistics for a team in a given season
func (ds *DataStore) GetTeamStats(team string, season int) *TeamStats {
	team = normalizeTeamName(team)
	matches := ds.GetMatchesByTeam(team)
	matchesInSeason := make([]Match, 0)

	for _, m := range matches {
		if m.Season == season {
			matchesInSeason = append(matchesInSeason, m)
		}
	}

	return calculateTeamStats(team, matchesInSeason)
}

// GetTeamStatsAllSeasons returns statistics for a team across all seasons
func (ds *DataStore) GetTeamStatsAllSeasons(team string) *TeamStats {
	team = normalizeTeamName(team)
	matches := ds.GetMatchesByTeam(team)
	return calculateTeamStats(team, matches)
}

// calculateTeamStats calculates statistics for a team from its matches
func calculateTeamStats(team string, matches []Match) *TeamStats {
	stats := &TeamStats{
		TeamName: team,
		Matches:  len(matches),
	}

	for _, m := range matches {
		isHome := m.HomeTeam == team
		var teamGoals, opponentGoals int
		if isHome {
			teamGoals = m.HomeGoal
			opponentGoals = m.AwayGoal
		} else {
			teamGoals = m.AwayGoal
			opponentGoals = m.HomeGoal
		}

		if isHome {
			stats.HomeMatches++
			stats.HomeGoalsFor += teamGoals
			stats.HomeGoalsAgainst += opponentGoals
		} else {
			stats.AwayMatches++
			stats.AwayGoalsFor += teamGoals
			stats.AwayGoalsAgainst += opponentGoals
		}

		if teamGoals > opponentGoals {
			if isHome {
				stats.HomeWins++
			} else {
				stats.AwayWins++
			}
			stats.Wins++
			stats.Points += 3
		} else if teamGoals == opponentGoals {
			if isHome {
				stats.HomeDraws++
			} else {
				stats.AwayDraws++
			}
			stats.Draws++
			stats.Points += 1
		} else {
			if isHome {
				stats.HomeLosses++
			} else {
				stats.AwayLosses++
			}
			stats.Losses++
		}

		stats.GoalsFor += teamGoals
		stats.GoalsAgainst += opponentGoals
	}

	if stats.Matches > 0 {
		stats.AvgGoalsPerMatch = float64(stats.GoalsFor+stats.GoalsAgainst) / float64(stats.Matches)
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}

	return stats
}

// GetHeadToHead returns head-to-head record between two teams
func (ds *DataStore) GetHeadToHead(team1, team2 string) *TeamStats {
	team1 = normalizeTeamName(team1)
	team2 = normalizeTeamName(team2)
	matches := ds.GetMatchesByTeams(team1, team2)

	// Calculate stats for team1
	stats := &TeamStats{
		TeamName:  fmt.Sprintf("%s vs %s", team1, team2),
		Matches:   len(matches),
	}

	for _, m := range matches {
		isTeam1Home := m.HomeTeam == team1
		var teamGoals, opponentGoals int
		if isTeam1Home {
			teamGoals = m.HomeGoal
			opponentGoals = m.AwayGoal
		} else {
			teamGoals = m.AwayGoal
			opponentGoals = m.HomeGoal
		}

		if teamGoals > opponentGoals {
			stats.Wins++
			stats.Points += 3
		} else if teamGoals == opponentGoals {
			stats.Draws++
			stats.Points += 1
		} else {
			stats.Losses++
		}

		stats.GoalsFor += teamGoals
		stats.GoalsAgainst += opponentGoals
	}

	if stats.Matches > 0 {
		stats.AvgGoalsPerMatch = float64(stats.GoalsFor+stats.GoalsAgainst) / float64(stats.Matches)
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}

	return stats
}

// GetTopScorers returns top scorers from all players
func (ds *DataStore) GetTopScorers(limit int) []Player {
	// Sort players by overall rating
	sorted := make([]Player, len(ds.Players))
	copy(sorted, ds.Players)

	for i := 0; i < len(sorted)-1; i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[j].Overall > sorted[i].Overall {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	if limit > len(sorted) {
		limit = len(sorted)
	}

	return sorted[:limit]
}

// GetPlayersByClub returns players filtered by club name
func (ds *DataStore) GetPlayersByClub(club string) []Player {
	var players []Player
	club = normalizeTeamName(club)

	for _, p := range ds.Players {
		if strings.Contains(strings.ToLower(p.Club), strings.ToLower(club)) {
			players = append(players, p)
		}
	}

	return players
}

// GetPlayersByNationality returns players filtered by nationality
func (ds *DataStore) GetPlayersByNationality(nationality string) []Player {
	var players []Player

	for _, p := range ds.Players {
		if strings.Contains(strings.ToLower(p.Nationality), strings.ToLower(nationality)) {
			players = append(players, p)
		}
	}

	return players
}

// GetPlayersByPosition returns players filtered by position
func (ds *DataStore) GetPlayersByPosition(position string) []Player {
	var players []Player

	for _, p := range ds.Players {
		if strings.Contains(strings.ToLower(p.Position), strings.ToLower(position)) {
			players = append(players, p)
		}
	}

	return players
}

// GetBrazilianPlayers returns all Brazilian players
func (ds *DataStore) GetBrazilianPlayers() []Player {
	return ds.GetPlayersByNationality("Brazil")
}

// GetBrazilianPlayersByClub returns Brazilian players grouped by club
func (ds *DataStore) GetBrazilianPlayersByClub() map[string][]Player {
	result := make(map[string][]Player)

	for _, p := range ds.Players {
		if strings.Contains(strings.ToLower(p.Nationality), "brazil") {
			result[p.Club] = append(result[p.Club], p)
		}
	}

	return result
}

// GetTeamStandings calculates standings for a team in a specific tournament and season
func (ds *DataStore) GetTeamStandings(tournament string, season int) []TeamStanding {
	// Get all matches for the tournament
	var tournamentMatches []Match

	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	// Filter by tournament
	for _, m := range allMatches {
		if strings.Contains(strings.ToLower(m.Tournament), strings.ToLower(tournament)) ||
			strings.Contains(strings.ToLower(tournament), strings.ToLower(m.Tournament)) {
			if m.Season == season || m.Season == 0 {
				tournamentMatches = append(tournamentMatches, m)
			}
		}
	}

	// Calculate standings
	teamStats := make(map[string]*TeamStats)

	for _, m := range tournamentMatches {
		if m.HomeTeam != "" && m.AwayTeam != "" {
			if _, exists := teamStats[m.HomeTeam]; !exists {
				teamStats[m.HomeTeam] = &TeamStats{TeamName: m.HomeTeam}
			}
			if _, exists := teamStats[m.AwayTeam]; !exists {
				teamStats[m.AwayTeam] = &TeamStats{TeamName: m.AwayTeam}
			}

			// Update home team stats
			homeStats := teamStats[m.HomeTeam]
			homeStats.Matches++
			homeStats.GoalsFor += m.HomeGoal
			homeStats.GoalsAgainst += m.AwayGoal

			// Update away team stats
			awayStats := teamStats[m.AwayTeam]
			awayStats.Matches++
			awayStats.GoalsFor += m.AwayGoal
			awayStats.GoalsAgainst += m.HomeGoal

			// Determine winner
			if m.HomeGoal > m.AwayGoal {
				homeStats.Wins++
				homeStats.Points += 3
				awayStats.Losses++
			} else if m.HomeGoal < m.AwayGoal {
				awayStats.Wins++
				awayStats.Points += 3
				homeStats.Losses++
			} else {
				homeStats.Draws++
				awayStats.Draws++
				homeStats.Points += 1
				awayStats.Points += 1
			}
		}
	}

	// Convert map to slice and sort
	standings := make([]TeamStanding, 0, len(teamStats))
	for _, stats := range teamStats {
		standings = append(standings, TeamStanding{
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

	// Sort by points, then goal difference
	for i := 0; i < len(standings)-1; i++ {
		for j := i + 1; j < len(standings); j++ {
			if standings[j].Points > standings[i].Points ||
				(standings[j].Points == standings[i].Points &&
					(standings[j].GoalsFor-standings[j].GoalsAgainst) > (standings[i].GoalsFor-standings[i].GoalsAgainst)) {
				standings[i], standings[j] = standings[j], standings[i]
			}
		}
	}

	return standings
}

// FindBiggestWins finds matches with the largest goal differences
func (ds *DataStore) FindBiggestWins(limit int) []Match {
	var allMatches []Match
	allMatches = append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	// Sort by goal difference
	for i := 0; i < len(allMatches)-1; i++ {
		for j := i + 1; j < len(allMatches); j++ {
			diffI := abs(allMatches[i].HomeGoal - allMatches[i].AwayGoal)
			diffJ := abs(allMatches[j].HomeGoal - allMatches[j].AwayGoal)
			if diffJ > diffI {
				allMatches[i], allMatches[j] = allMatches[j], allMatches[i]
			}
		}
	}

	if limit > len(allMatches) {
		limit = len(allMatches)
	}

	return allMatches[:limit]
}

// GetAverageGoalsPerMatch calculates average goals per match
func (ds *DataStore) GetAverageGoalsPerMatch() float64 {
	var allMatches []Match
	allMatches = append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	if len(allMatches) == 0 {
		return 0
	}

	var totalGoals int
	for _, m := range allMatches {
		totalGoals += m.HomeGoal + m.AwayGoal
	}

	return float64(totalGoals) / float64(len(allMatches))
}

// GetHomeWinRate calculates the percentage of home wins
func (ds *DataStore) GetHomeWinRate() float64 {
	var allMatches []Match
	allMatches = append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	if len(allMatches) == 0 {
		return 0
	}

	var homeWins, total int
	for _, m := range allMatches {
		total++
		if m.HomeGoal > m.AwayGoal {
			homeWins++
		}
	}

	return float64(homeWins) / float64(total) * 100
}

// GetPlayerByName searches for a player by name
func (ds *DataStore) GetPlayerByName(name string) *Player {
	for _, p := range ds.Players {
		if strings.Contains(strings.ToLower(p.Name), strings.ToLower(name)) {
			return &p
		}
	}
	return nil
}

// abs returns absolute value
func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
