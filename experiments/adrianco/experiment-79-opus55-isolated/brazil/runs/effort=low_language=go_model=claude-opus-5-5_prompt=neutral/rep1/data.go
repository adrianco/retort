package main

// Loading of the six Kaggle CSV files into a single in-memory Store.
//
// The three Brasileirão sources overlap (2003-2019, 2012-2022 and 2014-2023),
// as do the two Copa do Brasil sources, so matches are de-duplicated on
// (competition, home, away, date±1 day) and merged: the first source loaded
// wins on score, later ones contribute stadium and extended statistics.

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCup          = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

var allCompetitions = []string{CompSerieA, CompSerieB, CompSerieC, CompCup, CompLibertadores}

const (
	FileBrasileirao  = "Brasileirao_Matches.csv"
	FileCup          = "Brazilian_Cup_Matches.csv"
	FileLibertadores = "Libertadores_Matches.csv"
	FileExtended     = "BR-Football-Dataset.csv"
	FileHistorical   = "novo_campeonato_brasileiro.csv"
	FileFIFA         = "fifa_data.csv"
)

// ExtStats holds the extra per-match statistics of BR-Football-Dataset.csv.
type ExtStats struct {
	HomeCorners, AwayCorners float64
	HomeAttacks, AwayAttacks float64
	HomeShots, AwayShots     float64
	HasAttacks, HasShots     bool
}

// Match is one played match.
type Match struct {
	Date        time.Time
	Competition string
	Season      int
	Round       string // league round or cup round number
	Stage       string // cup stage, e.g. "final", "group stage"
	HomeKey     string
	AwayKey     string
	HomeGoals   int
	AwayGoals   int
	Arena       string
	Ext         *ExtStats
	Sources     []string
}

// Player is one row of the FIFA dataset.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	ClubKey     string // canonical team key when the club is in the match data
	Position    string
	Jersey      string
	Height      string
	Weight      string
	Foot        string
	Value       string
	Wage        string
	Skills      map[string]int
}

// FileInfo records what was read from one CSV file.
type FileInfo struct {
	Rows     int // data rows in the file
	Loaded   int // rows that produced a usable record
	Unplayed int // rows without a score
	Merged   int // rows merged into a match already known from another file
}

// Store is the queryable knowledge base.
type Store struct {
	Reg     *Registry
	Matches []*Match // sorted by date ascending
	Players []*Player
	Files   map[string]*FileInfo

	byTeam map[string][]*Match
	dedup  map[string][]*Match
}

var dateLayouts = []string{
	"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", time.RFC3339, "2006-01-02T15:04:05", "02/01/2006 15:04", "2006-01-02 15:04",
}

// parseDate accepts ISO, ISO with time and Brazilian DD/MM/YYYY dates.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	for _, l := range dateLayouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// parseGoals accepts "2" and "2.0"; "NA", "-" and "" mean not played.
func parseGoals(s string) (int, bool) {
	f, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil || f < 0 {
		return 0, false
	}
	return int(f), true
}

func atoi(s string) int {
	n, _ := parseGoals(s)
	return n
}

// readCSV returns the rows of a file as header-keyed maps.
func readCSV(path string) ([]map[string]string, []string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	header, err := r.Read()
	if err != nil {
		return nil, nil, fmt.Errorf("%s: %w", path, err)
	}
	for i := range header {
		header[i] = strings.TrimSpace(strings.TrimPrefix(header[i], "\ufeff"))
	}
	var rows []map[string]string
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, nil, fmt.Errorf("%s: %w", path, err)
		}
		row := make(map[string]string, len(header))
		for i, v := range rec {
			if i < len(header) {
				row[header[i]] = v
			}
		}
		rows = append(rows, row)
	}
	return rows, header, nil
}

// rawMatch is a match before team names are resolved.
type rawMatch struct {
	m          Match
	home, away string
	file       string
	intl       bool
}

