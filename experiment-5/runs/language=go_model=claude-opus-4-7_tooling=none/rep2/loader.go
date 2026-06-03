package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// LoadDataset loads every CSV under `dataDir` (typically data/kaggle) into
// a Dataset. Missing files are skipped with a warning so a partial install
// still produces a usable server.
func LoadDataset(dataDir string) (*Dataset, error) {
	ds := &Dataset{}

	type loader struct {
		name string
		fn   func(string) ([]Match, error)
	}
	matchLoaders := []loader{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadBRFootball},
		{"novo_campeonato_brasileiro.csv", loadNovoCampeonato},
	}
	for _, l := range matchLoaders {
		path := filepath.Join(dataDir, l.name)
		if _, err := os.Stat(path); err != nil {
			fmt.Fprintf(os.Stderr, "warning: skipping %s: %v\n", path, err)
			continue
		}
		matches, err := l.fn(path)
		if err != nil {
			return nil, fmt.Errorf("loading %s: %w", l.name, err)
		}
		ds.Matches = append(ds.Matches, matches...)
	}

	fifaPath := filepath.Join(dataDir, "fifa_data.csv")
	if _, err := os.Stat(fifaPath); err == nil {
		players, err := loadFifa(fifaPath)
		if err != nil {
			return nil, fmt.Errorf("loading fifa_data.csv: %w", err)
		}
		ds.Players = players
	} else {
		fmt.Fprintf(os.Stderr, "warning: skipping %s: %v\n", fifaPath, err)
	}

	return ds, nil
}

func openCSV(path string) (*os.File, *csv.Reader, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // tolerate ragged rows
	r.LazyQuotes = true
	r.ReuseRecord = false
	return f, r, nil
}

func indexHeader(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}
	return idx
}

func get(rec []string, idx map[string]int, key string) string {
	i, ok := idx[key]
	if !ok || i < 0 || i >= len(rec) {
		return ""
	}
	return strings.TrimSpace(rec[i])
}

func atoi(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

func atof(s string) float64 {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return f
	}
	return 0
}

// parseDate handles the variety of formats present across our CSVs.
func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}
	}
	layouts := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02 15:04",
		"2006-01-02",
		"02/01/2006",
		"2/1/2006",
		"01/02/2006",
	}
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

func loadBrasileirao(path string) ([]Match, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexHeader(header)

	var matches []Match
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		date := parseDate(get(rec, idx, "datetime"))
		m := Match{
			Source:      "Brasileirao_Matches.csv",
			Competition: "Brasileirão Série A",
			Date:        date,
			Season:      atoi(get(rec, idx, "season")),
			Round:       get(rec, idx, "round"),
			HomeTeam:    get(rec, idx, "home_team"),
			AwayTeam:    get(rec, idx, "away_team"),
			HomeState:   get(rec, idx, "home_team_state"),
			AwayState:   get(rec, idx, "away_team_state"),
			HomeGoals:   atoi(get(rec, idx, "home_goal")),
			AwayGoals:   atoi(get(rec, idx, "away_goal")),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func loadCup(path string) ([]Match, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexHeader(header)

	var matches []Match
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		m := Match{
			Source:      "Brazilian_Cup_Matches.csv",
			Competition: "Copa do Brasil",
			Date:        parseDate(get(rec, idx, "datetime")),
			Season:      atoi(get(rec, idx, "season")),
			Round:       get(rec, idx, "round"),
			HomeTeam:    get(rec, idx, "home_team"),
			AwayTeam:    get(rec, idx, "away_team"),
			HomeGoals:   atoi(get(rec, idx, "home_goal")),
			AwayGoals:   atoi(get(rec, idx, "away_goal")),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func loadLibertadores(path string) ([]Match, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexHeader(header)

	var matches []Match
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		m := Match{
			Source:      "Libertadores_Matches.csv",
			Competition: "Copa Libertadores",
			Date:        parseDate(get(rec, idx, "datetime")),
			Season:      atoi(get(rec, idx, "season")),
			Stage:       get(rec, idx, "stage"),
			HomeTeam:    get(rec, idx, "home_team"),
			AwayTeam:    get(rec, idx, "away_team"),
			HomeGoals:   atoi(get(rec, idx, "home_goal")),
			AwayGoals:   atoi(get(rec, idx, "away_goal")),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func loadBRFootball(path string) ([]Match, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexHeader(header)

	var matches []Match
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		date := parseDate(get(rec, idx, "date"))
		season := 0
		if !date.IsZero() {
			season = date.Year()
		}
		tournament := get(rec, idx, "tournament")
		m := Match{
			Source:      "BR-Football-Dataset.csv",
			Competition: tournament,
			Date:        date,
			Season:      season,
			HomeTeam:    get(rec, idx, "home"),
			AwayTeam:    get(rec, idx, "away"),
			HomeGoals:   atoi(get(rec, idx, "home_goal")),
			AwayGoals:   atoi(get(rec, idx, "away_goal")),
			HomeCorners: atof(get(rec, idx, "home_corner")),
			AwayCorners: atof(get(rec, idx, "away_corner")),
			HomeShots:   atof(get(rec, idx, "home_shots")),
			AwayShots:   atof(get(rec, idx, "away_shots")),
			HomeAttacks: atof(get(rec, idx, "home_attack")),
			AwayAttacks: atof(get(rec, idx, "away_attack")),
			HTResult:    get(rec, idx, "ht_result"),
			ATResult:    get(rec, idx, "at_result"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func loadNovoCampeonato(path string) ([]Match, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexHeader(header)

	var matches []Match
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		m := Match{
			Source:      "novo_campeonato_brasileiro.csv",
			Competition: "Brasileirão Série A",
			Date:        parseDate(get(rec, idx, "Data")),
			Season:      atoi(get(rec, idx, "Ano")),
			Round:       get(rec, idx, "Rodada"),
			HomeTeam:    get(rec, idx, "Equipe_mandante"),
			AwayTeam:    get(rec, idx, "Equipe_visitante"),
			HomeState:   get(rec, idx, "Mandante_UF"),
			AwayState:   get(rec, idx, "Visitante_UF"),
			HomeGoals:   atoi(get(rec, idx, "Gols_mandante")),
			AwayGoals:   atoi(get(rec, idx, "Gols_visitante")),
			Arena:       get(rec, idx, "Arena"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func loadFifa(path string) ([]Player, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexHeader(header)

	var players []Player
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		p := Player{
			ID:            atoi(get(rec, idx, "ID")),
			Name:          get(rec, idx, "Name"),
			Age:           atoi(get(rec, idx, "Age")),
			Nationality:   get(rec, idx, "Nationality"),
			Overall:       atoi(get(rec, idx, "Overall")),
			Potential:     atoi(get(rec, idx, "Potential")),
			Club:          get(rec, idx, "Club"),
			Position:      get(rec, idx, "Position"),
			JerseyNumber:  get(rec, idx, "Jersey Number"),
			Height:        get(rec, idx, "Height"),
			Weight:        get(rec, idx, "Weight"),
			PreferredFoot: get(rec, idx, "Preferred Foot"),
			Value:         get(rec, idx, "Value"),
			Wage:          get(rec, idx, "Wage"),
		}
		if p.Name == "" {
			continue
		}
		players = append(players, p)
	}
	return players, nil
}
