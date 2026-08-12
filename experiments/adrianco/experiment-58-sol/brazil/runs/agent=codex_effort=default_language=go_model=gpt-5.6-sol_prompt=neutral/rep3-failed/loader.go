package main

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type csvRows struct {
	header map[string]int
	rows   [][]string
}

func LoadDatabase(dataDir string) (*Database, error) {
	db := &Database{}
	loaders := []struct {
		name string
		fn   func(string) ([]Match, error)
	}{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadBrazilianCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadExtended},
		{"novo_campeonato_brasileiro.csv", loadHistorical},
	}
	var errs []error
	for _, loader := range loaders {
		matches, err := loader.fn(filepath.Join(dataDir, loader.name))
		if err != nil {
			errs = append(errs, fmt.Errorf("%s: %w", loader.name, err))
			continue
		}
		db.Matches = append(db.Matches, matches...)
	}
	players, err := loadPlayers(filepath.Join(dataDir, "fifa_data.csv"))
	if err != nil {
		errs = append(errs, fmt.Errorf("fifa_data.csv: %w", err))
	} else {
		db.Players = players
	}
	if len(errs) > 0 {
		return nil, errors.Join(errs...)
	}
	db.sort()
	return db, nil
}

func readCSV(path string) (csvRows, error) {
	f, err := os.Open(path)
	if err != nil {
		return csvRows{}, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	header, err := r.Read()
	if err != nil {
		return csvRows{}, err
	}
	indices := make(map[string]int, len(header))
	for i, h := range header {
		indices[fold(h)] = i
	}
	var rows [][]string
	for {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return csvRows{}, err
		}
		rows = append(rows, row)
	}
	return csvRows{header: indices, rows: rows}, nil
}

func (c csvRows) get(row []string, name string) string {
	i, ok := c.header[fold(name)]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func parseInt(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "nan") {
		return 0, false
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i, true
	}
	f, err := strconv.ParseFloat(s, 64)
	return int(f), err == nil
}

func intPointer(s string) *int {
	i, ok := parseInt(s)
	if !ok {
		return nil
	}
	return &i
}

var dateLayouts = []string{
	"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "1/2/2006",
	"02/01/06", time.RFC3339,
}

func parseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("unsupported date %q", s)
}

func baseMatch(c csvRows, row []string, competition, source, dateKey, homeKey, awayKey, hgKey, agKey, seasonKey string) (Match, bool) {
	hg, okH := parseInt(c.get(row, hgKey))
	ag, okA := parseInt(c.get(row, agKey))
	date, err := parseDate(c.get(row, dateKey))
	if !okH || !okA || err != nil {
		return Match{}, false
	}
	season, _ := parseInt(c.get(row, seasonKey))
	if season == 0 {
		season = date.Year()
	}
	// Retain source names internally: state suffixes disambiguate clubs such as
	// Atletico-MG and Atletico-PR. Presentation removes or expands them later.
	home, away := strings.TrimSpace(c.get(row, homeKey)), strings.TrimSpace(c.get(row, awayKey))
	if home == "" || away == "" {
		return Match{}, false
	}
	return Match{Date: date, Competition: competition, Season: season, HomeTeam: home, AwayTeam: away, HomeGoals: hg, AwayGoals: ag, Source: source}, true
}

func loadBrasileirao(path string) ([]Match, error) {
	c, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	result := make([]Match, 0, len(c.rows))
	for _, row := range c.rows {
		m, ok := baseMatch(c, row, "Brasileirão Série A", filepath.Base(path), "datetime", "home_team", "away_team", "home_goal", "away_goal", "season")
		if !ok {
			continue
		}
		m.Round, m.HomeState, m.AwayState = c.get(row, "round"), c.get(row, "home_team_state"), c.get(row, "away_team_state")
		result = append(result, m)
	}
	return result, nil
}

func loadBrazilianCup(path string) ([]Match, error) {
	c, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	result := make([]Match, 0, len(c.rows))
	for _, row := range c.rows {
		m, ok := baseMatch(c, row, "Copa do Brasil", filepath.Base(path), "datetime", "home_team", "away_team", "home_goal", "away_goal", "season")
		if !ok {
			continue
		}
		m.Round = c.get(row, "round")
		result = append(result, m)
	}
	return result, nil
}

func loadLibertadores(path string) ([]Match, error) {
	c, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	result := make([]Match, 0, len(c.rows))
	for _, row := range c.rows {
		m, ok := baseMatch(c, row, "Copa Libertadores", filepath.Base(path), "datetime", "home_team", "away_team", "home_goal", "away_goal", "season")
		if !ok {
			continue
		}
		m.Stage = c.get(row, "stage")
		result = append(result, m)
	}
	return result, nil
}

func loadExtended(path string) ([]Match, error) {
	c, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	result := make([]Match, 0, len(c.rows))
	for _, row := range c.rows {
		competition := titleWords(c.get(row, "tournament"))
		m, ok := baseMatch(c, row, competition, filepath.Base(path), "date", "home", "away", "home_goal", "away_goal", "")
		if !ok {
			continue
		}
		m.HomeCorners, m.AwayCorners = intPointer(c.get(row, "home_corner")), intPointer(c.get(row, "away_corner"))
		m.HomeAttacks, m.AwayAttacks = intPointer(c.get(row, "home_attack")), intPointer(c.get(row, "away_attack"))
		m.HomeShots, m.AwayShots = intPointer(c.get(row, "home_shots")), intPointer(c.get(row, "away_shots"))
		result = append(result, m)
	}
	return result, nil
}

func loadHistorical(path string) ([]Match, error) {
	c, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	result := make([]Match, 0, len(c.rows))
	for _, row := range c.rows {
		m, ok := baseMatch(c, row, "Brasileirão Série A", filepath.Base(path), "Data", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Ano")
		if !ok {
			continue
		}
		m.Round, m.HomeState, m.AwayState = c.get(row, "Rodada"), c.get(row, "Mandante_UF"), c.get(row, "Visitante_UF")
		m.Venue = c.get(row, "Arena")
		result = append(result, m)
	}
	return result, nil
}

var playerAttributes = []string{"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Stamina", "Strength", "LongShots", "Vision", "Penalties", "Composure", "StandingTackle", "GKDiving", "GKHandling", "GKReflexes"}

func loadPlayers(path string) ([]Player, error) {
	c, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	result := make([]Player, 0, len(c.rows))
	for _, row := range c.rows {
		id, ok := parseInt(c.get(row, "ID"))
		if !ok || c.get(row, "Name") == "" {
			continue
		}
		age, _ := parseInt(c.get(row, "Age"))
		overall, _ := parseInt(c.get(row, "Overall"))
		potential, _ := parseInt(c.get(row, "Potential"))
		p := Player{ID: id, Name: c.get(row, "Name"), Age: age, Nationality: c.get(row, "Nationality"), Overall: overall, Potential: potential, Club: c.get(row, "Club"), Position: c.get(row, "Position"), Jersey: c.get(row, "Jersey Number"), Height: c.get(row, "Height"), Weight: c.get(row, "Weight"), Attributes: map[string]int{}}
		for _, name := range playerAttributes {
			if value, ok := parseInt(c.get(row, name)); ok {
				p.Attributes[name] = value
			}
		}
		result = append(result, p)
	}
	return result, nil
}
