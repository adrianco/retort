// data.go - loads the six Kaggle CSV files into an in-memory knowledge graph:
// teams (nodes), matches (team-team edges, tagged with competition/season) and
// players (linked to teams through their club).
package main

import (
	"bufio"
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

// Dataset identifiers (one per CSV file).
const (
	SrcBrasileirao  = "brasileirao"
	SrcCup          = "copa_do_brasil"
	SrcLibertadores = "libertadores"
	SrcExtended     = "extended"
	SrcHistorical   = "historical"
)

var sourceFiles = map[string]string{
	SrcBrasileirao:  "Brasileirao_Matches.csv",
	SrcCup:          "Brazilian_Cup_Matches.csv",
	SrcLibertadores: "Libertadores_Matches.csv",
	SrcExtended:     "BR-Football-Dataset.csv",
	SrcHistorical:   "novo_campeonato_brasileiro.csv",
}

// sourcePriority: lower wins when several files cover the same competition-season.
var sourcePriority = map[string]int{SrcBrasileirao: 0, SrcCup: 0, SrcLibertadores: 0, SrcHistorical: 1, SrcExtended: 2}

// Team is a club node.
type Team struct {
	Key   string
	Name  string
	State string
}

// Match is one fixture from any of the match files.
type Match struct {
	Source      string
	Competition string
	Season      int
	Date        time.Time
	HasDate     bool
	Round       string
	Stage       string
	Home, Away  *Team
	HomeGoals   int
	AwayGoals   int
	Played      bool
	Arena       string
	Extra       *MatchExtra

	rawHome, rawAway string
}

// MatchExtra holds the extended statistics of BR-Football-Dataset.csv.
type MatchExtra struct {
	HomeCorners, AwayCorners         float64
	HomeAttacks, AwayAttacks         float64
	HomeShots, AwayShots             float64
	HasCorners, HasAttacks, HasShots bool
}

// Player is one row of the FIFA database.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	ClubKey     string // team key when the club also appears in match data
	Position    string
	Jersey      string
	Height      string
	Weight      string
	Foot        string
	Value       string
	Wage        string
	Attributes  map[string]int

	foldName, foldClub, foldNat string
}

// DB is the loaded knowledge graph.
type DB struct {
	Teams   map[string]*Team
	Matches []*Match
	Players []*Player
	Counts  map[string]int // rows loaded per dataset

	primary   map[string]string // competition|season -> preferred source
	nameCache map[string][3]string
	statesBy  map[string]map[string]int
	teamFolds map[string]string // team key -> folded display name
}

func compSeason(c string, s int) string { return c + "|" + strconv.Itoa(s) }

// FindDataDir locates the directory holding the CSV files.
func FindDataDir(explicit string) (string, error) {
	cands := []string{explicit, os.Getenv("BRSOCCER_DATA_DIR"), "data/kaggle", "../data/kaggle", "."}
	if exe, err := os.Executable(); err == nil {
		cands = append(cands, filepath.Join(filepath.Dir(exe), "data", "kaggle"))
	}
	for _, c := range cands {
		if c == "" {
			continue
		}
		if _, err := os.Stat(filepath.Join(c, sourceFiles[SrcBrasileirao])); err == nil {
			return c, nil
		}
	}
	return "", fmt.Errorf("data directory with %s not found (use -data or BRSOCCER_DATA_DIR)", sourceFiles[SrcBrasileirao])
}

func readCSV(path string) (header map[string]int, rows [][]string, err error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()
	br := bufio.NewReaderSize(f, 1<<16)
	if b, _ := br.Peek(3); len(b) == 3 && b[0] == 0xEF && b[1] == 0xBB && b[2] == 0xBF {
		br.Discard(3)
	}
	r := csv.NewReader(br)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1
	first, err := r.Read()
	if err != nil {
		return nil, nil, fmt.Errorf("%s: %w", path, err)
	}
	header = map[string]int{}
	for i, h := range first {
		header[strings.TrimSpace(h)] = i
	}
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, nil, fmt.Errorf("%s: %w", path, err)
		}
		rows = append(rows, rec)
	}
	return header, rows, nil
}

type rowGetter struct {
	h   map[string]int
	rec []string
}

func (g rowGetter) s(col string) string {
	i, ok := g.h[col]
	if !ok || i >= len(g.rec) {
		return ""
	}
	return strings.TrimSpace(g.rec[i])
}

