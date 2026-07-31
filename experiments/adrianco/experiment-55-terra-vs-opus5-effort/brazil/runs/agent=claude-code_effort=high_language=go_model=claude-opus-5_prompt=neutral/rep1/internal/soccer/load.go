// load.go reads the six Kaggle CSV files into raw records and then assembles
// them into the knowledge graph.
//
// Loading is deliberately two-pass. The first pass only parses team names so
// that the loader can learn which club bases are ambiguous across states; the
// second pass resolves every name to a canonical team ID using that knowledge,
// builds Match nodes and merges duplicate fixtures that appear in more than one
// dataset (Série A 2014-2019, for instance, is present in three files).
package soccer

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"math"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Dataset file names, in load-priority order. Earlier files win when two
// datasets disagree about the same fixture.
const (
	FileBrasileirao  = "Brasileirao_Matches.csv"
	FileNovoBR       = "novo_campeonato_brasileiro.csv"
	FileCup          = "Brazilian_Cup_Matches.csv"
	FileLibertadores = "Libertadores_Matches.csv"
	FileBRFootball   = "BR-Football-Dataset.csv"
	FileFIFA         = "fifa_data.csv"
)

// SourceFiles lists every dataset the loader consumes.
var SourceFiles = []string{
	FileBrasileirao, FileNovoBR, FileCup, FileLibertadores, FileBRFootball, FileFIFA,
}

// DatasetInfo describes one loaded CSV file.
type DatasetInfo struct {
	File        string `json:"file"`
	Description string `json:"description"`
	License     string `json:"license"`
	RowsRead    int    `json:"rows_read"`
	RowsUsed    int    `json:"rows_used"`
	RowsSkipped int    `json:"rows_skipped"`
}

// LoadStats summarises a load for the dataset_info tool.
type LoadStats struct {
	Datasets         []DatasetInfo `json:"datasets"`
	Teams            int           `json:"teams"`
	Matches          int           `json:"matches"`
	Players          int           `json:"players"`
	MergedDuplicates int           `json:"merged_duplicate_matches"`
	ScoreConflicts   int           `json:"score_conflicts"`
	LoadMillis       int64         `json:"load_ms"`
}

var datasetDescriptions = map[string][2]string{
	FileBrasileirao:  {"Brasileirão Série A matches 2012-2022 (with round and state)", "CC BY 4.0"},
	FileNovoBR:       {"Historical Brasileirão 2003-2019 (with stadium and winner)", "CC BY 4.0"},
	FileCup:          {"Copa do Brasil matches 2012-2021", "CC BY 4.0"},
	FileLibertadores: {"Copa Libertadores matches 2013-2022 (with tournament stage)", "CC BY 4.0"},
	FileBRFootball:   {"Série A/B/C and Copa do Brasil 2014-2023 with extended match statistics", "CC0 Public Domain"},
	FileFIFA:         {"FIFA 19 player database (18,207 players)", "Apache 2.0"},
}

// rawMatch is an un-resolved match row, before team names become team IDs.
type rawMatch struct {
	source      string
	priority    int
	competition string
	season      int
	round       int
	stage       string
	date        time.Time
	hasTime     bool
	kickOff     string
	homeRaw     string
	awayRaw     string
	homeHint    string
	awayHint    string
	homeGoals   int
	awayGoals   int
	venue       string
	stats       *MatchStats
}

// ---------------------------------------------------------------------------
// CSV plumbing
// ---------------------------------------------------------------------------

type table struct {
	name   string
	reader *csv.Reader
	idx    map[string]int
	closer io.Closer
}

func openTable(fsys fs.FS, name string) (*table, error) {
	f, err := fsys.Open(name)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", name, err)
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	r.ReuseRecord = true
	head, err := r.Read()
	if err != nil {
		f.Close()
		return nil, fmt.Errorf("read header of %s: %w", name, err)
	}
	idx := make(map[string]int, len(head))
	for i, h := range head {
		h = strings.TrimPrefix(h, "\ufeff")
		idx[strings.TrimSpace(h)] = i
	}
	return &table{name: name, reader: r, idx: idx, closer: f}, nil
}