// LoadStore reads all six CSV files from dir.
func LoadStore(dir string) (*Store, error) {
	s := &Store{
		Reg:    NewRegistry(),
		Files:  map[string]*FileInfo{},
		byTeam: map[string][]*Match{},
		dedup:  map[string][]*Match{},
	}
	var raws []rawMatch
	add := func(file string, row map[string]string, m Match, home, away, date, hg, ag string) {
		fi := s.Files[file]
		h, ok1 := parseGoals(hg)
		a, ok2 := parseGoals(ag)
		d, ok3 := parseDate(date)
		if !ok1 || !ok2 || !ok3 || strings.TrimSpace(home) == "" || strings.TrimSpace(away) == "" {
			fi.Unplayed++
			return
		}
		m.Date, m.HomeGoals, m.AwayGoals = d, h, a
		if m.Season == 0 {
			m.Season = d.Year()
		}
		m.Sources = []string{file}
		raws = append(raws, rawMatch{m: m, home: home, away: away, file: file, intl: m.Competition == CompLibertadores})
	}

	// Order matters: earlier files take precedence when matches overlap.
	loaders := []struct {
		file string
		fn   func(file string, row map[string]string)
	}{
		{FileBrasileirao, func(f string, r map[string]string) {
			add(f, r, Match{Competition: CompSerieA, Season: atoi(r["season"]), Round: r["round"]},
				r["home_team"], r["away_team"], r["datetime"], r["home_goal"], r["away_goal"])
		}},
		{FileHistorical, func(f string, r map[string]string) {
			add(f, r, Match{Competition: CompSerieA, Season: atoi(r["Ano"]), Round: r["Rodada"], Arena: strings.TrimSpace(r["Arena"])},
				r["Equipe_mandante"], r["Equipe_visitante"], r["Data"], r["Gols_mandante"], r["Gols_visitante"])
		}},
		{FileCup, func(f string, r map[string]string) {
			add(f, r, Match{Competition: CompCup, Season: atoi(r["season"]), Round: r["round"]},
				r["home_team"], r["away_team"], r["datetime"], r["home_goal"], r["away_goal"])
		}},
		{FileLibertadores, func(f string, r map[string]string) {
			add(f, r, Match{Competition: CompLibertadores, Season: atoi(r["season"]), Stage: strings.TrimSpace(r["stage"])},
				r["home_team"], r["away_team"], r["datetime"], r["home_goal"], r["away_goal"])
		}},
		{FileExtended, func(f string, r map[string]string) {
			comp, ok := map[string]string{"Serie A": CompSerieA, "Serie B": CompSerieB, "Serie C": CompSerieC, "Copa do Brasil": CompCup}[strings.TrimSpace(r["tournament"])]
			if !ok {
				comp = strings.TrimSpace(r["tournament"])
			}
			m := Match{Competition: comp}
			// The 2020 season was played until early 2021.
			if d, ok := parseDate(r["date"]); ok && d.Year() == 2021 && d.Before(time.Date(2021, 3, 8, 0, 0, 0, 0, time.UTC)) {
				m.Season = 2020
			}
			e := &ExtStats{}
			e.HomeCorners, _ = strconv.ParseFloat(r["home_corner"], 64)
			e.AwayCorners, _ = strconv.ParseFloat(r["away_corner"], 64)
			var err1, err2 error
			e.HomeAttacks, err1 = strconv.ParseFloat(r["home_attack"], 64)
			e.AwayAttacks, err2 = strconv.ParseFloat(r["away_attack"], 64)
			e.HasAttacks = err1 == nil && err2 == nil
			e.HomeShots, err1 = strconv.ParseFloat(r["home_shots"], 64)
			e.AwayShots, err2 = strconv.ParseFloat(r["away_shots"], 64)
			e.HasShots = err1 == nil && err2 == nil
			m.Ext = e
			add(f, r, m, r["home"], r["away"], r["date"], r["home_goal"], r["away_goal"])
		}},
	}
	for _, l := range loaders {
		rows, _, err := readCSV(filepath.Join(dir, l.file))
		if err != nil {
			return nil, err
		}
		s.Files[l.file] = &FileInfo{Rows: len(rows)}
		for _, row := range rows {
			l.fn(l.file, row)
		}
	}

	for _, r := range raws {
		s.Reg.observe(r.home)
		s.Reg.observe(r.away)
	}
	for i := range raws {
		r := &raws[i]
		m := r.m
		m.HomeKey = s.Reg.keyFor(r.home, r.intl)
		m.AwayKey = s.Reg.keyFor(r.away, r.intl)
		s.Files[r.file].Loaded++
		if old := s.findDuplicate(&m); old != nil {
			s.Files[r.file].Merged++
			old.Sources = append(old.Sources, r.file)
			if old.Arena == "" {
				old.Arena = m.Arena
			}
			if old.Ext == nil {
				old.Ext = m.Ext
			}
			continue
		}
		mp := &m
		s.Matches = append(s.Matches, mp)
		k := dedupKey(mp)
		s.dedup[k] = append(s.dedup[k], mp)
		s.Reg.Teams[m.HomeKey].Matches++
		s.Reg.Teams[m.AwayKey].Matches++
	}
	s.dedup = nil
	s.Reg.Freeze()
	s.initDerbies()
	s.markCupFinals()

	sort.SliceStable(s.Matches, func(i, j int) bool { return s.Matches[i].Date.Before(s.Matches[j].Date) })
	for _, m := range s.Matches {
		s.byTeam[m.HomeKey] = append(s.byTeam[m.HomeKey], m)
		s.byTeam[m.AwayKey] = append(s.byTeam[m.AwayKey], m)
	}
	if err := s.loadPlayers(filepath.Join(dir, FileFIFA)); err != nil {
		return nil, err
	}
	return s, nil
}

