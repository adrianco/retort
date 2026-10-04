package main

// Query layer: filtering, records, standings, rankings and player search.

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Filter selects matches. Zero values mean "any".
type Filter struct {
	Team        string // team key
	Opponent    string // team key
	Venue       string // "home" or "away", relative to Team
	Competition string // canonical competition name
	Season      int
	From, To    time.Time
	Stage       string // folded substring of stage, or a round number
}

// ResolveCompetition maps free text to a canonical competition name.
func ResolveCompetition(q string) (string, error) {
	f := fold(q)
	switch {
	case f == "" || f == "all" || f == "any":
		return "", nil
	case strings.Contains(f, "libertadores"):
		return CompLibertadores, nil
	case strings.Contains(f, "copa do brasil") || strings.Contains(f, "cup") || f == "copa":
		return CompCup, nil
	case strings.Contains(f, "serie b"):
		return CompSerieB, nil
	case strings.Contains(f, "serie c"):
		return CompSerieC, nil
	case strings.Contains(f, "brasileir") || strings.Contains(f, "serie a") || f == "campeonato brasileiro" || f == "league":
		return CompSerieA, nil
	}
	return "", fmt.Errorf("unknown competition %q (known: %s)", q, strings.Join(allCompetitions, ", "))
}

func (f Filter) matches(m *Match) bool {
	if f.Team != "" {
		home, away := m.HomeKey == f.Team, m.AwayKey == f.Team
		switch f.Venue {
		case "home":
			if !home {
				return false
			}
		case "away":
			if !away {
				return false
			}
		default:
			if !home && !away {
				return false
			}
		}
		if f.Opponent != "" {
			if !(home && m.AwayKey == f.Opponent) && !(away && m.HomeKey == f.Opponent) {
				return false
			}
			if f.Venue == "home" && m.AwayKey != f.Opponent || f.Venue == "away" && m.HomeKey != f.Opponent {
				return false
			}
		}
	}
	if f.Competition != "" && m.Competition != f.Competition {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if !f.From.IsZero() && m.Date.Before(f.From) {
		return false
	}
	if !f.To.IsZero() && !m.Date.Before(f.To.AddDate(0, 0, 1)) {
		return false
	}
	if f.Stage != "" {
		st := fold(f.Stage)
		if st == "final" || st == "finals" {
			if m.Stage != "final" {
				return false
			}
		} else if !strings.Contains(fold(m.Stage), strings.TrimSuffix(st, "s")) && m.Round != f.Stage {
			return false
		}
	}
	return true
}

// FindMatches returns matching matches in chronological order.
func (s *Store) FindMatches(f Filter) []*Match {
	src := s.Matches
	if f.Team != "" {
		src = s.byTeam[f.Team]
	}
	var out []*Match
	for _, m := range src {
		if f.matches(m) {
			out = append(out, m)
		}
	}
	return out
}

// Record is a win/draw/loss tally.
type Record struct {
	Played, Wins, Draws, Losses int
	GoalsFor, GoalsAgainst      int
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
func (r Record) PointsPerGame() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Points()) / float64(r.Played)
}

// RecordFor tallies a team's results over the given matches.
func RecordFor(team string, ms []*Match) Record {
	var r Record
	for _, m := range ms {
		switch team {
		case m.HomeKey:
			r.add(m.HomeGoals, m.AwayGoals)
		case m.AwayKey:
			r.add(m.AwayGoals, m.HomeGoals)
		}
	}
	return r
}

// TeamRow is one line of a standings table or ranking.
type TeamRow struct {
	Team string // key
	Record
}

// table builds per-team records from matches, restricted to a venue if given.
func table(ms []*Match, venue string) []TeamRow {
	idx := map[string]*TeamRow{}
	get := func(k string) *TeamRow {
		r, ok := idx[k]
		if !ok {
			r = &TeamRow{Team: k}
			idx[k] = r
		}
		return r
	}
	for _, m := range ms {
		if venue != "away" {
			get(m.HomeKey).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			get(m.AwayKey).add(m.AwayGoals, m.HomeGoals)
		}
	}
	out := make([]TeamRow, 0, len(idx))
	for _, r := range idx {
		out = append(out, *r)
	}
	return out
}