// num parses "2", "2.0"; ok=false for "", "NA", "-".
func (g rowGetter) num(col string) (float64, bool) {
	v, err := strconv.ParseFloat(g.s(col), 64)
	if err != nil || v != v {
		return 0, false
	}
	return v, true
}

func (g rowGetter) int(col string) int {
	v, _ := g.num(col)
	return int(v)
}

// LoadDB reads all six CSV files from dir.
func LoadDB(dir string) (*DB, error) {
	db := &DB{
		Teams: map[string]*Team{}, Counts: map[string]int{}, primary: map[string]string{},
		nameCache: map[string][3]string{}, statesBy: map[string]map[string]int{}, teamFolds: map[string]string{},
	}
	loaders := []struct {
		src string
		fn  func(rowGetter) *Match
	}{
		{SrcBrasileirao, func(g rowGetter) *Match {
			return &Match{Competition: CompSerieA, Season: g.int("season"), Round: g.s("round"),
				rawHome: g.s("home_team"), rawAway: g.s("away_team")}
		}},
		{SrcCup, func(g rowGetter) *Match {
			return &Match{Competition: CompCopaDoBrasil, Season: g.int("season"), Round: g.s("round"),
				rawHome: g.s("home_team"), rawAway: g.s("away_team")}
		}},
		{SrcLibertadores, func(g rowGetter) *Match {
			return &Match{Competition: CompLibertadores, Season: g.int("season"), Stage: g.s("stage"),
				rawHome: g.s("home_team"), rawAway: g.s("away_team")}
		}},
		{SrcExtended, func(g rowGetter) *Match {
			m := &Match{Competition: normalizeCompetition(g.s("tournament")), rawHome: g.s("home"), rawAway: g.s("away")}
			if m.Competition == "" {
				m.Competition = g.s("tournament")
			}
			e := &MatchExtra{}
			e.HomeCorners, e.HasCorners = g.num("home_corner")
			e.AwayCorners, _ = g.num("away_corner")
			e.HomeAttacks, e.HasAttacks = g.num("home_attack")
			e.AwayAttacks, _ = g.num("away_attack")
			e.HomeShots, e.HasShots = g.num("home_shots")
			e.AwayShots, _ = g.num("away_shots")
			m.Extra = e
			return m
		}},
		{SrcHistorical, func(g rowGetter) *Match {
			return &Match{Competition: CompSerieA, Season: g.int("Ano"), Round: g.s("Rodada"), Arena: g.s("Arena"),
				rawHome: g.s("Equipe_mandante"), rawAway: g.s("Equipe_visitante")}
		}},
	}
	for _, l := range loaders {
		h, rows, err := readCSV(filepath.Join(dir, sourceFiles[l.src]))
		if err != nil {
			return nil, err
		}
		db.Counts[l.src] = len(rows)
		for _, rec := range rows {
			g := rowGetter{h, rec}
			m := l.fn(g)
			m.Source = l.src
			if m.rawHome == "" || m.rawAway == "" {
				continue
			}
			var ds, hg, ag string
			switch l.src {
			case SrcExtended:
				ds, hg, ag = g.s("date")+" "+g.s("time"), "home_goal", "away_goal"
				if _, ok := parseDate(ds); !ok {
					ds = g.s("date")
				}
			case SrcHistorical:
				ds, hg, ag = g.s("Data"), "Gols_mandante", "Gols_visitante"
			default:
				ds, hg, ag = g.s("datetime"), "home_goal", "away_goal"
			}
			m.Date, m.HasDate = parseDate(ds)
			h1, ok1 := g.num(hg)
			a1, ok2 := g.num(ag)
			if ok1 && ok2 {
				m.HomeGoals, m.AwayGoals, m.Played = int(h1), int(a1), true
			}
			if m.Season == 0 && m.HasDate {
				m.Season = inferSeason(m.Competition, m.Date)
			}
			if !m.HasDate && !m.Played && m.Season == 0 {
				continue // placeholder row with no information
			}
			db.noteName(m.rawHome)
			db.noteName(m.rawAway)
			db.Matches = append(db.Matches, m)
		}
	}
	db.buildTeams()
	db.markFinals()
	db.choosePrimary()
	sort.SliceStable(db.Matches, func(i, j int) bool { return db.Matches[i].Date.Before(db.Matches[j].Date) })
	if err := db.loadPlayers(filepath.Join(dir, "fifa_data.csv")); err != nil {
		return nil, err
	}
	return db, nil
}

