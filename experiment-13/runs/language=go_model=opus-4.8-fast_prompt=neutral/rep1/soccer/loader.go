// loader.go: CSV ingestion. Each of the six datasets has its own column layout,
// date format and naming convention; the per-file loaders below normalize all
// of them into the unified Match / Player models. The loaders are tolerant:
// rows with unparseable essential fields are skipped rather than aborting the
// whole load, so a few malformed lines never take the server down.
package soccer

import (
	"encoding/csv"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// dateLayouts are tried in order when parsing a date/time string.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"02/01/2006 15:04:05",
	"01/02/2006", // last resort
}

// parseDate parses one of the several date formats found in the datasets.
// The second return reports whether a meaningful time-of-day was present.
func parseDate(s string) (time.Time, bool, bool) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "NA") {
		return time.Time{}, false, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			hasTime := strings.ContainsAny(layout, "H") || strings.Contains(layout, "15")
			return t, hasTime && !(t.Hour() == 0 && t.Minute() == 0 && t.Second() == 0), true
		}
	}
	return time.Time{}, false, false
}

// atoiLoose parses an integer that may be quoted, blank, or expressed as a
// float ("1.0"). Returns ok=false when no number can be read.
func atoiLoose(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "NA") {
		return 0, false
	}
	if n, err := strconv.Atoi(s); err == nil {
		return n, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f + 0.5), true
	}
	return 0, false
}

// newReader returns a lenient CSV reader (variable field counts, lazy quotes).
func newReader(r io.Reader) *csv.Reader {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1
	cr.LazyQuotes = true
	cr.TrimLeadingSpace = false
	return cr
}

// stripBOM removes a leading UTF-8 byte-order mark from a header field.
func stripBOM(s string) string {
	return strings.TrimPrefix(s, "\ufeff")
}

// LoadAll loads every dataset found under dir into a fresh Store. Missing files
// are skipped (with the names returned in the report) so the server can still
// start with a partial dataset. The returned LoadReport summarizes what loaded.
func LoadAll(dir string) (*Store, *LoadReport, error) {
	s := newStore()
	rep := &LoadReport{}

	type job struct {
		file string
		fn   func(*Store, io.Reader) (int, error)
	}
	jobs := []job{
		{"Brasileirao_Matches.csv", (*Store).loadBrasileirao},
		{"novo_campeonato_brasileiro.csv", (*Store).loadNovoCampeonato},
		{"Brazilian_Cup_Matches.csv", (*Store).loadCopaBrasil},
		{"Libertadores_Matches.csv", (*Store).loadLibertadores},
		{"BR-Football-Dataset.csv", (*Store).loadBRFootball},
		{"fifa_data.csv", (*Store).loadFIFA},
	}

	for _, j := range jobs {
		path := filepath.Join(dir, j.file)
		f, err := os.Open(path)
		if err != nil {
			rep.Missing = append(rep.Missing, j.file)
			continue
		}
		n, err := j.fn(s, f)
		f.Close()
		if err != nil {
			return nil, nil, err
		}
		rep.Files = append(rep.Files, FileReport{File: j.file, Rows: n})
	}

	s.finalize()
	rep.Matches = len(s.Matches)
	rep.Players = len(s.Players)
	rep.Duplicates = s.duplicates
	return s, rep, nil
}

// LoadReport summarizes a LoadAll call.
type LoadReport struct {
	Files      []FileReport
	Missing    []string
	Matches    int
	Players    int
	Duplicates int
}

// FileReport records how many records a single file contributed.
type FileReport struct {
	File string
	Rows int
}

// --- per-file loaders -------------------------------------------------------

func (s *Store) loadBrasileirao(r io.Reader) (int, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return 0, err
	}
	col := indexHeader(header)
	n := 0
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		hg, ok1 := atoiLoose(get(rec, col, "home_goal"))
		ag, ok2 := atoiLoose(get(rec, col, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		t, ht, _ := parseDate(get(rec, col, "datetime"))
		season, _ := atoiLoose(get(rec, col, "season"))
		m := Match{
			Competition: CompSerieA,
			Date:        t,
			HasTime:     ht,
			Season:      season,
			Round:       strings.TrimSpace(get(rec, col, "round")),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Source:      "Brasileirao_Matches.csv",
		}
		s.addMatch(&m, get(rec, col, "home_team"), get(rec, col, "away_team"))
		n++
	}
	return n, nil
}

func (s *Store) loadNovoCampeonato(r io.Reader) (int, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return 0, err
	}
	col := indexHeader(header)
	n := 0
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		hg, ok1 := atoiLoose(get(rec, col, "Gols_mandante"))
		ag, ok2 := atoiLoose(get(rec, col, "Gols_visitante"))
		if !ok1 || !ok2 {
			continue
		}
		t, ht, _ := parseDate(get(rec, col, "Data"))
		season, _ := atoiLoose(get(rec, col, "Ano"))
		m := Match{
			Competition: CompSerieA,
			Date:        t,
			HasTime:     ht,
			Season:      season,
			Round:       strings.TrimSpace(get(rec, col, "Rodada")),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Stadium:     strings.TrimSpace(get(rec, col, "Arena")),
			Source:      "novo_campeonato_brasileiro.csv",
		}
		s.addMatch(&m, get(rec, col, "Equipe_mandante"), get(rec, col, "Equipe_visitante"))
		n++
	}
	return n, nil
}

