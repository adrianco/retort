package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// The loader turns the six heterogeneous CSV files into a single slice of
// Match values plus a slice of Player values. Each source file has its own
// column layout, date format and goal encoding, so there is one small parser
// per file. Parsing is intentionally lenient: a malformed individual row is
// skipped rather than failing the whole load, because these are real-world
// scraped datasets.

// Canonical CSV file names expected inside the data directory.
const (
	FileBrasileirao  = "Brasileirao_Matches.csv"
	FileCopaBrasil   = "Brazilian_Cup_Matches.csv"
	FileLibertadores = "Libertadores_Matches.csv"
	FileBRFootball   = "BR-Football-Dataset.csv"
	FileNovoBR       = "novo_campeonato_brasileiro.csv"
	FileFifa         = "fifa_data.csv"
)

// dateLayouts are tried in order against a raw date cell.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006.01.02",
}

// parseDate best-effort parses the many date formats present in the datasets.
func parseDate(raw string) time.Time {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return time.Time{}
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, raw); err == nil {
			return t
		}
	}
	return time.Time{}
}

// parseGoals parses a goal count that may be an int ("2"), a float ("2.0") or
// blank. It returns -1 for an unparseable/blank value.
func parseGoals(raw string) int {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return -1
	}
	if n, err := strconv.Atoi(raw); err == nil {
		return n
	}
	if f, err := strconv.ParseFloat(raw, 64); err == nil {
		return int(math.Round(f))
	}
	return -1
}

func parseInt(raw string) int {
	raw = strings.TrimSpace(raw)
	if n, err := strconv.Atoi(raw); err == nil {
		return n
	}
	if f, err := strconv.ParseFloat(raw, 64); err == nil {
		return int(math.Round(f))
	}
	return 0
}

// newReader returns a CSV reader tolerant of ragged rows.
func newReader(r io.Reader) *csv.Reader {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1 // allow variable column counts
	cr.LazyQuotes = true
	return cr
}

// headerIndex maps column names (case-insensitive, BOM-stripped) to indices.
func headerIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimPrefix(h, "\uFEFF") // strip UTF-8 BOM on first column
		idx[strings.TrimSpace(strings.ToLower(h))] = i
	}
	return idx
}

func at(row []string, i int) string {
	if i < 0 || i >= len(row) {
		return ""
	}
	return row[i]
}

// field returns the value of a named column, or "" if the column is absent from
// this file. This matters because a bare map lookup for a missing key yields 0,
// which would silently read the first column (e.g. reading the datetime as the
// stage for files that have no stage column).
func field(h map[string]int, row []string, name string) string {
	i, ok := h[name]
	if !ok {
		return ""
	}
	return at(row, i)
}

func makeMatch(comp, home, away string, hg, ag, season int, round, stage, source string, date time.Time) Match {
	return Match{
		Competition: comp,
		Season:      season,
		Round:       round,
		Stage:       stage,
		Date:        date,
		HomeTeam:    CleanTeam(home),
		AwayTeam:    CleanTeam(away),
		HomeKey:     NormalizeTeam(home),
		AwayKey:     NormalizeTeam(away),
		HomeGoals:   hg,
		AwayGoals:   ag,
		HomeShots:   -1,
		AwayShots:   -1,
		HomeCorners: -1,
		AwayCorners: -1,
		Source:      source,
	}
}

// yearFrom returns the season year, preferring an explicit value and falling
// back to the match date's year.
func yearFrom(explicit string, date time.Time) int {
	if n := parseInt(explicit); n > 0 {
		return n
	}
	if !date.IsZero() {
		return date.Year()
	}
	return 0
}

// loadSimpleMatches parses the Brasileirão/Copa/Libertadores family, which all
// share a datetime + home/away + goals + season shape and differ only in a few
// columns. competition names the output; stageCol names the stage column (may
// be empty).
func loadSimpleMatches(r io.Reader, competition, source string) ([]Match, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	h := headerIndex(header)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue // skip malformed row
		}
		date := parseDate(field(h, row, "datetime"))
		m := makeMatch(
			competition,
			field(h, row, "home_team"),
			field(h, row, "away_team"),
			parseGoals(field(h, row, "home_goal")),
			parseGoals(field(h, row, "away_goal")),
			yearFrom(field(h, row, "season"), date),
			strings.TrimSpace(field(h, row, "round")),
			strings.TrimSpace(field(h, row, "stage")),
			source,
			date,
		)
		if m.HomeKey == "" && m.AwayKey == "" {
			continue
		}
		out = append(out, m)
	}
	return out, nil
}

// loadBRFootball parses the extended-statistics dataset.
func loadBRFootball(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	h := headerIndex(header)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		date := parseDate(field(h, row, "date"))
		comp := canonicalCompetition(strings.TrimSpace(field(h, row, "tournament")))
		m := makeMatch(
			comp,
			field(h, row, "home"),
			field(h, row, "away"),
			parseGoals(field(h, row, "home_goal")),
			parseGoals(field(h, row, "away_goal")),
			yearFrom("", date),
			"",
			"",
			FileBRFootball,
			date,
		)
		m.HomeShots = parseGoals(field(h, row, "home_shots"))
		m.AwayShots = parseGoals(field(h, row, "away_shots"))
		m.HomeCorners = parseGoals(field(h, row, "home_corner"))
		m.AwayCorners = parseGoals(field(h, row, "away_corner"))
		if m.HomeKey == "" && m.AwayKey == "" {
			continue
		}
		out = append(out, m)
	}
	return out, nil
}

