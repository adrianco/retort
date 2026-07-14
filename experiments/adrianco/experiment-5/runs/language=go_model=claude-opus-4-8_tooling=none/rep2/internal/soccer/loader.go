// loader.go reads the bundled CSV datasets into the in-memory Store. It is
// tolerant of the differing column layouts, date formats and numeric encodings
// used across the six source files and de-duplicates matches that appear in
// more than one dataset.
package soccer

import (
	"encoding/csv"
	"fmt"
	"io/fs"
	"path"
	"strconv"
	"strings"
	"time"
)

// matchFile describes one match CSV and the competition tagging logic for it.
type matchFile struct {
	name  string
	parse func(headers map[string]int, row []string) (Match, bool)
}

// Load reads every dataset found under dir within fsys and returns a populated
// Store. Missing files are skipped rather than treated as fatal so the server
// can still start with a partial dataset.
func Load(fsys fs.FS, dir string) (*Store, error) {
	s := &Store{}

	for _, mf := range matchFiles() {
		rows, headers, err := readCSV(fsys, path.Join(dir, mf.name))
		if err != nil {
			if isNotExist(err) {
				continue
			}
			return nil, fmt.Errorf("reading %s: %w", mf.name, err)
		}
		for _, row := range rows {
			if m, ok := mf.parse(headers, row); ok {
				m.Source = mf.name
				s.addMatch(m)
			}
		}
	}

	if rows, headers, err := readCSV(fsys, path.Join(dir, "fifa_data.csv")); err == nil {
		for _, row := range rows {
			if p, ok := parsePlayer(headers, row); ok {
				s.Players = append(s.Players, p)
			}
		}
	} else if !isNotExist(err) {
		return nil, fmt.Errorf("reading fifa_data.csv: %w", err)
	}

	s.finalize()
	return s, nil
}

func isNotExist(err error) bool {
	return strings.Contains(err.Error(), "no such file") ||
		strings.Contains(err.Error(), "file does not exist") ||
		strings.Contains(err.Error(), "cannot find")
}

// readCSV reads an entire CSV file, returning the data rows and a map from the
// (BOM-trimmed, trimmed) header name to its column index.
func readCSV(fsys fs.FS, name string) ([]([]string), map[string]int, error) {
	f, err := fsys.Open(name)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // tolerate ragged rows
	r.LazyQuotes = true

	all, err := r.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	if len(all) == 0 {
		return nil, map[string]int{}, nil
	}

	headers := make(map[string]int, len(all[0]))
	for i, h := range all[0] {
		h = strings.TrimPrefix(h, "\ufeff") // strip UTF-8 BOM
		headers[strings.TrimSpace(h)] = i
	}
	return all[1:], headers, nil
}

func matchFiles() []matchFile {
	// Order matters: the first source to insert a fixture wins on conflicting
	// fields (see Store.addMatch / mergeMatch). The official, single-competition
	// files are listed before the broad BR-Football dataset so their scores take
	// precedence; BR-Football mainly contributes seasons/competitions the others
	// do not cover (e.g. Série B and Série C).
	return []matchFile{
		{"Brasileirao_Matches.csv", parseBrasileirao},
		{"novo_campeonato_brasileiro.csv", parseNovo},
		{"Brazilian_Cup_Matches.csv", parseCup},
		{"Libertadores_Matches.csv", parseLibertadores},
		{"BR-Football-Dataset.csv", parseBRFootball},
	}
}

// --- per-file parsers ---

func parseBrasileirao(h map[string]int, row []string) (Match, bool) {
	home := get(h, row, "home_team")
	away := get(h, row, "away_team")
	if home == "" || away == "" {
		return Match{}, false
	}
	m := Match{Competition: CompSerieA}
	setTeams(&m, home, away)
	m.Season = atoi(get(h, row, "season"))
	m.Round = strings.TrimSpace(get(h, row, "round"))
	setScore(&m, get(h, row, "home_goal"), get(h, row, "away_goal"))
	setDate(&m, get(h, row, "datetime"))
	if m.Season == 0 {
		m.Season = m.Date.Year()
	}
	return m, true
}

func parseCup(h map[string]int, row []string) (Match, bool) {
	home := get(h, row, "home_team")
	away := get(h, row, "away_team")
	if home == "" || away == "" {
		return Match{}, false
	}
	m := Match{Competition: CompCopaBrasil}
	setTeams(&m, home, away)
	m.Season = atoi(get(h, row, "season"))
	m.Round = strings.TrimSpace(get(h, row, "round"))
	setScore(&m, get(h, row, "home_goal"), get(h, row, "away_goal"))
	setDate(&m, get(h, row, "datetime"))
	if m.Season == 0 {
		m.Season = m.Date.Year()
	}
	return m, true
}

