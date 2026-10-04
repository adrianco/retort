// data.go — loading the six Kaggle CSV files into an in-memory store.
//
// Matches from all five match files are normalised into a single Match type
// and de-duplicated: the same Série A game appears in up to three files
// (novo_campeonato_brasileiro, Brasileirao_Matches, BR-Football-Dataset), and
// Copa do Brasil games in two. Duplicates are merged (same competition, teams
// kick-off within 36 hours; the higher-priority source's score wins when
// files disagree), keeping every source name and the
// richest details (round, stage, arena, extended stats).
package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Competition identifiers.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Source file names.
const (
	SrcBrasileirao  = "Brasileirao_Matches.csv"
	SrcCup          = "Brazilian_Cup_Matches.csv"
	SrcLibertadores = "Libertadores_Matches.csv"
	SrcBRFootball   = "BR-Football-Dataset.csv"
	SrcHistorical   = "novo_campeonato_brasileiro.csv"
	SrcFIFA         = "fifa_data.csv"
)

// MatchStats holds the extended statistics from BR-Football-Dataset.csv.
type MatchStats struct {
	HomeCorners, AwayCorners int
	HomeAttacks, AwayAttacks int
	HomeShots, AwayShots     int
}

// Match is one played game.
type Match struct {
	ID          int
	Date        time.Time
	HasTime     bool
	Season      int
	Competition string
	Round       string // league round or cup round number
	Stage       string // knockout stage label (final, semifinals, ...)
	Home, Away  *Team
	HomeGoals   int
	AwayGoals   int
	Arena       string
	Stats       *MatchStats
	Sources     []string
}

// Winner returns the winning team, or nil for a draw.
func (m *Match) Winner() *Team {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return m.Home
	case m.AwayGoals > m.HomeGoals:
		return m.Away
	}
	return nil
}

// Involves reports whether team t played in the match.
func (m *Match) Involves(t *Team) bool { return m.Home == t || m.Away == t }

// Player is one row of the FIFA database.
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	ClubTeam      *Team // set when the club is a Brazilian club in the match data
	Value, Wage   string
	PreferredFoot string
	Position      string
	JerseyNumber  string
	Height        string
	Weight        string
	Joined        string
	ContractUntil string
	Skills        map[string]int
}

// SourceInfo summarises one loaded file.
type SourceInfo struct {
	File    string
	Rows    int
	Loaded  int
	Skipped int
	Notes   string
}

// Store holds all loaded data.
type Store struct {
	Teams   *TeamRegistry
	Matches []*Match
	Players []*Player
	Sources []SourceInfo
	// matchCount per team key (used to rank fuzzy name resolution).
	teamMatches map[*Team]int
	// shadowed marks residual duplicates excluded from aggregates.
	shadowed map[*Match]bool
}

// rawMatch is a match before team names are resolved.
type rawMatch struct {
	src                 string
	date                time.Time
	hasTime             bool
	season              int
	comp                string
	round, stage, arena string
	home, away          string
	homeHint, awayHint  string
	hg, ag              int
	stats               *MatchStats
}

// brazilianFIFAClubs are the FIFA 19 club names that correspond to clubs in
// the Brazilian match data.
var brazilianFIFAClubs = []string{
	"Grêmio", "Atlético Mineiro", "Cruzeiro", "Fluminense", "Santos", "Internacional",
	"América FC (Minas Gerais)", "Botafogo", "Bahia", "Paraná", "Atlético Paranaense",
	"Vitória", "Sport Club do Recife", "Chapecoense", "Ceará Sporting Club",
}

