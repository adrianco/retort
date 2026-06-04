// loader.go - parsing of the six Kaggle CSV datasets into the unified DB.
//
// Context
// -------
// All data ingestion lives here. Each CSV has its own column layout, date format
// and quirks (BOM on the FIFA header, quoted numeric goals in the Libertadores
// file, DD/MM/YYYY dates in the historical Brasileirão file). To keep callers
// decoupled from the filesystem layout, loading is driven by an fs.FS: the
// command embeds the data with go:embed, while tests point an os.DirFS at the
// repository's data directory.
//
// Datasets are read in priority order and de-duplicated on a
// (competition, season, day, home, away) key so a fixture present in more than
// one file is stored once. When a later (lower priority) duplicate carries
// extended statistics that the kept record lacks, those stats are merged in.
package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"io/fs"
	"strconv"
	"strings"
	"time"
)

// matchFile describes how to load one match dataset.
type matchFile struct {
	name        string
	competition string // fixed canonical competition, or "" to derive per row
}

// matchFiles lists the match datasets to ingest.
var matchFiles = []matchFile{
	{name: "Brasileirao_Matches.csv", competition: CompBrasileirao},
	{name: "Brazilian_Cup_Matches.csv", competition: CompCopaDoBrasil},
	{name: "Libertadores_Matches.csv", competition: CompLibertadores},
	{name: "novo_campeonato_brasileiro.csv", competition: CompBrasileirao},
	{name: "BR-Football-Dataset.csv", competition: ""}, // derived from tournament
}

// sourcePriority breaks ties when two datasets cover the same competition and
// season with the same number of matches. Lower wins. The historical Brasileirão
// file is preferred because it names the two "Atléticos" distinctly (Atlético-MG
// vs Athletico-PR), avoiding the suffix collision present in other files.
var sourcePriority = map[string]int{
	"novo_campeonato_brasileiro.csv": 0,
	"Brasileirao_Matches.csv":        1,
	"Brazilian_Cup_Matches.csv":      2,
	"Libertadores_Matches.csv":       3,
	"BR-Football-Dataset.csv":        4,
}

// Load reads every known dataset from fsys (files expected at the root of fsys)
// and returns a populated DB.
//
// The same fixture frequently appears in more than one dataset, and the datasets
// disagree on team spelling. Merging across files would therefore both
// double-count matches and split a single club into several differently-named
// entities. Instead, for each (competition, season) we keep matches from a
// single authoritative source — the file with the most matches for that bucket,
// ties broken by sourcePriority — so every computed table comes from one
// internally consistent file.
func Load(fsys fs.FS) (*DB, error) {
	db := &DB{}

	var all []*Match
	for _, mf := range matchFiles {
		rows, header, err := readCSV(fsys, mf.name)
		if err != nil {
			return nil, fmt.Errorf("loading %s: %w", mf.name, err)
		}
		idx := indexHeader(header)
		for _, row := range rows {
			if m := parseMatchRow(mf, idx, row); m != nil {
				all = append(all, m)
			}
		}
	}

	chosen := chooseSources(all)
	seen := make(map[string]bool)
	for _, m := range all {
		if m.Source != chosen[groupKey(m)] {
			continue
		}
		key := dedupKey(m)
		if seen[key] {
			continue // drop exact duplicate fixtures within a source
		}
		seen[key] = true
		db.Matches = append(db.Matches, m)
	}

	players, err := loadPlayers(fsys, "fifa_data.csv")
	if err != nil {
		return nil, err
	}
	db.Players = players

	return db, nil
}

// groupKey identifies a (competition, season) bucket.
func groupKey(m *Match) string {
	return m.Competition + "|" + strconv.Itoa(m.Season)
}

// srcCount tracks how many matches (and how many of them scored) a source
// contributes to a bucket.
type srcCount struct {
	scored int
	total  int
}

// chooseSources returns, for each (competition, season) bucket, the source file
// that should supply its matches. Selection prefers the source with the most
// *scored* matches (some files, e.g. recent Brasileirão seasons, carry fixtures
// with blank scores), falling back to total match count, then sourcePriority.
func chooseSources(all []*Match) map[string]string {
	counts := map[string]map[string]*srcCount{} // bucket -> source -> counts
	for _, m := range all {
		g := groupKey(m)
		if counts[g] == nil {
			counts[g] = map[string]*srcCount{}
		}
		c := counts[g][m.Source]
		if c == nil {
			c = &srcCount{}
			counts[g][m.Source] = c
		}
		c.total++
		if m.HasScore {
			c.scored++
		}
	}
	chosen := map[string]string{}
	for g, bySource := range counts {
		best := ""
		var bestC srcCount
		for src, c := range bySource {
			if best == "" || betterSource(*c, src, bestC, best) {
				best, bestC = src, *c
			}
		}
		chosen[g] = best
	}
	return chosen
}