// loadNovoBR parses the historical 2003-2019 Brasileirão dataset (Portuguese
// column names, DD/MM/YYYY dates).
func loadNovoBR(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	h := headerIndex(header)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		date := parseDate(field(h, row, "data"))
		m := makeMatch(
			CompBrasileirao,
			field(h, row, "equipe_mandante"),
			field(h, row, "equipe_visitante"),
			parseGoals(field(h, row, "gols_mandante")),
			parseGoals(field(h, row, "gols_visitante")),
			yearFrom(field(h, row, "ano"), date),
			strings.TrimSpace(field(h, row, "rodada")),
			"",
			FileNovoBR,
			date,
		)
		if m.HomeKey == "" && m.AwayKey == "" {
			continue
		}
		out = append(out, m)
	}
	return out, nil
}

// canonicalCompetition maps the free-text tournament labels in the BR-Football
// dataset onto canonical competition names where possible.
func canonicalCompetition(name string) string {
	switch strings.ToLower(strings.TrimSpace(name)) {
	case "serie a", "série a", "brasileirao", "brasileirão":
		return CompBrasileirao
	case "copa do brasil":
		return CompCopaBrasil
	case "libertadores", "copa libertadores":
		return CompLibertadores
	case "":
		return "Unknown"
	default:
		return name
	}
}

// loadPlayers parses the FIFA player database.
func loadPlayers(r io.Reader) ([]Player, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	h := headerIndex(header)
	var out []Player
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		name := strings.TrimSpace(field(h, row, "name"))
		if name == "" {
			continue
		}
		club := strings.TrimSpace(field(h, row, "club"))
		out = append(out, Player{
			ID:          parseInt(field(h, row, "id")),
			Name:        name,
			NameKey:     NormalizeName(name),
			Age:         parseInt(field(h, row, "age")),
			Nationality: strings.TrimSpace(field(h, row, "nationality")),
			Overall:     parseInt(field(h, row, "overall")),
			Potential:   parseInt(field(h, row, "potential")),
			Club:        club,
			ClubKey:     NormalizeTeam(club),
			Position:    strings.TrimSpace(field(h, row, "position")),
			Jersey:      parseInt(field(h, row, "jersey number")),
			Height:      strings.TrimSpace(field(h, row, "height")),
			Weight:      strings.TrimSpace(field(h, row, "weight")),
		})
	}
	return out, nil
}

// LoadDir loads all six datasets from dir and returns a populated Store.
// Missing files are skipped with a note in the returned Store's Warnings, so a
// partial dataset still yields a usable server.
func LoadDir(dir string) (*Store, error) {
	s := NewStore()

	type matchFile struct {
		name string
		fn   func(io.Reader) ([]Match, error)
	}
	matchFiles := []matchFile{
		{FileBrasileirao, func(r io.Reader) ([]Match, error) {
			return loadSimpleMatches(r, CompBrasileirao, FileBrasileirao)
		}},
		{FileCopaBrasil, func(r io.Reader) ([]Match, error) {
			return loadSimpleMatches(r, CompCopaBrasil, FileCopaBrasil)
		}},
		{FileLibertadores, func(r io.Reader) ([]Match, error) {
			return loadSimpleMatches(r, CompLibertadores, FileLibertadores)
		}},
		{FileNovoBR, loadNovoBR},
		// BR-Football is loaded last: it has inconsistent naming and dates, so
		// during deduplication its rows are merged into the cleaner league
		// records (which are kept) rather than the other way around.
		{FileBRFootball, loadBRFootball},
	}

	for _, mf := range matchFiles {
		path := filepath.Join(dir, mf.name)
		f, err := os.Open(path)
		if err != nil {
			s.Warnings = append(s.Warnings, fmt.Sprintf("skipped %s: %v", mf.name, err))
			continue
		}
		matches, err := mf.fn(f)
		f.Close()
		if err != nil {
			s.Warnings = append(s.Warnings, fmt.Sprintf("error parsing %s: %v", mf.name, err))
			continue
		}
		s.AddMatches(matches)
	}

	// Players.
	path := filepath.Join(dir, FileFifa)
	if f, err := os.Open(path); err != nil {
		s.Warnings = append(s.Warnings, fmt.Sprintf("skipped %s: %v", FileFifa, err))
	} else {
		players, perr := loadPlayers(f)
		f.Close()
		if perr != nil {
			s.Warnings = append(s.Warnings, fmt.Sprintf("error parsing %s: %v", FileFifa, perr))
		} else {
			s.AddPlayers(players)
		}
	}

	s.Index()
	return s, nil
}