// Standings computes a league table (3 points per win; ties broken by wins,
// goal difference, goals scored).
func (s *Store) Standings(comp string, season int) []TeamRow {
	all := table(s.FindMatches(Filter{Competition: comp, Season: season}), "")
	// Drop stray rows: a few mislabelled matches in the source data would
	// otherwise add one-match "teams" to a league table.
	maxPlayed := 0
	for _, r := range all {
		maxPlayed = max(maxPlayed, r.Played)
	}
	rows := all[:0]
	for _, r := range all {
		if comp == CompLibertadores || comp == CompCup || r.Played*4 >= maxPlayed {
			rows = append(rows, r)
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
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
		return s.TeamName(a.Team) < s.TeamName(b.Team)
	})
	return rows
}

// Rankings orders teams by a metric over the filtered matches.
func (s *Store) Rankings(f Filter, venue, metric string, minMatches int) ([]TeamRow, error) {
	val, ok := map[string]func(TeamRow) float64{
		"win_rate":        func(r TeamRow) float64 { return r.WinRate() },
		"points_per_game": func(r TeamRow) float64 { return r.PointsPerGame() },
		"points":          func(r TeamRow) float64 { return float64(r.Points()) },
		"wins":            func(r TeamRow) float64 { return float64(r.Wins) },
		"goals_for":       func(r TeamRow) float64 { return float64(r.GoalsFor) },
		"goals_against":   func(r TeamRow) float64 { return -float64(r.GoalsAgainst) },
		"goal_difference": func(r TeamRow) float64 { return float64(r.GoalDiff()) },
	}[metric]
	if !ok {
		return nil, fmt.Errorf("unknown metric %q", metric)
	}
	var rows []TeamRow
	for _, r := range table(s.FindMatches(f), venue) {
		if r.Played >= minMatches {
			rows = append(rows, r)
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		a, b := val(rows[i]), val(rows[j])
		if a != b {
			return a > b
		}
		if rows[i].Played != rows[j].Played {
			return rows[i].Played > rows[j].Played
		}
		return s.TeamName(rows[i].Team) < s.TeamName(rows[j].Team)
	})
	return rows, nil
}

// Summary aggregates a set of matches.
type Summary struct {
	Matches, Goals            int
	HomeWins, Draws, AwayWins int
	HomeGoals, AwayGoals      int
	CornerMatches             int
	Corners                   float64
}

func (a Summary) pct(n int) float64 {
	if a.Matches == 0 {
		return 0
	}
	return 100 * float64(n) / float64(a.Matches)
}
func (a Summary) AvgGoals() float64 {
	if a.Matches == 0 {
		return 0
	}
	return float64(a.Goals) / float64(a.Matches)
}

func Summarize(ms []*Match) Summary {
	var a Summary
	for _, m := range ms {
		a.Matches++
		a.Goals += m.HomeGoals + m.AwayGoals
		a.HomeGoals += m.HomeGoals
		a.AwayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			a.HomeWins++
		case m.HomeGoals == m.AwayGoals:
			a.Draws++
		default:
			a.AwayWins++
		}
		if m.Ext != nil {
			a.CornerMatches++
			a.Corners += m.Ext.HomeCorners + m.Ext.AwayCorners
		}
	}
	return a
}