// betterSource reports whether source (c, src) should be preferred over the
// current best (bestC, best): more scored matches wins, then more total, then
// lower sourcePriority.
func betterSource(c srcCount, src string, bestC srcCount, best string) bool {
	if c.scored != bestC.scored {
		return c.scored > bestC.scored
	}
	if c.total != bestC.total {
		return c.total > bestC.total
	}
	return sourcePriority[src] < sourcePriority[best]
}

// readCSV opens a file from fsys and returns its data rows plus the header.
func readCSV(fsys fs.FS, name string) (rows [][]string, header []string, err error) {
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
		return nil, nil, fmt.Errorf("%s: empty file", name)
	}
	header = all[0]
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff") // strip UTF-8 BOM
	}
	return all[1:], header, nil
}

// indexHeader builds a case-insensitive column-name -> index map.
func indexHeader(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.ToLower(strings.TrimSpace(h))] = i
	}
	return idx
}

// get returns the trimmed value of the named column for a row, or "" when the
// column or cell is missing.
func get(idx map[string]int, row []string, name string) string {
	i, ok := idx[strings.ToLower(name)]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// parseMatchRow converts a single CSV row into a *Match, or nil when the row is
// unusable. It dispatches on the dataset because column names differ.
func parseMatchRow(mf matchFile, idx map[string]int, row []string) *Match {
	switch mf.name {
	case "novo_campeonato_brasileiro.csv":
		return parseNovoRow(idx, row)
	case "BR-Football-Dataset.csv":
		return parseBRFootballRow(idx, row)
	default:
		return parseStandardRow(mf, idx, row)
	}
}

// parseStandardRow handles the three ricardomattos05 files which share the
// home_team/away_team/home_goal/away_goal/season schema.
func parseStandardRow(mf matchFile, idx map[string]int, row []string) *Match {
	homeRaw := get(idx, row, "home_team")
	awayRaw := get(idx, row, "away_team")
	if homeRaw == "" || awayRaw == "" {
		return nil
	}
	m := &Match{
		Competition: mf.competition,
		Source:      mf.name,
		HomeRaw:     homeRaw,
		AwayRaw:     awayRaw,
		HomeTeam:    CanonicalName(homeRaw),
		AwayTeam:    CanonicalName(awayRaw),
		Round:       get(idx, row, "round"),
		Stage:       get(idx, row, "stage"),
	}
	m.HomeGoals, m.AwayGoals, m.HasScore = parseScore(
		get(idx, row, "home_goal"), get(idx, row, "away_goal"))
	m.Season = parseInt(get(idx, row, "season"))
	m.Date, m.HasTime, m.HasDate = parseDate(get(idx, row, "datetime"))
	if m.Season == 0 && m.HasDate {
		m.Season = m.Date.Year()
	}
	return m
}

// parseNovoRow handles the historical 2003-2019 Brasileirão file (Portuguese
// column names, DD/MM/YYYY dates, stadium info).
func parseNovoRow(idx map[string]int, row []string) *Match {
	homeRaw := get(idx, row, "equipe_mandante")
	awayRaw := get(idx, row, "equipe_visitante")
	if homeRaw == "" || awayRaw == "" {
		return nil
	}
	m := &Match{
		Competition: CompBrasileirao,
		Source:      "novo_campeonato_brasileiro.csv",
		HomeRaw:     homeRaw,
		AwayRaw:     awayRaw,
		HomeTeam:    CanonicalName(homeRaw),
		AwayTeam:    CanonicalName(awayRaw),
		Round:       get(idx, row, "rodada"),
		Arena:       get(idx, row, "arena"),
	}
	m.HomeGoals, m.AwayGoals, m.HasScore = parseScore(
		get(idx, row, "gols_mandante"), get(idx, row, "gols_visitante"))
	m.Season = parseInt(get(idx, row, "ano"))
	m.Date, m.HasTime, m.HasDate = parseDate(get(idx, row, "data"))
	if m.Season == 0 && m.HasDate {
		m.Season = m.Date.Year()
	}
	return m
}

// parseBRFootballRow handles the extended-statistics dataset. Its tournament
// column names the competition and its numeric fields are floats ("1.0").
func parseBRFootballRow(idx map[string]int, row []string) *Match {
	homeRaw := get(idx, row, "home")
	awayRaw := get(idx, row, "away")
	if homeRaw == "" || awayRaw == "" {
		return nil
	}
	m := &Match{
		Competition: canonCompetition(get(idx, row, "tournament")),
		Source:      "BR-Football-Dataset.csv",
		HomeRaw:     homeRaw,
		AwayRaw:     awayRaw,
		HomeTeam:    CanonicalName(homeRaw),
		AwayTeam:    CanonicalName(awayRaw),
	}
	m.HomeGoals, m.AwayGoals, m.HasScore = parseScore(
		get(idx, row, "home_goal"), get(idx, row, "away_goal"))
	m.Date, m.HasTime, m.HasDate = parseDate(get(idx, row, "date"))
	if m.HasDate {
		m.Season = m.Date.Year()
	}
	// Extended statistics.
	m.HomeCorners = parseInt(get(idx, row, "home_corner"))
	m.AwayCorners = parseInt(get(idx, row, "away_corner"))
	m.HomeShots = parseInt(get(idx, row, "home_shots"))
	m.AwayShots = parseInt(get(idx, row, "away_shots"))
	m.HomeAttacks = parseInt(get(idx, row, "home_attack"))
	m.AwayAttacks = parseInt(get(idx, row, "away_attack"))
	m.HasExtended = true
	return m
}

// canonCompetition maps a free-form tournament label to a canonical key.
func canonCompetition(tournament string) string {
	t := strings.ToLower(strings.TrimSpace(tournament))
	switch {
	case strings.Contains(t, "copa do brasil"):
		return CompCopaDoBrasil
	case strings.Contains(t, "libertadores"):
		return CompLibertadores
	case strings.Contains(t, "serie b") || strings.Contains(t, "série b"):
		return CompSerieB
	case strings.Contains(t, "serie c") || strings.Contains(t, "série c"):
		return CompSerieC
	case strings.Contains(t, "serie a") || strings.Contains(t, "série a") ||
		strings.Contains(t, "brasileir"):
		return CompBrasileirao
	default:
		return CompOther
	}
}

// dedupKey identifies a logical fixture across datasets.
func dedupKey(m *Match) string {
	day := ""
	if m.HasDate {
		day = m.Date.Format("2006-01-02")
	}
	return strings.Join([]string{
		m.Competition,
		strconv.Itoa(m.Season),
		day,
		MatchKey(m.HomeTeam),
		MatchKey(m.AwayTeam),
	}, "|")
}

// dateLayouts are tried in order by parseDate.
var dateLayouts = []struct {
	layout  string
	hasTime bool
}{
	{"2006-01-02 15:04:05", true},
	{"2006-01-02T15:04:05", true},
	{"2006-01-02 15:04", true},
	{"2006-01-02", false},
	{"02/01/2006", false}, // DD/MM/YYYY (historical Brasileirão)
	{"2/1/2006", false},
}

// parseDate attempts the supported layouts. It returns the parsed time, whether
// a wall-clock time was present, and whether parsing succeeded at all.
func parseDate(s string) (t time.Time, hasTime bool, ok bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false, false
	}
	for _, l := range dateLayouts {
		if parsed, err := time.Parse(l.layout, s); err == nil {
			return parsed, l.hasTime, true
		}
	}
	return time.Time{}, false, false
}

