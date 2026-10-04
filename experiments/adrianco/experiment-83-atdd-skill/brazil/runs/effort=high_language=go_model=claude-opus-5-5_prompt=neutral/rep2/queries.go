// Query primitives over the knowledge graph: team resolution, match
// filtering, records, standings and player search. The MCP tool handlers in
// tools.go compose these and format the results as text.
package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Record is a win/draw/loss and goals tally.
type Record struct {
	Played, Won, Drawn, Lost int
	GF, GA                   int
	CleanSheets              int
}

// Add records one match result from the team's perspective.
func (r *Record) Add(gf, ga int) {
	r.Played++
	r.GF += gf
	r.GA += ga
	switch {
	case gf > ga:
		r.Won++
	case gf < ga:
		r.Lost++
	default:
		r.Drawn++
	}
	if ga == 0 {
		r.CleanSheets++
	}
}

// Points uses 3 points for a win and 1 for a draw.
func (r Record) Points() int { return 3*r.Won + r.Drawn }

// GD is the goal difference.
func (r Record) GD() int { return r.GF - r.GA }

// WinRate is the fraction of matches won (0-100).
func (r Record) WinRate() float64 { return pct(r.Won, r.Played) }

// PointsRate is the fraction of available points won (0-100).
func (r Record) PointsRate() float64 { return pct(r.Points(), 3*r.Played) }

func pct(n, d int) float64 {
	if d == 0 {
		return 0
	}
	return 100 * float64(n) / float64(d)
}

func ratio(n, d int) float64 {
	if d == 0 {
		return 0
	}
	return float64(n) / float64(d)
}

// Involves reports whether t played in m.
func (m *Match) Involves(t *Team) bool { return m.Home == t || m.Away == t }

// GoalsFor returns goals scored and conceded by t in m.
func (m *Match) GoalsFor(t *Team) (gf, ga int) {
	if m.Home == t {
		return m.HomeGoals, m.AwayGoals
	}
	return m.AwayGoals, m.HomeGoals
}

// Opponent returns the other team in m.
func (m *Match) Opponent(t *Team) *Team {
	if m.Home == t {
		return m.Away
	}
	return m.Home
}

// Winner returns the winning team or nil for a draw.
func (m *Match) Winner() *Team {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return m.Home
	case m.AwayGoals > m.HomeGoals:
		return m.Away
	}
	return nil
}

// Margin is the absolute goal difference.
func (m *Match) Margin() int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

