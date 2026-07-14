// query.go - Query and statistics engine for the Brazilian Soccer MCP server.
//
// Context: Operates on the in-memory Store loaded by store.go. Provides
// match filtering, head-to-head records, team statistics, computed league
// standings, competition-level aggregates, and FIFA player search. All
// functions are pure reads over the loaded slices, fast enough (<ms) for
// the spec's 2s/5s latency targets.
package main

import (
	"sort"
	"strings"
	"time"
)

// ---------- match filtering ----------

// MatchFilter selects matches. Zero values mean "no constraint".
type MatchFilter struct {
	Team        string // matches home or away
	Opponent    string // the other side, when Team is also set
	Competition string
	Season      int
	From, To    time.Time
}

func competitionMatches(comp, query string) bool {
	if query == "" {
		return true
	}
	c := normalizeText(comp)
	q := normalizeText(query)
	return strings.Contains(c, q) || strings.Contains(q, c)
}

// FilterMatches returns matches satisfying f, in chronological order.
func (s *Store) FilterMatches(f MatchFilter) []Match {
	var tq, oq Team
	if f.Team != "" {
		tq = parseTeam(f.Team, "")
	}
	if f.Opponent != "" {
		oq = parseTeam(f.Opponent, "")
	}
	var out []Match
	for _, m := range s.Matches {
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if !f.From.IsZero() && m.Date.Before(f.From) {
			continue
		}
		if !f.To.IsZero() && m.Date.After(f.To) {
			continue
		}
		switch {
		case f.Team != "" && f.Opponent != "":
			if !(teamQueryMatches(m.Home, tq) && teamQueryMatches(m.Away, oq)) &&
				!(teamQueryMatches(m.Away, tq) && teamQueryMatches(m.Home, oq)) {
				continue
			}
		case f.Team != "":
			if !teamQueryMatches(m.Home, tq) && !teamQueryMatches(m.Away, tq) {
				continue
			}
		case f.Opponent != "":
			if !teamQueryMatches(m.Home, oq) && !teamQueryMatches(m.Away, oq) {
				continue
			}
		}
		out = append(out, m)
	}
	return out
}

// ---------- head to head ----------

// H2H summarizes the record between two teams.
type H2H struct {
	Team1, Team2        string
	Wins1, Wins2, Draws int
	Goals1, Goals2      int
	Matches             []Match
}

// HeadToHead computes the record between two teams, optionally limited to a
// competition.
func (s *Store) HeadToHead(team1, team2, competition string) H2H {
	t1 := parseTeam(team1, "")
	t2 := parseTeam(team2, "")
	h := H2H{Team1: t1.Name, Team2: t2.Name}
	for _, m := range s.Matches {
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		var g1, g2 int
		switch {
		case teamQueryMatches(m.Home, t1) && teamQueryMatches(m.Away, t2):
			g1, g2 = m.HomeGoals, m.AwayGoals
		case teamQueryMatches(m.Home, t2) && teamQueryMatches(m.Away, t1):
			g1, g2 = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		h.Matches = append(h.Matches, m)
		h.Goals1 += g1
		h.Goals2 += g2
		switch {
		case g1 > g2:
			h.Wins1++
		case g2 > g1:
			h.Wins2++
		default:
			h.Draws++
		}
	}
	return h
}

// ---------- team statistics ----------

// Record is a W/D/L + goals tally.
type Record struct {
	Played, Wins, Draws, Losses int
	GoalsFor, GoalsAgainst      int
}

func (r Record) Points() int { return r.Wins*3 + r.Draws }

func (r Record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Played) * 100
}

// TeamStats aggregates a team's record. venue is "home", "away" or "" (all).
// Returns the overall record plus a per-competition breakdown.
func (s *Store) TeamStats(team string, season int, competition, venue string) (Record, map[string]*Record, int) {
	tq := parseTeam(team, "")
	var total Record
	byComp := map[string]*Record{}
	n := 0
	for _, m := range s.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		isHome := teamQueryMatches(m.Home, tq)
		isAway := teamQueryMatches(m.Away, tq)
		if isHome && isAway {
			continue // team playing itself: query too ambiguous to attribute
		}
		var gf, ga int
		switch {
		case isHome && venue != "away":
			gf, ga = m.HomeGoals, m.AwayGoals
		case isAway && venue != "home":
			gf, ga = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		n++
		for _, r := range []*Record{&total, ensureRecord(byComp, m.Competition)} {
			r.Played++
			r.GoalsFor += gf
			r.GoalsAgainst += ga
			switch {
			case gf > ga:
				r.Wins++
			case ga > gf:
				r.Losses++
			default:
				r.Draws++
			}
		}
	}
	return total, byComp, n
}

func ensureRecord(m map[string]*Record, key string) *Record {
	if r, ok := m[key]; ok {
		return r
	}
	r := &Record{}
	m[key] = r
	return r
}

// ---------- standings ----------

// StandingRow is one team's line in a computed league table.
type StandingRow struct {
	Team string
	Record
}

var sourcePriority = map[string]int{
	SrcSerieA:       0,
	SrcSerieAHist:   1,
	SrcCopaDoBrasil: 2,
	SrcLibertadores: 2,
	SrcExtended:     3,
}

