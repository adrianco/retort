// Brazilian Soccer MCP Server
//
// File: loader.go
// Responsibility: Read the six bundled Kaggle CSV files and convert each row
// into the normalized `Match` / `Player` domain types. Each source file has a
// different column layout, so the loader maps columns by header name (tolerant
// of ordering and a UTF-8 BOM) and applies the dataset-specific competition
// label. All parsing funnels through the helpers in normalize.go so team names,
// dates and numbers come out canonicalized.
package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// matchFile describes how to load one of the match CSVs.
type matchFile struct {
	name        string // file name within the data dir
	competition string // competition label to stamp on every row (empty => per-row)
}

// LoadAll reads every dataset under dataDir into a freshly built Store. Missing
// files are skipped with a warning rather than being fatal, so the server still
// starts if a dataset is absent.
func LoadAll(dataDir string) (*Store, error) {
	s := NewStore()

	matchFiles := []matchFile{
		{"Brasileirao_Matches.csv", "Brasileirão Série A"},
		{"Brazilian_Cup_Matches.csv", "Copa do Brasil"},
		{"Libertadores_Matches.csv", "Copa Libertadores"},
		{"novo_campeonato_brasileiro.csv", "Brasileirão Série A"},
		{"BR-Football-Dataset.csv", ""}, // competition comes from the row
	}

	for _, mf := range matchFiles {
		path := filepath.Join(dataDir, mf.name)
		n, err := loadMatchFile(s, path, mf)
		if err != nil {
			fmt.Fprintf(os.Stderr, "warning: %s: %v\n", mf.name, err)
			continue
		}
		fmt.Fprintf(os.Stderr, "loaded %d matches from %s\n", n, mf.name)
	}

	playerPath := filepath.Join(dataDir, "fifa_data.csv")
	pn, err := loadPlayers(s, playerPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "warning: fifa_data.csv: %v\n", err)
	} else {
		fmt.Fprintf(os.Stderr, "loaded %d players from fifa_data.csv\n", pn)
	}

	s.Index()
	return s, nil
}

// newCSVReader opens path and returns a csv.Reader configured to tolerate the
// ragged rows present in some of the datasets.
func newCSVReader(path string) (*os.File, *csv.Reader, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // allow variable column counts
	r.LazyQuotes = true
	r.ReuseRecord = true
	return f, r, nil
}

// headerIndex reads the first record and returns a map from normalized header
// name to column index. The leading UTF-8 BOM (present in fifa_data.csv) is
// stripped from the first column.
func headerIndex(r *csv.Reader) (map[string]int, error) {
	head, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := make(map[string]int, len(head))
	for i, h := range head {
		h = strings.TrimPrefix(h, "\ufeff")
		idx[strings.ToLower(strings.TrimSpace(h))] = i
	}
	return idx, nil
}

// get safely returns the trimmed value at the named column, or "" if the column
// is absent or the row is too short.
func get(row []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(strings.Trim(row[i], `"`))
}

// loadMatchFile loads a single match CSV into the store and returns the number
// of rows ingested.
func loadMatchFile(s *Store, path string, mf matchFile) (int, error) {
	f, r, err := newCSVReader(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	idx, err := headerIndex(r)
	if err != nil {
		return 0, err
	}

	count := 0
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue // skip malformed line
		}
		m, ok := rowToMatch(row, idx, mf)
		if !ok {
			continue
		}
		s.Matches = append(s.Matches, m)
		count++
	}
	return count, nil
}