func (t *table) next() ([]string, error) { return t.reader.Read() }

func (t *table) get(rec []string, col string) string {
	i, ok := t.idx[col]
	if !ok || i >= len(rec) {
		return ""
	}
	return strings.TrimSpace(rec[i])
}

// atoi parses an integer that may be written as a float ("2.0") or be empty.
func atoi(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if v, err := strconv.Atoi(s); err == nil {
		return v, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil && !math.IsNaN(f) {
		return int(math.Round(f)), true
	}
	return 0, false
}

// ---------------------------------------------------------------------------
// Per-file readers
// ---------------------------------------------------------------------------

func readBrasileirao(fsys fs.FS) ([]rawMatch, DatasetInfo, error) {
	return readMatchFile(fsys, FileBrasileirao, 1, func(t *table, rec []string) (rawMatch, bool) {
		date, hasTime, err := ParseDate(t.get(rec, "datetime"))
		hg, ok1 := atoi(t.get(rec, "home_goal"))
		ag, ok2 := atoi(t.get(rec, "away_goal"))
		season, _ := atoi(t.get(rec, "season"))
		round, _ := atoi(t.get(rec, "round"))
		if err != nil || !ok1 || !ok2 {
			return rawMatch{}, false
		}
		if season == 0 {
			season = date.Year()
		}
		return rawMatch{
			competition: CompSerieA, season: season, round: round,
			date: date, hasTime: hasTime, kickOff: kickOffOf(date, hasTime),
			homeRaw: t.get(rec, "home_team"), awayRaw: t.get(rec, "away_team"),
			homeHint: t.get(rec, "home_team_state"), awayHint: t.get(rec, "away_team_state"),
			homeGoals: hg, awayGoals: ag,
		}, true
	})
}

func readNovoBR(fsys fs.FS) ([]rawMatch, DatasetInfo, error) {
	return readMatchFile(fsys, FileNovoBR, 2, func(t *table, rec []string) (rawMatch, bool) {
		date, hasTime, err := ParseDate(t.get(rec, "Data"))
		hg, ok1 := atoi(t.get(rec, "Gols_mandante"))
		ag, ok2 := atoi(t.get(rec, "Gols_visitante"))
		season, _ := atoi(t.get(rec, "Ano"))
		round, _ := atoi(t.get(rec, "Rodada"))
		if err != nil || !ok1 || !ok2 {
			return rawMatch{}, false
		}
		if season == 0 {
			season = date.Year()
		}
		return rawMatch{
			competition: CompSerieA, season: season, round: round,
			date: date, hasTime: hasTime, kickOff: kickOffOf(date, hasTime),
			homeRaw: t.get(rec, "Equipe_mandante"), awayRaw: t.get(rec, "Equipe_visitante"),
			homeHint: t.get(rec, "Mandante_UF"), awayHint: t.get(rec, "Visitante_UF"),
			homeGoals: hg, awayGoals: ag,
			venue: t.get(rec, "Arena"),
		}, true
	})
}

func readCup(fsys fs.FS) ([]rawMatch, DatasetInfo, error) {
	rows, info, err := readMatchFile(fsys, FileCup, 3, func(t *table, rec []string) (rawMatch, bool) {
		date, hasTime, err := ParseDate(t.get(rec, "datetime"))
		hg, ok1 := atoi(t.get(rec, "home_goal"))
		ag, ok2 := atoi(t.get(rec, "away_goal"))
		season, _ := atoi(t.get(rec, "season"))
		round, _ := atoi(t.get(rec, "round"))
		if err != nil || !ok1 || !ok2 {
			return rawMatch{}, false
		}
		if season == 0 {
			season = date.Year()
		}
		return rawMatch{
			competition: CompCopaDoBrasil, season: season, round: round,
			date: date, hasTime: hasTime, kickOff: kickOffOf(date, hasTime),
			homeRaw: t.get(rec, "home_team"), awayRaw: t.get(rec, "away_team"),
			homeGoals: hg, awayGoals: ag,
		}, true
	})
	if err != nil {
		return nil, info, err
	}
	labelCupStages(rows)
	return rows, info, nil
}

// labelCupStages turns the Copa do Brasil's bare round numbers into stage
// names. The stage is inferred from how many matches the round contains rather
// than from its position, because the dataset's 2021 season stops after the
// round of 16 — counting back from the last round present would then label a
// round of 16 tie as the final.
func labelCupStages(rows []rawMatch) {
	counts := map[[2]int]int{}
	for _, r := range rows {
		if r.round > 0 {
			counts[[2]int{r.season, r.round}]++
		}
	}
	// The knockout phase proper starts after the largest round; earlier rounds
	// can also be small (2013-2015 open with a single two-legged preliminary
	// tie) and must not be mistaken for a final.
	knockoutFrom := map[int]int{}
	biggest := map[int]int{}
	for k, n := range counts {
		season, round := k[0], k[1]
		if n > biggest[season] || (n == biggest[season] && round < knockoutFrom[season]) {
			biggest[season] = n
			knockoutFrom[season] = round
		}
	}

	for i := range rows {
		if rows[i].round == 0 || rows[i].round < knockoutFrom[rows[i].season] {
			if rows[i].round > 0 {
				rows[i].stage = fmt.Sprintf("Round %d", rows[i].round)
			}
			continue
		}
		n := counts[[2]int{rows[i].season, rows[i].round}]
		switch {
		case n >= 1 && n <= 2:
			rows[i].stage = "Final"
		case n >= 3 && n <= 4:
			rows[i].stage = "Semifinals"
		case n >= 7 && n <= 8:
			rows[i].stage = "Quarterfinals"
		case n >= 13 && n <= 16:
			rows[i].stage = "Round of 16"
		default:
			rows[i].stage = fmt.Sprintf("Round %d", rows[i].round)
		}
	}
}

func readLibertadores(fsys fs.FS) ([]rawMatch, DatasetInfo, error) {
	return readMatchFile(fsys, FileLibertadores, 4, func(t *table, rec []string) (rawMatch, bool) {
		date, hasTime, err := ParseDate(t.get(rec, "datetime"))
		hg, ok1 := atoi(t.get(rec, "home_goal"))
		ag, ok2 := atoi(t.get(rec, "away_goal"))
		season, _ := atoi(t.get(rec, "season"))
		if err != nil || !ok1 || !ok2 {
			return rawMatch{}, false
		}
		if season == 0 {
			season = date.Year()
		}
		return rawMatch{
			competition: CompLibertadores, season: season,
			stage: titleStage(t.get(rec, "stage")),
			date:  date, hasTime: hasTime, kickOff: kickOffOf(date, hasTime),
			homeRaw: t.get(rec, "home_team"), awayRaw: t.get(rec, "away_team"),
			homeGoals: hg, awayGoals: ag,
		}, true
	})
}

func readBRFootball(fsys fs.FS) ([]rawMatch, DatasetInfo, error) {
	return readMatchFile(fsys, FileBRFootball, 5, func(t *table, rec []string) (rawMatch, bool) {
		date, _, err := ParseDate(t.get(rec, "date"))
		hg, ok1 := atoi(t.get(rec, "home_goal"))
		ag, ok2 := atoi(t.get(rec, "away_goal"))
		comp, ok3 := brFootballCompetition(t.get(rec, "tournament"))
		if err != nil || !ok1 || !ok2 || !ok3 {
			return rawMatch{}, false
		}
		stats := &MatchStats{HomeHTResult: t.get(rec, "ht_result"), AwayHTResult: t.get(rec, "at_result")}
		stats.HomeCorners, _ = atoi(t.get(rec, "home_corner"))
		stats.AwayCorners, _ = atoi(t.get(rec, "away_corner"))
		stats.TotalCorners, _ = atoi(t.get(rec, "total_corners"))
		stats.HomeAttacks, _ = atoi(t.get(rec, "home_attack"))
		stats.AwayAttacks, _ = atoi(t.get(rec, "away_attack"))
		stats.HomeShots, _ = atoi(t.get(rec, "home_shots"))
		stats.AwayShots, _ = atoi(t.get(rec, "away_shots"))
		return rawMatch{
			competition: comp, season: seasonOfDate(date, comp),
			date: date, kickOff: t.get(rec, "time"),
			homeRaw: t.get(rec, "home"), awayRaw: t.get(rec, "away"),
			homeGoals: hg, awayGoals: ag, stats: stats,
		}, true
	})
}

func brFootballCompetition(tournament string) (string, bool) {
	switch strings.ToLower(strings.TrimSpace(tournament)) {
	case "serie a":
		return CompSerieA, true
	case "serie b":
		return CompSerieB, true
	case "serie c":
		return CompSerieC, true
	case "copa do brasil":
		return CompCopaDoBrasil, true
	}
	return "", false
}

// seasonOfDate maps a calendar date onto a season for datasets that carry no
// season column. Brazilian league seasons are calendar-year affairs that never
// normally play in January or February, so a league match in those months is a
// spill-over from the previous season — which is exactly what happened when
// COVID pushed the 2020 Série A into February 2021. Without this correction the
// 2020 season loses 111 matches and 2021 gains them, corrupting both tables.
// The Copa do Brasil genuinely starts in February, so it is left alone.
func seasonOfDate(t time.Time, comp string) int {
	if competitionCatalog[comp].Kind == "league" && t.Month() <= time.February {
		return t.Year() - 1
	}
	return t.Year()
}

func kickOffOf(t time.Time, hasTime bool) string {
	if !hasTime {
		return ""
	}
	return t.Format("15:04")
}

func titleStage(s string) string {
	s = strings.TrimSpace(s)
	switch strings.ToLower(s) {
	case "group stage":
		return "Group Stage"
	case "round of 16":
		return "Round of 16"
	case "quarterfinals":
		return "Quarterfinals"
	case "semifinals":
		return "Semifinals"
	case "final":
		return "Final"
	}
	return s
}

// readMatchFile is the shared driver for the five match datasets.
func readMatchFile(fsys fs.FS, name string, priority int, parse func(*table, []string) (rawMatch, bool)) ([]rawMatch, DatasetInfo, error) {
	meta := datasetDescriptions[name]
	info := DatasetInfo{File: name, Description: meta[0], License: meta[1]}
	t, err := openTable(fsys, name)
	if err != nil {
		return nil, info, err
	}
	defer t.closer.Close()

	var out []rawMatch
	for {
		rec, err := t.next()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			// A malformed line should not abort a 10k-row dataset.
			info.RowsSkipped++
			continue
		}
		info.RowsRead++
		m, ok := parse(t, rec)
		if !ok || m.homeRaw == "" || m.awayRaw == "" {
			info.RowsSkipped++
			continue
		}
		m.source = name
		m.priority = priority
		out = append(out, m)
		info.RowsUsed++
	}
	return out, info, nil
}