// Standings computes a league table from match results for one competition
// and season. When several datasets cover the same season, only the highest
// priority source is used so matches are never double counted. Returns the
// table and the number of matches it was computed from.
func (s *Store) Standings(competition string, season int) ([]StandingRow, int) {
	if competition == "" {
		competition = CompSerieA
	}
	var pool []Match
	best := 99
	for _, m := range s.Matches {
		if m.Season != season || !competitionMatches(m.Competition, competition) {
			continue
		}
		if p := sourcePriority[m.Source]; p < best {
			best = p
			pool = pool[:0]
		} else if p > best {
			continue
		}
		pool = append(pool, m)
	}

	type group struct {
		name  string
		base  string
		state string
		rec   Record
	}
	groups := map[string]*group{}
	get := func(t Team) *group {
		key := t.Base + "|" + t.State
		g, ok := groups[key]
		if !ok {
			g = &group{name: t.Name, base: t.Base, state: t.State}
			groups[key] = g
		}
		return g
	}
	for _, m := range pool {
		h, a := get(m.Home), get(m.Away)
		h.rec.Played++
		a.rec.Played++
		h.rec.GoalsFor += m.HomeGoals
		h.rec.GoalsAgainst += m.AwayGoals
		a.rec.GoalsFor += m.AwayGoals
		a.rec.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			h.rec.Wins++
			a.rec.Losses++
		case m.HomeGoals < m.AwayGoals:
			a.rec.Wins++
			h.rec.Losses++
		default:
			h.rec.Draws++
			a.rec.Draws++
		}
	}

	// Disambiguate display names that share a base (e.g. Atlético-MG/PR/GO).
	baseCount := map[string]int{}
	for _, g := range groups {
		baseCount[g.base]++
	}
	rows := make([]StandingRow, 0, len(groups))
	for _, g := range groups {
		name := g.name
		if baseCount[g.base] > 1 && g.state != "" &&
			!strings.Contains(normalizeText(name), g.state) {
			name += "-" + strings.ToUpper(g.state)
		}
		rows = append(rows, StandingRow{Team: name, Record: g.rec})
	}
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		gdA, gdB := a.GoalsFor-a.GoalsAgainst, b.GoalsFor-b.GoalsAgainst
		if gdA != gdB {
			return gdA > gdB
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return rows, len(pool)
}

// ---------- competition aggregates ----------

// CompStats holds aggregate statistics over a set of matches.
type CompStats struct {
	Matches                   int
	TotalGoals                int
	HomeWins, AwayWins, Draws int
	BiggestWins               []Match
}

func (c CompStats) AvgGoals() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

func (c CompStats) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.HomeWins) / float64(c.Matches) * 100
}

// CompetitionStats aggregates over an optional competition and season filter.
func (s *Store) CompetitionStats(competition string, season int, topWins int) CompStats {
	var st CompStats
	var pool []Match
	for _, m := range s.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		st.Matches++
		st.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			st.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			st.AwayWins++
		default:
			st.Draws++
		}
		pool = append(pool, m)
	}
	sort.SliceStable(pool, func(i, j int) bool {
		mi := abs(pool[i].HomeGoals - pool[i].AwayGoals)
		mj := abs(pool[j].HomeGoals - pool[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		return pool[i].HomeGoals+pool[i].AwayGoals > pool[j].HomeGoals+pool[j].AwayGoals
	})
	if topWins > len(pool) {
		topWins = len(pool)
	}
	st.BiggestWins = pool[:topWins]
	return st
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

// ---------- players ----------

// PlayerFilter selects FIFA players. Zero values mean "no constraint".
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string // exact code (ST, GK...) or group: forward/midfielder/defender/goalkeeper
	MinOverall  int
	MaxAge      int
	SortBy      string // overall (default), potential, age
	Limit       int
}

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
	"striker":    {"ST", "CF", "LS", "RS"},
	"winger":     {"LW", "RW", "LM", "RM"},
	"midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
	"defender":   {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"},
	"goalkeeper": {"GK"},
}

func positionMatches(pos, query string) bool {
	if query == "" {
		return true
	}
	q := normalizeText(query)
	if group, ok := positionGroups[strings.TrimSuffix(q, "s")]; ok {
		for _, p := range group {
			if strings.EqualFold(pos, p) {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(pos, query)
}

// SearchPlayers filters and sorts the FIFA player database.
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	nameQ := normalizeText(f.Name)
	natQ := normalizeText(f.Nationality)
	clubQ := normalizeText(f.Club)
	var out []Player
	for _, p := range s.Players {
		if nameQ != "" && !strings.Contains(normalizeText(p.Name), nameQ) {
			continue
		}
		if natQ != "" && !strings.Contains(normalizeText(p.Nationality), natQ) {
			continue
		}
		if clubQ != "" && !strings.Contains(normalizeText(p.Club), clubQ) {
			continue
		}
		if !positionMatches(p.Position, f.Position) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxAge != 0 && p.Age > f.MaxAge {
			continue
		}
		out = append(out, p)
	}
	less := func(a, b Player) bool { return a.Overall > b.Overall }
	switch f.SortBy {
	case "potential":
		less = func(a, b Player) bool { return a.Potential > b.Potential }
	case "age":
		less = func(a, b Player) bool { return a.Age < b.Age }
	}
	sort.SliceStable(out, func(i, j int) bool { return less(out[i], out[j]) })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}
