// loader.go reads the six Kaggle CSVs, resolves every team spelling through
// the registry, merges rows that describe the same fixture and produces a
// ready-to-query Store.
//
// The five match files overlap heavily (Serie A 2012-2019 appears in three of
// them), so rows are keyed by competition+season+home+away and merged, with
// the richer source winning per field. Without that step every aggregate would
// be double counted.
package soccer

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// Source keys for the six datasets.
const (
	SrcBrasileirao  = "brasileirao_matches"
	SrcNovo         = "novo_brasileirao"
	SrcCup          = "brazilian_cup"
	SrcLibertadores = "libertadores"
	SrcBRFootball   = "br_football"
	SrcFIFA         = "fifa_players"
)

type sourceSpec struct {
	key      string
	file     string
	priority int // lower wins when two rows describe the same match
	desc     string
	license  string
	url      string
}

var matchSources = []sourceSpec{
	{SrcBrasileirao, "Brasileirao_Matches.csv", 1,
		"Brasileirão Série A fixtures with round numbers and team states (2012-2022)",
		"CC BY 4.0", "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro"},
	{SrcNovo, "novo_campeonato_brasileiro.csv", 2,
		"Historical Brasileirão Série A with stadiums (2003-2019)",
		"CC BY 4.0", "https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019"},
	{SrcCup, "Brazilian_Cup_Matches.csv", 3,
		"Copa do Brasil fixtures by round (2012-2021)",
		"CC BY 4.0", "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro"},
	{SrcLibertadores, "Libertadores_Matches.csv", 4,
		"Copa Libertadores fixtures by stage (2013-2022)",
		"CC BY 4.0", "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro"},
	{SrcBRFootball, "BR-Football-Dataset.csv", 5,
		"Série A/B/C and Copa do Brasil with corners, shots and attacks (2014-2023)",
		"CC0 Public Domain", "https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches"},
}

var playerSource = sourceSpec{SrcFIFA, "fifa_data.csv", 0,
	"FIFA player database: ratings, positions, clubs and attributes",
	"Apache 2.0", "https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data"}

// ---------------------------------------------------------------------------
// Locating the data
// ---------------------------------------------------------------------------

// DefaultDataDir is the location of the CSVs relative to the repository root.
const DefaultDataDir = "data/kaggle"

// DataDirEnv can override the data directory.
const DataDirEnv = "BRAZIL_SOCCER_DATA"

// FindDataDir resolves the directory holding the CSVs. An explicit path wins,
// then $BRAZIL_SOCCER_DATA, then data/kaggle looked up from the working
// directory upwards (which is what makes `go test ./...` work from any
// package directory).
func FindDataDir(explicit string) (string, error) {
	candidates := []string{}
	if explicit != "" {
		candidates = append(candidates, explicit)
	}
	if env := os.Getenv(DataDirEnv); env != "" {
		candidates = append(candidates, env)
	}
	if len(candidates) == 0 {
		wd, err := os.Getwd()
		if err != nil {
			return "", err
		}
		for dir := wd; ; {
			candidates = append(candidates, filepath.Join(dir, DefaultDataDir))
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	for _, c := range candidates {
		if _, err := os.Stat(filepath.Join(c, matchSources[0].file)); err == nil {
			return c, nil
		}
	}
	return "", fmt.Errorf("could not locate the Kaggle CSVs (looked for %s in %s); pass -data or set %s",
		matchSources[0].file, strings.Join(candidates, ", "), DataDirEnv)
}

// ---------------------------------------------------------------------------
// CSV plumbing
// ---------------------------------------------------------------------------

type row struct {
	cols   map[string]int
	values []string
}

func (r row) get(name string) string {
	i, ok := r.cols[name]
	if !ok || i >= len(r.values) {
		return ""
	}
	return strings.TrimSpace(r.values[i])
}

func (r row) getInt(name string) (int, bool) { return ParseIntLoose(r.get(name)) }

// eachRow streams a CSV file, calling fn for every data row. It returns the
// number of data rows read and the number that were malformed: a broken line
// is skipped rather than failing the whole load, but it is never silent.
func eachRow(path string, fn func(r row) error) (rows int, malformed int, err error) {
	f, err := os.Open(path)
	if err != nil {
		return 0, 0, err
	}
	defer f.Close()

	cr := csv.NewReader(f)
	cr.FieldsPerRecord = -1
	cr.LazyQuotes = true
	cr.ReuseRecord = true

	header, err := cr.Read()
	if err != nil {
		return 0, 0, fmt.Errorf("%s: reading header: %w", filepath.Base(path), err)
	}
	cols := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimSpace(strings.TrimPrefix(h, "\ufeff"))
		cols[h] = i
	}

	n := 0
	for {
		rec, err := cr.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			var pe *csv.ParseError
			if errors.As(err, &pe) {
				malformed++
				continue
			}
			return n, malformed, fmt.Errorf("%s: %w", filepath.Base(path), err)
		}
		n++
		if err := fn(row{cols: cols, values: rec}); err != nil {
			return n, malformed, err
		}
	}
	return n, malformed, nil
}