// parseScore parses two goal cells. It tolerates float formatting ("1.0") and
// reports HasScore=false when either side is missing/unparseable.
func parseScore(home, away string) (h, a int, ok bool) {
	hv, hok := parseGoal(home)
	av, aok := parseGoal(away)
	if !hok || !aok {
		return 0, 0, false
	}
	return hv, av, true
}

// parseGoal parses a single goal cell that may be an int or a float string.
func parseGoal(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if v, err := strconv.Atoi(s); err == nil {
		return v, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

// parseInt parses an integer that may be formatted as a float, returning 0 when
// the value is empty or unparseable.
func parseInt(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if v, err := strconv.Atoi(s); err == nil {
		return v
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

// loadPlayers parses the FIFA player dataset.
func loadPlayers(fsys fs.FS, name string) ([]*Player, error) {
	f, err := fsys.Open(name)
	if err != nil {
		return nil, fmt.Errorf("loading %s: %w", name, err)
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true

	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("reading %s header: %w", name, err)
	}
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}
	idx := indexHeader(header)

	var players []*Player
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("reading %s: %w", name, err)
		}
		name := get(idx, row, "name")
		if name == "" {
			continue
		}
		p := &Player{
			ID:             parseInt(get(idx, row, "id")),
			Name:           name,
			Age:            parseInt(get(idx, row, "age")),
			Nationality:    get(idx, row, "nationality"),
			Overall:        parseInt(get(idx, row, "overall")),
			Potential:      parseInt(get(idx, row, "potential")),
			Club:           get(idx, row, "club"),
			Position:       get(idx, row, "position"),
			JerseyNumber:   get(idx, row, "jersey number"),
			Height:         get(idx, row, "height"),
			Weight:         get(idx, row, "weight"),
			PreferredFoot:  get(idx, row, "preferred foot"),
			Finishing:      parseInt(get(idx, row, "finishing")),
			ShortPassing:   parseInt(get(idx, row, "shortpassing")),
			Dribbling:      parseInt(get(idx, row, "dribbling")),
			BallControl:    parseInt(get(idx, row, "ballcontrol")),
			SprintSpeed:    parseInt(get(idx, row, "sprintspeed")),
			StandingTackle: parseInt(get(idx, row, "standingtackle")),
		}
		players = append(players, p)
	}
	return players, nil
}
