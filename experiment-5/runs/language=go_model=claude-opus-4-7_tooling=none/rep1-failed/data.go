package main

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Competition constants.
const (
	CompBrasileirao   = "Brasileirão Série A"
	CompCopaDoBrasil  = "Copa do Brasil"
	CompLibertadores  = "Copa Libertadores"
	CompHistoricalBSL = "Brasileirão (Histórico 2003-2019)"
)

// Match is the normalized match record used across data sources.
type Match struct {
	Date        time.Time
	Competition string
	Season      int
	Round       string
	Stage       string
	HomeTeam    string
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Arena       string

	// Extended stats (only set for BR-Football-Dataset rows).
	HomeCorners  int
	AwayCorners  int
	HomeShots    int
	AwayShots    int
	TotalCorners int
	HasStats     bool

	// Source CSV filename for provenance.
	Source string
}

// Player is a row from fifa_data.csv (the columns we keep).
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
	PreferredFt  string
}

// DB holds the loaded dataset.
type DB struct {
	Matches []Match
	Players []Player
}

// DataRoot returns the directory where the CSVs live.
func DataRoot(base string) string {
	return filepath.Join(base, "data", "kaggle")
}

// LoadDB reads all six CSV files under <base>/data/kaggle and returns a DB.
// Individual file errors are reported but do not stop other files from
// loading; if every file fails, the function returns an error.
func LoadDB(base string) (*DB, error) {
	root := DataRoot(base)
	db := &DB{}

	type loader struct {
		file string
		fn   func(string, *DB) (int, error)
	}
	loaders := []loader{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadBRFootball},
		{"novo_campeonato_brasileiro.csv", loadNovoCampeonato},
		{"fifa_data.csv", loadFifa},
	}

	var errs []string
	successCount := 0
	for _, ld := range loaders {
		path := filepath.Join(root, ld.file)
		n, err := ld.fn(path, db)
		if err != nil {
			errs = append(errs, fmt.Sprintf("%s: %v", ld.file, err))
			continue
		}
		successCount++
		_ = n
	}
	if successCount == 0 {
		return nil, fmt.Errorf("no CSVs could be loaded: %s", strings.Join(errs, "; "))
	}
	return db, nil
}

// readCSV opens and returns a csv.Reader configured for variable field counts.
func readCSV(path string) (*os.File, *csv.Reader, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	return f, r, nil
}

// parseDate tries a series of formats and returns a zero time on failure.
func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}
	}
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02",
		"02/01/2006",
		"01/02/2006",
		time.RFC3339,
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// atoiSafe parses a numeric string (allowing decimals like "1.0"), returning 0.
func atoiSafe(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if v, err := strconv.Atoi(s); err == nil {
		return v
	}
	if v, err := strconv.ParseFloat(s, 64); err == nil {
		if math.IsNaN(v) || math.IsInf(v, 0) {
			return 0
		}
		return int(v)
	}
	return 0
}

// indexHeaders maps lower-case column names to their column index.
func indexHeaders(header []string) map[string]int {
	out := make(map[string]int, len(header))
	for i, h := range header {
		out[strings.ToLower(strings.TrimSpace(strings.TrimPrefix(h, "﻿")))] = i
	}
	return out
}

func get(row []string, idx map[string]int, key string) string {
	i, ok := idx[strings.ToLower(key)]
	if !ok || i < 0 || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// --- per-file loaders -----------------------------------------------------

func loadBrasileirao(path string, db *DB) (int, error) {
	f, r, err := readCSV(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return 0, err
	}
	idx := indexHeaders(header)
	count := 0
	for {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(get(row, idx, "datetime")),
			Competition: CompBrasileirao,
			Season:      atoiSafe(get(row, idx, "season")),
			Round:       get(row, idx, "round"),
			HomeTeam:    get(row, idx, "home_team"),
			AwayTeam:    get(row, idx, "away_team"),
			HomeGoals:   atoiSafe(get(row, idx, "home_goal")),
			AwayGoals:   atoiSafe(get(row, idx, "away_goal")),
			Source:      filepath.Base(path),
		}
		if m.HomeTeam == "" && m.AwayTeam == "" {
			continue
		}
		db.Matches = append(db.Matches, m)
		count++
	}
	return count, nil
}