// BiggestWins returns decisive matches by margin, then total goals, newest first.
func (s *Store) BiggestWins(f Filter, n int) []*Match {
	ms := append([]*Match(nil), s.FindMatches(f)...)
	abs := func(m *Match) int {
		d := m.HomeGoals - m.AwayGoals
		if d < 0 {
			d = -d
		}
		return d
	}
	sort.SliceStable(ms, func(i, j int) bool {
		a, b := ms[i], ms[j]
		if abs(a) != abs(b) {
			return abs(a) > abs(b)
		}
		if ta, tb := a.HomeGoals+a.AwayGoals, b.HomeGoals+b.AwayGoals; ta != tb {
			return ta > tb
		}
		return a.Date.After(b.Date)
	})
	if n > 0 && len(ms) > n {
		ms = ms[:n]
	}
	return ms
}

// Traditional rivalries (clássicos).
var derbyPairs = []struct{ a, b, name string }{
	{"Flamengo", "Fluminense", "Fla-Flu"},
	{"Flamengo", "Vasco", "Clássico dos Milhões"},
	{"Flamengo", "Botafogo", "Clássico da Rivalidade"},
	{"Fluminense", "Vasco", "Clássico dos Gigantes"},
	{"Fluminense", "Botafogo", "Clássico Vovô"},
	{"Botafogo", "Vasco", "Clássico da Amizade"},
	{"Corinthians", "Palmeiras", "Derby Paulista"},
	{"Corinthians", "São Paulo", "Majestoso"},
	{"Palmeiras", "São Paulo", "Choque-Rei"},
	{"Santos", "Corinthians", "Clássico Alvinegro"},
	{"Santos", "Palmeiras", "Clássico da Saudade"},
	{"Santos", "São Paulo", "San-São"},
	{"Grêmio", "Internacional", "Grenal"},
	{"Atlético-MG", "Cruzeiro", "Clássico Mineiro"},
	{"Bahia", "Vitória", "Ba-Vi"},
	{"Athletico-PR", "Coritiba", "Atletiba"},
	{"Sport", "Náutico", "Clássico dos Clássicos"},
	{"Sport", "Santa Cruz", "Clássico das Multidões"},
	{"Ceará", "Fortaleza", "Clássico-Rei"},
	{"Goiás", "Vila Nova", "Derby do Cerrado"},
	{"Avaí", "Figueirense", "Clássico de Florianópolis"},
	{"Remo", "Paysandu", "Re-Pa"},
	{"Guarani", "Ponte Preta", "Derby Campineiro"},
}

// DerbyName returns the rivalry name if the two teams are traditional rivals.
func (s *Store) DerbyName(a, b string) string {
	s.initDerbies()
	if n, ok := s.Reg.derbies[a+"\x00"+b]; ok {
		return n
	}
	return ""
}

func (s *Store) initDerbies() {
	if s.Reg.derbies != nil {
		return
	}
	d := map[string]string{}
	for _, p := range derbyPairs {
		ta, ok1 := s.Reg.Find(p.a)
		tb, ok2 := s.Reg.Find(p.b)
		if ok1 && ok2 {
			d[ta.Key+"\x00"+tb.Key] = p.name
			d[tb.Key+"\x00"+ta.Key] = p.name
		}
	}
	s.Reg.derbies = d
}

// Derbies returns matches between traditional rivals.
func (s *Store) Derbies(f Filter) []*Match {
	var out []*Match
	for _, m := range s.FindMatches(f) {
		if s.DerbyName(m.HomeKey, m.AwayKey) != "" {
			out = append(out, m)
		}
	}
	return out
}

// ---- players ----

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"},
	"midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
	"defender":   {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

// positionSet expands "forwards", "defender", "GK", "ST,CF" into position codes.
func positionSet(q string) map[string]bool {
	set := map[string]bool{}
	for _, part := range strings.FieldsFunc(q, func(r rune) bool { return r == ',' || r == '/' || r == ' ' }) {
		f := strings.TrimSuffix(fold(part), "s")
		switch f {
		case "striker", "attacker", "atacante":
			f = "forward"
		case "keeper", "goalie", "goleiro":
			f = "goalkeeper"
		case "midfield", "meia":
			f = "midfielder"
		case "defence", "defense", "zagueiro":
			f = "defender"
		}
		if g, ok := positionGroups[f]; ok {
			for _, p := range g {
				set[p] = true
			}
		} else {
			set[strings.ToUpper(part)] = true
		}
	}
	return set
}

// PlayerFilter selects players. Zero values mean "any".
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	MaxAge      int
	// BrazilianClubs restricts to clubs that appear in the match data.
	BrazilianClubs bool
}

