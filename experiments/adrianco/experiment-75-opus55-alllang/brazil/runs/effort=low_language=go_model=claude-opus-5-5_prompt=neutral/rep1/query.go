package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

// MatchFilter selects matches. Zero values mean "any".
type MatchFilter struct {
	Team        string // either side
	Opponent    string // other side (requires Team)
	Venue       string // "home", "away" or "" relative to Team
	Competition string
	Season      int
	From, To    time.Time
	Stage       string // round/stage, "final" handled specially for Copa do Brasil
}

// ResolveTeam maps user input to a set of known team keys.
// An exact key match wins; otherwise any key containing the query.
func (db *DB) ResolveTeam(q string) []string {
	k := NormalizeTeam(q)
	if k == "" {
		return nil
	}
	if _, ok := db.TeamNames[k]; ok {
		return []string{k}
	}
	var out []string
	for key := range db.TeamNames {
		if strings.Contains(key, k) {
			out = append(out, key)
		}
	}
	sort.Strings(out)
	return out
}

// NormalizeCompetition maps free text to a competition name ("" = any).
func NormalizeCompetition(s string) string {
	s = strings.ToLower(stripAccents(strings.TrimSpace(s)))
	switch {
	case s == "" || s == "all" || s == "any":
		return ""
	case strings.Contains(s, "liberta"):
		return CompLibertad
	case strings.Contains(s, "copa") || strings.Contains(s, "cup"):
		return CompCopaBrasil
	case strings.Contains(s, "serie b") || s == "b":
		return CompSerieB
	case strings.Contains(s, "serie c") || s == "c":
		return CompSerieC
	case strings.Contains(s, "brasileir") || strings.Contains(s, "serie a") || strings.Contains(s, "league") || s == "a":
		return CompBrasileirao
	}
	return s
}

func dedupKey(m *Match) string {
	if m.Competition == CompBrasileirao || m.Competition == CompSerieB || m.Competition == CompSerieC {
		return fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.HomeKey, m.AwayKey)
	}
	return fmt.Sprintf("%s|%s|%s|%s", m.Competition, m.Date.Format("2006-01-02"), m.HomeKey, m.AwayKey)
}

// cupFinalRounds returns the highest round number per Copa do Brasil season.
func (db *DB) cupFinalRounds() map[int]int {
	out := map[int]int{}
	for _, m := range db.Matches {
		if m.Competition == CompCopaBrasil && m.Source == "Brazilian_Cup_Matches.csv" {
			if r := atoi(m.Round); r > out[m.Season] {
				out[m.Season] = r
			}
		}
	}
	for y, r := range out {
		if r < 6 { // season incomplete in data; final not present
			delete(out, y)
		}
	}
	return out
}

