package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"strings"
)

// newCSVReader wraps r in a csv.Reader configured to tolerate the quoting
// quirks seen across the source files, and transparently skips a leading
// UTF-8 byte-order mark if present (fifa_data.csv has one).
func newCSVReader(r io.Reader) *csv.Reader {
	br := bufio.NewReader(r)
	bom, err := br.Peek(3)
	if err == nil && bom[0] == 0xEF && bom[1] == 0xBB && bom[2] == 0xBF {
		br.Discard(3)
	}
	cr := csv.NewReader(br)
	cr.FieldsPerRecord = -1
	cr.LazyQuotes = true
	cr.TrimLeadingSpace = true
	return cr
}

// headerIndex builds a column-name -> index map from a CSV header row, so
// loaders can look up fields by name instead of brittle positional offsets.
func headerIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(strings.Trim(h, "\""))] = i
	}
	return idx
}

func field(row []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

type warnFunc func(format string, args ...any)

func readAllRows(r io.Reader, warn warnFunc, source string) (map[string]int, [][]string, error) {
	cr := newCSVReader(r)
	header, err := cr.Read()
	if err != nil {
		return nil, nil, fmt.Errorf("%s: reading header: %w", source, err)
	}
	idx := headerIndex(header)
	var rows [][]string
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			warn("%s: skipping malformed row: %v", source, err)
			continue
		}
		rows = append(rows, row)
	}
	return idx, rows, nil
}

// loadBrasileirao parses Brasileirao_Matches.csv (Serie A, 2012-2022).
func loadBrasileirao(r io.Reader, warn warnFunc) ([]Match, error) {
	const source = "Brasileirao_Matches.csv"
	idx, rows, err := readAllRows(r, warn, source)
	if err != nil {
		return nil, err
	}
	var out []Match
	for n, row := range rows {
		date, dateOK := parseDateFlexible(field(row, idx, "datetime"))
		season, seasonOK := parseIntLoose(field(row, idx, "season"))
		hg, hgOK := parseGoal(field(row, idx, "home_goal"))
		ag, agOK := parseGoal(field(row, idx, "away_goal"))
		home, away := field(row, idx, "home_team"), field(row, idx, "away_team")
		if !seasonOK || home == "" || away == "" {
			warn("%s: row %d: skipping, missing season/teams", source, n+2)
			continue
		}
		m := Match{
			Competition: "Brasileirão",
			Season:      season,
			Round:       field(row, idx, "round"),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeState:   field(row, idx, "home_team_state"),
			AwayState:   field(row, idx, "away_team_state"),
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasGoals:    hgOK && agOK,
			Source:      source,
		}
		if dateOK {
			m.Date = date
			m.DateStr = date.Format("2006-01-02")
		}
		out = append(out, m)
	}
	return out, nil
}

// loadCup parses Brazilian_Cup_Matches.csv (Copa do Brasil, 2012-2021).
func loadCup(r io.Reader, warn warnFunc) ([]Match, error) {
	const source = "Brazilian_Cup_Matches.csv"
	idx, rows, err := readAllRows(r, warn, source)
	if err != nil {
		return nil, err
	}
	var out []Match
	for n, row := range rows {
		date, dateOK := parseDateFlexible(field(row, idx, "datetime"))
		season, seasonOK := parseIntLoose(field(row, idx, "season"))
		hg, hgOK := parseGoal(field(row, idx, "home_goal"))
		ag, agOK := parseGoal(field(row, idx, "away_goal"))
		home, away := field(row, idx, "home_team"), field(row, idx, "away_team")
		if !seasonOK || home == "" || away == "" {
			warn("%s: row %d: skipping, missing season/teams", source, n+2)
			continue
		}
		m := Match{
			Competition: "Copa do Brasil",
			Season:      season,
			Round:       field(row, idx, "round"),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasGoals:    hgOK && agOK,
			Source:      source,
		}
		if dateOK {
			m.Date = date
			m.DateStr = date.Format("2006-01-02")
		}
		out = append(out, m)
	}
	return out, nil
}

// loadLibertadores parses Libertadores_Matches.csv (2013-2022). A handful of
// rows have season="NA"; those are skipped.
func loadLibertadores(r io.Reader, warn warnFunc) ([]Match, error) {
	const source = "Libertadores_Matches.csv"
	idx, rows, err := readAllRows(r, warn, source)
	if err != nil {
		return nil, err
	}
	var out []Match
	for n, row := range rows {
		date, dateOK := parseDateFlexible(field(row, idx, "datetime"))
		season, seasonOK := parseIntLoose(field(row, idx, "season"))
		hg, hgOK := parseGoal(field(row, idx, "home_goal"))
		ag, agOK := parseGoal(field(row, idx, "away_goal"))
		home, away := field(row, idx, "home_team"), field(row, idx, "away_team")
		if !seasonOK || home == "" || away == "" {
			warn("%s: row %d: skipping, missing/unparseable season or teams", source, n+2)
			continue
		}
		m := Match{
			Competition: "Copa Libertadores",
			Season:      season,
			Stage:       field(row, idx, "stage"),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasGoals:    hgOK && agOK,
			Source:      source,
		}
		if dateOK {
			m.Date = date
			m.DateStr = date.Format("2006-01-02")
		}
		out = append(out, m)
	}
	return out, nil
}

