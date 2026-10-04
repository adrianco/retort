// matches.go — match filtering and aggregate statistics.
//
// Everything here is computed on the fly from the in-memory match list; the
// whole data set is ~17k games so linear scans answer in milliseconds.
package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// AllCompetitions in display order.
var AllCompetitions = []string{CompSerieA, CompSerieB, CompSerieC, CompCopaBrasil, CompLibertadores}

// ShortComp gives compact competition labels for match lines.
func ShortComp(c string) string {
	switch c {
	case CompSerieA:
		return "Brasileirão"
	case CompSerieB:
		return "Série B"
	case CompSerieC:
		return "Série C"
	case CompLibertadores:
		return "Libertadores"
	}
	return c
}

// ParseCompetition maps free text to competitions. Empty or "all" means
// every competition.
func ParseCompetition(q string) ([]string, error) {
	f := Fold(q)
	switch {
	case f == "" || f == "all" || f == "any":
		return nil, nil
	case strings.Contains(f, "libertadores"):
		return []string{CompLibertadores}, nil
	case strings.Contains(f, "copa do brasil") || strings.Contains(f, "brazil cup") ||
		strings.Contains(f, "brazilian cup") || f == "cup" || f == "copa":
		return []string{CompCopaBrasil}, nil
	case strings.Contains(f, "serie b") || f == "b":
		return []string{CompSerieB}, nil
	case strings.Contains(f, "serie c") || f == "c":
		return []string{CompSerieC}, nil
	case strings.Contains(f, "serie a") || strings.Contains(f, "brasileir") || strings.Contains(f, "brazilian league") ||
		f == "league" || f == "a" || strings.Contains(f, "campeonato brasileiro"):
		return []string{CompSerieA}, nil
	}
	return nil, fmt.Errorf("unknown competition %q (use Brasileirão/Série A, Série B, Série C, Copa do Brasil or Libertadores)", q)
}

// MatchFilter selects matches. Zero values mean "no constraint".
type MatchFilter struct {
	Team         *Team  // either side
	Opponent     *Team  // the other side (requires Team)
	Venue        string // "home" / "away" relative to Team
	HomeTeam     *Team
	AwayTeam     *Team
	Competitions []string
	Season       int
	SeasonFrom   int
	SeasonTo     int
	DateFrom     time.Time
	DateTo       time.Time
	Stage        string // folded substring of Stage
	Round        string
	// Canonical drops residual cross-file duplicates (used for tables and
	// aggregates so no game is counted twice).
	Canonical bool
	// Derbies keeps only traditional rivalry games.
	Derbies bool
}