// ---------------------------------------------------------------------------
// Intermediate representation
// ---------------------------------------------------------------------------

// rawMatch is a match row before team names have been canonicalised.
type rawMatch struct {
	source        string
	priority      int
	competitionID string
	season        int
	round         int
	stage         string
	date          time.Time
	hasTime       bool
	home, away    string
	homeGoals     int
	awayGoals     int
	venue         string
	stats         *ExtendedStats
}

type rawPlayer struct {
	p    *Player
	club string
}

// ---------------------------------------------------------------------------
// Load
// ---------------------------------------------------------------------------

// Options tunes what Load reads.
type Options struct {
	DataDir     string
	SkipPlayers bool
}

// Load reads every dataset and returns a queryable Store.
func Load(opts Options) (*Store, error) {
	start := time.Now()
	dir, err := FindDataDir(opts.DataDir)
	if err != nil {
		return nil, err
	}

	type result struct {
		spec      sourceSpec
		matches   []rawMatch
		players   []rawPlayer
		rows      int
		malformed int
		err       error
	}
	specs := append([]sourceSpec{}, matchSources...)
	if !opts.SkipPlayers {
		specs = append(specs, playerSource)
	}
	results := make([]result, len(specs))
	var wg sync.WaitGroup
	for i, spec := range specs {
		wg.Add(1)
		go func(i int, spec sourceSpec) {
			defer wg.Done()
			res := result{spec: spec}
			path := filepath.Join(dir, spec.file)
			switch spec.key {
			case SrcFIFA:
				res.players, res.rows, res.malformed, res.err = loadPlayers(path)
			default:
				res.matches, res.rows, res.malformed, res.err = loadMatchFile(spec, path)
			}
			results[i] = res
		}(i, spec)
	}
	wg.Wait()

	s := &Store{
		DataDir:  dir,
		Teams:    NewTeamRegistry(),
		LoadedAt: start,
	}
	for _, res := range results {
		if res.err != nil {
			return nil, res.err
		}
	}

	// Phase 1: observe every spelling, then freeze the canonical registry.
	for _, res := range results {
		for i := range res.matches {
			s.Teams.Observe(res.matches[i].home)
			s.Teams.Observe(res.matches[i].away)
		}
	}
	s.Teams.Build()

	// Phase 2: materialise and merge matches, richest source first.
	sort.SliceStable(results, func(i, j int) bool { return results[i].spec.priority < results[j].spec.priority })
	merger := newMatchMerger(s.Teams)
	info := map[string]*DatasetInfo{}
	for _, res := range results {
		di := &DatasetInfo{
			Key: res.spec.key, File: res.spec.file, Description: res.spec.desc,
			License: res.spec.license, URL: res.spec.url, Rows: res.rows,
		}
		info[res.spec.key] = di
		comps := map[string]bool{}
		for i := range res.matches {
			rm := &res.matches[i]
			home := s.Teams.Resolve(rm.home)
			away := s.Teams.Resolve(rm.away)
			if home == nil || away == nil || home.ID == away.ID {
				continue
			}
			merger.add(rm, home, away)
			di.Used++
			comps[rm.competitionID] = true
			if di.SeasonMin == 0 || rm.season < di.SeasonMin {
				di.SeasonMin = rm.season
			}
			if rm.season > di.SeasonMax {
				di.SeasonMax = rm.season
			}
		}
		for c := range comps {
			di.Competitions = append(di.Competitions, c)
		}
		sort.Strings(di.Competitions)
	}
	var anomalies []string
	s.Matches, anomalies = merger.finish()
	for _, res := range results {
		if res.malformed > 0 {
			anomalies = append(anomalies, fmt.Sprintf("%s: %d line(s) could not be parsed as CSV and were skipped",
				res.spec.file, res.malformed))
		}
	}
	s.Anomalies = anomalies

	// Phase 3: players, linked to canonical clubs where possible.
	for _, res := range results {
		if res.spec.key != SrcFIFA {
			continue
		}
		di := info[res.spec.key]
		for _, rp := range res.players {
			if t := s.Teams.LinkClub(rp.club); t != nil {
				rp.p.TeamID = t.ID
			}
			s.Players = append(s.Players, rp.p)
			di.Used++
		}
	}

	for _, spec := range specs {
		if di := info[spec.key]; di != nil {
			s.Datasets = append(s.Datasets, *di)
		}
	}

	s.index()
	s.Graph = buildGraph(s)
	s.LoadDuration = time.Since(start)
	return s, nil
}

