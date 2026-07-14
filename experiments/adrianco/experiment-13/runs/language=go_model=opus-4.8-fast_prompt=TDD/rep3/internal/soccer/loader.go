// Context: Brazilian Soccer MCP Server.
// File: loader.go
// Purpose: Parse each of the six provided CSV layouts into the common Match /
// Player model and assemble an in-memory DB. Each source has its own column
// layout, date format and naming conventions, so there is one parser per file
// plus shared helpers for dates and numeric fields.
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

// dateLayouts are tried in order by parseDate.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006 15:04",
}

// ParseDate parses a date string in any of the supported formats. Exported
// for use by the server layer when interpreting client-supplied dates.
func ParseDate(s string) (time.Time, bool) { return parseDate(s) }

// parseDate parses a date string in any of the supported formats.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// Atoi parses an integer, tolerating surrounding whitespace and a trailing
// ".0" float form (e.g. "3.0"). Returns 0 on failure. Exported for use by
// argument-coercion helpers in the server layer.
func Atoi(s string) int { return atoi(s) }

// atoi parses an integer, tolerating surrounding whitespace and a trailing
// ".0" float form (e.g. "3.0"). Returns 0 on failure.
func atoi(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

// newReader returns a csv.Reader tolerant of variable field counts.
func newReader(r io.Reader) *csv.Reader {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1
	cr.LazyQuotes = true
	return cr
}

// headerIndex maps lowercased, trimmed, BOM-stripped header names to column
// indexes for resilient column lookup.
func headerIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		key := strings.ToLower(strings.TrimSpace(strings.TrimPrefix(h, "\ufeff")))
		idx[key] = i
	}
	return idx
}

