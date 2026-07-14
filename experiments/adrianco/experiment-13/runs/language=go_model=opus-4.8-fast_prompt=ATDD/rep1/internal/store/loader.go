package store

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// Load builds a Store from the CSV datasets found under <dataDir>/kaggle.
// Missing files are tolerated (an absent dataset simply contributes nothing),
// which lets each test seed only the files it cares about.
func Load(dataDir string) (*Store, error) {
	kaggle := filepath.Join(dataDir, "kaggle")

	s := &Store{
		teamDisplay: map[string]string{},
		dedup:       map[string]bool{},
		loadedPairs: map[string]bool{},
		teamStates:  map[string]map[string]bool{},
	}

	// Files are processed in priority order: cleaner, more authoritative
	// sources first. When two datasets cover the same competition+season, only
	// the first (highest-priority) one is used for that season, so overlapping
	// datasets never double-count matches or invent phantom teams from naming
	// differences. Seasons a higher-priority file does not cover still load
	// from lower-priority files (e.g. pre-2012 Brasileirao, Serie B/C).
	loaders := []struct {
		file string
		fn   func(*Store, string) error
	}{
		{"Brasileirao_Matches.csv", (*Store).loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", (*Store).loadCopaDoBrasil},
		{"Libertadores_Matches.csv", (*Store).loadLibertadores},
		{"novo_campeonato_brasileiro.csv", (*Store).loadHistorical},
		{"BR-Football-Dataset.csv", (*Store).loadExtended},
		{"fifa_data.csv", (*Store).loadPlayers},
	}

	for _, l := range loaders {
		path := filepath.Join(kaggle, l.file)
		if _, err := os.Stat(path); err != nil {
			continue // dataset not present; skip
		}
		s.currentPairs = map[string]bool{}
		if err := l.fn(s, path); err != nil {
			return nil, fmt.Errorf("loading %s: %w", l.file, err)
		}
		for pair := range s.currentPairs {
			s.loadedPairs[pair] = true
		}
	}

	s.finalize()

	s.dedup = nil
	s.loadedPairs = nil
	s.currentPairs = nil
	s.teamStates = nil
	return s, nil
}

// openCSV opens a CSV file and returns a reader configured to tolerate the
// quirks in the provided datasets (variable field counts, BOMs, quotes).
func openCSV(path string) (*csv.Reader, *os.File, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // some rows have trailing/extra fields
	r.LazyQuotes = true
	r.ReuseRecord = false
	return r, f, nil
}

// readHeader reads the first row and returns a name->index column map. The first
// header cell may carry a UTF-8 BOM which is stripped.
func readHeader(r *csv.Reader) (map[string]int, error) {
	row, err := r.Read()
	if err != nil {
		return nil, err
	}
	cols := map[string]int{}
	for i, name := range row {
		name = strings.TrimPrefix(name, "\ufeff")
		cols[strings.TrimSpace(name)] = i
	}
	return cols, nil
}

// get safely fetches a column value by name from a record.
func get(rec []string, cols map[string]int, name string) string {
	if idx, ok := cols[name]; ok && idx < len(rec) {
		return rec[idx]
	}
	return ""
}

// addMatch records a match, applying de-duplication and team-name bookkeeping.
func (s *Store) addMatch(m Match) {
	homeBase := NormalizeTeam(m.HomeTeam)
	awayBase := NormalizeTeam(m.AwayTeam)
	if homeBase == "" || awayBase == "" {
		return
	}

	homeState := stateOrSuffix(m.HomeState, m.HomeTeam)
	awayState := stateOrSuffix(m.AwayState, m.AwayTeam)

	homeDisplay := CleanTeamName(m.HomeTeam)
	awayDisplay := CleanTeamName(m.AwayTeam)

	m.HomeKey = identityKey(homeBase, homeState)
	m.AwayKey = identityKey(awayBase, awayState)
	m.HomeTeam = homeDisplay
	m.AwayTeam = awayDisplay

	// Season-level source precedence: if an earlier (higher-priority) file
	// already supplied this competition+season, skip it here entirely.
	pair := fmt.Sprintf("%s|%d", m.Competition, m.Season)
	if s.loadedPairs != nil && s.loadedPairs[pair] {
		return
	}
	if s.currentPairs != nil {
		s.currentPairs[pair] = true
	}

	// Exact-duplicate guard (handles repeated rows within a single dataset).
	if s.dedup != nil {
		key := fmt.Sprintf("%s|%d|%s|%s|%d|%d", m.Competition, m.Season, m.HomeKey, m.AwayKey, m.HomeGoals, m.AwayGoals)
		if s.dedup[key] {
			return
		}
		s.dedup[key] = true
	}

	s.recordTeam(m.HomeKey, homeBase, homeState, homeDisplay)
	s.recordTeam(m.AwayKey, awayBase, awayState, awayDisplay)
	s.matches = append(s.matches, m)
}

// stateOrSuffix prefers an explicit UF column value, falling back to a state
// suffix parsed from the team name.
func stateOrSuffix(explicit, name string) string {
	if st := normState(explicit); st != "" {
		return st
	}
	return parseStateSuffix(name)
}

// normState lower-cases and validates a UF code, returning "" if not a state.
func normState(s string) string {
	s = strings.TrimSpace(s)
	if brazilianStates[strings.ToUpper(s)] {
		return strings.ToLower(s)
	}
	return ""
}

// recordTeam keeps the first display name seen for an identity key and tracks
// which states a base name appears under (for display disambiguation).
func (s *Store) recordTeam(key, base, state, display string) {
	if display != "" {
		if _, ok := s.teamDisplay[key]; !ok {
			s.teamDisplay[key] = display
		}
	}
	if s.teamStates[base] == nil {
		s.teamStates[base] = map[string]bool{}
	}
	if state != "" {
		s.teamStates[base][state] = true
	}
}

// finalize disambiguates display names for clubs that share a base name across
// different states (e.g. "Atletico (MG)" vs "Atletico (GO)") and rewrites each
// match's display names accordingly.
func (s *Store) finalize() {
	for key, disp := range s.teamDisplay {
		base, state := splitIdentity(key)
		if state != "" && len(s.teamStates[base]) > 1 {
			s.teamDisplay[key] = disp + " (" + strings.ToUpper(state) + ")"
		}
	}
	for i := range s.matches {
		s.matches[i].HomeTeam = s.display(s.matches[i].HomeKey)
		s.matches[i].AwayTeam = s.display(s.matches[i].AwayKey)
	}
}

func eachRow(r *csv.Reader, fn func(rec []string)) error {
	for {
		rec, err := r.Read()
		if err == io.EOF {
			return nil
		}
		if err != nil {
			// Skip malformed rows rather than aborting the whole dataset.
			continue
		}
		fn(rec)
	}
}

// --- Brasileirao_Matches.csv ------------------------------------------------

func (s *Store) loadBrasileirao(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	cols, err := readHeader(r)
	if err != nil {
		return err
	}
	return eachRow(r, func(rec []string) {
		hg, ok1 := parseGoal(get(rec, cols, "home_goal"))
		ag, ok2 := parseGoal(get(rec, cols, "away_goal"))
		if !ok1 || !ok2 {
			return
		}
		date, hasDate := ParseDate(get(rec, cols, "datetime"))
		s.addMatch(Match{
			Competition: CompBrasileirao,
			Season:      parseIntLoose(get(rec, cols, "season")),
			Round:       strings.TrimSpace(get(rec, cols, "round")),
			Date:        date,
			HasDate:     hasDate,
			HomeTeam:    get(rec, cols, "home_team"),
			AwayTeam:    get(rec, cols, "away_team"),
			HomeState:   get(rec, cols, "home_team_state"),
			AwayState:   get(rec, cols, "away_team_state"),
			HomeGoals:   hg,
			AwayGoals:   ag,
		})
	})
}

// --- Brazilian_Cup_Matches.csv ----------------------------------------------

func (s *Store) loadCopaDoBrasil(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	cols, err := readHeader(r)
	if err != nil {
		return err
	}
	return eachRow(r, func(rec []string) {
		hg, ok1 := parseGoal(get(rec, cols, "home_goal"))
		ag, ok2 := parseGoal(get(rec, cols, "away_goal"))
		if !ok1 || !ok2 {
			return
		}
		date, hasDate := ParseDate(get(rec, cols, "datetime"))
		s.addMatch(Match{
			Competition: CompCopaDoBrasil,
			Season:      parseIntLoose(get(rec, cols, "season")),
			Round:       strings.TrimSpace(get(rec, cols, "round")),
			Date:        date,
			HasDate:     hasDate,
			HomeTeam:    get(rec, cols, "home_team"),
			AwayTeam:    get(rec, cols, "away_team"),
			HomeGoals:   hg,
			AwayGoals:   ag,
		})
	})
}

// --- Libertadores_Matches.csv -----------------------------------------------

func (s *Store) loadLibertadores(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	cols, err := readHeader(r)
	if err != nil {
		return err
	}
	return eachRow(r, func(rec []string) {
		hg, ok1 := parseGoal(get(rec, cols, "home_goal"))
		ag, ok2 := parseGoal(get(rec, cols, "away_goal"))
		if !ok1 || !ok2 {
			return
		}
		date, hasDate := ParseDate(get(rec, cols, "datetime"))
		s.addMatch(Match{
			Competition: CompLibertadores,
			Season:      parseIntLoose(get(rec, cols, "season")),
			Stage:       strings.TrimSpace(get(rec, cols, "stage")),
			Date:        date,
			HasDate:     hasDate,
			HomeTeam:    get(rec, cols, "home_team"),
			AwayTeam:    get(rec, cols, "away_team"),
			HomeGoals:   hg,
			AwayGoals:   ag,
		})
	})
}

// --- novo_campeonato_brasileiro.csv -----------------------------------------

func (s *Store) loadHistorical(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	cols, err := readHeader(r)
	if err != nil {
		return err
	}
	return eachRow(r, func(rec []string) {
		hg, ok1 := parseGoal(get(rec, cols, "Gols_mandante"))
		ag, ok2 := parseGoal(get(rec, cols, "Gols_visitante"))
		if !ok1 || !ok2 {
			return
		}
		date, hasDate := ParseDate(get(rec, cols, "Data"))
		s.addMatch(Match{
			Competition: CompBrasileirao,
			Season:      parseIntLoose(get(rec, cols, "Ano")),
			Round:       strings.TrimSpace(get(rec, cols, "Rodada")),
			Date:        date,
			HasDate:     hasDate,
			HomeTeam:    get(rec, cols, "Equipe_mandante"),
			AwayTeam:    get(rec, cols, "Equipe_visitante"),
			HomeState:   get(rec, cols, "Mandante_UF"),
			AwayState:   get(rec, cols, "Visitante_UF"),
			HomeGoals:   hg,
			AwayGoals:   ag,
		})
	})
}

// --- BR-Football-Dataset.csv ------------------------------------------------

func (s *Store) loadExtended(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	cols, err := readHeader(r)
	if err != nil {
		return err
	}
	return eachRow(r, func(rec []string) {
		hg, ok1 := parseGoal(get(rec, cols, "home_goal"))
		ag, ok2 := parseGoal(get(rec, cols, "away_goal"))
		if !ok1 || !ok2 {
			return
		}
		date, hasDate := ParseDate(get(rec, cols, "date"))
		season := 0
		if hasDate {
			season = date.Year()
		}
		s.addMatch(Match{
			Competition: NormalizeCompetition(get(rec, cols, "tournament")),
			Season:      season,
			Date:        date,
			HasDate:     hasDate,
			HomeTeam:    get(rec, cols, "home"),
			AwayTeam:    get(rec, cols, "away"),
			HomeGoals:   hg,
			AwayGoals:   ag,
		})
	})
}

// --- fifa_data.csv ----------------------------------------------------------

func (s *Store) loadPlayers(path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()
	cols, err := readHeader(r)
	if err != nil {
		return err
	}
	return eachRow(r, func(rec []string) {
		name := strings.TrimSpace(get(rec, cols, "Name"))
		if name == "" {
			return
		}
		s.players = append(s.players, Player{
			ID:          strings.TrimSpace(get(rec, cols, "ID")),
			Name:        name,
			Age:         parseIntLoose(get(rec, cols, "Age")),
			Nationality: strings.TrimSpace(get(rec, cols, "Nationality")),
			Overall:     parseIntLoose(get(rec, cols, "Overall")),
			Potential:   parseIntLoose(get(rec, cols, "Potential")),
			Club:        strings.TrimSpace(get(rec, cols, "Club")),
			Position:    strings.TrimSpace(get(rec, cols, "Position")),
			JerseyNo:    strings.TrimSpace(get(rec, cols, "Jersey Number")),
			Height:      strings.TrimSpace(get(rec, cols, "Height")),
			Weight:      strings.TrimSpace(get(rec, cols, "Weight")),
		})
	})
}