func loadCup(path string, db *DB) (int, error) {
	f, r, err := readCSV(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return 0, err
	}
	idx := indexHeaders(header)
	count := 0
	for {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(get(row, idx, "datetime")),
			Competition: CompCopaDoBrasil,
			Season:      atoiSafe(get(row, idx, "season")),
			Round:       get(row, idx, "round"),
			HomeTeam:    get(row, idx, "home_team"),
			AwayTeam:    get(row, idx, "away_team"),
			HomeGoals:   atoiSafe(get(row, idx, "home_goal")),
			AwayGoals:   atoiSafe(get(row, idx, "away_goal")),
			Source:      filepath.Base(path),
		}
		if m.HomeTeam == "" && m.AwayTeam == "" {
			continue
		}
		db.Matches = append(db.Matches, m)
		count++
	}
	return count, nil
}

func loadLibertadores(path string, db *DB) (int, error) {
	f, r, err := readCSV(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return 0, err
	}
	idx := indexHeaders(header)
	count := 0
	for {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(get(row, idx, "datetime")),
			Competition: CompLibertadores,
			Season:      atoiSafe(get(row, idx, "season")),
			Stage:       get(row, idx, "stage"),
			HomeTeam:    get(row, idx, "home_team"),
			AwayTeam:    get(row, idx, "away_team"),
			HomeGoals:   atoiSafe(get(row, idx, "home_goal")),
			AwayGoals:   atoiSafe(get(row, idx, "away_goal")),
			Source:      filepath.Base(path),
		}
		if m.HomeTeam == "" && m.AwayTeam == "" {
			continue
		}
		db.Matches = append(db.Matches, m)
		count++
	}
	return count, nil
}

func loadBRFootball(path string, db *DB) (int, error) {
	f, r, err := readCSV(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return 0, err
	}
	idx := indexHeaders(header)
	count := 0
	for {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			continue
		}
		date := parseDate(get(row, idx, "date"))
		comp := get(row, idx, "tournament")
		if comp == "" {
			comp = "Unknown"
		}
		m := Match{
			Date:         date,
			Competition:  comp,
			Season:       date.Year(),
			HomeTeam:     get(row, idx, "home"),
			AwayTeam:     get(row, idx, "away"),
			HomeGoals:    atoiSafe(get(row, idx, "home_goal")),
			AwayGoals:    atoiSafe(get(row, idx, "away_goal")),
			HomeCorners:  atoiSafe(get(row, idx, "home_corner")),
			AwayCorners:  atoiSafe(get(row, idx, "away_corner")),
			HomeShots:    atoiSafe(get(row, idx, "home_shots")),
			AwayShots:    atoiSafe(get(row, idx, "away_shots")),
			TotalCorners: atoiSafe(get(row, idx, "total_corners")),
			HasStats:     true,
			Source:       filepath.Base(path),
		}
		if m.HomeTeam == "" && m.AwayTeam == "" {
			continue
		}
		db.Matches = append(db.Matches, m)
		count++
	}
	return count, nil
}

func loadNovoCampeonato(path string, db *DB) (int, error) {
	f, r, err := readCSV(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return 0, err
	}
	idx := indexHeaders(header)
	count := 0
	for {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(get(row, idx, "data")),
			Competition: CompHistoricalBSL,
			Season:      atoiSafe(get(row, idx, "ano")),
			Round:       get(row, idx, "rodada"),
			HomeTeam:    get(row, idx, "equipe_mandante"),
			AwayTeam:    get(row, idx, "equipe_visitante"),
			HomeGoals:   atoiSafe(get(row, idx, "gols_mandante")),
			AwayGoals:   atoiSafe(get(row, idx, "gols_visitante")),
			Arena:       get(row, idx, "arena"),
			Source:      filepath.Base(path),
		}
		if m.HomeTeam == "" && m.AwayTeam == "" {
			continue
		}
		db.Matches = append(db.Matches, m)
		count++
	}
	return count, nil
}

func loadFifa(path string, db *DB) (int, error) {
	f, r, err := readCSV(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return 0, err
	}
	idx := indexHeaders(header)
	count := 0
	for {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			continue
		}
		p := Player{
			ID:           atoiSafe(get(row, idx, "id")),
			Name:         get(row, idx, "name"),
			Age:          atoiSafe(get(row, idx, "age")),
			Nationality:  get(row, idx, "nationality"),
			Overall:      atoiSafe(get(row, idx, "overall")),
			Potential:    atoiSafe(get(row, idx, "potential")),
			Club:         get(row, idx, "club"),
			Position:     get(row, idx, "position"),
			JerseyNumber: get(row, idx, "jersey number"),
			Height:       get(row, idx, "height"),
			Weight:       get(row, idx, "weight"),
			PreferredFt:  get(row, idx, "preferred foot"),
		}
		if p.Name == "" {
			continue
		}
		db.Players = append(db.Players, p)
		count++
	}
	return count, nil
}
