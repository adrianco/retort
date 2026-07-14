package main

import (
	"encoding/csv"
	"io"
	"log"
	"os"
	"strconv"
	"strings"
	"time"
)

// ParseDate tries multiple date formats and returns a parsed time.Time.
func ParseDate(s string) (time.Time, error) {
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02",
		"02/01/2006",
	}
	s = strings.TrimSpace(s)
	for _, fmt := range formats {
		t, err := time.Parse(fmt, s)
		if err == nil {
			return t, nil
		}
	}
	return time.Time{}, nil
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	// Handle float strings like "1.0"
	if strings.Contains(s, ".") {
		f, err := strconv.ParseFloat(s, 64)
		if err != nil {
			return 0
		}
		return int(f)
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}

func parseFloat(s string) float64 {
	s = strings.TrimSpace(s)
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	return f
}

// indexMap builds a map from header name -> column index (0-based).
func indexMap(headers []string) map[string]int {
	m := make(map[string]int, len(headers))
	for i, h := range headers {
		// Strip BOM from first header if present
		h = strings.TrimPrefix(h, "\xef\xbb\xbf")
		h = strings.TrimSpace(h)
		m[h] = i
	}
	return m
}

// LoadBrasileirao loads Brasileirao_Matches.csv
// Headers: "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
func LoadBrasileirao(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexMap(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("LoadBrasileirao: skipping row due to error: %v", err)
			continue
		}
		if len(row) <= idx["season"] {
			continue
		}
		dt, _ := ParseDate(row[idx["datetime"]])
		m := Match{
			DateTime:    dt,
			HomeTeam:    strings.TrimSpace(row[idx["home_team"]]),
			AwayTeam:    strings.TrimSpace(row[idx["away_team"]]),
			HomeGoals:   parseInt(row[idx["home_goal"]]),
			AwayGoals:   parseInt(row[idx["away_goal"]]),
			Season:      parseInt(row[idx["season"]]),
			Round:       strings.TrimSpace(row[idx["round"]]),
			Competition: CompBrasileirao,
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// LoadCopa loads Brazilian_Cup_Matches.csv
// Headers: "round","datetime","home_team","away_team","home_goal","away_goal","season"
func LoadCopa(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexMap(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("LoadCopa: skipping row due to error: %v", err)
			continue
		}
		if len(row) <= idx["season"] {
			continue
		}
		dt, _ := ParseDate(row[idx["datetime"]])
		m := Match{
			DateTime:    dt,
			HomeTeam:    strings.TrimSpace(row[idx["home_team"]]),
			AwayTeam:    strings.TrimSpace(row[idx["away_team"]]),
			HomeGoals:   parseInt(row[idx["home_goal"]]),
			AwayGoals:   parseInt(row[idx["away_goal"]]),
			Season:      parseInt(row[idx["season"]]),
			Round:       strings.TrimSpace(row[idx["round"]]),
			Competition: CompCopa,
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// LoadLibertadores loads Libertadores_Matches.csv
// Headers: "datetime","home_team","away_team","home_goal","away_goal","season","stage"
func LoadLibertadores(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexMap(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("LoadLibertadores: skipping row due to error: %v", err)
			continue
		}
		if len(row) <= idx["season"] {
			continue
		}
		dt, _ := ParseDate(row[idx["datetime"]])
		m := Match{
			DateTime:    dt,
			HomeTeam:    strings.TrimSpace(row[idx["home_team"]]),
			AwayTeam:    strings.TrimSpace(row[idx["away_team"]]),
			HomeGoals:   parseInt(row[idx["home_goal"]]),
			AwayGoals:   parseInt(row[idx["away_goal"]]),
			Season:      parseInt(row[idx["season"]]),
			Stage:       strings.TrimSpace(row[idx["stage"]]),
			Competition: CompLibertadores,
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// LoadBRFootball loads BR-Football-Dataset.csv
// Headers: tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,...
func LoadBRFootball(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexMap(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("LoadBRFootball: skipping row due to error: %v", err)
			continue
		}
		dateCol, ok := idx["date"]
		if !ok || len(row) <= dateCol {
			continue
		}
		dt, _ := ParseDate(row[idx["date"]])
		m := Match{
			DateTime:    dt,
			HomeTeam:    strings.TrimSpace(row[idx["home"]]),
			AwayTeam:    strings.TrimSpace(row[idx["away"]]),
			HomeGoals:   parseInt(row[idx["home_goal"]]),
			AwayGoals:   parseInt(row[idx["away_goal"]]),
			HomeCorner:  parseFloat(row[idx["home_corner"]]),
			AwayCorner:  parseFloat(row[idx["away_corner"]]),
			HomeAttack:  parseFloat(row[idx["home_attack"]]),
			AwayAttack:  parseFloat(row[idx["away_attack"]]),
			HomeShots:   parseFloat(row[idx["home_shots"]]),
			AwayShots:   parseFloat(row[idx["away_shots"]]),
			Tournament:  strings.TrimSpace(row[idx["tournament"]]),
			Competition: CompBRFootball,
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// LoadHistorico loads novo_campeonato_brasileiro.csv
// Headers: ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
func LoadHistorico(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexMap(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("LoadHistorico: skipping row due to error: %v", err)
			continue
		}
		if len(row) <= idx["Ano"] {
			continue
		}
		dt, _ := ParseDate(row[idx["Data"]])
		m := Match{
			DateTime:    dt,
			HomeTeam:    strings.TrimSpace(row[idx["Equipe_mandante"]]),
			AwayTeam:    strings.TrimSpace(row[idx["Equipe_visitante"]]),
			HomeGoals:   parseInt(row[idx["Gols_mandante"]]),
			AwayGoals:   parseInt(row[idx["Gols_visitante"]]),
			Season:      parseInt(row[idx["Ano"]]),
			Round:       strings.TrimSpace(row[idx["Rodada"]]),
			Competition: CompHistorico,
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// LoadFIFA loads fifa_data.csv (has BOM)
// Headers (0-indexed): 0=BOM/"", 1=ID, 2=Name, 3=Age, 4=Photo, 5=Nationality, 6=Flag,
//
//	7=Overall, 8=Potential, 9=Club, 10=Club Logo, 11=Value, 12=Wage, ...
//	21=Position, 22=Jersey Number, 26=Height, 27=Weight
func LoadFIFA(path string) ([]Player, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1 // variable fields

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	// Strip BOM from first header
	if len(headers) > 0 {
		headers[0] = strings.TrimPrefix(headers[0], "\xef\xbb\xbf")
	}
	idx := indexMap(headers)

	// Build helper to safely get field
	get := func(row []string, key string) string {
		i, ok := idx[key]
		if !ok || i >= len(row) {
			return ""
		}
		return strings.TrimSpace(row[i])
	}

	var players []Player
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("LoadFIFA: skipping row due to error: %v", err)
			continue
		}
		name := get(row, "Name")
		if name == "" {
			continue
		}
		p := Player{
			ID:           parseInt(get(row, "ID")),
			Name:         name,
			Age:          parseInt(get(row, "Age")),
			Nationality:  get(row, "Nationality"),
			Overall:      parseInt(get(row, "Overall")),
			Potential:    parseInt(get(row, "Potential")),
			Club:         get(row, "Club"),
			Position:     get(row, "Position"),
			JerseyNumber: parseInt(get(row, "Jersey Number")),
			Height:       get(row, "Height"),
			Weight:       get(row, "Weight"),
		}
		players = append(players, p)
	}
	return players, nil
}
