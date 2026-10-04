package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Args are tool arguments as supplied by the MCP client.
type Args map[string]any

func (a Args) str(k string) string {
	switch v := a[k].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	case nil:
		return ""
	default:
		return fmt.Sprint(v)
	}
}

func (a Args) num(k string, def int) int {
	if n, err := strconv.Atoi(a.str(k)); err == nil {
		return n
	}
	return def
}

func compKey(s string) string {
	k := strings.ToLower(stripAccents(strings.TrimSpace(s)))
	switch {
	case k == "", k == "all":
		return ""
	case strings.Contains(k, "brasileir"), k == "serie a", strings.Contains(k, "campeonato"):
		return "brasileirao"
	case strings.Contains(k, "copa do brasil"), strings.Contains(k, "cup"):
		return "copa do brasil"
	case strings.Contains(k, "libertadores"):
		return "libertadores"
	}
	return k
}

func compMatches(comp, q string) bool {
	qk := compKey(q)
	return qk == "" || compKey(comp) == qk
}

type filter struct {
	team, opponent, comp, stage, venue string
	season                             int
	from, to                           time.Time
}

func filterFrom(a Args) filter {
	f := filter{team: a.str("team"), opponent: a.str("opponent"), comp: a.str("competition"), stage: a.str("stage"),
		venue: strings.ToLower(a.str("venue")), season: a.num("season", 0), from: parseDate(a.str("from")), to: parseDate(a.str("to"))}
	if !f.to.IsZero() {
		f.to = f.to.Add(24*time.Hour - time.Second)
	}
	return f
}

func (s *Store) finalRounds() map[int]string {
	max := map[int]int{}
	for _, m := range s.Matches {
		if m.Competition == "Copa do Brasil" {
			if r, err := strconv.Atoi(m.Round); err == nil && r > max[m.Season] {
				max[m.Season] = r
			}
		}
	}
	out := map[int]string{}
	for k, v := range max {
		out[k] = strconv.Itoa(v)
	}
	return out
}

