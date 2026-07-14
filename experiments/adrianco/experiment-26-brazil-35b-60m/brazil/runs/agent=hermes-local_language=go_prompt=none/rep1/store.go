package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

// DataStore holds all loaded data
type DataStore struct {
	mu             sync.RWMutex
	brasileirao    []BrasileiraoMatch
	copaDoBrasil   []CopaDoBrasilMatch
	libertadores   []LibertadoresMatch
	brFootball     []BRFootballMatch
	novoCampeonato []NovoCampeonatoMatch
	fifaPlayers    []FIFAPlayer
}

func NewDataStore() *DataStore {
	return &DataStore{}
}

// LoadAll loads all CSV files from the data directory
func (ds *DataStore) LoadAll(dataDir string) error {
	ds.mu.Lock()
	defer ds.mu.Unlock()

	if dataDir == "" {
		dataDir = "data/kaggle"
	}

	var errs []string
	if err := ds.loadBrasileirao(filepath.Join(dataDir, "Brasileirao_Matches.csv")); err != nil {
		errs = append(errs, fmt.Sprintf("Brasileirao: %v", err))
	}
	if err := ds.loadCopaDoBrasil(filepath.Join(dataDir, "Brazilian_Cup_Matches.csv")); err != nil {
		errs = append(errs, fmt.Sprintf("CopaDoBrasil: %v", err))
	}
	if err := ds.loadLibertadores(filepath.Join(dataDir, "Libertadores_Matches.csv")); err != nil {
		errs = append(errs, fmt.Sprintf("Libertadores: %v", err))
	}
	if err := ds.loadBRFootball(filepath.Join(dataDir, "BR-Football-Dataset.csv")); err != nil {
		errs = append(errs, fmt.Sprintf("BRFootball: %v", err))
	}
	if err := ds.loadNovoCampeonato(filepath.Join(dataDir, "novo_campeonato_brasileiro.csv")); err != nil {
		errs = append(errs, fmt.Sprintf("NovoCampeonato: %v", err))
	}
	if err := ds.loadFIFAPlayers(filepath.Join(dataDir, "fifa_data.csv")); err != nil {
		errs = append(errs, fmt.Sprintf("FIFA: %v", err))
	}

	if len(errs) > 0 {
		return fmt.Errorf("errors loading data: %s", strings.Join(errs, "; "))
	}
	return nil
}

func (ds *DataStore) loadBrasileirao(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}
	for i, rec := range records {
		if i == 0 || len(rec) < 9 {
			continue
		}
		ds.brasileirao = append(ds.brasileirao, BrasileiraoMatch{
			Datetime:      strings.TrimSpace(rec[0]),
			HomeTeam:      strings.TrimSpace(rec[1]),
			HomeTeamState: strings.TrimSpace(rec[2]),
			AwayTeam:      strings.TrimSpace(rec[3]),
			AwayTeamState: strings.TrimSpace(rec[4]),
			HomeGoal:      parseInt(rec[5]),
			AwayGoal:      parseInt(rec[6]),
			Season:        parseInt(rec[7]),
			Round:         parseInt(rec[8]),
			})
	}
	return nil
}

func (ds *DataStore) loadCopaDoBrasil(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}
	for i, rec := range records {
		if i == 0 || len(rec) < 7 {
			continue
		}
		ds.copaDoBrasil = append(ds.copaDoBrasil, CopaDoBrasilMatch{
			Round:       strings.TrimSpace(rec[0]),
			Datetime:    strings.TrimSpace(rec[1]),
			HomeTeam:    strings.TrimSpace(rec[2]),
			AwayTeam:    strings.TrimSpace(rec[3]),
			HomeGoal:    parseInt(rec[4]),
			AwayGoal:    parseInt(rec[5]),
			Season:      parseInt(rec[6]),
			Competition: "Copa do Brasil",
		})
	}
	return nil
}

func (ds *DataStore) loadLibertadores(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}
	for i, rec := range records {
		if i == 0 || len(rec) < 7 {
			continue
		}
		ds.libertadores = append(ds.libertadores, LibertadoresMatch{
			Datetime:    strings.TrimSpace(rec[0]),
			HomeTeam:    strings.TrimSpace(rec[1]),
			AwayTeam:    strings.TrimSpace(rec[2]),
			HomeGoal:    parseIntOrFloat(rec[3]),
			AwayGoal:    parseIntOrFloat(rec[4]),
			Season:      parseInt(rec[5]),
			Stage:       strings.TrimSpace(rec[6]),
			Competition: "Libertadores",
		})
	}
	return nil
}

