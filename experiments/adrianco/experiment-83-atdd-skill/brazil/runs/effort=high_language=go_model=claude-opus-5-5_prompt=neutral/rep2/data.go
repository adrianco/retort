// Data loading and the in-memory knowledge graph.
//
// All six Kaggle CSV files are loaded at start-up into a Store that acts as
// a small knowledge graph:
//
//	Team ──PLAYED_HOME/PLAYED_AWAY──▶ Match ──IN──▶ Competition/Season
//	Player ──PLAYS_FOR──▶ Team (for FIFA clubs that exist in the match data)
//
// Several files overlap (e.g. Série A 2012-2019 appears in three files), so
// matches are de-duplicated: the same fixture coming from a lower-priority
// source is merged into the existing match (extra statistics such as
// corners/shots are kept) rather than counted twice.
package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Source file names, in priority order (earlier wins on duplicates).
const (
	SrcBrasileirao  = "Brasileirao_Matches.csv"
	SrcHistorical   = "novo_campeonato_brasileiro.csv"
	SrcCup          = "Brazilian_Cup_Matches.csv"
	SrcLibertadores = "Libertadores_Matches.csv"
	SrcExtended     = "BR-Football-Dataset.csv"
	SrcFIFA         = "fifa_data.csv"
)

var matchSources = []string{SrcBrasileirao, SrcHistorical, SrcCup, SrcLibertadores, SrcExtended}

func sourcePriority(src string) int {
	for i, s := range matchSources {
		if s == src {
			return i
		}
	}
	return len(matchSources)
}

// MatchStats holds the extra statistics from BR-Football-Dataset.csv.
type MatchStats struct {
	HomeCorners, AwayCorners int
	HomeAttacks, AwayAttacks int
	HomeShots, AwayShots     int
}

// Match is a single fixture (a node in the graph).
type Match struct {
	ID          int
	Date        time.Time
	HasTime     bool
	Season      int
	Competition string
	Round       string // league round number, if known
	Stage       string // cup/Libertadores stage, if known
	Home, Away  *Team
	HomeGoals   int
	AwayGoals   int
	Arena       string
	Stats       *MatchStats
	Sources     []string
}

// Team is a club node.
type Team struct {
	Key      string
	Name     string
	Region   string
	Variants map[string]int // raw spellings seen in the data
	Matches  []*Match       // sorted by date
	Players  []*Player      // FIFA players whose club resolves to this team
}

// Player is a FIFA player node.
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	Team          *Team // non-nil when Club is a Brazilian club in the match data
	Position      string
	Jersey        string
	Height        string
	Weight        string
	Value         string
	Wage          string
	PreferredFoot string
	WeakFoot      string
	SkillMoves    string
	WorkRate      string
	Joined        string
	LoanedFrom    string
	ContractUntil string
	ReleaseClause string
	Skills        []Skill
	nameFold      string
}

// Skill is one named FIFA attribute rating.
type Skill struct {
	Name  string
	Value int
}

var skillColumns = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
	"Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
	"Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
	"LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
	"Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
	"GKKicking", "GKPositioning", "GKReflexes",
}

// FileInfo describes one loaded CSV file.
type FileInfo struct {
	Name    string
	Rows    int // data rows read
	Loaded  int // rows turned into records
	Skipped int // rows with unusable data (e.g. missing scores)
	Merged  int // match rows merged into an already-known fixture
}

// Store is the loaded knowledge graph.
type Store struct {
	Matches []*Match
	Teams   map[string]*Team
	Players []*Player
	Files   []FileInfo
	DataDir string
	reg     *teamRegistry
	// LoadTime is how long loading took.
	LoadTime time.Duration
}

// rawMatch is a match row before team resolution and de-duplication.
type rawMatch struct {
	source               string
	date                 time.Time
	hasTime              bool
	season               int
	comp                 string
	round, stage         string
	home, away           string
	homeState, awayState string
	hg, ag               int
	arena                string
	stats                *MatchStats
	foreign              bool // names may be non-Brazilian clubs (Libertadores)
	homeP, awayP         parsedName
}

// csvTable is a parsed CSV with header lookup.
type csvTable struct {
	header map[string]int
	rows   [][]string
}