func (s *Store) find(f filter) []Match {
	var finals map[int]string
	var out []Match
	for _, m := range s.Matches {
		if f.season != 0 && m.Season != f.season || !compMatches(m.Competition, f.comp) {
			continue
		}
		if !f.from.IsZero() && m.Date.Before(f.from) || !f.to.IsZero() && m.Date.After(f.to) {
			continue
		}
		if f.stage != "" {
			st := strings.ToLower(f.stage)
			if m.Competition == "Copa do Brasil" && st == "final" {
				if finals == nil {
					finals = s.finalRounds()
				}
				if fr := finals[m.Season]; fr == "" || m.Round != fr {
					continue
				}
			} else if !strings.Contains(strings.ToLower(m.Stage+" "+m.Round), st) {
				continue
			}
		}
		home, away := TeamMatches(m.Home, f.team), TeamMatches(m.Away, f.team)
		if f.opponent != "" {
			home = home && TeamMatches(m.Away, f.opponent)
			away = away && TeamMatches(m.Home, f.opponent)
		}
		switch f.venue {
		case "home":
			away = false
		case "away":
			home = false
		}
		if home || away {
			out = append(out, m)
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	return out
}

func formatMatch(m Match) string {
	ctx := m.Competition
	switch {
	case m.Stage != "":
		ctx += " " + m.Stage
	case m.Round != "" && m.Competition == "Copa do Brasil":
		ctx += " Round " + m.Round
	case m.Round != "":
		ctx += " Round " + m.Round
	}
	if m.Arena != "" {
		ctx += ", " + m.Arena
	}
	return fmt.Sprintf("- %s: %s %d-%d %s (%s)", m.Date.Format("2006-01-02"), DisplayName(m.Home), m.HomeGoals, m.AwayGoals, DisplayName(m.Away), ctx)
}

func listMatches(b *strings.Builder, ms []Match, limit int) {
	for i, m := range ms {
		if i >= limit {
			fmt.Fprintf(b, "- ... (%d more matches in dataset)\n", len(ms)-limit)
			break
		}
		b.WriteString(formatMatch(m) + "\n")
	}
}

// SearchMatches finds matches by team, opponent, competition, season, stage, venue and date range.
func (s *Store) SearchMatches(a Args) string {
	f := filterFrom(a)
	ms := s.find(f)
	var b strings.Builder
	if len(ms) == 0 {
		return "No matches found for those criteria."
	}
	fmt.Fprintf(&b, "Found %d matches:\n", len(ms))
	listMatches(&b, ms, a.num("limit", 20))
	return b.String()
}

type record struct {
	team                    string
	played, w, d, l, gf, ga int
}

func (r *record) add(gf, ga int) {
	r.played++
	r.gf += gf
	r.ga += ga
	switch {
	case gf > ga:
		r.w++
	case gf == ga:
		r.d++
	default:
		r.l++
	}
}
func (r record) pts() int { return 3*r.w + r.d }
func (r record) winRate() float64 {
	if r.played == 0 {
		return 0
	}
	return 100 * float64(r.w) / float64(r.played)
}

// HeadToHead lists matches between two teams and the overall record.
func (s *Store) HeadToHead(a Args) string {
	ta, tb := a.str("team_a"), a.str("team_b")
	if ta == "" || tb == "" {
		return "Please provide both team_a and team_b."
	}
	ms := s.find(filter{team: ta, opponent: tb, comp: a.str("competition"), season: a.num("season", 0)})
	if len(ms) == 0 {
		return fmt.Sprintf("No matches found between %s and %s.", ta, tb)
	}
	var wa, wb, d, ga, gb int
	for _, m := range ms {
		ah := TeamMatches(m.Home, ta)
		x, y := m.HomeGoals, m.AwayGoals
		if !ah {
			x, y = y, x
		}
		ga += x
		gb += y
		switch {
		case x > y:
			wa++
		case x < y:
			wb++
		default:
			d++
		}
	}
	na, nb := DisplayName(teamNameIn(ms[0], ta)), DisplayName(teamNameIn(ms[0], tb))
	var b strings.Builder
	limit := a.num("limit", 10)
	if limit == 1 {
		fmt.Fprintf(&b, "Last match between %s and %s:\n", na, nb)
	} else {
		fmt.Fprintf(&b, "%s vs %s%s:\n", na, nb, derbyLabel(ms[0]))
	}
	listMatches(&b, ms, limit)
	fmt.Fprintf(&b, "\nHead-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws\nGoals: %s %d, %s %d\n",
		len(ms), na, wa, nb, wb, d, na, ga, nb, gb)
	return b.String()
}

func teamNameIn(m Match, q string) string {
	if TeamMatches(m.Home, q) {
		return m.Home
	}
	return m.Away
}

func (s *Store) recordFor(team string, ms []Match) record {
	r := record{team: team}
	for _, m := range ms {
		if TeamMatches(m.Home, team) {
			r.add(m.HomeGoals, m.AwayGoals)
		} else {
			r.add(m.AwayGoals, m.HomeGoals)
		}
	}
	return r
}

func writeRecord(b *strings.Builder, r record) {
	fmt.Fprintf(b, "- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Points: %d\n- Win rate: %.1f%%\n",
		r.played, r.w, r.d, r.l, r.gf, r.ga, r.pts(), r.winRate())
}

// TeamRecord computes win/draw/loss and goals for a team.
func (s *Store) TeamRecord(a Args) string {
	f := filterFrom(a)
	if f.team == "" {
		return "Please provide a team."
	}
	ms := s.find(f)
	if len(ms) == 0 {
		return fmt.Sprintf("No matches found for %s.", f.team)
	}
	var b strings.Builder
	desc := DisplayName(teamNameIn(ms[0], f.team))
	if f.venue == "home" || f.venue == "away" {
		desc += " " + f.venue
	}
	desc += " record"
	var ctx []string
	if f.season != 0 {
		ctx = append(ctx, strconv.Itoa(f.season))
	}
	if f.comp != "" {
		ctx = append(ctx, ms[0].Competition)
	}
	if len(ctx) > 0 {
		desc += " (" + strings.Join(ctx, " ") + ")"
	}
	b.WriteString(desc + ":\n")
	writeRecord(&b, s.recordFor(f.team, ms))
	return b.String()
}

func (s *Store) table(ms []Match) []*record {
	recs := map[string]*record{}
	get := func(name string) *record {
		k := TeamKey(name)
		if recs[k] == nil {
			recs[k] = &record{team: DisplayName(name)}
		}
		return recs[k]
	}
	for _, m := range ms {
		get(m.Home).add(m.HomeGoals, m.AwayGoals)
		get(m.Away).add(m.AwayGoals, m.HomeGoals)
	}
	out := make([]*record, 0, len(recs))
	for _, r := range recs {
		out = append(out, r)
	}
	sort.Slice(out, func(i, j int) bool {
		x, y := out[i], out[j]
		if x.pts() != y.pts() {
			return x.pts() > y.pts()
		}
		if x.w != y.w {
			return x.w > y.w
		}
		if x.gf-x.ga != y.gf-y.ga {
			return x.gf-x.ga > y.gf-y.ga
		}
		return x.gf > y.gf
	})
	return out
}

// Standings calculates a league table for a season from match results.
func (s *Store) Standings(a Args) string {
	season := a.num("season", 0)
	if season == 0 {
		return "Please provide a season."
	}
	comp := a.str("competition")
	if comp == "" {
		comp = "Brasileirão"
	}
	ms := s.find(filter{season: season, comp: comp})
	if len(ms) == 0 {
		return fmt.Sprintf("No %s matches found for %d.", comp, season)
	}
	tbl := s.table(ms)
	var b strings.Builder
	if a.str("sort") == "goals" {
		sort.SliceStable(tbl, func(i, j int) bool { return tbl[i].gf > tbl[j].gf })
		fmt.Fprintf(&b, "%d %s teams by goals scored:\n", season, ms[0].Competition)
		for i, r := range tbl {
			fmt.Fprintf(&b, "%d. %s - %d GF, %d GA (%d matches)\n", i+1, r.team, r.gf, r.ga, r.played)
		}
		return b.String()
	}
	fmt.Fprintf(&b, "%d %s Standings (calculated from %d matches):\n", season, ms[0].Competition, len(ms))
	league := compKey(comp) == "brasileirao" || strings.HasPrefix(compKey(comp), "serie")
	for i, r := range tbl {
		note := ""
		if league && i == 0 {
			note = " - Champion"
		}
		if league && len(tbl) >= 16 && i >= len(tbl)-4 {
			note = " - Relegated"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d)%s\n", i+1, r.team, r.pts(), r.w, r.d, r.l, r.gf, r.ga, note)
	}
	return b.String()
}

func (s *Store) matchingPlayers(a Args) []Player {
	name, nat, club, pos := strings.ToLower(stripAccents(a.str("name"))), strings.ToLower(a.str("nationality")), strings.ToLower(stripAccents(a.str("club"))), strings.ToUpper(a.str("position"))
	if nat == "brazilian" {
		nat = "brazil"
	}
	min := a.num("min_overall", 0)
	var out []Player
	for _, p := range s.Players {
		if name != "" && !strings.Contains(strings.ToLower(stripAccents(p.Name)), name) {
			continue
		}
		if nat != "" && strings.ToLower(p.Nationality) != nat {
			continue
		}
		if club != "" && !strings.Contains(strings.ToLower(stripAccents(p.Club)), club) {
			continue
		}
		if pos != "" && !positionMatches(p.Position, pos) {
			continue
		}
		if p.Overall < min {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	return out
}

func positionMatches(p, q string) bool {
	groups := map[string][]string{
		"FORWARD": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}, "FORWARDS": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
		"MIDFIELDER": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
		"DEFENDER":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"}, "GOALKEEPER": {"GK"},
	}
	if g, ok := groups[q]; ok {
		for _, x := range g {
			if p == x {
				return true
			}
		}
		return false
	}
	return p == q
}

// SearchPlayers searches FIFA player data.
func (s *Store) SearchPlayers(a Args) string {
	ps := s.matchingPlayers(a)
	if len(ps) == 0 {
		return "No players found matching those criteria in the FIFA dataset (note: it mostly covers European leagues)."
	}
	limit := a.num("limit", 20)
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d players (sorted by overall rating):\n", len(ps))
	for i, p := range ps {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more)\n", len(ps)-limit)
			break
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Potential: %d, Position: %s, Club: %s, Nationality: %s, Age: %d, Height: %s, Weight: %s\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, orNone(p.Club), p.Nationality, p.Age, p.Height, p.Weight)
	}
	return b.String()
}

func orNone(s string) string {
	if s == "" {
		return "(no club)"
	}
	return s
}

// PlayersByClub groups matching players by club.
func (s *Store) PlayersByClub(a Args) string {
	ps := s.matchingPlayers(a)
	type agg struct {
		club       string
		n, ratings int
	}
	m := map[string]*agg{}
	for _, p := range ps {
		if p.Club == "" {
			continue
		}
		if m[p.Club] == nil {
			m[p.Club] = &agg{club: p.Club}
		}
		m[p.Club].n++
		m[p.Club].ratings += p.Overall
	}
	list := make([]*agg, 0, len(m))
	for _, v := range m {
		list = append(list, v)
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].n != list[j].n {
			return list[i].n > list[j].n
		}
		return list[i].club < list[j].club
	})
	var b strings.Builder
	fmt.Fprintf(&b, "Players by club (%d players, %d clubs):\n", len(ps), len(list))
	for i, c := range list {
		if i >= a.num("limit", 20) {
			break
		}
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %d)\n", c.club, c.n, c.ratings/c.n)
	}
	return b.String()
}