// loadBRFootball parses BR-Football-Dataset.csv, which spans several
// tournaments and carries extended per-match stats (corners/shots/attacks)
// not present elsewhere. Its competitions are tagged "(Extended Stats)" so
// they never silently merge with the primary standings-driving sources.
func loadBRFootball(r io.Reader, warn warnFunc) ([]Match, error) {
	const source = "BR-Football-Dataset.csv"
	idx, rows, err := readAllRows(r, warn, source)
	if err != nil {
		return nil, err
	}
	var out []Match
	for n, row := range rows {
		date, dateOK := combineDateTime(field(row, idx, "date"), field(row, idx, "time"))
		hg, hgOK := parseGoal(field(row, idx, "home_goal"))
		ag, agOK := parseGoal(field(row, idx, "away_goal"))
		home, away := field(row, idx, "home"), field(row, idx, "away")
		tournament := field(row, idx, "tournament")
		if !dateOK || home == "" || away == "" || tournament == "" {
			warn("%s: row %d: skipping, missing date/teams/tournament", source, n+2)
			continue
		}
		ext := &ExtendedStats{}
		if v, ok := parseFloatLoose(field(row, idx, "home_corner")); ok {
			ext.HomeCorners = v
		}
		if v, ok := parseFloatLoose(field(row, idx, "away_corner")); ok {
			ext.AwayCorners = v
		}
		if v, ok := parseFloatLoose(field(row, idx, "home_attack")); ok {
			ext.HomeAttacks = v
		}
		if v, ok := parseFloatLoose(field(row, idx, "away_attack")); ok {
			ext.AwayAttacks = v
		}
		if v, ok := parseFloatLoose(field(row, idx, "home_shots")); ok {
			ext.HomeShots = v
		}
		if v, ok := parseFloatLoose(field(row, idx, "away_shots")); ok {
			ext.AwayShots = v
		}
		m := Match{
			Competition: tournament + " (Extended Stats)",
			Season:      date.Year(),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasGoals:    hgOK && agOK,
			Date:        date,
			DateStr:     date.Format("2006-01-02"),
			Source:      source,
			Extended:    ext,
		}
		out = append(out, m)
	}
	return out, nil
}

// loadNovoCampeonato parses novo_campeonato_brasileiro.csv (Serie A,
// 2003-2019). Only seasons older than the earliest season in
// Brasileirao_Matches.csv are kept by the caller, to avoid double-counting
// matches present in both sources.
func loadNovoCampeonato(r io.Reader, warn warnFunc) ([]Match, error) {
	const source = "novo_campeonato_brasileiro.csv"
	idx, rows, err := readAllRows(r, warn, source)
	if err != nil {
		return nil, err
	}
	var out []Match
	for n, row := range rows {
		date, dateOK := parseDateFlexible(field(row, idx, "Data"))
		season, seasonOK := parseIntLoose(field(row, idx, "Ano"))
		hg, hgOK := parseGoal(field(row, idx, "Gols_mandante"))
		ag, agOK := parseGoal(field(row, idx, "Gols_visitante"))
		home, away := field(row, idx, "Equipe_mandante"), field(row, idx, "Equipe_visitante")
		if !seasonOK || home == "" || away == "" {
			warn("%s: row %d: skipping, missing season/teams", source, n+2)
			continue
		}
		m := Match{
			Competition: "Brasileirão",
			Season:      season,
			Round:       field(row, idx, "Rodada"),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeState:   field(row, idx, "Mandante_UF"),
			AwayState:   field(row, idx, "Visitante_UF"),
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasGoals:    hgOK && agOK,
			Arena:       field(row, idx, "Arena"),
			Source:      source,
		}
		if dateOK {
			m.Date = date
			m.DateStr = date.Format("2006-01-02")
		}
		out = append(out, m)
	}
	return out, nil
}

// loadFIFA parses fifa_data.csv into Player records.
func loadFIFA(r io.Reader, warn warnFunc) ([]Player, error) {
	const source = "fifa_data.csv"
	idx, rows, err := readAllRows(r, warn, source)
	if err != nil {
		return nil, err
	}
	var out []Player
	for n, row := range rows {
		name := field(row, idx, "Name")
		if name == "" {
			warn("%s: row %d: skipping, missing name", source, n+2)
			continue
		}
		id, _ := parseIntLoose(field(row, idx, "ID"))
		age, _ := parseIntLoose(field(row, idx, "Age"))
		overall, _ := parseIntLoose(field(row, idx, "Overall"))
		potential, _ := parseIntLoose(field(row, idx, "Potential"))
		p := Player{
			ID:           id,
			Name:         name,
			Age:          age,
			Nationality:  field(row, idx, "Nationality"),
			Overall:      overall,
			Potential:    potential,
			Club:         field(row, idx, "Club"),
			Position:     field(row, idx, "Position"),
			JerseyNumber: field(row, idx, "Jersey Number"),
			Height:       field(row, idx, "Height"),
			Weight:       field(row, idx, "Weight"),
			Value:        field(row, idx, "Value"),
			Wage:         field(row, idx, "Wage"),
		}
		out = append(out, p)
	}
	return out, nil
}
