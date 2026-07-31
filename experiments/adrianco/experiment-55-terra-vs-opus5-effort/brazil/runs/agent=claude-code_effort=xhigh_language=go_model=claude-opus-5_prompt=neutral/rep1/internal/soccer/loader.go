// loader.go reads the six Kaggle CSV files in data/kaggle into raw records.
//
// Each file has its own column layout, date format and naming convention, so a
// dedicated reader per file normalises them onto a common rawMatch / Player
// shape. Nothing here decides team identity: readers only record the raw
// spelling plus its parsed parts, and graph.go resolves those into Team entities
// once every file has been seen.
//
// Rows that cannot be used (missing score, unparseable date, placeholder rows
// such as the Libertadores fixture with season "NA" and "-" goals) are counted
// and reported through SourceInfo rather than silently dropped.
package soccer

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Dataset describes one CSV shipped with the project.
type Dataset struct {
	Key         string
	File        string
	Kind        string // "matches" or "players"
	Description string
	URL         string
	License     string
}

// Datasets is the manifest of provided data, in load order. The keys double as
// the Match.Source values and as the priority order for de-duplication.
var Datasets = []Dataset{
	{
		Key:         "brasileirao",
		File:        "Brasileirao_Matches.csv",
		Kind:        "matches",
		Description: "Brasileirão Série A matches 2012-2022 with round numbers and team states",
		URL:         "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
		License:     "CC BY 4.0",
	},
	{
		Key:         "copa_do_brasil",
		File:        "Brazilian_Cup_Matches.csv",
		Kind:        "matches",
		Description: "Copa do Brasil matches 2012-2021 with knockout round numbers",
		URL:         "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
		License:     "CC BY 4.0",
	},
	{
		Key:         "libertadores",
		File:        "Libertadores_Matches.csv",
		Kind:        "matches",
		Description: "Copa Libertadores matches 2013-2022 with tournament stages",
		URL:         "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
		License:     "CC BY 4.0",
	},
	{
		Key:         "historic_brasileirao",
		File:        "novo_campeonato_brasileiro.csv",
		Kind:        "matches",
		Description: "Historical Brasileirão Série A 2003-2019 including stadium names",
		URL:         "https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019",
		License:     "CC BY 4.0",
	},
	{
		Key:         "br_football",
		File:        "BR-Football-Dataset.csv",
		Kind:        "matches",
		Description: "Série A/B/C and Copa do Brasil 2014-2023 with shots, attacks and corners",
		URL:         "https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches",
		License:     "CC0 Public Domain",
	},
	{
		Key:         "fifa_players",
		File:        "fifa_data.csv",
		Kind:        "players",
		Description: "FIFA player database: 18,207 players with ratings and attributes",
		URL:         "https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data",
		License:     "Apache 2.0",
	},
}

// rawMatch is a match as read from a file, before team identity is resolved.
type rawMatch struct {
	source      string
	competition Competition
	season      int
	round       int
	stage       string
	date        time.Time
	hasDate     bool
	homeRaw     string
	awayRaw     string
	homeParts   nameParts
	awayParts   nameParts
	homeGoals   int
	awayGoals   int
	venue       string
	stats       *MatchStats
}

// loadResult carries everything a single file contributed.
type loadResult struct {
	info    SourceInfo
	matches []*rawMatch
	players []*Player
}

// FindDataDir locates the data/kaggle directory by walking up from start (or the
// working directory when start is empty). It lets both the server and the tests
// run from any directory inside the repository.
func FindDataDir(start string) (string, error) {
	if start == "" {
		wd, err := os.Getwd()
		if err != nil {
			return "", err
		}
		start = wd
	}
	dir, err := filepath.Abs(start)
	if err != nil {
		return "", err
	}
	for {
		candidate := filepath.Join(dir, "data", "kaggle")
		if st, err := os.Stat(candidate); err == nil && st.IsDir() {
			return candidate, nil
		}
		// Also accept being handed the kaggle directory itself.
		if st, err := os.Stat(filepath.Join(dir, Datasets[0].File)); err == nil && !st.IsDir() {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("could not find a data/kaggle directory at or above %s", start)
		}
		dir = parent
	}
}

// csvTable is a CSV file with its header indexed by name.
type csvTable struct {
	reader *csv.Reader
	index  map[string]int
	file   *os.File
	name   string
	row    []string
}