func dedupKey(m *Match) string { return m.Competition + "\x00" + m.HomeKey + "\x00" + m.AwayKey }

func dayOf(t time.Time) int64 { return t.Unix() / 86400 }

// findDuplicate returns an already loaded match describing the same fixture.
func (s *Store) findDuplicate(m *Match) *Match {
	for _, o := range s.dedup[dedupKey(m)] {
		if o.Sources[0] == m.Sources[0] {
			continue // never merge rows of the same file
		}
		d := dayOf(o.Date) - dayOf(m.Date)
		if d >= -1 && d <= 1 {
			return o
		}
		// A Série A pairing happens once per season at each ground.
		if m.Competition == CompSerieA && o.Season == m.Season {
			return o
		}
		// Cup dates differ by a few days between sources; the same fixture
		// with the same score in one season is the same match.
		if m.Competition == CompCup && o.Season == m.Season && o.HomeGoals == m.HomeGoals && o.AwayGoals == m.AwayGoals {
			return o
		}
	}
	return nil
}

// markCupFinals labels the last round of each complete Copa do Brasil season.
func (s *Store) markCupFinals() {
	type rk struct{ season, round int }
	count := map[rk]int{}
	maxRound := map[int]int{}
	for _, m := range s.Matches {
		if m.Competition != CompCup || m.Round == "" {
			continue
		}
		r := atoi(m.Round)
		count[rk{m.Season, r}]++
		if r > maxRound[m.Season] {
			maxRound[m.Season] = r
		}
	}
	for _, m := range s.Matches {
		if m.Competition != CompCup || m.Round == "" {
			continue
		}
		r := atoi(m.Round)
		if r == maxRound[m.Season] && r >= 6 && count[rk{m.Season, r}] <= 2 {
			m.Stage = "final"
		}
	}
}

var skillColumns = strings.Fields("Crossing Finishing HeadingAccuracy ShortPassing Volleys Dribbling Curve FKAccuracy LongPassing " +
	"BallControl Acceleration SprintSpeed Agility Reactions Balance ShotPower Jumping Stamina Strength LongShots Aggression " +
	"Interceptions Positioning Vision Penalties Composure Marking StandingTackle SlidingTackle GKDiving GKHandling GKKicking " +
	"GKPositioning GKReflexes")

// FIFA clubs that share a name with a Brazilian club but are unrelated.
var foreignClubs = map[string]bool{"Boavista FC": true}

func (s *Store) loadPlayers(path string) error {
	rows, _, err := readCSV(path)
	if err != nil {
		return err
	}
	fi := &FileInfo{Rows: len(rows)}
	s.Files[FileFIFA] = fi
	clubKeys := map[string]string{}
	for _, r := range rows {
		name := strings.TrimSpace(r["Name"])
		if name == "" {
			continue
		}
		p := &Player{
			ID: atoi(r["ID"]), Name: name, Age: atoi(r["Age"]), Nationality: strings.TrimSpace(r["Nationality"]),
			Overall: atoi(r["Overall"]), Potential: atoi(r["Potential"]), Club: strings.TrimSpace(r["Club"]),
			Position: strings.TrimSpace(r["Position"]), Jersey: strings.TrimSuffix(strings.TrimSpace(r["Jersey Number"]), ".0"),
			Height: r["Height"], Weight: r["Weight"], Foot: r["Preferred Foot"], Value: r["Value"], Wage: r["Wage"],
			Skills: map[string]int{},
		}
		for _, c := range skillColumns {
			if v, ok := parseGoals(r[c]); ok {
				p.Skills[c] = v
			}
		}
		key, seen := clubKeys[p.Club]
		if !seen {
			key = s.exactTeamKey(p.Club)
			clubKeys[p.Club] = key
		}
		p.ClubKey = key
		s.Players = append(s.Players, p)
		fi.Loaded++
	}
	sort.SliceStable(s.Players, func(i, j int) bool { return s.Players[i].Overall > s.Players[j].Overall })
	return nil
}

// exactTeamKey links a FIFA club name to a Brazilian team of the match data,
// without fuzzy matching. It returns "" when there is no such team.
func (s *Store) exactTeamKey(club string) string {
	if club == "" || foreignClubs[club] {
		return ""
	}
	p := parseName(club, false)
	st := p.state
	if st == "" {
		st = defaultStates[p.base]
	}
	if len(st) != 2 {
		return ""
	}
	if t, ok := s.Reg.Teams[p.base+"|"+st]; ok {
		return t.Key
	}
	return ""
}

// TeamName returns the display name for a team key.
func (s *Store) TeamName(key string) string {
	if t, ok := s.Reg.Teams[key]; ok {
		return t.Name
	}
	return key
}
