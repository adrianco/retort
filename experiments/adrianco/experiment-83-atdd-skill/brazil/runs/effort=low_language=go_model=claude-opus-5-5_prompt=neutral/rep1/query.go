package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

// NormalizeCompetition maps free text to a competition constant ("" = any).
func NormalizeCompetition(s string) string {
	c := StripAccents(strings.TrimSpace(s))
	switch {
	case c == "" || c == "all" || c == "any":
		return ""
	case strings.Contains(c, "liberta"):
		return CompLibertad
	case strings.Contains(c, "copa do brasil") || strings.Contains(c, "cup") || strings.Contains(c, "copa"):
		return CompCopaBrasil
	case strings.Contains(c, "serie b"):
		return CompSerieB
	case strings.Contains(c, "serie c"):
		return CompSerieC
	case strings.Contains(c, "brasileir") || strings.Contains(c, "serie a") || strings.Contains(c, "league") || strings.Contains(c, "campeonato"):
		return CompBrasileirao
	}
	return s
}

// Unique returns matches deduplicated across overlapping datasets
// (same home and away team within a day), preferring earlier-loaded sources.
func (db *DB) Unique() []*Match {
	if db.unique != nil {
		return db.unique
	}
	seen := map[string][]time.Time{}
	var out []*Match
	// priority by source order
	prio := map[string]int{SrcBrasileirao: 0, SrcCup: 1, SrcLib: 2, SrcHistorical: 3, SrcBRFootball: 4}
	ms := append([]*Match(nil), db.Matches...)
	sort.SliceStable(ms, func(i, j int) bool { return prio[ms[i].Source] < prio[ms[j].Source] })
	for _, m := range ms {
		// datasets disagree on kick-off dates by up to a day (time zones)
		k := m.HomeKey + "|" + m.AwayKey
		dup := false
		for _, d := range seen[k] {
			if diff := m.Date.Sub(d); diff < 36*time.Hour && diff > -36*time.Hour {
				dup = true
				break
			}
		}
		if dup {
			continue
		}
		seen[k] = append(seen[k], m.Date)
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.Before(out[j].Date) })
	db.unique = out
	return out
}

// ResolveTeam turns user input into the set of matching team keys.
func (db *DB) ResolveTeam(q string) map[string]bool {
	k := TeamKey(q)
	res := map[string]bool{}
	if k == "" {
		return res
	}
	if _, ok := db.TeamNames[k]; ok {
		res[k] = true
		return res
	}
	for key := range db.TeamNames {
		if containsWords(key, k) {
			res[key] = true
		}
	}
	return res
}

func containsWords(hay, needle string) bool {
	return strings.Contains(" "+hay+" ", " "+needle+" ")
}

func (db *DB) Name(key string) string {
	if n, ok := db.TeamNames[key]; ok {
		return n
	}
	return key
}

// MatchFilter selects matches.
type MatchFilter struct {
	Team, Opponent string
	Venue          string // home, away, or ""
	Competition    string
	Season         int
	From, To       time.Time
	Stage          string
}

func (db *DB) Filter(f MatchFilter) ([]*Match, error) {
	var tk, ok map[string]bool
	if f.Team != "" {
		tk = db.ResolveTeam(f.Team)
		if len(tk) == 0 {
			return nil, fmt.Errorf("unknown team %q", f.Team)
		}
	}
	if f.Opponent != "" {
		ok = db.ResolveTeam(f.Opponent)
		if len(ok) == 0 {
			return nil, fmt.Errorf("unknown team %q", f.Opponent)
		}
	}
	comp := NormalizeCompetition(f.Competition)
	stage := strings.ToLower(strings.TrimSpace(f.Stage))
	finals := map[int]string{}
	if stage == "final" || stage == "finals" {
		finals = db.cupFinalRounds()
	}
	var out []*Match
	for _, m := range db.Unique() {
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
			if stage == "final" || stage == "finals" {
				isFinal := (m.Competition == CompLibertad && m.Round == "final") ||
					(m.Competition == CompCopaBrasil && m.Source == SrcCup && finals[m.Season] == m.Round)
				if !isFinal {
					continue
				}
			} else if !strings.EqualFold(m.Round, stage) {
				continue
			}
		}
		if tk != nil {
			home, away := tk[m.HomeKey], tk[m.AwayKey]
			switch f.Venue {
			case "home":
				if !home {
					continue
				}
			case "away":
				if !away {
					continue
				}
			default:
				if !home && !away {
					continue
				}
			}
			if ok != nil {
				if !((home && ok[m.AwayKey]) || (away && ok[m.HomeKey])) {
					continue
				}
			}
		} else if ok != nil && !ok[m.HomeKey] && !ok[m.AwayKey] {
			continue
		}
		out = append(out, m)
	}
	return out, nil
}