func openCSV(path string) (*csvTable, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	r.ReuseRecord = true
	header, err := r.Read()
	if err != nil {
		f.Close()
		return nil, fmt.Errorf("%s: reading header: %w", filepath.Base(path), err)
	}
	index := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff") // UTF-8 BOM on fifa_data.csv
		index[strings.TrimSpace(h)] = i
	}
	return &csvTable{reader: r, index: index, file: f, name: filepath.Base(path)}, nil
}

func (t *csvTable) Close() error { return t.file.Close() }

// Next advances to the next row, returning false at EOF.
func (t *csvTable) Next() (bool, error) {
	rec, err := t.reader.Read()
	if errors.Is(err, io.EOF) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("%s: %w", t.name, err)
	}
	t.row = rec
	return true, nil
}

// col returns the trimmed value of a column, or "" when the column is absent.
func (t *csvTable) col(name string) string {
	i, ok := t.index[name]
	if !ok || i >= len(t.row) {
		return ""
	}
	return strings.TrimSpace(t.row[i])
}

// intCol parses a column that may be written as "3", "3.0" or "".
func (t *csvTable) intCol(name string) (int, bool) {
	return parseInt(t.col(name))
}

func parseInt(s string) (int, bool) {
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

// dateLayouts covers every format used across the six files.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006 15:04",
	"2006/01/02",
}

// parseDate accepts ISO timestamps, ISO dates and Brazilian DD/MM/YYYY dates.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "na") || s == "-" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// loadFile dispatches to the reader for a dataset.
func loadFile(dir string, ds Dataset) (*loadResult, error) {
	path := filepath.Join(dir, ds.File)
	table, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer table.Close()

	res := &loadResult{info: SourceInfo{
		Key: ds.Key, File: ds.File, Description: ds.Description,
		URL: ds.URL, License: ds.License, Kind: ds.Kind,
	}}

	var readRow func(t *csvTable, res *loadResult) error
	switch ds.Key {
	case "brasileirao":
		readRow = readBrasileirao
	case "copa_do_brasil":
		readRow = readCopaDoBrasil
	case "libertadores":
		readRow = readLibertadores
	case "historic_brasileirao":
		readRow = readHistoricBrasileirao
	case "br_football":
		readRow = readBRFootball
	case "fifa_players":
		readRow = readPlayer
	default:
		return nil, fmt.Errorf("no reader for dataset %q", ds.Key)
	}

	for {
		ok, err := table.Next()
		if err != nil {
			return nil, err
		}
		if !ok {
			break
		}
		if err := readRow(table, res); err != nil {
			res.info.Skipped++
			addSkipReason(&res.info, err.Error())
		}
	}
	summarise(res)
	return res, nil
}

// addSkipReason keeps a bounded, de-duplicated list of why rows were dropped.
func addSkipReason(info *SourceInfo, reason string) {
	for _, r := range info.SkipReasons {
		if r == reason {
			return
		}
	}
	if len(info.SkipReasons) < 8 {
		info.SkipReasons = append(info.SkipReasons, reason)
	}
}

// summarise fills in the row counts and season/competition coverage of a source.
func summarise(res *loadResult) {
	res.info.Rows = len(res.matches) + len(res.players)
	seen := map[Competition]bool{}
	for _, m := range res.matches {
		if !seen[m.competition] {
			seen[m.competition] = true
			res.info.Competition = append(res.info.Competition, string(m.competition))
		}
		if res.info.SeasonMin == 0 || m.season < res.info.SeasonMin {
			res.info.SeasonMin = m.season
		}
		if m.season > res.info.SeasonMax {
			res.info.SeasonMax = m.season
		}
	}
}

// errSkip formats a skip reason.
func errSkip(format string, args ...any) error { return fmt.Errorf(format, args...) }

// buildMatch performs the checks shared by every match reader.
func buildMatch(source string, comp Competition, homeRaw, awayRaw string, homeGoals, awayGoals int, season int) (*rawMatch, error) {
	hp := parseTeamName(homeRaw)
	ap := parseTeamName(awayRaw)
	if hp.empty() || ap.empty() {
		return nil, errSkip("row has an empty team name")
	}
	if season <= 0 {
		return nil, errSkip("row has no usable season")
	}
	return &rawMatch{
		source: source, competition: comp, season: season,
		homeRaw: homeRaw, awayRaw: awayRaw, homeParts: hp, awayParts: ap,
		homeGoals: homeGoals, awayGoals: awayGoals,
	}, nil
}

