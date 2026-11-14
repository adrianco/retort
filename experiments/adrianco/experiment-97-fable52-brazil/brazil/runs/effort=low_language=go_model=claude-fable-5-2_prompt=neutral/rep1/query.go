// query.go - the query engine: match search, records, standings, rankings,
// head-to-head, season statistics, knockout brackets, derbies and players.
package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter selects matches. Zero values mean "any".
type MatchFilter struct {
	Team        string // free text
	Opponent    string
	Venue       string // "home", "away" or "" (either) - relative to Team
	Competition string
	Season      int
	From, To    string // dates in any supported format
	Stage       string // e.g. "final", "semifinals", "group stage"
	Round       string
	Dataset     string // restrict to one CSV; disables de-duplication
	PlayedOnly  bool
}

func teamSet(ts []*Team) map[*Team]bool {
	s := map[*Team]bool{}
	for _, t := range ts {
		s[t] = true
	}
	return s
}

func teamNames(ts []*Team) string {
	n := make([]string, len(ts))
	for i, t := range ts {
		n[i] = t.Name
	}
	if len(n) > 6 {
		return strings.Join(n[:6], ", ") + fmt.Sprintf(" (+%d more)", len(n)-6)
	}
	return strings.Join(n, ", ")
}

func normalizeDataset(s string) (string, error) {
	f := fold(s)
	switch {
	case f == "" || f == "all" || f == "any":
		return "", nil
	case strings.Contains(f, "extended") || strings.Contains(f, "br-football") || strings.Contains(f, "stat"):
		return SrcExtended, nil
	case strings.Contains(f, "hist") || strings.Contains(f, "novo"):
		return SrcHistorical, nil
	case strings.Contains(f, "libertadores"):
		return SrcLibertadores, nil
	case strings.Contains(f, "cup") || strings.Contains(f, "copa"):
		return SrcCup, nil
	case strings.Contains(f, "brasileir"):
		return SrcBrasileirao, nil
	}
	return "", fmt.Errorf("unknown dataset %q (use brasileirao, copa_do_brasil, libertadores, extended or historical)", s)
}

// compiled filter
type matcher struct {
	db         *DB
	team, opp  map[*Team]bool
	venue      string
	comp       string
	season     int
	from, to   time.Time
	hasFrom    bool
	hasTo      bool
	stage      string
	round      string
	dataset    string
	playedOnly bool
}

func (db *DB) compile(f MatchFilter) (*matcher, error) {
	m := &matcher{db: db, season: f.Season, playedOnly: f.PlayedOnly, round: strings.TrimSpace(f.Round)}
	if f.Team != "" {
		ts := db.ResolveTeam(f.Team)
		if len(ts) == 0 {
			return nil, fmt.Errorf("no team matching %q found in the data", f.Team)
		}
		m.team = teamSet(ts)
	}
	if f.Opponent != "" {
		ts := db.ResolveTeam(f.Opponent)
		if len(ts) == 0 {
			return nil, fmt.Errorf("no team matching %q found in the data", f.Opponent)
		}
		m.opp = teamSet(ts)
		if m.team == nil { // opponent only: treat it as the team
			m.team, m.opp = m.opp, nil
		}
	}
	switch v := fold(f.Venue); v {
	case "", "either", "any", "all", "both":
	case "home", "away":
		if m.team == nil {
			return nil, fmt.Errorf("venue requires a team")
		}
		m.venue = v
	default:
		return nil, fmt.Errorf("venue must be home, away or either, got %q", f.Venue)
	}
	if f.Competition != "" {
		if m.comp = normalizeCompetition(f.Competition); m.comp == "" {
			return nil, fmt.Errorf("unknown competition %q (use Brasileirão/Serie A, Serie B, Serie C, Copa do Brasil or Libertadores)", f.Competition)
		}
	}
	var ok bool
	if f.From != "" {
		if m.from, ok = parseDate(f.From); !ok {
			return nil, fmt.Errorf("cannot parse date %q", f.From)
		}
		m.hasFrom = true
	}
	if f.To != "" {
		if m.to, ok = parseDate(f.To); !ok {
			return nil, fmt.Errorf("cannot parse date %q", f.To)
		}
		if m.to.Hour() == 0 && m.to.Minute() == 0 {
			m.to = m.to.Add(24*time.Hour - time.Second) // inclusive end day
		}
		m.hasTo = true
	}
	if s := fold(f.Stage); s != "" {
		switch {
		case strings.HasPrefix(s, "final"):
			s = "final"
		case strings.HasPrefix(s, "semi"):
			s = "semifinals"
		case strings.HasPrefix(s, "quarter"):
			s = "quarterfinals"
		case strings.Contains(s, "16"):
			s = "round of 16"
		case strings.HasPrefix(s, "group"):
			s = "group stage"
		}
		m.stage = s
	}
	var err error
	if m.dataset, err = normalizeDataset(f.Dataset); err != nil {
		return nil, err
	}
	return m, nil
}

