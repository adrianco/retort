package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

// headerIndex builds a map from column name to index.
func headerIndex(record []string) map[string]int {
	m := make(map[string]int, len(record))
	for i, h := range record {
		// Strip BOM and whitespace
		h = strings.TrimSpace(strings.TrimPrefix(h, "\xef\xbb\xbf"))
		m[h] = i
	}
	return m
}

func getField(record []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(record) {
		return ""
	}
	return strings.TrimSpace(record[i])
}

func getInt(record []string, idx map[string]int, name string) int {
	v := getField(record, idx, name)
	v = strings.Trim(v, `"`)
	n, _ := strconv.Atoi(v)
	return n
}

func getFloat(record []string, idx map[string]int, name string) float64 {
	v := getField(record, idx, name)
	f, _ := strconv.ParseFloat(v, 64)
	return f
}

// parseBrasileiraoCSV parses the Brasileirao_Matches.csv format.
func parseBrasileiraoCSV(r io.Reader) ([]Match, error) {
	cr := csv.NewReader(r)
	cr.LazyQuotes = true

	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("reading header: %w", err)
	}
	idx := headerIndex(header)

	var matches []Match
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		homeGoal := getInt(rec, idx, "home_goal")
		awayGoal := getInt(rec, idx, "away_goal")
		season := getInt(rec, idx, "season")
		round := getField(rec, idx, "round")
		// Store original team name (with state suffix) for disambiguation in standings.
		// normalizeTeamName is only called inside matchKey/teamContains for search.
		matches = append(matches, Match{
			HomeTeam:    getField(rec, idx, "home_team"),
			AwayTeam:    getField(rec, idx, "away_team"),
			HomeGoal:    homeGoal,
			AwayGoal:    awayGoal,
			Season:      season,
			Round:       round,
			Date:        parseDate(getField(rec, idx, "datetime")),
			Competition: "Brasileirao",
		})
	}
	return matches, nil
}

// parseCupCSV parses the Brazilian_Cup_Matches.csv format.
func parseCupCSV(r io.Reader) ([]Match, error) {
	cr := csv.NewReader(r)
	cr.LazyQuotes = true

	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("reading header: %w", err)
	}
	idx := headerIndex(header)

	var matches []Match
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		matches = append(matches, Match{
			HomeTeam:    getField(rec, idx, "home_team"),
			AwayTeam:    getField(rec, idx, "away_team"),
			HomeGoal:    getInt(rec, idx, "home_goal"),
			AwayGoal:    getInt(rec, idx, "away_goal"),
			Season:      getInt(rec, idx, "season"),
			Round:       getField(rec, idx, "round"),
			Date:        parseDate(getField(rec, idx, "datetime")),
			Competition: "Copa do Brasil",
		})
	}
	return matches, nil
}

// parseLibertadoresCSV parses the Libertadores_Matches.csv format.
func parseLibertadoresCSV(r io.Reader) ([]Match, error) {
	cr := csv.NewReader(r)
	cr.LazyQuotes = true

	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("reading header: %w", err)
	}
	idx := headerIndex(header)

	var matches []Match
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		// goals are sometimes quoted strings in this file
		homeGoalStr := strings.Trim(getField(rec, idx, "home_goal"), `"`)
		awayGoalStr := strings.Trim(getField(rec, idx, "away_goal"), `"`)
		homeGoal, _ := strconv.Atoi(homeGoalStr)
		awayGoal, _ := strconv.Atoi(awayGoalStr)

		matches = append(matches, Match{
			HomeTeam:    getField(rec, idx, "home_team"),
			AwayTeam:    getField(rec, idx, "away_team"),
			HomeGoal:    homeGoal,
			AwayGoal:    awayGoal,
			Season:      getInt(rec, idx, "season"),
			Date:        parseDate(getField(rec, idx, "datetime")),
			Competition: "Libertadores",
			Stage:       getField(rec, idx, "stage"),
		})
	}
	return matches, nil
}

// parseBRFootballCSV parses the BR-Football-Dataset.csv format.
func parseBRFootballCSV(r io.Reader) ([]Match, error) {
	cr := csv.NewReader(r)
	cr.LazyQuotes = true

	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("reading header: %w", err)
	}
	idx := headerIndex(header)

	var matches []Match
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		// goals are floats in this file
		homeGoalF := getFloat(rec, idx, "home_goal")
		awayGoalF := getFloat(rec, idx, "away_goal")
		tournament := getField(rec, idx, "tournament")
		date := parseDate(getField(rec, idx, "date"))
		// Extract year from date for season
		season := 0
		if len(date) >= 4 {
			season, _ = strconv.Atoi(date[:4])
		}

		matches = append(matches, Match{
			HomeTeam:    getField(rec, idx, "home"),
			AwayTeam:    getField(rec, idx, "away"),
			HomeGoal:    int(homeGoalF),
			AwayGoal:    int(awayGoalF),
			Season:      season,
			Date:        date,
			Competition: tournament,
			HomeCorner:  getFloat(rec, idx, "home_corner"),
			AwayCorner:  getFloat(rec, idx, "away_corner"),
			HomeShots:   getFloat(rec, idx, "home_shots"),
			AwayShots:   getFloat(rec, idx, "away_shots"),
		})
	}
	return matches, nil
}

