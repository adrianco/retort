package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// csvReader returns a csv.Reader configured for the variable-width, possibly
// BOM-prefixed files in this repository.
func csvReader(r io.Reader) *csv.Reader {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1 // tolerate ragged rows
	cr.LazyQuotes = true
	cr.ReuseRecord = false
	return cr
}

// readTable reads an entire CSV, returning a column-name→index map (from the
// header) and the data rows. A leading UTF-8 BOM on the first header cell is
// stripped.
func readTable(r io.Reader) (map[string]int, [][]string, error) {
	cr := csvReader(r)
	header, err := cr.Read()
	if err != nil {
		return nil, nil, err
	}
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\uFEFF")
	}
	idx := make(map[string]int, len(header))
	for i, name := range header {
		idx[strings.TrimSpace(name)] = i
	}
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	return idx, rows, nil
}

// get returns the trimmed value of column name for row, or "" if absent.
func get(row []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func loadBrasileirao(r io.Reader) ([]Match, error) {
	idx, rows, err := readTable(r)
	if err != nil {
		return nil, err
	}
	ms := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			Competition: CompBrasileirao,
			Source:      "Brasileirao_Matches.csv",
			HomeTeam:    get(row, idx, "home_team"),
			AwayTeam:    get(row, idx, "away_team"),
			Round:       get(row, idx, "round"),
		}
		if v, ok := parseInt(get(row, idx, "season")); ok {
			m.Season = v
		}
		applyScore(&m, get(row, idx, "home_goal"), get(row, idx, "away_goal"))
		applyDate(&m, get(row, idx, "datetime"))
		ms = append(ms, m)
	}
	return ms, nil
}

func loadCup(r io.Reader) ([]Match, error) {
	idx, rows, err := readTable(r)
	if err != nil {
		return nil, err
	}
	ms := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			Competition: CompCopaDoBrasil,
			Source:      "Brazilian_Cup_Matches.csv",
			HomeTeam:    get(row, idx, "home_team"),
			AwayTeam:    get(row, idx, "away_team"),
			Round:       get(row, idx, "round"),
		}
		if v, ok := parseInt(get(row, idx, "season")); ok {
			m.Season = v
		}
		applyScore(&m, get(row, idx, "home_goal"), get(row, idx, "away_goal"))
		applyDate(&m, get(row, idx, "datetime"))
		ms = append(ms, m)
	}
	return ms, nil
}

func loadLibertadores(r io.Reader) ([]Match, error) {
	idx, rows, err := readTable(r)
	if err != nil {
		return nil, err
	}
	ms := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			Competition: CompLibertadores,
			Source:      "Libertadores_Matches.csv",
			HomeTeam:    get(row, idx, "home_team"),
			AwayTeam:    get(row, idx, "away_team"),
			Stage:       get(row, idx, "stage"),
		}
		if v, ok := parseInt(get(row, idx, "season")); ok {
			m.Season = v
		}
		applyScore(&m, get(row, idx, "home_goal"), get(row, idx, "away_goal"))
		applyDate(&m, get(row, idx, "datetime"))
		ms = append(ms, m)
	}
	return ms, nil
}

func loadBRFootball(r io.Reader) ([]Match, error) {
	idx, rows, err := readTable(r)
	if err != nil {
		return nil, err
	}
	ms := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			Competition: get(row, idx, "tournament"),
			Source:      "BR-Football-Dataset.csv",
			HomeTeam:    get(row, idx, "home"),
			AwayTeam:    get(row, idx, "away"),
		}
		applyScore(&m, get(row, idx, "home_goal"), get(row, idx, "away_goal"))
		if v, ok := parseInt(get(row, idx, "home_corner")); ok {
			m.HomeCorners = v
		}
		if v, ok := parseInt(get(row, idx, "away_corner")); ok {
			m.AwayCorners = v
		}
		if v, ok := parseInt(get(row, idx, "home_shots")); ok {
			m.HomeShots = v
		}
		if v, ok := parseInt(get(row, idx, "away_shots")); ok {
			m.AwayShots = v
		}
		applyDate(&m, get(row, idx, "date"))
		if m.HasDate {
			m.Season = m.Date.Year()
		}
		ms = append(ms, m)
	}
	return ms, nil
}