// rowToMatch converts one CSV row to a Match, returning false if the row lacks
// the minimum required fields (both team names).
func rowToMatch(row []string, idx map[string]int, mf matchFile) (Match, bool) {
	// Column names differ between the English Kaggle files and the Portuguese
	// novo_campeonato file; look up both spellings.
	home := firstNonEmpty(get(row, idx, "home_team"), get(row, idx, "home"), get(row, idx, "equipe_mandante"))
	away := firstNonEmpty(get(row, idx, "away_team"), get(row, idx, "away"), get(row, idx, "equipe_visitante"))
	if home == "" || away == "" {
		return Match{}, false
	}

	// States (read first so they can inform the canonical key for datasets that
	// keep the state in a separate column, e.g. novo_campeonato).
	homeState := firstNonEmpty(get(row, idx, "home_team_state"), get(row, idx, "mandante_uf"))
	awayState := firstNonEmpty(get(row, idx, "away_team_state"), get(row, idx, "visitante_uf"))

	m := Match{
		HomeTeam:  teamDisplay(home, homeState),
		AwayTeam:  teamDisplay(away, awayState),
		HomeKey:   teamFullKey(home, homeState),
		AwayKey:   teamFullKey(away, awayState),
		HomeBase:  teamBaseKey(home),
		AwayBase:  teamBaseKey(away),
		HomeState: homeState,
		AwayState: awayState,
		Source:    filepath.Base(mf.name),
	}

	// Scores.
	hg, okH := atoi(firstNonEmpty(get(row, idx, "home_goal"), get(row, idx, "gols_mandante")))
	ag, okA := atoi(firstNonEmpty(get(row, idx, "away_goal"), get(row, idx, "gols_visitante")))
	if okH && okA {
		m.HomeGoal, m.AwayGoal, m.HasScore = hg, ag, true
	}

	// Date: dedicated column, or a date+time pair (BR-Football-Dataset).
	dateRaw := firstNonEmpty(get(row, idx, "datetime"), get(row, idx, "data"), get(row, idx, "date"))
	if t, ok := parseDate(dateRaw); ok {
		m.Date, m.HasDate = t, true
	}

	// Season / year.
	if yr, ok := atoi(firstNonEmpty(get(row, idx, "season"), get(row, idx, "ano"))); ok {
		m.Season = yr
	} else if m.HasDate {
		m.Season = m.Date.Year()
	}

	// Round.
	m.Round = firstNonEmpty(get(row, idx, "round"), get(row, idx, "rodada"))

	// Stadium (historical Brasileirão only).
	m.Stadium = get(row, idx, "arena")

	// Stage (Libertadores only).
	m.Stage = get(row, idx, "stage")

	// Competition: fixed label, or per-row tournament (BR-Football-Dataset).
	if mf.competition != "" {
		m.Competition = mf.competition
	} else {
		m.Competition = competitionLabel(get(row, idx, "tournament"))
	}

	// Extended stats (BR-Football-Dataset).
	hs, okHS := atoi(get(row, idx, "home_shots"))
	as, okAS := atoi(get(row, idx, "away_shots"))
	hc, _ := atoi(get(row, idx, "home_corner"))
	ac, _ := atoi(get(row, idx, "away_corner"))
	if okHS || okAS {
		m.HomeShots, m.AwayShots = hs, as
		m.HomeCorners, m.AwayCorners = hc, ac
		m.HasStats = true
	}

	return m, true
}

// competitionLabel maps the BR-Football-Dataset "tournament" values to the
// canonical competition names used elsewhere.
func competitionLabel(tournament string) string {
	switch normKey(tournament) {
	case "serie a":
		return "Brasileirão Série A"
	case "serie b":
		return "Brasileirão Série B"
	case "serie c":
		return "Brasileirão Série C"
	case "copa do brasil":
		return "Copa do Brasil"
	case "":
		return "Unknown"
	default:
		return tournament
	}
}

// loadPlayers loads the FIFA player CSV into the store.
func loadPlayers(s *Store, path string) (int, error) {
	f, r, err := newCSVReader(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	idx, err := headerIndex(r)
	if err != nil {
		return 0, err
	}

	count := 0
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		name := get(row, idx, "name")
		if name == "" {
			continue
		}
		p := Player{
			Name:        name,
			NameKey:     normKey(name),
			Nationality: get(row, idx, "nationality"),
			Club:        get(row, idx, "club"),
			ClubKey:     teamKey(get(row, idx, "club")),
			Position:    get(row, idx, "position"),
			Jersey:      get(row, idx, "jersey number"),
			Height:      get(row, idx, "height"),
			Weight:      get(row, idx, "weight"),
			PreferredFt: get(row, idx, "preferred foot"),
		}
		if id, ok := atoi(get(row, idx, "id")); ok {
			p.ID = id
		}
		if a, ok := atoi(get(row, idx, "age")); ok {
			p.Age = a
		}
		if o, ok := atoi(get(row, idx, "overall")); ok {
			p.Overall = o
		}
		if pt, ok := atoi(get(row, idx, "potential")); ok {
			p.Potential = pt
		}
		s.Players = append(s.Players, p)
		count++
	}
	return count, nil
}

// firstNonEmpty returns the first non-empty string among its arguments.
func firstNonEmpty(vals ...string) string {
	for _, v := range vals {
		if v != "" {
			return v
		}
	}
	return ""
}