// LoadStore reads all six CSV files from dir.
func LoadStore(dir string) (*Store, error) {
	s := &Store{Teams: NewTeamRegistry(), teamMatches: map[*Team]int{}}
	var raws []rawMatch
	cupRounds := map[cupRound]int{}
	loaders := []struct {
		file string
		fn   func([]string, map[string]int) (rawMatch, error)
	}{
		{SrcBrasileirao, parseBrasileirao},
		{SrcHistorical, parseHistorical},
		{SrcCup, parseCup},
		{SrcLibertadores, parseLibertadores},
		{SrcBRFootball, parseBRFootball},
	}
	for _, l := range loaders {
		info := SourceInfo{File: l.file}
		err := readCSV(filepath.Join(dir, l.file), func(rec []string, hdr map[string]int) {
			info.Rows++
			rm, err := l.fn(rec, hdr)
			if l.file == SrcCup {
				cupRounds[cupRound{rm.season, rm.round}]++
			}
			if err != nil {
				info.Skipped++
				return
			}
			rm.src = l.file
			raws = append(raws, rm)
			info.Loaded++
		})
		if err != nil {
			return nil, err
		}
		if info.Skipped > 0 {
			info.Notes = fmt.Sprintf("%d unplayed/invalid rows skipped", info.Skipped)
		}
		s.Sources = append(s.Sources, info)
	}
	labelCupStages(raws, cupRounds)

	for _, rm := range raws {
		s.Teams.Register(rm.home, rm.homeHint)
		s.Teams.Register(rm.away, rm.awayHint)
	}
	for _, c := range brazilianFIFAClubs {
		s.Teams.Register(c, "")
	}
	s.Teams.Finalize()
	s.mergeMatches(raws)

	players, info, err := loadFIFA(filepath.Join(dir, SrcFIFA), s.Teams)
	if err != nil {
		return nil, err
	}
	s.Players = players
	s.Sources = append(s.Sources, info)

	for _, m := range s.Matches {
		s.teamMatches[m.Home]++
		s.teamMatches[m.Away]++
	}
	s.computeShadowed()
	return s, nil
}

func readCSV(path string, fn func([]string, map[string]int)) error {
	f, err := os.Open(path)
	if err != nil {
		return fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	header, err := r.Read()
	if err != nil {
		return fmt.Errorf("read header of %s: %w", path, err)
	}
	hdr := map[string]int{}
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff")
		hdr[strings.TrimSpace(h)] = i
	}
	for {
		rec, err := r.Read()
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return fmt.Errorf("read %s: %w", path, err)
		}
		fn(rec, hdr)
	}
}

func field(rec []string, hdr map[string]int, name string) string {
	i, ok := hdr[name]
	if !ok || i >= len(rec) {
		return ""
	}
	return strings.TrimSpace(rec[i])
}

// parseGoals accepts "2", "2.0"; "NA", "-" and "" are errors (unplayed).
func parseGoals(s string) (int, error) {
	f, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil || f < 0 {
		return 0, fmt.Errorf("bad goals %q", s)
	}
	return int(f), nil
}

// ParseDate understands the date formats found in the datasets.
func ParseDate(s string) (t time.Time, hasTime bool, err error) {
	s = strings.TrimSpace(s)
	for _, f := range []string{"2006-01-02 15:04:05", "2006-01-02T15:04:05", "2006-01-02 15:04"} {
		if t, err := time.Parse(f, s); err == nil {
			return t, true, nil
		}
	}
	for _, f := range []string{"2006-01-02", "02/01/2006", "2/1/2006", "02-01-2006"} {
		if t, err := time.Parse(f, s); err == nil {
			return t, false, nil
		}
	}
	return time.Time{}, false, fmt.Errorf("bad date %q", s)
}

func goalsPair(rec []string, hdr map[string]int, h, a string) (int, int, error) {
	hg, err := parseGoals(field(rec, hdr, h))
	if err != nil {
		return 0, 0, err
	}
	ag, err := parseGoals(field(rec, hdr, a))
	if err != nil {
		return 0, 0, err
	}
	return hg, ag, nil
}

func parseBrasileirao(rec []string, hdr map[string]int) (rawMatch, error) {
	var rm rawMatch
	var err error
	if rm.date, rm.hasTime, err = ParseDate(field(rec, hdr, "datetime")); err != nil {
		return rm, err
	}
	if rm.hg, rm.ag, err = goalsPair(rec, hdr, "home_goal", "away_goal"); err != nil {
		return rm, err
	}
	rm.season, _ = strconv.Atoi(field(rec, hdr, "season"))
	rm.comp = CompSerieA
	rm.round = field(rec, hdr, "round")
	rm.home, rm.away = field(rec, hdr, "home_team"), field(rec, hdr, "away_team")
	rm.homeHint, rm.awayHint = field(rec, hdr, "home_team_state"), field(rec, hdr, "away_team_state")
	return rm, nil
}

