package loader

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"soccer-mcp/models"
)

// LoadData loads all CSV files and returns a populated DataStore
func LoadData(dataDir string) (*models.DataStore, error) {
	store := models.NewDataStore()

	// Load match files
	if err := loadBrasileiraoMatches(store, dataDir); err != nil {
		return nil, fmt.Errorf("failed to load Brasileirão matches: %w", err)
	}

	if err := loadCopaDoBrasilMatches(store, dataDir); err != nil {
		return nil, fmt.Errorf("failed to load Copa do Brasil matches: %w", err)
	}

	if err := loadLibertadoresMatches(store, dataDir); err != nil {
		return nil, fmt.Errorf("failed to load Libertadores matches: %w", err)
	}

	if err := loadExtendedMatches(store, dataDir); err != nil {
		return nil, fmt.Errorf("failed to load extended matches: %w", err)
	}

	if err := loadHistoricalMatches(store, dataDir); err != nil {
		return nil, fmt.Errorf("failed to load historical matches: %w", err)
	}

	// Load player data
	if err := loadPlayers(store, dataDir); err != nil {
		return nil, fmt.Errorf("failed to load players: %w", err)
	}

	// Set up team aliases for normalization
	setupTeamAliases(store)

	return store, nil
}

func loadBrasileiraoMatches(store *models.DataStore, dataDir string) error {
	filePath := fmt.Sprintf("%s/Brasileirao_Matches.csv", dataDir)
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", filePath, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", filePath, err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header row
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 8 {
			continue
		}

		match := models.Match{
			Tournament:    "Brasileirão",
			HomeTeamState: row[2],
			AwayTeamState: row[4],
		}

		// Parse datetime
		if row[0] != "" {
			if t, err := time.Parse("2006-01-02 15:04:05", row[0]); err == nil {
				match.Date = t
			} else if t, err := time.Parse("2006-01-02", row[0]); err == nil {
				match.Date = t
			}
		}

		// Parse home team (column 1)
		match.HomeTeam = normalizeTeamName(row[1])

		// Parse away team (column 3)
		match.AwayTeam = normalizeTeamName(row[3])

		// Parse goals (columns 5, 6)
		if homeGoals, err := strconv.Atoi(row[5]); err == nil {
			match.HomeGoals = homeGoals
		}
		if awayGoals, err := strconv.Atoi(row[6]); err == nil {
			match.AwayGoals = awayGoals
		}

		// Parse season (column 7)
		if season, err := strconv.Atoi(row[7]); err == nil {
			match.Season = season
		}

		// Parse round (column 8)
		if len(row) > 8 && row[8] != "" {
			if round, err := strconv.Atoi(row[8]); err == nil {
				match.Round = round
			}
		}

		store.BrasileiraoMatches = append(store.BrasileiraoMatches, match)
	}

	return nil
}

func loadCopaDoBrasilMatches(store *models.DataStore, dataDir string) error {
	filePath := fmt.Sprintf("%s/Brazilian_Cup_Matches.csv", dataDir)
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", filePath, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", filePath, err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header row
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 7 {
			continue
		}

		match := models.Match{
			Tournament:    "Copa do Brasil",
			Stage:         normalizeRound(row[0]),
		}

		// Parse datetime
		if row[1] != "" {
			if t, err := time.Parse("2006-01-02 15:04:05", row[1]); err == nil {
				match.Date = t
			} else if t, err := time.Parse("2006-01-02", row[1]); err == nil {
				match.Date = t
			}
		}

		// Parse home team (column 2)
		match.HomeTeam = normalizeTeamName(row[2])

		// Parse away team (column 3)
		match.AwayTeam = normalizeTeamName(row[3])

		// Parse goals (columns 4, 5)
		if homeGoals, err := strconv.Atoi(row[4]); err == nil {
			match.HomeGoals = homeGoals
		}
		if awayGoals, err := strconv.Atoi(row[5]); err == nil {
			match.AwayGoals = awayGoals
		}

		// Parse season (column 6)
		if season, err := strconv.Atoi(row[6]); err == nil {
			match.Season = season
		}

		store.CopaDoBrasilMatches = append(store.CopaDoBrasilMatches, match)
	}

	return nil
}