// ---------------------------------------------------------------------------
// Per-file readers
// ---------------------------------------------------------------------------

func loadMatchFile(spec sourceSpec, path string) ([]rawMatch, int, int, error) {
	var out []rawMatch
	var fn func(r row) error
	switch spec.key {
	case SrcBrasileirao:
		fn = func(r row) error {
			m, ok := parseBrasileirao(r)
			if ok {
				out = append(out, m)
			}
			return nil
		}
	case SrcNovo:
		fn = func(r row) error {
			m, ok := parseNovo(r)
			if ok {
				out = append(out, m)
			}
			return nil
		}
	case SrcCup:
		fn = func(r row) error {
			m, ok := parseCup(r)
			if ok {
				out = append(out, m)
			}
			return nil
		}
	case SrcLibertadores:
		fn = func(r row) error {
			m, ok := parseLibertadores(r)
			if ok {
				out = append(out, m)
			}
			return nil
		}
	case SrcBRFootball:
		fn = func(r row) error {
			m, ok := parseBRFootball(r)
			if ok {
				out = append(out, m)
			}
			return nil
		}
	default:
		return nil, 0, 0, fmt.Errorf("unknown match source %q", spec.key)
	}
	n, malformed, err := eachRow(path, fn)
	if err != nil {
		return nil, n, malformed, err
	}
	for i := range out {
		out[i].source = spec.key
		out[i].priority = spec.priority
	}
	if spec.key == SrcCup {
		labelCupStages(out)
	}
	return out, n, malformed, nil
}

func parseBrasileirao(r row) (rawMatch, bool) {
	date, hasTime, ok := ParseDate(r.get("datetime"))
	if !ok {
		return rawMatch{}, false
	}
	hg, ok1 := r.getInt("home_goal")
	ag, ok2 := r.getInt("away_goal")
	if !ok1 || !ok2 {
		return rawMatch{}, false
	}
	season, _ := r.getInt("season")
	if season == 0 {
		season = date.Year()
	}
	round, _ := r.getInt("round")
	return rawMatch{
		competitionID: CompBrasileirao,
		season:        season,
		round:         round,
		date:          date,
		hasTime:       hasTime,
		home:          r.get("home_team"),
		away:          r.get("away_team"),
		homeGoals:     hg,
		awayGoals:     ag,
	}, true
}