// inferSeason derives the season for files without a season column. The 2020
// season was played from August 2020 to early 2021 because of the pandemic.
func inferSeason(comp string, d time.Time) int {
	y := d.Year()
	if y == 2021 {
		cut := time.Date(2021, 3, 1, 0, 0, 0, 0, time.UTC)
		if comp == CompCopaDoBrasil {
			cut = time.Date(2021, 3, 9, 0, 0, 0, 0, time.UTC)
		}
		if d.Before(cut) {
			return 2020
		}
	}
	return y
}

func (db *DB) noteName(raw string) {
	if _, ok := db.nameCache[raw]; ok {
		return
	}
	base, state, disp := parseTeamName(raw)
	db.nameCache[raw] = [3]string{base, state, disp}
	if state != "" {
		if db.statesBy[base] == nil {
			db.statesBy[base] = map[string]int{}
		}
		db.statesBy[base][state]++
	}
}

// keyFor decides the final team key for a (base, state) pair.
func (db *DB) keyFor(base, state string) string {
	if state == "" || len(db.statesBy[base]) <= 1 || defaultState[base] == state {
		return base
	}
	return base + "-" + strings.ToLower(state)
}

func nonASCII(s string) int {
	n := 0
	for _, r := range s {
		if r > 127 {
			n++
		}
	}
	return n
}

func (db *DB) buildTeams() {
	type cand struct{ count, accents int }
	names := map[string]map[string]*cand{}
	states := map[string]string{}
	rawKey := map[string]string{}
	for raw, p := range db.nameCache {
		rawKey[raw] = db.keyFor(p[0], p[1])
	}
	for _, m := range db.Matches {
		for _, raw := range []string{m.rawHome, m.rawAway} {
			k := rawKey[raw]
			p := db.nameCache[raw]
			if names[k] == nil {
				names[k] = map[string]*cand{}
			}
			c := names[k][p[2]]
			if c == nil {
				c = &cand{accents: nonASCII(p[2])}
				names[k][p[2]] = c
			}
			c.count++
			if p[1] != "" {
				states[k] = p[1]
			}
		}
	}
	for k, cs := range names {
		best, bc := "", &cand{count: -1}
		for n, c := range cs {
			better := c.accents > bc.accents || (c.accents == bc.accents && (c.count > bc.count || (c.count == bc.count && n < best)))
			if bc.count < 0 || better {
				best, bc = n, c
			}
		}
		st := states[k]
		if st == "" {
			st = defaultState[k]
		}
		if i := strings.LastIndex(k, "-"); i > 0 && len(db.statesBy[k[:i]]) > 1 && !strings.HasSuffix(strings.ToUpper(best), strings.ToUpper(k[i:])) {
			best += "-" + strings.ToUpper(k[i+1:])
		}
		if o, ok := displayOverride[k]; ok {
			best = o
		}
		db.Teams[k] = &Team{Key: k, Name: best, State: st}
		db.teamFolds[k] = fold(best)
	}
	for _, m := range db.Matches {
		m.Home, m.Away = db.Teams[rawKey[m.rawHome]], db.Teams[rawKey[m.rawAway]]
	}
}

// markFinals tags Copa do Brasil finals, which the files do not label.
func (db *DB) markFinals() {
	type ck struct {
		src    string
		season int
	}
	groups := map[ck][]*Match{}
	for _, m := range db.Matches {
		if m.Competition == CompCopaDoBrasil {
			groups[ck{m.Source, m.Season}] = append(groups[ck{m.Source, m.Season}], m)
		}
	}
	samePair := func(a, b *Match) bool {
		return (a.Home == b.Home && a.Away == b.Away) || (a.Home == b.Away && a.Away == b.Home)
	}
	for k, ms := range groups {
		if k.src == SrcCup {
			maxR := 0
			byRound := map[int][]*Match{}
			for _, m := range ms {
				r, _ := strconv.Atoi(m.Round)
				byRound[r] = append(byRound[r], m)
				if r > maxR {
					maxR = r
				}
			}
			if f := byRound[maxR]; len(f) <= 2 && (len(f) == 1 || samePair(f[0], f[1])) {
				for _, m := range f {
					m.Stage = "final"
				}
			}
			continue
		}
		sort.SliceStable(ms, func(i, j int) bool { return ms[i].Date.Before(ms[j].Date) })
		// The file ends in Sept 2023 and starts mid-2014; only tag a two-legged tie
		// that closes a season with a full knockout phase behind it.
		if n := len(ms); n >= 100 && samePair(ms[n-1], ms[n-2]) && ms[n-1].Date.Sub(ms[n-2].Date) < 30*24*time.Hour {
			ms[n-1].Stage, ms[n-2].Stage = "final", "final"
		}
	}
}

