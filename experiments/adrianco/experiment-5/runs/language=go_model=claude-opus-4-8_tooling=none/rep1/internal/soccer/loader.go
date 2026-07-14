// Context:
//   - This file reads the six provided CSV files and converts each into the
//     unified Match/Player model. Every source has its own column layout, date
//     format and quirks, so there is one loader per file plus shared helpers.
//   - Quirks handled here: a UTF-8 BOM on the FIFA header row; goal counts
//     written as floats ("1.0"); Brazilian DD/MM/YYYY dates; goals quoted as
//     strings; and the BR-Football file having no season column (season is
//     derived from the match date).
//   - Loaders are tolerant: a malformed individual row is skipped rather than
//     aborting the whole load, so a single bad line never takes down the server.
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

// The canonical file names expected inside the data directory.
const (
	fileBrasileirao  = "Brasileirao_Matches.csv"
	fileCup          = "Brazilian_Cup_Matches.csv"
	fileLibertadores = "Libertadores_Matches.csv"
	fileBRFootball   = "BR-Football-Dataset.csv"
	fileNovo         = "novo_campeonato_brasileiro.csv"
	fileFifa         = "fifa_data.csv"
)

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006.01.02",
}

// parseDate tries each known layout. Returns the time and whether it succeeded.
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

// parseGoals parses a goal count that may be written as "2", "2.0" or "".
func parseGoals(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if n, err := strconv.Atoi(s); err == nil {
		return n, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func parseInt(s string) int {
	n, _ := strconv.Atoi(strings.TrimSpace(s))
	return n
}

// openCSV opens a file and returns a configured csv.Reader.
func openCSV(path string) (*os.File, *csv.Reader, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // tolerate ragged rows
	r.LazyQuotes = true
	return f, r, nil
}

// headerIndex builds a name->column map, trimming a leading BOM if present.
func headerIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff")
		idx[strings.TrimSpace(h)] = i
	}
	return idx
}

func get(row []string, idx map[string]int, name string) string {
	if i, ok := idx[name]; ok && i < len(row) {
		return strings.TrimSpace(row[i])
	}
	return ""
}

// finishMatch fills in the derived fields (clean names, normalized keys, season
// fallback) shared by every match loader.
func finishMatch(m *Match, source string) {
	m.HomeNorm = NormalizeTeam(m.HomeTeam)
	m.AwayNorm = NormalizeTeam(m.AwayTeam)
	m.HomeTeam = CleanTeamName(m.HomeTeam)
	m.AwayTeam = CleanTeamName(m.AwayTeam)
	if m.Season == 0 && m.HasDate {
		m.Season = m.Date.Year()
	}
	m.Sources = []string{source}
}