func loadLibertadoresMatches(store *models.DataStore, dataDir string) error {
	filePath := fmt.Sprintf("%s/Libertadores_Matches.csv", dataDir)
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", filePath, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", filePath, err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header row
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 7 {
			continue
		}

		match := models.Match{
			Tournament: "Libertadores",
		}

		// Parse datetime
		if row[0] != "" {
			if t, err := time.Parse("2006-01-02 15:04:05", row[0]); err == nil {
				match.Date = t
			} else if t, err := time.Parse("2006-01-02", row[0]); err == nil {
				match.Date = t
			}
		}

		// Parse home team (column 1)
		match.HomeTeam = normalizeTeamName(row[1])

		// Parse away team (column 2)
		match.AwayTeam = normalizeTeamName(row[2])

		// Parse goals (columns 3, 4)
		if homeGoals, err := strconv.Atoi(row[3]); err == nil {
			match.HomeGoals = homeGoals
		}
		if awayGoals, err := strconv.Atoi(row[4]); err == nil {
			match.AwayGoals = awayGoals
		}

		// Parse season (column 5)
		if season, err := strconv.Atoi(row[5]); err == nil {
			match.Season = season
		}

		// Parse stage (column 6)
		if len(row) > 6 && row[6] != "" {
			match.Stage = row[6]
		}

		store.LibertadoresMatches = append(store.LibertadoresMatches, match)
	}

	return nil
}

func loadExtendedMatches(store *models.DataStore, dataDir string) error {
	filePath := fmt.Sprintf("%s/BR-Football-Dataset.csv", dataDir)
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", filePath, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", filePath, err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header row
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 16 {
			continue
		}

		match := models.Match{
			Tournament:    row[0],
		}

		// Parse home team (column 1)
		match.HomeTeam = normalizeTeamName(row[1])

		// Parse away team (column 2)
		match.AwayTeam = normalizeTeamName(row[2])

		// Parse goals (columns 3, 4)
		if homeGoals, err := strconv.Atoi(row[3]); err == nil {
			match.HomeGoals = homeGoals
		}
		if awayGoals, err := strconv.Atoi(row[4]); err == nil {
			match.AwayGoals = awayGoals
		}

		// Parse corners (columns 5, 6)
		if homeCorners, err := strconv.Atoi(row[5]); err == nil {
			match.HomeCorners = homeCorners
		}
		if awayCorners, err := strconv.Atoi(row[6]); err == nil {
			match.AwayCorners = awayCorners
		}

		// Parse attacks (columns 7, 8)
		if homeAttacks, err := strconv.Atoi(row[7]); err == nil {
			match.HomeAttacks = homeAttacks
		}
		if awayAttacks, err := strconv.Atoi(row[8]); err == nil {
			match.AwayAttacks = awayAttacks
		}

		// Parse shots (columns 9, 10)
		if homeShots, err := strconv.Atoi(row[9]); err == nil {
			match.HomeShots = homeShots
		}
		if awayShots, err := strconv.Atoi(row[10]); err == nil {
			match.AwayShots = awayShots
		}

		// Parse time (column 11)
		match.StartTime = row[11]

		// Parse date (column 12)
		if row[12] != "" {
			// Try Brazilian format DD/MM/YYYY
			if t, err := time.Parse("02/01/2006", row[12]); err == nil {
				match.Date = t
			} else if t, err := time.Parse("2006-01-02", row[12]); err == nil {
				match.Date = t
			}
		}

		// Parse half-time result (column 13)
		match.HTResult = row[13]

		// Parse full-time result (column 14)
		match.ATResult = row[14]

		// Parse total corners (column 15)
		if totalCorners, err := strconv.Atoi(row[15]); err == nil {
			match.TotalCorners = totalCorners
		}

		store.ExtendedMatches = append(store.ExtendedMatches, match)
	}

	return nil
}

