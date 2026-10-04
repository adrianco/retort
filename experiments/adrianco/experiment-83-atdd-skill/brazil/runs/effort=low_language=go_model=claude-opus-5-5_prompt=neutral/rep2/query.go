package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter selects matches.
type MatchFilter struct {
	Team        string // either side
	Opponent    string // other side (requires Team)
	HomeTeam    string
	AwayTeam    string
	Competition string
	Season      int
	DateFrom    time.Time
	DateTo      time.Time
	Round       string // e.g. "final"
}

var sourcePriority = map[string]int{
	"Brasileirao_Matches.csv": 0, "Brazilian_Cup_Matches.csv": 0, "Libertadores_Matches.csv": 0,
	"novo_campeonato_brasileiro.csv": 1, "BR-Football-Dataset.csv": 2,
}

func firstTok(k string) string {
	if i := strings.IndexByte(k, ' '); i > 0 {
		return k[:i]
	}
	return k
}

func dedupKey(m *Match) string {
	return fmt.Sprintf("%s|%s|%d-%d|%s", firstTok(m.homeKey), firstTok(m.awayKey), m.HomeGoals, m.AwayGoals, m.Competition)
}

// sameFixture reports whether two records (from different sources) describe
// the same match; dates may differ by a day due to time zones.
func sameFixture(a, b *Match) bool {
	if a.Source == b.Source {
		return false
	}
	d := a.Date.Sub(b.Date)
	if d < 0 {
		d = -d
	}
	return d <= 36*time.Hour
}

// cupFinalRounds returns the last round number per season of the Copa do Brasil.
func (db *DB) cupFinalRounds() map[int]string {
	db.finalOnce.Do(func() {
		max := map[int]int{}
		for _, m := range db.Matches {
			if m.Competition == CompCopaDoBrasil && m.Source == "Brazilian_Cup_Matches.csv" {
				if r := atoi(m.Round); r > max[m.Season] {
					max[m.Season] = r
				}
			}
		}
		db.finalRounds = map[int]string{}
		for s, r := range max {
			if r < 5 { // season data incomplete; final not present
				continue
			}
			db.finalRounds[s] = fmt.Sprint(r)
		}
	})
	return db.finalRounds
}

func (db *DB) roundMatches(m *Match, round string) bool {
	if round == "" {
		return true
	}
	if Fold(m.Round) == round {
		return true
	}
	if round == "final" && m.Competition == CompCopaDoBrasil && m.Source == "Brazilian_Cup_Matches.csv" {
		return db.cupFinalRounds()[m.Season] == m.Round
	}
	return false
}