// Find returns deduplicated matches matching f, sorted by date descending.
func (db *DB) Find(f MatchFilter) []*Match {
	var teams, opps map[string]bool
	toSet := func(ks []string) map[string]bool {
		s := map[string]bool{}
		for _, k := range ks {
			s[k] = true
		}
		return s
	}
	if f.Team != "" {
		if teams = toSet(db.ResolveTeam(f.Team)); len(teams) == 0 {
			return nil
		}
	}
	if f.Opponent != "" {
		if opps = toSet(db.ResolveTeam(f.Opponent)); len(opps) == 0 {
			return nil
		}
	}
	comp := NormalizeCompetition(f.Competition)
	stage := strings.ToLower(strings.TrimSpace(f.Stage))
	var finals map[int]int
	if stage == "final" {
		finals = db.cupFinalRounds()
	}
	seen := map[string]bool{}
	var out []*Match
	for _, m := range db.Matches {
		if comp != "" && m.Competition != comp {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.From.IsZero() && m.Date.Before(f.From) {
			continue
		}
		if !f.To.IsZero() && m.Date.After(f.To.Add(24*time.Hour-time.Second)) {
			continue
		}
		if stage != "" {
			if m.Competition == CompCopaBrasil && stage == "final" {
				if m.Source != "Brazilian_Cup_Matches.csv" || finals[m.Season] == 0 || atoi(m.Round) != finals[m.Season] {
					continue
				}
			} else if !strings.EqualFold(m.Round, stage) {
				continue
			}
		}
		if teams != nil {
			home, away := teams[m.HomeKey], teams[m.AwayKey]
			switch f.Venue {
			case "home":
				away = false
			case "away":
				home = false
			}
			if !home && !away {
				continue
			}
			if opps != nil && !((home && opps[m.AwayKey]) || (away && opps[m.HomeKey])) {
				continue
			}
		}
		k := dedupKey(m)
		if seen[k] {
			continue
		}
		seen[k] = true
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	return out
}

// FormatMatch renders one match line.
func (db *DB) FormatMatch(m *Match) string {
	s := fmt.Sprintf("%s: %s %d-%d %s (%s", m.Date.Format("2006-01-02"), db.Name(m.HomeKey), m.HomeGoals, m.AwayGoals, db.Name(m.AwayKey), m.Competition)
	if m.Season > 0 {
		s += fmt.Sprintf(" %d", m.Season)
	}
	if m.Round != "" {
		if _, err := strconv.Atoi(m.Round); err == nil {
			s += " Round " + m.Round
		} else {
			s += ", " + m.Round
		}
	}
	if m.Arena != "" {
		s += ", " + m.Arena
	}
	s += ")"
	if m.HomeShots >= 0 {
		s += fmt.Sprintf(" [shots %d-%d, corners %d-%d]", m.HomeShots, m.AwayShots, m.HomeCorners, m.AwayCorners)
	}
	return s
}

// Record aggregates results for a team.
type Record struct {
	Team                    string
	Played, W, D, L, GF, GA int
}

func (r Record) Points() int { return 3*r.W + r.D }
func (r Record) GD() int     { return r.GF - r.GA }
func (r Record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return 100 * float64(r.W) / float64(r.Played)
}

func (r *Record) add(gf, ga int) {
	r.Played++
	r.GF += gf
	r.GA += ga
	switch {
	case gf > ga:
		r.W++
	case gf < ga:
		r.L++
	default:
		r.D++
	}
}

// Records computes per-team records over matches, with venue "home"/"away"/"".
func Records(ms []*Match, venue string) map[string]*Record {
	out := map[string]*Record{}
	get := func(k string) *Record {
		if out[k] == nil {
			out[k] = &Record{Team: k}
		}
		return out[k]
	}
	for _, m := range ms {
		if venue != "away" {
			get(m.HomeKey).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			get(m.AwayKey).add(m.AwayGoals, m.HomeGoals)
		}
	}
	return out
}

// TeamRecord computes a single team's record under filter f.
func (db *DB) TeamRecord(f MatchFilter) (Record, []string) {
	keys := db.ResolveTeam(f.Team)
	set := map[string]bool{}
	for _, k := range keys {
		set[k] = true
	}
	var r Record
	for _, m := range db.Find(f) {
		if set[m.HomeKey] && f.Venue != "away" {
			r.add(m.HomeGoals, m.AwayGoals)
		} else if set[m.AwayKey] && f.Venue != "home" {
			r.add(m.AwayGoals, m.HomeGoals)
		}
	}
	return r, keys
}

// Standings computes a league table sorted by points, wins, GD, GF.
func (db *DB) Standings(season int, comp string) []*Record {
	if comp == "" {
		comp = CompBrasileirao
	}
	recs := Records(db.Find(MatchFilter{Season: season, Competition: comp}), "")
	out := make([]*Record, 0, len(recs))
	for _, r := range recs {
		out = append(out, r)
	}
	sortRecords(out)
	return out
}

func sortRecords(rs []*Record) {
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
		return a.Team < b.Team
	})
}

// Summary holds aggregate statistics over a set of matches.
type Summary struct {
	Matches                   int
	Goals                     int
	HomeWins, AwayWins, Draws int
}

func (s Summary) AvgGoals() float64   { return ratio(s.Goals, s.Matches) }
func (s Summary) HomeWinPct() float64 { return 100 * ratio(s.HomeWins, s.Matches) }
func (s Summary) AwayWinPct() float64 { return 100 * ratio(s.AwayWins, s.Matches) }
func (s Summary) DrawPct() float64    { return 100 * ratio(s.Draws, s.Matches) }

func ratio(a, b int) float64 {
	if b == 0 {
		return 0
	}
	return float64(a) / float64(b)
}

func Summarize(ms []*Match) Summary {
	var s Summary
	for _, m := range ms {
		s.Matches++
		s.Goals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			s.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			s.AwayWins++
		default:
			s.Draws++
		}
	}
	return s
}