// TotalGoals is the number of goals in the match.
func (m *Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// ResolveTeam maps free text ("Flamengo", "Palmeiras-SP", "São Paulo FC",
// "Sport Club Corinthians Paulista") to a team node.
func (s *Store) ResolveTeam(q string) (*Team, error) {
	q = strings.TrimSpace(q)
	if q == "" {
		return nil, fmt.Errorf("team name is empty")
	}
	p := parseTeamName(q)
	// Candidates: the key with the usual default state and, for names given
	// without a region, the bare base (foreign clubs such as "River Plate").
	// The candidate with more matches wins.
	var found *Team
	for _, key := range []string{s.reg.key(p, false), p.Base} {
		if t, ok := s.Teams[key]; ok && (found == nil || len(t.Matches) > len(found.Matches)) {
			found = t
		}
		if p.Region != "" {
			break
		}
	}
	if found != nil {
		return found, nil
	}
	// Fuzzy fallback: every query token must appear in the key, the display
	// name or one of the raw spellings. Prefer the club with most matches.
	tokens := strings.Fields(strings.NewReplacer("-", " ", ".", " ").Replace(foldText(q)))
	var best *Team
	for _, t := range s.Teams {
		hay := t.Key + " " + foldText(t.Name)
		for v := range t.Variants {
			hay += " " + foldText(v)
		}
		ok := true
		for _, tok := range tokens {
			if !strings.Contains(hay, tok) {
				ok = false
				break
			}
		}
		if ok && (best == nil || len(t.Matches) > len(best.Matches) ||
			(len(t.Matches) == len(best.Matches) && t.Key < best.Key)) {
			best = t
		}
	}
	if best != nil {
		return best, nil
	}
	return nil, fmt.Errorf("team %q not found in the match data (try list_teams to search names)", q)
}

// MatchFilter selects matches. Zero values mean "no constraint".
type MatchFilter struct {
	Team, Opponent       *Team
	Venue                string // "home" or "away" relative to Team
	Competition          string
	Season               int
	SeasonFrom, SeasonTo int
	DateFrom, DateTo     time.Time
	Stage                string // canonical stage, see normalizeStage
}

// FindMatches returns matching fixtures in chronological order.
func (s *Store) FindMatches(f MatchFilter) []*Match {
	pool := s.Matches
	if f.Team != nil {
		pool = f.Team.Matches
	} else if f.Opponent != nil {
		pool = f.Opponent.Matches
	}
	var out []*Match
	for _, m := range pool {
		if f.Team != nil {
			if !m.Involves(f.Team) {
				continue
			}
			if f.Venue == "home" && m.Home != f.Team || f.Venue == "away" && m.Away != f.Team {
				continue
			}
		}
		if f.Opponent != nil && !m.Involves(f.Opponent) {
			continue
		}
		if f.Team != nil && f.Opponent != nil && f.Team == f.Opponent {
			continue
		}
		if f.Competition != "" && m.Competition != f.Competition {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.SeasonFrom != 0 && m.Season < f.SeasonFrom || f.SeasonTo != 0 && m.Season > f.SeasonTo {
			continue
		}
		day := truncDay(m.Date)
		if !f.DateFrom.IsZero() && day.Before(f.DateFrom) || !f.DateTo.IsZero() && day.After(f.DateTo) {
			continue
		}
		if f.Stage != "" && m.Stage != f.Stage {
			continue
		}
		out = append(out, m)
	}
	return out
}

func truncDay(t time.Time) time.Time {
	return time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, time.UTC)
}

// normalizeStage maps user wording to the stage labels used in the data.
func normalizeStage(s string) string {
	f := strings.NewReplacer("-", "", " ", "", "_", "").Replace(foldText(strings.TrimSpace(s)))
	switch {
	case f == "":
		return ""
	case strings.Contains(f, "semi"):
		return "semifinals"
	case strings.Contains(f, "quarter") || strings.Contains(f, "quartas"):
		return "quarterfinals"
	case strings.Contains(f, "16") || strings.Contains(f, "oitavas"):
		return "round of 16"
	case strings.Contains(f, "group") || strings.Contains(f, "grupo"):
		return "group stage"
	case strings.Contains(f, "final"):
		return "final"
	case strings.HasPrefix(f, "round"):
		return "round " + strings.TrimPrefix(f, "round")
	}
	return strings.TrimSpace(foldText(s))
}

// TeamRecord tallies a team's results over the given matches.
func TeamRecord(t *Team, ms []*Match) Record {
	var r Record
	for _, m := range ms {
		if m.Involves(t) {
			r.Add(m.GoalsFor(t))
		}
	}
	return r
}

// TeamTable aggregates records for every team appearing in ms. venue
// restricts to home or away matches of each team.
func TeamTable(ms []*Match, venue string) map[*Team]*Record {
	out := map[*Team]*Record{}
	add := func(t *Team, gf, ga int) {
		r := out[t]
		if r == nil {
			r = &Record{}
			out[t] = r
		}
		r.Add(gf, ga)
	}
	for _, m := range ms {
		if venue != "away" {
			add(m.Home, m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			add(m.Away, m.AwayGoals, m.HomeGoals)
		}
	}
	return out
}

// StandingRow is one line of a league table.
type StandingRow struct {
	Team *Team
	Record
}

// Standings computes a league table for a competition season from the
// de-duplicated fixtures of all files (one file may lack a result that
// another has). It also reports which files contributed.
func (s *Store) Standings(comp string, season int) (rows []StandingRow, sources string, n int) {
	ms := s.FindMatches(MatchFilter{Competition: comp, Season: season})
	used := map[string]bool{}
	for _, m := range ms {
		for _, src := range m.Sources {
			used[src] = true
		}
	}
	var names []string
	for _, src := range matchSources {
		if used[src] {
			names = append(names, src)
		}
	}
	for t, r := range TeamTable(ms, "") {
		rows = append(rows, StandingRow{Team: t, Record: *r})
	}
	sortStandings(rows)
	return rows, strings.Join(names, " + "), len(ms)
}

// sortStandings applies the Brasileirão tie-breakers: points, wins, goal
// difference, goals scored.
func sortStandings(rows []StandingRow) {
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.Won != b.Won {
			return a.Won > b.Won
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

// relegationSpots returns how many clubs went down from Série A in a season.
func relegationSpots(season int) int {
	if season == 2003 {
		return 2
	}
	return 4
}

// Seasons lists the seasons available for a competition (all if comp == "").
func (s *Store) Seasons(comp string) []int {
	set := map[int]bool{}
	for _, m := range s.Matches {
		if comp == "" || m.Competition == comp {
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

// derbies lists traditional Brazilian rivalries by canonical team key.
var derbies = []struct{ A, B, Name string }{
	{"flamengo-rj", "fluminense-rj", "Fla-Flu"},
	{"flamengo-rj", "vasco-rj", "Clássico dos Milhões"},
	{"flamengo-rj", "botafogo-rj", "Clássico da Rivalidade"},
	{"fluminense-rj", "vasco-rj", "Clássico dos Gigantes"},
	{"botafogo-rj", "fluminense-rj", "Clássico Vovô"},
	{"botafogo-rj", "vasco-rj", "Clássico da Amizade"},
	{"corinthians-sp", "palmeiras-sp", "Derby Paulista"},
	{"palmeiras-sp", "sao paulo-sp", "Choque-Rei"},
	{"corinthians-sp", "sao paulo-sp", "Majestoso"},
	{"santos-sp", "sao paulo-sp", "San-São"},
	{"corinthians-sp", "santos-sp", "Clássico Alvinegro"},
	{"palmeiras-sp", "santos-sp", "Clássico da Saudade"},
	{"gremio-rs", "internacional-rs", "Grenal"},
	{"atletico-mg", "cruzeiro-mg", "Clássico Mineiro"},
	{"atletico-pr", "coritiba-pr", "Atletiba"},
	{"bahia-ba", "vitoria-ba", "Ba-Vi"},
	{"ceara-ce", "fortaleza-ce", "Clássico-Rei"},
	{"nautico-pe", "sport-pe", "Clássico dos Clássicos"},
	{"santa cruz-pe", "sport-pe", "Clássico das Multidões"},
	{"goias-go", "vila nova-go", "Clássico Goiano"},
	{"avai-sc", "figueirense-sc", "Clássico da Ilha"},
	{"paysandu-pa", "remo-pa", "Re-Pa"},
	{"abc-rn", "america-rn", "Clássico-Rei Potiguar"},
	{"csa-al", "crb-al", "Clássico das Multidões Alagoano"},
}

// DerbyName returns the rivalry name for two teams, or "".
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

// Rivals lists derby opponents of t.
func (s *Store) Rivals(t *Team) []string {
	var out []string
	for _, d := range derbies {
		var other string
		switch t.Key {
		case d.A:
			other = d.B
		case d.B:
			other = d.A
		default:
			continue
		}
		if o, ok := s.Teams[other]; ok {
			out = append(out, fmt.Sprintf("%s (%s)", o.Name, d.Name))
		}
	}
	return out
}

// ---- players ----

// PlayerFilter selects FIFA players.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	ClubTeam    *Team
	Position    string
	MinOverall  int
	MaxAge      int
}

var demonyms = map[string]string{
	"brazilian": "brazil", "brasileiro": "brazil", "brasil": "brazil",
	"argentine": "argentina", "argentinian": "argentina", "uruguayan": "uruguay",
	"colombian": "colombia", "chilean": "chile", "paraguayan": "paraguay",
	"peruvian": "peru", "ecuadorian": "ecuador", "venezuelan": "venezuela",
	"bolivian": "bolivia", "mexican": "mexico", "portuguese": "portugal",
	"spanish": "spain", "french": "france", "german": "germany", "english": "england",
	"italian": "italy", "dutch": "netherlands", "belgian": "belgium", "american": "united states",
}

func normalizeNationality(s string) string {
	f := strings.TrimSpace(foldText(s))
	if v, ok := demonyms[f]; ok {
		return v
	}
	return f
}

// positionGroups expands group words to FIFA position codes.
var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LS", "RS", "LW", "RW", "LF", "RF"},
	"striker":    {"ST", "CF", "LS", "RS"},
	"winger":     {"LW", "RW", "LM", "RM"},
	"attacker":   {"ST", "CF", "LS", "RS", "LW", "RW", "LF", "RF"},
	"midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
	"keeper":     {"GK"},
}

// positionSet returns the accepted position codes for user input such as
// "forwards", "GK" or "ST,CF".
func positionSet(s string) map[string]bool {
	out := map[string]bool{}
	for _, part := range strings.FieldsFunc(s, func(r rune) bool { return r == ',' || r == '/' || r == ' ' }) {
		w := strings.TrimSuffix(strings.ToLower(part), "s")
		if codes, ok := positionGroups[w]; ok {
			for _, c := range codes {
				out[c] = true
			}
			continue
		}
		out[strings.ToUpper(part)] = true
	}
	return out
}

// FindPlayers returns players matching f, sorted by overall rating.
func (s *Store) FindPlayers(f PlayerFilter) []*Player {
	nameTokens := strings.Fields(foldText(f.Name))
	nat := normalizeNationality(f.Nationality)
	club := foldText(strings.TrimSpace(f.Club))
	positions := positionSet(f.Position)
	var out []*Player
	for _, p := range s.Players {
		if len(nameTokens) > 0 {
			ok := true
			for _, tok := range nameTokens {
				if !strings.Contains(p.nameFold, tok) {
					ok = false
					break
				}
			}
			if !ok {
				continue
			}
		}
		if nat != "" && foldText(p.Nationality) != nat {
			continue
		}
		if f.ClubTeam != nil || club != "" {
			if !(f.ClubTeam != nil && p.Team == f.ClubTeam) && !(club != "" && strings.Contains(foldText(p.Club), club)) {
				continue
			}
		}
		if len(positions) > 0 && !positions[p.Position] {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxAge > 0 && p.Age > f.MaxAge {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Potential > out[j].Potential
	})
	return out
}
