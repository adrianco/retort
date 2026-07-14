// Package main — Brazilian Soccer MCP Server.
//
// loader.go: CSV ingestion. Each of the five match files and the FIFA player
// file has its own column layout, naming convention and date format, so each
// gets a dedicated loader that maps raw rows into the unified Match/Player
// model. Rows with unparseable scores are kept but flagged HasScore=false;
// goals stored as floats ("1.0") or quoted strings ("2") are both handled.
// The FIFA file carries a UTF-8 BOM which is stripped from the first header.
package main

import (
	"encoding/csv"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// LoadDataset reads every provided CSV from dir into a single Dataset.
func LoadDataset(dir string) (*Dataset, error) {
	ds := &Dataset{}

	type matchFile struct {
		name string
		fn   func(rows [][]string) []Match
	}
	matchFiles := []matchFile{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"novo_campeonato_brasileiro.csv", loadHistorico},
		{"BR-Football-Dataset.csv", loadBRFootball},
	}
	for _, mf := range matchFiles {
		rows, err := readCSV(filepath.Join(dir, mf.name))
		if err != nil {
			return nil, err
		}
		ds.Matches = append(ds.Matches, mf.fn(rows)...)
	}

	playerRows, err := readCSV(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, err
	}
	ds.Players = loadPlayers(playerRows)

	return ds, nil
}

// readCSV reads a whole CSV file into rows (including the header row),
// tolerating ragged lines and stripping a leading UTF-8 BOM.
func readCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // allow variable column counts
	r.LazyQuotes = true

	var rows [][]string
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		rows = append(rows, rec)
	}
	if len(rows) > 0 && len(rows[0]) > 0 {
		rows[0][0] = strings.TrimPrefix(rows[0][0], "\uFEFF")
	}
	return rows, nil
}

// atoiGoals parses a goal count that may be an int ("2"), a float ("1.0"), or
// quoted/whitespace-padded. Returns the integer and whether it was valid.
func atoiGoals(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if n, err := strconv.Atoi(s); err == nil {
		return n, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

// atoiSafe parses an int, returning 0 on failure.
func atoiSafe(s string) int {
	n, _ := strconv.Atoi(strings.TrimSpace(s))
	return n
}

// makeMatch fills the team display names, normalized keys and score fields.
func makeMatch(source, comp, home, away, hg, ag string) Match {
	m := Match{
		Source:      source,
		Competition: comp,
		HomeTeam:    cleanName(home),
		AwayTeam:    cleanName(away),
		HomeTeamKey: NormalizeTeam(home),
		AwayTeamKey: NormalizeTeam(away),
	}
	h, okh := atoiGoals(hg)
	a, oka := atoiGoals(ag)
	if okh && oka {
		m.HomeGoals, m.AwayGoals, m.HasScore = h, a, true
	}
	return m
}

// cleanName trims surrounding whitespace from a display team name.
func cleanName(s string) string {
	return strings.TrimSpace(s)
}

// setDate parses and assigns a match date.
func (m *Match) setDate(s string) {
	if t, ok := ParseDate(s); ok {
		m.Date, m.HasDate = t, true
	}
}

// loadBrasileirao: datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
func loadBrasileirao(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		if len(r) < 9 {
			continue
		}
		m := makeMatch("Brasileirao", "Brasileirão", r[1], r[3], r[5], r[6])
		m.setDate(r[0])
		m.Season = atoiSafe(r[7])
		m.Round = strings.TrimSpace(r[8])
		out = append(out, m)
	}
	return out
}

// loadCup: round,datetime,home_team,away_team,home_goal,away_goal,season
func loadCup(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		if len(r) < 7 {
			continue
		}
		m := makeMatch("Cup", "Copa do Brasil", r[2], r[3], r[4], r[5])
		m.setDate(r[1])
		m.Round = strings.TrimSpace(r[0])
		m.Season = atoiSafe(r[6])
		out = append(out, m)
	}
	return out
}

// loadLibertadores: datetime,home_team,away_team,home_goal,away_goal,season,stage
func loadLibertadores(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		if len(r) < 7 {
			continue
		}
		m := makeMatch("Libertadores", "Copa Libertadores", r[1], r[2], r[3], r[4])
		m.setDate(r[0])
		m.Season = atoiSafe(r[5])
		m.Stage = strings.TrimSpace(r[6])
		out = append(out, m)
	}
	return out
}

// loadHistorico: ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
func loadHistorico(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		if len(r) < 12 {
			continue
		}
		m := makeMatch("Historico", "Brasileirão (histórico)", r[4], r[5], r[6], r[7])
		m.setDate(r[1])
		m.Season = atoiSafe(r[2])
		m.Round = strings.TrimSpace(r[3])
		m.Arena = strings.TrimSpace(r[11])
		out = append(out, m)
	}
	return out
}

// loadBRFootball: tournament,home,home_goal,away_goal,away,...,date,...
func loadBRFootball(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		if len(r) < 13 {
			continue
		}
		comp := strings.TrimSpace(r[0])
		m := makeMatch("BR-Football", comp, r[1], r[4], r[2], r[3])
		m.setDate(r[12])
		if m.HasDate {
			m.Season = m.Date.Year()
		}
		out = append(out, m)
	}
	return out
}

// loadPlayers parses the FIFA player database by header name so column-order
// changes don't break parsing.
func loadPlayers(rows [][]string) []Player {
	if len(rows) < 2 {
		return nil
	}
	idx := map[string]int{}
	for i, h := range rows[0] {
		idx[strings.TrimSpace(h)] = i
	}
	get := func(r []string, col string) string {
		if i, ok := idx[col]; ok && i < len(r) {
			return strings.TrimSpace(r[i])
		}
		return ""
	}

	var out []Player
	for _, r := range rows[1:] {
		name := get(r, "Name")
		if name == "" {
			continue
		}
		out = append(out, Player{
			ID:           atoiSafe(get(r, "ID")),
			Name:         name,
			Age:          atoiSafe(get(r, "Age")),
			Nationality:  get(r, "Nationality"),
			Overall:      atoiSafe(get(r, "Overall")),
			Potential:    atoiSafe(get(r, "Potential")),
			Club:         get(r, "Club"),
			Position:     get(r, "Position"),
			JerseyNumber: get(r, "Jersey Number"),
			Height:       get(r, "Height"),
			Weight:       get(r, "Weight"),
		})
	}
	return out
}