// FindMatches returns matching matches, de-duplicated across overlapping
// sources, sorted most recent first.
func (db *DB) FindMatches(f MatchFilter) []*Match {
	team, opp := TeamTokens(f.Team), TeamTokens(f.Opponent)
	home, away := TeamTokens(f.HomeTeam), TeamTokens(f.AwayTeam)
	comp := NormalizeCompetition(f.Competition)
	round := Fold(strings.TrimSpace(f.Round))
	buckets := map[string][]int{} // dedup key -> indexes into out
	var out []*Match
	for _, m := range db.Matches {
		if comp != "" && m.Competition != comp {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.DateFrom.IsZero() && m.Date.Before(f.DateFrom) {
			continue
		}
		if !f.DateTo.IsZero() && m.Date.After(f.DateTo.Add(24*time.Hour-time.Second)) {
			continue
		}
		if !db.roundMatches(m, round) {
			continue
		}
		if len(home) > 0 && !teamKeyMatches(m.homeKey, home) {
			continue
		}
		if len(away) > 0 && !teamKeyMatches(m.awayKey, away) {
			continue
		}
		if len(team) > 0 {
			h, a := teamKeyMatches(m.homeKey, team), teamKeyMatches(m.awayKey, team)
			if !h && !a {
				continue
			}
			if len(opp) > 0 {
				if !((h && teamKeyMatches(m.awayKey, opp)) || (a && teamKeyMatches(m.homeKey, opp))) {
					continue
				}
			}
		}
		k := dedupKey(m)
		dup := false
		for _, i := range buckets[k] {
			if sameFixture(out[i], m) {
				if sourcePriority[m.Source] < sourcePriority[out[i].Source] {
					out[i] = m
				}
				dup = true
				break
			}
		}
		if !dup {
			buckets[k] = append(buckets[k], len(out))
			out = append(out, m)
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	return out
}

// FormatMatch renders one match line.
func FormatMatch(m *Match) string {
	d := "unknown date"
	if !m.Date.IsZero() {
		d = m.Date.Format("2006-01-02")
	}
	extra := m.Competition
	if m.Round != "" {
		if _, err := fmt.Sscanf(m.Round, "%d", new(int)); err == nil {
			extra += " Round " + m.Round
		} else {
			extra += " " + m.Round
		}
	} else if m.Season != 0 {
		extra += fmt.Sprintf(" %d", m.Season)
	}
	s := fmt.Sprintf("%s: %s %d-%d %s (%s)", d, DisplayName(m.HomeTeam), m.HomeGoals, m.AwayGoals, DisplayName(m.AwayTeam), extra)
	if m.Arena != "" {
		s += " @ " + m.Arena
	}
	if m.HomeShots >= 0 && m.HomeCorners >= 0 {
		s += fmt.Sprintf(" [shots %d-%d, corners %d-%d]", m.HomeShots, m.AwayShots, m.HomeCorners, m.AwayCorners)
	}
	return s
}

func formatMatchList(ms []*Match, limit int) string {
	if limit <= 0 {
		limit = 20
	}
	var b strings.Builder
	for i, m := range ms {
		if i >= limit {
			fmt.Fprintf(&b, "- ... (%d more matches in dataset)\n", len(ms)-limit)
			break
		}
		b.WriteString("- " + FormatMatch(m) + "\n")
	}
	return b.String()
}

// SearchMatches is the text form of FindMatches.
func (db *DB) SearchMatches(f MatchFilter, limit int) string {
	ms := db.FindMatches(f)
	if len(ms) == 0 {
		return "No matches found for the given criteria."
	}
	return fmt.Sprintf("Found %d matches:\n%s", len(ms), formatMatchList(ms, limit))
}

// ---------- records ----------

// Record holds aggregate results.
type Record struct {
	Team                        string
	Played, Wins, Draws, Losses int
	GoalsFor, GoalsAgainst      int
	Points                      int
}

func (r *Record) add(gf, ga int) {
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
		r.Points += 3
	case gf == ga:
		r.Draws++
		r.Points++
	default:
		r.Losses++
	}
}

// WinRate in percent.
func (r *Record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Played)
}

// TeamRecord computes a team's record. venue is "home", "away" or "" (all).
func (db *DB) TeamRecord(team string, season int, competition, venue string) (*Record, []*Match) {
	q := TeamTokens(team)
	ms := db.FindMatches(MatchFilter{Team: team, Season: season, Competition: competition})
	r := &Record{Team: team}
	var used []*Match
	for _, m := range ms {
		h := teamKeyMatches(m.homeKey, q)
		if h && venue != "away" {
			r.add(m.HomeGoals, m.AwayGoals)
			used = append(used, m)
		} else if !h && venue != "home" {
			r.add(m.AwayGoals, m.HomeGoals)
			used = append(used, m)
		}
	}
	return r, used
}

// TeamRecordText formats TeamRecord.
func (db *DB) TeamRecordText(team string, season int, competition, venue string) string {
	r, ms := db.TeamRecord(team, season, competition, venue)
	if r.Played == 0 {
		return fmt.Sprintf("No matches found for %s with the given criteria.", team)
	}
	title := team
	if venue == "home" || venue == "away" {
		title += " " + venue
	}
	title += " record"
	var ctx []string
	if season != 0 {
		ctx = append(ctx, fmt.Sprint(season))
	}
	if c := NormalizeCompetition(competition); c != "" {
		ctx = append(ctx, c)
	}
	if len(ctx) > 0 {
		title += " (" + strings.Join(ctx, " ") + ")"
	}
	byComp := map[string]int{}
	for _, m := range ms {
		byComp[m.Competition]++
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %.1f%%\n",
		title, r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
	if len(byComp) > 1 {
		b.WriteString("- By competition: ")
		var parts []string
		for c, n := range byComp {
			parts = append(parts, fmt.Sprintf("%s %d", c, n))
		}
		sort.Strings(parts)
		b.WriteString(strings.Join(parts, ", ") + "\n")
	}
	b.WriteString("Recent matches:\n" + formatMatchList(ms, 5))
	return b.String()
}

// ---------- head to head ----------

var derbies = []struct{ name, a, b string }{
	{"Fla-Flu", "Flamengo", "Fluminense"},
	{"Derby Paulista", "Corinthians", "Palmeiras"},
	{"Choque-Rei", "Palmeiras", "Sao Paulo"},
	{"Majestoso", "Corinthians", "Sao Paulo"},
	{"San-São", "Santos", "Sao Paulo"},
	{"Clássico Alvinegro", "Corinthians", "Santos"},
	{"Clássico da Saudade", "Palmeiras", "Santos"},
	{"Grenal", "Gremio", "Internacional"},
	{"Clássico Mineiro", "Atletico MG", "Cruzeiro"},
	{"Clássico dos Milhões", "Flamengo", "Vasco"},
	{"Clássico Vovô", "Botafogo", "Fluminense"},
	{"Clássico da Amizade", "Botafogo", "Vasco"},
	{"Clássico Rei", "Flamengo", "Botafogo"},
	{"Clássico dos Gigantes", "Fluminense", "Vasco"},
	{"Ba-Vi", "Bahia", "Vitoria"},
	{"Atletiba", "Atletico PR", "Coritiba"},
	{"Clássico-Rei (CE)", "Ceara", "Fortaleza"},
}

func derbyName(a, b string) string {
	ka, kb := TeamTokens(a), TeamTokens(b)
	for _, d := range derbies {
		da, dbb := TeamKey(d.a), TeamKey(d.b)
		if (teamKeyMatches(da, ka) && teamKeyMatches(dbb, kb)) || (teamKeyMatches(da, kb) && teamKeyMatches(dbb, ka)) {
			return d.name
		}
	}
	return ""
}

// HeadToHead returns a summary of matches between two teams.
func (db *DB) HeadToHead(a, b string, competition string, season int, limit int) string {
	ms := db.FindMatches(MatchFilter{Team: a, Opponent: b, Competition: competition, Season: season})
	title := fmt.Sprintf("%s vs %s", a, b)
	if d := derbyName(a, b); d != "" {
		title += " (" + d + " derby)"
	}
	if len(ms) == 0 {
		return title + ": no matches found in dataset."
	}
	qa := TeamTokens(a)
	var wa, wb, dr, ga, gb int
	for _, m := range ms {
		x, y := m.HomeGoals, m.AwayGoals
		if !teamKeyMatches(m.homeKey, qa) {
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
			dr++
		}
	}
	return fmt.Sprintf("%s:\n%s\nHead-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws\nGoals: %s %d, %s %d\n",
		title, formatMatchList(ms, limit), len(ms), a, wa, b, wb, dr, a, ga, b, gb)
}

// ListDerbies searches all derby matches (optionally for a season).
func (db *DB) ListDerbies(season int, limit int) string {
	var b strings.Builder
	total := 0
	for _, d := range derbies {
		ms := db.FindMatches(MatchFilter{Team: d.a, Opponent: d.b, Season: season})
		if len(ms) == 0 {
			continue
		}
		total += len(ms)
		fmt.Fprintf(&b, "%s (%s vs %s): %d matches\n%s", d.name, d.a, d.b, len(ms), formatMatchList(ms, limit))
	}
	if total == 0 {
		return "No derby matches found."
	}
	return fmt.Sprintf("Derby matches found: %d\n%s", total, b.String())
}

// ---------- standings ----------

// Standings computes a league table from a single source to avoid
// double-counting overlapping datasets.
func (db *DB) Standings(season int, competition string) ([]*Record, string) {
	comp := NormalizeCompetition(competition)
	if comp == "" {
		comp = CompSerieA
	}
	bySource := map[string][]*Match{}
	for _, m := range db.Matches {
		if m.Season == season && m.Competition == comp {
			bySource[m.Source] = append(bySource[m.Source], m)
		}
	}
	src := ""
	for s, ms := range bySource {
		if src == "" || len(ms) > len(bySource[src]) || (len(ms) == len(bySource[src]) && sourcePriority[s] < sourcePriority[src]) {
			src = s
		}
	}
	tab := map[string]*Record{}
	get := func(name string) *Record {
		k := TeamKey(DisplayName(name))
		if r, ok := tab[k]; ok {
			return r
		}
		r := &Record{Team: DisplayName(name)}
		tab[k] = r
		return r
	}
	for _, m := range bySource[src] {
		get(m.HomeTeam).add(m.HomeGoals, m.AwayGoals)
		get(m.AwayTeam).add(m.AwayGoals, m.HomeGoals)
	}
	out := make([]*Record, 0, len(tab))
	for _, r := range tab {
		out = append(out, r)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if gd1, gd2 := a.GoalsFor-a.GoalsAgainst, b.GoalsFor-b.GoalsAgainst; gd1 != gd2 {
			return gd1 > gd2
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return out, src
}

// StandingsText formats the table, champion and relegation zone.
func (db *DB) StandingsText(season int, competition string, top int) string {
	tab, src := db.Standings(season, competition)
	comp := NormalizeCompetition(competition)
	if comp == "" {
		comp = CompSerieA
	}
	if len(tab) == 0 {
		return fmt.Sprintf("No %s data for %d.", comp, season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from %s):\n", season, comp, src)
	if top <= 0 || top > len(tab) {
		top = len(tab)
	}
	for i, r := range tab[:top] {
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW %dD %dL, GF %d, GA %d, GD %+d)\n", i+1, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalsFor-r.GoalsAgainst)
	}
	if comp == CompSerieA || comp == CompSerieB {
		fmt.Fprintf(&b, "Champion: %s with %d points\n", tab[0].Team, tab[0].Points)
		if len(tab) >= 16 {
			var rel []string
			for _, r := range tab[len(tab)-4:] {
				rel = append(rel, r.Team)
			}
			fmt.Fprintf(&b, "Relegation zone (bottom 4): %s\n", strings.Join(rel, ", "))
		}
	}
	return b.String()
}

// ---------- rankings ----------

// TeamRankings ranks teams by a metric over matches matching season/competition.
// metric: goals_for, goals_against, wins, win_rate, points. venue: home/away/"".
func (db *DB) TeamRankings(metric string, season int, competition, venue string, minMatches, limit int) string {
	ms := db.FindMatches(MatchFilter{Season: season, Competition: competition})
	tab := map[string]*Record{}
	get := func(name string) *Record {
		k := TeamKey(DisplayName(name))
		if r, ok := tab[k]; ok {
			return r
		}
		r := &Record{Team: DisplayName(name)}
		tab[k] = r
		return r
	}
	for _, m := range ms {
		if venue != "away" {
			get(m.HomeTeam).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			get(m.AwayTeam).add(m.AwayGoals, m.HomeGoals)
		}
	}
	if minMatches <= 0 {
		minMatches = 1
		if metric == "win_rate" {
			minMatches = 10
			if season == 0 {
				minMatches = 50
			}
		}
	}
	var out []*Record
	for _, r := range tab {
		if r.Played >= minMatches {
			out = append(out, r)
		}
	}
	val := func(r *Record) float64 {
		switch metric {
		case "goals_against":
			return -float64(r.GoalsAgainst)
		case "wins":
			return float64(r.Wins)
		case "win_rate":
			return r.WinRate()
		case "points":
			return float64(r.Points)
		default:
			return float64(r.GoalsFor)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if val(out[i]) != val(out[j]) {
			return val(out[i]) > val(out[j])
		}
		return out[i].Team < out[j].Team
	})
	if limit <= 0 {
		limit = 10
	}
	if len(out) == 0 {
		return "No data for the given criteria."
	}
	if metric == "" {
		metric = "goals_for"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Team ranking by %s", metric)
	if venue != "" {
		b.WriteString(" (" + venue + " matches)")
	}
	if season != 0 {
		fmt.Fprintf(&b, ", season %d", season)
	}
	if c := NormalizeCompetition(competition); c != "" {
		b.WriteString(", " + c)
	}
	b.WriteString(":\n")
	for i, r := range out {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "%d. %s - P %d, W %d D %d L %d, GF %d GA %d, win rate %.1f%%\n", i+1, r.Team, r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
	}
	return b.String()
}

// CompareSeasons aggregates statistics for each season.
func (db *DB) CompareSeasons(seasons []int, competition string) string {
	if competition == "" {
		competition = CompSerieA
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Season comparison (%s):\n", NormalizeCompetition(competition))
	for _, s := range seasons {
		ms := db.FindMatches(MatchFilter{Season: s, Competition: competition})
		if len(ms) == 0 {
			fmt.Fprintf(&b, "%d: no data\n", s)
			continue
		}
		var goals, hw, aw, dr int
		for _, m := range ms {
			goals += m.HomeGoals + m.AwayGoals
			switch {
			case m.HomeGoals > m.AwayGoals:
				hw++
			case m.HomeGoals < m.AwayGoals:
				aw++
			default:
				dr++
			}
		}
		n := float64(len(ms))
		fmt.Fprintf(&b, "%d: %d matches, %d goals (%.2f/match), home wins %.1f%%, away wins %.1f%%, draws %.1f%%",
			s, len(ms), goals, float64(goals)/n, 100*float64(hw)/n, 100*float64(aw)/n, 100*float64(dr)/n)
		if tab, _ := db.Standings(s, competition); len(tab) > 0 {
			fmt.Fprintf(&b, ", leader: %s (%d pts)", tab[0].Team, tab[0].Points)
		}
		b.WriteString("\n")
	}
	return b.String()
}

// TeamCompetitions lists competitions and seasons a team appears in.
func (db *DB) TeamCompetitions(team string) string {
	ms := db.FindMatches(MatchFilter{Team: team})
	if len(ms) == 0 {
		return fmt.Sprintf("No matches found for %s.", team)
	}
	type agg struct {
		n       int
		seasons map[int]bool
	}
	by := map[string]*agg{}
	for _, m := range ms {
		a := by[m.Competition]
		if a == nil {
			a = &agg{seasons: map[int]bool{}}
			by[m.Competition] = a
		}
		a.n++
		a.seasons[m.Season] = true
	}
	var comps []string
	for c := range by {
		comps = append(comps, c)
	}
	sort.Strings(comps)
	var b strings.Builder
	fmt.Fprintf(&b, "Competitions for %s (%d matches in dataset):\n", team, len(ms))
	for _, c := range comps {
		var ss []int
		for s := range by[c].seasons {
			ss = append(ss, s)
		}
		sort.Ints(ss)
		fmt.Fprintf(&b, "- %s: %d matches, seasons %d-%d (%d seasons)\n", c, by[c].n, ss[0], ss[len(ss)-1], len(ss))
	}
	return b.String()
}

// ---------- players ----------

// PlayerFilter selects players.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string // exact position code or group: forward, midfielder, defender, goalkeeper
	MinOverall  int
}

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"},
	"midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

func positionMatches(pos, q string) bool {
	q = strings.TrimSuffix(strings.ToLower(strings.TrimSpace(q)), "s")
	if q == "" {
		return true
	}
	switch q {
	case "striker", "attacker", "winger":
		q = "forward"
	case "midfield":
		q = "midfielder"
	case "defence", "defense", "back":
		q = "defender"
	case "keeper", "gk":
		q = "goalkeeper"
	}
	if g, ok := positionGroups[q]; ok {
		for _, p := range g {
			if p == pos {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(pos, q)
}

// FindPlayers returns players sorted by Overall descending.
func (db *DB) FindPlayers(f PlayerFilter) []*Player {
	name := Fold(strings.TrimSpace(f.Name))
	nat := Fold(strings.TrimSpace(f.Nationality))
	if nat == "brazilian" {
		nat = "brazil"
	}
	club := TeamTokens(f.Club)
	var out []*Player
	for _, p := range db.Players {
		if name != "" && !strings.Contains(p.nameKey, name) {
			continue
		}
		if nat != "" && Fold(p.Nationality) != nat {
			continue
		}
		if len(club) > 0 && !teamKeyMatches(p.clubKey, club) {
			continue
		}
		if !positionMatches(p.Position, f.Position) {
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

// FormatPlayer renders one player line.
func FormatPlayer(p *Player) string {
	club := p.Club
	if club == "" {
		club = "Free agent"
	}
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s", p.Name, p.Overall, p.Potential, p.Position, p.Age, p.Nationality, club)
}

// SearchPlayers is the text form of FindPlayers.
func (db *DB) SearchPlayers(f PlayerFilter, limit int) string {
	ps := db.FindPlayers(f)
	if len(ps) == 0 {
		msg := "No players found for the given criteria."
		if f.Club != "" {
			msg += " Note: the FIFA dataset does not include some Brazilian clubs (e.g. Flamengo, Palmeiras, São Paulo, Corinthians) due to licensing; use players_by_club to see which clubs are covered."
		}
		return msg
	}
	if limit <= 0 {
		limit = 20
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d players (sorted by overall rating):\n", len(ps))
	for i, p := range ps {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more)\n", len(ps)-limit)
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(p))
	}
	return b.String()
}

// PlayerDetails returns full attributes for players matching name.
func (db *DB) PlayerDetails(name string) string {
	ps := db.FindPlayers(PlayerFilter{Name: name})
	if len(ps) == 0 {
		return fmt.Sprintf("No player named %q found.", name)
	}
	var b strings.Builder
	for i, p := range ps {
		if i >= 5 {
			fmt.Fprintf(&b, "... (%d more players match)\n", len(ps)-5)
			break
		}
		fmt.Fprintf(&b, "%s\n  Jersey: %s, Height: %s, Weight: %s, Foot: %s, Value: %s\n  Skills:", FormatPlayer(p), p.Jersey, p.Height, p.Weight, p.Foot, p.Value)
		for _, s := range skillCols {
			if v, ok := p.Skills[s]; ok {
				fmt.Fprintf(&b, " %s %d,", s, v)
			}
		}
		b.WriteString("\n")
	}
	return strings.TrimRight(b.String(), ",\n") + "\n"
}

// brazilianClubKeys are teams appearing in Brazilian domestic match data.
func (db *DB) brazilianClubKeys() map[string]bool {
	keys := map[string]bool{}
	for _, m := range db.Matches {
		if m.Competition == CompLibertadores {
			continue
		}
		keys[TeamKey(DisplayName(m.HomeTeam))] = true
		keys[TeamKey(DisplayName(m.AwayTeam))] = true
	}
	return keys
}

// PlayersByClub summarizes players of a nationality grouped by club.
// If brazilianClubsOnly, only clubs found in Brazilian match data are included.
func (db *DB) PlayersByClub(nationality string, brazilianClubsOnly bool, limit int) string {
	ps := db.FindPlayers(PlayerFilter{Nationality: nationality})
	var bk map[string]bool
	if brazilianClubsOnly {
		bk = db.brazilianClubKeys()
	}
	type agg struct {
		n, sum int
	}
	by := map[string]*agg{}
	for _, p := range ps {
		if p.Club == "" {
			continue
		}
		if bk != nil && !bk[p.clubKey] {
			continue
		}
		a := by[p.Club]
		if a == nil {
			a = &agg{}
			by[p.Club] = a
		}
		a.n++
		a.sum += p.Overall
	}
	clubs := make([]string, 0, len(by))
	for c := range by {
		clubs = append(clubs, c)
	}
	sort.Slice(clubs, func(i, j int) bool {
		if by[clubs[i]].n != by[clubs[j]].n {
			return by[clubs[i]].n > by[clubs[j]].n
		}
		return clubs[i] < clubs[j]
	})
	if len(clubs) == 0 {
		return "No players found."
	}
	if limit <= 0 {
		limit = 20
	}
	var b strings.Builder
	label := nationality
	if label == "" {
		label = "All"
	}
	fmt.Fprintf(&b, "%s players by club", label)
	if brazilianClubsOnly {
		b.WriteString(" (Brazilian clubs)")
	}
	b.WriteString(":\n")
	for i, c := range clubs {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f)\n", c, by[c].n, float64(by[c].sum)/float64(by[c].n))
	}
	return b.String()
}

// TeamProfile combines match data with FIFA player data for a club (cross-file).
func (db *DB) TeamProfile(team string) string {
	var b strings.Builder
	b.WriteString(db.TeamRecordText(team, 0, "", ""))
	b.WriteString("\n")
	b.WriteString(db.TeamCompetitions(team))
	ps := db.FindPlayers(PlayerFilter{Club: team})
	b.WriteString("\nFIFA players at club:\n")
	if len(ps) == 0 {
		b.WriteString("- none in FIFA dataset\n")
	}
	for i, p := range ps {
		if i >= 10 {
			fmt.Fprintf(&b, "... (%d more)\n", len(ps)-10)
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(p))
	}
	return b.String()
}

// Overview describes loaded datasets.
func (db *DB) Overview() string {
	var b strings.Builder
	b.WriteString("Loaded datasets:\n")
	var files []string
	for f := range db.Sources {
		files = append(files, f)
	}
	sort.Strings(files)
	for _, f := range files {
		fmt.Fprintf(&b, "- %s: %d rows\n", f, db.Sources[f])
	}
	by := map[string]int{}
	for _, m := range db.Matches {
		by[m.Competition]++
	}
	b.WriteString("Matches by competition (raw, incl. overlaps):\n")
	var cs []string
	for c := range by {
		cs = append(cs, c)
	}
	sort.Strings(cs)
	for _, c := range cs {
		fmt.Fprintf(&b, "- %s: %d\n", c, by[c])
	}
	return b.String()
}