func parseNovo(r row) (rawMatch, bool) {
	date, hasTime, ok := ParseDate(r.get("Data"))
	if !ok {
		return rawMatch{}, false
	}
	hg, ok1 := r.getInt("Gols_mandante")
	ag, ok2 := r.getInt("Gols_visitante")
	if !ok1 || !ok2 {
		return rawMatch{}, false
	}
	season, _ := r.getInt("Ano")
	if season == 0 {
		season = date.Year()
	}
	round, _ := r.getInt("Rodada")
	home := qualifyWithState(r.get("Equipe_mandante"), r.get("Mandante_UF"))
	away := qualifyWithState(r.get("Equipe_visitante"), r.get("Visitante_UF"))
	return rawMatch{
		competitionID: CompBrasileirao,
		season:        season,
		round:         round,
		date:          date,
		hasTime:       hasTime,
		home:          home,
		away:          away,
		homeGoals:     hg,
		awayGoals:     ag,
		venue:         r.get("Arena"),
	}, true
}

// qualifyWithState appends the state column to a club name so that clubs
// sharing a name stay apart ("América" + MG). Names that already identify a
// club on their own are left alone, because the state column is not always
// right: novo_campeonato_brasileiro.csv files Vitória (Bahia) under ES for
// part of its rows, which would otherwise invent a second club.
func qualifyWithState(name, uf string) string {
	uf = strings.ToUpper(strings.TrimSpace(uf))
	if name == "" || uf == "" {
		return name
	}
	if _, ok := BrazilianStates[uf]; !ok {
		return name
	}
	if NormalizeTeamName(name).Qualifier != "" || hasCuratedBareName(name) {
		return name
	}
	return name + "-" + uf
}

func parseCup(r row) (rawMatch, bool) {
	date, hasTime, ok := ParseDate(r.get("datetime"))
	if !ok {
		return rawMatch{}, false
	}
	hg, ok1 := r.getInt("home_goal")
	ag, ok2 := r.getInt("away_goal")
	if !ok1 || !ok2 {
		return rawMatch{}, false
	}
	season, _ := r.getInt("season")
	if season == 0 {
		season = date.Year()
	}
	round, _ := r.getInt("round")
	return rawMatch{
		competitionID: CompCopaDoBrasil,
		season:        season,
		round:         round,
		date:          date,
		hasTime:       hasTime,
		home:          r.get("home_team"),
		away:          r.get("away_team"),
		homeGoals:     hg,
		awayGoals:     ag,
	}, true
}

func parseLibertadores(r row) (rawMatch, bool) {
	date, hasTime, ok := ParseDate(r.get("datetime"))
	if !ok {
		return rawMatch{}, false
	}
	hg, ok1 := r.getInt("home_goal")
	ag, ok2 := r.getInt("away_goal")
	if !ok1 || !ok2 {
		return rawMatch{}, false
	}
	season, _ := r.getInt("season")
	if season == 0 {
		season = date.Year()
	}
	return rawMatch{
		competitionID: CompLibertadores,
		season:        season,
		stage:         strings.ToLower(r.get("stage")),
		date:          date,
		hasTime:       hasTime,
		home:          r.get("home_team"),
		away:          r.get("away_team"),
		homeGoals:     hg,
		awayGoals:     ag,
	}, true
}

var brFootballCompetitions = map[string]string{
	"serie a":        CompBrasileirao,
	"serie b":        CompSerieB,
	"serie c":        CompSerieC,
	"copa do brasil": CompCopaDoBrasil,
}