// Statistics reports aggregate goal and result statistics.
func (s *Store) Statistics(a Args) string {
	f := filterFrom(a)
	ms := s.find(f)
	if len(ms) == 0 {
		return "No matches found for those criteria."
	}
	var goals, hw, aw, d int
	for _, m := range ms {
		goals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			hw++
		case m.HomeGoals < m.AwayGoals:
			aw++
		default:
			d++
		}
	}
	n := float64(len(ms))
	label := "All competitions"
	if f.comp != "" {
		label = ms[0].Competition
	}
	if f.season != 0 {
		label += fmt.Sprintf(" %d", f.season)
	}
	return fmt.Sprintf("%s statistics (%d matches):\n- Total goals: %d\n- Average goals per match: %.2f\n- Home win rate: %.1f%%\n- Away win rate: %.1f%%\n- Draw rate: %.1f%%\n",
		label, len(ms), goals, float64(goals)/n, 100*float64(hw)/n, 100*float64(aw)/n, 100*float64(d)/n)
}

// BiggestWins lists matches with the largest goal margins.
func (s *Store) BiggestWins(a Args) string {
	ms := s.find(filterFrom(a))
	sort.SliceStable(ms, func(i, j int) bool {
		di, dj := abs(ms[i].HomeGoals-ms[i].AwayGoals), abs(ms[j].HomeGoals-ms[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		return ms[i].HomeGoals+ms[i].AwayGoals > ms[j].HomeGoals+ms[j].AwayGoals
	})
	var b strings.Builder
	b.WriteString("Biggest victories in dataset:\n")
	for i, m := range ms {
		if i >= a.num("limit", 10) {
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, strings.TrimPrefix(formatMatch(m), "- "))
	}
	return b.String()
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// RankTeams ranks teams by win rate, optionally only home or away matches.
func (s *Store) RankTeams(a Args) string {
	f := filterFrom(a)
	venue := f.venue
	f.venue = ""
	f.team = ""
	ms := s.find(f)
	recs := map[string]*record{}
	get := func(name string) *record {
		k := TeamKey(name)
		if recs[k] == nil {
			recs[k] = &record{team: DisplayName(name)}
		}
		return recs[k]
	}
	for _, m := range ms {
		if venue != "away" {
			get(m.Home).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			get(m.Away).add(m.AwayGoals, m.HomeGoals)
		}
	}
	min := a.num("min_matches", 20)
	if f.season != 0 {
		min = a.num("min_matches", 5)
	}
	var list []*record
	for _, r := range recs {
		if r.played >= min {
			list = append(list, r)
		}
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].winRate() != list[j].winRate() {
			return list[i].winRate() > list[j].winRate()
		}
		return list[i].team < list[j].team
	})
	var b strings.Builder
	what := "overall"
	if venue == "home" || venue == "away" {
		what = venue
	}
	fmt.Fprintf(&b, "Teams ranked by %s win rate (min %d matches):\n", what, min)
	for i, r := range list {
		if i >= a.num("limit", 10) {
			break
		}
		fmt.Fprintf(&b, "%d. %s - %.1f%% win rate (%dW %dD %dL in %d, GF %d GA %d)\n", i+1, r.team, r.winRate(), r.w, r.d, r.l, r.played, r.gf, r.ga)
	}
	return b.String()
}

// TeamProfile combines match data across competitions with FIFA player data.
func (s *Store) TeamProfile(a Args) string {
	team := a.str("team")
	if team == "" {
		return "Please provide a team."
	}
	ms := s.find(filter{team: team})
	var b strings.Builder
	if len(ms) == 0 {
		fmt.Fprintf(&b, "No matches found for %s.\n", team)
	} else {
		name := DisplayName(teamNameIn(ms[0], team))
		fmt.Fprintf(&b, "%s profile:\n\nRecord across all competitions:\n", name)
		writeRecord(&b, s.recordFor(team, ms))
		by := map[string][]Match{}
		for _, m := range ms {
			by[m.Competition] = append(by[m.Competition], m)
		}
		comps := make([]string, 0, len(by))
		for c := range by {
			comps = append(comps, c)
		}
		sort.Strings(comps)
		b.WriteString("\nCompetitions played:\n")
		for _, c := range comps {
			r := s.recordFor(team, by[c])
			seasons := map[int]bool{}
			for _, m := range by[c] {
				seasons[m.Season] = true
			}
			fmt.Fprintf(&b, "- %s: %d matches over %d seasons (%dW %dD %dL)\n", c, r.played, len(seasons), r.w, r.d, r.l)
		}
		b.WriteString("\nRecent matches:\n")
		listMatches(&b, ms, 5)
	}
	ps := s.matchingPlayers(Args{"club": team})
	fmt.Fprintf(&b, "\nPlayers in FIFA dataset at clubs matching %q: %d\n", team, len(ps))
	for i, p := range ps {
		if i >= 10 {
			break
		}
		fmt.Fprintf(&b, "- %s (%s, %d) - %s\n", p.Name, p.Position, p.Overall, p.Club)
	}
	return b.String()
}

var derbyList = []struct{ name, a, b string }{
	{"Fla-Flu", "Flamengo", "Fluminense"}, {"Clássico dos Milhões", "Flamengo", "Vasco"},
	{"Clássico Vovô", "Botafogo", "Fluminense"}, {"Clássico da Rivalidade", "Flamengo", "Botafogo"},
	{"Clássico dos Gigantes", "Fluminense", "Vasco"}, {"Clássico da Amizade", "Botafogo", "Vasco"},
	{"Derby Paulista", "Corinthians", "Palmeiras"}, {"Choque-Rei", "Palmeiras", "Sao Paulo"},
	{"Majestoso", "Corinthians", "Sao Paulo"}, {"San-São", "Santos", "Sao Paulo"},
	{"Clássico Alvinegro", "Corinthians", "Santos"}, {"Clássico da Saudade", "Palmeiras", "Santos"},
	{"Grenal", "Gremio", "Internacional"}, {"Clássico Mineiro", "Atletico MG", "Cruzeiro"},
	{"Ba-Vi", "Bahia", "Vitoria"}, {"Atletiba", "Athletico", "Coritiba"},
}

func derbyLabel(m Match) string {
	for _, d := range derbyList {
		if (TeamKey(m.Home) == TeamKey(d.a) && TeamKey(m.Away) == TeamKey(d.b)) || (TeamKey(m.Home) == TeamKey(d.b) && TeamKey(m.Away) == TeamKey(d.a)) {
			return " (" + d.name + ")"
		}
	}
	return ""
}

// Derbies lists traditional rivalry matches.
func (s *Store) Derbies(a Args) string {
	f := filterFrom(a)
	f.team = ""
	var b strings.Builder
	n := 0
	for _, m := range s.find(f) {
		if l := derbyLabel(m); l != "" {
			if n < a.num("limit", 50) {
				b.WriteString(formatMatch(m) + l + "\n")
			}
			n++
		}
	}
	if n == 0 {
		return "No derbies found for those criteria."
	}
	return fmt.Sprintf("Found %d derby matches:\n", n) + b.String()
}

// DataSummary describes loaded datasets.
func (s *Store) DataSummary(Args) string {
	files := make([]string, 0, len(s.Files))
	for f := range s.Files {
		files = append(files, f)
	}
	sort.Strings(files)
	var b strings.Builder
	b.WriteString("Loaded datasets:\n")
	for _, f := range files {
		fmt.Fprintf(&b, "- %s: %d rows\n", f, s.Files[f])
	}
	by := map[string]int{}
	for _, m := range s.Matches {
		by[m.Competition]++
	}
	fmt.Fprintf(&b, "\nUnique matches after de-duplication: %d\n", len(s.Matches))
	comps := make([]string, 0, len(by))
	for c := range by {
		comps = append(comps, c)
	}
	sort.Strings(comps)
	for _, c := range comps {
		fmt.Fprintf(&b, "- %s: %d\n", c, by[c])
	}
	fmt.Fprintf(&b, "Players: %d\n", len(s.Players))
	return b.String()
}
