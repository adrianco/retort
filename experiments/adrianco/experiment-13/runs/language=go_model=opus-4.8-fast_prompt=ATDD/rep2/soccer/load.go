// CSV ingestion for the soccer domain. Each provided dataset has its own
// columns, date format, and team-naming convention; the loaders here translate
// every file into the unified Match/Player models, tolerating multiple date
// formats and UTF-8 (incl. a BOM) gracefully.
package soccer

import (
	"encoding/csv"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// knownMatchFiles maps each provided match CSV to the competition it belongs to
// (empty means the competition is read from a column in the file).
var competitionByFile = map[string]string{
	"Brasileirao_Matches.csv":        "Brasileirão",
	"Brazilian_Cup_Matches.csv":      "Copa do Brasil",
	"Libertadores_Matches.csv":       "Copa Libertadores",
	"novo_campeonato_brasileiro.csv": "Brasileirão",
}

// LoadDir reads every recognised CSV in dir into a new Store. Unknown files are
// ignored. Missing files are not an error (the dir may hold a subset).
func LoadDir(dir string) (*Store, error) {
	s := NewStore()
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		path := filepath.Join(dir, name)
		switch name {
		case "fifa_data.csv":
			if err := loadFIFA(s, path); err != nil {
				return nil, err
			}
		case "BR-Football-Dataset.csv":
			if err := loadExtended(s, path); err != nil {
				return nil, err
			}
		case "novo_campeonato_brasileiro.csv":
			if err := loadHistorical(s, path); err != nil {
				return nil, err
			}
		case "Libertadores_Matches.csv":
			if err := loadLibertadores(s, path); err != nil {
				return nil, err
			}
		case "Brazilian_Cup_Matches.csv":
			if err := loadCup(s, path); err != nil {
				return nil, err
			}
		case "Brasileirao_Matches.csv":
			if err := loadBrasileirao(s, path); err != nil {
				return nil, err
			}
		}
	}
	s.dedupMatches()
	return s, nil
}

// openCSV returns a configured csv.Reader over the file, stripping a UTF-8 BOM
// and tolerating rows with a varying number of fields.
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

// headerIndex builds a column-name -> index map, trimming whitespace and a
// leading BOM from header cells.
func headerIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff")
		idx[strings.TrimSpace(h)] = i
	}
	return idx
}

func get(row []string, i int) string {
	if i < 0 || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func atoi(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if n, err := strconv.Atoi(s); err == nil {
		return n
	}
	// Tolerate float-formatted integers like "2.0".
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(math.Round(f))
	}
	return 0
}

// parseDate accepts the several formats present across the datasets:
// "2012-05-19 18:30:00", "2023-09-24", and Brazilian "29/03/2003".
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	layouts := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02",
		"02/01/2006",
		"2/1/2006",
		"02/01/2006 15:04:05",
	}
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