func parseBRFootball(r row) (rawMatch, bool) {
	comp, ok := brFootballCompetitions[Fold(r.get("tournament"))]
	if !ok {
		return rawMatch{}, false
	}
	date, hasTime, ok := ParseDateTime(r.get("date"), r.get("time"))
	if !ok {
		return rawMatch{}, false
	}
	hg, ok1 := r.getInt("home_goal")
	ag, ok2 := r.getInt("away_goal")
	if !ok1 || !ok2 {
		return rawMatch{}, false
	}
	optInt := func(col string) OptInt {
		if v, ok := r.getInt(col); ok {
			return NewOptInt(v)
		}
		return OptInt{}
	}
	stats := &ExtendedStats{
		HomeCorners:  optInt("home_corner"),
		AwayCorners:  optInt("away_corner"),
		HomeShots:    optInt("home_shots"),
		AwayShots:    optInt("away_shots"),
		HomeAttacks:  optInt("home_attack"),
		AwayAttacks:  optInt("away_attack"),
		TotalCorners: optInt("total_corners"),
		HTHomeResult: r.get("ht_result"),
		HTAwayResult: r.get("at_result"),
	}
	return rawMatch{
		competitionID: comp,
		season:        brFootballSeason(comp, date),
		date:          date,
		hasTime:       hasTime,
		home:          r.get("home"),
		away:          r.get("away"),
		homeGoals:     hg,
		awayGoals:     ag,
		stats:         stats,
	}, true
}

// brFootballSeason derives the season of a BR-Football row, which only carries
// a date. Brazilian league seasons run from April to December, so a league
// fixture played in January or February belongs to the previous season: the
// COVID-delayed 2020 Série A ran until 25 February 2021.
func brFootballSeason(comp string, date time.Time) int {
	if c, ok := CompetitionByID(comp); ok && c.Kind == "league" && date.Month() <= time.February {
		return date.Year() - 1
	}
	return date.Year()
}

// labelCupStages turns Copa do Brasil round numbers into stage names. The
// numbering shifted between formats, so the ladder is derived per season from
// the number of fixtures in each round, counting down from the last round.
func labelCupStages(ms []rawMatch) {
	counts := map[int]map[int]int{} // season -> round -> matches
	for _, m := range ms {
		if counts[m.season] == nil {
			counts[m.season] = map[int]int{}
		}
		counts[m.season][m.round]++
	}
	ladder := []struct {
		name string
		max  int
	}{{"final", 2}, {"semifinals", 4}, {"quarterfinals", 8}, {"round of 16", 16}}

	stages := map[int]map[int]string{} // season -> round -> stage
	for season, rounds := range counts {
		nums := make([]int, 0, len(rounds))
		for r := range rounds {
			nums = append(nums, r)
		}
		sort.Sort(sort.Reverse(sort.IntSlice(nums)))
		stages[season] = map[int]string{}
		li := 0
		for _, r := range nums {
			for li < len(ladder) && rounds[r] > ladder[li].max {
				li++
			}
			if li >= len(ladder) {
				break
			}
			stages[season][r] = ladder[li].name
			li++
		}
	}
	for i := range ms {
		if st, ok := stages[ms[i].season][ms[i].round]; ok {
			ms[i].stage = st
		}
	}
}

func loadPlayers(path string) ([]rawPlayer, int, int, error) {
	var out []rawPlayer
	n, malformed, err := eachRow(path, func(r row) error {
		name := r.get("Name")
		if name == "" {
			return nil
		}
		id, _ := r.getInt("ID")
		age, _ := r.getInt("Age")
		overall, _ := r.getInt("Overall")
		potential, _ := r.getInt("Potential")
		jersey, _ := r.getInt("Jersey Number")
		p := &Player{
			ID:          id,
			Name:        name,
			Age:         age,
			Nationality: r.get("Nationality"),
			Overall:     overall,
			Potential:   potential,
			Club:        r.get("Club"),
			Position:    r.get("Position"),
			Jersey:      jersey,
			Foot:        r.get("Preferred Foot"),
			Height:      r.get("Height"),
			Weight:      r.get("Weight"),
			Value:       r.get("Value"),
			Wage:        r.get("Wage"),
			ReleaseCl:   r.get("Release Clause"),
			Joined:      r.get("Joined"),
			ContractEnd: r.get("Contract Valid Until"),
			WorkRate:    r.get("Work Rate"),
		}
		p.skills = make([]int16, len(SkillNames))
		for i, sn := range SkillNames {
			if v, ok := r.getInt(sn); ok {
				p.skills[i] = int16(v)
			} else {
				p.skills[i] = -1
			}
		}
		out = append(out, rawPlayer{p: p, club: p.Club})
		return nil
	})
	return out, n, malformed, err
}

