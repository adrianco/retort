package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"
)

// Match represents a unified match record across all datasets.
type Match struct {
	DateTime    time.Time
	HomeTeam    string
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Season      int
	Competition string
	Round       string
	Stage       string
	Arena       string
	// Extended stats (BR-Football-Dataset only)
	HomeCorners int
	AwayCorners int
	HomeAttacks int
	AwayAttacks int
	HomeShots   int
	AwayShots   int
}

// Player represents a FIFA player record.
type Player struct {
	ID         string
	Name       string
	Age        int
	Nationality string
	Overall    int
	Potential  int
	Club       string
	Position   string
	JerseyNum  string
	Height     string
	Weight     string
	Value      string
	Wage       string
	Foot       string
}

// Database holds all loaded data.
type Database struct {
	Matches []Match
	Players []Player
}

// accentMap maps accented runes to their ASCII equivalents for matching.
var accentMap = strings.NewReplacer(
	"ã", "a", "â", "a", "á", "a", "à", "a", "ä", "a",
	"Ã", "a", "Â", "a", "Á", "a", "À", "a", "Ä", "a",
	"ê", "e", "é", "e", "è", "e", "ë", "e",
	"Ê", "e", "É", "e", "È", "e", "Ë", "e",
	"í", "i", "î", "i", "ï", "i",
	"Í", "i", "Î", "i", "Ï", "i",
	"õ", "o", "ô", "o", "ó", "o", "ò", "o", "ö", "o",
	"Õ", "o", "Ô", "o", "Ó", "o", "Ò", "o", "Ö", "o",
	"ú", "u", "û", "u", "ü", "u",
	"Ú", "u", "Û", "u", "Ü", "u",
	"ç", "c", "Ç", "c",
	"ñ", "n", "Ñ", "n",
)

// normalizeForSearch prepares a string for accent-insensitive matching.
func normalizeForSearch(s string) string {
	return accentMap.Replace(strings.ToLower(s))
}

// normalize strips state suffixes (e.g. "Palmeiras-SP" -> "Palmeiras") and trims whitespace.
func normalize(name string) string {
	name = strings.TrimSpace(name)
	// Remove UTF-8 BOM if present (0xEF 0xBB 0xBF)
	name = strings.TrimPrefix(name, "\xef\xbb\xbf")
	// Strip state suffix like "-SP", "-RJ", etc.
	if idx := strings.LastIndex(name, "-"); idx != -1 {
		suffix := name[idx+1:]
		if len(suffix) == 2 && isAllUpper(suffix) {
			name = name[:idx]
		}
	}
	return strings.TrimSpace(name)
}

func isAllUpper(s string) bool {
	for _, r := range s {
		if !unicode.IsUpper(r) {
			return false
		}
	}
	return len(s) > 0
}

// normalizeLower returns a lowercase, accent-stripped, normalized team name for matching.
func normalizeLower(name string) string {
	return normalizeForSearch(normalize(name))
}

// teamMatches returns true if query matches teamName (case-insensitive, normalized).
func teamMatches(teamName, query string) bool {
	tn := normalizeLower(teamName)
	q := strings.ToLower(strings.TrimSpace(query))
	return strings.Contains(tn, q) || strings.Contains(q, tn)
}

var dateFormats = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006",
}

func parseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	for _, f := range dateFormats {
		if t, err := time.Parse(f, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("cannot parse date: %q", s)
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	if s == "" || s == "NA" || s == "N/A" {
		return 0
	}
	// handle floats like "1.0"
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(math.Round(f))
	}
	v, _ := strconv.Atoi(s)
	return v
}

func readCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true
	return r.ReadAll()
}

func headerIndex(headers []string) map[string]int {
	m := make(map[string]int, len(headers))
	for i, h := range headers {
		h = strings.TrimSpace(h)
		h = strings.TrimPrefix(h, "\xef\xbb\xbf")
		m[strings.ToLower(h)] = i
	}
	return m
}

