// Context: CSV ingestion. Each Load* function parses one dataset described in
// TASK.md into Match/Player structs, applying team-name normalization and
// tolerant date/number parsing. Load wires all six files into a single DB.
// Parsing is deliberately lenient: a malformed cell is skipped rather than
// aborting the whole load, since the goal is a usable demo knowledge base.
package soccer

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

// DB is the in-memory knowledge base.
type DB struct {
	Matches []Match
	Players []Player

	// aliases maps a bare (suffix-less) team key to its unambiguous canonical
	// key, e.g. "flamengo" -> "flamengo-rj". Only populated for teams that are
	// seen with exactly one state, so genuinely ambiguous names like "atletico"
	// (MG/PR/GO) are left bare. Used to resolve user queries and FIFA club names
	// to the same keys stored on matches.
	aliases map[string]string
}

// Load reads all six CSV files from dir and returns a populated DB. Missing
// files are reported as errors but loading continues for the rest, so a partial
// dataset still yields a usable DB.
func Load(dir string) (*DB, error) {
	db := &DB{}
	var errs []string

	type matchFile struct {
		name string
		fn   func(io.Reader) ([]Match, error)
	}
	files := []matchFile{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadExtended},
		{"novo_campeonato_brasileiro.csv", loadHistorical},
	}
	for _, f := range files {
		ms, err := withFile(filepath.Join(dir, f.name), f.fn)
		if err != nil {
			errs = append(errs, fmt.Sprintf("%s: %v", f.name, err))
			continue
		}
		db.Matches = append(db.Matches, ms...)
	}

	// The datasets overlap heavily (the same Brasileirão season appears in three
	// files) but use inconsistent team naming, so row-level fuzzy dedup is
	// unreliable. Instead we pick a single authoritative source per
	// (competition, season); within one source naming is consistent and counts
	// are correct. A light exact-dedup then removes any intra-source repeats.
	// Order matters: keys are still bare here, then we learn state-aware aliases
	// from the survivors and promote.
	db.Matches = selectBestSource(db.Matches)
	db.Matches = dedupeMatches(db.Matches)
	db.aliases = buildAliases(db.Matches)
	db.promoteMatchKeys()

	players, err := withFile(filepath.Join(dir, "fifa_data.csv"), loadPlayers)
	if err != nil {
		errs = append(errs, fmt.Sprintf("fifa_data.csv: %v", err))
	} else {
		db.Players = players
	}
	// Resolve FIFA club keys through the same alias map so club queries align
	// with team match keys.
	for i := range db.Players {
		db.Players[i].ClubKey = db.canonicalKey(db.Players[i].Club)
	}

	if len(errs) > 0 {
		return db, fmt.Errorf("load errors: %s", strings.Join(errs, "; "))
	}
	return db, nil
}

// sourcePriority ranks the datasets when more than one covers the same
// (competition, season). The dedicated single-competition files are preferred
// over the broad BR-Football dataset because they carry state codes and cleaner
// naming; for Brasileirão the historical file (which includes the state UF and
// stadium) outranks the modern file.
func sourcePriority(source string) int {
	switch source {
	case "novo_campeonato_brasileiro.csv":
		return 3
	case "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv":
		return 3
	case "Brasileirao_Matches.csv":
		return 2
	case "BR-Football-Dataset.csv":
		return 1
	default:
		return 1
	}
}

// selectBestSource keeps, for each (competition, season), only the rows from the
// single highest-priority source present. This avoids double counting a season
// that appears in multiple datasets while preserving seasons/competitions (e.g.
// Série B/C) that exist in only one file.
func selectBestSource(ms []Match) []Match {
	best := map[string]int{}
	groupKey := func(m Match) string {
		return m.Competition + "\x00" + fmt.Sprint(m.Season)
	}
	for _, m := range ms {
		k := groupKey(m)
		if p := sourcePriority(m.Source); p > best[k] {
			best[k] = p
		}
	}
	out := make([]Match, 0, len(ms))
	for _, m := range ms {
		if sourcePriority(m.Source) == best[groupKey(m)] {
			out = append(out, m)
		}
	}
	return out
}