// Filter returns matches satisfying f in chronological order.
func (s *Store) Filter(f MatchFilter) []*Match {
	comps := map[string]bool{}
	for _, c := range f.Competitions {
		comps[c] = true
	}
	stage := NormalizeStage(f.Stage)
	var out []*Match
	for _, m := range s.Matches {
		if len(comps) > 0 && !comps[m.Competition] {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.SeasonFrom != 0 && m.Season < f.SeasonFrom {
			continue
		}
		if f.SeasonTo != 0 && m.Season > f.SeasonTo {
			continue
		}
		if !f.DateFrom.IsZero() && m.Date.Before(f.DateFrom) {
			continue
		}
		if !f.DateTo.IsZero() && !m.Date.Before(f.DateTo.Add(24*time.Hour)) {
			continue
		}
		if f.Team != nil {
			switch f.Venue {
			case "home":
				if m.Home != f.Team {
					continue
				}
			case "away":
				if m.Away != f.Team {
					continue
				}
			default:
				if !m.Involves(f.Team) {
					continue
				}
			}
			if f.Opponent != nil {
				other := m.Away
				if m.Away == f.Team {
					other = m.Home
				}
				if other != f.Opponent {
					continue
				}
			}
		}
		if f.HomeTeam != nil && m.Home != f.HomeTeam {
			continue
		}
		if f.AwayTeam != nil && m.Away != f.AwayTeam {
			continue
		}
		if stage != "" && NormalizeStage(m.Stage) != stage {
			continue
		}
		if f.Round != "" && m.Round != f.Round {
			continue
		}
		if f.Derbies && DerbyName(m.Home, m.Away) == "" {
			continue
		}
		if f.Canonical && !s.IsCanonical(m) {
			continue
		}
		out = append(out, m)
	}
	return out
}

// Record is a win/draw/loss tally.
type Record struct {
	Team                   *Team
	Played, W, D, L        int
	GF, GA                 int
	CleanSheets            int
	HomePlayed, AwayPlayed int
}

// Points uses three points for a win.
func (r Record) Points() int { return 3*r.W + r.D }

// GD is the goal difference.
func (r Record) GD() int { return r.GF - r.GA }

// WinRate in percent.
func (r Record) WinRate() float64 { return pct(r.W, r.Played) }

// PointsRate is the share of available points won, in percent.
func (r Record) PointsRate() float64 { return pct(r.Points(), 3*r.Played) }

func pct(a, b int) float64 {
	if b == 0 {
		return 0
	}
	return 100 * float64(a) / float64(b)
}

func ratio(a, b int) float64 {
	if b == 0 {
		return 0
	}
	return float64(a) / float64(b)
}

// Add counts match m from team t's perspective.
func (r *Record) Add(m *Match, t *Team) {
	gf, ga := m.HomeGoals, m.AwayGoals
	if m.Away == t {
		gf, ga = ga, gf
		r.AwayPlayed++
	} else {
		r.HomePlayed++
	}
	r.Played++
	r.GF += gf
	r.GA += ga
	if ga == 0 {
		r.CleanSheets++
	}
	switch {
	case gf > ga:
		r.W++
	case gf < ga:
		r.L++
	default:
		r.D++
	}
}

// TeamRecord tallies t's results over ms.
func TeamRecord(t *Team, ms []*Match) Record {
	r := Record{Team: t}
	for _, m := range ms {
		if m.Involves(t) {
			r.Add(m, t)
		}
	}
	return r
}

// Records tallies every team appearing in ms. venue limits to home or away games.
func Records(ms []*Match, venue string) []Record {
	by := map[*Team]*Record{}
	get := func(t *Team) *Record {
		if by[t] == nil {
			by[t] = &Record{Team: t}
		}
		return by[t]
	}
	for _, m := range ms {
		if venue != "away" {
			get(m.Home).Add(m, m.Home)
		}
		if venue != "home" {
			get(m.Away).Add(m, m.Away)
		}
	}
	out := make([]Record, 0, len(by))
	for _, r := range by {
		out = append(out, *r)
	}
	return out
}

// SortStandings orders by points, wins, goal difference, goals scored, name.
func SortStandings(rs []Record) {
	sort.Slice(rs, func(i, j int) bool {
		a, b := rs[i], rs[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.W != b.W {
			return a.W > b.W
		}
		if a.GD() != b.GD() {
			return a.GD() > b.GD()
		}
		if a.GF != b.GF {
			return a.GF > b.GF
		}
		return a.Team.Name < b.Team.Name
	})
}

// Standings computes a league table for a competition season. Teams with
// under a quarter of the leader's games are stray rows (BR-Football-Dataset
// lists a few regional games under "Serie A") and are left out.
func (s *Store) Standings(comp string, season int) ([]Record, []*Match) {
	ms := s.Filter(MatchFilter{Competitions: []string{comp}, Season: season, Canonical: true})
	rs := Records(ms, "")
	maxPlayed := 0
	for _, r := range rs {
		maxPlayed = maxInt(maxPlayed, r.Played)
	}
	stray := map[*Team]bool{}
	for _, r := range rs {
		if r.Played*4 < maxPlayed {
			stray[r.Team] = true
		}
	}
	if len(stray) > 0 {
		var keep []*Match
		for _, m := range ms {
			if !stray[m.Home] && !stray[m.Away] {
				keep = append(keep, m)
			}
		}
		ms = keep
		rs = Records(ms, "")
	}
	SortStandings(rs)
	return rs, ms
}

// RelegationSpots returns how many teams went down from Série A in a season.
func RelegationSpots(comp string, season, teams int) int {
	if comp != CompSerieA {
		return 0
	}
	switch {
	case season == 2003:
		return 2
	case teams >= 20:
		return 4
	}
	return 0
}

// H2H summarises games between a and b.
type H2H struct {
	A, B           *Team
	Matches        []*Match
	AWins, BWins   int
	Draws          int
	AGoals, BGoals int
}

// HeadToHead computes the head-to-head record of a and b within f.
func (s *Store) HeadToHead(a, b *Team, f MatchFilter) H2H {
	f.Team, f.Opponent = a, b
	h := H2H{A: a, B: b, Matches: s.Filter(f)}
	for _, m := range h.Matches {
		ag, bg := m.HomeGoals, m.AwayGoals
		if m.Away == a {
			ag, bg = bg, ag
		}
		h.AGoals += ag
		h.BGoals += bg
		switch {
		case ag > bg:
			h.AWins++
		case bg > ag:
			h.BWins++
		default:
			h.Draws++
		}
	}
	return h
}

// SortBiggestWins orders by goal margin, then winner's goals, then date.
func SortBiggestWins(ms []*Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		di, dj := margin(ms[i]), margin(ms[j])
		if di != dj {
			return di > dj
		}
		wi, wj := maxInt(ms[i].HomeGoals, ms[i].AwayGoals), maxInt(ms[j].HomeGoals, ms[j].AwayGoals)
		if wi != wj {
			return wi > wj
		}
		return ms[i].Date.Before(ms[j].Date)
	})
}

