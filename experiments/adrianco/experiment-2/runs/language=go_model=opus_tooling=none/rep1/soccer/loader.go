package soccer

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

type Match struct {
	Date        time.Time
	HomeTeam    string
	AwayTeam    string
	HomeGoal    int
	AwayGoal    int
	Season      int
	Round       string
	Competition string
	Stage       string
	Arena       string
}

type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber string
	Height       string
	Weight       string
}

type DB struct {
	Matches []Match
	Players []Player
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	// handle floats like "1.0"
	if i := strings.Index(s, "."); i >= 0 {
		s = s[:i]
	}
	n, _ := strconv.Atoi(s)
	return n
}

func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	layouts := []string{
		"2006-01-02 15:04:05",
		"2006-01-02",
		"02/01/2006",
		"2006/01/02",
	}
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// NormalizeTeam lower-cases and strips club prefixes, preserving any 2-letter
// state suffix (e.g. "-sp") so that "Atletico-MG" and "Atletico-PR" remain
// distinct keys.
func NormalizeTeam(name string) string {
	n := strings.ToLower(strings.TrimSpace(name))
	// strip parenthetical country like " (uru)"
	if i := strings.Index(n, "("); i >= 0 {
		n = strings.TrimSpace(n[:i])
	}
	// remove common club prefixes/words
	for _, w := range []string{"sport club ", "esporte clube ", "clube de regatas do ", "clube ", "sociedade esportiva "} {
		n = strings.TrimPrefix(n, w)
	}
	n = stripDiacritics(n)
	// normalise whitespace
	n = strings.Join(strings.Fields(n), " ")
	return n
}

// teamBase returns the team name without any trailing "-XX" state or country
// suffix. Useful for loose matching when a user types just "Flamengo".
func teamBase(n string) string {
	if i := strings.LastIndex(n, "-"); i >= 0 {
		suf := strings.TrimSpace(n[i+1:])
		if len(suf) == 2 {
			return strings.TrimSpace(n[:i])
		}
	}
	return n
}

// TeamMatches reports whether a stored team name matches a user-provided query.
// Match is true when both normalised names are equal or when the query has no
// state suffix and equals the stored name's base.
func TeamMatches(query, stored string) bool {
	q := NormalizeTeam(query)
	s := NormalizeTeam(stored)
	if q == s {
		return true
	}
	qBase, sBase := teamBase(q), teamBase(s)
	// If the query lacks a state suffix, match on base.
	if q == qBase {
		return q == sBase
	}
	return false
}

func stripDiacritics(s string) string {
	replacements := map[rune]rune{
		'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
		'é': 'e', 'ê': 'e', 'è': 'e', 'ë': 'e',
		'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
		'ó': 'o', 'õ': 'o', 'ô': 'o', 'ò': 'o', 'ö': 'o',
		'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
		'ç': 'c', 'ñ': 'n',
	}
	var b strings.Builder
	for _, r := range s {
		if v, ok := replacements[r]; ok {
			b.WriteRune(v)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

func readCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	var rows [][]string
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return rows, err
		}
		rows = append(rows, rec)
	}
	return rows, nil
}

func headerIndex(header []string) map[string]int {
	m := make(map[string]int, len(header))
	for i, h := range header {
		m[strings.TrimSpace(strings.ToLower(strings.Trim(h, "\ufeff")))] = i
	}
	return m
}

func get(row []string, idx map[string]int, key string) string {
	if i, ok := idx[strings.ToLower(key)]; ok && i < len(row) {
		return row[i]
	}
	return ""
}

