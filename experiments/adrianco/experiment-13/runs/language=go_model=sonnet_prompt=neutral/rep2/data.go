package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Match represents a soccer match from any of the CSV datasets.
type Match struct {
	HomeTeam    string
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Date        time.Time
	Season      int
	Round       string
	Competition string
	Stage       string
	Arena       string
	HomeState   string
	AwayState   string
	// Extended stats (only present for BR-Football-Dataset rows)
	HomeCorners float64
	AwayCorners float64
	HomeShots   float64
	AwayShots   float64
	HasStats    bool
}

// Player represents a FIFA player entry.
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber string
	Height       string
	Weight       string
	Value        string
	Wage         string
}

// Database holds all loaded data.
type Database struct {
	Matches []Match
	Players []Player
}

var dateFormats = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05Z",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006",
}

func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	for _, f := range dateFormats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

func parseGoals(s string) int {
	s = strings.TrimSpace(s)
	// Strip surrounding quotes that can survive CSV LazyQuotes parsing
	s = strings.Trim(s, "\"")
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i
	}
	return 0
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	i, _ := strconv.Atoi(s)
	return i
}

func parseFloat(s string) float64 {
	s = strings.TrimSpace(s)
	f, _ := strconv.ParseFloat(s, 64)
	return f
}

// readCSV opens and parses a CSV file, returning headers and rows.
// It handles BOM markers in the file.
func readCSV(path string) ([]string, [][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true

	records, err := r.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	if len(records) == 0 {
		return nil, nil, nil
	}

	headers := records[0]
	// Strip UTF-8 BOM from first header field
	if len(headers) > 0 {
		// Strip UTF-8 BOM (EF BB BF) that some CSV files include
		headers[0] = strings.TrimPrefix(headers[0], "\xef\xbb\xbf")
		// Also handle BOM expressed as a Go rune (U+FEFF)
		headers[0] = strings.TrimPrefix(headers[0], "\ufeff")
	}
	return headers, records[1:], nil
}

// headerIndex builds a map from column name to index.
func headerIndex(headers []string) map[string]int {
	m := make(map[string]int, len(headers))
	for i, h := range headers {
		m[strings.TrimSpace(h)] = i
	}
	return m
}

// col safely retrieves a column value by name.
func col(row []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// loadBrasileirao loads Brasileirao_Matches.csv
func loadBrasileirao(path string) ([]Match, error) {
	headers, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	idx := headerIndex(headers)

	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			HomeTeam:    col(row, idx, "home_team"),
			AwayTeam:    col(row, idx, "away_team"),
			HomeGoals:   parseGoals(col(row, idx, "home_goal")),
			AwayGoals:   parseGoals(col(row, idx, "away_goal")),
			Date:        parseDate(col(row, idx, "datetime")),
			Season:      parseInt(col(row, idx, "season")),
			Round:       col(row, idx, "round"),
			HomeState:   col(row, idx, "home_team_state"),
			AwayState:   col(row, idx, "away_team_state"),
			Competition: "Brasileirão Serie A",
		}
		if m.HomeTeam == "" {
			continue
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadCopaDoBrasil loads Brazilian_Cup_Matches.csv
func loadCopaDoBrasil(path string) ([]Match, error) {
	headers, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	idx := headerIndex(headers)

	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			HomeTeam:    col(row, idx, "home_team"),
			AwayTeam:    col(row, idx, "away_team"),
			HomeGoals:   parseGoals(col(row, idx, "home_goal")),
			AwayGoals:   parseGoals(col(row, idx, "away_goal")),
			Date:        parseDate(col(row, idx, "datetime")),
			Season:      parseInt(col(row, idx, "season")),
			Round:       col(row, idx, "round"),
			Competition: "Copa do Brasil",
		}
		if m.HomeTeam == "" {
			continue
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadLibertadores loads Libertadores_Matches.csv
func loadLibertadores(path string) ([]Match, error) {
	headers, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	idx := headerIndex(headers)

	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			HomeTeam:    col(row, idx, "home_team"),
			AwayTeam:    col(row, idx, "away_team"),
			HomeGoals:   parseGoals(col(row, idx, "home_goal")),
			AwayGoals:   parseGoals(col(row, idx, "away_goal")),
			Date:        parseDate(col(row, idx, "datetime")),
			Season:      parseInt(col(row, idx, "season")),
			Stage:       col(row, idx, "stage"),
			Competition: "Copa Libertadores",
		}
		if m.HomeTeam == "" {
			continue
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadBRFootball loads BR-Football-Dataset.csv
func loadBRFootball(path string) ([]Match, error) {
	headers, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	idx := headerIndex(headers)

	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			HomeTeam:    col(row, idx, "home"),
			AwayTeam:    col(row, idx, "away"),
			HomeGoals:   parseGoals(col(row, idx, "home_goal")),
			AwayGoals:   parseGoals(col(row, idx, "away_goal")),
			Date:        parseDate(col(row, idx, "date")),
			Competition: col(row, idx, "tournament"),
			HomeCorners: parseFloat(col(row, idx, "home_corner")),
			AwayCorners: parseFloat(col(row, idx, "away_corner")),
			HomeShots:   parseFloat(col(row, idx, "home_shots")),
			AwayShots:   parseFloat(col(row, idx, "away_shots")),
			HasStats:    true,
		}
		// Infer season from date
		if !m.Date.IsZero() {
			m.Season = m.Date.Year()
		}
		if m.HomeTeam == "" {
			continue
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// brasileiraoMatchesStartYear is the first year covered by Brasileirao_Matches.csv.
// Seasons from this year onwards are skipped in novo_campeonato_brasileiro.csv to
// avoid double-counting the same matches with different team name conventions.
const brasileiraoMatchesStartYear = 2012

// loadNovoCampeonato loads novo_campeonato_brasileiro.csv.
// Only loads seasons before brasileiraoMatchesStartYear to avoid overlap.
func loadNovoCampeonato(path string) ([]Match, error) {
	headers, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	idx := headerIndex(headers)

	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		season := parseInt(col(row, idx, "Ano"))
		// Skip seasons already covered by Brasileirao_Matches.csv
		if season >= brasileiraoMatchesStartYear {
			continue
		}
		m := Match{
			HomeTeam:    col(row, idx, "Equipe_mandante"),
			AwayTeam:    col(row, idx, "Equipe_visitante"),
			HomeGoals:   parseGoals(col(row, idx, "Gols_mandante")),
			AwayGoals:   parseGoals(col(row, idx, "Gols_visitante")),
			Date:        parseDate(col(row, idx, "Data")),
			Season:      season,
			Round:       col(row, idx, "Rodada"),
			HomeState:   col(row, idx, "Mandante_UF"),
			AwayState:   col(row, idx, "Visitante_UF"),
			Arena:       col(row, idx, "Arena"),
			Competition: "Brasileirão Serie A",
		}
		if m.HomeTeam == "" {
			continue
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadFIFA loads fifa_data.csv
func loadFIFA(path string) ([]Player, error) {
	headers, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	idx := headerIndex(headers)

	players := make([]Player, 0, len(rows))
	for _, row := range rows {
		p := Player{
			ID:           parseInt(col(row, idx, "ID")),
			Name:         col(row, idx, "Name"),
			Age:          parseInt(col(row, idx, "Age")),
			Nationality:  col(row, idx, "Nationality"),
			Overall:      parseInt(col(row, idx, "Overall")),
			Potential:    parseInt(col(row, idx, "Potential")),
			Club:         col(row, idx, "Club"),
			Position:     col(row, idx, "Position"),
			JerseyNumber: col(row, idx, "Jersey Number"),
			Height:       col(row, idx, "Height"),
			Weight:       col(row, idx, "Weight"),
			Value:        col(row, idx, "Value"),
			Wage:         col(row, idx, "Wage"),
		}
		if p.Name == "" {
			continue
		}
		players = append(players, p)
	}
	return players, nil
}

// loadDatabase loads all CSV files from the given directory.
func loadDatabase(dataDir string) (*Database, error) {
	db := &Database{}

	type matchLoader struct {
		file string
		fn   func(string) ([]Match, error)
	}

	loaders := []matchLoader{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCopaDoBrasil},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadBRFootball},
		{"novo_campeonato_brasileiro.csv", loadNovoCampeonato},
	}

	for _, l := range loaders {
		path := filepath.Join(dataDir, l.file)
		matches, err := l.fn(path)
		if err != nil {
			return nil, fmt.Errorf("loading %s: %w", l.file, err)
		}
		db.Matches = append(db.Matches, matches...)
	}

	players, err := loadFIFA(filepath.Join(dataDir, "fifa_data.csv"))
	if err != nil {
		return nil, fmt.Errorf("loading fifa_data.csv: %w", err)
	}
	db.Players = players

	return db, nil
}