func parseLibertadores(h map[string]int, row []string) (Match, bool) {
	home := get(h, row, "home_team")
	away := get(h, row, "away_team")
	if home == "" || away == "" {
		return Match{}, false
	}
	m := Match{Competition: CompLibertadores}
	setTeams(&m, home, away)
	m.Season = atoi(get(h, row, "season"))
	m.Stage = strings.TrimSpace(get(h, row, "stage"))
	setScore(&m, get(h, row, "home_goal"), get(h, row, "away_goal"))
	setDate(&m, get(h, row, "datetime"))
	if m.Season == 0 {
		m.Season = m.Date.Year()
	}
	return m, true
}

func parseBRFootball(h map[string]int, row []string) (Match, bool) {
	home := get(h, row, "home")
	away := get(h, row, "away")
	if home == "" || away == "" {
		return Match{}, false
	}
	m := Match{Competition: brFootballComp(get(h, row, "tournament"))}
	setTeams(&m, home, away)
	setScore(&m, get(h, row, "home_goal"), get(h, row, "away_goal"))
	setDate(&m, get(h, row, "date"))
	m.Season = m.Date.Year()
	return m, true
}

func brFootballComp(tournament string) string {
	switch strings.TrimSpace(tournament) {
	case "Serie A":
		return CompSerieA
	case "Serie B":
		return CompSerieB
	case "Serie C":
		return CompSerieC
	case "Copa do Brasil":
		return CompCopaBrasil
	default:
		return strings.TrimSpace(tournament)
	}
}

func parseNovo(h map[string]int, row []string) (Match, bool) {
	home := get(h, row, "Equipe_mandante")
	away := get(h, row, "Equipe_visitante")
	if home == "" || away == "" {
		return Match{}, false
	}
	m := Match{Competition: CompSerieA}
	setTeams(&m, home, away)
	m.Season = atoi(get(h, row, "Ano"))
	m.Round = strings.TrimSpace(get(h, row, "Rodada"))
	m.Stadium = strings.TrimSpace(get(h, row, "Arena"))
	setScore(&m, get(h, row, "Gols_mandante"), get(h, row, "Gols_visitante"))
	setDate(&m, get(h, row, "Data"))
	if m.Season == 0 {
		m.Season = m.Date.Year()
	}
	return m, true
}

func parsePlayer(h map[string]int, row []string) (Player, bool) {
	name := strings.TrimSpace(get(h, row, "Name"))
	if name == "" {
		return Player{}, false
	}
	return Player{
		ID:            atoi(get(h, row, "ID")),
		Name:          name,
		Age:           atoi(get(h, row, "Age")),
		Nationality:   strings.TrimSpace(get(h, row, "Nationality")),
		Overall:       atoi(get(h, row, "Overall")),
		Potential:     atoi(get(h, row, "Potential")),
		Club:          strings.TrimSpace(get(h, row, "Club")),
		Position:      strings.TrimSpace(get(h, row, "Position")),
		JerseyNumber:  strings.TrimSpace(get(h, row, "Jersey Number")),
		Height:        strings.TrimSpace(get(h, row, "Height")),
		Weight:        strings.TrimSpace(get(h, row, "Weight")),
		PreferredFoot: strings.TrimSpace(get(h, row, "Preferred Foot")),
	}, true
}

// --- field helpers ---

func get(h map[string]int, row []string, col string) string {
	i, ok := h[col]
	if !ok || i >= len(row) {
		return ""
	}
	return row[i]
}

func setTeams(m *Match, home, away string) {
	m.HomeRaw = strings.TrimSpace(home)
	m.AwayRaw = strings.TrimSpace(away)
	m.HomeTeam = DisplayName(home)
	m.AwayTeam = DisplayName(away)
}

func setScore(m *Match, home, away string) {
	hs, hok := parseGoals(home)
	as, aok := parseGoals(away)
	if hok && aok {
		m.HomeGoals = hs
		m.AwayGoals = as
		m.HasScore = true
	}
}

func setDate(m *Match, raw string) {
	if t, ok := parseDate(raw); ok {
		m.Date = t
		m.HasDate = true
	}
}

func atoi(s string) int {
	n, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		// tolerate float-encoded integers such as "12.0"
		if f, ferr := strconv.ParseFloat(strings.TrimSpace(s), 64); ferr == nil {
			return int(f)
		}
		return 0
	}
	return n
}

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

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006/01/02",
}

func parseDate(raw string) (time.Time, bool) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, raw); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}
