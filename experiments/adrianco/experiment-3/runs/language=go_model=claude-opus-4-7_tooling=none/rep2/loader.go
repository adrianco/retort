// loader.go reads the six provided CSV datasets into the in-memory DataStore,
// handling the differing column layouts, date formats and encodings.
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

// dateLayouts are tried in order when parsing the various date columns.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006 15:04:05",
}

// parseDate attempts to interpret s as a date using the known layouts.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// parseGoal parses a score cell that may be an int ("2") or a float ("2.0").
func parseGoal(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

// parseInt is a lenient integer parser that tolerates floats and blanks.
func parseInt(s string) int {
	v, _ := parseGoal(s)
	return v
}

// readCSV opens path and returns a header->index map plus all data rows.
func readCSV(path string) (map[string]int, [][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // tolerate ragged rows
	r.LazyQuotes = true
	r.ReuseRecord = false

	rows, err := r.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	if len(rows) == 0 {
		return nil, nil, fmt.Errorf("%s: empty file", path)
	}

	const bom = "\ufeff"
	header := make(map[string]int, len(rows[0]))
	for i, name := range rows[0] {
		name = strings.TrimPrefix(name, bom) // strip UTF-8 BOM
		header[strings.TrimSpace(name)] = i
	}
	return header, rows[1:], nil
}

// cell safely fetches a trimmed cell value by header name.
func cell(header map[string]int, row []string, name string) string {
	i, ok := header[name]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// newMatch builds a Match, deriving normalized keys and season from the date
// when no explicit season is supplied.
func newMatch(competition, source string, date time.Time, hasDate bool, season int,
	home, away string, hg, ag int, hasScore bool) Match {
	if season == 0 && hasDate {
		season = date.Year()
	}
	return Match{
		Competition: competition,
		Source:      source,
		Date:        date,
		HasDate:     hasDate,
		Season:      season,
		HomeTeam:    home,
		AwayTeam:    away,
		HomeKey:     normalizeTeamKey(home),
		AwayKey:     normalizeTeamKey(away),
		HomeGoal:    hg,
		AwayGoal:    ag,
		HasScore:    hasScore,
	}
}

func loadBrasileirao(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	out := make([]Match, 0, len(rows))
	src := filepath.Base(path)
	for _, row := range rows {
		date, hasDate := parseDate(cell(header, row, "datetime"))
		hg, ok1 := parseGoal(cell(header, row, "home_goal"))
		ag, ok2 := parseGoal(cell(header, row, "away_goal"))
		m := newMatch("Brasileirão Série A", src, date, hasDate,
			parseInt(cell(header, row, "season")),
			cell(header, row, "home_team"), cell(header, row, "away_team"),
			hg, ag, ok1 && ok2)
		m.Round = cell(header, row, "round")
		out = append(out, m)
	}
	return out, nil
}

func loadCup(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	out := make([]Match, 0, len(rows))
	src := filepath.Base(path)
	for _, row := range rows {
		date, hasDate := parseDate(cell(header, row, "datetime"))
		hg, ok1 := parseGoal(cell(header, row, "home_goal"))
		ag, ok2 := parseGoal(cell(header, row, "away_goal"))
		m := newMatch("Copa do Brasil", src, date, hasDate,
			parseInt(cell(header, row, "season")),
			cell(header, row, "home_team"), cell(header, row, "away_team"),
			hg, ag, ok1 && ok2)
		m.Round = cell(header, row, "round")
		m.Stage = cell(header, row, "round")
		out = append(out, m)
	}
	return out, nil
}

func loadLibertadores(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	out := make([]Match, 0, len(rows))
	src := filepath.Base(path)
	for _, row := range rows {
		date, hasDate := parseDate(cell(header, row, "datetime"))
		hg, ok1 := parseGoal(cell(header, row, "home_goal"))
		ag, ok2 := parseGoal(cell(header, row, "away_goal"))
		m := newMatch("Copa Libertadores", src, date, hasDate,
			parseInt(cell(header, row, "season")),
			cell(header, row, "home_team"), cell(header, row, "away_team"),
			hg, ag, ok1 && ok2)
		m.Stage = cell(header, row, "stage")
		out = append(out, m)
	}
	return out, nil
}

// brFootballCompetition maps the BR-Football "tournament" column onto the
// unified competition names so cross-dataset queries line up.
func brFootballCompetition(tournament string) string {
	switch strings.ToLower(strings.TrimSpace(tournament)) {
	case "serie a":
		return "Brasileirão Série A"
	case "serie b":
		return "Brasileirão Série B"
	case "serie c":
		return "Brasileirão Série C"
	case "copa do brasil":
		return "Copa do Brasil"
	default:
		return tournament
	}
}

func loadBRFootball(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	out := make([]Match, 0, len(rows))
	src := filepath.Base(path)
	for _, row := range rows {
		date, hasDate := parseDate(cell(header, row, "date"))
		hg, ok1 := parseGoal(cell(header, row, "home_goal"))
		ag, ok2 := parseGoal(cell(header, row, "away_goal"))
		m := newMatch(brFootballCompetition(cell(header, row, "tournament")), src,
			date, hasDate, 0,
			cell(header, row, "home"), cell(header, row, "away"),
			hg, ag, ok1 && ok2)
		m.HomeShots = parseInt(cell(header, row, "home_shots"))
		m.AwayShots = parseInt(cell(header, row, "away_shots"))
		m.HomeCorners = parseInt(cell(header, row, "home_corner"))
		m.AwayCorners = parseInt(cell(header, row, "away_corner"))
		m.HasStats = true
		out = append(out, m)
	}
	return out, nil
}

func loadNovo(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	out := make([]Match, 0, len(rows))
	src := filepath.Base(path)
	for _, row := range rows {
		date, hasDate := parseDate(cell(header, row, "Data"))
		hg, ok1 := parseGoal(cell(header, row, "Gols_mandante"))
		ag, ok2 := parseGoal(cell(header, row, "Gols_visitante"))
		m := newMatch("Brasileirão Série A", src, date, hasDate,
			parseInt(cell(header, row, "Ano")),
			cell(header, row, "Equipe_mandante"), cell(header, row, "Equipe_visitante"),
			hg, ag, ok1 && ok2)
		m.Round = cell(header, row, "Rodada")
		m.Arena = cell(header, row, "Arena")
		out = append(out, m)
	}
	return out, nil
}

func loadPlayers(path string) ([]Player, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	out := make([]Player, 0, len(rows))
	for _, row := range rows {
		club := cell(header, row, "Club")
		p := Player{
			ID:            parseInt(cell(header, row, "ID")),
			Name:          cell(header, row, "Name"),
			Age:           parseInt(cell(header, row, "Age")),
			Nationality:   cell(header, row, "Nationality"),
			Overall:       parseInt(cell(header, row, "Overall")),
			Potential:     parseInt(cell(header, row, "Potential")),
			Club:          club,
			ClubKey:       normalizeTeamKey(club),
			Position:      cell(header, row, "Position"),
			JerseyNumber:  cell(header, row, "Jersey Number"),
			Height:        cell(header, row, "Height"),
			Weight:        cell(header, row, "Weight"),
			Value:         cell(header, row, "Value"),
			Wage:          cell(header, row, "Wage"),
			PreferredFoot: cell(header, row, "Preferred Foot"),
		}
		if p.Name == "" {
			continue
		}
		out = append(out, p)
	}
	return out, nil
}

// keepMatch decides whether a match survives de-duplication. Several datasets
// cover the same competition and seasons but with inconsistent team naming, so
// rather than fuzzily matching names we designate a single authoritative
// source per (competition, season) and discard the rest. This guarantees no
// double-counting in standings and aggregate statistics.
func keepMatch(m Match) bool {
	switch m.Competition {
	case "Brasileirão Série A":
		// novo_campeonato owns 2003-2019; Brasileirao_Matches owns 2020-2022.
		switch m.Source {
		case "novo_campeonato_brasileiro.csv":
			return m.Season <= 2019
		case "Brasileirao_Matches.csv":
			return m.Season >= 2020
		default: // BR-Football "Serie A" is redundant with the above.
			return false
		}
	case "Copa do Brasil":
		// Brazilian_Cup owns 2012-2021; BR-Football extends 2022 onward.
		switch m.Source {
		case "Brazilian_Cup_Matches.csv":
			return m.Season <= 2021
		default: // BR-Football "Copa do Brasil"
			return m.Season >= 2022
		}
	default:
		// Série B, Série C (BR-Football only) and Libertadores have one source.
		return true
	}
}

// selectAuthoritative removes cross-dataset duplicate fixtures by keeping only
// the authoritative source for each competition and season (see keepMatch).
func selectAuthoritative(matches []Match) []Match {
	out := make([]Match, 0, len(matches))
	for _, m := range matches {
		if keepMatch(m) {
			out = append(out, m)
		}
	}
	return out
}

// matchFile pairs a CSV filename with its loader function.
type matchFile struct {
	name   string
	loader func(string) ([]Match, error)
}

// LoadAll reads every dataset under dir and returns a populated DataStore.
func LoadAll(dir string) (*DataStore, error) {
	store := &DataStore{}

	files := []matchFile{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadBRFootball},
		{"novo_campeonato_brasileiro.csv", loadNovo},
	}
	for _, mf := range files {
		path := filepath.Join(dir, mf.name)
		matches, err := mf.loader(path)
		if err != nil {
			return nil, fmt.Errorf("loading %s: %w", mf.name, err)
		}
		store.Matches = append(store.Matches, matches...)
	}

	store.Matches = selectAuthoritative(store.Matches)

	players, err := loadPlayers(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, fmt.Errorf("loading fifa_data.csv: %w", err)
	}
	store.Players = players

	return store, nil
}