func loadNovo(r io.Reader) ([]Match, error) {
	idx, rows, err := readTable(r)
	if err != nil {
		return nil, err
	}
	ms := make([]Match, 0, len(rows))
	for _, row := range rows {
		m := Match{
			Competition: CompBrasileirao,
			Source:      "novo_campeonato_brasileiro.csv",
			HomeTeam:    get(row, idx, "Equipe_mandante"),
			AwayTeam:    get(row, idx, "Equipe_visitante"),
			Round:       get(row, idx, "Rodada"),
			Stadium:     get(row, idx, "Arena"),
		}
		if v, ok := parseInt(get(row, idx, "Ano")); ok {
			m.Season = v
		}
		applyScore(&m, get(row, idx, "Gols_mandante"), get(row, idx, "Gols_visitante"))
		applyDate(&m, get(row, idx, "Data"))
		ms = append(ms, m)
	}
	return ms, nil
}

func loadFIFA(r io.Reader) ([]Player, error) {
	idx, rows, err := readTable(r)
	if err != nil {
		return nil, err
	}
	ps := make([]Player, 0, len(rows))
	for _, row := range rows {
		p := Player{
			Name:         get(row, idx, "Name"),
			Nationality:  get(row, idx, "Nationality"),
			Club:         get(row, idx, "Club"),
			Position:     get(row, idx, "Position"),
			JerseyNumber: get(row, idx, "Jersey Number"),
			Height:       get(row, idx, "Height"),
			Weight:       get(row, idx, "Weight"),
		}
		if v, ok := parseInt(get(row, idx, "ID")); ok {
			p.ID = v
		}
		if v, ok := parseInt(get(row, idx, "Age")); ok {
			p.Age = v
		}
		if v, ok := parseInt(get(row, idx, "Overall")); ok {
			p.Overall = v
		}
		if v, ok := parseInt(get(row, idx, "Potential")); ok {
			p.Potential = v
		}
		ps = append(ps, p)
	}
	return ps, nil
}

// applyScore parses and stores a home/away goal pair, setting HasScore only
// when both values parse.
func applyScore(m *Match, home, away string) {
	h, okH := parseInt(home)
	a, okA := parseInt(away)
	if okH && okA {
		m.HomeGoals, m.AwayGoals, m.HasScore = h, a, true
	}
}

// applyDate parses and stores a match date, setting HasDate on success.
func applyDate(m *Match, s string) {
	if t, ok := ParseDate(s); ok {
		m.Date, m.HasDate = t, true
	}
}

// matchLoaders maps each match dataset file name to its loader.
var matchLoaders = map[string]func(io.Reader) ([]Match, error){
	"Brasileirao_Matches.csv":        loadBrasileirao,
	"Brazilian_Cup_Matches.csv":      loadCup,
	"Libertadores_Matches.csv":       loadLibertadores,
	"BR-Football-Dataset.csv":        loadBRFootball,
	"novo_campeonato_brasileiro.csv": loadNovo,
}

// LoadDir loads every known dataset from dir (typically "data/kaggle") into a
// KB. Missing files are reported as errors; a file that fails to parse aborts
// the load.
func LoadDir(dir string) (*KB, error) {
	kb := &KB{}
	for name, loader := range matchLoaders {
		path := filepath.Join(dir, name)
		ms, err := loadMatchFile(path, loader)
		if err != nil {
			return nil, err
		}
		kb.Matches = append(kb.Matches, ms...)
	}
	ps, err := loadPlayerFile(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, err
	}
	kb.Players = ps
	return kb, nil
}

func loadMatchFile(path string, loader func(io.Reader) ([]Match, error)) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	ms, err := loader(f)
	if err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	return ms, nil
}

func loadPlayerFile(path string) ([]Player, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	ps, err := loadFIFA(f)
	if err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	return ps, nil
}