// fullKey combines a bare team key with a state/country code, e.g.
// ("flamengo", "RJ") -> "flamengo-rj".
func fullKey(bare, state string) string {
	if state == "" {
		return bare
	}
	return bare + "-" + strings.ToLower(state)
}

// buildAliases scans all match rows and, for each bare team key that is only
// ever associated with a single state, records the canonical state-qualified
// key. Bare keys seen with multiple states (e.g. several "Atlético"/"América"
// clubs) are intentionally omitted, leaving them ambiguous.
func buildAliases(ms []Match) map[string]string {
	states := map[string]map[string]bool{}
	note := func(bare, state string) {
		if bare == "" || state == "" {
			return
		}
		if states[bare] == nil {
			states[bare] = map[string]bool{}
		}
		states[bare][strings.ToLower(state)] = true
	}
	for _, m := range ms {
		note(m.HomeKey, m.HomeState)
		note(m.AwayKey, m.AwayState)
	}
	aliases := make(map[string]string, len(states))
	for bare, set := range states {
		if len(set) == 1 {
			for st := range set {
				aliases[bare] = bare + "-" + st
			}
		}
	}
	return aliases
}

// canonicalKey resolves a human-entered or raw team name to the canonical key
// used on match rows: state-qualified when a state is known or can be inferred,
// otherwise the bare key.
func (db *DB) canonicalKey(name string) string {
	bare := teamKey(name)
	if bare == "" {
		return ""
	}
	if st := suffixState(name); st != "" {
		return fullKey(bare, st)
	}
	if canon, ok := db.aliases[bare]; ok {
		return canon
	}
	return bare
}

// promoteMatchKeys rewrites the bare HomeKey/AwayKey set during loading to their
// canonical state-aware form using the per-row state and the alias map.
func (db *DB) promoteMatchKeys() {
	resolve := func(bare, state string) string {
		if state != "" {
			return fullKey(bare, state)
		}
		if canon, ok := db.aliases[bare]; ok {
			return canon
		}
		return bare
	}
	for i := range db.Matches {
		db.Matches[i].HomeKey = resolve(db.Matches[i].HomeKey, db.Matches[i].HomeState)
		db.Matches[i].AwayKey = resolve(db.Matches[i].AwayKey, db.Matches[i].AwayState)
	}
}

// dedupeMatches collapses the same real fixture appearing in more than one
// dataset (e.g. a 2019 Brasileirão game present in Brasileirao_Matches.csv,
// novo_campeonato_brasileiro.csv, and BR-Football-Dataset.csv). Without this,
// records and standings are multiply counted. Matches are keyed by competition,
// season, the two team keys, and the match day; when a day is unavailable the
// round/stage is used to keep distinct fixtures apart. On collision we keep the
// first occurrence but copy in extended statistics or a missing date/score from
// the duplicate so no information is lost.
func dedupeMatches(in []Match) []Match {
	seen := make(map[string]int, len(in))
	out := make([]Match, 0, len(in))
	for _, m := range in {
		day := ""
		if m.HasDate {
			day = m.Date.Format("2006-01-02")
		}
		disc := day
		if disc == "" {
			disc = m.Round + "|" + m.Stage
		}
		key := strings.Join([]string{m.Competition, fmt.Sprint(m.Season), m.HomeKey, m.AwayKey, disc}, "\x00")
		if idx, ok := seen[key]; ok {
			merge(&out[idx], m)
			continue
		}
		seen[key] = len(out)
		out = append(out, m)
	}
	return out
}

// merge folds information from dup into the kept match without overwriting
// existing values.
func merge(kept *Match, dup Match) {
	if !kept.HasStats && dup.HasStats {
		kept.HasStats = true
		kept.HomeShots, kept.AwayShots = dup.HomeShots, dup.AwayShots
		kept.HomeCorners, kept.AwayCorners = dup.HomeCorners, dup.AwayCorners
		kept.HomeAttacks, kept.AwayAttacks = dup.HomeAttacks, dup.AwayAttacks
	}
	if !kept.HasScore && dup.HasScore {
		kept.HomeGoals, kept.AwayGoals, kept.HasScore = dup.HomeGoals, dup.AwayGoals, true
	}
	if !kept.HasDate && dup.HasDate {
		kept.Date, kept.HasDate = dup.Date, true
	}
	if kept.Stadium == "" {
		kept.Stadium = dup.Stadium
	}
	if kept.Round == "" {
		kept.Round = dup.Round
	}
	if kept.HomeState == "" {
		kept.HomeState = dup.HomeState
	}
	if kept.AwayState == "" {
		kept.AwayState = dup.AwayState
	}
}

