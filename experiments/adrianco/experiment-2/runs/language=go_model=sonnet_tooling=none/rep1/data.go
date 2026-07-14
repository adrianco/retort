// Package main - Brazilian Soccer MCP Server
// data.go: Data structures and CSV loading for all 6 datasets.
// Loads match data from Brasileirao, Copa do Brasil, Libertadores, BR-Football-Dataset,
// and historical Brasileirao; plus FIFA player data. All data is held in memory.
package main

import (
	"encoding/csv"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// Match represents a unified match record across all datasets.
type Match struct {
	Date        string // YYYY-MM-DD
	HomeTeam    string
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Season      int
	Competition string // e.g. "Brasileirao", "Copa do Brasil", "Libertadores"
	Round       string
	Stage       string
	Arena       string
	// Extended stats (BR-Football-Dataset only)
	HomeCorner float64
	AwayCorner float64
	HomeShots  float64
	AwayShots  float64
}

// Player represents a FIFA player record.
type Player struct {
	ID           string
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
}

// Database holds all loaded data.
type Database struct {
	Matches []Match
	Players []Player
}

// NewDatabase creates a new empty database.
func NewDatabase() *Database {
	return &Database{}
}

// readCSV opens a CSV file and returns records as a slice of string maps keyed by header name.
// Handles UTF-8 BOM and lazy quotes.
func readCSV(filename string) ([]map[string]string, error) {
	f, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	// Strip UTF-8 BOM from first header field if present.
	if len(headers) > 0 {
		headers[0] = strings.TrimPrefix(headers[0], "\xEF\xBB\xBF")
		headers[0] = strings.TrimPrefix(headers[0], "\uFEFF")
		headers[0] = strings.TrimSpace(headers[0])
	}

	var records []map[string]string
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			// Skip malformed rows
			continue
		}
		record := make(map[string]string, len(headers))
		for i, h := range headers {
			if i < len(row) {
				record[h] = strings.TrimSpace(row[i])
			}
		}
		records = append(records, record)
	}
	return records, nil
}

// getField tries multiple field name variations and returns the first non-empty value found.
func getField(record map[string]string, keys ...string) string {
	for _, k := range keys {
		if v, ok := record[k]; ok && v != "" {
			return v
		}
	}
	return ""
}