func (t *csvTable) get(row []string, col string) string {
	i, ok := t.header[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func readCSV(path string) (*csvTable, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1
	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("%s: reading header: %w", path, err)
	}
	t := &csvTable{header: map[string]int{}}
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff")
		t.header[strings.TrimSpace(h)] = i
	}
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("%s: %w", path, err)
		}
		t.rows = append(t.rows, row)
	}
	return t, nil
}

// parseGoals parses "2", "2.0" or "\"2\"" goal counts.
func parseGoals(s string) (int, bool) {
	s = strings.Trim(strings.TrimSpace(s), `"`)
	if s == "" || s == "NA" || s == "-" {
		return 0, false
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil || f < 0 || math.IsNaN(f) {
		return 0, false
	}
	return int(math.Round(f)), true
}

func parseIntLoose(s string) int {
	n, _ := parseGoals(s)
	return n
}

// LoadStore loads every CSV in dataDir.
func LoadStore(dataDir string) (*Store, error) {
	start := time.Now()
	s := &Store{Teams: map[string]*Team{}, DataDir: dataDir}
	var raws []*rawMatch
	loaders := []struct {
		file string
		fn   func(*csvTable, *FileInfo) []*rawMatch
	}{
		{SrcBrasileirao, loadBrasileirao},
		{SrcHistorical, loadHistorical},
		{SrcCup, loadCup},
		{SrcLibertadores, loadLibertadores},
		{SrcExtended, loadExtended},
	}
	for _, l := range loaders {
		t, err := readCSV(filepath.Join(dataDir, l.file))
		if err != nil {
			return nil, err
		}
		info := FileInfo{Name: l.file, Rows: len(t.rows)}
		rs := l.fn(t, &info)
		info.Loaded = len(rs)
		s.Files = append(s.Files, info)
		raws = append(raws, rs...)
	}
	reg := newTeamRegistry(raws)
	s.reg = reg
	s.buildMatches(raws, reg)

	t, err := readCSV(filepath.Join(dataDir, SrcFIFA))
	if err != nil {
		return nil, err
	}
	info := FileInfo{Name: SrcFIFA, Rows: len(t.rows)}
	s.loadPlayers(t, &info, reg)
	s.Files = append(s.Files, info)
	s.LoadTime = time.Since(start)
	return s, nil
}

func loadBrasileirao(t *csvTable, info *FileInfo) []*rawMatch {
	var out []*rawMatch
	for _, row := range t.rows {
		d, hasTime, err := parseDate(t.get(row, "datetime"))
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		season, err2 := strconv.Atoi(t.get(row, "season"))
		if err != nil || !ok1 || !ok2 || err2 != nil {
			info.Skipped++
			continue
		}
		out = append(out, &rawMatch{
			source: SrcBrasileirao, date: d, hasTime: hasTime, season: season, comp: CompSerieA,
			round: t.get(row, "round"), home: t.get(row, "home_team"), away: t.get(row, "away_team"),
			homeState: t.get(row, "home_team_state"), awayState: t.get(row, "away_team_state"), hg: hg, ag: ag,
		})
	}
	return out
}

func loadHistorical(t *csvTable, info *FileInfo) []*rawMatch {
	// The Mandante_UF/Visitante_UF columns are not used: they contain errors
	// (Vitória is labelled "ES" instead of "BA"), so states are inferred.
	var out []*rawMatch
	for _, row := range t.rows {
		d, _, err := parseDate(t.get(row, "Data"))
		hg, ok1 := parseGoals(t.get(row, "Gols_mandante"))
		ag, ok2 := parseGoals(t.get(row, "Gols_visitante"))
		season, err2 := strconv.Atoi(t.get(row, "Ano"))
		if err != nil || !ok1 || !ok2 || err2 != nil {
			info.Skipped++
			continue
		}
		out = append(out, &rawMatch{
			source: SrcHistorical, date: d, season: season, comp: CompSerieA,
			round: t.get(row, "Rodada"), home: t.get(row, "Equipe_mandante"), away: t.get(row, "Equipe_visitante"),
			hg: hg, ag: ag, arena: t.get(row, "Arena"),
		})
	}
	return out
}

func loadCup(t *csvTable, info *FileInfo) []*rawMatch {
	var out []*rawMatch
	for _, row := range t.rows {
		d, hasTime, err := parseDate(t.get(row, "datetime"))
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		season, err2 := strconv.Atoi(t.get(row, "season"))
		if err != nil || !ok1 || !ok2 || err2 != nil {
			info.Skipped++
			continue
		}
		out = append(out, &rawMatch{
			source: SrcCup, date: d, hasTime: hasTime, season: season, comp: CompCopaBrasil,
			round: t.get(row, "round"), home: t.get(row, "home_team"), away: t.get(row, "away_team"), hg: hg, ag: ag,
		})
	}
	labelCupStages(out)
	return out
}

// labelCupStages turns Copa do Brasil round numbers into stage names. In a
// completed season the last round has a single two-legged tie (the final),
// so rounds are labelled backwards from it.
func labelCupStages(ms []*rawMatch) {
	bySeason := map[int]map[int]int{}
	for _, m := range ms {
		r, err := strconv.Atoi(m.round)
		if err != nil {
			continue
		}
		if bySeason[m.season] == nil {
			bySeason[m.season] = map[int]int{}
		}
		bySeason[m.season][r]++
	}
	names := []string{"final", "semifinals", "quarterfinals", "round of 16"}
	for _, m := range ms {
		r, err := strconv.Atoi(m.round)
		if err != nil {
			continue
		}
		rounds := bySeason[m.season]
		maxRound := 0
		for k := range rounds {
			if k > maxRound {
				maxRound = k
			}
		}
		m.stage = "round " + m.round
		if rounds[maxRound] <= 2 { // season complete: last round is the final
			if back := maxRound - r; back < len(names) {
				m.stage = names[back]
			}
		}
	}
}

func loadLibertadores(t *csvTable, info *FileInfo) []*rawMatch {
	var out []*rawMatch
	for _, row := range t.rows {
		d, hasTime, err := parseDate(t.get(row, "datetime"))
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		season, err2 := strconv.Atoi(t.get(row, "season"))
		if err != nil || !ok1 || !ok2 || err2 != nil {
			info.Skipped++
			continue
		}
		out = append(out, &rawMatch{
			source: SrcLibertadores, date: d, hasTime: hasTime, season: season, comp: CompLibertadores,
			stage: strings.ToLower(t.get(row, "stage")), home: t.get(row, "home_team"), away: t.get(row, "away_team"),
			hg: hg, ag: ag, foreign: true,
		})
	}
	return out
}

// extendedSeason infers the season of a BR-Football row from its date. The
// 2020 season was delayed by COVID-19 and finished in early 2021.
func extendedSeason(d time.Time) int {
	if d.Year() == 2021 && d.Before(time.Date(2021, 3, 9, 0, 0, 0, 0, time.UTC)) {
		return 2020
	}
	return d.Year()
}

func loadExtended(t *csvTable, info *FileInfo) []*rawMatch {
	var out []*rawMatch
	for _, row := range t.rows {
		d, _, err := parseDate(t.get(row, "date"))
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		comp, err2 := normalizeCompetition(t.get(row, "tournament"))
		if err != nil || !ok1 || !ok2 || err2 != nil || comp == "" {
			info.Skipped++
			continue
		}
		if tm := t.get(row, "time"); tm != "" {
			if tt, err := time.Parse("15:04:05", tm); err == nil {
				d = d.Add(time.Duration(tt.Hour())*time.Hour + time.Duration(tt.Minute())*time.Minute)
			}
		}
		out = append(out, &rawMatch{
			source: SrcExtended, date: d, hasTime: true, season: extendedSeason(d), comp: comp,
			home: t.get(row, "home"), away: t.get(row, "away"), hg: hg, ag: ag,
			stats: &MatchStats{
				HomeCorners: parseIntLoose(t.get(row, "home_corner")), AwayCorners: parseIntLoose(t.get(row, "away_corner")),
				HomeAttacks: parseIntLoose(t.get(row, "home_attack")), AwayAttacks: parseIntLoose(t.get(row, "away_attack")),
				HomeShots: parseIntLoose(t.get(row, "home_shots")), AwayShots: parseIntLoose(t.get(row, "away_shots")),
			},
		})
	}
	return out
}

// teamRegistry resolves parsed names to canonical team keys. Names without a
// state (e.g. "Flamengo") get the state most often observed for that base
// name across all files ("flamengo-rj" rather than "flamengo-pi").
type teamRegistry struct {
	stateCounts map[string]map[string]int
	topFlight   map[string]bool // bases seen in Série A data
}

func newTeamRegistry(raws []*rawMatch) *teamRegistry {
	r := &teamRegistry{stateCounts: map[string]map[string]int{}, topFlight: map[string]bool{}}
	for _, m := range raws {
		m.homeP = parseWithHint(m.home, m.homeState)
		m.awayP = parseWithHint(m.away, m.awayState)
		for _, p := range []parsedName{m.homeP, m.awayP} {
			if m.comp == CompSerieA {
				r.topFlight[p.Base] = true
			}
			if p.Region != "" && !p.Country {
				if r.stateCounts[p.Base] == nil {
					r.stateCounts[p.Base] = map[string]int{}
				}
				r.stateCounts[p.Base][p.Region]++
			}
		}
	}
	return r
}

func parseWithHint(raw, stateHint string) parsedName {
	p := parseTeamName(raw)
	if p.Region == "" && stateHint != "" {
		if st := strings.ToLower(stateHint); brazilianStates[st] {
			p.Region = st
		}
	}
	return p
}

// defaultState returns the most frequently observed state for base.
func (r *teamRegistry) defaultState(base string) string {
	best, bestN := "", 0
	for st, n := range r.stateCounts[base] {
		if n > bestN || (n == bestN && st < best) {
			best, bestN = st, n
		}
	}
	return best
}

// key resolves a parsed name. In a foreign context (Libertadores) a
// suffix-less name is only treated as Brazilian if it is a Série A club.
func (r *teamRegistry) key(p parsedName, foreign bool) string {
	if p.Region != "" {
		return teamKey(p.Base, p.Region)
	}
	if foreign && !r.topFlight[p.Base] {
		return p.Base
	}
	return teamKey(p.Base, r.defaultState(p.Base))
}

// curatedNames overrides display names where the data's spellings are
// ambiguous or inconsistent.
var curatedNames = map[string]string{
	"atletico-mg":      "Atlético Mineiro",
	"atletico-pr":      "Athletico Paranaense",
	"atletico-go":      "Atlético Goianiense",
	"america-mg":       "América Mineiro",
	"america-rn":       "América de Natal",
	"botafogo-rj":      "Botafogo",
	"bragantino-sp":    "Red Bull Bragantino",
	"vasco-rj":         "Vasco da Gama",
	"sport-pe":         "Sport Recife",
	"sao paulo-sp":     "São Paulo",
	"gremio-rs":        "Grêmio",
	"csa-al":           "CSA",
	"crb-al":           "CRB",
	"abc-rn":           "ABC",
	"nautico-pe":       "Náutico",
	"ceara-ce":         "Ceará",
	"goias-go":         "Goiás",
	"avai-sc":          "Avaí",
	"criciuma-sc":      "Criciúma",
	"cuiaba-mt":        "Cuiabá",
	"vitoria-ba":       "Vitória",
	"parana-pr":        "Paraná",
	"internacional-rs": "Internacional",
	"fortaleza-ce":     "Fortaleza",
	"remo-pa":          "Remo",
	"moto-ma":          "Moto Club",
	"portuguesa-sp":    "Portuguesa",
}

func (s *Store) team(key, raw string, p parsedName) *Team {
	t, ok := s.Teams[key]
	if !ok {
		t = &Team{Key: key, Region: p.Region, Variants: map[string]int{}}
		s.Teams[key] = t
	}
	t.Variants[raw]++
	return t
}

func (s *Store) buildMatches(raws []*rawMatch, reg *teamRegistry) {
	sort.SliceStable(raws, func(i, j int) bool {
		return sourcePriority(raws[i].source) < sourcePriority(raws[j].source)
	})
	index := map[string][]*Match{}
	merged := map[string]int{}
	for _, r := range raws {
		home := s.team(reg.key(r.homeP, r.foreign), r.home, r.homeP)
		away := s.team(reg.key(r.awayP, r.foreign), r.away, r.awayP)
		k := r.comp + "|" + home.Key + "|" + away.Key
		var dup *Match
		for _, c := range index[k] {
			days := math.Abs(c.Date.Sub(r.date).Hours()) / 24
			if containsString(c.Sources, r.source) {
				// Within one file only repeated rows (same score, dates at
				// most a day apart because of UTC/local time) are duplicates;
				// other repeats are distinct fixtures or a home/away typo in
				// the source (Botafogo-Flamengo 2009), which we keep.
				if math.Abs(truncDay(c.Date).Sub(truncDay(r.date)).Hours()) <= 24 && c.HomeGoals == r.hg && c.AwayGoals == r.ag {
					dup = c
					break
				}
				continue
			}
			if (isLeague(r.comp) && c.Season == r.season) || days <= 3 {
				dup = c
				break
			}
		}
		if dup != nil {
			dup.Sources = append(dup.Sources, r.source)
			if dup.Stats == nil {
				dup.Stats = r.stats
			}
			if dup.Arena == "" {
				dup.Arena = r.arena
			}
			if dup.Round == "" {
				dup.Round = r.round
			}
			merged[r.source]++
			continue
		}
		m := &Match{
			ID: len(s.Matches) + 1, Date: r.date, HasTime: r.hasTime, Season: r.season,
			Competition: r.comp, Round: r.round, Stage: r.stage, Home: home, Away: away,
			HomeGoals: r.hg, AwayGoals: r.ag, Arena: r.arena, Stats: r.stats, Sources: []string{r.source},
		}
		s.Matches = append(s.Matches, m)
		index[k] = append(index[k], m)
	}
	for i := range s.Files {
		s.Files[i].Merged = merged[s.Files[i].Name]
	}
	s.dropStrayLeagueMatches()
	inferCupFinals(s.Matches)
	sort.SliceStable(s.Matches, func(i, j int) bool { return s.Matches[i].Date.Before(s.Matches[j].Date) })
	for _, m := range s.Matches {
		m.Home.Matches = append(m.Home.Matches, m)
		m.Away.Matches = append(m.Away.Matches, m)
	}
	for key, t := range s.Teams {
		if len(t.Matches) == 0 {
			delete(s.Teams, key)
		}
	}
	s.assignNames()
}

// dropStrayLeagueMatches removes league rows between two clubs that play no
// other match in that league season. BR-Football-Dataset.csv contains e.g. a
// regional "Brasilia FC vs CA Taguatinga" game labelled as Série A 2016.
func (s *Store) dropStrayLeagueMatches() {
	type compSeason struct {
		comp   string
		season int
		team   *Team
	}
	counts := map[compSeason]int{}
	for _, m := range s.Matches {
		if isLeague(m.Competition) {
			counts[compSeason{m.Competition, m.Season, m.Home}]++
			counts[compSeason{m.Competition, m.Season, m.Away}]++
		}
	}
	kept := s.Matches[:0]
	for _, m := range s.Matches {
		if isLeague(m.Competition) &&
			counts[compSeason{m.Competition, m.Season, m.Home}] < 3 &&
			counts[compSeason{m.Competition, m.Season, m.Away}] < 3 {
			continue
		}
		kept = append(kept, m)
	}
	s.Matches = kept
}

func containsString(list []string, s string) bool {
	for _, v := range list {
		if v == s {
			return true
		}
	}
	return false
}

// inferCupFinals labels the Copa do Brasil final for seasons whose round
// information does not reach the final (seasons only present in the extended
// dataset, or 2021 where the cup file stops early): the last match of the
// season, plus the preceding match if it was the first leg between the same
// two clubs.
func inferCupFinals(ms []*Match) {
	bySeason := map[int][]*Match{}
	for _, m := range ms {
		if m.Competition == CompCopaBrasil {
			bySeason[m.Season] = append(bySeason[m.Season], m)
		}
	}
	for _, list := range bySeason {
		hasFinal := false
		for _, m := range list {
			if m.Stage == "final" {
				hasFinal = true
				break
			}
		}
		if hasFinal || len(list) < 2 {
			continue
		}
		sort.Slice(list, func(i, j int) bool { return list[i].Date.Before(list[j].Date) })
		last := list[len(list)-1]
		if last.Stage != "" {
			continue
		}
		last.Stage = "final"
		prev := list[len(list)-2]
		if prev.Stage == "" && prev.Home == last.Away && prev.Away == last.Home {
			prev.Stage = "final"
		}
	}
}

// assignNames picks a display name per team: curated if available,
// otherwise the most common spelling (accented spellings preferred). When
// several clubs share a base name, the less prominent ones get a state
// suffix ("Flamengo-PI").
func (s *Store) assignNames() {
	byBase := map[string][]*Team{}
	for _, t := range s.Teams {
		cands := map[string]int{}
		for raw, n := range t.Variants {
			cands[displayBase(raw)] += n
		}
		best, bestScore := "", math.MinInt
		for name, n := range cands {
			score := n
			if hasNonASCII(name) {
				score += 1 << 20
			}
			if hasGenericToken(name) {
				score -= 1 << 21
			}
			if score > bestScore || (score == bestScore && name < best) {
				best, bestScore = name, score
			}
		}
		t.Name = best
		base := strings.TrimSuffix(t.Key, "-"+t.Region)
		byBase[base] = append(byBase[base], t)
	}
	for _, group := range byBase {
		if len(group) < 2 {
			continue
		}
		sort.Slice(group, func(i, j int) bool { return len(group[i].Matches) > len(group[j].Matches) })
		for _, t := range group[1:] {
			if t.Region != "" {
				t.Name += "-" + strings.ToUpper(t.Region)
			}
		}
	}
	for key, name := range curatedNames {
		if t, ok := s.Teams[key]; ok {
			t.Name = name
		}
	}
}

func (s *Store) loadPlayers(t *csvTable, info *FileInfo, reg *teamRegistry) {
	clubTotal, clubBrazil := map[string]int{}, map[string]int{}
	for _, row := range t.rows {
		id, err := strconv.Atoi(t.get(row, "ID"))
		name := t.get(row, "Name")
		if err != nil || name == "" {
			info.Skipped++
			continue
		}
		p := &Player{
			ID: id, Name: name, Age: parseIntLoose(t.get(row, "Age")), Nationality: t.get(row, "Nationality"),
			Overall: parseIntLoose(t.get(row, "Overall")), Potential: parseIntLoose(t.get(row, "Potential")),
			Club: t.get(row, "Club"), Position: t.get(row, "Position"), Jersey: strings.TrimSuffix(t.get(row, "Jersey Number"), ".0"),
			Height: t.get(row, "Height"), Weight: t.get(row, "Weight"), Value: t.get(row, "Value"), Wage: t.get(row, "Wage"),
			PreferredFoot: t.get(row, "Preferred Foot"), WeakFoot: t.get(row, "Weak Foot"), SkillMoves: t.get(row, "Skill Moves"),
			WorkRate: t.get(row, "Work Rate"), Joined: t.get(row, "Joined"), LoanedFrom: t.get(row, "Loaned From"),
			ContractUntil: t.get(row, "Contract Valid Until"), ReleaseClause: t.get(row, "Release Clause"),
			nameFold: foldText(name),
		}
		for _, c := range skillColumns {
			if v := t.get(row, c); v != "" {
				p.Skills = append(p.Skills, Skill{Name: c, Value: parseIntLoose(v)})
			}
		}
		s.Players = append(s.Players, p)
		if p.Club != "" {
			clubTotal[p.Club]++
			if p.Nationality == "Brazil" {
				clubBrazil[p.Club]++
			}
		}
	}
	info.Loaded = len(s.Players)
	// A FIFA club is linked to a team node when its name resolves to a club
	// in the Brazilian match data and most of its squad is Brazilian (this
	// keeps e.g. Argentina's River Plate away from River Plate-SE).
	clubTeam := map[string]*Team{}
	for club, n := range clubTotal {
		if clubBrazil[club]*2 < n {
			continue
		}
		key := reg.key(parseTeamName(club), false)
		if team, ok := s.Teams[key]; ok {
			clubTeam[club] = team
		}
	}
	for _, p := range s.Players {
		if team := clubTeam[p.Club]; team != nil {
			p.Team = team
			team.Players = append(team.Players, p)
		}
	}
	for _, team := range s.Teams {
		sort.SliceStable(team.Players, func(i, j int) bool { return team.Players[i].Overall > team.Players[j].Overall })
	}
}

// hasGenericToken reports whether a display name carries club-type words
// such as "FC" or "EC" ("Santa Cruz FC" is less preferable than "Santa Cruz").
func hasGenericToken(name string) bool {
	tokens := strings.Fields(foldText(name))
	if len(tokens) < 2 {
		return false
	}
	return leadingGeneric[tokens[0]] || trailingGeneric[tokens[len(tokens)-1]]
}