// ---------------------------------------------------------------------------
// Merging duplicate fixtures
// ---------------------------------------------------------------------------

type matchMerger struct {
	buckets map[string][]*Match
	order   []*Match
	teams   *TeamRegistry
}

func newMatchMerger(teams *TeamRegistry) *matchMerger {
	return &matchMerger{buckets: map[string][]*Match{}, teams: teams}
}

// mergeWindow is how far apart two records for the same fixture may be dated
// before they are treated as different matches (sources disagree by a day for
// late kick-offs).
const mergeWindow = 3 * 24 * time.Hour

// add files a parsed row, merging it into an existing fixture when one of the
// other datasets already described it.
//
// The key deliberately leaves the season out and relies on the date window
// instead: sources disagree about which season a January fixture belongs to,
// but the same pair never meets twice at the same venue within three days.
func (mm *matchMerger) add(rm *rawMatch, home, away *Team) {
	key := fmt.Sprintf("%s|%s|%s", rm.competitionID, home.ID, away.ID)
	for _, existing := range mm.buckets[key] {
		d := existing.Date.Sub(rm.date)
		if d < 0 {
			d = -d
		}
		if d <= mergeWindow {
			mergeInto(existing, rm)
			return
		}
	}
	m := &Match{
		Date:          rm.date,
		HasTime:       rm.hasTime,
		CompetitionID: rm.competitionID,
		Season:        rm.season,
		Round:         rm.round,
		Stage:         rm.stage,
		HomeTeamID:    home.ID,
		AwayTeamID:    away.ID,
		HomeName:      home.Name,
		AwayName:      away.Name,
		HomeGoals:     rm.homeGoals,
		AwayGoals:     rm.awayGoals,
		Venue:         rm.venue,
		Sources:       []string{rm.source},
		Stats:         rm.stats,
	}
	m.ID = fmt.Sprintf("%s:%d:%s:%s-%s", rm.competitionID, rm.season, rm.date.Format("20060102"), home.ID, away.ID)
	mm.buckets[key] = append(mm.buckets[key], m)
	mm.order = append(mm.order, m)
}

// mergeInto folds a lower priority record into the record already held. Scores
// and dates stay with the higher priority source; everything the winner is
// missing is filled in from the newcomer.
func mergeInto(m *Match, rm *rawMatch) {
	seen := false
	for _, s := range m.Sources {
		if s == rm.source {
			seen = true
			break
		}
	}
	if !seen {
		m.Sources = append(m.Sources, rm.source)
	}
	if m.Round == 0 && rm.round > 0 {
		m.Round = rm.round
	}
	if m.Stage == "" && rm.stage != "" {
		m.Stage = rm.stage
	}
	if m.Venue == "" && rm.venue != "" {
		m.Venue = rm.venue
	}
	if !m.HasTime && rm.hasTime {
		m.Date, m.HasTime = rm.date, true
	}
	if m.Stats == nil && rm.stats != nil {
		m.Stats = rm.stats
	}
}

func (mm *matchMerger) finish() ([]*Match, []string) {
	out := mm.order
	sort.SliceStable(out, func(i, j int) bool {
		if !out[i].Date.Equal(out[j].Date) {
			return out[i].Date.Before(out[j].Date)
		}
		if out[i].CompetitionID != out[j].CompetitionID {
			return out[i].CompetitionID < out[j].CompetitionID
		}
		return out[i].ID < out[j].ID
	})
	out, typoNotes := repairLeagueTypos(out, mm.teams)
	out, pruneNotes := pruneLeagueOutliers(out)
	inferCupFinals(out)
	return out, append(typoNotes, pruneNotes...)
}

