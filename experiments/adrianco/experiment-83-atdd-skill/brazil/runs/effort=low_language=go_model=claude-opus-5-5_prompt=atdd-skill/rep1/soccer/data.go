package soccer

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	SerieA       = "Brasileirão Série A"
	SerieB       = "Brasileirão Série B"
	SerieC       = "Série C"
	CopaDoBrasil = "Copa do Brasil"
	Libertadores = "Libertadores"
)

type Match struct {
	Date                                           time.Time
	Competition                                    string
	Season                                         int
	Round, Stage, Arena                            string
	HomeKey, AwayKey                               string
	HomeGoals, AwayGoals                           int
	HomeCorners, AwayCorners, HomeShots, AwayShots int
	HasStats                                       bool
	Sources                                        []string
}

type Player struct {
	Name, Nationality, Club, Position, Foot, Height, Weight, Value string
	Age, Overall, Potential, Jersey                                int
	Skills                                                         map[string]int
}

type DB struct {
	Matches       []*Match
	Players       []*Player
	names         map[string]string
	index         map[string]*Match
	cupFinalRound map[int]int
}

func (db *DB) Name(key string) string {
	if n, ok := db.names[key]; ok {
		return n
	}
	return key
}

func (db *DB) seeName(raw, key string) {
	if countryTag.MatchString(strings.TrimSpace(raw)) {
		raw = countryTag.ReplaceAllString(strings.TrimSpace(raw), "") + " (" + strings.ToUpper(key[strings.LastIndex(key, "-")+1:]) + ")"
	} else {
		raw = strings.TrimSpace(parens.ReplaceAllString(raw, ""))
	}
	d := displayName(raw, key)
	cur, ok := db.names[key]
	if !ok || (!hasAccent(cur) && hasAccent(d)) || (hasAccent(cur) == hasAccent(d) && len(d) < len(cur)) {
		db.names[key] = d
	}
}

func readCSV(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	rows, err := r.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if len(rows) == 0 {
		return nil, nil
	}
	hdr := rows[0]
	hdr[0] = strings.TrimPrefix(hdr[0], "\ufeff")
	out := make([]map[string]string, 0, len(rows)-1)
	for _, row := range rows[1:] {
		m := make(map[string]string, len(hdr))
		for i, h := range hdr {
			if i < len(row) {
				m[h] = strings.TrimSpace(row[i])
			}
		}
		out = append(out, m)
	}
	return out, nil
}

// ParseDate accepts ISO dates, ISO date-times and Brazilian DD/MM/YYYY.
func ParseDate(s string) (time.Time, error) {
	for _, l := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "2006-01-02T15:04:05"} {
		if t, err := time.Parse(l, strings.TrimSpace(s)); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("unrecognised date %q", s)
}

func num(s string) int {
	f, _ := strconv.ParseFloat(strings.TrimSpace(s), 64)
	return int(f)
}

// Load reads all six provided CSV files from dir.
func Load(dir string) (*DB, error) {
	db := &DB{names: map[string]string{}, index: map[string]*Match{}, cupFinalRound: map[int]int{}}
	type src struct {
		file string
		conv func(map[string]string) *Match
	}
	sources := []src{
		{"Brasileirao_Matches.csv", func(r map[string]string) *Match {
			return db.newMatch(r["datetime"], SerieA, num(r["season"]), r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], func(m *Match) { m.Round = r["round"] })
		}},
		{"novo_campeonato_brasileiro.csv", func(r map[string]string) *Match {
			return db.newMatch(r["Data"], SerieA, num(r["Ano"]), r["Equipe_mandante"], r["Equipe_visitante"], r["Gols_mandante"], r["Gols_visitante"], func(m *Match) { m.Round = r["Rodada"]; m.Arena = r["Arena"] })
		}},
		{"Brazilian_Cup_Matches.csv", func(r map[string]string) *Match {
			return db.newMatch(r["datetime"], CopaDoBrasil, num(r["season"]), r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], func(m *Match) { m.Round = r["round"] })
		}},
		{"Libertadores_Matches.csv", func(r map[string]string) *Match {
			return db.newMatch(r["datetime"], Libertadores, num(r["season"]), r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], func(m *Match) { m.Stage = r["stage"] })
		}},
		{"BR-Football-Dataset.csv", func(r map[string]string) *Match {
			comp := map[string]string{"Serie A": SerieA, "Serie B": SerieB, "Serie C": SerieC, "Copa do Brasil": CopaDoBrasil}[r["tournament"]]
			if comp == "" {
				comp = r["tournament"]
			}
			return db.newMatch(r["date"], comp, 0, r["home"], r["away"], r["home_goal"], r["away_goal"], func(m *Match) {
				m.HomeCorners, m.AwayCorners = num(r["home_corner"]), num(r["away_corner"])
				m.HomeShots, m.AwayShots = num(r["home_shots"]), num(r["away_shots"])
				m.HasStats = true
			})
		}},
	}
	for _, s := range sources {
		rows, err := readCSV(filepath.Join(dir, s.file))
		if err != nil {
			return nil, err
		}
		for _, r := range rows {
			if m := s.conv(r); m != nil {
				m.Sources = []string{s.file}
				db.add(m)
			}
		}
	}
	for _, m := range db.Matches {
		if m.Competition == CopaDoBrasil && m.Round != "" {
			if r := num(m.Round); r > db.cupFinalRound[m.Season] {
				db.cupFinalRound[m.Season] = r
			}
		}
	}
	sort.SliceStable(db.Matches, func(i, j int) bool { return db.Matches[i].Date.After(db.Matches[j].Date) })
	return db, db.loadPlayers(filepath.Join(dir, "fifa_data.csv"))
}