// BiggestWins returns matches sorted by goal margin then total goals.
func BiggestWins(ms []*Match, n int) []*Match {
	cp := append([]*Match(nil), ms...)
	abs := func(x int) int {
		if x < 0 {
			return -x
		}
		return x
	}
	sort.SliceStable(cp, func(i, j int) bool {
		a, b := cp[i], cp[j]
		da, dbb := abs(a.HomeGoals-a.AwayGoals), abs(b.HomeGoals-b.AwayGoals)
		if da != dbb {
			return da > dbb
		}
		return a.HomeGoals+a.AwayGoals > b.HomeGoals+b.AwayGoals
	})
	if len(cp) > n {
		cp = cp[:n]
	}
	return cp
}

// Rivalries lists traditional Brazilian derbies (pairs of team keys).
var Rivalries = []struct{ Name, A, B string }{
	{"Fla-Flu", "flamengo", "fluminense"},
	{"Clássico dos Milhões", "flamengo", "vasco"},
	{"Clássico Vovô", "fluminense", "botafogo"},
	{"Clássico da Rivalidade", "vasco", "botafogo"},
	{"Clássico Rei", "flamengo", "botafogo"},
	{"Clássico dos Gigantes", "fluminense", "vasco"},
	{"Derby Paulista", "corinthians", "palmeiras"},
	{"Choque-Rei", "palmeiras", "sao paulo"},
	{"Majestoso", "corinthians", "sao paulo"},
	{"San-São", "santos", "sao paulo"},
	{"Clássico Alvinegro", "corinthians", "santos"},
	{"Clássico da Saudade", "palmeiras", "santos"},
	{"Grenal", "gremio", "internacional"},
	{"Clássico Mineiro", "atletico mineiro", "cruzeiro"},
	{"Atletiba", "athletico paranaense", "coritiba"},
	{"Ba-Vi", "bahia", "vitoria"},
	{"Clássico-Rei (CE)", "ceara", "fortaleza"},
	{"Clássico dos Clássicos", "sport", "nautico"},
}

// RivalryName returns the derby name for a match, if any.
func RivalryName(a, b string) string {
	for _, r := range Rivalries {
		if (r.A == a && r.B == b) || (r.A == b && r.B == a) {
			return r.Name
		}
	}
	return ""
}

// PlayerFilter selects FIFA players.
type PlayerFilter struct {
	Name, Nationality, Club, Position string
	MinOverall                        int
}

func fold(s string) string { return strings.ToLower(stripAccents(s)) }

// forwardPositions etc. allow position group searches.
var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
	"midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

func positionMatches(want, have string) bool {
	w := strings.TrimSuffix(fold(strings.TrimSpace(want)), "s")
	if g, ok := positionGroups[w]; ok {
		for _, p := range g {
			if p == have {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(strings.TrimSpace(want), have)
}

// clubMatches compares club names allowing team-name normalization.
func clubMatches(want, club string) bool {
	if club == "" {
		return false
	}
	if strings.Contains(fold(club), fold(want)) {
		return true
	}
	return NormalizeTeam(club) == NormalizeTeam(want)
}

// FindPlayers returns players sorted by overall rating descending.
func (db *DB) FindPlayers(f PlayerFilter) []*Player {
	var out []*Player
	name := fold(strings.TrimSpace(f.Name))
	for _, p := range db.Players {
		if name != "" && !strings.Contains(fold(p.Name), name) {
			continue
		}
		if f.Nationality != "" && !strings.EqualFold(stripAccents(p.Nationality), stripAccents(nationality(f.Nationality))) {
			continue
		}
		if f.Club != "" && !clubMatches(f.Club, p.Club) {
			continue
		}
		if f.Position != "" && !positionMatches(f.Position, p.Position) {
			continue
		}
		if p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	return out
}

func nationality(s string) string {
	switch fold(strings.TrimSpace(s)) {
	case "brazilian", "brasil", "brasileiro":
		return "Brazil"
	case "argentinian", "argentine":
		return "Argentina"
	}
	return strings.TrimSpace(s)
}

// BrazilianClubKeys are the team keys seen in Brazilian match data.
func (db *DB) isBrazilianClub(club string) bool {
	if club == "" {
		return false
	}
	_, ok := db.TeamNames[NormalizeTeam(club)]
	return ok
}

func (p *Player) String() string {
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s",
		p.Name, p.Overall, p.Potential, p.Position, p.Age, p.Nationality, orNone(p.Club))
}

func orNone(s string) string {
	if s == "" {
		return "(none)"
	}
	return s
}