// parseFloat parses a float64 from a string, returning 0 on error.
func parseFloat(s string) float64 {
	s = strings.TrimSpace(s)
	if s == "" || s == "NaN" || s == "nan" {
		return 0
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	return f
}

// LoadBrasileiraoMatches loads Brasileirao_Matches.csv.
func (db *Database) LoadBrasileiraoMatches(filename string) error {
	records, err := readCSV(filename)
	if err != nil {
		return err
	}
	for _, r := range records {
		dateStr := getField(r, "datetime")
		t, _ := parseDate(dateStr)
		homeGoals := parseGoals(getField(r, "home_goal"))
		awayGoals := parseGoals(getField(r, "away_goal"))
		season := parseSeason(getField(r, "season"))
		db.Matches = append(db.Matches, Match{
			Date:        formatDate(t),
			HomeTeam:    getField(r, "home_team"),
			AwayTeam:    getField(r, "away_team"),
			HomeGoals:   homeGoals,
			AwayGoals:   awayGoals,
			Season:      season,
			Competition: "Brasileirao",
			Round:       getField(r, "round"),
		})
	}
	return nil
}

// LoadCupMatches loads Brazilian_Cup_Matches.csv.
func (db *Database) LoadCupMatches(filename string) error {
	records, err := readCSV(filename)
	if err != nil {
		return err
	}
	for _, r := range records {
		dateStr := getField(r, "datetime")
		t, _ := parseDate(dateStr)
		homeGoals := parseGoals(getField(r, "home_goal"))
		awayGoals := parseGoals(getField(r, "away_goal"))
		season := parseSeason(getField(r, "season"))
		db.Matches = append(db.Matches, Match{
			Date:        formatDate(t),
			HomeTeam:    getField(r, "home_team"),
			AwayTeam:    getField(r, "away_team"),
			HomeGoals:   homeGoals,
			AwayGoals:   awayGoals,
			Season:      season,
			Competition: "Copa do Brasil",
			Round:       getField(r, "round"),
		})
	}
	return nil
}

// LoadLibertadoresMatches loads Libertadores_Matches.csv.
func (db *Database) LoadLibertadoresMatches(filename string) error {
	records, err := readCSV(filename)
	if err != nil {
		return err
	}
	for _, r := range records {
		dateStr := getField(r, "datetime")
		t, _ := parseDate(dateStr)
		homeGoals := parseGoals(getField(r, "home_goal"))
		awayGoals := parseGoals(getField(r, "away_goal"))
		season := parseSeason(getField(r, "season"))
		db.Matches = append(db.Matches, Match{
			Date:        formatDate(t),
			HomeTeam:    getField(r, "home_team"),
			AwayTeam:    getField(r, "away_team"),
			HomeGoals:   homeGoals,
			AwayGoals:   awayGoals,
			Season:      season,
			Competition: "Libertadores",
			Stage:       getField(r, "stage"),
		})
	}
	return nil
}

// LoadBRFootballDataset loads BR-Football-Dataset.csv.
func (db *Database) LoadBRFootballDataset(filename string) error {
	records, err := readCSV(filename)
	if err != nil {
		return err
	}
	for _, r := range records {
		dateStr := getField(r, "date")
		t, _ := parseDate(dateStr)
		homeGoals := parseGoals(getField(r, "home_goal"))
		awayGoals := parseGoals(getField(r, "away_goal"))

		competition := getField(r, "tournament")
		db.Matches = append(db.Matches, Match{
			Date:        formatDate(t),
			HomeTeam:    getField(r, "home"),
			AwayTeam:    getField(r, "away"),
			HomeGoals:   homeGoals,
			AwayGoals:   awayGoals,
			Competition: competition,
			HomeCorner:  parseFloat(getField(r, "home_corner")),
			AwayCorner:  parseFloat(getField(r, "away_corner")),
			HomeShots:   parseFloat(getField(r, "home_shots")),
			AwayShots:   parseFloat(getField(r, "away_shots")),
		})
	}
	return nil
}

// LoadHistoricalBrasileirao loads novo_campeonato_brasileiro.csv (Portuguese column names).
func (db *Database) LoadHistoricalBrasileirao(filename string) error {
	records, err := readCSV(filename)
	if err != nil {
		return err
	}
	for _, r := range records {
		dateStr := getField(r, "Data")
		t, _ := parseDate(dateStr)
		homeGoals := parseGoals(getField(r, "Gols_mandante"))
		awayGoals := parseGoals(getField(r, "Gols_visitante"))
		season := parseSeason(getField(r, "Ano"))
		db.Matches = append(db.Matches, Match{
			Date:        formatDate(t),
			HomeTeam:    getField(r, "Equipe_mandante"),
			AwayTeam:    getField(r, "Equipe_visitante"),
			HomeGoals:   homeGoals,
			AwayGoals:   awayGoals,
			Season:      season,
			Competition: "Brasileirao",
			Round:       getField(r, "Rodada"),
			Arena:       getField(r, "Arena"),
		})
	}
	return nil
}

// LoadFIFAPlayers loads fifa_data.csv.
func (db *Database) LoadFIFAPlayers(filename string) error {
	records, err := readCSV(filename)
	if err != nil {
		return err
	}
	for _, r := range records {
		name := getField(r, "Name")
		if name == "" {
			continue
		}
		age := parseGoals(getField(r, "Age"))
		overall := parseGoals(getField(r, "Overall"))
		potential := parseGoals(getField(r, "Potential"))
		db.Players = append(db.Players, Player{
			ID:           getField(r, "ID"),
			Name:         name,
			Age:          age,
			Nationality:  getField(r, "Nationality"),
			Overall:      overall,
			Potential:    potential,
			Club:         getField(r, "Club"),
			Position:     getField(r, "Position"),
			JerseyNumber: getField(r, "Jersey Number"),
			Height:       getField(r, "Height"),
			Weight:       getField(r, "Weight"),
		})
	}
	return nil
}

// LoadAll loads all datasets from the given directory.
func (db *Database) LoadAll(dir string) error {
	loaders := []struct {
		file   string
		loader func(string) error
	}{
		{"Brasileirao_Matches.csv", db.LoadBrasileiraoMatches},
		{"Brazilian_Cup_Matches.csv", db.LoadCupMatches},
		{"Libertadores_Matches.csv", db.LoadLibertadoresMatches},
		{"BR-Football-Dataset.csv", db.LoadBRFootballDataset},
		{"novo_campeonato_brasileiro.csv", db.LoadHistoricalBrasileirao},
		{"fifa_data.csv", db.LoadFIFAPlayers},
	}
	for _, l := range loaders {
		path := filepath.Join(dir, l.file)
		if err := l.loader(path); err != nil {
			return err
		}
	}
	return nil
}