func get(row []string, i int) string {
	if i < 0 || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// field looks up a column by header name, returning "" when the column is
// absent. This avoids the trap where a missing map key yields index 0 and
// silently reads the wrong column.
func field(row []string, idx map[string]int, key string) string {
	i, ok := idx[key]
	if !ok {
		return ""
	}
	return get(row, i)
}

func parseBrasileirao(r io.Reader) ([]Match, error) {
	return parseStandardMatches(r, CompBrasileirao, "Brasileirao_Matches.csv")
}

// parseStandardMatches handles the shared layout of the Brasileirão,
// Copa do Brasil and Libertadores files (datetime/home/away/goals/season with
// optional round and stage columns).
func parseStandardMatches(r io.Reader, competition, source string) ([]Match, error) {
	cr := newReader(r)
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, nil
	}
	h := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		home := field(row, h, "home_team")
		away := field(row, h, "away_team")
		if home == "" && away == "" {
			continue
		}
		m := Match{
			Competition: competition,
			Season:      atoi(field(row, h, "season")),
			Round:       field(row, h, "round"),
			Stage:       field(row, h, "stage"),
			HomeRaw:     home,
			AwayRaw:     away,
			HomeTeam:    CanonicalName(home),
			AwayTeam:    CanonicalName(away),
			Source:      source,
		}
		hg := field(row, h, "home_goal")
		ag := field(row, h, "away_goal")
		if hg != "" && ag != "" {
			m.HomeGoals = atoi(hg)
			m.AwayGoals = atoi(ag)
			m.HasScore = true
		}
		if d, ok := parseDate(field(row, h, "datetime")); ok {
			m.Date = d
			m.HasDate = true
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func parseCup(r io.Reader) ([]Match, error) {
	return parseStandardMatches(r, CompCopaDoBrasil, "Brazilian_Cup_Matches.csv")
}

func parseLibertadores(r io.Reader) ([]Match, error) {
	return parseStandardMatches(r, CompLibertadores, "Libertadores_Matches.csv")
}

// parseBRFootball handles the extended-statistics dataset, whose competition
// label lives in the "tournament" column and whose goals are floats.
func parseBRFootball(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, nil
	}
	h := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		home := field(row, h, "home")
		away := field(row, h, "away")
		if home == "" && away == "" {
			continue
		}
		m := Match{
			Competition: canonicalBRCompetition(field(row, h, "tournament")),
			HomeRaw:     home,
			AwayRaw:     away,
			HomeTeam:    CanonicalName(home),
			AwayTeam:    CanonicalName(away),
			HomeGoals:   atoi(field(row, h, "home_goal")),
			AwayGoals:   atoi(field(row, h, "away_goal")),
			HasScore:    true,
			Source:      "BR-Football-Dataset.csv",
		}
		if d, ok := parseDate(field(row, h, "date")); ok {
			m.Date = d
			m.HasDate = true
			m.Season = d.Year()
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// parseNovo handles the historical Brasileirão (2003-2019) dataset, which uses
// Portuguese column names and DD/MM/YYYY dates.
func parseNovo(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, nil
	}
	h := headerIndex(rows[0])
	var matches []Match
	for _, row := range rows[1:] {
		home := field(row, h, "equipe_mandante")
		away := field(row, h, "equipe_visitante")
		if home == "" && away == "" {
			continue
		}
		m := Match{
			Competition: CompBrasileirao,
			Season:      atoi(field(row, h, "ano")),
			Round:       field(row, h, "rodada"),
			HomeRaw:     home,
			AwayRaw:     away,
			HomeTeam:    CanonicalName(home),
			AwayTeam:    CanonicalName(away),
			HomeGoals:   atoi(field(row, h, "gols_mandante")),
			AwayGoals:   atoi(field(row, h, "gols_visitante")),
			HasScore:    true,
			Source:      "novo_campeonato_brasileiro.csv",
		}
		if d, ok := parseDate(field(row, h, "data")); ok {
			m.Date = d
			m.HasDate = true
		}
		matches = append(matches, m)
	}
	return matches, nil
}

// parsePlayers handles the FIFA player database.
func parsePlayers(r io.Reader) ([]Player, error) {
	cr := newReader(r)
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, nil
	}
	h := headerIndex(rows[0])
	var players []Player
	for _, row := range rows[1:] {
		name := field(row, h, "name")
		if name == "" {
			continue
		}
		players = append(players, Player{
			ID:          atoi(field(row, h, "id")),
			Name:        name,
			Age:         atoi(field(row, h, "age")),
			Nationality: field(row, h, "nationality"),
			Overall:     atoi(field(row, h, "overall")),
			Potential:   atoi(field(row, h, "potential")),
			Club:        field(row, h, "club"),
			Position:    field(row, h, "position"),
		})
	}
	return players, nil
}

// DB is the in-memory knowledge base: all matches and players.
type DB struct {
	Matches []Match
	Players []Player
}

// fileParser pairs a CSV filename with its parser.
type fileParser struct {
	file  string
	parse func(io.Reader) ([]Match, error)
}

// Load reads all six datasets from dir (e.g. "data/kaggle") into a DB.
func Load(dir string) (*DB, error) {
	db := &DB{}
	matchFiles := []fileParser{
		{"Brasileirao_Matches.csv", parseBrasileirao},
		{"Brazilian_Cup_Matches.csv", parseCup},
		{"Libertadores_Matches.csv", parseLibertadores},
		{"BR-Football-Dataset.csv", parseBRFootball},
		{"novo_campeonato_brasileiro.csv", parseNovo},
	}
	for _, fp := range matchFiles {
		matches, err := loadMatchFile(filepath.Join(dir, fp.file), fp.parse)
		if err != nil {
			return nil, fmt.Errorf("loading %s: %w", fp.file, err)
		}
		db.Matches = append(db.Matches, matches...)
	}
	// Collapse the same fixture appearing across overlapping source files.
	db.Matches = dedupeMatches(db.Matches)
	players, err := loadPlayerFile(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, fmt.Errorf("loading fifa_data.csv: %w", err)
	}
	db.Players = players
	return db, nil
}

func loadMatchFile(path string, parse func(io.Reader) ([]Match, error)) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return parse(f)
}

func loadPlayerFile(path string) ([]Player, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return parsePlayers(f)
}
