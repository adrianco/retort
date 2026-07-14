// CSV loading for the six Kaggle datasets. Each file has its own column layout,
// so there is a dedicated parser per file; BuildDB stitches them together and
// deduplicates matches that appear in more than one source.
package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

// Source priorities. When the same competition/season exists in several files
// the lowest priority value is kept as the canonical record.
const (
	prioBrasileirao  = 1 // Brasileirao_Matches.csv (rounds, 2012-2022)
	prioNovo         = 2 // novo_campeonato_brasileiro.csv (2003-2019)
	prioLibertadores = 3 // Libertadores_Matches.csv
	prioCup          = 4 // Brazilian_Cup_Matches.csv
	prioBRFootball   = 5 // BR-Football-Dataset.csv (extended stats)
)

// dataFiles lists the CSV files expected inside the data directory.
var dataFiles = struct {
	brasileirao, cup, libertadores, brFootball, novo, fifa string
}{
	brasileirao:  "Brasileirao_Matches.csv",
	cup:          "Brazilian_Cup_Matches.csv",
	libertadores: "Libertadores_Matches.csv",
	brFootball:   "BR-Football-Dataset.csv",
	novo:         "novo_campeonato_brasileiro.csv",
	fifa:         "fifa_data.csv",
}

// readCSV reads an entire CSV file, returning a trimmed header and the data
// rows. It tolerates ragged rows and a UTF-8 BOM on the first header cell.
func readCSV(path string) ([]string, [][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	rows, err := r.ReadAll()
	if err != nil {
		return nil, nil, fmt.Errorf("%s: %w", filepath.Base(path), err)
	}
	if len(rows) == 0 {
		return nil, nil, nil
	}
	header := rows[0]
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}
	for i := range header {
		header[i] = strings.TrimSpace(header[i])
	}
	return header, rows[1:], nil
}

// colMap maps header names to their column index.
func colMap(header []string) map[string]int {
	m := make(map[string]int, len(header))
	for i, h := range header {
		m[h] = i
	}
	return m
}

func cell(row []string, idx int) string {
	if idx >= 0 && idx < len(row) {
		return strings.TrimSpace(row[idx])
	}
	return ""
}