func (db *DB) cupFinalRounds() map[int]string {
	max := map[int]int{}
	for _, m := range db.Matches {
		if m.Source == SrcCup {
			if r, err := strconv.Atoi(m.Round); err == nil && r > max[m.Season] {
				max[m.Season] = r
			}
		}
	}
	out := map[int]string{}
	for s, r := range max {
		if r < 7 { // season data incomplete; final not in dataset
			continue
		}
		out[s] = strconv.Itoa(r)
	}
	return out
}

func FormatMatch(m *Match) string {
	s := fmt.Sprintf("%s: %s %d-%d %s (%s", m.Date.Format("2006-01-02"), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
	if m.Round != "" {
		if _, err := strconv.Atoi(m.Round); err == nil {
			s += " Round " + m.Round
		} else {
			s += " " + m.Round
		}
	}
	s += ")"
	if m.Arena != "" {
		s += " @ " + m.Arena
	}
	if m.HomeShots >= 0 && m.HomeCorners >= 0 {
		s += fmt.Sprintf(" [shots %d-%d, corners %d-%d]", m.HomeShots, m.AwayShots, m.HomeCorners, m.AwayCorners)
	}
	return s
}

// Record aggregates results.
type Record struct {
	Team            string
	Played, W, D, L int
	GF, GA          int
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

// TeamRecord computes a team's record over the filtered matches.
func (db *DB) TeamRecord(f MatchFilter) (Record, []*Match, error) {
	ms, err := db.Filter(f)
	if err != nil {
		return Record{}, nil, err
	}
	tk := db.ResolveTeam(f.Team)
	var r Record
	for _, m := range ms {
		if tk[m.HomeKey] && (f.Venue != "away") {
			r.add(m.HomeGoals, m.AwayGoals)
		} else {
			r.add(m.AwayGoals, m.HomeGoals)
		}
	}
	return r, ms, nil
}

// HeadToHead summary.
type H2H struct {
	A, B           string
	AWins, BWins   int
	Draws          int
	AGoals, BGoals int
	Matches        []*Match
}

func (db *DB) HeadToHead(a, b, comp string) (H2H, error) {
	ms, err := db.Filter(MatchFilter{Team: a, Opponent: b, Competition: comp})
	if err != nil {
		return H2H{}, err
	}
	ak := db.ResolveTeam(a)
	h := H2H{A: db.displayFor(a), B: db.displayFor(b), Matches: ms}
	for _, m := range ms {
		ag, bg := m.HomeGoals, m.AwayGoals
		if !ak[m.HomeKey] {
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
	return h, nil
}

func (db *DB) displayFor(q string) string {
	ks := db.ResolveTeam(q)
	if len(ks) == 1 {
		for k := range ks {
			return db.Name(k)
		}
	}
	return q
}

// LeagueMatches returns the matches of one league season from a single
// source dataset (the most complete one) to avoid double-counting.
func (db *DB) LeagueMatches(comp string, season int) []*Match {
	bySrc := map[string][]*Match{}
	for _, m := range db.Matches {
		if m.Competition == comp && m.Season == season {
			bySrc[m.Source] = append(bySrc[m.Source], m)
		}
	}
	best := ""
	for _, s := range []string{SrcBrasileirao, SrcHistorical, SrcBRFootball, SrcCup, SrcLib} {
		if len(bySrc[s]) > len(bySrc[best]) {
			best = s
		}
	}
	return bySrc[best]
}

// Standings computes a league table.
func (db *DB) Standings(comp string, season int) []Record {
	recs := map[string]*Record{}
	get := func(k string) *Record {
		if recs[k] == nil {
			recs[k] = &Record{Team: db.Name(k)}
		}
		return recs[k]
	}
	for _, m := range db.LeagueMatches(comp, season) {
		get(m.HomeKey).add(m.HomeGoals, m.AwayGoals)
		get(m.AwayKey).add(m.AwayGoals, m.HomeGoals)
	}
	var out []Record
	for _, r := range recs {
		out = append(out, *r)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
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
	return out
}

// Rivalries lists traditional derbies by team key.
var Rivalries = []struct{ A, B, Name string }{
	{"flamengo", "fluminense", "Fla-Flu"},
	{"flamengo", "vasco", "Clássico dos Milhões"},
	{"flamengo", "botafogo", "Clássico da Rivalidade"},
	{"fluminense", "vasco", "Clássico dos Gigantes"},
	{"botafogo", "fluminense", "Clássico Vovô"},
	{"botafogo", "vasco", "Clássico da Amizade"},
	{"corinthians", "palmeiras", "Derby Paulista"},
	{"corinthians", "sao paulo", "Majestoso"},
	{"corinthians", "santos", "Clássico Alvinegro"},
	{"palmeiras", "sao paulo", "Choque-Rei"},
	{"palmeiras", "santos", "Clássico da Saudade"},
	{"santos", "sao paulo", "San-São"},
	{"gremio", "internacional", "Grenal"},
	{"atletico mineiro", "cruzeiro", "Clássico Mineiro"},
	{"athletico paranaense", "coritiba", "Atletiba"},
	{"bahia", "vitoria", "Ba-Vi"},
	{"ceara", "fortaleza", "Clássico-Rei"},
	{"nautico", "sport", "Clássico dos Clássicos"},
	{"santa cruz", "sport", "Clássico das Multidões"},
	{"avai", "figueirense", "Clássico da Ilha"},
	{"goias", "vila nova", "Clássico Goiano"},
	{"paysandu", "remo", "Re-Pa"},
}

func DerbyName(a, b string) string {
	for _, r := range Rivalries {
		if (r.A == a && r.B == b) || (r.A == b && r.B == a) {
			return r.Name
		}
	}
	return ""
}

// CompStats summarizes a set of matches.
type CompStats struct {
	Matches                   int
	Goals                     int
	HomeWins, AwayWins, Draws int
}

func Summarize(ms []*Match) CompStats {
	var s CompStats
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

func pct(a, b int) float64 {
	if b == 0 {
		return 0
	}
	return 100 * float64(a) / float64(b)
}

// TeamRecords aggregates records for every team over the matches.
func (db *DB) TeamRecords(ms []*Match, venue string) []Record {
	recs := map[string]*Record{}
	get := func(k string) *Record {
		if recs[k] == nil {
			recs[k] = &Record{Team: db.Name(k)}
		}
		return recs[k]
	}
	for _, m := range ms {
		if venue != "away" {
			get(m.HomeKey).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			get(m.AwayKey).add(m.AwayGoals, m.HomeGoals)
		}
	}
	var out []Record
	for _, r := range recs {
		out = append(out, *r)
	}
	return out
}

// PlayerFilter selects players.
type PlayerFilter struct {
	Name, Nationality, Club, Position string
	MinOverall                        int
	BrazilianClubsOnly                bool
}

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"},
	"striker":    {"ST", "CF", "LS", "RS"},
	"winger":     {"LW", "RW", "LM", "RM"},
	"midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

func positionMatches(pos, q string) bool {
	q = strings.ToLower(strings.TrimSpace(q))
	q = strings.TrimSuffix(q, "s")
	if q == "goalie" || q == "keeper" {
		q = "goalkeeper"
	}
	if g, ok := positionGroups[q]; ok {
		for _, p := range g {
			if strings.EqualFold(pos, p) {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(pos, q)
}

func (db *DB) BrazilianClubSet() map[string]bool {
	if db.brClubs != nil {
		return db.brClubs
	}
	s := map[string]bool{}
	for _, m := range db.Matches {
		if m.Competition == CompBrasileirao || m.Competition == CompSerieB || m.Competition == CompSerieC {
			s[m.HomeKey], s[m.AwayKey] = true, true
		}
	}
	db.brClubs = s
	return s
}

func (db *DB) SearchPlayers(f PlayerFilter) []*Player {
	name := StripAccents(strings.TrimSpace(f.Name))
	nat := StripAccents(strings.TrimSpace(f.Nationality))
	if nat == "brasil" || nat == "brazilian" {
		nat = "brazil"
	}
	var clubKeys map[string]bool
	clubQ := StripAccents(strings.TrimSpace(f.Club))
	exactClub := false
	if f.Club != "" {
		ck := TeamKey(f.Club)
		clubKeys = map[string]bool{ck: true}
		for _, p := range db.Players {
			if p.ClubKey == ck {
				exactClub = true
				break
			}
		}
	}
	br := db.BrazilianClubSet()
	var out []*Player
	for _, p := range db.Players {
		if name != "" && !nameMatches(StripAccents(p.Name), name) {
			continue
		}
		if nat != "" && StripAccents(p.Nationality) != nat {
			continue
		}
		if clubKeys != nil && !clubKeys[p.ClubKey] && (exactClub || !strings.Contains(StripAccents(p.Club), clubQ)) {
			continue
		}
		if f.Position != "" && !positionMatches(p.Position, f.Position) {
			continue
		}
		if p.Overall < f.MinOverall {
			continue
		}
		if f.BrazilianClubsOnly && !br[p.ClubKey] {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	return out
}

func FormatPlayer(p *Player) string {
	club := p.Club
	if club == "" {
		club = "Free agent"
	}
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s", p.Name, p.Overall, p.Potential, p.Position, p.Age, p.Nationality, club)
}

// nameMatches reports whether every word of q appears in the player name.
func nameMatches(name, q string) bool {
	for _, w := range strings.Fields(q) {
		if !strings.Contains(name, w) {
			return false
		}
	}
	return true
}
