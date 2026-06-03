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
)

// Match is a normalized match record from any of the match CSVs.
type Match struct {
	Competition string
	Date        time.Time
	HomeTeam    string
	AwayTeam    string
	HomeKey     string
	AwayKey     string
	HomeGoals   int
	AwayGoals   int
	Season      int
	Round       string
	Arena       string
	Stage       string
	Source      string
}

// Player is a normalized FIFA player record.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	ClubKey     string
	Position    string
	Jersey      int
	Height      string
	Weight      string
}

// DataStore holds all loaded records.
type DataStore struct {
	Matches []Match
	Players []Player

	matchesByTeamKey  map[string][]int
	playersByClubKey  map[string][]int
	playersByNatLower map[string][]int
}

func NewDataStore() *DataStore {
	return &DataStore{
		matchesByTeamKey:  map[string][]int{},
		playersByClubKey:  map[string][]int{},
		playersByNatLower: map[string][]int{},
	}
}

// LoadAll loads every CSV under dataDir/kaggle.
func (d *DataStore) LoadAll(dataDir string) error {
	kaggle := filepath.Join(dataDir, "kaggle")
	type loader struct {
		file string
		fn   func(string) error
	}
	loaders := []loader{
		{"Brasileirao_Matches.csv", d.loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", d.loadCopaBrasil},
		{"Libertadores_Matches.csv", d.loadLibertadores},
		{"BR-Football-Dataset.csv", d.loadBRFootball},
		{"novo_campeonato_brasileiro.csv", d.loadNovoBrasileirao},
		{"fifa_data.csv", d.loadFifa},
	}
	for _, l := range loaders {
		path := filepath.Join(kaggle, l.file)
		if err := l.fn(path); err != nil {
			return fmt.Errorf("load %s: %w", l.file, err)
		}
	}
	d.dedupMatches()
	d.buildIndexes()
	return nil
}

// dedupMatches removes duplicate matches that appear in more than one CSV
// (e.g. 2019 Brasileirão is in both Brasileirao_Matches.csv and novo_campeonato_brasileiro.csv).
// Match identity = (date YYYY-MM-DD, normalized teams, score, competition family).
func (d *DataStore) dedupMatches() {
	seen := make(map[string]bool, len(d.Matches))
	out := d.Matches[:0]
	for _, m := range d.Matches {
		date := ""
		if !m.Date.IsZero() {
			date = m.Date.Format("2006-01-02")
		}
		// Use a coarse competition key so "Brasileirão" matches "Serie A".
		compKey := competitionKey(m.Competition)
		key := date + "|" + m.HomeKey + "|" + m.AwayKey + "|" +
			fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals) + "|" + compKey
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, m)
	}
	d.Matches = out
}

// competitionKey groups equivalent competition names from different CSVs.
func competitionKey(c string) string {
	s := strings.ToLower(c)
	switch {
	case strings.Contains(s, "brasileir") || strings.Contains(s, "serie a"):
		return "brasileirao"
	case strings.Contains(s, "copa do brasil") || strings.Contains(s, "brazilian cup"):
		return "copa-do-brasil"
	case strings.Contains(s, "libertadores"):
		return "libertadores"
	case strings.Contains(s, "sudamericana"):
		return "sudamericana"
	}
	return s
}

func (d *DataStore) buildIndexes() {
	for i, m := range d.Matches {
		d.matchesByTeamKey[m.HomeKey] = append(d.matchesByTeamKey[m.HomeKey], i)
		if m.AwayKey != m.HomeKey {
			d.matchesByTeamKey[m.AwayKey] = append(d.matchesByTeamKey[m.AwayKey], i)
		}
	}
	for i, p := range d.Players {
		d.playersByClubKey[p.ClubKey] = append(d.playersByClubKey[p.ClubKey], i)
		nat := strings.ToLower(p.Nationality)
		d.playersByNatLower[nat] = append(d.playersByNatLower[nat], i)
	}
}

// --- CSV helpers ----------------------------------------------------------

func openCSV(path string) (*csv.Reader, *os.File, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	return r, f, nil
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if i := strings.IndexByte(s, '.'); i > 0 {
		s = s[:i]
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}

// parseDate accepts ISO ("2023-09-24"), ISO+time, or Brazilian DD/MM/YYYY.
func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}
	}
	layouts := []string{
		"2006-01-02 15:04:05",
		"2006-01-02",
		"02/01/2006",
		time.RFC3339,
	}
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// utf8BOM is the byte sequence for U+FEFF.
const utf8BOM = "\xef\xbb\xbf"

// headerIndex builds a header -> column-index map.
func headerIndex(header []string) map[string]int {
	out := make(map[string]int, len(header))
	for i, h := range header {
		clean := strings.TrimPrefix(h, utf8BOM)
		out[strings.TrimSpace(strings.ToLower(clean))] = i
	}
	return out
}

