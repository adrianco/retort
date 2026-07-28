package store

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/models"
)

// DataLoader handles loading data from CSV files
type DataLoader struct {
	matches  []models.Match
	players  []models.Player
	dataPath string
}

// NewDataLoader creates a new DataLoader
func NewDataLoader(dataPath string) *DataLoader {
	return &DataLoader{
		dataPath: dataPath,
		matches:  make([]models.Match, 0),
		players:  make([]models.Player, 0),
	}
}

// LoadAll loads all CSV files
func (dl *DataLoader) LoadAll() error {
	files := []string{
		"Brasileirao_Matches.csv",
		"Brazilian_Cup_Matches.csv",
		"Libertadores_Matches.csv",
		"BR-Football-Dataset.csv",
		"novo_campeonato_brasileiro.csv",
		"fifa_data.csv",
	}

	for _, file := range files {
		err := dl.LoadFile(file)
		if err != nil {
			return fmt.Errorf("failed to load %s: %w", file, err)
		}
	}
	return nil
}

// LoadFile loads a single CSV file
func (dl *DataLoader) LoadFile(filename string) error {
	path := filepath.Join(dl.dataPath, filename)
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	if len(records) < 2 {
		return nil
	}

	switch {
	case strings.Contains(filename, "Brasileirao"):
		return dl.loadBrasileiraoMatches(records)
	case strings.Contains(filename, "Brazilian_Cup"):
		return dl.loadBrazilianCupMatches(records)
	case strings.Contains(filename, "Libertadores"):
		return dl.loadLibertadoresMatches(records)
	case strings.Contains(filename, "BR-Football"):
		return dl.loadBRFootballMatches(records)
	case strings.Contains(filename, "novo_campeonato"):
		return dl.loadNovoCampeonatoMatches(records)
	case strings.Contains(filename, "fifa_data"):
		return dl.loadFIFAPlayers(records)
	}

	return fmt.Errorf("unknown file type: %s", filename)
}

// loadBrasileiraoMatches loads Brasileirão Serie A matches
func (dl *DataLoader) loadBrasileiraoMatches(records [][]string) error {
	// Skip header
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 9 {
			continue
		}

		datetime, _ := time.Parse("2006-01-02 15:04:05", row[0])
		homeTeam := normalizeTeamName(row[1])
		homeTeamState := row[2]
		awayTeam := normalizeTeamName(row[3])
		awayTeamState := row[4]

		homeGoal, _ := strconv.Atoi(row[5])
		awayGoal, _ := strconv.Atoi(row[6])
		season, _ := strconv.Atoi(row[7])
		round, _ := strconv.Atoi(row[8])

		dl.matches = append(dl.matches, models.Match{
			ID:            len(dl.matches) + 1,
			Datetime:      datetime,
			HomeTeam:      homeTeam,
			HomeTeamState: homeTeamState,
			AwayTeam:      awayTeam,
			AwayTeamState: awayTeamState,
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Season:        season,
			Round:         round,
		})
	}
	return nil
}

// loadBrazilianCupMatches loads Copa do Brasil matches
func (dl *DataLoader) loadBrazilianCupMatches(records [][]string) error {
	// Skip header
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 7 {
			continue
		}

		datetime, _ := time.Parse("2006-01-02 15:04:05", row[1])
		homeTeam := normalizeTeamName(row[2])
		awayTeam := normalizeTeamName(row[3])

		homeGoal, _ := strconv.Atoi(row[4])
		awayGoal, _ := strconv.Atoi(row[5])
		season, _ := strconv.Atoi(row[6])
		roundStr := strings.Trim(row[0], "\"")
		round, _ := strconv.Atoi(roundStr)

		dl.matches = append(dl.matches, models.Match{
			ID:            len(dl.matches) + 1,
			Datetime:      datetime,
			HomeTeam:      homeTeam,
			HomeTeamState: "",
			AwayTeam:      awayTeam,
			AwayTeamState: "",
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Season:        season,
			Round:         round,
			Tournament:    "Copa do Brasil",
		})
	}
	return nil
}

// loadLibertadoresMatches loads Copa Libertadores matches
func (dl *DataLoader) loadLibertadoresMatches(records [][]string) error {
	// Skip header
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 7 {
			continue
		}

		datetime, _ := time.Parse("2006-01-02 15:04:05", row[0])
		homeTeam := normalizeTeamName(row[1])
		awayTeam := normalizeTeamName(row[2])

		homeGoal, _ := strconv.Atoi(row[3])
		awayGoal, _ := strconv.Atoi(row[4])
		season, _ := strconv.Atoi(row[5])
		stage := row[6]

		dl.matches = append(dl.matches, models.Match{
			ID:            len(dl.matches) + 1,
			Datetime:      datetime,
			HomeTeam:      homeTeam,
			HomeTeamState: "",
			AwayTeam:      awayTeam,
			AwayTeamState: "",
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Season:        season,
			Stage:         stage,
			Tournament:    "Copa Libertadores",
		})
	}
	return nil
}