func loadHistoricalMatches(store *models.DataStore, dataDir string) error {
	filePath := fmt.Sprintf("%s/novo_campeonato_brasileiro.csv", dataDir)
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", filePath, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", filePath, err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header row
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 11 {
			continue
		}

		match := models.Match{
			Tournament: "Brasileirão",
		}

		// Parse ID (column 0)
		if id, err := strconv.Atoi(row[0]); err == nil {
			match.ID = id
		}

		// Parse date (column 1) - Brazilian format DD/MM/YYYY
		if row[1] != "" {
			if t, err := time.Parse("02/01/2006", row[1]); err == nil {
				match.Date = t
			}
		}

		// Parse year (column 2)
		if year, err := strconv.Atoi(row[2]); err == nil {
			match.Season = year
		}

		// Parse round (column 3)
		if round, err := strconv.Atoi(row[3]); err == nil {
			match.Round = round
		}

		// Parse home team (column 4)
		match.HomeTeam = normalizeTeamName(row[4])

		// Parse away team (column 5)
		match.AwayTeam = normalizeTeamName(row[5])

		// Parse home goals (column 6)
		if homeGoals, err := strconv.Atoi(row[6]); err == nil {
			match.HomeGoals = homeGoals
		}

		// Parse away goals (column 7)
		if awayGoals, err := strconv.Atoi(row[7]); err == nil {
			match.AwayGoals = awayGoals
		}

		// Parse state abbreviations (columns 8, 9)
		match.HomeTeamState = row[8]
		match.AwayTeamState = row[9]

		// Parse winner (column 10)
		match.Winner = row[10]

		// Parse stadium (column 11 if exists)
		if len(row) > 10 {
			match.Stadium = row[10]
		}

		store.HistoricalMatches = append(store.HistoricalMatches, match)
	}

	return nil
}

func loadPlayers(store *models.DataStore, dataDir string) error {
	filePath := fmt.Sprintf("%s/fifa_data.csv", dataDir)
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", filePath, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", filePath, err)
	}

	if len(records) < 2 {
		return fmt.Errorf("no data in %s", filePath)
	}

	// Skip header row
	for i := 1; i < len(records); i++ {
		row := records[i]
		if len(row) < 25 {
			continue
		}

		player := models.Player{}

		// Parse basic info
		if id, err := strconv.Atoi(row[0]); err == nil {
			player.ID = id
		}
		player.Name = row[1]

		if age, err := strconv.Atoi(row[2]); err == nil {
			player.Age = age
		}

		player.Nationality = row[3]
		player.Club = row[6]
		player.Position = row[4]

		// Parse numeric skills
		parseSkill := func(val string) int {
			if v, err := strconv.Atoi(val); err == nil {
				return v
			}
			return 0
		}

		player.Overall = parseSkill(row[5])
		player.Potential = parseSkill(row[6])
		player.JerseyNum = parseSkill(row[7])

		if len(row) > 8 {
			player.Height = row[8]
		}
		if len(row) > 9 {
			player.Weight = row[9]
		}

		// Parse skill ratings (columns 10+)
		skillCols := []string{
			"Crossing", "Finishing", "Dribbling", "Control", "Shooting",
			"Passing", "Defense", "Physicality", "Penalties", "FreeKick",
			"Save", "Corner", "Acceleration", "SprintSpeed", "Positioning",
			"Reaction", "Balanced", "Aggression", "Interceptions", "Vision",
			"Composure",
		}

		for j, colName := range skillCols {
			idx := 10 + j
			if idx < len(row) {
				switch colName {
				case "Crossing":
					player.Crossing = parseSkill(row[idx])
				case "Finishing":
					player.Finishing = parseSkill(row[idx])
				case "Dribbling":
					player.Dribbling = parseSkill(row[idx])
				case "Control":
					player.Control = parseSkill(row[idx])
				case "Shooting":
					player.Shooting = parseSkill(row[idx])
				case "Passing":
					player.Passing = parseSkill(row[idx])
				case "Defense":
					player.Defense = parseSkill(row[idx])
				case "Physicality":
					player.Physicality = parseSkill(row[idx])
				case "Penalties":
					player.Penalties = parseSkill(row[idx])
				case "FreeKick":
					player.FreeKick = parseSkill(row[idx])
				case "Save":
					player.Save = parseSkill(row[idx])
				case "Corner":
					player.Corner = parseSkill(row[idx])
				case "Acceleration":
					player.Acceleration = parseSkill(row[idx])
				case "SprintSpeed":
					player.SprintSpeed = parseSkill(row[idx])
				case "Positioning":
					player.Positioning = parseSkill(row[idx])
				case "Reaction":
					player.Reaction = parseSkill(row[idx])
				case "Balanced":
					player.Balanced = parseSkill(row[idx])
				case "Aggression":
					player.Aggression = parseSkill(row[idx])
				case "Interceptions":
					player.Interceptions = parseSkill(row[idx])
				case "Vision":
					player.Vision = parseSkill(row[idx])
				case "Composure":
					player.Composure = parseSkill(row[idx])
				}
			}
		}

		store.Players = append(store.Players, player)
	}

	return nil
}