func parseHistorical(rec []string, hdr map[string]int) (rawMatch, error) {
	var rm rawMatch
	var err error
	if rm.date, rm.hasTime, err = ParseDate(field(rec, hdr, "Data")); err != nil {
		return rm, err
	}
	if rm.hg, rm.ag, err = goalsPair(rec, hdr, "Gols_mandante", "Gols_visitante"); err != nil {
		return rm, err
	}
	rm.season, _ = strconv.Atoi(field(rec, hdr, "Ano"))
	rm.comp = CompSerieA
	rm.round = field(rec, hdr, "Rodada")
	rm.arena = field(rec, hdr, "Arena")
	rm.home, rm.away = field(rec, hdr, "Equipe_mandante"), field(rec, hdr, "Equipe_visitante")
	rm.homeHint, rm.awayHint = field(rec, hdr, "Mandante_UF"), field(rec, hdr, "Visitante_UF")
	return rm, nil
}

func parseCup(rec []string, hdr map[string]int) (rawMatch, error) {
	var rm rawMatch
	var err error
	rm.round = field(rec, hdr, "round")
	rm.season, _ = strconv.Atoi(field(rec, hdr, "season"))
	rm.comp = CompCopaBrasil
	rm.home, rm.away = field(rec, hdr, "home_team"), field(rec, hdr, "away_team")
	// Stage labelling needs every row, including unplayed ones; the goals
	// check comes last so labelCupStages can still see the round sizes.
	if rm.date, rm.hasTime, err = ParseDate(field(rec, hdr, "datetime")); err != nil {
		return rm, err
	}
	if rm.hg, rm.ag, err = goalsPair(rec, hdr, "home_goal", "away_goal"); err != nil {
		return rm, err
	}
	return rm, nil
}

func parseLibertadores(rec []string, hdr map[string]int) (rawMatch, error) {
	var rm rawMatch
	var err error
	if rm.date, rm.hasTime, err = ParseDate(field(rec, hdr, "datetime")); err != nil {
		return rm, err
	}
	if rm.hg, rm.ag, err = goalsPair(rec, hdr, "home_goal", "away_goal"); err != nil {
		return rm, err
	}
	if rm.season, err = strconv.Atoi(field(rec, hdr, "season")); err != nil {
		return rm, err
	}
	rm.comp = CompLibertadores
	rm.stage = field(rec, hdr, "stage")
	rm.home, rm.away = field(rec, hdr, "home_team"), field(rec, hdr, "away_team")
	return rm, nil
}

func parseBRFootball(rec []string, hdr map[string]int) (rawMatch, error) {
	var rm rawMatch
	var err error
	if rm.date, _, err = ParseDate(field(rec, hdr, "date")); err != nil {
		return rm, err
	}
	if rm.hg, rm.ag, err = goalsPair(rec, hdr, "home_goal", "away_goal"); err != nil {
		return rm, err
	}
	switch field(rec, hdr, "tournament") {
	case "Serie A":
		rm.comp = CompSerieA
	case "Serie B":
		rm.comp = CompSerieB
	case "Serie C":
		rm.comp = CompSerieC
	case "Copa do Brasil":
		rm.comp = CompCopaBrasil
	default:
		return rm, fmt.Errorf("unknown tournament")
	}
	rm.season = rm.date.Year()
	// The 2020 league season was delayed by COVID-19 and finished in
	// February 2021; the 2021 season only started at the end of May.
	if rm.comp != CompCopaBrasil && rm.season == 2021 && rm.date.Month() <= time.March {
		rm.season = 2020
	}
	rm.home, rm.away = field(rec, hdr, "home"), field(rec, hdr, "away")
	num := func(name string) int {
		f, _ := strconv.ParseFloat(field(rec, hdr, name), 64)
		return int(f)
	}
	rm.stats = &MatchStats{
		HomeCorners: num("home_corner"), AwayCorners: num("away_corner"),
		HomeAttacks: num("home_attack"), AwayAttacks: num("away_attack"),
		HomeShots: num("home_shots"), AwayShots: num("away_shots"),
	}
	return rm, nil
}

type cupRound struct {
	season int
	round  string
}