// loadBRFootballMatches loads BR-Football dataset matches
func (dl *DataLoader) loadBRFootballMatches(records [][]string) error {
	// Skip header
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 17 {
			continue
		}

		tournament := row[0]
		homeTeam := normalizeTeamName(row[1])
		awayTeam := normalizeTeamName(row[4])

		homeGoal, _ := strconv.Atoi(row[2])
		awayGoal, _ := strconv.Atoi(row[3])

		// Parse date
		dateStr := row[13]
		datetime, _ := time.Parse("2006-01-02", dateStr)

		dl.matches = append(dl.matches, models.Match{
			ID:            len(dl.matches) + 1,
			Datetime:      datetime,
			HomeTeam:      homeTeam,
			HomeTeamState: "",
			AwayTeam:      awayTeam,
			AwayTeamState: "",
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Tournament:    tournament,
		})
	}
	return nil
}

// loadNovoCampeonatoMatches loads historical Brasileirão matches (2003-2019)
func (dl *DataLoader) loadNovoCampeonatoMatches(records [][]string) error {
	// Skip header
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 13 {
			continue
		}

		// Parse date in DD/MM/YYYY format
		dateStr := row[1]
		dateParts := strings.Split(dateStr, "/")
		if len(dateParts) < 3 {
			continue
		}
		day, _ := strconv.Atoi(dateParts[0])
		month, _ := strconv.Atoi(dateParts[1])
		year, _ := strconv.Atoi(dateParts[2])

		datetime := time.Date(year, time.Month(month), day, 0, 0, 0, 0, time.UTC)

		homeTeam := normalizeTeamName(row[4])
		awayTeam := normalizeTeamName(row[5])

		homeGoal, _ := strconv.Atoi(row[6])
		awayGoal, _ := strconv.Atoi(row[7])

		season, _ := strconv.Atoi(row[2])
		round, _ := strconv.Atoi(row[3])

		dl.matches = append(dl.matches, models.Match{
			ID:            len(dl.matches) + 1,
			Datetime:      datetime,
			HomeTeam:      homeTeam,
			HomeTeamState: row[8],
			AwayTeam:      awayTeam,
			AwayTeamState: row[9],
			HomeGoal:      homeGoal,
			AwayGoal:      awayGoal,
			Season:        season,
			Round:         round,
		})
	}
	return nil
}

// loadFIFAPlayers loads FIFA player data
func (dl *DataLoader) loadFIFAPlayers(records [][]string) error {
	// Skip header
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 50 {
			continue
		}

		id, _ := strconv.Atoi(row[1])
		name := row[2]
		age, _ := strconv.Atoi(row[3])
		nationality := row[5]
		overall, _ := strconv.Atoi(row[6])
		potential, _ := strconv.Atoi(row[7])
		club := normalizeTeamName(row[8])
		position := row[20]
		jerseyNum, _ := strconv.Atoi(row[21])

		var height, weight string
		if len(row) > 24 {
			height = row[24]
			weight = row[25]
		}

		var crossing, finishing, headingAccuracy, shortPassing, volleys, dribbling, curve, fkAccuracy, longPassing, ballControl int
		var acceleration, sprintSpeed, agility, reactions, balance, shotPower, jumping, stamina, strength, longShots int
		var aggression, interceptions, positioning, vision, penalties, composure, marking, standingTackle, slidingTackle int
		var gkDiving, gkHandling, gkKicking, gkPositioning, gkReflexes int

		// Skill attributes start around column 33
		if len(row) > 33 {
			crossing = parseIntOrZero(row[33])
			finishing = parseIntOrZero(row[34])
			headingAccuracy = parseIntOrZero(row[35])
			shortPassing = parseIntOrZero(row[36])
			volleys = parseIntOrZero(row[37])
			dribbling = parseIntOrZero(row[38])
			curve = parseIntOrZero(row[39])
			fkAccuracy = parseIntOrZero(row[40])
			longPassing = parseIntOrZero(row[41])
			ballControl = parseIntOrZero(row[42])
		}

		if len(row) > 43 {
			acceleration = parseIntOrZero(row[43])
			sprintSpeed = parseIntOrZero(row[44])
			agility = parseIntOrZero(row[45])
			reactions = parseIntOrZero(row[46])
			balance = parseIntOrZero(row[47])
			shotPower = parseIntOrZero(row[48])
			jumping = parseIntOrZero(row[49])
			stamina = parseIntOrZero(row[50])
			strength = parseIntOrZero(row[51])
			longShots = parseIntOrZero(row[52])
		}

		if len(row) > 53 {
			aggression = parseIntOrZero(row[53])
			interceptions = parseIntOrZero(row[54])
			positioning = parseIntOrZero(row[55])
			vision = parseIntOrZero(row[56])
			penalties = parseIntOrZero(row[57])
			composure = parseIntOrZero(row[58])
		}

		if len(row) > 59 {
			marking = parseIntOrZero(row[59])
			standingTackle = parseIntOrZero(row[60])
			slidingTackle = parseIntOrZero(row[61])
		}

		if len(row) > 62 {
			gkDiving = parseIntOrZero(row[62])
			gkHandling = parseIntOrZero(row[63])
			gkKicking = parseIntOrZero(row[64])
			gkPositioning = parseIntOrZero(row[65])
			gkReflexes = parseIntOrZero(row[66])
		}

		dl.players = append(dl.players, models.Player{
			ID:              id,
			Name:            name,
			Age:             age,
			Nationality:     nationality,
			Overall:         overall,
			Potential:       potential,
			Club:            club,
			Position:        position,
			JerseyNumber:    jerseyNum,
			Height:          height,
			Weight:          weight,
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
		})
	}
	return nil
}

