// Package main contains a dependency-free MCP server for the Brazilian soccer
// datasets that ship with this repository.
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

// Match is the common representation used for records from all five match CSVs.
type Match struct {
	Date        time.Time `json:"date"`
	Home        string    `json:"home_team"`
	Away        string    `json:"away_team"`
	HomeGoals   int       `json:"home_goals"`
	AwayGoals   int       `json:"away_goals"`
	Competition string    `json:"competition"`
	Season      int       `json:"season"`
	Round       string    `json:"round,omitempty"`
	Stage       string    `json:"stage,omitempty"`
	Stadium     string    `json:"stadium,omitempty"`
	Source      string    `json:"source"`
}

type Player struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Age         int    `json:"age"`
	Nationality string `json:"nationality"`
	Overall     int    `json:"overall"`
	Potential   int    `json:"potential"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	Jersey      string `json:"jersey_number"`
}

// Repository keeps parsed data in memory. Loading once makes queries fast and
// avoids any database or network dependency for the demo server.
type Repository struct {
	Matches []Match
	Players []Player
}

func NewRepository(dataDir string) (*Repository, error) {
	r := &Repository{}
	var errs []error
	loaders := []func(string, *Repository) error{loadBrasileirao, loadCup, loadLibertadores, loadExtended, loadHistorical, loadPlayers}
	files := []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv"}
	for i, load := range loaders {
		if err := load(filepath.Join(dataDir, files[i]), r); err != nil {
			errs = append(errs, fmt.Errorf("%s: %w", files[i], err))
		}
	}
	if len(errs) > 0 {
		return nil, errors.Join(errs...)
	}
	return r, nil
}

func readRows(file string, fn func(map[string]string) error) error {
	f, err := os.Open(file)
	if err != nil {
		return err
	}
	defer f.Close()
	cr := csv.NewReader(f)
	cr.FieldsPerRecord = -1
	cr.TrimLeadingSpace = true
	head, err := cr.Read()
	if err != nil {
		return err
	}
	for i := range head {
		head[i] = strings.TrimPrefix(strings.TrimSpace(head[i]), "\ufeff")
	}
	for {
		rec, err := cr.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return err
		}
		row := make(map[string]string, len(head))
		for i, key := range head {
			if i < len(rec) {
				row[key] = strings.TrimSpace(rec[i])
			}
		}
		if err := fn(row); err != nil {
			return err
		}
	}
	return nil
}

func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", time.RFC3339} {
		if t, err := time.Parse(layout, s); err == nil {
			return t
		}
	}
	return time.Time{}
}
func integer(s string) int { n, _ := strconv.ParseFloat(strings.TrimSpace(s), 64); return int(n) }
func dateSeason(d time.Time, supplied string) int {
	if s := integer(supplied); s != 0 {
		return s
	}
	if !d.IsZero() {
		return d.Year()
	}
	return 0
}

func appendMatch(r *Repository, row map[string]string, comp, source, dateCol, homeCol, awayCol, hgCol, agCol, seasonCol, roundCol, stageCol, stadiumCol string) error {
	d := parseDate(row[dateCol])
	r.Matches = append(r.Matches, Match{Date: d, Home: row[homeCol], Away: row[awayCol], HomeGoals: integer(row[hgCol]), AwayGoals: integer(row[agCol]), Competition: comp, Season: dateSeason(d, row[seasonCol]), Round: row[roundCol], Stage: row[stageCol], Stadium: row[stadiumCol], Source: source})
	return nil
}
func loadBrasileirao(p string, r *Repository) error {
	return readRows(p, func(x map[string]string) error {
		return appendMatch(r, x, "Brasileirão", "Brasileirao_Matches.csv", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round", "", "")
	})
}
func loadCup(p string, r *Repository) error {
	return readRows(p, func(x map[string]string) error {
		return appendMatch(r, x, "Copa do Brasil", "Brazilian_Cup_Matches.csv", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round", "", "")
	})
}
func loadLibertadores(p string, r *Repository) error {
	return readRows(p, func(x map[string]string) error {
		return appendMatch(r, x, "Copa Libertadores", "Libertadores_Matches.csv", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "", "stage", "")
	})
}
func loadExtended(p string, r *Repository) error {
	return readRows(p, func(x map[string]string) error {
		return appendMatch(r, x, x["tournament"], "BR-Football-Dataset.csv", "date", "home", "away", "home_goal", "away_goal", "", "", "", "")
	})
}
func loadHistorical(p string, r *Repository) error {
	return readRows(p, func(x map[string]string) error {
		return appendMatch(r, x, "Brasileirão", "novo_campeonato_brasileiro.csv", "Data", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Ano", "Rodada", "", "Arena")
	})
}
func loadPlayers(p string, r *Repository) error {
	return readRows(p, func(x map[string]string) error {
		r.Players = append(r.Players, Player{ID: x["ID"], Name: x["Name"], Age: integer(x["Age"]), Nationality: x["Nationality"], Overall: integer(x["Overall"]), Potential: integer(x["Potential"]), Club: x["Club"], Position: x["Position"], Jersey: x["Jersey Number"]})
		return nil
	})
}