// ---------------------------------------------------------------------------
// Player loading
// ---------------------------------------------------------------------------

var skillColumns = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
	"Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
	"Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
	"ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
	"Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
	"Composure", "Marking", "StandingTackle", "SlidingTackle",
	"GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
}

func readPlayers(fsys fs.FS) ([]*Player, DatasetInfo, error) {
	meta := datasetDescriptions[FileFIFA]
	info := DatasetInfo{File: FileFIFA, Description: meta[0], License: meta[1]}
	t, err := openTable(fsys, FileFIFA)
	if err != nil {
		return nil, info, err
	}
	defer t.closer.Close()

	var out []*Player
	for {
		rec, err := t.next()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			info.RowsSkipped++
			continue
		}
		info.RowsRead++
		name := t.get(rec, "Name")
		if name == "" {
			info.RowsSkipped++
			continue
		}
		id, _ := atoi(t.get(rec, "ID"))
		age, _ := atoi(t.get(rec, "Age"))
		overall, _ := atoi(t.get(rec, "Overall"))
		potential, _ := atoi(t.get(rec, "Potential"))
		jersey, _ := atoi(t.get(rec, "Jersey Number"))
		reputation, _ := atoi(t.get(rec, "International Reputation"))
		weakFoot, _ := atoi(t.get(rec, "Weak Foot"))
		skillMoves, _ := atoi(t.get(rec, "Skill Moves"))

		p := &Player{
			ID: id, Name: name, Age: age,
			Nationality: t.get(rec, "Nationality"),
			Overall:     overall, Potential: potential,
			Club:           t.get(rec, "Club"),
			Position:       t.get(rec, "Position"),
			JerseyNumber:   jersey,
			Height:         t.get(rec, "Height"),
			Weight:         t.get(rec, "Weight"),
			Value:          t.get(rec, "Value"),
			Wage:           t.get(rec, "Wage"),
			PreferredFoot:  t.get(rec, "Preferred Foot"),
			WorkRate:       t.get(rec, "Work Rate"),
			BodyType:       t.get(rec, "Body Type"),
			Joined:         t.get(rec, "Joined"),
			ContractUntil:  t.get(rec, "Contract Valid Until"),
			ReleaseClause:  t.get(rec, "Release Clause"),
			IntlReputation: reputation,
			WeakFoot:       weakFoot,
			SkillMoves:     skillMoves,
			Skills:         make(map[string]int, len(skillColumns)),
		}
		p.ValueEUR = parseMoney(p.Value)
		p.WageEUR = parseMoney(p.Wage)
		for _, c := range skillColumns {
			if v, ok := atoi(t.get(rec, c)); ok {
				p.Skills[c] = v
			}
		}
		out = append(out, p)
		info.RowsUsed++
	}
	return out, info, nil
}