// labelCupStages names the late Copa do Brasil rounds from the number of
// games listed in each round, including unplayed ones (two-legged ties:
// 2 games = final, 4 = semifinals...).
func labelCupStages(raws []rawMatch, count map[cupRound]int) {
	// Only the last four rounds of a season can be knockout finals etc.;
	// early preliminary rounds also have few games.
	maxRound := map[int]int{}
	for k := range count {
		if n, err := strconv.Atoi(k.round); err == nil && n > maxRound[k.season] {
			maxRound[k.season] = n
		}
	}
	for i := range raws {
		rm := &raws[i]
		if rm.src != SrcCup {
			continue
		}
		if n, err := strconv.Atoi(rm.round); err != nil || n < maxRound[rm.season]-3 {
			continue
		}
		switch count[cupRound{rm.season, rm.round}] {
		case 2:
			rm.stage = "final"
		case 4:
			rm.stage = "semifinals"
		case 8:
			rm.stage = "quarterfinals"
		case 16:
			rm.stage = "round of 16"
		}
	}
}

// sourcePriority orders sources when merging duplicates (lower wins).
var sourcePriority = map[string]int{
	SrcBrasileirao: 0, SrcHistorical: 1, SrcCup: 2, SrcLibertadores: 3, SrcBRFootball: 4,
}

func (s *Store) mergeMatches(raws []rawMatch) {
	sort.SliceStable(raws, func(i, j int) bool {
		return sourcePriority[raws[i].src] < sourcePriority[raws[j].src]
	})
	type mk struct {
		comp       string
		home, away *Team
	}
	index := map[mk][]*Match{}
	for _, rm := range raws {
		home := s.Teams.Lookup(rm.home, rm.homeHint)
		away := s.Teams.Lookup(rm.away, rm.awayHint)
		k := mk{rm.comp, home, away}
		var dup *Match
		for _, m := range index[k] {
			d := m.Date.Sub(rm.date)
			if d < 0 {
				d = -d
			}
			if d <= 36*time.Hour {
				dup = m
				break
			}
		}
		if dup != nil {
			dup.Sources = append(dup.Sources, rm.src)
			if dup.Round == "" {
				dup.Round = rm.round
			}
			if dup.Stage == "" {
				dup.Stage = rm.stage
			}
			if dup.Arena == "" {
				dup.Arena = rm.arena
			}
			if dup.Stats == nil {
				dup.Stats = rm.stats
			}
			continue
		}
		m := &Match{
			ID: len(s.Matches) + 1, Date: rm.date, HasTime: rm.hasTime, Season: rm.season,
			Competition: rm.comp, Round: rm.round, Stage: rm.stage, Home: home, Away: away,
			HomeGoals: rm.hg, AwayGoals: rm.ag, Arena: rm.arena, Stats: rm.stats,
			Sources: []string{rm.src},
		}
		s.Matches = append(s.Matches, m)
		index[k] = append(index[k], m)
	}
	sort.SliceStable(s.Matches, func(i, j int) bool { return s.Matches[i].Date.Before(s.Matches[j].Date) })
}

// computeShadowed flags residual duplicates that survived merging (usually
// because the files disagree on the date or score of a game). A league
// season contains each home/away pairing once and a cup pairing cannot recur
// within four days, so only the copy from the highest-priority file is kept
// for aggregates. Série A and B are double round-robins, so a lone
// BR-Football-Dataset.csv copy of a pairing already confirmed by a better
// file is dropped (that file repeats some rescheduled games); otherwise
// repeats within one file are kept, since they can be genuine (Série C
// second-phase groups) or a mislabelled home side (2009 Botafogo-Flamengo).
func (s *Store) computeShadowed() {
	s.shadowed = map[*Match]bool{}
	type pk struct {
		comp       string
		season     int
		home, away *Team
	}
	groups := map[pk][]*Match{}
	for _, m := range s.Matches {
		k := pk{m.Competition, m.Season, m.Home, m.Away}
		groups[k] = append(groups[k], m)
	}
	best := func(m *Match) int {
		p := 99
		for _, src := range m.Sources {
			if sourcePriority[src] < p {
				p = sourcePriority[src]
			}
		}
		return p
	}
	shareSource := func(a, b *Match) bool {
		for _, x := range a.Sources {
			for _, y := range b.Sources {
				if x == y {
					return true
				}
			}
		}
		return false
	}
	isLeague := func(c string) bool { return c == CompSerieA || c == CompSerieB || c == CompSerieC }
	roundRobin := func(c string) bool { return c == CompSerieA || c == CompSerieB }
	for k, ms := range groups {
		for i, a := range ms {
			for _, b := range ms[i+1:] {
				if s.shadowed[a] || s.shadowed[b] {
					continue
				}
				// Copies sharing a file are genuine repeats unless, in a
				// round-robin league, one copy is confirmed by a better file.
				if shareSource(a, b) && (!roundRobin(k.comp) || best(a) == best(b)) {
					continue
				}
				d := a.Date.Sub(b.Date)
				if d < 0 {
					d = -d
				}
				if !isLeague(k.comp) && d > 4*24*time.Hour {
					continue
				}
				if best(a) < best(b) || (best(a) == best(b) && len(a.Sources) >= len(b.Sources)) {
					s.shadowed[b] = true
				} else {
					s.shadowed[a] = true
				}
			}
		}
	}
}