func (m *matcher) match(x *Match) bool {
	if m.dataset != "" {
		if x.Source != m.dataset {
			return false
		}
	} else if !m.db.IsPrimary(x) {
		return false
	}
	if m.playedOnly && !x.Played {
		return false
	}
	if m.comp != "" && x.Competition != m.comp {
		return false
	}
	if m.season != 0 && x.Season != m.season {
		return false
	}
	if m.stage != "" && x.Stage != m.stage {
		return false
	}
	if m.round != "" && x.Round != m.round {
		return false
	}
	if (m.hasFrom || m.hasTo) && !x.HasDate {
		return false
	}
	if m.hasFrom && x.Date.Before(m.from) {
		return false
	}
	if m.hasTo && x.Date.After(m.to) {
		return false
	}
	if m.team != nil {
		h, a := m.team[x.Home], m.team[x.Away]
		switch m.venue {
		case "home":
			a = false
		case "away":
			h = false
		}
		if !h && !a {
			return false
		}
		if m.opp != nil && !((h && m.opp[x.Away]) || (a && m.opp[x.Home])) {
			return false
		}
	}
	return true
}

// FindMatches returns matching fixtures in chronological order.
func (db *DB) FindMatches(f MatchFilter) ([]*Match, error) {
	m, err := db.compile(f)
	if err != nil {
		return nil, err
	}
	var out []*Match
	for _, x := range db.Matches {
		if m.match(x) {
			out = append(out, x)
		}
	}
	return out, nil
}

// Record is an aggregated win/draw/loss record.
type Record struct {
	Team                   *Team
	Played, Wins, Draws    int
	Losses                 int
	GoalsFor, GoalsAgainst int
}

func (r *Record) add(gf, ga int) {
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case gf == ga:
		r.Draws++
	default:
		r.Losses++
	}
}

func (r Record) Points() int   { return 3*r.Wins + r.Draws }
func (r Record) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }
func (r Record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Played)
}

// TeamRecord aggregates the record of f.Team (which must be set) and also
// returns a per-competition breakdown.
func (db *DB) TeamRecord(f MatchFilter) (total Record, byComp map[string]*Record, teams []*Team, err error) {
	if f.Team == "" {
		return total, nil, nil, fmt.Errorf("team is required")
	}
	f.PlayedOnly = true
	m, err := db.compile(f)
	if err != nil {
		return total, nil, nil, err
	}
	teams = db.ResolveTeam(f.Team)
	byComp = map[string]*Record{}
	for _, x := range db.Matches {
		if !m.match(x) {
			continue
		}
		gf, ga := x.HomeGoals, x.AwayGoals
		if !m.team[x.Home] || m.venue == "away" {
			gf, ga = ga, gf
		}
		total.add(gf, ga)
		if byComp[x.Competition] == nil {
			byComp[x.Competition] = &Record{}
		}
		byComp[x.Competition].add(gf, ga)
	}
	return total, byComp, teams, nil
}

// H2H is a head-to-head summary between two teams (or team groups).
type H2H struct {
	A, B           []*Team
	Matches        []*Match
	AWins, BWins   int
	Draws          int
	AGoals, BGoals int
}

func (db *DB) HeadToHead(a, b string, f MatchFilter) (*H2H, error) {
	f.Team, f.Opponent, f.Venue = a, b, ""
	if a == "" || b == "" {
		return nil, fmt.Errorf("two teams are required")
	}
	ms, err := db.FindMatches(f)
	if err != nil {
		return nil, err
	}
	h := &H2H{A: db.ResolveTeam(a), B: db.ResolveTeam(b), Matches: ms}
	as := teamSet(h.A)
	for _, x := range ms {
		if !x.Played {
			continue
		}
		ag, bg := x.HomeGoals, x.AwayGoals
		if !as[x.Home] {
			ag, bg = bg, ag
		}
		h.AGoals += ag
		h.BGoals += bg
		switch {
		case ag > bg:
			h.AWins++
		case ag < bg:
			h.BWins++
		default:
			h.Draws++
		}
	}
	return h, nil
}

