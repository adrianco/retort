// load.go reads the six Kaggle CSV files into the knowledge graph. It handles
// the differing column layouts, multiple date formats, float-encoded goals and
// UTF-8 BOMs, and de-duplicates fixtures that appear in more than one source.
package soccer

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// dateLayouts are tried in order when parsing a match date.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02 15:04",
	"2006-01-02",
	"02/01/2006",
	"2006/01/02",
}

// parseDate attempts to parse s using the known layouts.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(strings.Trim(strings.TrimSpace(s), `"`))
	if s == "" {
		return time.Time{}, false
	}
	for _, l := range dateLayouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// parseGoals parses a goal count that may be quoted ("2"), float-encoded
// ("2.0") or empty.
func parseGoals(s string) (int, bool) {
	s = strings.TrimSpace(strings.Trim(strings.TrimSpace(s), `"`))
	if s == "" {
		return 0, false
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func parseIntField(s string) int {
	s = strings.TrimSpace(strings.Trim(strings.TrimSpace(s), `"`))
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

// table is a CSV decoded into a header index plus rows.
type table struct {
	idx  map[string]int
	rows [][]string
}

// col returns the value of the named column for a row, or "" if absent.
func (t table) col(row []string, name string) string {
	i, ok := t.idx[name]
	if !ok || i >= len(row) {
		return ""
	}
	return row[i]
}

// readTable parses a CSV file, stripping a leading UTF-8 BOM from the first
// header cell so columns line up.
func readTable(path string) (table, error) {
	f, err := os.Open(path)
	if err != nil {
		return table{}, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // tolerate ragged rows
	r.LazyQuotes = true

	records, err := r.ReadAll()
	if err != nil {
		return table{}, fmt.Errorf("parsing %s: %w", path, err)
	}
	if len(records) == 0 {
		return table{}, fmt.Errorf("%s: empty file", path)
	}

	header := records[0]
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}
	return table{idx: idx, rows: records[1:]}, nil
}

// Load reads every supported CSV found under dir and returns the populated DB.
// Missing files are skipped (with the names recorded in skipped) so the server
// can still start with a partial dataset.
func Load(dir string) (*DB, error) {
	db := newDB()

	type spec struct {
		file   string
		loader func(*DB, table)
	}
	// Order matters: richer, dedicated sources are loaded before the broad
	// BR-Football dataset so that de-duplication keeps the richer record.
	specs := []spec{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"novo_campeonato_brasileiro.csv", loadNovo},
		{"BR-Football-Dataset.csv", loadBRFootball},
		{"fifa_data.csv", loadPlayers},
	}

	loadedAny := false
	for _, s := range specs {
		path := filepath.Join(dir, s.file)
		t, err := readTable(path)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return nil, err
		}
		s.loader(db, t)
		loadedAny = true
	}
	if !loadedAny {
		return nil, fmt.Errorf("no data files found in %q", dir)
	}

	db.selectCoverage()
	db.finalizeTeams()
	return db, nil
}

// sourcePriority ranks data sources when more than one covers the same
// competition+season. Lower wins. The dedicated, round-annotated files are
// preferred; the broad BR-Football dataset is the fallback that fills gaps
// (Série B/C and seasons the dedicated files do not reach).
func sourcePriority(source string) int {
	switch source {
	case "novo_campeonato_brasileiro.csv": // Série A 2003-2019, richest
		return 0
	case "Brazilian_Cup_Matches.csv": // Copa do Brasil
		return 0
	case "Libertadores_Matches.csv": // Libertadores
		return 0
	case "Brasileirao_Matches.csv": // Série A 2012-2022
		return 1
	case "BR-Football-Dataset.csv": // broad fallback
		return 5
	default:
		return 9
	}
}

// addMatch records the home/away team names (with optional state hints from a
// dedicated column) on the match and appends it. Canonical keys are resolved
// later by finalizeTeams once the full set of region variants is known.
func (db *DB) addMatch(m Match, home, away, homeState, awayState string) {
	m.homeBase, m.homeRegion, m.homeDisplay = resolveTeam(home, homeState)
	m.awayBase, m.awayRegion, m.awayDisplay = resolveTeam(away, awayState)
	if m.homeBase == "" || m.awayBase == "" {
		return
	}
	db.Matches = append(db.Matches, m)
}

// resolveTeam splits a raw name and falls back to an explicit state column when
// the name itself carries no region suffix.
func resolveTeam(raw, state string) (base, region, display string) {
	base, region, display = splitTeam(raw)
	if region == "" {
		if s := strings.ToLower(strings.TrimSpace(state)); s != "" {
			region = s
		}
	}
	return base, region, display
}

func loadBrasileirao(db *DB, t table) {
	for _, row := range t.rows {
		date, hasDate := parseDate(t.col(row, "datetime"))
		hg, hs := parseGoals(t.col(row, "home_goal"))
		ag, as := parseGoals(t.col(row, "away_goal"))
		m := Match{
			Competition: CompBrasileiraoA,
			Season:      parseIntField(t.col(row, "season")),
			Round:       strings.TrimSpace(t.col(row, "round")),
			Date:        date,
			HasDate:     hasDate,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    hs && as,
			Source:      "Brasileirao_Matches.csv",
		}
		db.addMatch(m, t.col(row, "home_team"), t.col(row, "away_team"),
			t.col(row, "home_team_state"), t.col(row, "away_team_state"))
	}
}

func loadCup(db *DB, t table) {
	for _, row := range t.rows {
		date, hasDate := parseDate(t.col(row, "datetime"))
		hg, hs := parseGoals(t.col(row, "home_goal"))
		ag, as := parseGoals(t.col(row, "away_goal"))
		m := Match{
			Competition: CompCopaDoBrasil,
			Season:      parseIntField(t.col(row, "season")),
			Round:       strings.TrimSpace(t.col(row, "round")),
			Date:        date,
			HasDate:     hasDate,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    hs && as,
			Source:      "Brazilian_Cup_Matches.csv",
		}
		db.addMatch(m, t.col(row, "home_team"), t.col(row, "away_team"), "", "")
	}
}

func loadLibertadores(db *DB, t table) {
	for _, row := range t.rows {
		date, hasDate := parseDate(t.col(row, "datetime"))
		hg, hs := parseGoals(t.col(row, "home_goal"))
		ag, as := parseGoals(t.col(row, "away_goal"))
		m := Match{
			Competition: CompLibertadores,
			Season:      parseIntField(t.col(row, "season")),
			Stage:       strings.TrimSpace(t.col(row, "stage")),
			Date:        date,
			HasDate:     hasDate,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    hs && as,
			Source:      "Libertadores_Matches.csv",
		}
		db.addMatch(m, t.col(row, "home_team"), t.col(row, "away_team"), "", "")
	}
}

func loadNovo(db *DB, t table) {
	for _, row := range t.rows {
		date, hasDate := parseDate(t.col(row, "Data"))
		hg, hs := parseGoals(t.col(row, "Gols_mandante"))
		ag, as := parseGoals(t.col(row, "Gols_visitante"))
		m := Match{
			Competition: CompBrasileiraoA,
			Season:      parseIntField(t.col(row, "Ano")),
			Round:       strings.TrimSpace(t.col(row, "Rodada")),
			Stadium:     strings.TrimSpace(t.col(row, "Arena")),
			Date:        date,
			HasDate:     hasDate,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    hs && as,
			Source:      "novo_campeonato_brasileiro.csv",
		}
		db.addMatch(m, t.col(row, "Equipe_mandante"), t.col(row, "Equipe_visitante"),
			t.col(row, "Mandante_UF"), t.col(row, "Visitante_UF"))
	}
}

func loadBRFootball(db *DB, t table) {
	for _, row := range t.rows {
		date, hasDate := parseDate(t.col(row, "date"))
		hg, hs := parseGoals(t.col(row, "home_goal"))
		ag, as := parseGoals(t.col(row, "away_goal"))
		season := 0
		if hasDate {
			season = date.Year()
		}
		m := Match{
			Competition: NormalizeCompetition(t.col(row, "tournament")),
			Season:      season,
			Date:        date,
			HasDate:     hasDate,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasScore:    hs && as,
			HomeShots:   parseIntField(t.col(row, "home_shots")),
			AwayShots:   parseIntField(t.col(row, "away_shots")),
			HomeCorners: parseIntField(t.col(row, "home_corner")),
			AwayCorners: parseIntField(t.col(row, "away_corner")),
			HasStats:    true,
			Source:      "BR-Football-Dataset.csv",
		}
		db.addMatch(m, t.col(row, "home"), t.col(row, "away"), "", "")
	}
}

func loadPlayers(db *DB, t table) {
	for _, row := range t.rows {
		name := strings.TrimSpace(t.col(row, "Name"))
		if name == "" {
			continue
		}
		p := Player{
			ID:            parseIntField(t.col(row, "ID")),
			Name:          name,
			Age:           parseIntField(t.col(row, "Age")),
			Nationality:   strings.TrimSpace(t.col(row, "Nationality")),
			Overall:       parseIntField(t.col(row, "Overall")),
			Potential:     parseIntField(t.col(row, "Potential")),
			Club:          strings.TrimSpace(t.col(row, "Club")),
			Position:      strings.TrimSpace(t.col(row, "Position")),
			JerseyNumber:  strings.TrimSpace(t.col(row, "Jersey Number")),
			Height:        strings.TrimSpace(t.col(row, "Height")),
			Weight:        strings.TrimSpace(t.col(row, "Weight")),
			PreferredFoot: strings.TrimSpace(t.col(row, "Preferred Foot")),
		}
		db.Players = append(db.Players, p)
	}
}

// selectCoverage eliminates cross-source duplication. Several datasets cover
// the same competition and season (e.g. Brasileirão Série A 2019 appears in
// three files) but with differing team-name spellings, so per-fixture
// de-duplication is unreliable. Instead, for each (competition, season) we keep
// matches from a single authoritative source — the one with the best priority
// among those that cover that pair — which guarantees a clean, non-overlapping
// fixture set for standings and aggregate statistics.
func (db *DB) selectCoverage() {
	type cs struct {
		comp   string
		season int
	}
	best := map[cs]int{}
	for _, m := range db.Matches {
		k := cs{m.Competition, m.Season}
		p := sourcePriority(m.Source)
		if cur, ok := best[k]; !ok || p < cur {
			best[k] = p
		}
	}

	out := db.Matches[:0]
	for _, m := range db.Matches {
		if sourcePriority(m.Source) == best[cs{m.Competition, m.Season}] {
			out = append(out, m)
		}
	}
	db.Matches = out
}

// finalizeTeams resolves each match's intermediate team fields into canonical
// keys and builds the team registry. A base name (e.g. "atletico") is only
// disambiguated by its region when it is genuinely shared by two or more
// clubs from different states; unambiguous clubs keep a region-free key so
// their fixtures merge across sources that spell the name differently.
func (db *DB) finalizeTeams() {
	// Count appearances of each (base, region) pair so we can tell a genuinely
	// shared name (e.g. the three big Atléticos) from a famous club that merely
	// has a tiny lower-division namesake (Flamengo-RJ vs the 2-match Flamengo-PI).
	regionsByBase := map[string]map[string]int{}
	note := func(base, region string) {
		if base == "" || region == "" {
			return
		}
		set := regionsByBase[base]
		if set == nil {
			set = map[string]int{}
			regionsByBase[base] = set
		}
		set[region]++
	}
	for _, m := range db.Matches {
		note(m.homeBase, m.homeRegion)
		note(m.awayBase, m.awayRegion)
	}
	// A base is ambiguous only if at least two of its regions are "major"
	// (appear in a meaningful number of matches), so distinct same-named clubs
	// are separated while incidental namesakes fold into the dominant club.
	const minMajorMatches = 10
	ambiguous := func(base string) bool {
		major := 0
		for _, n := range regionsByBase[base] {
			if n >= minMajorMatches {
				major++
			}
		}
		return major >= 2
	}

	keyFor := func(base, region string) string {
		if base == "" {
			return ""
		}
		if ambiguous(base) && region != "" {
			return base + " " + region
		}
		return base
	}

	db.teams = map[string]string{}
	register := func(key, base, region, display string) {
		if key == "" {
			return
		}
		if ambiguous(base) && region != "" {
			display = display + " (" + strings.ToUpper(region) + ")"
		}
		if cur, ok := db.teams[key]; !ok || len(display) < len(cur) {
			db.teams[key] = display
		}
	}

	out := db.Matches[:0]
	for _, m := range db.Matches {
		m.HomeKey = keyFor(m.homeBase, m.homeRegion)
		m.AwayKey = keyFor(m.awayBase, m.awayRegion)
		if m.HomeKey == "" || m.AwayKey == "" {
			continue
		}
		register(m.HomeKey, m.homeBase, m.homeRegion, m.homeDisplay)
		register(m.AwayKey, m.awayBase, m.awayRegion, m.awayDisplay)
		out = append(out, m)
	}
	db.Matches = out
}