func margin(m *Match) int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// Aggregate summarises a set of matches.
type Aggregate struct {
	Matches                     int
	Goals, HomeGoals, AwayGoals int
	HomeWins, AwayWins, Draws   int
	StatsMatches                int
	Corners, Shots              int
}

// Summarise computes aggregate statistics over ms.
func Summarise(ms []*Match) Aggregate {
	var a Aggregate
	for _, m := range ms {
		a.Matches++
		a.Goals += m.HomeGoals + m.AwayGoals
		a.HomeGoals += m.HomeGoals
		a.AwayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			a.HomeWins++
		case m.AwayGoals > m.HomeGoals:
			a.AwayWins++
		default:
			a.Draws++
		}
		if m.Stats != nil && (m.Stats.HomeCorners+m.Stats.AwayCorners+m.Stats.HomeShots+m.Stats.AwayShots) > 0 {
			a.StatsMatches++
			a.Corners += m.Stats.HomeCorners + m.Stats.AwayCorners
			a.Shots += m.Stats.HomeShots + m.Stats.AwayShots
		}
	}
	return a
}

// Tie is a (possibly two-legged) knockout pairing.
type Tie struct {
	Stage    string
	A, B     *Team
	Legs     []*Match
	AGoals   int
	BGoals   int
	FirstLeg time.Time
}

// Winner returns the aggregate winner, or nil if level (decided on penalties,
// which the data does not record).
func (t Tie) Winner() *Team {
	switch {
	case t.AGoals > t.BGoals:
		return t.A
	case t.BGoals > t.AGoals:
		return t.B
	}
	return nil
}

// Ties groups knockout matches into ties by stage and pairing.
func Ties(ms []*Match) []Tie {
	type key struct {
		season int
		stage  string
		a, b   *Team
	}
	idx := map[key]int{}
	var ties []Tie
	for _, m := range ms {
		if m.Stage == "" || strings.Contains(m.Stage, "group") {
			continue
		}
		a, b := m.Home, m.Away
		if a.Key > b.Key {
			a, b = b, a
		}
		k := key{m.Season, m.Stage, a, b}
		i, ok := idx[k]
		if !ok {
			// The first-leg home side is listed first.
			ties = append(ties, Tie{Stage: m.Stage, A: m.Home, B: m.Away, FirstLeg: m.Date})
			i = len(ties) - 1
			idx[k] = i
		}
		t := &ties[i]
		t.Legs = append(t.Legs, m)
		if m.Home == t.A {
			t.AGoals += m.HomeGoals
			t.BGoals += m.AwayGoals
		} else {
			t.AGoals += m.AwayGoals
			t.BGoals += m.HomeGoals
		}
	}
	return ties
}