// parseMoney converts FIFA money strings such as "€110.5M" or "€565K" to euros.
func parseMoney(s string) float64 {
	s = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(s), "€"))
	if s == "" {
		return 0
	}
	mult := 1.0
	switch {
	case strings.HasSuffix(s, "M"):
		mult, s = 1e6, strings.TrimSuffix(s, "M")
	case strings.HasSuffix(s, "K"):
		mult, s = 1e3, strings.TrimSuffix(s, "K")
	}
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	return v * mult
}

// ---------------------------------------------------------------------------
// Graph assembly
// ---------------------------------------------------------------------------

// Load reads all six datasets from fsys (a directory containing the CSV files)
// and returns the assembled knowledge graph.
func Load(fsys fs.FS) (*Graph, error) {
	start := time.Now()

	type reader struct {
		fn func(fs.FS) ([]rawMatch, DatasetInfo, error)
	}
	readers := []reader{
		{readBrasileirao}, {readNovoBR}, {readCup}, {readLibertadores}, {readBRFootball},
	}

	var raws []rawMatch
	var stats LoadStats
	for _, r := range readers {
		rows, info, err := r.fn(fsys)
		if err != nil {
			return nil, err
		}
		raws = append(raws, rows...)
		stats.Datasets = append(stats.Datasets, info)
	}

	players, playerInfo, err := readPlayers(fsys)
	if err != nil {
		return nil, err
	}
	stats.Datasets = append(stats.Datasets, playerInfo)

	g := newGraph()
	res := newTeamResolver()

	// Pass 1 — learn which club bases occur with which regions.
	for i := range raws {
		res.observe(raws[i].homeRaw, raws[i].homeHint)
		res.observe(raws[i].awayRaw, raws[i].awayHint)
	}

	// Pass 2 — resolve names, create teams and merge duplicate fixtures.
	byKey := make(map[string][]*Match, len(raws))
	sort.SliceStable(raws, func(i, j int) bool { return raws[i].priority < raws[j].priority })
	for i := range raws {
		r := &raws[i]
		homeID := g.ensureTeam(res, r.homeRaw, r.homeHint)
		awayID := g.ensureTeam(res, r.awayRaw, r.awayHint)
		if homeID == "" || awayID == "" || homeID == awayID {
			continue
		}
		key := fmt.Sprintf("%s|%d|%s|%s", r.competition, r.season, homeID, awayID)
		if prev := findFixture(byKey[key], r); prev != nil {
			if mergeMatch(prev, r) {
				stats.ScoreConflicts++
			}
			stats.MergedDuplicates++
			continue
		}
		m := &Match{
			ID:          fmt.Sprintf("%s|%s", key, FormatDate(r.date)),
			Competition: r.competition,
			Season:      r.season,
			Round:       r.round,
			Stage:       r.stage,
			Date:        r.date,
			HasTime:     r.hasTime,
			KickOff:     r.kickOff,
			HomeTeamID:  homeID,
			AwayTeamID:  awayID,
			HomeGoals:   r.homeGoals,
			AwayGoals:   r.awayGoals,
			Venue:       r.venue,
			Stats:       r.stats,
			Sources:     []string{r.source},
		}
		byKey[key] = append(byKey[key], m)
		g.Matches = append(g.Matches, m)
	}

	// Work out each FIFA club's share of Brazilian players before linking, so
	// linkClub can reject same-named foreign clubs.
	clubTotal, clubBrazilian := map[string]int{}, map[string]int{}
	for _, p := range players {
		if p.Club == "" {
			continue
		}
		clubTotal[p.Club]++
		if strings.EqualFold(p.Nationality, "Brazil") {
			clubBrazilian[p.Club]++
		}
	}
	linked := map[string]string{}
	for _, p := range players {
		id, ok := linked[p.Club]
		if !ok {
			share := 0.0
			if n := clubTotal[p.Club]; n > 0 {
				share = float64(clubBrazilian[p.Club]) / float64(n)
			}
			id = g.linkClub(res, p.Club, share)
			linked[p.Club] = id
		}
		p.ClubTeamID = id
	}
	g.Players = players

	g.finalize()
	stats.Teams = len(g.Teams)
	stats.Matches = len(g.Matches)
	stats.Players = len(g.Players)
	stats.LoadMillis = time.Since(start).Milliseconds()
	g.Stats = stats
	return g, nil
}