func withFile[T any](path string, fn func(io.Reader) ([]T, error)) ([]T, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return fn(f)
}

// newReader returns a CSV reader tolerant of ragged rows and stray BOMs.
func newReader(r io.Reader) *csv.Reader {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1
	cr.LazyQuotes = true
	cr.ReuseRecord = true
	return cr
}

// header maps column name -> index, trimming the UTF-8 BOM from the first cell.
func header(row []string) map[string]int {
	h := make(map[string]int, len(row))
	for i, c := range row {
		c = strings.TrimPrefix(c, "\ufeff")
		h[strings.TrimSpace(c)] = i
	}
	return h
}

func get(row []string, idx int) string {
	if idx < 0 || idx >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[idx])
}

func atoi(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	// Some numeric columns are floats like "2.0".
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

// parseDate accepts the several formats seen across datasets.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	layouts := []string{
		"2006-01-02 15:04:05",
		"2006-01-02",
		"02/01/2006",
		"2006-01-02T15:04:05",
	}
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

func setTeams(m *Match, homeRaw, awayRaw, homeState, awayState string) {
	m.HomeRaw, m.AwayRaw = homeRaw, awayRaw
	m.HomeTeam, m.AwayTeam = cleanTeamName(homeRaw), cleanTeamName(awayRaw)
	// HomeKey/AwayKey start as the *bare* (suffix-stripped) key; Load promotes
	// them to canonical, state-aware keys once all rows are seen.
	m.HomeKey, m.AwayKey = teamKey(homeRaw), teamKey(awayRaw)
	if homeState == "" {
		homeState = suffixState(homeRaw)
	}
	if awayState == "" {
		awayState = suffixState(awayRaw)
	}
	m.HomeState, m.AwayState = homeState, awayState
}

func loadBrasileirao(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	first, err := cr.Read()
	if err != nil {
		return nil, err
	}
	h := header(first)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{Competition: CompBrasileirao, Source: "Brasileirao_Matches.csv"}
		setTeams(&m, get(row, h["home_team"]), get(row, h["away_team"]),
			get(row, h["home_team_state"]), get(row, h["away_team_state"]))
		if t, ok := parseDate(get(row, h["datetime"])); ok {
			m.Date, m.HasDate = t, true
		}
		m.Season, _ = atoi(get(row, h["season"]))
		m.Round = get(row, h["round"])
		hg, ok1 := atoi(get(row, h["home_goal"]))
		ag, ok2 := atoi(get(row, h["away_goal"]))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		out = append(out, m)
	}
	return out, nil
}

func loadCup(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	first, err := cr.Read()
	if err != nil {
		return nil, err
	}
	h := header(first)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{Competition: CompCopaDoBrasil, Source: "Brazilian_Cup_Matches.csv"}
		setTeams(&m, get(row, h["home_team"]), get(row, h["away_team"]), "", "")
		if t, ok := parseDate(get(row, h["datetime"])); ok {
			m.Date, m.HasDate = t, true
		}
		m.Season, _ = atoi(get(row, h["season"]))
		m.Round = get(row, h["round"])
		hg, ok1 := atoi(get(row, h["home_goal"]))
		ag, ok2 := atoi(get(row, h["away_goal"]))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		out = append(out, m)
	}
	return out, nil
}

func loadLibertadores(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	first, err := cr.Read()
	if err != nil {
		return nil, err
	}
	h := header(first)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{Competition: CompLibertadores, Source: "Libertadores_Matches.csv"}
		setTeams(&m, get(row, h["home_team"]), get(row, h["away_team"]), "", "")
		if t, ok := parseDate(get(row, h["datetime"])); ok {
			m.Date, m.HasDate = t, true
		}
		m.Season, _ = atoi(get(row, h["season"]))
		m.Stage = get(row, h["stage"])
		hg, ok1 := atoi(get(row, h["home_goal"]))
		ag, ok2 := atoi(get(row, h["away_goal"]))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		out = append(out, m)
	}
	return out, nil
}