func (ds *DataStore) loadBRFootball(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}
	for i, rec := range records {
		if i == 0 || len(rec) < 18 {
			continue
		}
		ds.brFootball = append(ds.brFootball, BRFootballMatch{
			Tournament:   strings.TrimSpace(rec[0]),
			HomeTeam:     strings.TrimSpace(rec[1]),
			HomeGoal:     parseFloat(rec[2]),
			AwayGoal:     parseFloat(rec[3]),
			AwayTeam:     strings.TrimSpace(rec[4]),
			HomeCorner:   parseFloat(rec[5]),
			AwayCorner:   parseFloat(rec[6]),
			HomeAttack:   parseFloat(rec[7]),
			AwayAttack:   parseFloat(rec[8]),
			HomeShots:    parseFloat(rec[9]),
			AwayShots:    parseFloat(rec[10]),
			Time:         strings.TrimSpace(rec[11]),
			Date:         strings.TrimSpace(rec[12]),
			HTDiff:       parseFloat(rec[13]),
			ATDiff:       parseFloat(rec[14]),
			HTResult:     strings.TrimSpace(rec[15]),
			ATResult:     strings.TrimSpace(rec[16]),
			TotalCorners: parseFloat(rec[17]),
		})
	}
	return nil
}

func (ds *DataStore) loadNovoCampeonato(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	reader.TrimLeadingSpace = true
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}
	for i, rec := range records {
		if i == 0 || len(rec) < 12 {
			continue
		}
		ds.novoCampeonato = append(ds.novoCampeonato, NovoCampeonatoMatch{
			ID:            strings.TrimSpace(rec[0]),
			DateStr:       strings.TrimSpace(rec[1]),
			Year:          parseInt(rec[2]),
			Round:         parseInt(rec[3]),
			HomeTeam:      strings.TrimSpace(rec[4]),
			AwayTeam:      strings.TrimSpace(rec[5]),
			HomeGoal:      parseInt(rec[6]),
			AwayGoal:      parseInt(rec[7]),
			HomeTeamState: strings.TrimSpace(rec[8]),
			AwayTeamState: strings.TrimSpace(rec[9]),
			Winner:        strings.TrimSpace(rec[10]),
			Arena:         strings.TrimSpace(rec[11]),
		})
	}
	return nil
}

func (ds *DataStore) loadFIFAPlayers(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	reader.FieldsPerRecord = -1

	header, err := reader.Read()
	if err != nil {
		return err
	}

	// Build header index map
	headerIdx := make(map[string]int)
	for i, h := range header {
		headerIdx[strings.TrimSpace(h)] = i
	}

	for {
		rec, err := reader.Read()
		if err != nil {
			break
		}
		if len(rec) < 10 {
			continue
		}

		name := strings.TrimSpace(rec[headerIdx["Name"]])
		nationality := strings.TrimSpace(rec[headerIdx["Nationality"]])
		club := strings.TrimSpace(rec[headerIdx["Club"]])
		position := strings.TrimSpace(rec[headerIdx["Position"]])

		player := FIFAPlayer{
			ID:          strings.TrimSpace(rec[headerIdx["ID"]]),
			Name:        name,
			Age:         parseInt(rec[headerIdx["Age"]]),
			Nationality: nationality,
			Overall:     parseInt(rec[headerIdx["Overall"]]),
			Potential:   parseInt(rec[headerIdx["Potential"]]),
			Club:        club,
			Position:    position,
			JerseyNumber: strings.TrimSpace(rec[headerIdx["Jersey Number"]]),
		}

		// Map skills by header
		skillCols := []string{
			"Crossing", "Finishing", "HeadingAccuracy",
			"ShortPassing", "Volleys", "Dribbling",
			"Curve", "FKAccuracy", "LongPassing",
			"BallControl", "Acceleration", "SprintSpeed",
			"Agility", "Reactions", "Balance",
			"ShotPower", "Jumping", "Stamina",
			"Strength", "LongShots", "Aggression",
			"Interceptions", "Positioning", "Vision",
			"Penalties", "Composure", "Marking",
			"StandingTackle", "SlidingTackle",
		}
		skillMap := map[string]*int{
			"Crossing":      &player.Crossing,
			"Finishing":     &player.Finishing,
			"HeadingAccuracy": &player.HeadingAccuracy,
			"ShortPassing":  &player.ShortPassing,
			"Volleys":       &player.Volleys,
			"Dribbling":     &player.Dribbling,
			"Curve":         &player.Curve,
			"FKAccuracy":    &player.FKAccuracy,
			"LongPassing":   &player.LongPassing,
			"BallControl":   &player.BallControl,
			"Acceleration":  &player.Acceleration,
			"SprintSpeed":   &player.SprintSpeed,
			"Agility":       &player.Agility,
			"Reactions":     &player.Reactions,
			"Balance":       &player.Balance,
			"ShotPower":     &player.ShotPower,
			"Jumping":       &player.Jumping,
			"Stamina":       &player.Stamina,
			"Strength":      &player.Strength,
			"LongShots":     &player.LongShots,
			"Aggression":    &player.Aggression,
			"Interceptions": &player.Interceptions,
			"Positioning":   &player.Positioning,
			"Vision":        &player.Vision,
			"Penalties":     &player.Penalties,
			"Composure":     &player.Composure,
			"Marking":       &player.Marking,
			"StandingTackle": &player.StandingTackle,
			"SlidingTackle": &player.SlidingTackle,
		}

		for _, col := range skillCols {
			idx := headerIdx[col]
			ptr := skillMap[col]
			if ptr != nil && idx < len(rec) {
				*ptr = parseInt(rec[idx])
			}
		}

		ds.fifaPlayers = append(ds.fifaPlayers, player)
	}
	return nil
}