func get(row []string, idx map[string]int, key string) string {
	i, ok := idx[key]
	if !ok || i >= len(row) {
		return ""
	}
	return row[i]
}

// --- Per-file loaders -----------------------------------------------------

func (d *DataStore) loadBrasileirao(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
		home := get(row, idx, "home_team")
		away := get(row, idx, "away_team")
		m := Match{
			Competition: "Brasileirão",
			Date:        parseDate(get(row, idx, "datetime")),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeam(home),
			AwayKey:     NormalizeTeam(away),
			HomeGoals:   parseInt(get(row, idx, "home_goal")),
			AwayGoals:   parseInt(get(row, idx, "away_goal")),
			Season:      parseInt(get(row, idx, "season")),
			Round:       strings.TrimSpace(get(row, idx, "round")),
			Source:      "Brasileirao_Matches.csv",
		}
		d.Matches = append(d.Matches, m)
	}
	return nil
}

func (d *DataStore) loadCopaBrasil(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
		home := get(row, idx, "home_team")
		away := get(row, idx, "away_team")
		m := Match{
			Competition: "Copa do Brasil",
			Date:        parseDate(get(row, idx, "datetime")),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeam(home),
			AwayKey:     NormalizeTeam(away),
			HomeGoals:   parseInt(get(row, idx, "home_goal")),
			AwayGoals:   parseInt(get(row, idx, "away_goal")),
			Season:      parseInt(get(row, idx, "season")),
			Round:       strings.TrimSpace(get(row, idx, "round")),
			Source:      "Brazilian_Cup_Matches.csv",
		}
		d.Matches = append(d.Matches, m)
	}
	return nil
}

func (d *DataStore) loadLibertadores(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
		home := get(row, idx, "home_team")
		away := get(row, idx, "away_team")
		m := Match{
			Competition: "Libertadores",
			Date:        parseDate(get(row, idx, "datetime")),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeam(home),
			AwayKey:     NormalizeTeam(away),
			HomeGoals:   parseInt(get(row, idx, "home_goal")),
			AwayGoals:   parseInt(get(row, idx, "away_goal")),
			Season:      parseInt(get(row, idx, "season")),
			Stage:       strings.TrimSpace(get(row, idx, "stage")),
			Source:      "Libertadores_Matches.csv",
		}
		m.Round = m.Stage
		d.Matches = append(d.Matches, m)
	}
	return nil
}

func (d *DataStore) loadBRFootball(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
		tournament := strings.TrimSpace(get(row, idx, "tournament"))
		home := get(row, idx, "home")
		away := get(row, idx, "away")
		date := parseDate(get(row, idx, "date"))
		season := 0
		if !date.IsZero() {
			season = date.Year()
		}
		m := Match{
			Competition: tournament,
			Date:        date,
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeam(home),
			AwayKey:     NormalizeTeam(away),
			HomeGoals:   parseInt(get(row, idx, "home_goal")),
			AwayGoals:   parseInt(get(row, idx, "away_goal")),
			Season:      season,
			Source:      "BR-Football-Dataset.csv",
		}
		d.Matches = append(d.Matches, m)
	}
	return nil
}

func (d *DataStore) loadNovoBrasileirao(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
		home := get(row, idx, "equipe_mandante")
		away := get(row, idx, "equipe_visitante")
		m := Match{
			Competition: "Brasileirão",
			Date:        parseDate(get(row, idx, "data")),
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeam(home),
			AwayKey:     NormalizeTeam(away),
			HomeGoals:   parseInt(get(row, idx, "gols_mandante")),
			AwayGoals:   parseInt(get(row, idx, "gols_visitante")),
			Season:      parseInt(get(row, idx, "ano")),
			Round:       strings.TrimSpace(get(row, idx, "rodada")),
			Arena:       strings.TrimSpace(get(row, idx, "arena")),
			Source:      "novo_campeonato_brasileiro.csv",
		}
		d.Matches = append(d.Matches, m)
	}
	return nil
}

func (d *DataStore) loadFifa(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		club := strings.TrimSpace(get(row, idx, "club"))
		p := Player{
			ID:          parseInt(get(row, idx, "id")),
			Name:        strings.TrimSpace(get(row, idx, "name")),
			Age:         parseInt(get(row, idx, "age")),
			Nationality: strings.TrimSpace(get(row, idx, "nationality")),
			Overall:     parseInt(get(row, idx, "overall")),
			Potential:   parseInt(get(row, idx, "potential")),
			Club:        club,
			ClubKey:     NormalizeTeam(club),
			Position:    strings.TrimSpace(get(row, idx, "position")),
			Jersey:      parseInt(get(row, idx, "jersey number")),
			Height:      strings.TrimSpace(get(row, idx, "height")),
			Weight:      strings.TrimSpace(get(row, idx, "weight")),
		}
		if p.Name == "" {
			continue
		}
		d.Players = append(d.Players, p)
	}
	return nil
}