// findFixture returns the already-recorded match that r duplicates, if any.
func findFixture(candidates []*Match, r *rawMatch) *Match {
	for _, c := range candidates {
		if sameFixture(c, r) {
			return c
		}
	}
	return nil
}

// sameFixture decides whether a duplicate key really is the same match. League
// fixtures are unique per (season, home, away); cup ties are not, so we also
// require the dates to be close together.
func sameFixture(prev *Match, r *rawMatch) bool {
	if prev.Date.IsZero() || r.date.IsZero() {
		return true
	}
	d := prev.Date.Sub(r.date)
	if d < 0 {
		d = -d
	}
	if d <= 10*24*time.Hour {
		return true
	}
	// Distant dates but an identical scoreline in a league season is still the
	// same fixture recorded with a bad date.
	return competitionCatalog[prev.Competition].Kind == "league" &&
		prev.HomeGoals == r.homeGoals && prev.AwayGoals == r.awayGoals
}

// mergeMatch folds a lower-priority duplicate into the record already held,
// filling in fields the winner lacks. It reports whether the two sources
// disagreed about the scoreline.
func mergeMatch(dst *Match, r *rawMatch) bool {
	dst.Sources = addAlias(dst.Sources, r.source)
	if dst.Round == 0 {
		dst.Round = r.round
	}
	if dst.Stage == "" {
		dst.Stage = r.stage
	}
	if dst.Venue == "" {
		dst.Venue = r.venue
	}
	if dst.Stats == nil {
		dst.Stats = r.stats
	}
	if dst.KickOff == "" {
		dst.KickOff = r.kickOff
	}
	return dst.HomeGoals != r.homeGoals || dst.AwayGoals != r.awayGoals
}