// choosePrimary picks, per competition-season, the dataset used for statistics
// so that matches present in several files are not counted twice.
func (db *DB) choosePrimary() {
	played := map[string]map[string]int{}
	for _, m := range db.Matches {
		k := compSeason(m.Competition, m.Season)
		if played[k] == nil {
			played[k] = map[string]int{}
		}
		if m.Played {
			played[k][m.Source]++
		} else {
			played[k][m.Source] += 0
		}
	}
	for k, by := range played {
		max := 0
		for _, n := range by {
			if n > max {
				max = n
			}
		}
		// Highest-priority file wins unless it is missing results that another
		// file has (e.g. the unplayed final rounds of 2022 in Brasileirao_Matches).
		best := ""
		for s, n := range by {
			if float64(n) < 0.97*float64(max) {
				continue
			}
			if best == "" || sourcePriority[s] < sourcePriority[best] || (sourcePriority[s] == sourcePriority[best] && s < best) {
				best = s
			}
		}
		db.primary[k] = best
	}
}

// IsPrimary reports whether m belongs to the de-duplicated default view.
func (db *DB) IsPrimary(m *Match) bool {
	return db.primary[compSeason(m.Competition, m.Season)] == m.Source
}

var attributeColumns = strings.Fields("Crossing Finishing HeadingAccuracy ShortPassing Volleys Dribbling Curve FKAccuracy LongPassing BallControl Acceleration SprintSpeed Agility Reactions Balance ShotPower Jumping Stamina Strength LongShots Aggression Interceptions Positioning Vision Penalties Composure Marking StandingTackle SlidingTackle GKDiving GKHandling GKKicking GKPositioning GKReflexes")

func (db *DB) loadPlayers(path string) error {
	h, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	db.Counts["fifa"] = len(rows)
	clubKeys := map[string]string{}
	for _, rec := range rows {
		g := rowGetter{h, rec}
		p := &Player{
			ID: g.int("ID"), Name: g.s("Name"), Age: g.int("Age"), Nationality: g.s("Nationality"),
			Overall: g.int("Overall"), Potential: g.int("Potential"), Club: g.s("Club"), Position: g.s("Position"),
			Jersey: strings.TrimSuffix(g.s("Jersey Number"), ".0"), Height: g.s("Height"), Weight: g.s("Weight"),
			Foot: g.s("Preferred Foot"), Value: g.s("Value"), Wage: g.s("Wage"), Attributes: map[string]int{},
		}
		if p.Name == "" {
			continue
		}
		for _, c := range attributeColumns {
			if v, ok := g.num(c); ok {
				p.Attributes[c] = int(v)
			}
		}
		p.foldName, p.foldClub, p.foldNat = fold(p.Name), fold(p.Club), fold(p.Nationality)
		if p.Club != "" {
			k, ok := clubKeys[p.Club]
			if !ok {
				// Only exact names or known aliases link to match-data teams, so
				// foreign namesakes (Boavista FC, Santos Laguna) stay unlinked.
				if _, isAlias := aliases[p.foldClub]; isAlias || db.Teams[p.foldClub] != nil {
					base, state, _ := parseTeamName(p.Club)
					if db.Teams[db.keyFor(base, state)] != nil {
						k = db.keyFor(base, state)
					}
				}
				clubKeys[p.Club] = k
			}
			p.ClubKey = k
		}
		db.Players = append(db.Players, p)
	}
	return nil
}

// ResolveTeam turns free text into team keys: an exact (normalized) match if
// there is one, otherwise every team whose name contains the text.
func (db *DB) ResolveTeam(q string) []*Team {
	if strings.TrimSpace(q) == "" {
		return nil
	}
	base, state, _ := parseTeamName(q)
	for _, k := range []string{db.keyFor(base, state), base} {
		if t := db.Teams[k]; t != nil {
			return []*Team{t}
		}
	}
	f := fold(q)
	var out []*Team
	for k, t := range db.Teams {
		if strings.Contains(k, f) || strings.Contains(db.teamFolds[k], f) {
			out = append(out, t)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Key < out[j].Key })
	return out
}