func (db *DB) newMatch(date, comp string, season int, home, away, hg, ag string, extra func(*Match)) *Match {
	t, err := ParseDate(date)
	if err != nil || home == "" || away == "" {
		return nil
	}
	if season == 0 {
		season = t.Year()
		if comp != CopaDoBrasil && t.Month() <= time.March {
			season-- // league seasons can spill into the next calendar year (e.g. 2020)
		}
	}
	m := &Match{Date: t, Competition: comp, Season: season, HomeKey: TeamKey(home), AwayKey: TeamKey(away), HomeGoals: num(hg), AwayGoals: num(ag)}
	db.seeName(home, m.HomeKey)
	db.seeName(away, m.AwayKey)
	extra(m)
	return m
}

func (m *Match) keys() []string {
	pair := m.Competition + "|" + m.HomeKey + "|" + m.AwayKey
	if m.Competition == SerieA || m.Competition == SerieB || m.Competition == SerieC {
		return []string{fmt.Sprint(m.Season) + "|" + pair}
	}
	var ks []string
	for d := -1; d <= 1; d++ {
		ks = append(ks, m.Date.AddDate(0, 0, d).Format("2006-01-02")+"|"+pair)
	}
	return ks
}

// add merges a match seen in several files into one record.
func (db *DB) add(m *Match) {
	for _, k := range m.keys() {
		if ex, ok := db.index[k]; ok {
			ex.Sources = append(ex.Sources, m.Sources...)
			if m.HasStats && !ex.HasStats {
				ex.HomeCorners, ex.AwayCorners, ex.HomeShots, ex.AwayShots, ex.HasStats = m.HomeCorners, m.AwayCorners, m.HomeShots, m.AwayShots, true
			}
			return
		}
	}
	db.index[m.keys()[len(m.keys())/2]] = m
	db.Matches = append(db.Matches, m)
}

var skillCols = []string{"Crossing", "Finishing", "Dribbling", "ShortPassing", "LongShots", "Acceleration", "SprintSpeed", "Stamina", "Strength", "StandingTackle", "GKDiving", "GKReflexes"}

func (db *DB) loadPlayers(path string) error {
	rows, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, r := range rows {
		p := &Player{Name: r["Name"], Nationality: r["Nationality"], Club: r["Club"], Position: r["Position"], Foot: r["Preferred Foot"],
			Height: r["Height"], Weight: r["Weight"], Value: r["Value"], Age: num(r["Age"]), Overall: num(r["Overall"]),
			Potential: num(r["Potential"]), Jersey: num(r["Jersey Number"]), Skills: map[string]int{}}
		for _, c := range skillCols {
			if v, ok := r[c]; ok && v != "" {
				p.Skills[c] = num(v)
			}
		}
		db.Players = append(db.Players, p)
	}
	sort.SliceStable(db.Players, func(i, j int) bool { return db.Players[i].Overall > db.Players[j].Overall })
	return nil
}