func loadBrasileirao(s *Store, path string) error {
	return loadMatchFile(s, path, "Brasileirão", func(idx map[string]int, row []string) (Match, bool) {
		m := Match{
			Competition: "Brasileirão",
			HomeTeam:    CanonicalTeam(get(row, idx["home_team"]), get(row, idx["home_team_state"])),
			AwayTeam:    CanonicalTeam(get(row, idx["away_team"]), get(row, idx["away_team_state"])),
			HomeGoals:   atoi(get(row, idx["home_goal"])),
			AwayGoals:   atoi(get(row, idx["away_goal"])),
			Season:      atoi(get(row, idx["season"])),
			Round:       get(row, idx["round"]),
		}
		if t, ok := parseDate(get(row, idx["datetime"])); ok {
			m.Date, m.HasDate = t, true
		}
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

func loadCup(s *Store, path string) error {
	return loadMatchFile(s, path, "Copa do Brasil", func(idx map[string]int, row []string) (Match, bool) {
		m := Match{
			Competition: "Copa do Brasil",
			HomeTeam:    CanonicalTeam(get(row, idx["home_team"]), ""),
			AwayTeam:    CanonicalTeam(get(row, idx["away_team"]), ""),
			HomeGoals:   atoi(get(row, idx["home_goal"])),
			AwayGoals:   atoi(get(row, idx["away_goal"])),
			Season:      atoi(get(row, idx["season"])),
			Round:       get(row, idx["round"]),
		}
		if t, ok := parseDate(get(row, idx["datetime"])); ok {
			m.Date, m.HasDate = t, true
		}
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

func loadLibertadores(s *Store, path string) error {
	return loadMatchFile(s, path, "Copa Libertadores", func(idx map[string]int, row []string) (Match, bool) {
		m := Match{
			Competition: "Copa Libertadores",
			HomeTeam:    CanonicalTeam(get(row, idx["home_team"]), ""),
			AwayTeam:    CanonicalTeam(get(row, idx["away_team"]), ""),
			HomeGoals:   atoi(get(row, idx["home_goal"])),
			AwayGoals:   atoi(get(row, idx["away_goal"])),
			Season:      atoi(get(row, idx["season"])),
			Stage:       get(row, idx["stage"]),
		}
		if t, ok := parseDate(get(row, idx["datetime"])); ok {
			m.Date, m.HasDate = t, true
		}
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

func loadHistorical(s *Store, path string) error {
	return loadMatchFile(s, path, "Brasileirão", func(idx map[string]int, row []string) (Match, bool) {
		m := Match{
			Competition: "Brasileirão",
			HomeTeam:    CanonicalTeam(get(row, idx["Equipe_mandante"]), get(row, idx["Mandante_UF"])),
			AwayTeam:    CanonicalTeam(get(row, idx["Equipe_visitante"]), get(row, idx["Visitante_UF"])),
			HomeGoals:   atoi(get(row, idx["Gols_mandante"])),
			AwayGoals:   atoi(get(row, idx["Gols_visitante"])),
			Season:      atoi(get(row, idx["Ano"])),
			Round:       get(row, idx["Rodada"]),
		}
		if t, ok := parseDate(get(row, idx["Data"])); ok {
			m.Date, m.HasDate = t, true
		}
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

func loadExtended(s *Store, path string) error {
	return loadMatchFile(s, path, "", func(idx map[string]int, row []string) (Match, bool) {
		comp := get(row, idx["tournament"])
		if comp == "" {
			comp = "Unknown"
		}
		m := Match{
			Competition: comp,
			HomeTeam:    CanonicalTeam(get(row, idx["home"]), ""),
			AwayTeam:    CanonicalTeam(get(row, idx["away"]), ""),
			HomeGoals:   atoi(get(row, idx["home_goal"])),
			AwayGoals:   atoi(get(row, idx["away_goal"])),
		}
		if t, ok := parseDate(get(row, idx["date"])); ok {
			m.Date, m.HasDate = t, true
			m.Season = t.Year()
		}
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

// loadMatchFile drives the shared CSV loop, delegating row->Match mapping to fn.
func loadMatchFile(s *Store, path, source string, fn func(idx map[string]int, row []string) (Match, bool)) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		if err == io.EOF {
			return nil
		}
		return err
	}
	idx := headerIndex(header)
	base := filepath.Base(path)
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue // skip malformed rows rather than aborting the load
		}
		m, ok := fn(idx, row)
		if !ok {
			continue
		}
		m.Source = base
		s.AddMatch(m)
	}
	return nil
}

func loadFIFA(s *Store, path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		if err == io.EOF {
			return nil
		}
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
		name := get(row, idx["Name"])
		if name == "" {
			continue
		}
		p := Player{
			ID:          atoi(get(row, idx["ID"])),
			Name:        name,
			Age:         atoi(get(row, idx["Age"])),
			Nationality: get(row, idx["Nationality"]),
			Overall:     atoi(get(row, idx["Overall"])),
			Potential:   atoi(get(row, idx["Potential"])),
			Club:        get(row, idx["Club"]),
			Position:    get(row, idx["Position"]),
		}
		s.AddPlayer(p)
	}
	return nil
}
