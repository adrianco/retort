// Context
// -------
// CSV loading for all six provided datasets. Each loader maps source columns by
// header name (robust to column reordering), normalizes team names and dates,
// assigns a canonical competition, and appends Match/Player records to the
// Graph. Overlapping match datasets (e.g. Brasileirao_Matches.csv and
// novo_campeonato_brasileiro.csv share 2012-2019) are deduplicated by the Graph
// so aggregate statistics are not double counted.
package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// dataFiles lists the expected CSV file names within the data directory.
const (
	fileBrasileirao  = "Brasileirao_Matches.csv"
	fileCup          = "Brazilian_Cup_Matches.csv"
	fileLibertadores = "Libertadores_Matches.csv"
	fileBRFootball   = "BR-Football-Dataset.csv"
	fileNovo         = "novo_campeonato_brasileiro.csv"
	fileFifa         = "fifa_data.csv"
)

// LoadGraph loads every dataset found in dataDir into a new Graph. Missing
// optional files are skipped with no error; a completely empty load returns an
// error so callers fail fast on a bad path.
func LoadGraph(dataDir string) (*Graph, error) {
	g := NewGraph()

	loaders := []struct {
		file string
		fn   func(*Graph, string) error
	}{
		// Accent-rich, canonical sources first so their display names win.
		{fileBrasileirao, loadBrasileirao},
		{fileCup, loadCup},
		{fileLibertadores, loadLibertadores},
		{fileNovo, loadNovo},
		{fileBRFootball, loadBRFootball},
	}
	for _, l := range loaders {
		path := filepath.Join(dataDir, l.file)
		if _, err := os.Stat(path); err != nil {
			continue // optional file absent
		}
		if err := l.fn(g, path); err != nil {
			return nil, fmt.Errorf("loading %s: %w", l.file, err)
		}
	}

	if path := filepath.Join(dataDir, fileFifa); fileExists(path) {
		if err := loadFifa(g, path); err != nil {
			return nil, fmt.Errorf("loading %s: %w", fileFifa, err)
		}
	}

	if len(g.Matches) == 0 && len(g.Players) == 0 {
		return nil, fmt.Errorf("no data loaded from %q (no CSV files found)", dataDir)
	}
	g.finalize()
	return g, nil
}

func fileExists(p string) bool {
	_, err := os.Stat(p)
	return err == nil
}

// readCSV opens a CSV file and returns its header (with BOM stripped) plus a
// column-name -> index map and the data rows.
func readCSV(path string) (idx map[string]int, rows [][]string, err error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // tolerate ragged rows
	r.LazyQuotes = true

	header, err := r.Read()
	if err != nil {
		return nil, nil, err
	}
	idx = make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(stripBOM(h))] = i
	}
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, nil, err
		}
		rows = append(rows, rec)
	}
	return idx, rows, nil
}

func stripBOM(s string) string { return strings.TrimPrefix(s, "\ufeff") }

// cell safely fetches a column value from a record using the header index.
func cell(rec []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(rec) {
		return ""
	}
	return strings.TrimSpace(rec[i])
}

func loadBrasileirao(g *Graph, path string) error {
	idx, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, rec := range rows {
		m, ok := baseMatch(rec, idx, "datetime", "home_team", "away_team", "home_goal", "away_goal", "season")
		if !ok {
			continue
		}
		m.Competition = CompBrasileirao
		m.Round = cell(rec, idx, "round")
		m.Source = fileBrasileirao
		if s := cell(rec, idx, "home_team_state"); s != "" {
			m.HomeState = strings.ToUpper(s)
		}
		if s := cell(rec, idx, "away_team_state"); s != "" {
			m.AwayState = strings.ToUpper(s)
		}
		g.addMatch(m)
	}
	return nil
}

func loadCup(g *Graph, path string) error {
	idx, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, rec := range rows {
		m, ok := baseMatch(rec, idx, "datetime", "home_team", "away_team", "home_goal", "away_goal", "season")
		if !ok {
			continue
		}
		m.Competition = CompCopaBrasil
		m.Round = cell(rec, idx, "round")
		m.Source = fileCup
		g.addMatch(m)
	}
	return nil
}

func loadLibertadores(g *Graph, path string) error {
	idx, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, rec := range rows {
		m, ok := baseMatch(rec, idx, "datetime", "home_team", "away_team", "home_goal", "away_goal", "season")
		if !ok {
			continue
		}
		m.Competition = CompLibertadores
		m.Stage = cell(rec, idx, "stage")
		m.Source = fileLibertadores
		g.addMatch(m)
	}
	return nil
}