// parseIntOrZero parses a string to int, returns 0 if parsing fails
func parseIntOrZero(s string) int {
	val, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		return 0
	}
	return val
}

// normalizeTeamName normalizes team names for consistent matching
func normalizeTeamName(name string) string {
	// Remove state suffix (e.g., "-SP", "-RJ", "-MG", "-PE")
	normalized := strings.TrimSpace(name)
	
	// Remove common suffixes
	suffixes := []string{"-SP", "-RJ", "-MG", "-PE", "-SC", "-BA", "-PR", "-RS", "-GO", "-DF", "-ES", "-AM", "-AL", "-SE", "-TO", "-AP", "-AC", "-RO", "-RR", "-PA"}
	
	for _, suffix := range suffixes {
		if strings.HasSuffix(normalized, suffix) {
			normalized = strings.TrimSpace(strings.TrimSuffix(normalized, suffix))
			break
		}
	}

	// Remove parentheses content that might contain extra info
	if idx := strings.Index(normalized, "("); idx > 0 {
		normalized = strings.TrimSpace(normalized[:idx])
	}

	// Normalize common name variations
	variations := map[string]string{
		"Sao Paulo":            "São Paulo",
		"Saopaulo":             "São Paulo",
		"Guarani de Juiz de Fora": "Guarani",
		"Botafogo FR":          "Botafogo",
		"Botafogo F.R.":        "Botafogo",
		"Fluminense FC":        "Fluminense",
		"Fluminense F.C.":      "Fluminense",
		"Palmeiras SP":         "Palmeiras",
		"Palmeiras-SP":         "Palmeiras",
		"Corinthians SP":       "Corinthians",
		"Corinthians-SP":       "Corinthians",
		"Grêmio":               "Gremio",
		"Grêmio FBPA":          "Gremio",
		"Figueirense":          "Figueirense",
		"Santa Cruz":           "Santa Cruz",
		"Vasco da Gama":        "Vasco da Gama",
		"Vasco":                "Vasco da Gama",
		"Cruzeiro":             "Cruzeiro",
		"Cruzeiro EC":          "Cruzeiro",
		"Atlético":             "Atlético",
		"Atletico-MG":          "Atlético",
		"Atletico MG":          "Atlético",
		"America MG":           "América MG",
		"América-MG":           "América MG",
		"America":              "América",
		"Fortaleza":            "Fortaleza",
		"Fortaleza EC":         "Fortaleza",
		"Bahia":                "Bahia",
		"Bahia EC":             "Bahia",
		"Santos FC":            "Santos",
		"Santos-SP":            "Santos",
		"Internacional":        "Internacional",
		"Internacional RS":     "Internacional",
		"Juventude":            "Juventude",
		"Athletico Paranaense": "Athletico Paranaense",
		"Parana":               "Athletico Paranaense",
		"Athletico-PR":         "Athletico Paranaense",
		"Coritiba":             "Coritiba",
		"Coritiba PR":          "Coritiba",
		"Cuiaba":               "Cuiabá",
		"Cuiabá MT":            "Cuiabá",
		"Bragantino":           "Bragantino",
		"Red Bull Bragantino":  "Bragantino",
		"Red Bull":             "Red Bull Bragantino",
	}

	if normalized, ok := variations[normalized]; ok {
		return normalized
	}

	return normalized
}

// MatchCount returns the number of loaded matches
func (dl *DataLoader) MatchCount() int {
	return len(dl.matches)
}

// PlayerCount returns the number of loaded players
func (dl *DataLoader) PlayerCount() int {
	return len(dl.players)
}

// Matches returns all loaded matches
func (dl *DataLoader) Matches() []models.Match {
	return dl.matches
}

// Players returns all loaded players
func (dl *DataLoader) Players() []models.Player {
	return dl.players
}