// loadBrasileirao reads Brasileirao_Matches.csv (Série A, 2012+).
func loadBrasileirao(path string) ([]Match, error) {
	return loadGeneric(path, fileBrasileirao, CompSerieA, func(row []string, idx map[string]int) (Match, bool) {
		m := Match{Competition: CompSerieA}
		m.HomeTeam = get(row, idx, "home_team")
		m.AwayTeam = get(row, idx, "away_team")
		m.HomeState = get(row, idx, "home_team_state")
		m.AwayState = get(row, idx, "away_team_state")
		m.Round = get(row, idx, "round")
		m.Season = parseInt(get(row, idx, "season"))
		if t, ok := parseDate(get(row, idx, "datetime")); ok {
			m.Date, m.HasDate = t, true
		}
		hg, ok1 := parseGoals(get(row, idx, "home_goal"))
		ag, ok2 := parseGoals(get(row, idx, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

// loadCup reads Brazilian_Cup_Matches.csv (Copa do Brasil).
func loadCup(path string) ([]Match, error) {
	return loadGeneric(path, fileCup, CompCopaDoBrasil, func(row []string, idx map[string]int) (Match, bool) {
		m := Match{Competition: CompCopaDoBrasil}
		m.HomeTeam = get(row, idx, "home_team")
		m.AwayTeam = get(row, idx, "away_team")
		m.Round = get(row, idx, "round")
		m.Season = parseInt(get(row, idx, "season"))
		if t, ok := parseDate(get(row, idx, "datetime")); ok {
			m.Date, m.HasDate = t, true
		}
		hg, ok1 := parseGoals(get(row, idx, "home_goal"))
		ag, ok2 := parseGoals(get(row, idx, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

// loadLibertadores reads Libertadores_Matches.csv (Copa Libertadores).
func loadLibertadores(path string) ([]Match, error) {
	return loadGeneric(path, fileLibertadores, CompLibertadores, func(row []string, idx map[string]int) (Match, bool) {
		m := Match{Competition: CompLibertadores}
		m.HomeTeam = get(row, idx, "home_team")
		m.AwayTeam = get(row, idx, "away_team")
		m.Stage = get(row, idx, "stage")
		m.Season = parseInt(get(row, idx, "season"))
		if t, ok := parseDate(get(row, idx, "datetime")); ok {
			m.Date, m.HasDate = t, true
		}
		hg, ok1 := parseGoals(get(row, idx, "home_goal"))
		ag, ok2 := parseGoals(get(row, idx, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

// loadBRFootball reads BR-Football-Dataset.csv (Série A/B/C and Copa do Brasil,
// with extended statistics). It has no season column, so season is the year of
// the match date.
func loadBRFootball(path string) ([]Match, error) {
	return loadGeneric(path, fileBRFootball, "", func(row []string, idx map[string]int) (Match, bool) {
		m := Match{Competition: canonicalCompetition(get(row, idx, "tournament"))}
		m.HomeTeam = get(row, idx, "home")
		m.AwayTeam = get(row, idx, "away")
		if t, ok := parseDate(get(row, idx, "date")); ok {
			m.Date, m.HasDate = t, true
		}
		hg, ok1 := parseGoals(get(row, idx, "home_goal"))
		ag, ok2 := parseGoals(get(row, idx, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		return m, m.HomeTeam != "" && m.AwayTeam != "" && m.Competition != ""
	})
}

// loadNovo reads novo_campeonato_brasileiro.csv (historical Série A 2003-2019).
func loadNovo(path string) ([]Match, error) {
	return loadGeneric(path, fileNovo, CompSerieA, func(row []string, idx map[string]int) (Match, bool) {
		m := Match{Competition: CompSerieA}
		m.HomeTeam = get(row, idx, "Equipe_mandante")
		m.AwayTeam = get(row, idx, "Equipe_visitante")
		m.HomeState = get(row, idx, "Mandante_UF")
		m.AwayState = get(row, idx, "Visitante_UF")
		m.Round = get(row, idx, "Rodada")
		m.Arena = get(row, idx, "Arena")
		m.Season = parseInt(get(row, idx, "Ano"))
		if t, ok := parseDate(get(row, idx, "Data")); ok {
			m.Date, m.HasDate = t, true
		}
		hg, ok1 := parseGoals(get(row, idx, "Gols_mandante"))
		ag, ok2 := parseGoals(get(row, idx, "Gols_visitante"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		return m, m.HomeTeam != "" && m.AwayTeam != ""
	})
}

// loadGeneric drives the shared read loop: read header, map columns, apply the
// per-file row converter, finish derived fields, skip rows the converter rejects.
func loadGeneric(path, source, _ string, convert func([]string, map[string]int) (Match, bool)) ([]Match, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := headerIndex(header)

	var out []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue // skip malformed line
		}
		m, ok := convert(row, idx)
		if !ok {
			continue
		}
		finishMatch(&m, source)
		out = append(out, m)
	}
	return out, nil
}

// loadPlayers reads fifa_data.csv into Player records.
func loadPlayers(path string) ([]Player, error) {
	f, r, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := headerIndex(header)

	var out []Player
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		p := Player{
			ID:            parseInt(get(row, idx, "ID")),
			Name:          get(row, idx, "Name"),
			Age:           parseInt(get(row, idx, "Age")),
			Nationality:   get(row, idx, "Nationality"),
			Overall:       parseInt(get(row, idx, "Overall")),
			Potential:     parseInt(get(row, idx, "Potential")),
			Club:          get(row, idx, "Club"),
			Position:      get(row, idx, "Position"),
			JerseyNumber:  get(row, idx, "Jersey Number"),
			Height:        get(row, idx, "Height"),
			Weight:        get(row, idx, "Weight"),
			PreferredFoot: get(row, idx, "Preferred Foot"),
			Value:         get(row, idx, "Value"),
			Wage:          get(row, idx, "Wage"),
		}
		if p.Name == "" {
			continue
		}
		p.NameNorm = normalizeText(p.Name)
		p.ClubNorm = normalizeText(p.Club)
		out = append(out, p)
	}
	return out, nil
}

// loadAllMatches loads every match file present in dir. Missing files are
// skipped (so the loader works even if a subset of data is available); a parse
// error on a present file is returned.
func loadAllMatches(dir string) ([]Match, error) {
	type fileLoader struct {
		name string
		fn   func(string) ([]Match, error)
	}
	loaders := []fileLoader{
		{fileBrasileirao, loadBrasileirao},
		{fileCup, loadCup},
		{fileLibertadores, loadLibertadores},
		{fileBRFootball, loadBRFootball},
		{fileNovo, loadNovo},
	}
	var all []Match
	for _, l := range loaders {
		path := filepath.Join(dir, l.name)
		if _, err := os.Stat(path); err != nil {
			continue // file not present
		}
		ms, err := l.fn(path)
		if err != nil {
			return nil, err
		}
		all = append(all, ms...)
	}
	return all, nil
}