// repairLeagueTypos reattaches fixtures that a misspelling split off a club.
//
// BR-Football-Dataset.csv spells Vila Nova (Goiás) as "Villa Nova" in two of
// its 2017 Série B rows, which would otherwise leave the season with 21 clubs
// and no champion. A reassignment only happens when the stray club plays far
// too few fixtures for the season, exactly one regular club is one edit away,
// and the two are not the same club already - so América-MG and América-RN,
// whose names are zero edits apart, are never merged.
func repairLeagueTypos(ms []*Match, teams *TeamRegistry) ([]*Match, []string) {
	counts := map[compSeason]map[string]int{}
	for _, m := range ms {
		if c, ok := CompetitionByID(m.CompetitionID); !ok || c.Kind != "league" {
			continue
		}
		cs := compSeason{m.CompetitionID, m.Season}
		if counts[cs] == nil {
			counts[cs] = map[string]int{}
		}
		counts[cs][m.HomeTeamID]++
		counts[cs][m.AwayTeamID]++
	}

	remap := map[compSeason]map[string]string{}
	var notes []string
	// Both maps are walked in a fixed order so the reported anomalies do not
	// change between loads.
	for _, cs := range sortedCompSeasons(counts) {
		played := counts[cs]
		modal := modalCount(played)
		if modal < 8 {
			continue
		}
		for _, id := range sortedKeys(played) {
			n := played[id]
			if n*4 >= modal {
				continue
			}
			stray := teams.Team(id)
			if stray == nil {
				continue
			}
			strayBase := NormalizeTeamName(stray.Name).Base
			var target string
			hits := 0
			for _, other := range sortedKeys(played) {
				on := played[other]
				if other == id || on*2 < modal {
					continue
				}
				candidate := teams.Team(other)
				if candidate == nil {
					continue
				}
				if Levenshtein(strayBase, NormalizeTeamName(candidate.Name).Base) == 1 {
					target, hits = other, hits+1
				}
			}
			if hits != 1 {
				continue
			}
			if remap[cs] == nil {
				remap[cs] = map[string]string{}
			}
			remap[cs][id] = target
			notes = append(notes, fmt.Sprintf("%s %d: %d fixture(s) filed under %q were read as the misspelling of %q and reattached",
				cs.comp, cs.season, n, stray.Name, teams.Team(target).Name))
		}
	}
	if len(remap) == 0 {
		return ms, nil
	}

	kept := ms[:0]
	seen := map[string][]*Match{}
	for _, m := range ms {
		cs := compSeason{m.CompetitionID, m.Season}
		repaired := false
		if fix := remap[cs]; fix != nil {
			if to, ok := fix[m.HomeTeamID]; ok {
				m.HomeTeamID, m.HomeName, repaired = to, teams.Team(to).Name, true
			}
			if to, ok := fix[m.AwayTeamID]; ok {
				m.AwayTeamID, m.AwayName, repaired = to, teams.Team(to).Name, true
			}
		}
		if repaired && m.HomeTeamID == m.AwayTeamID {
			notes = append(notes, fmt.Sprintf("%s %d: dropped %s (%s) after the repair left both sides as the same club",
				m.CompetitionID, m.Season, m.Label(), m.DateString()))
			continue
		}
		// A repair can expose a duplicate of a fixture that was already filed
		// under the correct spelling, so every match is indexed and only the
		// repaired ones are checked against the index.
		key := fmt.Sprintf("%s|%d|%s|%s", m.CompetitionID, m.Season, m.HomeTeamID, m.AwayTeamID)
		if repaired {
			duplicate := false
			for _, other := range seen[key] {
				if within(other.Date, m.Date, mergeWindow) {
					other.Sources = append(other.Sources, m.Sources...)
					duplicate = true
					break
				}
			}
			if duplicate {
				continue
			}
		}
		seen[key] = append(seen[key], m)
		kept = append(kept, m)
	}
	return kept, notes
}