// readBrasileirao reads Brasileirao_Matches.csv (Série A, explicit season/round).
func readBrasileirao(t *csvTable, res *loadResult) error {
	hg, okH := t.intCol("home_goal")
	ag, okA := t.intCol("away_goal")
	if !okH || !okA {
		return errSkip("missing goals")
	}
	season, _ := t.intCol("season")
	m, err := buildMatch("brasileirao", SerieA, t.col("home_team"), t.col("away_team"), hg, ag, season)
	if err != nil {
		return err
	}
	if r, ok := t.intCol("round"); ok {
		m.round = r
	}
	if d, ok := parseDate(t.col("datetime")); ok {
		m.date, m.hasDate = d, true
	}
	// The state columns are authoritative when the name itself lacks a suffix.
	if st := strings.ToUpper(t.col("home_team_state")); brazilianStates[st] && m.homeParts.State == "" {
		m.homeParts.State = st
	}
	if st := strings.ToUpper(t.col("away_team_state")); brazilianStates[st] && m.awayParts.State == "" {
		m.awayParts.State = st
	}
	res.matches = append(res.matches, m)
	return nil
}

// readCopaDoBrasil reads Brazilian_Cup_Matches.csv. The file numbers knockout
// rounds 1..8; the stage label is derived later, once the final round of each
// season is known.
func readCopaDoBrasil(t *csvTable, res *loadResult) error {
	hg, okH := t.intCol("home_goal")
	ag, okA := t.intCol("away_goal")
	if !okH || !okA {
		return errSkip("missing goals")
	}
	season, _ := t.intCol("season")
	m, err := buildMatch("copa_do_brasil", CopaDoBrasil, t.col("home_team"), t.col("away_team"), hg, ag, season)
	if err != nil {
		return err
	}
	if r, ok := t.intCol("round"); ok {
		m.round = r
	}
	if d, ok := parseDate(t.col("datetime")); ok {
		m.date, m.hasDate = d, true
	}
	res.matches = append(res.matches, m)
	return nil
}

// readLibertadores reads Libertadores_Matches.csv, which carries an explicit
// stage and includes one placeholder row (season "NA", goals "-").
func readLibertadores(t *csvTable, res *loadResult) error {
	hg, okH := t.intCol("home_goal")
	ag, okA := t.intCol("away_goal")
	if !okH || !okA {
		return errSkip("missing goals (placeholder fixture)")
	}
	season, ok := t.intCol("season")
	if !ok {
		return errSkip("missing season")
	}
	m, err := buildMatch("libertadores", Libertadores, t.col("home_team"), t.col("away_team"), hg, ag, season)
	if err != nil {
		return err
	}
	m.stage = strings.ToLower(strings.TrimSpace(t.col("stage")))
	if d, ok := parseDate(t.col("datetime")); ok {
		m.date, m.hasDate = d, true
	}
	res.matches = append(res.matches, m)
	return nil
}

// readHistoricBrasileirao reads novo_campeonato_brasileiro.csv (2003-2019),
// which uses Portuguese column names, DD/MM/YYYY dates and records the stadium.
func readHistoricBrasileirao(t *csvTable, res *loadResult) error {
	hg, okH := t.intCol("Gols_mandante")
	ag, okA := t.intCol("Gols_visitante")
	if !okH || !okA {
		return errSkip("missing goals")
	}
	season, _ := t.intCol("Ano")
	m, err := buildMatch("historic_brasileirao", SerieA, t.col("Equipe_mandante"), t.col("Equipe_visitante"), hg, ag, season)
	if err != nil {
		return err
	}
	if r, ok := t.intCol("Rodada"); ok {
		m.round = r
	}
	if d, ok := parseDate(t.col("Data")); ok {
		m.date, m.hasDate = d, true
	}
	m.venue = t.col("Arena")
	if st := strings.ToUpper(t.col("Mandante_UF")); brazilianStates[st] && m.homeParts.State == "" {
		m.homeParts.State = st
	}
	if st := strings.ToUpper(t.col("Visitante_UF")); brazilianStates[st] && m.awayParts.State == "" {
		m.awayParts.State = st
	}
	res.matches = append(res.matches, m)
	return nil
}

// brFootballCompetitions maps the tournament column of BR-Football-Dataset.csv.
var brFootballCompetitions = map[string]Competition{
	"serie a":        SerieA,
	"serie b":        SerieB,
	"serie c":        SerieC,
	"copa do brasil": CopaDoBrasil,
}