// parseHistoricalCSV parses the novo_campeonato_brasileiro.csv format.
func parseHistoricalCSV(r io.Reader) ([]Match, error) {
	cr := csv.NewReader(r)
	cr.LazyQuotes = true

	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("reading header: %w", err)
	}
	idx := headerIndex(header)

	var matches []Match
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		yearStr := getField(rec, idx, "Ano")
		year, _ := strconv.Atoi(yearStr)
		roundStr := getField(rec, idx, "Rodada")

		matches = append(matches, Match{
			HomeTeam:    getField(rec, idx, "Equipe_mandante"),
			AwayTeam:    getField(rec, idx, "Equipe_visitante"),
			HomeGoal:    getInt(rec, idx, "Gols_mandante"),
			AwayGoal:    getInt(rec, idx, "Gols_visitante"),
			Season:      year,
			Round:       roundStr,
			Date:        parseDate(getField(rec, idx, "Data")),
			Competition: "Brasileirao",
			Arena:       getField(rec, idx, "Arena"),
		})
	}
	return matches, nil
}

// parseFIFACSV parses the fifa_data.csv format (has BOM and index column).
func parseFIFACSV(r io.Reader) ([]Player, error) {
	cr := csv.NewReader(r)
	cr.LazyQuotes = true
	cr.FieldsPerRecord = -1 // variable fields

	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("reading header: %w", err)
	}
	idx := headerIndex(header)

	var players []Player
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		overall := getInt(rec, idx, "Overall")
		potential := getInt(rec, idx, "Potential")
		age := getInt(rec, idx, "Age")

		players = append(players, Player{
			ID:           getField(rec, idx, "ID"),
			Name:         getField(rec, idx, "Name"),
			Age:          age,
			Nationality:  getField(rec, idx, "Nationality"),
			Overall:      overall,
			Potential:    potential,
			Club:         getField(rec, idx, "Club"),
			Position:     getField(rec, idx, "Position"),
			JerseyNumber: getField(rec, idx, "Jersey Number"),
			Height:       getField(rec, idx, "Height"),
			Weight:       getField(rec, idx, "Weight"),
		})
	}
	return players, nil
}

// loadAllData loads all CSV files from dataDir into a Database.
func loadAllData(dataDir string) (*Database, error) {
	db := &Database{}

	files := []struct {
		name   string
		parser func(io.Reader) ([]Match, error)
	}{
		{dataDir + "/Brasileirao_Matches.csv", parseBrasileiraoCSV},
		{dataDir + "/Brazilian_Cup_Matches.csv", parseCupCSV},
		{dataDir + "/Libertadores_Matches.csv", parseLibertadoresCSV},
		{dataDir + "/BR-Football-Dataset.csv", parseBRFootballCSV},
		{dataDir + "/novo_campeonato_brasileiro.csv", parseHistoricalCSV},
	}

	seen := make(map[string]bool)
	for _, f := range files {
		file, err := os.Open(f.name)
		if err != nil {
			return nil, fmt.Errorf("opening %s: %w", f.name, err)
		}
		matches, err := f.parser(stripBOM(file))
		file.Close()
		if err != nil {
			return nil, fmt.Errorf("parsing %s: %w", f.name, err)
		}
		for _, m := range matches {
			key := matchKey(m)
			if seen[key] {
				continue
			}
			seen[key] = true
			db.Matches = append(db.Matches, m)
		}
	}

	// Load FIFA players
	fifaFile, err := os.Open(dataDir + "/fifa_data.csv")
	if err != nil {
		return nil, fmt.Errorf("opening fifa_data.csv: %w", err)
	}
	players, err := parseFIFACSV(stripBOM(fifaFile))
	fifaFile.Close()
	if err != nil {
		return nil, fmt.Errorf("parsing fifa_data.csv: %w", err)
	}
	db.Players = players

	return db, nil
}

// stripBOM returns a reader that skips a UTF-8 BOM if present.
func stripBOM(r io.ReadSeeker) io.Reader {
	bom := make([]byte, 3)
	n, _ := r.Read(bom)
	if n == 3 && bom[0] == 0xEF && bom[1] == 0xBB && bom[2] == 0xBF {
		return r // BOM consumed
	}
	// No BOM – seek back and return original
	r.Seek(0, io.SeekStart)
	return r
}
