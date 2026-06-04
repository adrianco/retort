// Package store: CSV loading.
//
// Context:
//   - Each of the six datasets has a distinct schema; a dedicated parser per
//     file maps it onto the unified Match / Player model.
//   - Goals appear as ints ("2"), quoted ints, and floats ("1.0"); dates appear
//     as ISO datetimes and Brazilian DD/MM/YYYY. Helpers below tolerate all of
//     these and silently skip unparseable rows rather than failing the load.
//   - Files are read with encoding/csv (UTF-8); a leading BOM on fifa_data.csv
//     is stripped from the first header cell.
package store

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

// Store holds all loaded data.
type Store struct {
	Matches []Match
	Players []Player
}

// dataFiles maps each CSV filename to the parser that loads it.
var matchFiles = []struct {
	name  string
	parse func(rows [][]string) []Match
}{
	{"Brasileirao_Matches.csv", parseBrasileirao},
	{"Brazilian_Cup_Matches.csv", parseCopaDoBrasil},
	{"Libertadores_Matches.csv", parseLibertadores},
	{"BR-Football-Dataset.csv", parseBRFootball},
	{"novo_campeonato_brasileiro.csv", parseNovoCampeonato},
}

// Load reads every dataset from dir (typically "data/kaggle") into a Store.
// The match datasets overlap (e.g. the Brasileirão appears in both
// Brasileirao_Matches.csv and novo_campeonato_brasileiro.csv, and again as
// "Serie A" in BR-Football-Dataset.csv), so competition labels are canonicalized
// and identical fixtures are de-duplicated to keep standings/stats accurate.
func Load(dir string) (*Store, error) {
	s := &Store{}
	for _, f := range matchFiles {
		rows, err := readCSV(filepath.Join(dir, f.name))
		if err != nil {
			return nil, fmt.Errorf("load %s: %w", f.name, err)
		}
		if len(rows) < 2 {
			continue // empty or header-only file
		}
		s.Matches = append(s.Matches, f.parse(rows)...)
	}
	s.Matches = dedupMatches(s.Matches)
	players, err := loadPlayers(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, fmt.Errorf("load fifa_data.csv: %w", err)
	}
	s.Players = players
	return s, nil
}

// canonComp maps the many competition spellings across datasets onto canonical
// labels so the same fixture from different files lands in one bucket.
func canonComp(c string) string {
	lc := strings.ToLower(c)
	switch {
	case strings.Contains(lc, "serie b") || strings.Contains(lc, "série b"):
		return "Brasileirão Série B"
	case strings.Contains(lc, "serie c") || strings.Contains(lc, "série c"):
		return "Brasileirão Série C"
	case strings.Contains(lc, "serie a") || strings.Contains(lc, "série a"):
		return CompBrasileirao
	case strings.Contains(lc, "copa do brasil"):
		return CompCopaDoBrasil
	case strings.Contains(lc, "libertadores"):
		return CompLibertadores
	default:
		return c
	}
}

// authoritative lists competitions that have a dedicated, state-annotated source
// file. BR-Football-Dataset uses inconsistent club names without state codes, so
// its rows for these competitions cannot be reliably de-duplicated against the
// authoritative files; they are dropped to keep standings/stats correct.
// BR-Football still contributes its UNIQUE competitions (Série B, Série C).
var authoritative = map[string]bool{
	CompBrasileirao:  true,
	CompCopaDoBrasil: true,
	CompLibertadores: true,
}

// dedupKey identifies the same fixture across datasets: canonical competition,
// state-aware team keys, season, and date (when known).
func dedupKey(m Match) string {
	d := ""
	if m.HasDate {
		d = m.Date.Format("2006-01-02")
	}
	return strings.ToLower(m.Competition) + "|" +
		TeamKey(m.HomeTeam, m.HomeState) + "|" + TeamKey(m.AwayTeam, m.AwayState) + "|" +
		strconv.Itoa(m.Season) + "|" + d
}

// dedupMatches canonicalizes competition labels, drops BR-Football rows for
// competitions owned by an authoritative file, and removes duplicate fixtures,
// keeping the first occurrence (dedicated per-competition files load first and
// carry the richest metadata).
func dedupMatches(matches []Match) []Match {
	seen := make(map[string]struct{}, len(matches))
	out := matches[:0]
	for _, m := range matches {
		m.Competition = canonComp(m.Competition)
		if m.Source == "BR-Football-Dataset.csv" && authoritative[m.Competition] {
			continue // covered (and better named) by a dedicated file
		}
		key := dedupKey(m)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, m)
	}
	return out
}

// readCSV reads an entire CSV file, returning data rows (header dropped) plus
// the header as the caller may need it via column indices computed here.
func readCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // tolerate ragged rows
	r.LazyQuotes = true
	records, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(records) == 0 {
		return nil, nil
	}
	// Strip a UTF-8 BOM from the first cell of the header if present.
	records[0][0] = strings.TrimPrefix(records[0][0], "\uFEFF")
	return records, nil
}

// --- field parsing helpers ---