func within(a, b time.Time, window time.Duration) bool {
	d := a.Sub(b)
	if d < 0 {
		d = -d
	}
	return d <= window
}

// pruneLeagueOutliers removes fixtures that a league season cannot contain.
//
// BR-Football-Dataset.csv files a handful of state championship games under
// "Serie A" (Brasília FC vs CA Taguatinga, 30 January 2016). A club cannot
// play one game in a 38 round league, so a fixture is dropped when *both*
// clubs played fewer than a quarter of the season's usual number of games.
// Every drop is reported back to the caller.
func pruneLeagueOutliers(ms []*Match) ([]*Match, []string) {
	counts := map[compSeason]map[string]int{}
	for _, m := range ms {
		c, ok := CompetitionByID(m.CompetitionID)
		if !ok || c.Kind != "league" {
			continue
		}
		cs := compSeason{m.CompetitionID, m.Season}
		if counts[cs] == nil {
			counts[cs] = map[string]int{}
		}
		counts[cs][m.HomeTeamID]++
		counts[cs][m.AwayTeamID]++
	}
	thresholds := map[compSeason]int{}
	for cs, played := range counts {
		modal := modalCount(played)
		if modal >= 8 {
			thresholds[cs] = modal / 4
		}
	}
	var notes []string
	kept := ms[:0]
	for _, m := range ms {
		cs := compSeason{m.CompetitionID, m.Season}
		if t, ok := thresholds[cs]; ok {
			if counts[cs][m.HomeTeamID] < t && counts[cs][m.AwayTeamID] < t {
				notes = append(notes, fmt.Sprintf("dropped %s %d %s (%s): both clubs appear in too few fixtures to belong to this league season",
					m.CompetitionID, m.Season, m.Label(), m.DateString()))
				continue
			}
		}
		kept = append(kept, m)
	}
	return kept, notes
}

// sortedKeys returns a map's keys in a fixed order.
func sortedKeys(m map[string]int) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// sortedCompSeasons orders competition seasons by competition then year.
func sortedCompSeasons(m map[compSeason]map[string]int) []compSeason {
	out := make([]compSeason, 0, len(m))
	for cs := range m {
		out = append(out, cs)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].comp != out[j].comp {
			return out[i].comp < out[j].comp
		}
		return out[i].season < out[j].season
	})
	return out
}

func modalCount(counts map[string]int) int {
	freq := map[int]int{}
	best, bestFreq := 0, 0
	for _, c := range counts {
		freq[c]++
		if freq[c] > bestFreq || (freq[c] == bestFreq && c > best) {
			best, bestFreq = c, freq[c]
		}
	}
	return best
}

// inferCupFinals labels the decisive tie of cup seasons that arrived without
// round numbers (Copa do Brasil 2022-2023 only exist in BR-Football-Dataset).
// The label is only applied when the last two fixtures of the season are the
// two legs of one tie, and it is reported as inferred.
func inferCupFinals(ms []*Match) {
	bySeason := map[int][]*Match{}
	labelled := map[int]bool{}
	for _, m := range ms {
		if m.CompetitionID != CompCopaDoBrasil {
			continue
		}
		bySeason[m.Season] = append(bySeason[m.Season], m)
		if m.Stage != "" {
			labelled[m.Season] = true
		}
	}
	for season, list := range bySeason {
		if labelled[season] || len(list) < 4 {
			continue
		}
		sort.SliceStable(list, func(i, j int) bool { return list[i].Date.Before(list[j].Date) })
		a, b := list[len(list)-2], list[len(list)-1]
		if a.HomeTeamID == b.AwayTeamID && a.AwayTeamID == b.HomeTeamID {
			a.Stage, b.Stage = "final (inferred)", "final (inferred)"
		}
	}
}
