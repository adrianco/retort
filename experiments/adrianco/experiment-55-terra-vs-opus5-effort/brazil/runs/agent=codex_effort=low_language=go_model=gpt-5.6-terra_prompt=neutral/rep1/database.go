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
	"unicode"
)

type Match struct {
	Date        time.Time `json:"date"`
	Home        string    `json:"home_team"`
	Away        string    `json:"away_team"`
	Competition string    `json:"competition"`
	Stage       string    `json:"stage,omitempty"`
	Stadium     string    `json:"stadium,omitempty"`
	HomeGoals   int       `json:"home_goals"`
	AwayGoals   int       `json:"away_goals"`
	Season      int       `json:"season"`
	Round       int       `json:"round,omitempty"`
	Corners     *float64  `json:"total_corners,omitempty"`
}
type Player struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	Age         int    `json:"age,omitempty"`
	Overall     int    `json:"overall,omitempty"`
	Potential   int    `json:"potential,omitempty"`
}
type Database struct {
	Matches []Match
	Players []Player
}

func LoadDatabase(dir string) (*Database, error) {
	d := &Database{}
	for _, spec := range []struct {
		name, comp        string
		historical, stats bool
	}{
		{"Brasileirao_Matches.csv", "Brasileirão", false, false}, {"Brazilian_Cup_Matches.csv", "Copa do Brasil", false, false}, {"Libertadores_Matches.csv", "Libertadores", false, false}, {"BR-Football-Dataset.csv", "", false, true}, {"novo_campeonato_brasileiro.csv", "Brasileirão", true, false},
	} {
		ms, err := loadMatches(filepath.Join(dir, spec.name), spec.comp, spec.historical, spec.stats)
		if err != nil {
			return nil, err
		}
		d.Matches = append(d.Matches, ms...)
	}
	ps, err := loadPlayers(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, err
	}
	d.Players = ps
	return d, nil
}
func csvRows(path string) ([]map[string]string, error) {
	f, e := os.Open(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	h, e := r.Read()
	if e != nil {
		return nil, e
	}
	for i := range h {
		h[i] = strings.TrimPrefix(h[i], "\ufeff")
	}
	var out []map[string]string
	for {
		x, e := r.Read()
		if e == io.EOF {
			break
		}
		if e != nil {
			return nil, fmt.Errorf("%s: %w", path, e)
		}
		m := map[string]string{}
		for i, v := range x {
			if i < len(h) {
				m[h[i]] = v
			}
		}
		out = append(out, m)
	}
	return out, nil
}
func loadMatches(path, competition string, historical, stats bool) ([]Match, error) {
	rows, e := csvRows(path)
	if e != nil {
		return nil, e
	}
	out := make([]Match, 0, len(rows))
	for _, r := range rows {
		m := Match{Competition: competition}
		if historical {
			m.Home = r["Equipe_mandante"]
			m.Away = r["Equipe_visitante"]
			m.HomeGoals = num(r["Gols_mandante"])
			m.AwayGoals = num(r["Gols_visitante"])
			m.Season = num(r["Ano"])
			m.Round = num(r["Rodada"])
			m.Stadium = r["Arena"]
			m.Date = parseDate(r["Data"])
		} else if stats {
			m.Home = r["home"]
			m.Away = r["away"]
			m.HomeGoals = num(r["home_goal"])
			m.AwayGoals = num(r["away_goal"])
			m.Competition = r["tournament"]
			m.Date = parseDate(r["date"])
			m.Season = m.Date.Year()
			if r["total_corners"] != "" {
				v, _ := strconv.ParseFloat(r["total_corners"], 64)
				m.Corners = &v
			}
		} else {
			m.Home = r["home_team"]
			m.Away = r["away_team"]
			m.HomeGoals = num(r["home_goal"])
			m.AwayGoals = num(r["away_goal"])
			m.Season = num(r["season"])
			m.Round = num(r["round"])
			m.Stage = r["stage"]
			m.Date = parseDate(r["datetime"])
		}
		if m.Home != "" && m.Away != "" {
			out = append(out, m)
		}
	}
	return out, nil
}
func loadPlayers(path string) ([]Player, error) {
	rows, e := csvRows(path)
	if e != nil {
		return nil, e
	}
	out := make([]Player, 0, len(rows))
	for _, r := range rows {
		out = append(out, Player{num(r["ID"]), r["Name"], r["Nationality"], r["Club"], r["Position"], num(r["Age"]), num(r["Overall"]), num(r["Potential"])})
	}
	return out, nil
}
func num(s string) int { v, _ := strconv.ParseFloat(strings.TrimSpace(s), 64); return int(v) }
func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	for _, f := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006"} {
		if t, e := time.Parse(f, s); e == nil {
			return t
		}
	}
	return time.Time{}
}
func norm(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	var b strings.Builder
	for _, r := range s {
		if unicode.Is(unicode.Mn, r) {
			continue
		}
		switch r {
		case 'á', 'à', 'ã', 'â', 'ä':
			r = 'a'
		case 'é', 'ê', 'ë':
			r = 'e'
		case 'í', 'î', 'ï':
			r = 'i'
		case 'ó', 'ô', 'õ', 'ö':
			r = 'o'
		case 'ú', 'ü':
			r = 'u'
		case 'ç':
			r = 'c'
		}
		if unicode.IsLetter(r) || unicode.IsNumber(r) || unicode.IsSpace(r) {
			b.WriteRune(r)
		}
	}
	s = strings.Join(strings.Fields(b.String()), " ")
	for _, suffix := range []string{" sp", " rj", " mg", " rs", " pr", " pe", " ba", " ce", " go", " sc", " df", " pa", " es", " mt", " am", " al"} {
		if strings.HasSuffix(s, suffix) {
			s = strings.TrimSpace(strings.TrimSuffix(s, suffix))
		}
	}
	return strings.TrimPrefix(s, "sport club ")
}
func teamMatch(name, query string) bool {
	n, q := norm(name), norm(query)
	return n == q || strings.Contains(n, q) || strings.Contains(q, n)
}