// readBRFootball reads BR-Football-Dataset.csv. The file has no season column,
// only a calendar date; seasonForDate reconstructs the season.
func readBRFootball(t *csvTable, res *loadResult) error {
	comp, ok := brFootballCompetitions[foldKey(t.col("tournament"))]
	if !ok {
		return errSkip("unknown tournament %q", t.col("tournament"))
	}
	hg, okH := t.intCol("home_goal")
	ag, okA := t.intCol("away_goal")
	if !okH || !okA {
		return errSkip("missing goals")
	}
	date, hasDate := parseDate(t.col("date"))
	if !hasDate {
		return errSkip("missing date")
	}
	m, err := buildMatch("br_football", comp, t.col("home"), t.col("away"), hg, ag, seasonForDate(comp, date))
	if err != nil {
		return err
	}
	m.date, m.hasDate = date, true
	stats := &MatchStats{KickOff: t.col("time")}
	stats.HomeCorners, _ = t.intCol("home_corner")
	stats.AwayCorners, _ = t.intCol("away_corner")
	stats.TotalCorners, _ = t.intCol("total_corners")
	stats.HomeAttacks, _ = t.intCol("home_attack")
	stats.AwayAttacks, _ = t.intCol("away_attack")
	stats.HomeShots, _ = t.intCol("home_shots")
	stats.AwayShots, _ = t.intCol("away_shots")
	m.stats = stats
	res.matches = append(res.matches, m)
	return nil
}

// seasonForDate maps a kick-off date to a season. Brazilian league seasons run
// from April/May to December, except for the pandemic-shifted 2020 season which
// finished in February 2021, so January and February belong to the previous
// season. Cups are played inside a single calendar year.
func seasonForDate(comp Competition, d time.Time) int {
	if comp.IsLeague() && d.Month() <= time.February {
		return d.Year() - 1
	}
	return d.Year()
}

// playerSkillColumns are the FIFA attribute columns kept for each player.
var playerSkillColumns = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
	"Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
	"Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
	"ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
	"Interceptions", "Positioning", "Vision", "Penalties", "Composure",
	"Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
	"GKKicking", "GKPositioning", "GKReflexes",
}

// readPlayer reads one row of fifa_data.csv.
func readPlayer(t *csvTable, res *loadResult) error {
	name := t.col("Name")
	if name == "" {
		return errSkip("player row without a name")
	}
	id, _ := t.intCol("ID")
	overall, ok := t.intCol("Overall")
	if !ok {
		return errSkip("player row without an overall rating")
	}
	p := &Player{
		ID:          id,
		Name:        name,
		Nationality: t.col("Nationality"),
		Overall:     overall,
		Club:        t.col("Club"),
		Position:    strings.ToUpper(t.col("Position")),
		Height:      t.col("Height"),
		Weight:      t.col("Weight"),
		Foot:        t.col("Preferred Foot"),
		WorkRate:    t.col("Work Rate"),
		Value:       t.col("Value"),
		Wage:        t.col("Wage"),
		Joined:      t.col("Joined"),
		ContractTo:  t.col("Contract Valid Until"),
		nameKey:     foldKey(name),
	}
	p.Age, _ = t.intCol("Age")
	p.Potential, _ = t.intCol("Potential")
	p.Jersey, _ = t.intCol("Jersey Number")
	p.ValueEUR = parseMoney(p.Value)
	p.WageEUR = parseMoney(p.Wage)
	skills := make(map[string]int, len(playerSkillColumns))
	for _, col := range playerSkillColumns {
		if v, ok := t.intCol(col); ok {
			skills[col] = v
		}
	}
	if len(skills) > 0 {
		p.Skills = skills
	}
	res.players = append(res.players, p)
	return nil
}

// parseMoney converts the FIFA money notation ("€110.5M", "€565K") to euros.
func parseMoney(s string) int64 {
	s = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(s), "€"))
	if s == "" || s == "0" {
		return 0
	}
	mult := int64(1)
	switch {
	case strings.HasSuffix(s, "M"), strings.HasSuffix(s, "m"):
		mult, s = 1_000_000, s[:len(s)-1]
	case strings.HasSuffix(s, "K"), strings.HasSuffix(s, "k"):
		mult, s = 1_000, s[:len(s)-1]
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	return int64(f * float64(mult))
}
