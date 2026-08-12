package main

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Match struct {
	Competition string    `json:"competition"`
	Date        time.Time `json:"date"`
	Round       string    `json:"round,omitempty"`
	Stage       string    `json:"stage,omitempty"`
	Home        string    `json:"home_team"`
	Away        string    `json:"away_team"`
	HomeGoals   int       `json:"home_goals"`
	AwayGoals   int       `json:"away_goals"`
	Season      int       `json:"season"`
	Venue       string    `json:"venue,omitempty"`
}

type Player struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	Age         int    `json:"age"`
	Overall     int    `json:"overall"`
	Potential   int    `json:"potential"`
}

type Store struct {
	Matches []Match
	Players []Player
}

func LoadStore(dir string) (*Store, error) {
	s := &Store{}
	files := []struct {
		name, competition    string
		historical, extended bool
	}{
		{"Brasileirao_Matches.csv", "Brasileirão", false, false},
		{"Brazilian_Cup_Matches.csv", "Copa do Brasil", false, false},
		{"Libertadores_Matches.csv", "Copa Libertadores", false, false},
		{"novo_campeonato_brasileiro.csv", "Brasileirão", true, false},
		{"BR-Football-Dataset.csv", "", false, true},
	}
	for _, f := range files {
		p := filepath.Join(dir, f.name)
		file, err := os.Open(p)
		if err != nil {
			if errors.Is(err, os.ErrNotExist) {
				continue
			}
			return nil, err
		}
		var ms []Match
		if f.historical {
			ms, err = readHistorical(file, f.competition)
		} else if f.extended {
			ms, err = readExtended(file)
		} else {
			ms, err = readMatches(file, f.competition)
		}
		file.Close()
		if err != nil {
			return nil, fmt.Errorf("%s: %w", f.name, err)
		}
		s.Matches = append(s.Matches, ms...)
	}
	file, err := os.Open(filepath.Join(dir, "fifa_data.csv"))
	if err == nil {
		s.Players, err = readPlayers(file)
		file.Close()
	}
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	sort.SliceStable(s.Matches, func(i, j int) bool { return s.Matches[i].Date.Before(s.Matches[j].Date) })
	return s, nil
}

func header(r []string) map[string]int {
	m := map[string]int{}
	for i, v := range r {
		m[strings.ToLower(strings.TrimSpace(strings.TrimPrefix(v, "\ufeff")))] = i
	}
	return m
}
func val(row []string, h map[string]int, keys ...string) string {
	for _, k := range keys {
		if i, ok := h[strings.ToLower(k)]; ok && i < len(row) {
			return strings.TrimSpace(row[i])
		}
	}
	return ""
}
func integer(v string) int {
	v = strings.TrimSpace(v)
	if i, err := strconv.Atoi(v); err == nil {
		return i
	}
	if f, err := strconv.ParseFloat(v, 64); err == nil {
		return int(f)
	}
	return 0
}
func parseDate(v string) time.Time {
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "02/01/2006 15:04:05"} {
		if t, e := time.Parse(layout, strings.TrimSpace(v)); e == nil {
			return t
		}
	}
	return time.Time{}
}
func readAll(r io.Reader) ([][]string, map[string]int, error) {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	if len(rows) == 0 {
		return rows, map[string]int{}, nil
	}
	return rows, header(rows[0]), nil
}
func readMatches(r io.Reader, comp string) ([]Match, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Match{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Match{Competition: comp, Date: parseDate(val(x, h, "datetime")), Round: val(x, h, "round"), Home: val(x, h, "home_team"), Away: val(x, h, "away_team"), HomeGoals: integer(val(x, h, "home_goal")), AwayGoals: integer(val(x, h, "away_goal")), Season: integer(val(x, h, "season")), Stage: val(x, h, "stage")})
	}
	return out, nil
}
func readHistorical(r io.Reader, comp string) ([]Match, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Match{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Match{Competition: comp, Date: parseDate(val(x, h, "data")), Round: val(x, h, "rodada"), Home: val(x, h, "equipe_mandante"), Away: val(x, h, "equipe_visitante"), HomeGoals: integer(val(x, h, "gols_mandante")), AwayGoals: integer(val(x, h, "gols_visitante")), Season: integer(val(x, h, "ano")), Venue: val(x, h, "arena")})
	}
	return out, nil
}
func readExtended(r io.Reader) ([]Match, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Match{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Match{Competition: val(x, h, "tournament"), Date: parseDate(val(x, h, "date")), Home: val(x, h, "home"), Away: val(x, h, "away"), HomeGoals: integer(val(x, h, "home_goal")), AwayGoals: integer(val(x, h, "away_goal"))})
	}
	return out, nil
}
func readPlayers(r io.Reader) ([]Player, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Player{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Player{ID: integer(val(x, h, "id")), Name: val(x, h, "name"), Age: integer(val(x, h, "age")), Nationality: val(x, h, "nationality"), Overall: integer(val(x, h, "overall")), Potential: integer(val(x, h, "potential")), Club: val(x, h, "club"), Position: val(x, h, "position")})
	}
	return out, nil
}

func clean(s string) string { return strings.ToLower(strings.TrimSpace(s)) }
func teamMatch(a, b string) bool {
	a, b = clean(a), clean(b)
	return a == b || strings.TrimSuffix(a, "-sp") == strings.TrimSuffix(b, "-sp")
}