// NormalizeStage maps user wording ("finals", "semi-final", "last 16",
// "oitavas") to the stage labels used in the data.
func NormalizeStage(q string) string {
	f := Fold(q)
	switch {
	case f == "":
		return ""
	case strings.Contains(f, "group") || strings.Contains(f, "grupo"):
		return "group stage"
	case strings.Contains(f, "quarter") || strings.Contains(f, "quartas"):
		return "quarterfinals"
	case strings.Contains(f, "semi"):
		return "semifinals"
	case strings.Contains(f, "16") || strings.Contains(f, "oitavas") || strings.Contains(f, "eighth"):
		return "round of 16"
	case strings.Contains(f, "final"):
		return "final"
	}
	return f
}

// StageOrder ranks knockout stage labels from earliest to latest.
func StageOrder(stage string) int {
	switch NormalizeStage(stage) {
	case "group stage":
		return 0
	case "round of 16":
		return 1
	case "quarterfinals":
		return 2
	case "semifinals":
		return 3
	case "final":
		return 4
	}
	return -1
}

// derby describes a traditional rivalry between two canonical clubs.
type derby struct {
	Name string
	A, B string // team keys
}

var derbies = []derby{
	{"Fla-Flu", "flamengo|RJ", "fluminense|RJ"},
	{"Clássico dos Milhões", "flamengo|RJ", "vasco|RJ"},
	{"Clássico da Rivalidade", "flamengo|RJ", "botafogo|RJ"},
	{"Clássico dos Gigantes", "fluminense|RJ", "vasco|RJ"},
	{"Clássico Vovô", "fluminense|RJ", "botafogo|RJ"},
	{"Clássico da Amizade", "botafogo|RJ", "vasco|RJ"},
	{"Derby Paulista", "corinthians|SP", "palmeiras|SP"},
	{"Choque-Rei", "palmeiras|SP", "sao paulo|SP"},
	{"Majestoso", "corinthians|SP", "sao paulo|SP"},
	{"San-São", "santos|SP", "sao paulo|SP"},
	{"Clássico Alvinegro", "corinthians|SP", "santos|SP"},
	{"Clássico da Saudade", "palmeiras|SP", "santos|SP"},
	{"Derby Campineiro", "guarani|SP", "ponte preta|SP"},
	{"Grenal", "gremio|RS", "internacional|RS"},
	{"Clássico Mineiro", "atletico|MG", "cruzeiro|MG"},
	{"Atletiba", "athletico|PR", "coritiba|PR"},
	{"Ba-Vi", "bahia|BA", "vitoria|BA"},
	{"Clássico-Rei", "ceara|CE", "fortaleza|CE"},
	{"Clássico dos Clássicos", "sport|PE", "nautico|PE"},
	{"Clássico das Multidões", "sport|PE", "santa cruz|PE"},
	{"Clássico Goiano", "goias|GO", "vila nova|GO"},
	{"Clássico Catarinense", "avai|SC", "figueirense|SC"},
	{"Re-Pa", "remo|PA", "paysandu|PA"},
	{"Clássico Alagoano", "csa|AL", "crb|AL"},
}

// DerbyName returns the rivalry name if a and b are traditional rivals.
func DerbyName(a, b *Team) string {
	if a == nil || b == nil {
		return ""
	}
	for _, d := range derbies {
		if (a.Key == d.A && b.Key == d.B) || (a.Key == d.B && b.Key == d.A) {
			return d.Name
		}
	}
	return ""
}