// loadExtended parses BR-Football-Dataset.csv, mapping the tournament column to
// a canonical competition and capturing extended match statistics.
func loadExtended(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	first, err := cr.Read()
	if err != nil {
		return nil, err
	}
	h := header(first)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{Competition: canonComp(get(row, h["tournament"])), Source: "BR-Football-Dataset.csv"}
		setTeams(&m, get(row, h["home"]), get(row, h["away"]), "", "")
		if t, ok := parseDate(get(row, h["date"])); ok {
			m.Date, m.HasDate = t, true
			m.Season = t.Year()
		}
		hg, ok1 := atoi(get(row, h["home_goal"]))
		ag, ok2 := atoi(get(row, h["away_goal"]))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		m.HomeShots, _ = atoi(get(row, h["home_shots"]))
		m.AwayShots, _ = atoi(get(row, h["away_shots"]))
		m.HomeCorners, _ = atoi(get(row, h["home_corner"]))
		m.AwayCorners, _ = atoi(get(row, h["away_corner"]))
		m.HomeAttacks, _ = atoi(get(row, h["home_attack"]))
		m.AwayAttacks, _ = atoi(get(row, h["away_attack"]))
		m.HasStats = true
		out = append(out, m)
	}
	return out, nil
}

func loadHistorical(r io.Reader) ([]Match, error) {
	cr := newReader(r)
	first, err := cr.Read()
	if err != nil {
		return nil, err
	}
	h := header(first)
	var out []Match
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{Competition: CompBrasileirao, Source: "novo_campeonato_brasileiro.csv"}
		setTeams(&m, get(row, h["Equipe_mandante"]), get(row, h["Equipe_visitante"]),
			get(row, h["Mandante_UF"]), get(row, h["Visitante_UF"]))
		if t, ok := parseDate(get(row, h["Data"])); ok {
			m.Date, m.HasDate = t, true
		}
		m.Season, _ = atoi(get(row, h["Ano"]))
		m.Round = get(row, h["Rodada"])
		m.Stadium = get(row, h["Arena"])
		hg, ok1 := atoi(get(row, h["Gols_mandante"]))
		ag, ok2 := atoi(get(row, h["Gols_visitante"]))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, ok1 && ok2
		out = append(out, m)
	}
	return out, nil
}

// canonComp maps free-text tournament names to a canonical competition label.
func canonComp(s string) string {
	k := matchKey(s)
	switch {
	case strings.Contains(k, "serie a"), strings.Contains(k, "brasileir"):
		return CompBrasileirao
	case strings.Contains(k, "copa do brasil"):
		return CompCopaDoBrasil
	case strings.Contains(k, "libertadores"):
		return CompLibertadores
	case s == "":
		return CompOther
	default:
		return s
	}
}

func loadPlayers(r io.Reader) ([]Player, error) {
	cr := newReader(r)
	first, err := cr.Read()
	if err != nil {
		return nil, err
	}
	h := header(first)
	var out []Player
	for {
		row, err := cr.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		p := Player{
			Name:          get(row, h["Name"]),
			Nationality:   get(row, h["Nationality"]),
			Club:          get(row, h["Club"]),
			Position:      get(row, h["Position"]),
			JerseyNumber:  get(row, h["Jersey Number"]),
			Height:        get(row, h["Height"]),
			Weight:        get(row, h["Weight"]),
			PreferredFoot: get(row, h["Preferred Foot"]),
			Value:         get(row, h["Value"]),
			Wage:          get(row, h["Wage"]),
		}
		if p.Name == "" {
			continue
		}
		p.ID, _ = atoi(get(row, h["ID"]))
		p.Age, _ = atoi(get(row, h["Age"]))
		p.Overall, _ = atoi(get(row, h["Overall"]))
		p.Potential, _ = atoi(get(row, h["Potential"]))
		p.NameKey = matchKey(p.Name)
		p.ClubKey = teamKey(p.Club)
		out = append(out, p)
	}
	return out, nil
}