// parseIntLoose parses integers that may be written as floats ("2.0") or
// quoted strings, returning false when the value is absent or unparseable.
func parseIntLoose(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

// newMatch fills in the derived fields (display names, keys, score flag) shared
// by every per-file parser.
func newMatch(competition, source string, prio int, homeRaw, awayRaw string,
	homeGoal, awayGoal string) Match {
	m := Match{
		Competition: competition,
		Source:      source,
		SourcePrio:  prio,
		HomeRaw:     homeRaw,
		AwayRaw:     awayRaw,
		HomeTeam:    displayTeamName(homeRaw),
		AwayTeam:    displayTeamName(awayRaw),
		HomeID:      parseTeamIdentity(homeRaw),
		AwayID:      parseTeamIdentity(awayRaw),
	}
	hg, hok := parseIntLoose(homeGoal)
	ag, aok := parseIntLoose(awayGoal)
	if hok && aok {
		m.HomeGoal, m.AwayGoal, m.HasScore = hg, ag, true
	}
	return m
}

func loadBrasileirao(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	c := colMap(header)
	out := make([]Match, 0, len(rows))
	for _, row := range rows {
		home := cell(row, c["home_team"])
		away := cell(row, c["away_team"])
		if home == "" || away == "" {
			continue
		}
		m := newMatch("Brasileirão Série A", dataFiles.brasileirao, prioBrasileirao,
			home, away, cell(row, c["home_goal"]), cell(row, c["away_goal"]))
		m.Round = cell(row, c["round"])
		if s, ok := parseIntLoose(cell(row, c["season"])); ok {
			m.Season = s
		}
		if d, ok := parseDate(cell(row, c["datetime"])); ok {
			m.Date, m.HasDate = d, true
		}
		out = append(out, m)
	}
	return out, nil
}

func loadCup(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	c := colMap(header)
	out := make([]Match, 0, len(rows))
	for _, row := range rows {
		home := cell(row, c["home_team"])
		away := cell(row, c["away_team"])
		if home == "" || away == "" {
			continue
		}
		m := newMatch("Copa do Brasil", dataFiles.cup, prioCup,
			home, away, cell(row, c["home_goal"]), cell(row, c["away_goal"]))
		m.Round = cell(row, c["round"])
		if s, ok := parseIntLoose(cell(row, c["season"])); ok {
			m.Season = s
		}
		if d, ok := parseDate(cell(row, c["datetime"])); ok {
			m.Date, m.HasDate = d, true
		}
		out = append(out, m)
	}
	return out, nil
}

func loadLibertadores(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	c := colMap(header)
	out := make([]Match, 0, len(rows))
	for _, row := range rows {
		home := cell(row, c["home_team"])
		away := cell(row, c["away_team"])
		if home == "" || away == "" {
			continue
		}
		m := newMatch("Copa Libertadores", dataFiles.libertadores, prioLibertadores,
			home, away, cell(row, c["home_goal"]), cell(row, c["away_goal"]))
		m.Stage = cell(row, c["stage"])
		if s, ok := parseIntLoose(cell(row, c["season"])); ok {
			m.Season = s
		}
		if d, ok := parseDate(cell(row, c["datetime"])); ok {
			m.Date, m.HasDate = d, true
		}
		out = append(out, m)
	}
	return out, nil
}

func loadBRFootball(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	c := colMap(header)
	out := make([]Match, 0, len(rows))
	for _, row := range rows {
		home := cell(row, c["home"])
		away := cell(row, c["away"])
		if home == "" || away == "" {
			continue
		}
		m := newMatch(normalizeCompetition(cell(row, c["tournament"])),
			dataFiles.brFootball, prioBRFootball,
			home, away, cell(row, c["home_goal"]), cell(row, c["away_goal"]))
		if d, ok := parseDate(cell(row, c["date"])); ok {
			m.Date, m.HasDate, m.Season = d, true, d.Year()
		}
		hc, hcok := parseIntLoose(cell(row, c["home_corner"]))
		ac, acok := parseIntLoose(cell(row, c["away_corner"]))
		hs, hsok := parseIntLoose(cell(row, c["home_shots"]))
		as, asok := parseIntLoose(cell(row, c["away_shots"]))
		if hcok || acok || hsok || asok {
			m.HomeCorner, m.AwayCorner = hc, ac
			m.HomeShots, m.AwayShots = hs, as
			m.HasStats = true
		}
		out = append(out, m)
	}
	return out, nil
}

func loadNovo(path string) ([]Match, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	c := colMap(header)
	out := make([]Match, 0, len(rows))
	for _, row := range rows {
		home := cell(row, c["Equipe_mandante"])
		away := cell(row, c["Equipe_visitante"])
		if home == "" || away == "" {
			continue
		}
		m := newMatch("Brasileirão Série A", dataFiles.novo, prioNovo,
			home, away, cell(row, c["Gols_mandante"]), cell(row, c["Gols_visitante"]))
		m.Round = cell(row, c["Rodada"])
		m.Stadium = cell(row, c["Arena"])
		if s, ok := parseIntLoose(cell(row, c["Ano"])); ok {
			m.Season = s
		}
		if d, ok := parseDate(cell(row, c["Data"])); ok {
			m.Date, m.HasDate = d, true
		}
		out = append(out, m)
	}
	return out, nil
}

func loadPlayers(path string) ([]Player, error) {
	header, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	c := colMap(header)
	out := make([]Player, 0, len(rows))
	for _, row := range rows {
		name := cell(row, c["Name"])
		if name == "" {
			continue
		}
		p := Player{
			Name:          name,
			Nationality:   cell(row, c["Nationality"]),
			Club:          cell(row, c["Club"]),
			Position:      cell(row, c["Position"]),
			JerseyNumber:  cell(row, c["Jersey Number"]),
			Height:        cell(row, c["Height"]),
			Weight:        cell(row, c["Weight"]),
			PreferredFoot: cell(row, c["Preferred Foot"]),
		}
		if v, ok := parseIntLoose(cell(row, c["ID"])); ok {
			p.ID = v
		}
		if v, ok := parseIntLoose(cell(row, c["Age"])); ok {
			p.Age = v
		}
		if v, ok := parseIntLoose(cell(row, c["Overall"])); ok {
			p.Overall = v
		}
		if v, ok := parseIntLoose(cell(row, c["Potential"])); ok {
			p.Potential = v
		}
		out = append(out, p)
	}
	return out, nil
}

// canonicalize keeps, for every (competition, season) pair, only the matches
// from the highest-priority source so overlapping datasets are not counted
// twice. Matches without a season are always kept.
func canonicalize(all []Match) []Match {
	best := map[string]int{}
	for _, m := range all {
		if m.Season == 0 {
			continue
		}
		k := m.Competition + "|" + strconv.Itoa(m.Season)
		if p, ok := best[k]; !ok || m.SourcePrio < p {
			best[k] = m.SourcePrio
		}
	}
	out := make([]Match, 0, len(all))
	for _, m := range all {
		if m.Season == 0 {
			out = append(out, m)
			continue
		}
		k := m.Competition + "|" + strconv.Itoa(m.Season)
		if best[k] == m.SourcePrio {
			out = append(out, m)
		}
	}
	return out
}

// BuildDB loads every dataset from dataDir and assembles the in-memory DB.
func BuildDB(dataDir string) (*DB, error) {
	type loader struct {
		file string
		fn   func(string) ([]Match, error)
	}
	loaders := []loader{
		{dataFiles.brasileirao, loadBrasileirao},
		{dataFiles.cup, loadCup},
		{dataFiles.libertadores, loadLibertadores},
		{dataFiles.brFootball, loadBRFootball},
		{dataFiles.novo, loadNovo},
	}

	var all []Match
	for _, l := range loaders {
		matches, err := l.fn(filepath.Join(dataDir, l.file))
		if err != nil {
			return nil, err
		}
		all = append(all, matches...)
	}

	players, err := loadPlayers(filepath.Join(dataDir, dataFiles.fifa))
	if err != nil {
		return nil, err
	}

	db := &DB{
		AllMatches:  all,
		Matches:     canonicalize(all),
		Players:     players,
		teamDisplay: map[string]string{},
	}
	for _, m := range all {
		hk, ak := m.HomeID.groupKey(), m.AwayID.groupKey()
		db.teamDisplay[hk] = betterDisplay(db.teamDisplay[hk], m.HomeTeam)
		db.teamDisplay[ak] = betterDisplay(db.teamDisplay[ak], m.AwayTeam)
	}
	return db, nil
}

// resolveDataDir picks the first existing directory among the flag value, the
// SOCCER_DATA_DIR environment variable, and a path next to the executable.
func resolveDataDir(flagVal string) string {
	candidates := []string{}
	if env := strings.TrimSpace(os.Getenv("SOCCER_DATA_DIR")); env != "" {
		candidates = append(candidates, env)
	}
	candidates = append(candidates, flagVal)
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), flagVal))
	}
	for _, c := range candidates {
		if st, err := os.Stat(c); err == nil && st.IsDir() {
			return c
		}
	}
	return flagVal
}

// seasonsOf returns the sorted distinct seasons present in matches.
func seasonsOf(matches []Match) []int {
	set := map[int]bool{}
	for _, m := range matches {
		if m.Season > 0 {
			set[m.Season] = true
		}
	}
	out := make([]int, 0, len(set))
	for s := range set {
		out = append(out, s)
	}
	sort.Ints(out)
	return out
}