func colStr(row []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func colInt(row []string, idx map[string]int, col string) int {
	return parseInt(colStr(row, idx, col))
}

// loadBrasileirao loads Brasileirao_Matches.csv
func loadBrasileirao(path string) ([]Match, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if len(rows) < 2 {
		return nil, nil
	}
	idx := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		dt, _ := parseDate(colStr(row, idx, "datetime"))
		m := Match{
			DateTime:    dt,
			HomeTeam:    normalize(colStr(row, idx, "home_team")),
			AwayTeam:    normalize(colStr(row, idx, "away_team")),
			HomeGoals:   colInt(row, idx, "home_goal"),
			AwayGoals:   colInt(row, idx, "away_goal"),
			Season:      colInt(row, idx, "season"),
			Competition: "Brasileirão Serie A",
			Round:       colStr(row, idx, "round"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadCopaDoBrasil loads Brazilian_Cup_Matches.csv
func loadCopaDoBrasil(path string) ([]Match, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if len(rows) < 2 {
		return nil, nil
	}
	idx := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		dt, _ := parseDate(colStr(row, idx, "datetime"))
		m := Match{
			DateTime:    dt,
			HomeTeam:    normalize(colStr(row, idx, "home_team")),
			AwayTeam:    normalize(colStr(row, idx, "away_team")),
			HomeGoals:   colInt(row, idx, "home_goal"),
			AwayGoals:   colInt(row, idx, "away_goal"),
			Season:      colInt(row, idx, "season"),
			Competition: "Copa do Brasil",
			Round:       colStr(row, idx, "round"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadLibertadores loads Libertadores_Matches.csv
func loadLibertadores(path string) ([]Match, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if len(rows) < 2 {
		return nil, nil
	}
	idx := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		dt, _ := parseDate(colStr(row, idx, "datetime"))
		m := Match{
			DateTime:    dt,
			HomeTeam:    normalize(colStr(row, idx, "home_team")),
			AwayTeam:    normalize(colStr(row, idx, "away_team")),
			HomeGoals:   colInt(row, idx, "home_goal"),
			AwayGoals:   colInt(row, idx, "away_goal"),
			Season:      colInt(row, idx, "season"),
			Competition: "Copa Libertadores",
			Stage:       colStr(row, idx, "stage"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadBRFootball loads BR-Football-Dataset.csv (extended stats)
func loadBRFootball(path string) ([]Match, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if len(rows) < 2 {
		return nil, nil
	}
	idx := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		dt, _ := parseDate(colStr(row, idx, "date"))
		season := 0
		if !dt.IsZero() {
			season = dt.Year()
		}
		m := Match{
			DateTime:    dt,
			HomeTeam:    normalize(colStr(row, idx, "home")),
			AwayTeam:    normalize(colStr(row, idx, "away")),
			HomeGoals:   colInt(row, idx, "home_goal"),
			AwayGoals:   colInt(row, idx, "away_goal"),
			Season:      season,
			Competition: colStr(row, idx, "tournament"),
			HomeCorners: colInt(row, idx, "home_corner"),
			AwayCorners: colInt(row, idx, "away_corner"),
			HomeAttacks: colInt(row, idx, "home_attack"),
			AwayAttacks: colInt(row, idx, "away_attack"),
			HomeShots:   colInt(row, idx, "home_shots"),
			AwayShots:   colInt(row, idx, "away_shots"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadHistorical loads novo_campeonato_brasileiro.csv
func loadHistorical(path string) ([]Match, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if len(rows) < 2 {
		return nil, nil
	}
	idx := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		dt, _ := parseDate(colStr(row, idx, "data"))
		m := Match{
			DateTime:    dt,
			HomeTeam:    normalize(colStr(row, idx, "equipe_mandante")),
			AwayTeam:    normalize(colStr(row, idx, "equipe_visitante")),
			HomeGoals:   colInt(row, idx, "gols_mandante"),
			AwayGoals:   colInt(row, idx, "gols_visitante"),
			Season:      colInt(row, idx, "ano"),
			Competition: "Brasileirão Serie A",
			Round:       colStr(row, idx, "rodada"),
			Arena:       colStr(row, idx, "arena"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// loadFIFA loads fifa_data.csv
func loadFIFA(path string) ([]Player, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := headerIndex(headers)

	var players []Player
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		p := Player{
			ID:          colStr(row, idx, "id"),
			Name:        colStr(row, idx, "name"),
			Age:         colInt(row, idx, "age"),
			Nationality: colStr(row, idx, "nationality"),
			Overall:     colInt(row, idx, "overall"),
			Potential:   colInt(row, idx, "potential"),
			Club:        colStr(row, idx, "club"),
			Position:    colStr(row, idx, "position"),
			JerseyNum:   colStr(row, idx, "jersey num"),
			Height:      colStr(row, idx, "height"),
			Weight:      colStr(row, idx, "weight"),
			Value:       colStr(row, idx, "value"),
			Wage:        colStr(row, idx, "wage"),
			Foot:        colStr(row, idx, "preferred foot"),
		}
		if p.Name != "" {
			players = append(players, p)
		}
	}
	return players, nil
}

// LoadDatabase loads all CSV files from the data directory.
func LoadDatabase(dataDir string) (*Database, error) {
	db := &Database{}

	type loader struct {
		file string
		fn   func(string) ([]Match, error)
	}
	matchLoaders := []loader{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCopaDoBrasil},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadBRFootball},
		{"novo_campeonato_brasileiro.csv", loadHistorical},
	}

	for _, l := range matchLoaders {
		path := filepath.Join(dataDir, l.file)
		matches, err := l.fn(path)
		if err != nil {
			return nil, fmt.Errorf("loading %s: %w", l.file, err)
		}
		db.Matches = append(db.Matches, matches...)
	}

	// Deduplicate matches: same date, home team, away team, and scores may appear in multiple files.
	db.Matches = deduplicateMatches(db.Matches)

	players, err := loadFIFA(filepath.Join(dataDir, "fifa_data.csv"))
	if err != nil {
		return nil, fmt.Errorf("loading fifa_data.csv: %w", err)
	}
	db.Players = players

	return db, nil
}

// deduplicateMatches removes exact-duplicate match records (same date, teams, goals).
func deduplicateMatches(matches []Match) []Match {
	seen := make(map[string]struct{}, len(matches))
	result := make([]Match, 0, len(matches))
	for _, m := range matches {
		dateStr := "?"
		if !m.DateTime.IsZero() {
			dateStr = m.DateTime.Format("2006-01-02")
		}
		key := fmt.Sprintf("%s|%s|%s|%d|%d",
			dateStr,
			normalizeLower(m.HomeTeam),
			normalizeLower(m.AwayTeam),
			m.HomeGoals,
			m.AwayGoals,
		)
		if _, ok := seen[key]; !ok {
			seen[key] = struct{}{}
			result = append(result, m)
		}
	}
	return result
}

// --- Query helpers ---

// FilterMatches returns matches where either team contains teamQuery (normalized).
// Competition matching is accent-insensitive (e.g. "brasileirao" matches "Brasileirão").
func (db *Database) FilterMatches(teamQuery, competition string, season int) []Match {
	var result []Match
	tq := normalizeForSearch(teamQuery)
	cq := normalizeForSearch(competition)
	for _, m := range db.Matches {
		if tq != "" {
			ht := normalizeForSearch(m.HomeTeam)
			at := normalizeForSearch(m.AwayTeam)
			if !strings.Contains(ht, tq) && !strings.Contains(at, tq) {
				continue
			}
		}
		if cq != "" && !strings.Contains(normalizeForSearch(m.Competition), cq) {
			continue
		}
		if season > 0 && m.Season != season {
			continue
		}
		result = append(result, m)
	}
	return result
}

// FilterMatchesH2H returns matches between two specific teams.
func (db *Database) FilterMatchesH2H(team1, team2 string) []Match {
	t1 := normalizeForSearch(team1)
	t2 := normalizeForSearch(team2)
	var result []Match
	for _, m := range db.Matches {
		ht := normalizeLower(m.HomeTeam)
		at := normalizeLower(m.AwayTeam)
		if (strings.Contains(ht, t1) && strings.Contains(at, t2)) ||
			(strings.Contains(ht, t2) && strings.Contains(at, t1)) {
			result = append(result, m)
		}
	}
	return result
}

// TeamRecord holds win/draw/loss stats for a team.
type TeamRecord struct {
	Team      string
	Wins      int
	Draws     int
	Losses    int
	GoalsFor  int
	GoalsAgainst int
	Matches   int
	Points    int
}

func (t *TeamRecord) WinRate() float64 {
	if t.Matches == 0 {
		return 0
	}
	return float64(t.Wins) / float64(t.Matches) * 100
}

// TeamStats calculates stats for a team across filtered matches.
func TeamStats(team string, matches []Match, homeOnly bool) TeamRecord {
	tq := strings.ToLower(strings.TrimSpace(team))
	rec := TeamRecord{Team: team}
	for _, m := range matches {
		ht := normalizeLower(m.HomeTeam)
		at := normalizeLower(m.AwayTeam)
		isHome := strings.Contains(ht, tq)
		isAway := strings.Contains(at, tq)
		if !isHome && !isAway {
			continue
		}
		if homeOnly && !isHome {
			continue
		}
		rec.Matches++
		if isHome {
			rec.GoalsFor += m.HomeGoals
			rec.GoalsAgainst += m.AwayGoals
			if m.HomeGoals > m.AwayGoals {
				rec.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				rec.Draws++
			} else {
				rec.Losses++
			}
		} else {
			rec.GoalsFor += m.AwayGoals
			rec.GoalsAgainst += m.HomeGoals
			if m.AwayGoals > m.HomeGoals {
				rec.Wins++
			} else if m.AwayGoals == m.HomeGoals {
				rec.Draws++
			} else {
				rec.Losses++
			}
		}
	}
	rec.Points = rec.Wins*3 + rec.Draws
	return rec
}

// Standings computes a table for a competition/season.
func (db *Database) Standings(competition string, season int) []TeamRecord {
	matches := db.FilterMatches("", competition, season)
	teams := make(map[string]*TeamRecord)
	for _, m := range matches {
		for _, t := range []string{m.HomeTeam, m.AwayTeam} {
			k := normalizeLower(t)
			if _, ok := teams[k]; !ok {
				teams[k] = &TeamRecord{Team: t}
			}
		}
		// home
		hk := normalizeLower(m.HomeTeam)
		ak := normalizeLower(m.AwayTeam)
		teams[hk].Matches++
		teams[hk].GoalsFor += m.HomeGoals
		teams[hk].GoalsAgainst += m.AwayGoals
		teams[ak].Matches++
		teams[ak].GoalsFor += m.AwayGoals
		teams[ak].GoalsAgainst += m.HomeGoals
		if m.HomeGoals > m.AwayGoals {
			teams[hk].Wins++
			teams[ak].Losses++
		} else if m.HomeGoals == m.AwayGoals {
			teams[hk].Draws++
			teams[ak].Draws++
		} else {
			teams[hk].Losses++
			teams[ak].Wins++
		}
	}
	result := make([]TeamRecord, 0, len(teams))
	for _, r := range teams {
		r.Points = r.Wins*3 + r.Draws
		result = append(result, *r)
	}
	sort.Slice(result, func(i, j int) bool {
		if result[i].Points != result[j].Points {
			return result[i].Points > result[j].Points
		}
		gdi := result[i].GoalsFor - result[i].GoalsAgainst
		gdj := result[j].GoalsFor - result[j].GoalsAgainst
		if gdi != gdj {
			return gdi > gdj
		}
		return result[i].GoalsFor > result[j].GoalsFor
	})
	return result
}

// BiggestWins returns top N matches by goal difference.
func (db *Database) BiggestWins(n int, competition string, season int) []Match {
	matches := db.FilterMatches("", competition, season)
	sort.Slice(matches, func(i, j int) bool {
		di := abs(matches[i].HomeGoals - matches[i].AwayGoals)
		dj := abs(matches[j].HomeGoals - matches[j].AwayGoals)
		return di > dj
	})
	if n > 0 && len(matches) > n {
		return matches[:n]
	}
	return matches
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// FilterPlayers returns players matching name/nationality/club/position queries.
func (db *Database) FilterPlayers(name, nationality, club, position string) []Player {
	nq := strings.ToLower(name)
	natq := strings.ToLower(nationality)
	cq := strings.ToLower(club)
	pq := strings.ToLower(position)
	var result []Player
	for _, p := range db.Players {
		if nq != "" && !strings.Contains(strings.ToLower(p.Name), nq) {
			continue
		}
		if natq != "" && !strings.Contains(strings.ToLower(p.Nationality), natq) {
			continue
		}
		if cq != "" && !strings.Contains(strings.ToLower(p.Club), cq) {
			continue
		}
		if pq != "" && !strings.Contains(strings.ToLower(p.Position), pq) {
			continue
		}
		result = append(result, p)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Overall > result[j].Overall
	})
	return result
}

// GoalsPerMatch returns average total goals per match across filtered matches.
func GoalsPerMatch(matches []Match) float64 {
	if len(matches) == 0 {
		return 0
	}
	total := 0
	for _, m := range matches {
		total += m.HomeGoals + m.AwayGoals
	}
	return float64(total) / float64(len(matches))
}

// HomeWinRate returns the fraction of matches where home team won.
func HomeWinRate(matches []Match) float64 {
	if len(matches) == 0 {
		return 0
	}
	wins := 0
	for _, m := range matches {
		if m.HomeGoals > m.AwayGoals {
			wins++
		}
	}
	return float64(wins) / float64(len(matches)) * 100
}

// AllTeams returns a sorted unique list of all team names.
func (db *Database) AllTeams() []string {
	seen := make(map[string]struct{})
	for _, m := range db.Matches {
		seen[m.HomeTeam] = struct{}{}
		seen[m.AwayTeam] = struct{}{}
	}
	teams := make([]string, 0, len(seen))
	for t := range seen {
		teams = append(teams, t)
	}
	sort.Strings(teams)
	return teams
}

// Seasons returns sorted unique seasons.
func (db *Database) Seasons(competition string) []int {
	seen := make(map[int]struct{})
	for _, m := range db.Matches {
		if competition == "" || strings.Contains(strings.ToLower(m.Competition), strings.ToLower(competition)) {
			if m.Season > 0 {
				seen[m.Season] = struct{}{}
			}
		}
	}
	seasons := make([]int, 0, len(seen))
	for s := range seen {
		seasons = append(seasons, s)
	}
	sort.Ints(seasons)
	return seasons
}

// TopScoringTeams returns teams sorted by total goals scored.
func (db *Database) TopScoringTeams(competition string, season int, n int) []TeamRecord {
	matches := db.FilterMatches("", competition, season)
	teams := make(map[string]*TeamRecord)
	for _, m := range matches {
		for _, t := range []string{m.HomeTeam, m.AwayTeam} {
			k := normalizeLower(t)
			if _, ok := teams[k]; !ok {
				teams[k] = &TeamRecord{Team: t}
			}
		}
		hk := normalizeLower(m.HomeTeam)
		ak := normalizeLower(m.AwayTeam)
		teams[hk].GoalsFor += m.HomeGoals
		teams[hk].GoalsAgainst += m.AwayGoals
		teams[hk].Matches++
		teams[ak].GoalsFor += m.AwayGoals
		teams[ak].GoalsAgainst += m.HomeGoals
		teams[ak].Matches++
		if m.HomeGoals > m.AwayGoals {
			teams[hk].Wins++
			teams[ak].Losses++
		} else if m.HomeGoals == m.AwayGoals {
			teams[hk].Draws++
			teams[ak].Draws++
		} else {
			teams[hk].Losses++
			teams[ak].Wins++
		}
	}
	result := make([]TeamRecord, 0, len(teams))
	for _, r := range teams {
		r.Points = r.Wins*3 + r.Draws
		result = append(result, *r)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].GoalsFor > result[j].GoalsFor
	})
	if n > 0 && len(result) > n {
		return result[:n]
	}
	return result
}