// normNationality lets "Brazilian"/"Brasil" match the dataset's "Brazil".
func normNationality(q string) string {
	f := fold(q)
	switch f {
	case "brazilian", "brasil", "brasileiro", "brasileiros", "brazilians":
		return "brazil"
	case "argentinian", "argentine":
		return "argentina"
	}
	return f
}

// SearchPlayers returns players sorted by overall rating (descending).
func (s *Store) SearchPlayers(f PlayerFilter) []*Player {
	name := fold(f.Name)
	nameToks := strings.Fields(name)
	nat := normNationality(f.Nationality)
	club := fold(f.Club)
	clubKey := ""
	if club != "" {
		if t, ok := s.Reg.Find(f.Club); ok {
			clubKey = t.Key
		}
	}
	// A club that is linked to the match data is matched exactly, so that
	// "Santos" does not also return Santos Laguna.
	linked := false
	for _, p := range s.Players {
		if clubKey != "" && p.ClubKey == clubKey {
			linked = true
			break
		}
	}
	var pos map[string]bool
	if strings.TrimSpace(f.Position) != "" {
		pos = positionSet(f.Position)
	}
	var out []*Player
	for _, p := range s.Players {
		if name != "" {
			pn := fold(p.Name)
			if !strings.Contains(pn, name) {
				all := true
				for _, t := range nameToks {
					if !strings.Contains(pn, t) {
						all = false
						break
					}
				}
				if !all {
					continue
				}
			}
		}
		if nat != "" && fold(p.Nationality) != nat {
			continue
		}
		if club != "" {
			if linked && p.ClubKey != clubKey {
				continue
			}
			if !linked && !strings.Contains(fold(p.Club), club) {
				continue
			}
		}
		if pos != nil && !pos[p.Position] {
			continue
		}
		if p.Overall < f.MinOverall || (f.MaxAge > 0 && p.Age > f.MaxAge) {
			continue
		}
		if f.BrazilianClubs && p.ClubKey == "" {
			continue
		}
		out = append(out, p)
	}
	return out
}

// ClubSummary aggregates the players of one club.
type ClubSummary struct {
	Club    string
	Players int
	Avg     float64
	Best    *Player
}

// ClubSummaries groups players by club, largest squads first.
func ClubSummaries(ps []*Player) []ClubSummary {
	idx := map[string]*ClubSummary{}
	sum := map[string]int{}
	for _, p := range ps {
		c := p.Club
		if c == "" {
			c = "(no club)"
		}
		cs, ok := idx[c]
		if !ok {
			cs = &ClubSummary{Club: c, Best: p}
			idx[c] = cs
		}
		cs.Players++
		sum[c] += p.Overall
		if p.Overall > cs.Best.Overall {
			cs.Best = p
		}
	}
	out := make([]ClubSummary, 0, len(idx))
	for c, cs := range idx {
		cs.Avg = float64(sum[c]) / float64(cs.Players)
		out = append(out, *cs)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Players != out[j].Players {
			return out[i].Players > out[j].Players
		}
		if out[i].Avg != out[j].Avg {
			return out[i].Avg > out[j].Avg
		}
		return out[i].Club < out[j].Club
	})
	return out
}

// BrazilianFIFAClubs lists the FIFA clubs that were linked to match data.
func (s *Store) BrazilianFIFAClubs() []string {
	seen := map[string]bool{}
	var out []string
	for _, p := range s.Players {
		if p.ClubKey != "" && !seen[p.Club] {
			seen[p.Club] = true
			out = append(out, p.Club)
		}
	}
	sort.Strings(out)
	return out
}