// IsCanonical reports whether m should be counted in aggregates (it is not
// a residual duplicate of another game).
func (s *Store) IsCanonical(m *Match) bool { return !s.shadowed[m] }

// Seasons lists the seasons available for a competition.
func (s *Store) Seasons(comp string) []int {
	set := map[int]bool{}
	for _, m := range s.Matches {
		if m.Competition == comp {
			set[m.Season] = true
		}
	}
	var out []int
	for y := range set {
		out = append(out, y)
	}
	sort.Ints(out)
	return out
}

// SourceSummary lists the files contributing to ms.
func SourceSummary(ms []*Match) string {
	set := map[string]bool{}
	for _, m := range ms {
		for _, src := range m.Sources {
			set[src] = true
		}
	}
	var out []string
	for src := range set {
		out = append(out, src)
	}
	sort.Slice(out, func(i, j int) bool { return sourcePriority[out[i]] < sourcePriority[out[j]] })
	return strings.Join(out, " + ")
}

// MatchCount returns how many matches a team played in the data.
func (s *Store) MatchCount(t *Team) int { return s.teamMatches[t] }

// ResolveTeam resolves free text to the best team, preferring teams with
// more matches when the name is ambiguous.
func (s *Store) ResolveTeam(q string) (*Team, []*Team) {
	hits := s.Teams.Resolve(q, s.MatchCount)
	if len(hits) == 0 {
		return nil, nil
	}
	return hits[0], hits
}

var skillColumns = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
	"Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
	"Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
	"LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
	"Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
	"GKKicking", "GKPositioning", "GKReflexes",
}

func loadFIFA(path string, reg *TeamRegistry) ([]*Player, SourceInfo, error) {
	info := SourceInfo{File: SrcFIFA}
	brClub := map[string]*Team{}
	for _, c := range brazilianFIFAClubs {
		brClub[c] = reg.Lookup(c, "")
	}
	var players []*Player
	err := readCSV(path, func(rec []string, hdr map[string]int) {
		info.Rows++
		name := field(rec, hdr, "Name")
		if name == "" {
			info.Skipped++
			return
		}
		atoi := func(k string) int { n, _ := strconv.Atoi(field(rec, hdr, k)); return n }
		p := &Player{
			ID: atoi("ID"), Name: name, Age: atoi("Age"), Nationality: field(rec, hdr, "Nationality"),
			Overall: atoi("Overall"), Potential: atoi("Potential"), Club: field(rec, hdr, "Club"),
			Value: field(rec, hdr, "Value"), Wage: field(rec, hdr, "Wage"),
			PreferredFoot: field(rec, hdr, "Preferred Foot"), Position: field(rec, hdr, "Position"),
			JerseyNumber: field(rec, hdr, "Jersey Number"), Height: field(rec, hdr, "Height"),
			Weight: field(rec, hdr, "Weight"), Joined: field(rec, hdr, "Joined"),
			ContractUntil: field(rec, hdr, "Contract Valid Until"), Skills: map[string]int{},
		}
		if p.JerseyNumber != "" {
			if f, err := strconv.ParseFloat(p.JerseyNumber, 64); err == nil {
				p.JerseyNumber = strconv.Itoa(int(f))
			}
		}
		p.ClubTeam = brClub[p.Club]
		for _, c := range skillColumns {
			if v := field(rec, hdr, c); v != "" {
				if n, err := strconv.ParseFloat(v, 64); err == nil {
					p.Skills[c] = int(n)
				}
			}
		}
		players = append(players, p)
		info.Loaded++
	})
	return players, info, err
}