func loadNovo(g *Graph, path string) error {
	idx, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, rec := range rows {
		m, ok := baseMatch(rec, idx, "Data", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Ano")
		if !ok {
			continue
		}
		m.Competition = CompBrasileirao
		m.Round = cell(rec, idx, "Rodada")
		m.Stadium = cell(rec, idx, "Arena")
		m.Source = fileNovo
		if s := cell(rec, idx, "Mandante_UF"); s != "" {
			m.HomeState = strings.ToUpper(s)
		}
		if s := cell(rec, idx, "Visitante_UF"); s != "" {
			m.AwayState = strings.ToUpper(s)
		}
		g.addMatch(m)
	}
	return nil
}

func loadBRFootball(g *Graph, path string) error {
	idx, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, rec := range rows {
		m, ok := baseMatch(rec, idx, "date", "home", "away", "home_goal", "away_goal", "")
		if !ok {
			continue
		}
		m.Competition = canonicalCompetition(cell(rec, idx, "tournament"))
		m.Source = fileBRFootball
		// Season derived from match date when no explicit season column.
		m.Season = m.Date.Year()
		// Extended statistics.
		if hs, ok := parseIntLoose(cell(rec, idx, "home_shots")); ok {
			m.HasStats = true
			m.HomeShots = hs
		}
		if as, ok := parseIntLoose(cell(rec, idx, "away_shots")); ok {
			m.HasStats = true
			m.AwayShots = as
		}
		m.HomeCorner, _ = parseIntLoose(cell(rec, idx, "home_corner"))
		m.AwayCorner, _ = parseIntLoose(cell(rec, idx, "away_corner"))
		m.HomeAttack, _ = parseIntLoose(cell(rec, idx, "home_attack"))
		m.AwayAttack, _ = parseIntLoose(cell(rec, idx, "away_attack"))
		g.addMatch(m)
	}
	return nil
}

// baseMatch builds a Match from generic home/away/goal/date columns. seasonCol
// may be empty when the season is derived elsewhere. Returns ok=false when the
// row lacks the minimum required fields (both teams and a parseable date).
func baseMatch(rec []string, idx map[string]int, dateCol, homeCol, awayCol, homeGoalCol, awayGoalCol, seasonCol string) (Match, bool) {
	homeRaw := cell(rec, idx, homeCol)
	awayRaw := cell(rec, idx, awayCol)
	if homeRaw == "" || awayRaw == "" {
		return Match{}, false
	}
	date, hasTime, ok := ParseDate(cell(rec, idx, dateCol))
	if !ok {
		return Match{}, false
	}
	hg, _ := parseIntLoose(cell(rec, idx, homeGoalCol))
	ag, _ := parseIntLoose(cell(rec, idx, awayGoalCol))

	m := Match{
		Date:      date,
		HasTime:   hasTime,
		HomeRaw:   homeRaw,
		AwayRaw:   awayRaw,
		HomeTeam:  NormalizeTeamName(homeRaw),
		AwayTeam:  NormalizeTeamName(awayRaw),
		HomeState: StateFromName(homeRaw),
		AwayState: StateFromName(awayRaw),
		HomeGoals: hg,
		AwayGoals: ag,
	}
	if seasonCol != "" {
		if s, ok := parseIntLoose(cell(rec, idx, seasonCol)); ok {
			m.Season = s
		}
	}
	if m.Season == 0 {
		m.Season = date.Year()
	}
	return m, true
}

// canonicalCompetition maps a free-form tournament label onto a canonical
// competition name, falling back to a title-cased version of the raw label.
func canonicalCompetition(raw string) string {
	l := strings.ToLower(stripDiacritics(raw))
	switch {
	case strings.Contains(l, "libertadores"):
		return CompLibertadores
	case strings.Contains(l, "copa do brasil"), strings.Contains(l, "brazil cup"):
		return CompCopaBrasil
	case strings.Contains(l, "brasileir"), strings.Contains(l, "serie a"), strings.Contains(l, "serie-a"):
		return CompBrasileirao
	case raw == "":
		return "Unknown"
	default:
		return raw
	}
}

func loadFifa(g *Graph, path string) error {
	idx, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, rec := range rows {
		name := cell(rec, idx, "Name")
		if name == "" {
			continue
		}
		id, _ := parseIntLoose(cell(rec, idx, "ID"))
		age, _ := parseIntLoose(cell(rec, idx, "Age"))
		overall, _ := parseIntLoose(cell(rec, idx, "Overall"))
		potential, _ := parseIntLoose(cell(rec, idx, "Potential"))
		p := Player{
			ID:          id,
			Name:        name,
			Age:         age,
			Nationality: cell(rec, idx, "Nationality"),
			Overall:     overall,
			Potential:   potential,
			Club:        cell(rec, idx, "Club"),
			Position:    cell(rec, idx, "Position"),
			Jersey:      cell(rec, idx, "Jersey Number"),
			Height:      cell(rec, idx, "Height"),
			Weight:      cell(rec, idx, "Weight"),
		}
		g.addPlayer(p)
	}
	return nil
}