func (s *Store) loadCopaBrasil(r io.Reader) (int, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return 0, err
	}
	col := indexHeader(header)
	n := 0
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		hg, ok1 := atoiLoose(get(rec, col, "home_goal"))
		ag, ok2 := atoiLoose(get(rec, col, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		t, ht, _ := parseDate(get(rec, col, "datetime"))
		season, _ := atoiLoose(get(rec, col, "season"))
		m := Match{
			Competition: CompCopaBrasil,
			Date:        t,
			HasTime:     ht,
			Season:      season,
			Round:       strings.TrimSpace(get(rec, col, "round")),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Source:      "Brazilian_Cup_Matches.csv",
		}
		s.addMatch(&m, get(rec, col, "home_team"), get(rec, col, "away_team"))
		n++
	}
	return n, nil
}

func (s *Store) loadLibertadores(r io.Reader) (int, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return 0, err
	}
	col := indexHeader(header)
	n := 0
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		hg, ok1 := atoiLoose(get(rec, col, "home_goal"))
		ag, ok2 := atoiLoose(get(rec, col, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		t, ht, _ := parseDate(get(rec, col, "datetime"))
		season, _ := atoiLoose(get(rec, col, "season"))
		m := Match{
			Competition: CompLibertadores,
			Date:        t,
			HasTime:     ht,
			Season:      season,
			Stage:       strings.TrimSpace(get(rec, col, "stage")),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Source:      "Libertadores_Matches.csv",
		}
		s.addMatch(&m, get(rec, col, "home_team"), get(rec, col, "away_team"))
		n++
	}
	return n, nil
}

func (s *Store) loadBRFootball(r io.Reader) (int, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return 0, err
	}
	col := indexHeader(header)
	n := 0
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		hg, ok1 := atoiLoose(get(rec, col, "home_goal"))
		ag, ok2 := atoiLoose(get(rec, col, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		date := get(rec, col, "date")
		tm := get(rec, col, "time")
		if tm != "" && !strings.EqualFold(strings.TrimSpace(tm), "NA") {
			date = strings.TrimSpace(date) + " " + strings.TrimSpace(tm)
		}
		t, ht, _ := parseDate(date)
		season := 0
		if !t.IsZero() {
			season = t.Year()
		}
		m := Match{
			Competition: mapTournament(get(rec, col, "tournament")),
			Date:        t,
			HasTime:     ht,
			Season:      season,
			HomeGoals:   hg,
			AwayGoals:   ag,
			Source:      "BR-Football-Dataset.csv",
			HasStats:    true,
		}
		m.HomeShots, _ = atoiLoose(get(rec, col, "home_shots"))
		m.AwayShots, _ = atoiLoose(get(rec, col, "away_shots"))
		m.HomeCorners, _ = atoiLoose(get(rec, col, "home_corner"))
		m.AwayCorners, _ = atoiLoose(get(rec, col, "away_corner"))
		s.addMatch(&m, get(rec, col, "home"), get(rec, col, "away"))
		n++
	}
	return n, nil
}

// mapTournament maps a BR-Football tournament label to a canonical competition.
func mapTournament(t string) string {
	switch strings.ToLower(strings.TrimSpace(t)) {
	case "serie a", "série a":
		return CompSerieA
	case "serie b", "série b":
		return CompSerieB
	case "serie c", "série c":
		return CompSerieC
	case "copa do brasil":
		return CompCopaBrasil
	default:
		return strings.TrimSpace(t)
	}
}

func (s *Store) loadFIFA(r io.Reader) (int, error) {
	cr := newReader(r)
	header, err := cr.Read()
	if err != nil {
		return 0, err
	}
	if len(header) > 0 {
		header[0] = stripBOM(header[0])
	}
	col := indexHeader(header)
	n := 0
	for {
		rec, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		name := strings.TrimSpace(get(rec, col, "Name"))
		if name == "" {
			continue
		}
		id, _ := atoiLoose(get(rec, col, "ID"))
		age, _ := atoiLoose(get(rec, col, "Age"))
		overall, _ := atoiLoose(get(rec, col, "Overall"))
		potential, _ := atoiLoose(get(rec, col, "Potential"))
		club := strings.TrimSpace(get(rec, col, "Club"))
		nat := strings.TrimSpace(get(rec, col, "Nationality"))
		p := Player{
			ID:            id,
			Name:          name,
			Age:           age,
			Nationality:   nat,
			Overall:       overall,
			Potential:     potential,
			Club:          club,
			ClubKey:       NormalizeTeam(club),
			Position:      strings.TrimSpace(get(rec, col, "Position")),
			Jersey:        strings.TrimSpace(get(rec, col, "Jersey Number")),
			Height:        strings.TrimSpace(get(rec, col, "Height")),
			Weight:        strings.TrimSpace(get(rec, col, "Weight")),
			PreferredFoot: strings.TrimSpace(get(rec, col, "Preferred Foot")),
			Value:         strings.TrimSpace(get(rec, col, "Value")),
			Wage:          strings.TrimSpace(get(rec, col, "Wage")),
			NameKey:       NormalizeName(name),
			NationKey:     NormalizeName(nat),
		}
		s.Players = append(s.Players, p)
		n++
	}
	return n, nil
}

// --- header helpers ---------------------------------------------------------

// indexHeader maps trimmed column names to their position.
func indexHeader(header []string) map[string]int {
	m := make(map[string]int, len(header))
	for i, h := range header {
		m[strings.TrimSpace(h)] = i
	}
	return m
}

// get returns the trimmed value of the named column, or "" if absent.
func get(rec []string, col map[string]int, name string) string {
	i, ok := col[name]
	if !ok || i >= len(rec) {
		return ""
	}
	return strings.TrimSpace(rec[i])
}