// LoadAll loads every CSV under dataDir (expects kaggle layout).
func LoadAll(dataDir string) (*DB, error) {
	db := &DB{}
	files := []struct {
		name string
		comp string
		fn   func(*DB, [][]string, string)
	}{
		{"Brasileirao_Matches.csv", "Brasileirão Serie A", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", "Copa do Brasil", loadCup},
		{"Libertadores_Matches.csv", "Copa Libertadores", loadLibertadores},
		{"BR-Football-Dataset.csv", "", loadBRFootball},
		{"novo_campeonato_brasileiro.csv", "Brasileirão (historical)", loadNovo},
	}
	for _, f := range files {
		path := filepath.Join(dataDir, f.name)
		if _, err := os.Stat(path); err != nil {
			continue
		}
		rows, err := readCSV(path)
		if err != nil {
			return db, fmt.Errorf("read %s: %w", f.name, err)
		}
		if len(rows) < 2 {
			continue
		}
		f.fn(db, rows, f.comp)
	}
	playersPath := filepath.Join(dataDir, "fifa_data.csv")
	if _, err := os.Stat(playersPath); err == nil {
		rows, err := readCSV(playersPath)
		if err != nil {
			return db, err
		}
		loadPlayers(db, rows)
	}
	return db, nil
}

func loadBrasileirao(db *DB, rows [][]string, comp string) {
	idx := headerIndex(rows[0])
	for _, r := range rows[1:] {
		m := Match{
			Date:        parseDate(get(r, idx, "datetime")),
			HomeTeam:    get(r, idx, "home_team"),
			AwayTeam:    get(r, idx, "away_team"),
			HomeGoal:    parseInt(get(r, idx, "home_goal")),
			AwayGoal:    parseInt(get(r, idx, "away_goal")),
			Season:      parseInt(get(r, idx, "season")),
			Round:       get(r, idx, "round"),
			Competition: comp,
		}
		db.Matches = append(db.Matches, m)
	}
}

func loadCup(db *DB, rows [][]string, comp string) {
	idx := headerIndex(rows[0])
	for _, r := range rows[1:] {
		m := Match{
			Date:        parseDate(get(r, idx, "datetime")),
			HomeTeam:    get(r, idx, "home_team"),
			AwayTeam:    get(r, idx, "away_team"),
			HomeGoal:    parseInt(get(r, idx, "home_goal")),
			AwayGoal:    parseInt(get(r, idx, "away_goal")),
			Season:      parseInt(get(r, idx, "season")),
			Round:       get(r, idx, "round"),
			Competition: comp,
		}
		db.Matches = append(db.Matches, m)
	}
}

func loadLibertadores(db *DB, rows [][]string, comp string) {
	idx := headerIndex(rows[0])
	for _, r := range rows[1:] {
		m := Match{
			Date:        parseDate(get(r, idx, "datetime")),
			HomeTeam:    get(r, idx, "home_team"),
			AwayTeam:    get(r, idx, "away_team"),
			HomeGoal:    parseInt(get(r, idx, "home_goal")),
			AwayGoal:    parseInt(get(r, idx, "away_goal")),
			Season:      parseInt(get(r, idx, "season")),
			Stage:       get(r, idx, "stage"),
			Competition: comp,
		}
		db.Matches = append(db.Matches, m)
	}
}

func loadBRFootball(db *DB, rows [][]string, comp string) {
	idx := headerIndex(rows[0])
	for _, r := range rows[1:] {
		t := parseDate(get(r, idx, "date"))
		m := Match{
			Date:        t,
			HomeTeam:    get(r, idx, "home"),
			AwayTeam:    get(r, idx, "away"),
			HomeGoal:    parseInt(get(r, idx, "home_goal")),
			AwayGoal:    parseInt(get(r, idx, "away_goal")),
			Season:      t.Year(),
			Competition: get(r, idx, "tournament"),
		}
		db.Matches = append(db.Matches, m)
	}
}

func loadNovo(db *DB, rows [][]string, comp string) {
	idx := headerIndex(rows[0])
	for _, r := range rows[1:] {
		m := Match{
			Date:        parseDate(get(r, idx, "data")),
			HomeTeam:    get(r, idx, "equipe_mandante"),
			AwayTeam:    get(r, idx, "equipe_visitante"),
			HomeGoal:    parseInt(get(r, idx, "gols_mandante")),
			AwayGoal:    parseInt(get(r, idx, "gols_visitante")),
			Season:      parseInt(get(r, idx, "ano")),
			Round:       get(r, idx, "rodada"),
			Competition: comp,
			Arena:       get(r, idx, "arena"),
		}
		db.Matches = append(db.Matches, m)
	}
}

func loadPlayers(db *DB, rows [][]string) {
	idx := headerIndex(rows[0])
	for _, r := range rows[1:] {
		p := Player{
			ID:           parseInt(get(r, idx, "id")),
			Name:         get(r, idx, "name"),
			Age:          parseInt(get(r, idx, "age")),
			Nationality:  get(r, idx, "nationality"),
			Overall:      parseInt(get(r, idx, "overall")),
			Potential:    parseInt(get(r, idx, "potential")),
			Club:         get(r, idx, "club"),
			Position:     get(r, idx, "position"),
			JerseyNumber: get(r, idx, "jersey number"),
			Height:       get(r, idx, "height"),
			Weight:       get(r, idx, "weight"),
		}
		db.Players = append(db.Players, p)
	}
}