// Accessors
func (ds *DataStore) GetBrasilieiraoMatches() []BrasileiraoMatch {
	ds.mu.RLock()
	defer ds.mu.RUnlock()
	cp := make([]BrasileiraoMatch, len(ds.brasileirao))
	copy(cp, ds.brasileirao)
	return cp
}

func (ds *DataStore) GetCopaDoBrasilMatches() []CopaDoBrasilMatch {
	ds.mu.RLock()
	defer ds.mu.RUnlock()
	cp := make([]CopaDoBrasilMatch, len(ds.copaDoBrasil))
	copy(cp, ds.copaDoBrasil)
	return cp
}

func (ds *DataStore) GetLibertadoresMatches() []LibertadoresMatch {
	ds.mu.RLock()
	defer ds.mu.RUnlock()
	cp := make([]LibertadoresMatch, len(ds.libertadores))
	copy(cp, ds.libertadores)
	return cp
}

func (ds *DataStore) GetBRFootballMatches() []BRFootballMatch {
	ds.mu.RLock()
	defer ds.mu.RUnlock()
	cp := make([]BRFootballMatch, len(ds.brFootball))
	copy(cp, ds.brFootball)
	return cp
}

func (ds *DataStore) GetNovoCampeonatoMatches() []NovoCampeonatoMatch {
	ds.mu.RLock()
	defer ds.mu.RUnlock()
	cp := make([]NovoCampeonatoMatch, len(ds.novoCampeonato))
	copy(cp, ds.novoCampeonato)
	return cp
}

func (ds *DataStore) GetFIFAPlayers() []FIFAPlayer {
	ds.mu.RLock()
	defer ds.mu.RUnlock()
	cp := make([]FIFAPlayer, len(ds.fifaPlayers))
	copy(cp, ds.fifaPlayers)
	return cp
}

// Helpers
func parseInt(s string) int {
	v, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		return 0
	}
	return v
}

func parseIntOrFloat(s string) int {
	f := parseFloat(s)
	return int(f)
}

func parseFloat(s string) float64 {
	v, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil {
		return 0
	}
	return v
}

// NormalizeTeamName removes state suffixes like "-SP", "-RJ", "-MG"
func NormalizeTeamName(name string) string {
	normalized := name
	suffixes := []string{
		"-AM", "-BA", "-CE", "-DF", "-ES", "-GO", "-MA", "-MG",
		"-MS", "-MT", "-PA", "-PB", "-PE", "-PI", "-PR", "-RJ",
		"-RN", "-RO", "-RR", "-RS", "-SC", "-SE", "-SP", "-TO",
	}
	for _, sfx := range suffixes {
		if strings.HasSuffix(strings.ToUpper(normalized), sfx) {
			normalized = normalized[:len(normalized)-len(sfx)]
			break
		}
	}
	normalized = strings.TrimSpace(normalized)
	normalized = strings.TrimSuffix(normalized, "-")
	return normalized
}

// NormalizeName removes accents and lowercases
func NormalizeName(name string) string {
	name = strings.ToLower(strings.TrimSpace(name))
	var result []rune
	for _, r := range name {
		switch r {
		case 'á', 'à', 'â', 'ã', 'ä':
			result = append(result, 'a')
		case 'é', 'è', 'ê', 'ë':
			result = append(result, 'e')
		case 'í', 'ì', 'î', 'ï':
			result = append(result, 'i')
		case 'ó', 'ò', 'ô', 'õ', 'ö':
			result = append(result, 'o')
		case 'ú', 'ù', 'û', 'ü':
			result = append(result, 'u')
		case 'ç':
			result = append(result, 'c')
		default:
			result = append(result, r)
		}
	}
	return string(result)
}

// SimilarName checks if two team names are similar
func SimilarName(a, b string) bool {
	return NormalizeName(a) == NormalizeName(b)
}

// ExtractDate extracts date from datetime string
func ExtractDate(dt string) string {
	dt = strings.TrimSpace(dt)
	if len(dt) >= 10 {
		return dt[:10]
	}
	return dt
}