func parseGoal(s string) (int, bool) {
	s = strings.TrimSpace(strings.Trim(s, `"`))
	if s == "" {
		return 0, false
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func parseYear(s string) int {
	s = strings.TrimSpace(strings.Trim(s, `"`))
	if v, err := strconv.Atoi(s); err == nil {
		return v
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

// dateLayouts are tried in order against a trimmed date string.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006-01-02T15:04:05",
}

func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(strings.Trim(s, `"`))
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

// col safely indexes a row.
func col(row []string, i int) string {
	if i < 0 || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// --- per-dataset parsers ---

// Brasileirao_Matches.csv:
// datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
func parseBrasileirao(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		hg, ok1 := parseGoal(col(r, 5))
		ag, ok2 := parseGoal(col(r, 6))
		t, hasDate := parseDate(col(r, 0))
		out = append(out, Match{
			Competition: CompBrasileirao,
			Date:        t,
			HasDate:     hasDate,
			Season:      parseYear(col(r, 7)),
			Round:       col(r, 8),
			HomeTeam:    col(r, 1),
			AwayTeam:    col(r, 3),
			HomeState:   col(r, 2),
			AwayState:   col(r, 4),
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    ok1 && ok2,
			Source:      "Brasileirao_Matches.csv",
		})
	}
	return out
}

// Brazilian_Cup_Matches.csv:
// round,datetime,home_team,away_team,home_goal,away_goal,season
func parseCopaDoBrasil(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		hg, ok1 := parseGoal(col(r, 4))
		ag, ok2 := parseGoal(col(r, 5))
		t, hasDate := parseDate(col(r, 1))
		out = append(out, Match{
			Competition: CompCopaDoBrasil,
			Date:        t,
			HasDate:     hasDate,
			Season:      parseYear(col(r, 6)),
			Round:       col(r, 0),
			HomeTeam:    col(r, 2),
			AwayTeam:    col(r, 3),
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    ok1 && ok2,
			Source:      "Brazilian_Cup_Matches.csv",
		})
	}
	return out
}

// Libertadores_Matches.csv:
// datetime,home_team,away_team,home_goal,away_goal,season,stage
func parseLibertadores(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		hg, ok1 := parseGoal(col(r, 3))
		ag, ok2 := parseGoal(col(r, 4))
		t, hasDate := parseDate(col(r, 0))
		out = append(out, Match{
			Competition: CompLibertadores,
			Date:        t,
			HasDate:     hasDate,
			Season:      parseYear(col(r, 5)),
			Stage:       col(r, 6),
			HomeTeam:    col(r, 1),
			AwayTeam:    col(r, 2),
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    ok1 && ok2,
			Source:      "Libertadores_Matches.csv",
		})
	}
	return out
}

// BR-Football-Dataset.csv:
// tournament,home,home_goal,away_goal,away,...,date,...
func parseBRFootball(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		hg, ok1 := parseGoal(col(r, 2))
		ag, ok2 := parseGoal(col(r, 3))
		t, hasDate := parseDate(col(r, 12))
		comp := col(r, 0)
		if comp == "" {
			comp = "Other"
		}
		season := 0
		if hasDate {
			season = t.Year()
		}
		out = append(out, Match{
			Competition: comp,
			Date:        t,
			HasDate:     hasDate,
			Season:      season,
			HomeTeam:    col(r, 1),
			AwayTeam:    col(r, 4),
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    ok1 && ok2,
			Source:      "BR-Football-Dataset.csv",
		})
	}
	return out
}

// novo_campeonato_brasileiro.csv:
// ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
func parseNovoCampeonato(rows [][]string) []Match {
	var out []Match
	for _, r := range rows[1:] {
		hg, ok1 := parseGoal(col(r, 6))
		ag, ok2 := parseGoal(col(r, 7))
		t, hasDate := parseDate(col(r, 1))
		out = append(out, Match{
			Competition: CompBrasileirao,
			Date:        t,
			HasDate:     hasDate,
			Season:      parseYear(col(r, 2)),
			Round:       col(r, 3),
			HomeTeam:    col(r, 4),
			AwayTeam:    col(r, 5),
			HomeState:   col(r, 8),
			AwayState:   col(r, 9),
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    ok1 && ok2,
			Arena:       col(r, 11),
			Source:      "novo_campeonato_brasileiro.csv",
		})
	}
	return out
}

// loadPlayers parses fifa_data.csv into Player records. Column order is fixed
// per the dataset header (see TASK.md / README.md).
func loadPlayers(path string) ([]Player, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	header[0] = strings.TrimPrefix(header[0], "\uFEFF")
	idx := map[string]int{}
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}
	get := func(row []string, name string) string {
		if i, ok := idx[name]; ok {
			return col(row, i)
		}
		return ""
	}
	atoi := func(s string) int {
		v, _ := strconv.Atoi(strings.TrimSpace(s))
		return v
	}

	var players []Player
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		players = append(players, Player{
			ID:          atoi(get(row, "ID")),
			Name:        get(row, "Name"),
			Age:         atoi(get(row, "Age")),
			Nationality: get(row, "Nationality"),
			Overall:     atoi(get(row, "Overall")),
			Potential:   atoi(get(row, "Potential")),
			Club:        get(row, "Club"),
			Position:    get(row, "Position"),
			JerseyNum:   get(row, "Jersey Number"),
			Height:      get(row, "Height"),
			Weight:      get(row, "Weight"),
		})
	}
	return players, nil
}