// setupTeamAliases creates a mapping of team name variations to normalized names
func setupTeamAliases(store *models.DataStore) {
	aliases := map[string]string{
		// Palmeiras
		"Palmeiras":            "Palmeiras",
		"Palmeiras-SP":         "Palmeiras",
		"São Paulo Palmeiras":  "Palmeiras",
		"Palmeiras SP":         "Palmeiras",

		// Flamengo
		"Flamengo":             "Flamengo",
		"Flamengo-RJ":          "Flamengo",
		"Flamengo RJ":          "Flamengo",
		"CR Flamengo":          "Flamengo",

		// São Paulo
		"São Paulo":            "São Paulo",
		"São Paulo-SP":         "São Paulo",
		"São Paulo FC":         "São Paulo",
		"São Paulo SP":         "São Paulo",

		// Corinthians
		"Corinthians":          "Corinthians",
		"Corinthians-SP":       "Corinthians",
		"Corinthians SP":       "Corinthians",
		"Sport Club Corinthians Paulista": "Corinthians",

		// Santos
		"Santos":               "Santos",
		"Santos-SP":            "Santos",
		"Santos SP":            "Santos",

		// Palmeiras alternate
		"SC Palmeiras":         "Palmeiras",

		// Grêmio
		"Grêmio":               "Grêmio",
		"Grêmio-RS":            "Grêmio",
		"Grêmio SP":            "Grêmio",
		"Grêmio FBPA":          "Grêmio",

		// Fluminense
		"Fluminense":           "Fluminense",
		"Fluminense-RJ":        "Fluminense",
		"Fluminense RJ":        "Fluminense",

		// Botafogo
		"Botafogo":             "Botafogo",
		"Botafogo-RJ":          "Botafogo",
		"Botafogo RJ":          "Botafogo",
		"Botafogo FR":          "Botafogo",

		// Internacional
		"Internacional":        "Internacional",
		"Internacional-RS":     "Internacional",
		"Internacional SP":     "Internacional",

		// Cruzeiro
		"Cruzeiro":             "Cruzeiro",
		"Cruzeiro-MG":          "Cruzeiro",
		"Cruzeiro MG":          "Cruzeiro",

		// Vasco da Gama
		"Vasco da Gama":        "Vasco da Gama",
		"Vasco":                "Vasco da Gama",
		"Vasco da Gama-RJ":     "Vasco da Gama",
		"Vasco RJ":             "Vasco da Gama",

		// Athletico Paranaense
		"Athletico Paranaense": "Athletico Paranaense",
		"Athletico-PR":         "Athletico Paranaense",
		"Athletico PR":         "Athletico Paranaense",
		"Atlético Paranaense":  "Athletico Paranaense",
		"Atlético-PR":          "Athletico Paranaense",
		"Atlético PR":          "Athletico Paranaense",

		// Atlético Mineiro
		"Atlético Mineiro":     "Atlético Mineiro",
		"Atlético-MG":          "Atlético Mineiro",
		"Atlético MG":          "Atlético Mineiro",
		"Atletico Mineiro":     "Atlético Mineiro",
		"Atletico-MG":          "Atlético Mineiro",
		"Atletico MG":          "Atlético Mineiro",

		// Bahia
		"Bahia":                "Bahia",
		"Bahia-BA":             "Bahia",
		"Bahia BA":             "Bahia",

		// Fortaleza
		"Fortaleza":            "Fortaleza",
		"Fortaleza-CE":         "Fortaleza",
		"Fortaleza CE":         "Fortaleza",

		// Cuiabá
		"Cuiabá":               "Cuiabá",
		"Cuiaba":               "Cuiabá",
		"Cuiabá-MT":            "Cuiabá",
		"Cuiaba MT":            "Cuiabá",

		// Ponte Preta
		"Ponte Preta":          "Ponte Preta",
		"Ponte Preta-SP":       "Ponte Preta",
		"Ponte Preta SP":       "Ponte Preta",

		// Goiás
		"Goiás":                "Goiás",
		"Goiass":               "Goiás",
		"Goiás GO":             "Goiás",
		"Goiás-GO":             "Goiás",

		// Coritiba
		"Coritiba":             "Coritiba",
		"Coritiba-PR":          "Coritiba",
		"Coritiba PR":          "Coritiba",
		"Coritiba FC":          "Coritiba",
		"CoritibaFootBallClub": "Coritiba",

		// Vitória
		"Vitória":              "Vitória",
		"Vitória-BA":           "Vitória",
		"Vitória BA":           "Vitória",
		"Vitoria":              "Vitória",

		// Santa Cruz

		// Sport Recife
		"Sport Recife":         "Sport Recife",
		"Sport":                "Sport Recife",
		"Sport-PE":             "Sport Recife",
		"Sport PE":             "Sport Recife",

		// América Mineiro
		"América Mineiro":      "América Mineiro",
		"América-MG":           "América Mineiro",
		"América MG":           "América Mineiro",
		"America Mineiro":      "América Mineiro",
		"America-MG":           "América Mineiro",
		"America MG":           "América Mineiro",

		// Avaí
		"Avaí":                 "Avaí",
		"Avai":                 "Avaí",
		"Avaí-SC":              "Avaí",
		"Avai SC":              "Avaí",

		// Bragantino
		"Bragantino":           "Bragantino",
		"Red Bull Bragantino":  "Bragantino",
		"Bragantino-SP":        "Bragantino",
		"Bragantino SP":        "Bragantino",

		// Juventude
		"Juventude":            "Juventude",
		"Juventude-RS":         "Juventude",
		"Juventude RS":         "Juventude",
	}

	for normalized, original := range aliases {
		store.TeamAliases[original] = normalized
	}
}

// normalizeTeamName converts team names to a consistent format
func normalizeTeamName(name string) string {
	if name == "" {
		return ""
	}
	// Remove state suffix if present
	name = strings.TrimSpace(name)
	if idx := strings.LastIndex(name, "-"); idx != -1 {
		// Check if what follows is a state abbreviation (2 letters)
		if idx+3 <= len(name) {
			suffix := name[idx+1 : idx+3]
			if suffix == "SP" || suffix == "RJ" || suffix == "MG" || suffix == "PR" ||
				suffix == "RS" || suffix == "BA" || suffix == "CE" || suffix == "MT" ||
				suffix == "PE" || suffix == "GO" || suffix == "SC" {
				name = name[:idx]
			}
		}
	}
	// Check in aliases map
	if normalized, ok := models.NewDataStore().TeamAliases[name]; ok {
		return normalized
	}
	return strings.TrimSpace(name)
}

// normalizeRound converts round names to a consistent format
func normalizeRound(round string) string {
	round = strings.TrimSpace(round)
	round = strings.ReplaceAll(round, "Final", "Final")
	round = strings.ReplaceAll(round, "Semifinal", "Semifinal")
	round = strings.ReplaceAll(round, "Quarterfinal", "Quarterfinal")
	return round
}