// table builds per-team records over the filtered matches. venue restricts
// each team's record to its home or away games.
func (db *DB) table(f MatchFilter, venue string) ([]*Record, error) {
	f.PlayedOnly = true
	f.Venue = ""
	m, err := db.compile(f)
	if err != nil {
		return nil, err
	}
	recs := map[*Team]*Record{}
	get := func(t *Team) *Record {
		if recs[t] == nil {
			recs[t] = &Record{Team: t}
		}
		return recs[t]
	}
	for _, x := range db.Matches {
		if !m.match(x) {
			continue
		}
		if venue != "away" && (m.team == nil || m.team[x.Home]) {
			get(x.Home).add(x.HomeGoals, x.AwayGoals)
		}
		if venue != "home" && (m.team == nil || m.team[x.Away]) {
			get(x.Away).add(x.AwayGoals, x.HomeGoals)
		}
	}
	out := make([]*Record, 0, len(recs))
	for _, r := range recs {
		out = append(out, r)
	}
	return out, nil
}

func sortStandings(rs []*Record) {
	sort.Slice(rs, func(i, j int) bool {
		a, b := rs[i], rs[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team.Name < b.Team.Name
	})
}

// Standings computes a league table (3 pts per win; ties broken by wins, goal
// difference, goals scored). complete reports a full double round-robin.
func (db *DB) Standings(competition string, season int) (rows []*Record, complete bool, err error) {
	comp := normalizeCompetition(competition)
	if competition == "" {
		comp = CompSerieA
	}
	if comp == "" {
		return nil, false, fmt.Errorf("unknown competition %q", competition)
	}
	if season == 0 {
		return nil, false, fmt.Errorf("season is required")
	}
	rows, err = db.table(MatchFilter{Competition: comp, Season: season}, "")
	if err != nil {
		return nil, false, err
	}
	if len(rows) == 0 {
		return nil, false, fmt.Errorf("no played %s matches for season %d (available: %s)", comp, season, db.seasonsOf(comp))
	}
	sortStandings(rows)
	complete = true
	for _, r := range rows {
		if r.Played != 2*(len(rows)-1) {
			complete = false
		}
	}
	return rows, complete, nil
}

func (db *DB) seasonsOf(comp string) string {
	lo, hi := 0, 0
	for _, m := range db.Matches {
		if m.Competition == comp && m.Season > 0 {
			if lo == 0 || m.Season < lo {
				lo = m.Season
			}
			if m.Season > hi {
				hi = m.Season
			}
		}
	}
	if lo == 0 {
		return "none"
	}
	return fmt.Sprintf("%d-%d", lo, hi)
}

var rankMetrics = map[string]func(*Record) float64{
	"points":                  func(r *Record) float64 { return float64(r.Points()) },
	"wins":                    func(r *Record) float64 { return float64(r.Wins) },
	"draws":                   func(r *Record) float64 { return float64(r.Draws) },
	"losses":                  func(r *Record) float64 { return float64(r.Losses) },
	"goals_for":               func(r *Record) float64 { return float64(r.GoalsFor) },
	"goals_against":           func(r *Record) float64 { return float64(r.GoalsAgainst) },
	"goal_difference":         func(r *Record) float64 { return float64(r.GoalDiff()) },
	"win_rate":                func(r *Record) float64 { return r.WinRate() },
	"points_per_match":        func(r *Record) float64 { return float64(r.Points()) / float64(r.Played) },
	"goals_per_match":         func(r *Record) float64 { return float64(r.GoalsFor) / float64(r.Played) },
	"goals_against_per_match": func(r *Record) float64 { return float64(r.GoalsAgainst) / float64(r.Played) },
}

func metricIsRate(m string) bool {
	return strings.Contains(m, "rate") || strings.Contains(m, "per_match")
}

// RankTeams orders teams by a metric over the filtered matches.
func (db *DB) RankTeams(metric string, f MatchFilter, venue string, minMatches int, ascending bool) ([]*Record, error) {
	fn := rankMetrics[metric]
	if fn == nil {
		keys := make([]string, 0, len(rankMetrics))
		for k := range rankMetrics {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		return nil, fmt.Errorf("unknown metric %q (use one of: %s)", metric, strings.Join(keys, ", "))
	}
	venue = fold(venue)
	if venue != "home" && venue != "away" {
		venue = ""
	}
	f.Team, f.Opponent = "", ""
	rows, err := db.table(f, venue)
	if err != nil {
		return nil, err
	}
	if minMatches < 1 {
		minMatches = 1
	}
	out := rows[:0]
	for _, r := range rows {
		if r.Played >= minMatches {
			out = append(out, r)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := fn(out[i]), fn(out[j])
		if a != b {
			return (a > b) != ascending
		}
		if out[i].Played != out[j].Played {
			return out[i].Played > out[j].Played
		}
		return out[i].Team.Name < out[j].Team.Name
	})
	return out, nil
}

// BiggestWins returns played matches ordered by goal margin, then total goals.
func (db *DB) BiggestWins(f MatchFilter, limit int) ([]*Match, error) {
	f.PlayedOnly = true
	ms, err := db.FindMatches(f)
	if err != nil {
		return nil, err
	}
	abs := func(m *Match) int {
		if d := m.HomeGoals - m.AwayGoals; d < 0 {
			return -d
		} else {
			return d
		}
	}
	sort.SliceStable(ms, func(i, j int) bool {
		if abs(ms[i]) != abs(ms[j]) {
			return abs(ms[i]) > abs(ms[j])
		}
		return ms[i].HomeGoals+ms[i].AwayGoals > ms[j].HomeGoals+ms[j].AwayGoals
	})
	if limit > 0 && len(ms) > limit {
		ms = ms[:limit]
	}
	return ms, nil
}

// SeasonStats are aggregate numbers over a set of matches.
type SeasonStats struct {
	Matches, Goals            int
	HomeWins, Draws, AwayWins int
	HomeGoals, AwayGoals      int
	Corners, CornerMatches    float64
	Shots, ShotMatches        float64
}

func (s SeasonStats) AvgGoals() float64 { return ratio(float64(s.Goals), float64(s.Matches)) }
func pct(a, b int) float64              { return 100 * ratio(float64(a), float64(b)) }
func ratio(a, b float64) float64 {
	if b == 0 {
		return 0
	}
	return a / b
}

func (db *DB) Stats(f MatchFilter) (SeasonStats, error) {
	var s SeasonStats
	f.PlayedOnly = true
	ms, err := db.FindMatches(f)
	if err != nil {
		return s, err
	}
	for _, m := range ms {
		s.Matches++
		s.Goals += m.HomeGoals + m.AwayGoals
		s.HomeGoals += m.HomeGoals
		s.AwayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			s.HomeWins++
		case m.HomeGoals == m.AwayGoals:
			s.Draws++
		default:
			s.AwayWins++
		}
		if e := m.Extra; e != nil {
			if e.HasCorners {
				s.Corners += e.HomeCorners + e.AwayCorners
				s.CornerMatches++
			}
			if e.HasShots {
				s.Shots += e.HomeShots + e.AwayShots
				s.ShotMatches++
			}
		}
	}
	return s, nil
}

// Tie is a knockout pairing (one or two legs).
type Tie struct {
	Stage          string
	A, B           *Team
	Matches        []*Match
	AGoals, BGoals int
	Winner         *Team // nil when level on aggregate (penalties/away goals not in data) or unplayed
}

var stageOrder = map[string]int{"group stage": 0, "round of 16": 1, "quarterfinals": 2, "semifinals": 3, "final": 4}

// Bracket groups the knockout matches of a cup season into ties per stage.
func (db *DB) Bracket(competition string, season int) ([]*Tie, error) {
	comp := normalizeCompetition(competition)
	if comp != CompLibertadores && comp != CompCopaDoBrasil {
		return nil, fmt.Errorf("bracket is available for Copa Libertadores and Copa do Brasil, got %q", competition)
	}
	ms, err := db.FindMatches(MatchFilter{Competition: comp, Season: season})
	if err != nil {
		return nil, err
	}
	if len(ms) == 0 {
		return nil, fmt.Errorf("no %s matches for season %d (available: %s)", comp, season, db.seasonsOf(comp))
	}
	ties := map[string]*Tie{}
	var order []*Tie
	for _, m := range ms {
		stage := m.Stage
		if stage == "" && m.Round != "" {
			stage = "round " + m.Round
		}
		if stage == "group stage" || stage == "" {
			continue
		}
		a, b := m.Home, m.Away
		if a.Key > b.Key {
			a, b = b, a
		}
		k := stage + "|" + a.Key + "|" + b.Key
		t := ties[k]
		if t == nil {
			t = &Tie{Stage: stage, A: m.Home, B: m.Away}
			ties[k] = t
			order = append(order, t)
		}
		t.Matches = append(t.Matches, m)
		if m.Played {
			if m.Home == t.A {
				t.AGoals += m.HomeGoals
				t.BGoals += m.AwayGoals
			} else {
				t.AGoals += m.AwayGoals
				t.BGoals += m.HomeGoals
			}
		}
	}
	for _, t := range order {
		played := false
		for _, m := range t.Matches {
			played = played || m.Played
		}
		if played && t.AGoals > t.BGoals {
			t.Winner = t.A
		} else if played && t.BGoals > t.AGoals {
			t.Winner = t.B
		}
	}
	rank := func(s string) int {
		if o, ok := stageOrder[s]; ok {
			return 100 + o
		}
		n := 0
		fmt.Sscanf(s, "round %d", &n)
		return n
	}
	sort.SliceStable(order, func(i, j int) bool { return rank(order[i].Stage) < rank(order[j].Stage) })
	return order, nil
}

// Derby is a traditional rivalry.
type Derby struct{ A, B, Name string }

var derbies = []Derby{
	{"flamengo", "fluminense", "Fla-Flu"}, {"flamengo", "vasco", "Clássico dos Milhões"},
	{"flamengo", "botafogo", "Clássico da Rivalidade"}, {"fluminense", "vasco", "Clássico dos Gigantes"},
	{"fluminense", "botafogo", "Clássico Vovô"}, {"botafogo", "vasco", "Clássico da Amizade"},
	{"corinthians", "palmeiras", "Derby Paulista"}, {"corinthians", "sao paulo", "Majestoso"},
	{"palmeiras", "sao paulo", "Choque-Rei"}, {"corinthians", "santos", "Clássico Alvinegro"},
	{"palmeiras", "santos", "Clássico da Saudade"}, {"santos", "sao paulo", "San-São"},
	{"gremio", "internacional", "Grenal"}, {"atletico", "cruzeiro", "Clássico Mineiro"},
	{"bahia", "vitoria", "Ba-Vi"}, {"sport", "nautico", "Clássico dos Clássicos"},
	{"sport", "santa cruz", "Clássico das Multidões"}, {"nautico", "santa cruz", "Clássico das Emoções"},
	{"ceara", "fortaleza", "Clássico-Rei"}, {"athletico", "coritiba", "Atletiba"},
	{"goias", "vila nova", "Derby do Cerrado"}, {"avai", "figueirense", "Clássico de Florianópolis"},
	{"remo", "paysandu", "Re-Pa"}, {"crb", "csa", "Clássico das Multidões (AL)"},
}

// DerbyName returns the rivalry name for a pairing, or "".
func DerbyName(a, b *Team) string {
	for _, d := range derbies {
		if (d.A == a.Key && d.B == b.Key) || (d.A == b.Key && d.B == a.Key) {
			return d.Name
		}
	}
	return ""
}

// Derbies returns the filtered matches played between traditional rivals.
func (db *DB) Derbies(f MatchFilter) ([]*Match, error) {
	ms, err := db.FindMatches(f)
	if err != nil {
		return nil, err
	}
	out := ms[:0]
	for _, m := range ms {
		if DerbyName(m.Home, m.Away) != "" {
			out = append(out, m)
		}
	}
	return out, nil
}

// PlayerFilter selects players. Zero values mean "any".
type PlayerFilter struct {
	Name, Nationality, Club, Position string
	MinOverall, MaxAge                int
	SortBy                            string // overall (default), potential, age, name or an attribute
}

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"},
	"midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

func positionSet(q string) (map[string]bool, error) {
	f := strings.TrimSuffix(fold(q), "s")
	switch f {
	case "attacker", "striker", "atacante":
		f = "forward"
	case "keeper", "goalie", "goleiro":
		f = "goalkeeper"
	case "midfield", "meia":
		f = "midfielder"
	case "defence", "defense", "back", "zagueiro":
		f = "defender"
	}
	set := map[string]bool{}
	if g, ok := positionGroups[f]; ok {
		for _, p := range g {
			set[p] = true
		}
		return set, nil
	}
	for _, p := range strings.FieldsFunc(strings.ToUpper(q), func(r rune) bool { return r == ',' || r == ' ' || r == '/' }) {
		set[p] = true
	}
	for p := range set {
		known := false
		for _, g := range positionGroups {
			for _, x := range g {
				known = known || x == p
			}
		}
		if !known {
			return nil, fmt.Errorf("unknown position %q (use forward, midfielder, defender, goalkeeper or a code such as ST, CB, GK)", q)
		}
	}
	return set, nil
}

func attributeByName(q string) string {
	f := strings.ReplaceAll(fold(q), "_", "")
	f = strings.ReplaceAll(f, " ", "")
	for _, a := range attributeColumns {
		if strings.ToLower(a) == f {
			return a
		}
	}
	return ""
}

// SearchPlayers filters and sorts the FIFA players.
func (db *DB) SearchPlayers(f PlayerFilter) ([]*Player, error) {
	nameToks := strings.Fields(fold(f.Name))
	nat := fold(f.Nationality)
	switch nat {
	case "brazilian", "brasil", "brasileiro", "brasileiros", "brazilians":
		nat = "brazil"
	}
	var pos map[string]bool
	if f.Position != "" {
		var err error
		if pos, err = positionSet(f.Position); err != nil {
			return nil, err
		}
	}
	club := fold(f.Club)
	clubKey := ""
	if club != "" {
		if ts := db.ResolveTeam(f.Club); len(ts) == 1 {
			for _, p := range db.Players {
				if p.ClubKey == ts[0].Key {
					clubKey = ts[0].Key
					break
				}
			}
		}
	}
	var out []*Player
next:
	for _, p := range db.Players {
		for _, t := range nameToks {
			if !strings.Contains(p.foldName, t) {
				continue next
			}
		}
		if nat != "" && p.foldNat != nat {
			continue
		}
		if pos != nil && !pos[p.Position] {
			continue
		}
		if clubKey != "" {
			if p.ClubKey != clubKey {
				continue
			}
		} else if club != "" && !strings.Contains(p.foldClub, club) {
			continue
		}
		if p.Overall < f.MinOverall || (f.MaxAge > 0 && p.Age > f.MaxAge) {
			continue
		}
		out = append(out, p)
	}
	key := func(p *Player) float64 { return float64(p.Overall) }
	switch s := fold(f.SortBy); s {
	case "", "overall", "rating":
	case "potential":
		key = func(p *Player) float64 { return float64(p.Potential) }
	case "age":
		key = func(p *Player) float64 { return -float64(p.Age) } // youngest first
	case "name":
		sort.SliceStable(out, func(i, j int) bool { return out[i].foldName < out[j].foldName })
		return out, nil
	default:
		a := attributeByName(s)
		if a == "" {
			return nil, fmt.Errorf("unknown sort_by %q (use overall, potential, age, name or an attribute such as Finishing)", f.SortBy)
		}
		key = func(p *Player) float64 { return float64(p.Attributes[a]) }
	}
	sort.SliceStable(out, func(i, j int) bool {
		if key(out[i]) != key(out[j]) {
			return key(out[i]) > key(out[j])
		}
		return out[i].Overall > out[j].Overall
	})
	return out, nil
}

// ClubGroup summarises a club's players in a result set.
type ClubGroup struct {
	Club       string
	Count      int
	AvgOverall float64
	Best       *Player
}

func GroupByClub(ps []*Player) []ClubGroup {
	idx := map[string]int{}
	var out []ClubGroup
	for _, p := range ps {
		c := p.Club
		if c == "" {
			c = "(no club)"
		}
		i, ok := idx[c]
		if !ok {
			i = len(out)
			idx[c] = i
			out = append(out, ClubGroup{Club: c, Best: p})
		}
		g := &out[i]
		g.Count++
		g.AvgOverall += float64(p.Overall)
		if p.Overall > g.Best.Overall {
			g.Best = p
		}
	}
	for i := range out {
		out[i].AvgOverall /= float64(out[i].Count)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Count != out[j].Count {
			return out[i].Count > out[j].Count
		}
		return out[i].AvgOverall > out[j].AvgOverall
	})
	return out
}
